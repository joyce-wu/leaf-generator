import bpy
from mathutils import Vector, Matrix
from math import *

params = {
    'animation_step' : 5,
    'animation_length' : 600
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

            euler = mat.to_euler('XYZ')

            obj.rotation_euler = euler
            obj.keyframe_insert(data_path="rotation_euler", frame=t)

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
        

    print(boid.history)
    boid.draw()

execute()
