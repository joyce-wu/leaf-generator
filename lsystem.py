'''

Sources:
https://github.com/abiusx/L3D (to quickly test generated strings)
The Algorithmic Beauty of Plants, ch 1-2

'''

import bpy
from mathutils import Vector, Matrix
from math import *
import random

# from https://blender.stackexchange.com/questions/6173/where-does-console-output-go
def bprint(*data):
    print(*data)
#    for window in bpy.context.window_manager.windows:
#        screen = window.screen
#        for area in screen.areas:
#            if area.type == 'CONSOLE':
#                override = {'window': window, 'screen': screen, 'area': area}
#                bpy.ops.console.scrollback_append(override, text=' '.join(str(x) for x in data), type="OUTPUT")  


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


# from https://blender.stackexchange.com/questions/5898/how-can-i-create-a-cylinder-linking-two-points-with-python
def draw_cylinder_between(p1, p2, radius):
    bpy.ops.curve.primitive_bezier_curve_add()
    obj = bpy.context.object
    obj.data.dimensions = '3D'
    obj.data.fill_mode = 'FULL'
    obj.data.bevel_depth = radius
    obj.data.bevel_resolution = 4

    obj.data.splines[0].bezier_points[0].co = p1
    obj.data.splines[0].bezier_points[0].handle_left_type = 'VECTOR'
    obj.data.splines[0].bezier_points[0].handle_right_type = 'VECTOR'

    obj.data.splines[0].bezier_points[1].co = p2
    obj.data.splines[0].bezier_points[1].handle_left_type = 'VECTOR'
    obj.data.splines[0].bezier_points[1].handle_right_type = 'VECTOR'

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
    
    modifier = obj.modifiers.new(name='Bend', type='SIMPLE_DEFORM')
    modifier.deform_method = 'BEND'
    modifier.deform_axis = 'X'
    modifier.angle = bend_angle
    
    obj.location = location + bpy.context.scene.cursor.location
    obj.rotation_euler = direction
    

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
        draw_cylinder_between(self.pos, end, self.thickness)
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
        
        gen_leaf(self.params['leaf_type'], self.params['leaf_scale'], self.pos, euler, self.params['leaf_bend'])
        
        
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
    
    

def execute(context):
    # todo: make these inputs
    params = {
        'n_iter' : 4, # number of iterations
        'length' : 0.5, # scales lengths of all branches
        'length_scale' : 1.1, # scales lengths of lower-order branches relative to higher-order ones
        'thickness' : 0.01, # scales thicknesses of all branches
        # thickness_scale is not paramaterized since it depends on branching rules
        'branch_angle' : 19, # branching angle, in degrees
        'leaf_angle' : 41, # Angle between leaf and branch
        'leaf_scale' : 0.8, # Scaling factor for leaf
        'leaf_bend' : 0, # Bend angle for leaf
        'leaf_type': 3, # leaf type
        'tropism' : Vector([0, 0, -1]), # direction to bend branches towards
        'tropism_scale' : 0.22, # strength of bending force
        'seed' : 6 # random seed
    }

#    params = {
#        'n_iter' : 5, # number of iterations
#        'length' : 0.5, # scales lengths of all branches
#        'length_scale' : 1.07, # scales lengths of lower-order branches relative to higher-order ones
#        'thickness' : 0.01, # scales thicknesses of all branches
#        # thickness_scale is not paramaterized since it depends on branching rules
#        'branch_angle' : 55, # branching angle, in degrees
#        'tropism' : Vector([-0.61, -0.19, 0.77]), # direction to bend branches towards
#        'tropism_scale' : 0.40, # strength of bending force
#        'seed' : 3 # random seed
#    }

#    params = {
#        'n_iter' : 3,
#        'length' : 0.5, # scales lengths of all branches
#        'length_scale' : 1.05, # scales lengths of lower-order branches relative to higher-order ones
#        'thickness' : 0.01, # scales thicknesses of all branches
#        # thickness_scale is not paramaterized since it depends on branching rules
#        'branch_angle' : 40, # branching angle, in degrees
#        'tropism' : Vector([-.4, 0, -1]), # direction to bend branches towards
#        'tropism_scale' : 0.3, # strength of bending force
#        'seed' : 30 # random seed
#    }

    axiom = parse_lstring("!({thickness})F({length2})A".format(**params, length2=params['length']*2))
    
    rules = {
        "A" : parse_lstring(
            "!({th})?F({length})[&({branch_angle})F({length})A]/(94)[&({branch_angle})F({length})A]/(132.63)[&({branch_angle})F({length})A]".format(**params, th=params['thickness']*1.73)),
        "F" : [lambda F: LNode("F", F.params[0] * params['length_scale'])],
        "!" : [lambda n: LNode("!", n.params[0] * 1.7)]
    }
#    axiom = parse_lstring("!(.01)F(1)/(45)A")
#    rules = {
#        "A" : parse_lstring("!(.01732)/(45)F(.5)[&(19)F(.50)A]/(94)[&(19)F(.50)A]/(132.63)[&(19)F(.50)A]"),
#        "F" : [lambda F: LNode("F", F.params[0] * 1.1)],
#        "!" : [lambda n: LNode("!", n.params[0] * 1.7)]
#    }
    
    lstring = generate_lstring(axiom, rules, params['n_iter'])
    
    
    # second pass--add leaves
    leaf_rules = {
        "A" : parse_lstring("?[&({leaf_angle})L]/(120)[&({leaf_angle})L]/(120)[&({leaf_angle})L]".format(**params))
    }
    lstring = generate_lstring(lstring, leaf_rules, 1)
    
    
    random.seed(params['seed'])
    draw_lstring(lstring, **params)
    
    # gen_leaf(leaf_type, scale, location, euler, bend_angle)
    # gen_leaf(3, 0.3, (0,0,0), (0,0,0), 0)

    
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


execute(bpy.context)

