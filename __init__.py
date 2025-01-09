bl_info = {
    "name": "Simple Render Set-Up",
    "blender": (2, 80, 0),
    "category": "Object",
    "description":"N panel-Tool"
}

import bpy
import mathutils
import time
from bpy.props import EnumProperty, StringProperty

class RenderBC(bpy.types.Operator):#Метод для РЕНДЕРА цвета на плоскости
    bl_idname = "object.renderbc"
    bl_label = "Simple RENDER BC/N"

    def execute(self, context):
        rend_res_val = context.active_object.simple_bake_image_res
        context.scene.render.resolution_y= int(rend_res_val)
        context.scene.render.resolution_x= int(rend_res_val)
        if(context.scene.camera):#проверяем была ли уже камера на сцене
            old_cam = context.scene.camera
        else:
            old_cam = None
        mat = context.active_object.active_material#забираем материал с выбранного объекта
        bpy.ops.mesh.primitive_plane_add(location=[0,0,-12])#создаем плейн OFFSET FOR RENDER PLANE
        plane_obj = context.object
        context.active_object.data.materials.append(mat)
        bpy.ops.object.camera_add(location=[0,0,-9.2222],rotation=[0,0,0])#создаем камеру OFFSET FOR RENDER CAMERA
        camera_obj = context.object

        context.scene.camera = camera_obj
        context.scene.view_layers["ViewLayer"].use_pass_diffuse_color = True#включаем пасс цвета в слоях
        context.scene.view_layers["ViewLayer"].use_pass_normal = True# вкючаем пас нормала
        context.scene.use_nodes = True
        node_tree = context.scene.node_tree

        render_layers_node = None#объявление переменных для композитора
        render_viewer_nodeBC = None
        render_viewer_nodeN = None
        bpy.ops.render.render(animation= False,use_viewport= True)#рендерим и проверяем весь композитор
        node_tree.nodes.clear()#очищаем все ноды
        render_layers_node = node_tree.nodes.new(type='CompositorNodeRLayers')
        render_layers_node.name = 'Render Layers'#создаем ноду слоя
        render_viewer_nodeBC = node_tree.nodes.new(type='CompositorNodeViewer')
        render_viewer_nodeBC.label = 'ViewerBC'#и ноду вывода
        render_viewer_nodeN = node_tree.nodes.new(type='CompositorNodeViewer')
        render_viewer_nodeN.label = 'ViewerN'#и ноду вывода
        render_viewer_nodeBC.location = (300,0)#двигаем чтоб красиво было
        render_viewer_nodeN.location = (300,-200)#двигаем чтоб красиво было
        node_tree.links.new(render_layers_node.outputs['DiffCol'],render_viewer_nodeBC.inputs['Image'])#соединяем их
        node_tree.links.new(render_layers_node.outputs['Normal'],render_viewer_nodeN.inputs['Image'])#соединяем их
        bpy.data.objects.remove(plane_obj,do_unlink=True)#удаляем камеру и плейн
        bpy.data.objects.remove(camera_obj,do_unlink=True)
        if old_cam == None:#если на сцене была камера вертаем взад
            context.scene.camera = None
        else:
            context.scene.camera = old_cam
        workspaces = bpy.data.workspaces#уходим в композитор чтоб забрать цвет или нормал
        
        def on_workspace_changed(self, context):
            if context.window.workspace == workspaces.get("Compositing"):
                for area in bpy.context.screen.areas:
                    if area.type == 'DOPESHEET_EDITOR':
                        area.type = 'IMAGE_EDITOR'
                
            bpy.msgbus.clear_by_owner(self)
            pass
        
        bpy.msgbus.subscribe_rna(
            key = (bpy.types.Window, "workspace"),
            owner=self,
            notify=on_workspace_changed,
            args=(self, context)
        )
        
        #create_workspace_if_not_exist(self, context)
        context.window.workspace = workspaces.get("Compositing")
    
        return {'FINISHED'}

class RenderSettBC(bpy.types.Operator):##Запекание цвета
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
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    # Ищем узел с указанным лейблом чтоб не создовать несколько
                    found_node = None
                    found_node1 = None
                    for node in node_tree.nodes:
                        if node.label == bake_target_label:
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
                            break
        bpy.ops.object.bake(type="DIFFUSE",use_clear= True) 
########удаление использованного из материала
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    # Ищем узел с указанным лейблом чтоб не создовать несколько
                    found_node = None
                    found_node1 = None
                    for node in node_tree.nodes:
                        if node.label == bake_target_label:
                            found_node = node
                            node_tree.nodes.remove(found_node)
                        
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            node_tree.nodes.remove(found_node1)
                                       
        return {'FINISHED'}


class RenderSettEmi(bpy.types.Operator):##Запекание емисии
    bl_idname = "object.rendersettemi"
    bl_label = "Simple Bake Emi"
    
    def execute(self,context):
        bake_target_label = context.active_object.simple_bake_image_name
        bake_target_label_uv = bake_target_label + "_uv"
        cur_obj = bpy.context.active_object#находим выбранный объект
        cyc_sett = bpy.data.scenes["Scene"].cycles
        cyc_sett.bake_type = 'EMIT'
        cyc_sett = context.scene.cycles
        cyc_sett.device = "GPU"
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = 10
        context.scene.render.engine = 'CYCLES'
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
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            found_node1.uv_map = cur_obj.data.uv_layers.active.name
                            break
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
                            break
        bpy.ops.object.bake(type="EMIT",use_clear= True) 
        ########удаление использованного из материала
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    # Ищем узел с указанным лейблом чтоб не создовать несколько
                    found_node = None
                    found_node1 = None
                    for node in node_tree.nodes:
                        if node.label == bake_target_label:
                            found_node = node
                            node_tree.nodes.remove(found_node)
                        
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            node_tree.nodes.remove(found_node1)
        return {'FINISHED'}
    
class RenderSettNorm(bpy.types.Operator):##Запекание нормала
    bl_idname = "object.rendersettnorm"
    bl_label = "Simple Bake Normal"
    
    def execute(self,context):
        bake_target_label = context.active_object.simple_bake_image_name
        bake_target_label_uv = bake_target_label + "_uv"
        cur_obj = bpy.context.active_object#находим выбранный объект
        cyc_sett = bpy.data.scenes["Scene"].cycles
        cyc_sett.bake_type = 'NORMAL'
        cyc_sett = context.scene.cycles
        cyc_sett.device = "GPU"
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = 10
        context.scene.render.engine = 'CYCLES'
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
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            found_node1.uv_map = cur_obj.data.uv_layers.active.name
                            break
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
                            break
        bpy.ops.object.bake(type="NORMAL",use_clear= True) 
        ########удаление использованного из материала
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    # Ищем узел с указанным лейблом чтоб не создовать несколько
                    found_node = None
                    found_node1 = None
                    for node in node_tree.nodes:
                        if node.label == bake_target_label:
                            found_node = node
                            node_tree.nodes.remove(found_node)
                        
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            node_tree.nodes.remove(found_node1)
        return {'FINISHED'}

class RenderEngineCycles(bpy.types.Operator):
    bl_idname = "object.re_cycles"
    bl_label = "Set Cycles"
    def execute(self, context):
        context.scene.render.engine = 'CYCLES'
        cyc_sett = context.scene.cycles
        cyc_sett = bpy.data.scenes["Scene"].cycles
        cyc_sett.device = "GPU"
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = 10
        return {'FINISHED'}
    
class RenderEngineEevee(bpy.types.Operator):
    bl_idname = "object.re_eevee"
    bl_label = "Set Eevee"
    def execute(self, context):
        context.scene.render.engine = 'BLENDER_EEVEE_NEXT'#включаем еву
        context.scene.eevee.taa_render_samples = 16#настройки евы
        context.scene.eevee.use_shadows = False
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
        if bpy.context.active_object:
            if(bpy.context.active_object.type != "CAMERA"):
                #layout.prop(bpy.data.scenes["Scene"], 'name', text='Разрешение')
                row = layout.row()
                row.prop(context.active_object, 'simple_bake_resolution', text='Resolution', icon='OBJECT_HIDDEN')
                row = layout.row()
                row.prop(context.active_object, 'simple_bake_image_name', text="Image name", icon= 'NODE_TEXTURE')
                layout.prop(bpy.context.active_object.data.uv_layers,'active_index',text = "UV Map")
                layout.operator("object.rendersettbc", icon='RESTRICT_RENDER_OFF')
                layout.operator("object.rendersettemi", icon='RESTRICT_RENDER_OFF')
                layout.operator("object.rendersettnorm", icon='RESTRICT_RENDER_OFF')
                layout.split(factor=0.1)
                box = layout.box()
                row = box.row()
                row.prop(context.active_object, 'simple_bake_image_res', text="Render Resolution")
                box.operator("object.renderbc")
                box.operator("object.re_cycles")
                box.operator("object.re_eevee")
        else:
            row = layout.row()
            row.label(text = "No object selected")

# Регистрация классов
def register():
    ## Classes
    
    bpy.utils.register_class(RenderSettEmi)
    bpy.utils.register_class(RenderSettBC)
    bpy.utils.register_class(RenderSettNorm)
    bpy.utils.register_class(OBJECT_PT_CustomPanel)
    bpy.utils.register_class(RenderBC)
    bpy.utils.register_class(RenderEngineCycles)
    bpy.utils.register_class(RenderEngineEevee)
    
    register_properties()
    
    ## Properties
        
    ## Methods
    
    #create_workspace_for_baker()
    
    pass


def unregister():
    bpy.utils.unregister_class(RenderSettEmi)
    bpy.utils.unregister_class(RenderSettBC)
    bpy.utils.unregister_class(RenderSettNorm)
    bpy.utils.unregister_class(OBJECT_PT_CustomPanel)
    bpy.utils.unregister_class(RenderBC)
    bpy.utils.unregister_class(RenderEngineCycles)
    bpy.utils.unregister_class(RenderEngineEevee)
    
    unregister_properties()
    

def register_properties():
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
    bpy.types.Object.simple_bake_image_res = StringProperty(
        name = "Render Resolution",
        default="1024"
    )
    pass


def unregister_properties():
    del bpy.types.Object.simple_bake_resolution
    del bpy.types.Object.simple_bake_image_name
    del bpy.types.Object.simple_bake_image_res
    pass

if __name__ == "__main__":
    register()