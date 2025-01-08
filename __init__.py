

import bpy
import mathutils
import time
from bpy.props import EnumProperty, StringProperty
# Оператор для выполнения действия

class RenderSettBC(bpy.types.Operator):
    bl_idname = "object.rendersettbc"
    bl_label = "Simple Bake BC"
    
    def execute(self,context):
        bake_target_label = context.active_object.simple_bake_image_name
        bake_target_label_uv = bake_target_label + "_uv"
        cur_obj = context.active_object#находим выбранный объект
        #выставление настроек рендера
        cyc_sett = context.scene.cycles
        cyc_sett.device = "GPU"
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = 10
        cyc_sett.bake_type = 'DIFFUSE'
        context.scene.render.engine = 'CYCLES'
        context.scene.render.bake.use_pass_direct = False
        context.scene.render.bake.use_pass_indirect = False
        bake_resolution = int(context.active_object.simple_bake_resolution)
        found_image = False
        for image in bpy.data.images:
            if(image.name == bake_target_label):
                found_image = True
                break
        if(found_image == False):
            bake_img = bpy.ops.image.new(name = bake_target_label,width=bake_resolution,height=bake_resolution)#создаем картинку
        if(len(cur_obj.data.materials)>0):#если есть материал
            print('gotmat')
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    print('gotnode')
                    # Ищем узел с указанным лейблом чтоб не создовать несколько
                    found_node = None
                    found_node1 = None
                    for node in node_tree.nodes:
                        if node.label == bake_target_label:
                            print('gotAlready')
                            found_node = node
                            node_tree.nodes.active = found_node
                        if node.label == bake_target_label_uv:
                                found_node1 = node
                                found_node1.uv_map = cur_obj.data.uv_layers.active.name
                                break
                        else:
                            texture_image_my = nodes.new(type="ShaderNodeTexImage")#создаем  ноду картинки
                            print('createimagenode')
                            texture_image_my.label = bake_target_label

                            uv_map_node  = nodes.new(type="ShaderNodeUVMap")#создаем ноду юв
                            uv_map_node.label = bake_target_label_uv
                            uv_map_node.uv_map = cur_obj.data.uv_layers.active.name#выбираем юв
                            node_tree.links.new(uv_map_node.outputs['UV'],texture_image_my.inputs['Vector'])#соединяем юв и картинку
                            node_tree.nodes.active = texture_image_my#делаем активной
                            node_tree.nodes.active.image = bpy.data.images[bake_target_label]#ставим в выбранную картинку
                    
        bpy.ops.object.bake(type="DIFFUSE",use_clear= True)        
        return {'FINISHED'}


class RenderSettEmi(bpy.types.Operator):
    bl_idname = "object.rendersettemi"
    bl_label = "Simple Bake Emi"
    
    def execute(self,context):
        bake_target_label = context.active_object.simple_bake_image_name
        bake_target_label_uv = bake_target_label + "_uv"
        cur_obj = bpy.context.active_object#находим выбранный объект
        cyc_sett = bpy.data.scenes["Scene"].cycles
        cyc_sett.bake_type = 'EMIT'
        bake_resolution = int(context.active_object.simple_bake_resolution)
        found_image = False
        for image in bpy.data.images:
            if(image.name == bake_target_label):
                found_image = True
                break
        if(found_image == False):
            bake_img = bpy.ops.image.new(name = bake_target_label,width=bake_resolution,height=bake_resolution)#создаем картинку
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    # Ищем узел с указанным лейблом чтоб не создовать несколько
                    found_node = None
                    for node in node_tree.nodes:
                        if node.label == bake_target_label:
                            found_node = node
                            node_tree.nodes.active = found_node
                            break
                if found_node:
                    if node_tree:
                        # Ищем узел юв и переназначем юв если выбрана новая
                        found_node = None
                        for node in node_tree.nodes:
                            if node.label == bake_target_label_uv:
                                found_node1 = node
                                found_node1.uv_map = cur_obj.data.uv_layers.active.name
                                break
                    pass
                else:
                    texture_image_my = nodes.new(type="ShaderNodeTexImage")#создаем  ноду картинки
                    texture_image_my.label = bake_target_label

                    uv_map_node  = nodes.new(type="ShaderNodeUVMap")#создаем ноду юв
                    uv_map_node.label = bake_target_label_uv
                    uv_map_node.uv_map = cur_obj.data.uv_layers.active.name#выбираем юв

                    node_tree.links.new(uv_map_node.outputs['UV'],texture_image_my.inputs['Vector'])#соединяем юв и картинку
                    bake_resolution = int(context.active_object.simple_bake_resolution)
                    
                    node_tree.nodes.active = texture_image_my#делаем активной
                    node_tree.nodes.active.image = bpy.data.images[bake_target_label]#ставим в выбранную картинку    
                
        else:
            pass
        bpy.ops.object.bake(type="EMIT",use_clear= True) 
        return {'FINISHED'}

# Панель для добавления кнопки
class OBJECT_PT_CustomPanel(bpy.types.Panel):
    bl_label = "Set Render Settings For Bake"
    bl_idname = "OBJECT_PT_custom_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'  # Категория панели в N-сайдбаре

    def draw(self, context):
        layout = self.layout
        if context.active_object:
            #layout.prop(bpy.data.scenes["Scene"], 'name', text='Разрешение')
            row = layout.row()
            row.prop(context.active_object, 'simple_bake_resolution', text='Resolution', icon='OBJECT_HIDDEN')
            row = layout.row()
            row.prop(context.active_object, 'simple_bake_image_name', text="Image name", icon= 'NODE_TEXTURE')
            layout.prop(bpy.context.active_object.data.uv_layers,'active_index',text = "UV Map")
            layout.operator("object.rendersettbc", icon='RESTRICT_RENDER_OFF')
            layout.operator("object.rendersettemi", icon='RESTRICT_RENDER_OFF')
        else:
            row = layout.row()
            row.label(text = "No object selected")

# Регистрация классов
def register():
    bpy.utils.register_class(RenderSettEmi)
    bpy.utils.register_class(RenderSettBC)
    bpy.utils.register_class(OBJECT_PT_CustomPanel)

    bpy.types.Object.simple_bake_resolution = EnumProperty(
        name="Resolution",
        items=(
            ("128", "128x128", ""),
            ("256", "256x256", ""),
            ("512", "512x512", ""),
            ("1024", "1024x1024", ""),
            ("2048", "2048x2048", ""),
            ("4096", "4096x4096", ""),
            #TODO: Add more
        ),
        default="1024"
    )
    bpy.types.Object.simple_bake_image_name = StringProperty(
        name = "Bake Image Name",
        default="BakedImage"
    )

def unregister():
    bpy.utils.unregister_class(RenderSettEmi)
    bpy.utils.unregister_class(RenderSettBC)
    bpy.utils.unregister_class(OBJECT_PT_CustomPanel)
    del bpy.types.Object.simple_bake_resolution
    del bpy.types.Object.simple_bake_image_name

if __name__ == "__main__":
    register()