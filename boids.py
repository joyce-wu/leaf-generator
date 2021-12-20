import bpy
from mathutils import Vector, Matrix
from math import *
import random

params = {
    'animation_step' : 5,
    'animation_length' : 300 * 5,
    'visual_range' : 7.5,       # radius of vision for each boid
    'collision_radius' : 2.0,   # collision radius
    
    # weights for boid behavior rules
    'fly_towards_center' : 1.0,
    'avoid_collisions' : 1.0,
    'match_velocity' : 1.0,
    'stay_in_territory' : 1.0,
    
    'max_speed': 35.0,
    'territory_center' : Vector([0,0,10]),
    'territory_radius' : 40,
    'count' : 50,               # number of boids
    'seed' : 123456
}



class Boid:
    def __init__(self, name, p, v):
        self.name = name
        self.p = p # position
        self.v = v # velocity vector
        self.history = [] # array of (p, v)
        self.history.append( (self.p.copy(), self.v.copy()) )

    def save_frame(self):
        self.p += self.v
        self.p.z = max(self.p.z, 0)
        self.history.append( (self.p.copy(), self.v.copy()) )

    def draw(self):
        # draw boid
        bpy.ops.mesh.primitive_cone_add(
            radius1=1,
            radius2=0,
            depth=2,
            enter_editmode=False,
            align='WORLD',
            location=(0, 0, 0), 
            scale=(1, 1, 1)
        )
        bpy.context.object.name = self.name
        bpy.context.object.data.name = self.name
        # bpy.ops.object.shade_smooth()
        # bpy.data.objects[name].scale = [scale, scale, scale]

        obj = bpy.context.object
        obj.rotation_mode = 'QUATERNION'

        for i, (p, v) in enumerate(self.history):
            t = i * params['animation_step']
            if t > params['animation_length']:
                return

            # location
            obj.location = p
            obj.keyframe_insert(data_path="location", frame=t)

            # direction
            # construct h, l, u
            h = v.normalized()
            up = Vector([0, 0, 1])
            l = up.cross(h)
            l.normalize()
            u = h.cross(l)

            # turn into angle
            mat = Matrix([h, l, u])
            mat.transpose()
            
            base_mat = Matrix([[0, 0, 1], [0, 1, 0], [-1, 0, 0]])
            mat = mat @ base_mat

            quat = mat.to_quaternion()
            obj.rotation_quaternion = quat
            obj.keyframe_insert(data_path="rotation_quaternion", frame=t)

def boids_init():
    boids = []
    r = params['territory_radius']
    s = params['max_speed'] * 0.5
    while len(boids) < params['count']:
        p = []
        v = []
        for i in range(3):
            p.append(random.random() * r - r/2)
            v.append(random.random() * s - s/2)
        
        p = Vector(p)
        v = Vector(v)
        if p.z <= 0:
            continue
        
        name = "boid_{:04}".format(len(boids))
        boids.append(Boid(name, p, v))

    print("Created {} boids".format(len(boids)))
    return boids
    

# return the list of boids that are radius distance or closer to boids[ix]
def boids_get_neighbors(boids, ix, radius):
    boid = boids[ix]
    radius_squared = radius ** 2
    
    for i, other_boid in enumerate(boids):
        if i == ix:
            continue
        dist_squared = (other_boid.p - boid.p).length_squared
        if dist_squared < radius_squared:
            yield other_boid
        

# make boids fly towards center of neighbors. modifies boids[ix].v
def boids_fly_towards_center(boids):
    factor = 0.05 * params['fly_towards_center']
    
    for ix in range(len(boids)):
        center = Vector([0,0,0])
        n_neighbors = 0
        
        for neighbor in boids_get_neighbors(boids, ix, params['visual_range']):
            center += neighbor.p
            n_neighbors += 1
        
        if n_neighbors:
            center = center / n_neighbors
            boids[ix].v += (center - boids[ix].p) * factor

# make boids avoid others that are too close. modifies boids[ix].v
def boids_avoid_collisions(boids):
    factor = 0.05 * params['avoid_collisions']
    dv = Vector([0,0,0])
    
    for ix in range(len(boids)):
        for neighbor in boids_get_neighbors(boids, ix, params['collision_radius']):
            dv += (boids[ix].p - neighbor.p)
        
        boids[ix].v += dv * factor

# make boids match velocity of neighbors. modifies boids[ix].v
def boids_match_velocity(boids):
    factor = 0.05 * params['match_velocity']
    
    for ix in range(len(boids)):
        avg_v = Vector([0,0,0])
        n_neighbors = 0
        
        for neighbor in boids_get_neighbors(boids, ix, params['visual_range']):
            avg_v += neighbor.v
            n_neighbors += 1
        
        if n_neighbors:
            avg_v = avg_v / n_neighbors
            boids[ix].v += (avg_v - boids[ix].v) * factor

# limit boids speed
def boids_limit_speed(boids):
    for boid in boids:
        s_sq = boid.v.length_squared
        if s_sq > params['max_speed']**2:
            boid.v.normalize()
            boid.v = boid.v * params['max_speed']
            print("limit speed")


# keep boids in territory
def boids_stay_in_territory(boids):
    factor = 1.0 * params['stay_in_territory'] * params['max_speed']/10
    r = params['territory_radius']
    margin = 5
    r -= margin
    
    for boid in boids:
        dist = boid.p - params['territory_center']
        if dist.length_squared > params['territory_radius']**2:
            dv = dist.normalized()
            boid.v -= dv * factor
        
        if boid.p.z < margin:
            boid.v.z += factor

def gen_right_wing():
    return (
        [#vectors
            Vector([0, 0, 0]), 
            Vector([0.2, 0, 0.2]),
            Vector([0.35, 0, 0.15]),
            Vector([0.35, 0, 0.05]),
            Vector([0.3, 0, -0.05]),
            Vector([0.05, 0, -0.15]),
            Vector([0.3, 0, -0.25]),
            Vector([0.35, 0, -0.4]),
            Vector([0.2, 0, -0.55]),
            Vector([0, 0, -0.3]),
        ],
        [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]], #faces
    )

def gen_left_wing():
    return (
        [#vectors
            Vector([0, 0, 0]), 
            Vector([-0.2, 0, 0.2]),
            Vector([-0.35, 0, 0.15]),
            Vector([-0.35, 0, 0.05]),
            Vector([-0.3, 0, -0.05]),
            Vector([-0.05, 0, -0.15]),
            Vector([-0.3, 0, -0.25]),
            Vector([-0.35, 0, -0.4]),
            Vector([-0.2, 0, -0.55]),
            Vector([0, 0, -0.3]),
        ],
        [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]], #faces
    )

def execute():
    random.seed(params['seed'])
    
    right_wing = gen_right_wing()
    right_verts = right_wing[0]
    right_faces = right_wing[1]
    mesh = bpy.data.meshes.new(name="Wing")
    mesh.from_pydata(right_verts, [], right_faces) 
    rwing_obj = bpy.data.objects.new("Wing", mesh)
    bpy.context.scene.collection.objects.link(rwing_obj)
    bpy.context.view_layer.objects.active = rwing_obj
    
    left_wing = gen_left_wing()
    left_verts = left_wing[0]
    left_faces = left_wing[1]
    mesh = bpy.data.meshes.new(name="Wing")
    mesh.from_pydata(left_verts, [], left_faces) 
    lwing_obj = bpy.data.objects.new("Wing", mesh)
    bpy.context.scene.collection.objects.link(lwing_obj)
    bpy.context.view_layer.objects.active = lwing_obj
    lwing_obj.select_get()
    
    
    '''
    radius = 5
    z_rotation = 0
    rotation_step = 1.25
    direction = 1
    boid = Boid("boid_test", p=Vector([radius,0,0]), v=Vector([0,radius,0]))
    
    for i in range(0, params['animation_length'], params['animation_step']):
        rad = i * params['animation_step'] / params['animation_length'] * 2 * pi
        boid.v = radius * Vector([-1 * sin(rad), cos(rad), 0])
        boid.save_frame()
        
        total_steps = params['animation_length'] / params['animation_step']
        
        if (z_rotation >= 1.25):
            direction = -1
        elif (z_rotation <= -1.25):
            direction = 1
        
        z_rotation += (rotation_step * direction)
        rwing_obj.rotation_euler = (0, 0, z_rotation)
        lwing_obj.rotation_euler = (0, 0, -z_rotation) 
        t = i * params['animation_step'] / 8
        lwing_obj.keyframe_insert(data_path="rotation_euler", frame=t)
        rwing_obj.keyframe_insert(data_path="rotation_euler", frame=t)
        

    boid.draw()
    '''
    
    boids = boids_init()

    for i in range(0, params['animation_length'], params['animation_step']):
        boids_fly_towards_center(boids)
        boids_avoid_collisions(boids)
        boids_match_velocity(boids)
        boids_limit_speed(boids)
        boids_stay_in_territory(boids)
        
        for boid in boids:
            boid.save_frame()
    
    for boid in boids:
        boid.draw()
        
    
execute()
