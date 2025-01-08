

import bpy
import mathutils
import time

from bpy.props import EnumProperty, StringProperty

baked_texture_index = 0

# Оператор для выполнения действия
class RenderSette(bpy.types.Operator):
    bl_idname = "object.rendersett"
    bl_label = "Bake it simple!"
    
    def execute(self,context):
        global baked_texture_index
        bpy.context.scene.render.engine = 'CYCLES'
        #выставление настроек рендера
        cyc_sett = bpy.data.scenes["Scene"].cycles
        cyc_sett.device = "GPU"
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = 10
        cyc_sett.bake_type = 'DIFFUSE'
        bpy.data.scenes["Scene"].render.bake.use_pass_direct = False
        bpy.data.scenes["Scene"].render.bake.use_pass_indirect = False
        #настройка материала
        cur_obj = context.active_object#находим выбранный объект
        node_tree = context.active_object.active_material.node_tree#лезем в новы
        nodes = node_tree.nodes#и в дерево
        bake_resolution = int(context.active_object.simple_bake_resolution) #разрешение для запекания
        print(context.active_object.simple_bake_resolution)
        bake_target_label = context.active_object.simple_bake_image_name
        baked_texture_index += 1

        if node_tree:
            # Ищем узел с указанным лейблом чтоб не создовать несколько
            found_node = None
            for node in node_tree.nodes:
                if node.label == bake_target_label:
                    found_node = node
                    node_tree.nodes.active = found_node
                    break
        if found_node:
            pass
        else:
            texture_image_my = nodes.new(type="ShaderNodeTexImage")#создаем  ноду картинки
            texture_image_my.label = bake_target_label
            bake_img = bpy.ops.image.new(name = bake_target_label, width=bake_resolution, height=bake_resolution)#создаем картинку
            bpy.ops.image.reload()
            bpy.data.images[bake_target_label].generated_width = bake_resolution
            bpy.data.images[bake_target_label].generated_height = bake_resolution

            texture_image_my.select = True#делаем выбранной
                
        if node_tree:
            # Ищем узел с указанным лейблом чтоб назначить картинку(в первом цикле все черные становятся)
            found_node = None
            for node in node_tree.nodes:
                if node.label == bake_target_label:
                    found_node = node
                    found_node.image = bpy.data.images[bake_target_label]
                    found_node.select = True
                    node_tree.nodes.active = found_node
                    break
        if found_node:
            pass
        time.sleep(1)
        bpy.ops.object.bake(type="DIFFUSE",use_clear= True)
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
        #layout.prop(bpy.data.scenes["Scene"], 'name', text='Разрешение')
        row = layout.row()
        row.prop(context.active_object, 'simple_bake_resolution', text='Resolution')
        row = layout.row()
        row.prop(context.active_object, 'simple_bake_image_name', text="Image name")
        
        # Добавление кнопки, которая вызывает наш оператор
        layout.operator("object.rendersett")

    

# Регистрация классов
def register():
    bpy.utils.register_class(RenderSette)
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
        default=None
    )

    bpy.types.Object.simple_bake_image_name = StringProperty(
        name = "Image name",
        default="BakedImage"
    )

    pass

def unregister():
    bpy.utils.unregister_class(RenderSette)
    bpy.utils.unregister_class(OBJECT_PT_CustomPanel)

    del bpy.types.Object.simple_bake_resolution
    del bpy.types.Object.simple_bake_image_name

    pass

if __name__ == "__main__":
    register()