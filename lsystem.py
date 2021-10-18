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
from mathutils import Vector, Matrix
from math import *
import random

class TreeProperties(bpy.types.PropertyGroup):
    leaf_types = [('1', 'Ovate', 'Ovate'), ('2', 'Linear', 'Linear'), ('3', 'Cordate', 'Cordate'), ('4', 'Maple', 'Maple'), ('5', 'Palmate', 'Palmate'), ('6', 'Spiky Oak', 'Spiky Oak'), ('7', 'Rounded Oak', 'Rounded Oak'), ('8', 'Elliptic', 'Elliptic'), ('9', 'Rectangle', 'Rectangle'), ('10', 'Triangle', 'Triangle')]
    
    leaf_type : bpy.props.EnumProperty(name="Type", items=leaf_types)
    leaf_bend : bpy.props.FloatProperty(name="Bend", default=90, min=0, max=360)
    leaf_scale : bpy.props.FloatProperty(name="Scale", default=0.8)
    leaf_branch_angle : bpy.props.IntProperty(name="Leaf Branch Angle", default=41)
    branch_length : bpy.props.FloatProperty(name="Length", default=0.5, min=0.01)
    branch_length_scale : bpy.props.FloatProperty(name="Length Scale", default=1.1)
    branch_thickness : bpy.props.FloatProperty(name="Thickness", default=0.01)
    branch_angle : bpy.props.FloatProperty(name="Angle", default=19, min=0, max=360)
    n_iter : bpy.props.IntProperty(name="Level Count", default=4, min=1, max=5)
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
    
    def draw_lstring(lstring, **params):
        turtle = Turtle(**params)
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
    def __init__(self, tropism=None, tropism_scale=0, **params):
        # pushed to stack
        self.pos = Vector([0, 0, 0])
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
    
class TreeGen(bpy.types.Operator):
    bl_idname = "object.tree_gen"
    bl_category = "Tree Generator"
    bl_label = "Generate Tree"
    bl_options = {'REGISTER'}
    
    def execute(self, context):
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
        LSystem.draw_lstring(lstring, **params)  
        return {'FINISHED'}

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

