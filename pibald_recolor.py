bl_info = {
    "name": "Pibald Recolors",
    "author": "Antler Shed",
    "version": (1, 0),
    "blender": (4, 0, 1),
    "location": "View3D > N Panel > Recolors",
    "description": "Adds custom properties to meshes that describe color palettes as well as supporting ui elements in the Vertex Paint tab.",
    "warning": "",
    "doc_url": "",
    "category": "Paint",
}

import bpy
import time
from bpy.types import (
    Context,
    Mesh,
    Operator,
    Menu,
    Panel,
    PropertyGroup,
)
from bpy.props import (
    BoolProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty,
    PointerProperty,
    CollectionProperty,
)

PALETTE_ATTR_NAME = 'PaletteId'
'''
Color update time interval. 
necessary because this uses blender's prop layout for updating colors
by default these property changes do not push an undo history state
forcing it do so on update would push an undo step for every incremental change to colors when dragging it around in the gui
so this hack prevents a million updates from getting pushed by enforcing a minimum time interval between color changes before undo states are created
'''
MIN_UNDO_TIME = 1.5

'''
Refresh Colors
'''

def apply_recolor(mesh: Mesh, color_index):
    color_props = mesh.recolor_props
    if mesh.color_attributes.active_color and PALETTE_ATTR_NAME in mesh.attributes:
        palette_data = mesh.attributes[PALETTE_ATTR_NAME].data
        for dex in range( len( palette_data ) ):
            #col will just be a float tuple of length 4 on the interval [0,1], RGBA format
            palette_id = palette_data[dex].value
            if color_index is None or palette_id == color_index and len(color_props.recolors[color_props.active_palette].colors) > 0:
                mesh.color_attributes.active_color.data[dex].color = color_props.get_color(palette_id) + (1.0,)
              
'''
Palette Selection
'''

class RECOLOR_OT_set_active_palette(Operator):
    
    bl_idname = "recolor.set_active_palette"
    bl_label = ""
    bl_description = "Sets the active recolor palette index and updates the vertex colors of all objects with pallete id attribute to match the active palette"
    bl_options = {'UNDO'}
    
    index : IntProperty(
        name="",
        description="Index of the palette to be activated.",
        min=0,
        default=0
    )
    
    @classmethod
    def poll( self, context: Context ):
        return context.vertex_paint_object and context.object.type == 'MESH'
    
    def execute( self, context ):
        color_props = bpy.context.object.data.recolor_props
        color_props.set_active_palette(self.index)
        return {'FINISHED'}

'''
Palette Addition
'''

class RECOLOR_OT_add_palette(Operator):
    
    bl_idname = "recolor.add_palette"
    bl_label = ""
    bl_description = "Adds a copy of the basis palette as a new recolor palette"
    bl_options = {'UNDO'}
    
    @classmethod
    def poll( self, context: Context ):
        return context.vertex_paint_object and context.object.type == 'MESH'
    
    def execute( self, context ):
        color_props = bpy.context.object.data.recolor_props
        color_props.add_palette()
        return {'FINISHED'}

'''
Palette Removal
'''

class RECOLOR_OT_remove_palette( Operator ):
    
    bl_idname = "recolor.remove_palette"
    bl_label = ""
    bl_description = "Removes the active recolor palette"
    bl_options = {'UNDO'}
    
    @classmethod
    def poll( self, context: Context ):
        return context.vertex_paint_object and context.object.type == 'MESH'
    
    def execute( self, context ):
        color_props = bpy.context.object.data.recolor_props
        color_props.remove_palette(context)
        return {'FINISHED'}
        
'''
Get basis palette from primary vertex colors
'''

class RECOLOR_OT_setup_basis_palette( Operator ):
    
    bl_idname = "recolor.setup_basis"
    bl_label = ""
    bl_description = "Builds a basis palette from the vertex colors used in the current mesh"
    bl_options = {'UNDO'}
    
    def get_index_of_nearest_color(self, colors, test):
        nearest_index = 0
        nearest = 3
        for dex in range(len(colors)):
            diff = abs(colors[dex][0] - test[0]) + abs(colors[dex][1] - test[1]) + abs(colors[dex][2] - test[2])
            if abs(colors[dex][0] - test[0]) + abs(colors[dex][1] - test[1]) + abs(colors[dex][2] - test[2]) < nearest:
                nearest = diff
                nearest_index = dex
        return nearest_index
        
    @classmethod
    def poll( self, context: Context ):
        return context.vertex_paint_object and context.object.type == 'MESH'
    
    def execute(self, context):
        color_props = bpy.context.object.data.recolor_props
        basis_palette = color_props.get_basis_colors()
        new_colors = []
        
        mesh = context.object.data
        #Nab a color palette from existing things.
        
        if mesh.color_attributes.active_color and mesh.recolor_props.active_palette == 0:
            color_data = mesh.color_attributes.active_color.data
            if PALETTE_ATTR_NAME not in mesh.attributes:
                mesh.attributes.new( PALETTE_ATTR_NAME, 'INT8', 'CORNER' )
                for item in mesh.attributes[PALETTE_ATTR_NAME].data:
                    item.value = -1
            for dex in range( len( color_data ) ):
                #col will just be a float tuple of length 4 on the interval [0,1], RGBA format
                col = tuple( color_data[dex].color )[:3]
                in_palette = False
                for basis_color in basis_palette:
                     in_palette = in_palette or (abs(basis_color[0] - col[0]) < 0.0039 and abs(basis_color[1] - col[1]) < 0.0039 and abs(basis_color[2] - col[2]) < 0.0039)
                     if in_palette:
                         break
                if not in_palette:
                    color_props.update_active = False
                    color_props.add_basis_color( col )
                    color_props.update_active = True
                    basis_palette = color_props.get_basis_colors()
                mesh.attributes[PALETTE_ATTR_NAME].data[dex].value = self.get_index_of_nearest_color(basis_palette, col )
            i = 0
            while i < len(color_props.get_basis_colors()):
                if not any([dex.value == i for dex in mesh.attributes[PALETTE_ATTR_NAME].data ]):
                    color_props.update_active = False
                    color_props.remove_basis_color( mesh, i )
                    color_props.update_active = True
                else:
                    i += 1
                
        
        return {'FINISHED'}

"""Class for colors CollectionProperty"""
class RECOLOR_Color(PropertyGroup):

    def update_color(self, context):
        if (time.monotonic() - self.last_push_time) > MIN_UNDO_TIME:
            bpy.ops.ed.undo_push()
        self['last_push_time'] = time.monotonic()
        color_props = context.object.data.recolor_props
        for palette in color_props.recolors:
            if self in palette.colors.values() and color_props.update_active:
                apply_recolor( context.object.data, palette.colors.values().index( self ) )
    
    last_push_time: FloatProperty(
        default=0.0
    )
    
    color: FloatVectorProperty(
        name="",
        description="",
        default=(0.0, 0.0, 0.0),
        min=0, max=1,
        subtype='COLOR',
        size=3,
        update=update_color,
    )

"""Class for colors CollectionProperty"""
class RECOLOR_Label(PropertyGroup):
    
    def update_label(self, context):
        bpy.ops.ed.undo_push()
    
    label: StringProperty(
        name="",
        description="",
        default="Color",
        update=update_label,
    )

class RECOLOR_Palette(PropertyGroup):

    
    palette_name: StringProperty(
        name="",
        default="Untitled Palette",
    )
    
    colors: CollectionProperty(
        type=RECOLOR_Color
    )

class RECOLOR_Properties(PropertyGroup):
    
    def get_color(self, index):
        if self.active_palette < len(self.recolors) and index < len(self.recolors[self.active_palette].colors):
            return tuple( self.recolors[self.active_palette].colors[index].color )
        else:
            return None
    
    def set_color(self, index, color):
        self.recolors[self.active_palette].colors[index] = color
    
    def set_active_palette(self, index):
        self.active_palette = max( min( index, len( self.recolors ) - 1 ), 0 )
        
    def add_palette(self):
        new_palette = self.recolors.add()
        for basis_color in self.recolors[0].colors:
            new_color = new_palette.colors.add()
            new_color.color = basis_color.color
    
    def remove_palette(self, context):
        #disallow removal of the basis palette
        if self.active_palette != 0:
            self.recolors.remove(self.active_palette)
            if self.active_palette >= len(self.recolors):
                self.set_active_palette(len( self.recolors ) - 1 )
            else:
                apply_recolor(context.object.data, None)
            
    def get_basis_colors(self):
        return [tuple(color.color) for color in self.recolors[0].colors]
    
    def add_basis_color(self, color):
        for palette in self.recolors:
            new_color = palette.colors.add()
            new_color.color = color
        self.labels.add()
    
    def remove_basis_color(self, mesh, index):
        palette_data = mesh.attributes[PALETTE_ATTR_NAME].data
        for i in range(len(palette_data)):
            if palette_data[i].value > index:
                palette_data[i].value = palette_data[i].value - 1
        for palette in self.recolors:
            palette.colors.remove(index)
        self.labels.remove(index)
    
    def on_active_palette_update(self, context):
        apply_recolor(context.object.data, None)
        while len(self.recolors[0].colors) > len(self.labels):
            self.labels.add()
        while len(self.recolors[0].colors) < len(self.labels):
            self.labels.remove(len(self.labels)-1)
    
    size: IntProperty(
        name="Size",
        description="Number of colors in the base palette and all recolor palettes",
        min=-1,
        default=0
    )
    
    active_palette: IntProperty(
        name="Active Palette",
        description="Selected Palette Index",
        min=-1,
        default=-1,
        update=on_active_palette_update
    )
    
    update_active: BoolProperty(
        name="Update Active",
        description="Flag for controlling updates because Blender puts its callbacks in the data objects instead of the UI",
        default=True
    )
    
    recolors: CollectionProperty(
        type=RECOLOR_Palette
    )
    
    labels: CollectionProperty(
        type=RECOLOR_Label
    )


class VIEW3D_UL_recolor_element(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        
        #get properties
        color_props = data
        item_index = color_props.recolors.values().index(item)
        
        row = layout.row(align=True)
            
        #setup active palette button
        col = row.column( align = True )
        props = col.operator("recolor.set_active_palette", text="", icon= 'RADIOBUT_ON' if color_props.active_palette == item_index else 'RADIOBUT_OFF')
        props.index = item_index
        
        
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            col = row.column( align = True )
            if item_index == 0:
                col.label(text = "Basis")
            else:
                col.prop(color_props.recolors[item_index], "palette_name")
            if color_props.active_palette == item_index:
                for index, color in enumerate(color_props.recolors[item_index].colors):
                    col_row = col.row( align = True )
                    if len(color_props.labels) > index:
                        col_row.prop(color_props.labels[index], "label")
                    else:
                        col_row.label(text = "--")
                    col_row.prop(color, "color", event=True, toggle=True)
            
            

class VIEW3D_PT_recolor_palette(Panel):
    bl_label = "Model Recolors"
    bl_options = {'DEFAULT_CLOSED'}
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Recolors'

    @classmethod
    def poll( self, context: Context ):
        return context.vertex_paint_object and context.object.type == 'MESH'
    
    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator("recolor.add_palette", text="", icon='ADD')
        row.operator("recolor.remove_palette", text="", icon='REMOVE')
        color_props = context.object.data.recolor_props
        if color_props.active_palette == 0:
            row.operator("recolor.setup_basis", text="", icon='FILE_REFRESH')
        row = layout.row(align = True)
        layout.template_list("VIEW3D_UL_recolor_element", "", color_props, "recolors", color_props, "active_palette")
        
        
        

classes = (
    RECOLOR_Color,
    RECOLOR_Label,
    RECOLOR_Palette,
    RECOLOR_Properties,
    RECOLOR_OT_add_palette,
    RECOLOR_OT_remove_palette,
    RECOLOR_OT_set_active_palette,
    RECOLOR_OT_setup_basis_palette,
    VIEW3D_UL_recolor_element,
    VIEW3D_PT_recolor_palette,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Mesh.recolor_props = PointerProperty(
        type=RECOLOR_Properties,
        name="Recolor Properties",
        description="Global properties required by the Recolor plugin"
    )
    

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Mesh.recolor_props
