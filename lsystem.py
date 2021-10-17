'''

Sources:
https://github.com/abiusx/L3D (to quickly test generated strings)
The Algorithmic Beauty of Plants, ch 1-2

'''

import bpy
from mathutils import Vector, Matrix
from math import *

# from https://blender.stackexchange.com/questions/6173/where-does-console-output-go
def bprint(*data):
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'CONSOLE':
                override = {'window': window, 'screen': screen, 'area': area}
                bpy.ops.console.scrollback_append(override, text=' '.join(str(x) for x in data), type="OUTPUT")  


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
    

class Turtle:
    def __init__(self):
        self.pos = Vector([0, 0, 0])
        self.h = Vector([0, 0, 1]) # heading, starts directly up
        self.l = Vector([-1, 0, 0]) # direction left, towards negative x
        self.u = Vector([0, -1, 0]) # direction up, towards negative y
        self.thickness = 0.05
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
        self.l = self.v.cross(h)
        self.l.normalize()
        self.u = self.h.cross(self.l)
        
    def draw(self, dist):
        end = self.pos + dist * self.h
        draw_cylinder_between(self.pos, end, self.thickness)
        self.pos = end
        
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


def draw_lstring(lstring):
    turtle = Turtle()
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
        elif l == '!':
            turtle.thickness = params[0]
    
    

def execute(context):
    axiom = parse_lstring("!(.01)F(1)/(45)A")
    rules = {
        "A" : parse_lstring("!(.01732)/(45)F(.5)[&(19)F(.50)A]/(94)[&(19)F(.50)A]/(132.63)[&(19)F(.50)A]"),
        "F" : [lambda F: LNode("F", F.params[0] * 1.1)],
        "!" : [lambda n: LNode("!", n.params[0] * 1.7)]
    }
    
    lstring = generate_lstring(axiom, rules, 2)
    # bprint(lstring_to_str(lstring))
    draw_lstring(lstring)

    
    return {'FINISHED'}


execute(bpy.context)











	