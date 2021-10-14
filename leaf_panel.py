import bpy

class LeafPanel(bpy.types.Panel):
    bl_label = "Leaf"
    bl_idname = "PT_Leaf"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Leaf Generator"
    
    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text = "Add a Leaf")
    