'''

Sources:
https://github.com/abiusx/L3D (to quickly test generated strings)
https://github.com/friggog/tree-gen/blob/master/leaf.py
The Algorithmic Beauty of Plants, ch 1-2

'''
bl_info = {
    "name": "Tree Generator",
    "category": "Object",
    "description": "Generate trees with leaf and branch variation",
    "author": "Lance Tan and Joyce Wu",
    "version": (1, 0),
    'blender': (2, 80, 0),
    "location": "View3D > Tool",
}

import bpy
import bmesh
from mathutils import Vector, Matrix, Euler
from math import *
import random

SCENE_SIZE = 100
class TreeProperties(bpy.types.PropertyGroup):
    leaf_types = [('1', 'Ovate', 'Ovate'), ('2', 'Linear', 'Linear'), ('3', 'Cordate', 'Cordate'), ('4', 'Maple', 'Maple'), ('5', 'Palmate', 'Palmate'), ('6', 'Spiky Oak', 'Spiky Oak'), ('7', 'Rounded Oak', 'Rounded Oak'), ('8', 'Elliptic', 'Elliptic'), ('9', 'Rectangle', 'Rectangle'), ('10', 'Triangle', 'Triangle')]
    
    leaf_type : bpy.props.EnumProperty(name="Type", items=leaf_types)
    leaf_bend : bpy.props.FloatProperty(name="Bend", default=90, min=0, max=360)
    leaf_scale : bpy.props.FloatProperty(name="Scale", default=0.8)
    leaf_branch_angle : bpy.props.IntProperty(name="Leaf Branch Angle", default=41)
    branch_length : bpy.props.FloatProperty(name="Length", default=1.0, min=0.01)
    branch_length_scale : bpy.props.FloatProperty(name="Length Scale", default=1.1)
    branch_thickness : bpy.props.FloatProperty(name="Thickness", default=0.1)
    branch_angle : bpy.props.FloatProperty(name="Angle", default=35, min=0, max=360)
    n_iter : bpy.props.IntProperty(name="Level Count", default=1, min=1, max=5)
    tropism : bpy.props.FloatVectorProperty(name="Tropism", default=(0, 0, -1), size=3)
    tropism_scale : bpy.props.FloatProperty(name="Tropism Scale", default=0.22)
    seed : bpy.props.IntProperty(name="Seed", default=6)
        
class LNode:
    def __init__(self, l, *params):
        self.l = l
        self.params = params

    def __repr__(self):
        if not self.params:
            return self.l
        else:
            return self.l + '(' + ','.join('{:.3f}'.format(x) for x in self.params) + ')'

    def apply_rule(self, successors):
        ans = []
        for node_or_func in successors:
            if callable(node_or_func):
                ans.append(node_or_func(self))
            else:
                ans.append(node_or_func)
        return ans

class LSystem:
    def parse_lstring(s):
        i = 0
        ans = []
        while i < len(s):
            ch = s[i]
            if i+1 < len(s) and s[i+1] == '(':
                j = s.find(')', i+1)
                params = s[i+2:j]
                params = [float(x) for x in params.split(',')]
                ans.append(LNode(ch, *params))
                i = j + 1
            else:
                ans.append(LNode(ch))
                i += 1

        return ans

    def lstring_to_str(lstring):
        return ''.join(str(lnode) for lnode in lstring)

    def generate_lstring(axiom, rules, n_iter):
        lstring = axiom    
        for i in range(n_iter):
            ans = []
            for node in lstring:
                if node.l in rules.keys():
                    ans += node.apply_rule(rules[node.l])
                else:
                    ans.append(node)
            lstring = ans

        return lstring
    
    def draw_lstring(lstring, pos, **params):
        turtle = Turtle(pos=pos, **params)
        for lnode in lstring:
            l, params = lnode.l, lnode.params
            if l == 'F':
                turtle.draw(params[0])
            elif l == '[':
                turtle.push_state()
            elif l == ']':
                turtle.pop_state()
            elif l == '/':
                turtle.rotate_h(params[0])
            elif l == '\\':
                turtle.rotate_h(-params[0])
            elif l == '+':
                turtle.rotate_u(params[0])
            elif l == '-':
                turtle.rotate_u(-params[0])
            elif l == '&':
                turtle.rotate_l(params[0])
            elif l == '^':
                turtle.rotate_l(-params[0])
            elif l == '$':
                turtle.rotate_horizontal()
            elif l == '?':
                turtle.rotate_h(360*random.random())
            elif l == '!':
                turtle.thickness = params[0]
            elif l == 'L':
                turtle.draw_leaf()

class Branch(bpy.types.Operator):
    bl_idname = "object.branch_gen"
    bl_category = "Branch Generator"
    bl_label = "Generate Branch"
    bl_options = {'REGISTER'}
    
    def verts():
        verts = []
        for k in range(48):
            angle = (2 * pi) / 48 * k
            r = 1 + (cos(4 * angle) / 6)
            verts.append(Vector((r * cos(angle), r * sin(angle), 0)))
        return verts
    
    def faces():
        faces = []
        for k in range(48):
            faces.append(k)    
        return [faces]
    
    verts = verts()
    faces = faces()
    
    def gen_branch(pos, dist, end, direction, thickness):
        branch_verts = [vert.xyz * thickness + pos.xyz for vert in Branch.verts]
        mesh = bpy.data.meshes.new(name="Branch")
        mesh.from_pydata(branch_verts, [], Branch.faces)
        obj = bpy.data.objects.new("Branch", mesh)
        bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_get()
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        faces = bm.faces[:]
        extrude_vec = end - pos
        for face in faces:
            r = bmesh.ops.extrude_discrete_faces(bm, faces=[face])
            bmesh.ops.translate(bm, vec=extrude_vec, verts=r['faces'][0].verts)
        bm.to_mesh(obj.data)
        obj.data.update()

class Leaf(bpy.types.Operator):
    bl_idname = "object.leaf_gen"
    bl_category = "Leaf Generator"
    bl_label = "Generate Leaf"
    bl_options = {'REGISTER'}
    
    def gen_leaf(leaf_type, scale, location, direction, bend_angle):
        mesh = bpy.data.meshes.new(name="Leaf")
        shape = leaf_shape(leaf_type)
        verts = shape[0]
        faces = shape[1]
        
        verts = [vert.zxy * scale for vert in verts]
        
        mesh.from_pydata(verts, [], faces) 
        
        obj = bpy.data.objects.new("Leaf", mesh)
        bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_get()
        
        obj.location = location + bpy.context.scene.cursor.location
        obj.rotation_euler = direction
        
        modifier = obj.modifiers.new(name='Bend', type='SIMPLE_DEFORM')
        modifier.deform_method = 'TWIST'
        modifier.deform_axis = 'X'
        modifier.angle = radians(bend_angle)

class Turtle:
    def __init__(self, tropism=None, tropism_scale=0, pos=Vector([0,0,0]), **params):
        # pushed to stack
        self.pos = pos
        self.h = Vector([0, 0, 1]) # heading
        self.l = Vector([1, 0, 0]) # direction left
        self.u = Vector([0, 1, 0]) # direction up
        self.thickness = 0.05
        
        # not pushed to stack because they never change
        self.tropism = tropism
        self.params = params
        self.tropism_scale = tropism_scale
        
        self.stack = []
    
    def rotate_h(self, deg):
        mat = Matrix.Rotation(deg/180*pi, 4, self.h)
        self.l.rotate(mat)
        self.u.rotate(mat)
    
    def rotate_l(self, deg):
        mat = Matrix.Rotation(deg/180*pi, 4, self.l)
        self.h.rotate(mat)
        self.u.rotate(mat)
    
    def rotate_u(self, deg):
        mat = Matrix.Rotation(deg/180*pi, 4, self.u)
        self.h.rotate(mat)
        self.l.rotate(mat)
    
    def rotate_horiziontal(self):
        v = Vector([0, 0, 1])
        self.l = v.cross(h)
        self.l.normalize()
        self.u = self.h.cross(self.l)
        
    def draw(self, dist):
        end = self.pos + dist * self.h
        mat = Matrix([self.h, self.l, self.u])
        mat.transpose()
        euler = mat.to_euler('XYZ')
        Branch.gen_branch(self.pos, dist, end, euler, self.thickness)
        self.pos = end
        
        if self.tropism and self.tropism_scale:
            torque = self.h.cross(self.tropism)
            theta = 0
            if torque.length > 0.0001:
                try:
                    theta = asin(min(torque.length, 1))
                except:
                    bprint('bad torque length', torque.length)
                    
            if theta:
                torque.normalize()
                mat = Matrix.Rotation(theta * self.tropism_scale, 4, torque)
                self.h.rotate(mat)
                self.l.rotate(mat)
                self.u.rotate(mat)
    
    def draw_leaf(self):
        
        mat = Matrix([self.h, self.l, self.u])
        mat.transpose()
        euler = mat.to_euler('XYZ')
        
        Leaf.gen_leaf(self.params['leaf_type'], self.params['leaf_scale'], self.pos, euler, self.params['leaf_bend'])
        
        
    def push_state(self):
        state = [
            self.pos.copy(),
            self.h.copy(),
            self.l.copy(),
            self.u.copy(),
            self.thickness
        ]
        self.stack.append(state)
    
    def pop_state(self):
        [
            self.pos,
            self.h,
            self.l,
            self.u,
            self.thickness
        ] = self.stack.pop()    
        
class Field:
    def draw():
        mesh = bpy.data.meshes.new(name="Grass Blade")
        shape = leaf_shape(0)
        verts = [
                    Vector([0, 0, 0]),
                    Vector([0, 0, 1]),
                    Vector([1, 0, 4]),
                    Vector([2, 0, 6]),
                    Vector([3, 0, 7]),
                    Vector([3.5, 0, 7]),
                    Vector([3, 0, 6.5]),
                    Vector([1.5, 0, 4]),
                    Vector([0.5, 0, 1]),
                    Vector([0.5, 0, 0]),
                ]
        faces = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]]
        mesh.from_pydata(verts, [], faces) 

        blade = bpy.data.objects.new("Blade", mesh)
        bpy.context.scene.collection.objects.link(blade)
        bpy.context.view_layer.objects.active = blade
        blade.select_get()
#        mat = bpy.data.materials.new(name='GrassMaterial')
#        blade.data.materials.append(mat)
#        mat.use_nodes=True
#        mat_nodes = mat.node_tree.nodes
#        mat_nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.010, 0.0065, 0.8, 1.0)
            

        bpy.ops.mesh.primitive_plane_add(size=SCENE_SIZE)
        grass = bpy.context.active_object
        grass.modifiers.new("grass", type='PARTICLE_SYSTEM')
        ps = grass.particle_systems["grass"].settings
        ps.type = 'HAIR'
        ps.use_advanced_hair = True
        ps.render_type = 'OBJECT'
        ps.instance_object = bpy.data.objects["Blade"]
        ps.count = 20000
        ps.particle_size = 0.075
        ps.size_random = 0.5
        ps.use_rotations = True
        ps.rotation_factor_random = 0.2
        ps.rotation_mode = 'GLOB_Y'

def leaf_shape(t):
    return [
        (  # 1 = ovate
            [
                Vector([0.005, 0, 0]),
                Vector([0.005, 0, 0.1]),
                Vector([0.15, 0, 0.15]),
                Vector([0.25, 0, 0.3]),
                Vector([0.2, 0, 0.6]),
                Vector([0, 0, 1]),
                Vector([-0.2, 0, 0.6]),
                Vector([-0.25, 0, 0.3]),
                Vector([-0.15, 0, 0.15]),
                Vector([-0.005, 0, 0.1]),
                Vector([-0.005, 0, 0]),
            ],
            [[0, 1, 9, 10], [1, 2, 3, 4], [4, 5, 6], [6, 7, 8, 9], [4, 6, 9, 1]],
        ),
        (  # 2 = linear
            [
                Vector([0.005, 0, 0]),
                Vector([0.005, 0, 0.1]),
                Vector([0.1, 0, 0.15]),
                Vector([0.1, 0, 0.95]),
                Vector([0, 0, 1]),
                Vector([-0.1, 0, 0.95]),
                Vector([-0.1, 0, 0.15]),
                Vector([-0.005, 0, 0.1]),
                Vector([-0.005, 0, 0]),
            ],
            [[0, 1, 7, 8], [1, 2, 3], [3, 4, 5], [5, 6, 7], [1, 3, 5, 7]],
        ),
        (  # 3 = cordate
            [
                Vector([0.005, 0, 0]),
                Vector([0.01, 0, 0.2]),
                Vector([0.2, 0, 0.1]),
                Vector([0.35, 0, 0.35]),
                Vector([0.25, 0, 0.6]),
                Vector([0.1, 0, 0.8]),
                Vector([0, 0, 1]),
                Vector([-0.1, 0, 0.8]),
                Vector([-0.25, 0, 0.6]),
                Vector([-0.35, 0, 0.35]),
                Vector([-0.2, 0, 0.1]),
                Vector([-0.01, 0, 0.2]),
                Vector([-0.005, 0, 0]),
            ],
            [
                [0, 1, 11, 12],
                [1, 2, 3, 4],
                [11, 10, 9, 8],
                [11, 1, 4, 8],
                [8, 7, 6, 5, 4],
            ],
        ),
        (  # 4 = maple
            [
                Vector([0.005, 0, 0]),
                Vector([0.005, 0, 0.1]),
                Vector([0.25, 0, 0.07]),
                Vector([0.2, 0, 0.18]),
                Vector([0.5, 0, 0.37]),
                Vector([0.43, 0, 0.4]),
                Vector([0.45, 0, 0.58]),
                Vector([0.3, 0, 0.57]),
                Vector([0.27, 0, 0.67]),
                Vector([0.11, 0, 0.52]),
                Vector([0.2, 0, 0.82]),
                Vector([0.08, 0, 0.77]),
                Vector([0, 0, 1]),
                Vector([-0.08, 0, 0.77]),
                Vector([-0.2, 0, 0.82]),
                Vector([-0.11, 0, 0.52]),
                Vector([-0.27, 0, 0.67]),
                Vector([-0.3, 0, 0.57]),
                Vector([-0.45, 0, 0.58]),
                Vector([-0.43, 0, 0.4]),
                Vector([-0.5, 0, 0.37]),
                Vector([-0.2, 0, 0.18]),
                Vector([-0.25, 0, 0.07]),
                Vector([-0.005, 0, 0.1]),
                Vector([-0.005, 0, 0]),
            ],
            [
                [0, 1, 23, 24],
                [1, 2, 3, 4, 5],
                [23, 22, 21, 20, 19],
                [1, 5, 6, 7, 8],
                [23, 19, 18, 17, 16],
                [1, 8, 9, 10, 11],
                [23, 16, 15, 14, 13],
                [1, 11, 12, 13, 23],
            ],
        ),
        (  # 5 = palmate
            [
                Vector([0.005, 0, 0]),
                Vector([0.005, 0, 0.1]),
                Vector([0.25, 0, 0.1]),
                Vector([0.5, 0, 0.3]),
                Vector([0.2, 0, 0.45]),
                Vector([0, 0, 1]),
                Vector([-0.2, 0, 0.45]),
                Vector([-0.5, 0, 0.3]),
                Vector([-0.25, 0, 0.1]),
                Vector([-0.005, 0, 0.1]),
                Vector([-0.005, 0, 0]),
            ],
            [[0, 1, 9, 10], [1, 2, 3, 4], [1, 4, 5, 6, 9], [9, 8, 7, 6]],
        ),
        (  # 6 = spiky oak
            [
                Vector([0.005, 0, 0]),
                Vector([0.005, 0, 0.1]),
                Vector([0.16, 0, 0.17]),
                Vector([0.11, 0, 0.2]),
                Vector([0.23, 0, 0.33]),
                Vector([0.15, 0, 0.34]),
                Vector([0.32, 0, 0.55]),
                Vector([0.16, 0, 0.5]),
                Vector([0.27, 0, 0.75]),
                Vector([0.11, 0, 0.7]),
                Vector([0.18, 0, 0.9]),
                Vector([0.07, 0, 0.86]),
                Vector([0, 0, 1]),
                Vector([-0.07, 0, 0.86]),
                Vector([-0.18, 0, 0.9]),
                Vector([-0.11, 0, 0.7]),
                Vector([-0.27, 0, 0.75]),
                Vector([-0.16, 0, 0.5]),
                Vector([-0.32, 0, 0.55]),
                Vector([-0.15, 0, 0.34]),
                Vector([-0.23, 0, 0.33]),
                Vector([-0.11, 0, 0.2]),
                Vector([-0.16, 0, 0.17]),
                Vector([-0.005, 0, 0.1]),
                Vector([-0.005, 0, 0]),
            ],
            [
                [0, 1, 23, 24],
                [1, 2, 3],
                [3, 4, 5],
                [5, 6, 7],
                [7, 8, 9],
                [9, 10, 11],
                [1, 3, 5, 7, 9, 11, 12, 13, 15, 17, 19, 21, 23],
                [23, 22, 21],
                [21, 20, 19],
                [19, 18, 17],
                [17, 16, 15],
                [15, 14, 13],
            ],
        ),
        (  # 7 = round oak
            [
                Vector([0.005, 0, 0]),
                Vector([0.005, 0, 0.1]),
                Vector([0.11, 0, 0.16]),
                Vector([0.11, 0, 0.2]),
                Vector([0.22, 0, 0.26]),
                Vector([0.23, 0, 0.32]),
                Vector([0.15, 0, 0.34]),
                Vector([0.25, 0, 0.45]),
                Vector([0.23, 0, 0.53]),
                Vector([0.16, 0, 0.5]),
                Vector([0.23, 0, 0.64]),
                Vector([0.2, 0, 0.72]),
                Vector([0.11, 0, 0.7]),
                Vector([0.16, 0, 0.83]),
                Vector([0.12, 0, 0.87]),
                Vector([0.06, 0, 0.85]),
                Vector([0.07, 0, 0.95]),
                Vector([0, 0, 1]),
                Vector([-0.07, 0, 0.95]),
                Vector([-0.06, 0, 0.85]),
                Vector([-0.12, 0, 0.87]),
                Vector([-0.16, 0, 0.83]),
                Vector([-0.11, 0, 0.7]),
                Vector([-0.2, 0, 0.72]),
                Vector([-0.23, 0, 0.64]),
                Vector([-0.16, 0, 0.5]),
                Vector([-0.23, 0, 0.53]),
                Vector([-0.25, 0, 0.45]),
                Vector([-0.15, 0, 0.34]),
                Vector([-0.23, 0, 0.32]),
                Vector([-0.22, 0, 0.26]),
                Vector([-0.11, 0, 0.2]),
                Vector([-0.11, 0, 0.16]),
                Vector([-0.005, 0, 0.1]),
                Vector([-0.005, 0, 0]),
            ],
            [
                [0, 1, 33, 34],
                [1, 2, 3],
                [3, 4, 5, 6],
                [6, 7, 8, 9],
                [9, 10, 11, 12],
                [12, 13, 14, 15],
                [15, 16, 17],
                [1, 3, 6, 9, 12, 15, 17, 19, 22, 25, 28, 31, 33],
                [33, 32, 31],
                [31, 30, 29, 28],
                [28, 27, 26, 25],
                [25, 24, 23, 22],
                [22, 21, 20, 19],
                [19, 18, 17],
            ],
        ),
        (  # 8 = elliptic (default)
            [
                Vector([0.005, 0, 0]),
                Vector([0.005, 0, 0.1]),
                Vector([0.15, 0, 0.2]),
                Vector([0.25, 0, 0.45]),
                Vector([0.2, 0, 0.75]),
                Vector([0, 0, 1]),
                Vector([-0.2, 0, 0.75]),
                Vector([-0.25, 0, 0.45]),
                Vector([-0.15, 0, 0.2]),
                Vector([-0.005, 0, 0.1]),
                Vector([-0.005, 0, 0]),
            ],
            [[0, 1, 9, 10], [1, 2, 3, 4], [4, 5, 6], [6, 7, 8, 9], [4, 6, 9, 1]],
        ),
        (  # 9 = rectangle
            [
                Vector([-0.5, 0, 0]),
                Vector([-0.5, 0, 1]),
                Vector([0.5, 0, 1]),
                Vector([0.5, 0, 0]),
            ],
            [[0, 1, 2, 3]],
            [(0, 0), (0, 1), (1, 1), (1, 0)],
        ),
        (  # 10 = triangle
            [Vector([-0.5, 0, 0]), Vector([0, 0, 1]), Vector([0.5, 0, 0])],
            [[0, 1, 2]],
            [(0, 0), (0.5, 1), (1, 0)],
        ),
    ][t]


class TreePanel(bpy.types.Panel):
    bl_label = "Tree Generator"
    bl_idname = "OBJECT_PT_Tree"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tree Generator"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        mytool = scene.my_tool
        
        row = layout.row()
        row.label(text="Tree Parameters")
        box = layout.box()
        box.prop(mytool, "n_iter")
        row = box.row()
        row.prop(mytool, "tropism")
        box.prop(mytool, "tropism_scale")
        box.prop(mytool, "seed")
        
        row = layout.row()
        row.label(text="Leaf Parameters:")
        box = layout.box()
        box.prop(mytool, "leaf_type")
        box.prop(mytool, "leaf_bend")
        box.prop(mytool, "leaf_scale")
        box.prop(mytool, "leaf_branch_angle")
        
        row = layout.row()
        row.label(text="Branch Parameters")
        box = layout.box()
        box.prop(mytool, "branch_length")
        box.prop(mytool, "branch_length_scale")
        box.prop(mytool, "branch_thickness")
        box.prop(mytool, "branch_angle")
        
        layout.operator(TreeGen.bl_idname)


### ==== BEGIN BOIDS STUFF ==== ###

class Boid:
    STATE_FLOCKING = "flocking"
    STATE_SEEKING = "seeking"
    STATE_WAITING = "waiting"
    
    def __init__(self, name, p, v):
        self.name = name
        self.state = Boid.STATE_FLOCKING
        self.seeking_dest = None
        
        self.p = p # position
        self.v = v # velocity vector
        self.history = [] # array of (state, p, v)
        self.history.append( (self.state, self.p.copy(), self.v.copy()) )        

    def draw(self, params):
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
        
        # add wings
        right_wing = gen_right_wing()
        right_verts = right_wing[0]
        right_faces = right_wing[1]
        mesh = bpy.data.meshes.new(name="Wing")
        mesh.from_pydata(right_verts, [], right_faces) 
        rwing_obj = bpy.data.objects.new(self.name+"_RWing", mesh)
        bpy.context.scene.collection.objects.link(rwing_obj)
        bpy.context.view_layer.objects.active = rwing_obj
        rwing_obj.parent = obj
        rwing_obj.location = Vector((0.0, -0.34154030680656433, 0.31113627552986145))
        rwing_obj.scale = Vector((3, 1, 3))
        rwing_obj.rotation_euler = Euler((-0.46983131766319275, -0.0, 0.0), 'XYZ')
        rwing_obj.rotation_mode = "ZXY"
        
        left_wing = gen_left_wing()
        left_verts = left_wing[0]
        left_faces = left_wing[1]
        mesh = bpy.data.meshes.new(name="Wing")
        mesh.from_pydata(left_verts, [], left_faces) 
        lwing_obj = bpy.data.objects.new(self.name+"_LWing", mesh)
        bpy.context.scene.collection.objects.link(lwing_obj)
        bpy.context.view_layer.objects.active = lwing_obj
        lwing_obj.parent = obj
        lwing_obj.location = Vector((0.0, -0.34154030680656433, 0.31113627552986145))
        lwing_obj.scale = Vector((3, 1, 3))
        lwing_obj.rotation_euler = Euler((-0.46983131766319275, -0.0, 0.0), 'XYZ')
        lwing_obj.rotation_mode = "ZXY"

        for i, (state, p, v) in enumerate(self.history):
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
            
            base_mat = Matrix.Rotation(pi/2, 4, "Y") @ Matrix.Rotation(-pi/2, 4, "Z")
            base_mat = base_mat.to_3x3()
            mat = mat @ base_mat
            
            quat = mat.to_quaternion()
            obj.rotation_quaternion = quat
            obj.keyframe_insert(data_path="rotation_quaternion", frame=t)
        
        
        # animate wings
        z_rotation = 0
        rotation_step = 1.5
        direction = 1
        for t in range(0, params['animation_length'], 5):
            
            if (z_rotation >= 0):
                direction = -1
            elif (z_rotation <= -1.25):
                direction = 1
        
            z_rotation += (rotation_step * direction)
            rwing_obj.rotation_euler.z = z_rotation
            lwing_obj.rotation_euler.z = -z_rotation
            lwing_obj.keyframe_insert(data_path="rotation_euler", frame=t)
            rwing_obj.keyframe_insert(data_path="rotation_euler", frame=t)

def boids_init(params):
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
def boids_fly_towards_center(boids, params):
    factor = 0.05 * params['fly_towards_center']
    
    for ix in range(len(boids)):
        if boids[ix].state is Boid.STATE_FLOCKING:
            center = Vector([0,0,0])
            n_neighbors = 0
            
            for neighbor in boids_get_neighbors(boids, ix, params['visual_range']):
                center += neighbor.p
                n_neighbors += 1
            
            if n_neighbors:
                center = center / n_neighbors
                boids[ix].v += (center - boids[ix].p) * factor

# make boids avoid others that are too close. modifies boids[ix].v
def boids_avoid_collisions(boids, params):
    factor = 0.05 * params['avoid_collisions']
    dv = Vector([0,0,0])
    
    for ix in range(len(boids)):
        if boids[ix].state is Boid.STATE_FLOCKING:
            for neighbor in boids_get_neighbors(boids, ix, params['collision_radius']):
                dv += (boids[ix].p - neighbor.p)
            boids[ix].v += dv * factor

# make boids match velocity of neighbors. modifies boids[ix].v
def boids_match_velocity(boids, params):
    factor = 0.05 * params['match_velocity']
    
    for ix in range(len(boids)):
        if boids[ix].state is Boid.STATE_FLOCKING:
            avg_v = Vector([0,0,0])
            n_neighbors = 0
            
            for neighbor in boids_get_neighbors(boids, ix, params['visual_range']):
                avg_v += neighbor.v
                n_neighbors += 1
            
            if n_neighbors:
                avg_v = avg_v / n_neighbors
                boids[ix].v += (avg_v - boids[ix].v) * factor

# limit boids speed
def boids_limit_speed(boids, params):
    for boid in boids:
        s_sq = boid.v.length_squared
        if s_sq > params['max_speed']**2:
            boid.v.normalize()
            boid.v = boid.v * params['max_speed']
            print("limit speed")


# keep boids in territory
def boids_stay_in_territory(boids, params):
    factor = 1.0 * params['stay_in_territory'] * params['max_speed']/10
    r = params['territory_radius']
    margin = 5
    r -= margin
    
    for boid in boids:
        if boid.state is Boid.STATE_FLOCKING:
            
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

def create_boids(params):
    x = SCENE_SIZE/2 - 10
    beehive_pos = [
        Vector((x, x, 0)),
        Vector((x, -x, 0)),
        Vector((-x, x, 0)),
        Vector((-x, -x, 0))
    ]
         
    boids = boids_init(params)

    for i in range(0, params['animation_length'], params['animation_step']):
        # print("=== STEP {}".format(i))
        boids_fly_towards_center(boids, params)
        boids_avoid_collisions(boids, params)
        boids_match_velocity(boids, params)
        boids_limit_speed(boids, params)
        boids_stay_in_territory(boids, params)
        
        # state transitions
        for boid in boids:
            if boid.state is Boid.STATE_FLOCKING and random.random() < .05:
                # print("Boid {} is now seeking".format(boid.name))
                # make it go to a beehive
                boid.state = Boid.STATE_SEEKING
                dest = random.choice(beehive_pos).copy()
                new_v = dest - boid.p
                new_v.normalize()
                boid.v = new_v * boid.v.length
                boid.seeking_dest = dest
            elif boid.state is Boid.STATE_WAITING and random.random() < 0.10:
                # print("Boid {} is now flocking".format(boid.name))
                boid.state = Boid.STATE_FLOCKING
                boid.seeking_dest = None
                s = params['max_speed'] * 0.25
                boid.v = Vector(random.uniform(-s, s) for _ in range(3))
                
            elif boid.state is Boid.STATE_SEEKING:
                new_v = boid.seeking_dest - boid.p
                new_v.normalize()
                boid.v = new_v * boid.v.length
                
                d2 = (boid.p - boid.seeking_dest).length_squared
                if d2 < boid.v.length_squared:
                    # print("Boid {} is now waiting".format(boid.name))
                    boid.state = Boid.STATE_WAITING
                    boid.p = boid.seeking_dest
            
            # save new pos    
            if boid.state is not Boid.STATE_WAITING:
                boid.p += boid.v
                
            boid.p.z = max(boid.p.z, 0)
            boid.history.append( (boid.state, boid.p.copy(), boid.v.copy()) )
    
    print("Pathing boids done")
    for boid in boids:
        boid.draw(params)

### === MAIN PANEL === ### 
    
class TreeGen(bpy.types.Operator):
    bl_idname = "object.tree_gen"
    bl_category = "Tree Generator"
    bl_label = "Generate Tree"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
        print("Growing grass....")
        Field.draw()
        
        print("Planting flowers.....")
        
        mytool = context.scene.my_tool
        params = {
            'n_iter' : mytool.n_iter, # number of iterations
            'length' : mytool.branch_length, # scales lengths of all branches
            'length_scale' : mytool.branch_length_scale, # scales lengths of lower-order branches relative to higher-order ones
            'thickness' : mytool.branch_thickness, # scales thicknesses of all branches
            # thickness_scale is not paramaterized since it depends on branching rules
            'branch_angle' : mytool.branch_angle, # branching angle, in degrees
            'leaf_angle' : mytool.leaf_branch_angle, # Angle between leaf and branch
            'leaf_scale' : mytool.leaf_scale, # Scaling factor for leaf
            'leaf_bend' : mytool.leaf_bend, # Bend angle for leaf
            'leaf_type': int(mytool.leaf_type) - 1, # leaf type
            'tropism' : mytool.tropism, # direction to bend branches towards
            'tropism_scale' : mytool.tropism_scale, # strength of bending force
            'seed' : mytool.seed # random seed
        }
        
        axiom = LSystem.parse_lstring("!({thickness})F({length2})A".format(**params, length2=params['length']*2))

        rules = {
            "A" : LSystem.parse_lstring(
                "!({th})?F({length})[&({branch_angle})F({length})A]/(94)[&({branch_angle})F({length})A]/(132.63)[&({branch_angle})F({length})A]".format(**params, th=params['thickness']*1.73)),
            "F" : [lambda F: LNode("F", F.params[0] * params['length_scale'])],
            "!" : [lambda n: LNode("!", n.params[0] * 1.7)]
        }
        lstring = LSystem.generate_lstring(axiom, rules, params['n_iter'])
        
        # second pass--add leaves
        leaf_rules = {
            "A" : LSystem.parse_lstring("?[&({leaf_angle})L]/(120)[&({leaf_angle})L]/(120)[&({leaf_angle})L]".format(**params))
        }
        lstring = LSystem.generate_lstring(lstring, leaf_rules, 1)
        
        random.seed(params['seed'])
        flower_locations = []
        for num_flowers in range(100):
            pos = Vector([random.randrange(-SCENE_SIZE/2, SCENE_SIZE/2), random.randrange(-SCENE_SIZE/2, SCENE_SIZE/2), 0])
            LSystem.draw_lstring(lstring, pos, **params) 
            flower_locations.append(pos)
            
        print("Hatching bees...")
        boid_params = {
            # paramaterize these
            'count' : 50,               # number of boids
            'visual_range' : 7.5,       # radius of vision for each boid
            'collision_radius' : 2.0,   # collision radius
            'fly_towards_center' : 1.0, # weights for boid behavior rules
            'avoid_collisions' : 1.0,
            'match_velocity' : 1.0,
            'stay_in_territory' : 1.0,
            'seed' : 123456,            # Random seed

            # dont paramaterize these
            'animation_step' : 5,
            'animation_length' : 300 * 5,
            'max_speed': 35.0,
            'territory_center' : Vector([0,0,10]),
            'territory_radius' : 40,
        }
        
        create_boids(params=boid_params)
        
        print("Done!")
        return {'FINISHED'}

classes = [TreeProperties, TreePanel, TreeGen, Leaf, Branch]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        bpy.types.Scene.my_tool = bpy.props.PointerProperty(type=TreeProperties)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
        del bpy.types.Scene.my_tool

if __name__ == "__main__":
    register()

