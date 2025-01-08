

import bpy
import mathutils
import time
res = 1024
# Оператор для выполнения действия
class RenderSette(bpy.types.Operator):
    bl_idname = "object.rendersett"
    bl_label = "Set Simple bake settings"
    
    def execute(self,context):
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
        cur_obj = bpy.context.active_object#находим выбранный объект
        node_tree = bpy.context.active_object.active_material.node_tree#лезем в новы
        nodes = node_tree.nodes#и в дерево
        target_label = 'lbl'
        res = bpy.data.scenes["Scene"].render.resolution_x#разрешение для запекания

        if node_tree:
            # Ищем узел с указанным лейблом чтоб не создовать несколько
            found_node = None
            for node in node_tree.nodes:
                if node.label == target_label:
                    found_node = node
                    node_tree.nodes.active = found_node
                    break
        if found_node:
            pass
        else:
            texture_image_my = nodes.new(type="ShaderNodeTexImage")#создаем  ноду картинки
            texture_image_my.label = "lbl"
            bake_img = bpy.ops.image.new(name = "Bake",width=res,height=res)#создаем картинку
            bpy.ops.image.reload()
            bpy.data.images["Bake"].generated_width = res
            bpy.data.images["Bake"].generated_height = res

            texture_image_my.select = True#делаем выбранной
                
        if node_tree:
            # Ищем узел с указанным лейблом чтоб назначить картинку(в первом цикле все черные становятся)
            found_node = None
            for node in node_tree.nodes:
                if node.label == target_label:
                    found_node = node
                    found_node.image = bpy.data.images["Bake"]
                    found_node.select = True
                    node_tree.nodes.active = found_node
                    break
        if found_node:
            pass
        time.sleep(1)
        bpy.ops.object.bake(type="DIFFUSE",use_clear= True)
        print('hi')
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
        row.prop(bpy.data.scenes["Scene"].render,'resolution_x',text="Разрешение")
        # Добавление кнопки, которая вызывает наш оператор
        layout.operator("object.rendersett")

# Регистрация классов
def register():
    bpy.utils.register_class(RenderSette)
    bpy.utils.register_class(OBJECT_PT_CustomPanel)

def unregister():
    bpy.utils.unregister_class(RenderSette)
    bpy.utils.unregister_class(OBJECT_PT_CustomPanel)

if __name__ == "__main__":
    register()