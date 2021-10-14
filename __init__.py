bl_info = {
    "name": "Leaf Generator",
    "category": "Object",
    "description": "Generate leaves with color variation",
    "author": "Lance Tan and Joyce Wu",
    "version": (0, 0, 1),
    'blender': (2, 80, 0)
}


import bpy


def register():
    bpy.utils.register_class(LeafPanel)


def unregister():
    bpy.utils.unregister_class(LeafPanel)


if __name__ == "__main__":
    register()