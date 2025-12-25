bl_info = {
    "name": "Simple Render Set-Up",
    "blender": (2, 80, 0),
    "category": "Object",
    "description":"N panel-Tool"
}
##еще много оптимизировать
import bpy
from bpy.props import EnumProperty, StringProperty
import numpy as np

bpy.types.Scene.r_name = bpy.props.StringProperty(
    name="r_name",
    default=""
)
bpy.types.Scene.m_name = bpy.props.StringProperty(
    name="m_name",
    default=""
)
bpy.types.Scene.ao_name = bpy.props.StringProperty(
    name="ao_name",
    default=""
)

class RenderSettSave(bpy.types.Operator):##Запекание емисии
    bl_idname = "object.rendersettsave"
    bl_label = "SAVE BEFORE BAKE!"
    
    def execute(self,context):
        if bpy.data.filepath:
            bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
        else:
            self.report({'ERROR'}, "Save the file first")
            return {'CANCELLED'}
        self.report({'WARNING'}, "File saved!")
        return {'FINISHED'}
    
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
        workspaces = bpy.data.workspaces
        context.window.workspace = workspaces.get("Compositing")
        if bpy.data.node_groups.get("NodeTree"):#проверяем есть ли уже композитор
            pass
        else:
            bpy.ops.node.new_compositing_node_group(name = 'NodeTree')
        node_tree = bpy.data.node_groups["NodeTree"]
        #bpy.data.screens["Compositing"].areas[3].spaces[0].
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
        node_tree.links.new(render_layers_node.outputs['Diffuse Color'],render_viewer_nodeBC.inputs['Image'])#соединяем их
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

class RenderSettSelfEmi(bpy.types.Operator):##Запекание цвета
    bl_idname = "object.rendersettselfemi"
    bl_label = "Simple Bake COMBINED"
    
    def execute(self,context):

        samples = int(context.active_object.samples)
        bake_target_label = context.active_object.simple_bake_image_name
        bake_target_label_uv = bake_target_label + "_uv"
        cur_obj = context.active_object#находим выбранный объект
        #выставление настроек рендера
        cyc_sett = context.scene.cycles
        cyc_sett.device = "GPU"
        bpy.data.scenes["Scene"].render.bake.use_selected_to_active = False
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = samples
        cyc_sett.bake_type = 'COMBINED'
        context.scene.render.engine = 'CYCLES'
        context.scene.render.bake.use_pass_direct = True
        context.scene.render.bake.use_pass_indirect = True
        context.scene.render.bake.use_pass_color = True
        bake_resolution = int(context.active_object.simple_bake_resolution)
        found_image = False
        for image in bpy.data.images:
            if(image.name == bake_target_label):#если картинка уже существовала
                    img = bpy.data.images.get(bake_target_label)
                    bpy.data.images.remove(img)#удаляем ее
                    found_image = False
                    break
        if(found_image == False):
            bake_img = bpy.ops.image.new(name = bake_target_label,width=bake_resolution,height=bake_resolution)#создаем картинку
            bpy.data.images[bake_target_label].colorspace_settings.name = "sRGB"#назначаем нужный цветовой профиль
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
                            texture_image_my.label = bake_target_label
                            uv_map_node  = nodes.new(type="ShaderNodeUVMap")#создаем ноду юв
                            uv_map_node.label = bake_target_label_uv
                            uv_map_node.uv_map = cur_obj.data.uv_layers.active.name#выбираем юв
                            node_tree.links.new(uv_map_node.outputs['UV'],texture_image_my.inputs['Vector'])#соединяем юв и картинку
                            node_tree.nodes.active = texture_image_my#делаем активной
                            node_tree.nodes.active.image = bpy.data.images[bake_target_label]#ставим в выбранную картинку
                            break
        context.scene.render.bake.use_selected_to_active = False#отключаем запекание с активного на выбранный
        bpy.ops.object.bake(type="COMBINED",use_clear= True) 
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

class RenderSettBC(bpy.types.Operator):##Запекание цвета
    bl_idname = "object.rendersettbc"
    bl_label = "Simple Bake BC"
    
    def execute(self,context):

        samples = int(context.active_object.samples)
        bake_target_label_BC = context.active_object.simple_bake_image_name + '_bc'
        bake_target_label_uv = bake_target_label_BC + "_uv"
        cur_obj = context.active_object#находим выбранный объект
        #выставление настроек рендера
        cyc_sett = context.scene.cycles
        cyc_sett.device = "GPU"
        bpy.data.scenes["Scene"].render.bake.use_selected_to_active = False
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = samples
        cyc_sett.bake_type = 'EMIT'
        context.scene.render.engine = 'CYCLES'
        context.scene.render.bake.use_pass_direct = False
        context.scene.render.bake.use_pass_indirect = False
        context.scene.render.bake.use_pass_color = True
        node_tree = None
        principled_node = None
        bake_resolution = int(context.active_object.simple_bake_resolution)
        found_image = False
        mats_bc = [None] * len(cur_obj.data.materials)
        for image in bpy.data.images:
            if(image.name == bake_target_label_BC):#если картинка уже существовала
                img = bpy.data.images.get(bake_target_label_BC)
                bpy.data.images.remove(img)#удаляем ее
                found_image = False
                break
        if(found_image == False):
            bake_img = bpy.ops.image.new(name = bake_target_label_BC,width=bake_resolution,height=bake_resolution)#создаем картинку
            bpy.data.images[bake_target_label_BC].colorspace_settings.name = "sRGB"#назначаем нужный цветовой профиль
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                    principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                    BC_input = principled_node.inputs[0]#нашли вход BC
                    if BC_input.is_linked == False:
                        self.report({'ERROR'}, "Base Color input is not connected on material "+cur_obj.data.materials[index].name)#если не подключен металик
                        return {'CANCELLED'}
                    else:
                        pass
                if node_tree:
                    # Ищем узел с указанным лейблом чтоб не создовать несколько
                    found_node = None
                    found_node1 = None
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_BC:
                            found_node = node
                            node_tree.nodes.active = found_node
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            found_node1.uv_map = cur_obj.data.uv_layers.active.name
                            break
                        else:
                            ########################################################################################### Поиск и пересоединение Металика
                            output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                            principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                            BC_input = principled_node.inputs[0]#нашли вход BC
                            emission_input = principled_node.inputs[27]#нашли вход Emission
                            emission_str = principled_node.inputs[28]#нашли вход Emission strength
                            def_emi_str = emission_str.default_value#сохранили стандартную эмиссию
                            emission_str_val = 1.0
                            connected_node_metalic= None#ищем подключенную ноду к металику
                            connected_socket_metalic = None#ищем ее название
                            emission_str.default_value = emission_str_val
                            if emission_input.is_linked:#если есть какоенибудь соединение
                                link = emission_input.links[0]  # Берём первое соединение
                                mats_bc[index] = ( link.from_node, link.from_socket.name )
                            if BC_input.is_linked:#если есть какоенибудь соединение
                                link = BC_input.links[0]  # Берём первое соединение
                                connected_node_metalic = link.from_node  # Нода, откуда идёт связь
                                connected_socket_metalic = link.from_socket.name  # имя, откуда идёт связь
                            else:
                                self.report({'ERROR'}, "BC input is not connected on material "+cur_obj.data.materials[index].name)#если не подключен металик
                                return {'CANCELLED'}
                            if connected_node_metalic:#если существует подключенная нода
                                node_tree.links.new(connected_node_metalic.outputs[connected_socket_metalic],principled_node.inputs[27])#соединяем с emission color

                            texture_image_my = nodes.new(type="ShaderNodeTexImage")#создаем  ноду картинки
                            texture_image_my.label = bake_target_label_BC
                            uv_map_node  = nodes.new(type="ShaderNodeUVMap")#создаем ноду юв
                            uv_map_node.label = bake_target_label_uv
                            uv_map_node.uv_map = cur_obj.data.uv_layers.active.name#выбираем юв
                            node_tree.links.new(uv_map_node.outputs['UV'],texture_image_my.inputs['Vector'])#соединяем юв и картинку
                            node_tree.nodes.active = texture_image_my#делаем активной
                            node_tree.nodes.active.image = bpy.data.images[bake_target_label_BC]#ставим в выбранную картинку
                            break
        context.scene.render.bake.use_selected_to_active = False#отключаем запекание с активного на выбранный
        bpy.ops.object.bake(type="EMIT",use_clear= True) 
        ############################################################################################Вертаем взад
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                    principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                    emission_input_input = principled_node.inputs[27]#нашли вход emission
                    emission_str = principled_node.inputs[28]
                    emission_str.default_value = def_emi_str#возвращаем силу емиссии
                    if emission_input_input.is_linked:#если есть какоенибудь соединение
                            link = emission_input_input.links[0]  # Берём первое соединение
                            node_tree.links.remove(link)
                            if mats_bc[index]:#соединяем с тем emi что был до запекания
                                node_tree.links.new(mats_bc[index][0].outputs[mats_bc[index][1]],principled_node.inputs[27])#соединяем с emission
        ###########################################################################################
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
                        if node.label == bake_target_label_BC:
                            found_node = node
                            node_tree.nodes.remove(found_node)
                        
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            node_tree.nodes.remove(found_node1)
                                       
        return {'FINISHED'}

    

class RenderSettAO(bpy.types.Operator):##Запекание цвета
    bl_idname = "object.rendersettao"
    bl_label = "Simple Bake AO"
    def execute(self,context):

        samples = int(context.active_object.samples)
        bake_target_label_ao = context.active_object.simple_bake_image_name + '_AO'
        bake_target_label_uv = bake_target_label_ao + "_uv"
        cur_obj = context.active_object#находим выбранный объект
        #выставление настроек рендера
        cyc_sett = context.scene.cycles
        cyc_sett.device = "GPU"
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = samples
        bpy.data.scenes["Scene"].render.bake.use_selected_to_active = False
        cyc_sett.bake_type = 'AO'
        context.scene.render.engine = 'CYCLES'
        bake_resolution = int(context.active_object.simple_bake_resolution)
        found_image = False
        for image in bpy.data.images:
            if(image.name == bake_target_label_ao):#если картинка уже существовала
                    img = bpy.data.images.get(bake_target_label_ao)
                    bpy.data.images.remove(img)#удаляем ее
                    found_image = False
                    break
        if(found_image == False):
            bake_img = bpy.ops.image.new(name = bake_target_label_ao,width=bake_resolution,height=bake_resolution,float = True)#создаем картинку
            bpy.data.images[bake_target_label_ao].colorspace_settings.name = "Non-Color"#назначаем нужный цветовой профиль
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
                        if node.label == bake_target_label_ao:
                            found_node = node
                            node_tree.nodes.active = found_node
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            found_node1.uv_map = cur_obj.data.uv_layers.active.name
                            break
                        else:
                            texture_image_my = nodes.new(type="ShaderNodeTexImage")#создаем  ноду картинки
                            texture_image_my.label = bake_target_label_ao
                            uv_map_node  = nodes.new(type="ShaderNodeUVMap")#создаем ноду юв
                            uv_map_node.label = bake_target_label_uv
                            uv_map_node.uv_map = cur_obj.data.uv_layers.active.name#выбираем юв
                            node_tree.links.new(uv_map_node.outputs['UV'],texture_image_my.inputs['Vector'])#соединяем юв и картинку
                            node_tree.nodes.active = texture_image_my#делаем активной
                            node_tree.nodes.active.image = bpy.data.images[bake_target_label_ao]#ставим в выбранную картинку
                            break
        context.scene.render.bake.use_selected_to_active = False#отключаем запекание с активного на выбранный
        bpy.ops.object.bake(type="AO",use_clear= True) 
        bpy.types.Scene.ao_name = bake_target_label_ao
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
                        if node.label == bake_target_label_ao:
                            found_node = node
                            node_tree.nodes.remove(found_node)
                        
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            node_tree.nodes.remove(found_node1)
                                       
        return {'FINISHED'}


class RenderSettM(bpy.types.Operator):##Запекание цвета
    bl_idname = "object.rendersettm"
    bl_label = "Simple Bake M"
    
    def execute(self,context):
        
        samples = int(context.active_object.samples)
        bake_target_label_m = context.active_object.simple_bake_image_name + '_M'
        bake_target_label_uv = bake_target_label_m + "_uv"
        cur_obj = context.active_object#находим выбранный объект
        #выставление настроек рендера
        cyc_sett = context.scene.cycles
        cyc_sett.device = "GPU"
        bpy.data.scenes["Scene"].render.bake.use_selected_to_active = False
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = samples
        cyc_sett.bake_type = 'EMIT'
        context.scene.render.engine = 'CYCLES'
        context.scene.render.bake.use_pass_direct = False
        context.scene.render.bake.use_pass_indirect = False
        context.scene.render.bake.use_pass_color = True
        node_tree = None
        principled_node = None
        bake_resolution = int(context.active_object.simple_bake_resolution)
        found_image = False
        mats_bc = [None] * len(cur_obj.data.materials)
        for image in bpy.data.images:
            if(image.name == bake_target_label_m):#если картинка уже существовала
                img = bpy.data.images.get(bake_target_label_m)
                bpy.data.images.remove(img)#удаляем ее
                found_image = False
                break
        if(found_image == False):
            bake_img = bpy.ops.image.new(name = bake_target_label_m,width=bake_resolution,height=bake_resolution,float = True)#создаем картинку
            bpy.data.images[bake_target_label_m].colorspace_settings.name = "Non-Color"#назначаем нужный цветовой профиль
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                    principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                    metalic_input = principled_node.inputs.get("Metallic")#нашли вход металик
                    if metalic_input.is_linked == False:
                        self.report({'ERROR'}, "Metallic input is not connected on material "+cur_obj.data.materials[index].name)#если не подключен металик
                        return {'CANCELLED'}
                    else:
                        pass
                if node_tree:
                    # Ищем узел с указанным лейблом чтоб не создовать несколько
                    found_node = None
                    found_node1 = None
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_m:
                            found_node = node
                            node_tree.nodes.active = found_node
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            found_node1.uv_map = cur_obj.data.uv_layers.active.name
                            break
                        else:
                            ########################################################################################### Поиск и пересоединение Металика
                            output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                            principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                            metalic_input = principled_node.inputs.get("Metallic")#нашли вход металик
                            emission_input = principled_node.inputs[27]#нашли вход Emission
                            emission_str = principled_node.inputs[28]#нашли вход Emission strength
                            def_emi_str = emission_str.default_value#сохранили стандартную эмиссию
                            emission_str_val = 1.0
                            connected_node_metalic= None#ищем подключенную ноду к металику
                            connected_socket_metalic = None#ищем ее название
                            emission_str.default_value = emission_str_val
                            if emission_input.is_linked:#если есть какоенибудь соединение
                                link = emission_input.links[0]  # Берём первое соединение
                                mats_bc[index] = ( link.from_node, link.from_socket.name )
                            if metalic_input.is_linked:#если есть какоенибудь соединение
                                link = metalic_input.links[0]  # Берём первое соединение
                                connected_node_metalic = link.from_node  # Нода, откуда идёт связь
                                connected_socket_metalic = link.from_socket.name  # имя, откуда идёт связь
                            else:
                                self.report({'ERROR'}, "Metallic input is not connected on material "+cur_obj.data.materials[index].name)#если не подключен металик
                                return {'CANCELLED'}
                            if connected_node_metalic:#если существует подключенная нода
                                node_tree.links.new(connected_node_metalic.outputs[connected_socket_metalic],principled_node.inputs[27])#соединяем с emission color

                            texture_image_my = nodes.new(type="ShaderNodeTexImage")#создаем  ноду картинки
                            texture_image_my.label = bake_target_label_m
                            uv_map_node  = nodes.new(type="ShaderNodeUVMap")#создаем ноду юв
                            uv_map_node.label = bake_target_label_uv
                            uv_map_node.uv_map = cur_obj.data.uv_layers.active.name#выбираем юв
                            node_tree.links.new(uv_map_node.outputs['UV'],texture_image_my.inputs['Vector'])#соединяем юв и картинку
                            node_tree.nodes.active = texture_image_my#делаем активной
                            node_tree.nodes.active.image = bpy.data.images[bake_target_label_m]#ставим в выбранную картинку
                            break
        context.scene.render.bake.use_selected_to_active = False#отключаем запекание с активного на выбранный
        bpy.ops.object.bake(type="EMIT",use_clear= True) 
        bpy.types.Scene.m_name = bake_target_label_m
        ############################################################################################Вертаем взад
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                    principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                    emission_input_input = principled_node.inputs[27]#нашли вход emission
                    emission_str = principled_node.inputs[28]
                    emission_str.default_value = def_emi_str#возвращаем силу емиссии
                    if emission_input_input.is_linked:#если есть какоенибудь соединение
                            link = emission_input_input.links[0]  # Берём первое соединение
                            node_tree.links.remove(link)
                            if mats_bc[index]:#соединяем с тем emi что был до запекания
                                node_tree.links.new(mats_bc[index][0].outputs[mats_bc[index][1]],principled_node.inputs[27])#соединяем с emission
        ###########################################################################################
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
                        if node.label == bake_target_label_m:
                            found_node = node
                            node_tree.nodes.remove(found_node)
                        
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            node_tree.nodes.remove(found_node1)
                                       
        return {'FINISHED'}

class RenderSettEmi(bpy.types.Operator):##Запекание емисии
    bl_idname = "object.rendersettemi"
    bl_label = "Simple Bake Emission"
    
    def execute(self,context):

        samples = int(context.active_object.samples)
        bake_target_label = context.active_object.simple_bake_image_name
        bake_target_label_uv = bake_target_label + "_uv"
        cur_obj = bpy.context.active_object#находим выбранный объект
        cyc_sett = bpy.data.scenes["Scene"].cycles
        cyc_sett.bake_type = 'EMIT'
        cyc_sett = context.scene.cycles
        cyc_sett.device = "GPU"
        bpy.data.scenes["Scene"].render.bake.use_selected_to_active = False
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = samples
        context.scene.render.engine = 'CYCLES'
        bake_resolution = int(context.active_object.simple_bake_resolution)
        found_image = False
        for image in bpy.data.images:
            if(image.name == bake_target_label):#если картинка уже существовала
                    img = bpy.data.images.get(bake_target_label)
                    bpy.data.images.remove(img)#удаляем ее
                    found_image = False
                    break
        if(found_image == False):
            bake_img = bpy.ops.image.new(name = bake_target_label,width=bake_resolution,height=bake_resolution,float = True)#создаем картинку
            bpy.data.images[bake_target_label].colorspace_settings.name = "sRGB"#назначаем нужный цветовой профиль
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                    principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                    emission_input = principled_node.inputs[27]#нашли вход эмисии
                    if emission_input.is_linked == False:
                        self.report({'ERROR'}, "Emission input is not connected on material "+cur_obj.data.materials[index].name)#если не подключен эмиссионный
                        return {'CANCELLED'}
                    else:
                        pass
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
        context.scene.render.bake.use_selected_to_active = False#отключаем запекание с активного на выбранный
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

class RenderSettOp(bpy.types.Operator):##Запекание емисии
    bl_idname = "object.rendersettop"
    bl_label = "Simple Bake OP(IOR input)"
    
    def execute(self,context):

        samples = int(context.active_object.samples)
        bake_target_label_op = context.active_object.simple_bake_image_name + '_op'
        bake_target_label_uv = bake_target_label_op + "_uv"
        cur_obj = bpy.context.active_object#находим выбранный объект
        cyc_sett = bpy.data.scenes["Scene"].cycles
        cyc_sett.bake_type = 'EMIT'
        cyc_sett = context.scene.cycles
        cyc_sett.device = "GPU"
        bpy.data.scenes["Scene"].render.bake.use_selected_to_active = False
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = samples
        context.scene.render.engine = 'CYCLES'
        bake_resolution = int(context.active_object.simple_bake_resolution)
        found_image = False
        mats_bc = [None] * len(cur_obj.data.materials)
        mats_m = [None] * len(cur_obj.data.materials)
        bake_img_op = None
        for image in bpy.data.images:
            if(image.name == bake_target_label_op):#если картинка уже существовала
                    img = bpy.data.images.get(bake_target_label_op)
                    bpy.data.images.remove(img)#удаляем ее
                    found_image = False
                    break
        if(found_image == False):
            bake_img_op = bpy.ops.image.new(name = bake_target_label_op,width=bake_resolution,height=bake_resolution,float = True)#создаем картинку
            bpy.data.images[bake_target_label_op].colorspace_settings.name = "Non-Color"#назначаем нужный цветовой профиль
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                    principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                    ior_input = principled_node.inputs[3]#нашли вход ior
                    if ior_input.is_linked == False:
                        self.report({'ERROR'}, "IOR input is not connected on material "+cur_obj.data.materials[index].name)#если не подключен ior
                        return {'CANCELLED'}
                    else:
                        pass
                if node_tree:
                    # Ищем узел с указанным лейблом чтоб не создовать несколько
                    found_node = None
                    found_node1 = None
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_op:
                            found_node = node
                            node_tree.nodes.active = found_node
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            found_node1.uv_map = cur_obj.data.uv_layers.active.name
                            break
                        else:
                            ########################################################################################### Поиск и пересоединение Металика
                            output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                            principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                            op_input = principled_node.inputs[3]#нашли вход ior
                            bc_input = principled_node.inputs[0]#нашли вход bc
                            m_input = principled_node.inputs[1]#нашли вход m
                            connected_node_op= None#ищем подключенную ноду к opacity
                            connected_socket_op = None#ищем ее название
                            if m_input.is_linked:#если есть какоенибудь соединение m
                                link_m = m_input.links[0]  # Берём первое соединение
                                mats_m[index] = ( link_m.from_node, link_m.from_socket.name )
                                node_tree.links.remove(link_m) #удаляем то что в металик идет
                            if bc_input.is_linked:#если есть какоенибудь соединение
                                link = bc_input.links[0]  # Берём первое соединение
                                mats_bc[index] = ( link.from_node, link.from_socket.name )
                            if op_input.is_linked:#если есть какоенибудь соединение
                                link = op_input.links[0]  # Берём первое соединение
                                connected_node_op = link.from_node  # Нода, откуда идёт связь
                                connected_socket_op = link.from_socket.name  # имя, откуда идёт связь
                            else:
                                self.report({'ERROR'}, "Opacity input is not connected on material "+cur_obj.data.materials[index].name)#если не подключен op
                                return {'CANCELLED'}
                            if connected_node_op:#если существует подключенная нода
                                node_tree.links.new(connected_node_op.outputs[connected_socket_op],principled_node.inputs[0])#соединяем с bc

                            texture_image_my = nodes.new(type="ShaderNodeTexImage")#создаем  ноду картинки
                            texture_image_my.label = bake_target_label_op
                            uv_map_node  = nodes.new(type="ShaderNodeUVMap")#создаем ноду юв
                            uv_map_node.label = bake_target_label_uv
                            uv_map_node.uv_map = cur_obj.data.uv_layers.active.name#выбираем юв
                            node_tree.links.new(uv_map_node.outputs['UV'],texture_image_my.inputs['Vector'])#соединяем юв и картинку
                            node_tree.nodes.active = texture_image_my#делаем активной
                            node_tree.nodes.active.image = bpy.data.images[bake_target_label_op]#ставим в выбранную картинку
                            break
        context.scene.render.bake.use_selected_to_active = False#отключаем запекание с активного на выбранный
        bpy.ops.object.bake(type="DIFFUSE",use_clear= True) 
        bpy.types.Scene.op_name = bake_target_label_op
        ############################################################################################Вертаем взад
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                    principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                    bc_input = principled_node.inputs[0]#нашли вход bc
                    if bc_input.is_linked:#если есть какоенибудь соединение
                            link = bc_input.links[0]  # Берём первое соединение
                            node_tree.links.remove(link)
                            if mats_bc[index]:#соединяем с тем bc что был до запекания
                                node_tree.links.new(mats_bc[index][0].outputs[mats_bc[index][1]],principled_node.inputs[0])#соединяем с bc
                            if mats_m[index]:#соединяем с тем bc что был до запекания
                                node_tree.links.new(mats_m[index][0].outputs[mats_m[index][1]],principled_node.inputs[1])#соединяем с m
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
                        if node.label == bake_target_label_op:
                            found_node = node
                            node_tree.nodes.remove(found_node)
                        
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            node_tree.nodes.remove(found_node1) 
        return {'FINISHED'}
    
class RenderSettRough(bpy.types.Operator):##Запекание емисии
    bl_idname = "object.rendersettrough"
    bl_label = "Simple Bake R"
    
    def execute(self,context):

        samples = int(context.active_object.samples)
        bake_target_label_R = context.active_object.simple_bake_image_name + '_R'
        bake_target_label_uv = bake_target_label_R + "_uv"
        cur_obj = bpy.context.active_object#находим выбранный объект
        cyc_sett = bpy.data.scenes["Scene"].cycles
        cyc_sett = context.scene.cycles
        cyc_sett.device = "GPU"
        bpy.data.scenes["Scene"].render.bake.use_selected_to_active = False
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = samples
        context.scene.render.engine = 'CYCLES'
        bake_resolution = int(context.active_object.simple_bake_resolution)
        found_image = False
        mats_bc = [None] * len(cur_obj.data.materials)
        bake_img_r = None
        for image in bpy.data.images:
            if(image.name == bake_target_label_R):#если картинка уже существовала
                    img = bpy.data.images.get(bake_target_label_R)
                    bpy.data.images.remove(img)#удаляем ее
                    found_image = False
                    break
        if(found_image == False):
            bake_img_r = bpy.ops.image.new(name = bake_target_label_R,width=bake_resolution,height=bake_resolution,float = True)#создаем картинку
            bpy.data.images[bake_target_label_R].colorspace_settings.name = "Non-Color"#назначаем нужный цветовой профиль
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                    principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                    roughness_input = principled_node.inputs[2]#нашли вход roughness
                    if roughness_input.is_linked == False:
                        self.report({'ERROR'}, "Roughness input is not connected on material "+cur_obj.data.materials[index].name)#если не подключен roughness
                        return {'CANCELLED'}
                    else:
                        pass
                if node_tree:
                    # Ищем узел с указанным лейблом чтоб не создовать несколько
                    found_node = None
                    found_node1 = None
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_R:
                            found_node = node
                            node_tree.nodes.active = found_node
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            found_node1.uv_map = cur_obj.data.uv_layers.active.name
                            break
                        else:
                            ########################################################################################### Поиск и пересоединение Металика
                            output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                            principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                            roughness_input = principled_node.inputs[2]#нашли вход roughness
                            emission_input = principled_node.inputs[27]#нашли вход Emission
                            emission_str = principled_node.inputs[28]#нашли вход Emission strength
                            def_emi_str = emission_str.default_value#сохранили стандартную эмиссию
                            emission_str_val = 1.0#значение силы емиссии
                            connected_node_roughness= None#ищем подключенную ноду к металику
                            connected_socket_roughness = None#ищем ее название
                            emission_str.default_value = emission_str_val#назначение силы эмиссии
                            if emission_input.is_linked:#если есть какоенибудь соединение
                                link = emission_input.links[0]  # Берём первое соединение
                                mats_bc[index] = ( link.from_node, link.from_socket.name )
                            if roughness_input.is_linked:#если есть какоенибудь соединение
                                link = roughness_input.links[0]  # Берём первое соединение
                                connected_node_roughness = link.from_node  # Нода, откуда идёт связь
                                connected_socket_roughness = link.from_socket.name  # имя, откуда идёт связь
                            else:
                                self.report({'ERROR'}, "Roughness input is not connected on material "+cur_obj.data.materials[index].name)#если не подключен roughness
                                return {'CANCELLED'}
                            if connected_node_roughness:#если существует подключенная нода
                                node_tree.links.new(connected_node_roughness.outputs[connected_socket_roughness],principled_node.inputs[27])#соединяем с emission color

                            texture_image_my = nodes.new(type="ShaderNodeTexImage")#создаем  ноду картинки
                            texture_image_my.label = bake_target_label_R
                            uv_map_node  = nodes.new(type="ShaderNodeUVMap")#создаем ноду юв
                            uv_map_node.label = bake_target_label_uv
                            uv_map_node.uv_map = cur_obj.data.uv_layers.active.name#выбираем юв
                            node_tree.links.new(uv_map_node.outputs['UV'],texture_image_my.inputs['Vector'])#соединяем юв и картинку
                            node_tree.nodes.active = texture_image_my#делаем активной
                            node_tree.nodes.active.image = bpy.data.images[bake_target_label_R]#ставим в выбранную картинку
                            break
        context.scene.render.bake.use_selected_to_active = False#отключаем запекание с активного на выбранный
        bpy.ops.object.bake(type="EMIT",use_clear= True) 
        bpy.types.Scene.r_name = bake_target_label_R
        ############################################################################################Вертаем взад
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                    principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                    emission_input_input = principled_node.inputs[27]#нашли вход emission
                    emission_str = principled_node.inputs[28]
                    emission_str.default_value = def_emi_str
                    if emission_input_input.is_linked:#если есть какоенибудь соединение
                            link = emission_input_input.links[0]  # Берём первое соединение
                            node_tree.links.remove(link)
                            if mats_bc[index]:#соединяем с тем emi что был до запекания
                                node_tree.links.new(mats_bc[index][0].outputs[mats_bc[index][1]],principled_node.inputs[27])#соединяем с emission
        ###########################################################################################
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
                        if node.label == bake_target_label_R:
                            found_node = node
                            node_tree.nodes.remove(found_node)
                        
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            node_tree.nodes.remove(found_node1) 
        return {'FINISHED'}

class RenderSettNorm(bpy.types.Operator):##Запекание нормала
    bl_idname = "object.rendersettnorm"
    bl_label = "Simple Bake N     (DESCRIPTION)"
    bl_description = "if you want to review baked normal in material after baking select uv that your baking to in normal map node or delete base uv cuz it brokes it"
    
    def execute(self,context):

        samples = int(context.active_object.samples)
        bake_target_label_N = context.active_object.simple_bake_image_name + "_N"
        bake_target_label_uv = bake_target_label_N + "_uv"
        cur_obj = bpy.context.active_object#находим выбранный объект
        cyc_sett = bpy.data.scenes["Scene"].cycles
        cyc_sett.bake_type = 'NORMAL'
        bpy.data.scenes["Scene"].render.bake.normal_space = 'OBJECT'#СНАЧАЛА запекаем в обджект спейсе потому что блендер тупит с тангенс спейсом
        cyc_sett = context.scene.cycles
        cyc_sett.device = "GPU"
        bpy.data.scenes["Scene"].render.bake.use_selected_to_active = False
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = samples
        context.scene.render.engine = 'CYCLES'
        bake_resolution = int(context.active_object.simple_bake_resolution)
        found_image = False
        mats_ior = [None] * len(cur_obj.data.materials)
        mats_n = [None] * len(cur_obj.data.materials)
        node_normal_object = None
        for image in bpy.data.images:
            if(image.name == bake_target_label_N):#если картинка уже существовала
                    img = bpy.data.images.get(bake_target_label_N)
                    bpy.data.images.remove(img)#удаляем ее
                    found_image = False
                    break
        if(found_image == False):
            bake_img = bpy.ops.image.new(name = bake_target_label_N,width=bake_resolution,height=bake_resolution)#создаем картинку
            bpy.data.images[bake_target_label_N].colorspace_settings.name = "Non-Color"#назначаем нужный цветовой профиль
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                    principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                    n_input = principled_node.inputs[5]#нашли вход normal
                    if n_input.is_linked == False:
                        self.report({'ERROR'}, "Normal input is not connected on material "+cur_obj.data.materials[index].name)#если не подключен normal
                        return {'CANCELLED'}
                    else:
                        pass
                if node_tree:
                    # Ищем узел с указанным лейблом чтоб не создовать несколько
                    found_node = None
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_N:
                            found_node = node
                            node_tree.nodes.active = found_node
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            found_node1.uv_map = cur_obj.data.uv_layers.active.name
                            break
                        else:
                            output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                            principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                            op_input = principled_node.inputs[3]#нашли вход ior
                            n_input = principled_node.inputs[5]#нашли вход normal
                            connected_node_n= None#ищем подключенную ноду к normal
                            connected_socket_n = None#ищем ее название
                            connected_node_op= None#ищем подключенную ноду к opacity
                            connected_socket_op = None#ищем ее название
                            link = None
                            if op_input.is_linked:#если есть какоенибудь соединение
                                link = op_input.links[0]  # Берём первое соединение
                                connected_node_op = link.from_node  # Нода, откуда идёт связь
                                connected_socket_op = link.from_socket.name  # имя, откуда идёт связь
                                mats_ior[index] = ( link.from_node, link.from_socket.name )
                            if n_input.is_linked:#если есть какоенибудь соединение с нормалом
                                link_n = n_input.links[0]  # Берём первое соединение
                                connected_node_n = link_n.from_node  # Нода, откуда идёт связь
                                connected_socket_n = link_n.from_socket.name  # имя, откуда идёт связь
                                mats_n[index] = ( link_n.from_node, link_n.from_socket.name )#запоминаем что было до запекания
                            if connected_node_op:
                                node_tree.links.remove(link)
                            texture_image_my = nodes.new(type="ShaderNodeTexImage")#создаем  ноду картинки
                            texture_image_my_second = nodes.new(type="ShaderNodeTexImage")#создаем  ноду картинки для второго прохода запекания
                            node_normal_object = nodes.new(type="ShaderNodeNormalMap")#создаем ноду нормал мап
                            node_normal_object.name = 'NormalMapObject'# обзываем ее чтоб не путать потом
                            node_normal_object.label = 'NormalMapObject'# обзываем ее чтоб не путать потом
                            node_normal_object.space = 'OBJECT'#ставим обджект спейс
                            texture_image_my.label = bake_target_label_N
                            texture_image_my_second.label = bake_target_label_N #вторая нода для тангенс спейса

                            uv_map_node  = nodes.new(type="ShaderNodeUVMap")#создаем ноду юв
                            uv_map_node.label = bake_target_label_uv
                            uv_map_node.uv_map = cur_obj.data.uv_layers.active.name#выбираем юв

                            node_tree.links.new(uv_map_node.outputs['UV'],texture_image_my.inputs['Vector'])#соединяем юв и картинку
                            node_tree.links.new(uv_map_node.outputs['UV'],texture_image_my_second.inputs['Vector'])#соединяем юв и вторую картинку
                            node_tree.links.new(texture_image_my_second.outputs['Color'],node_normal_object.inputs['Color'])#соединяем вторую картинку и нормал мап
                            bake_resolution = int(context.active_object.simple_bake_resolution)
                            
                            node_tree.nodes.active = texture_image_my_second#делаем активной текстуру для тангенс спейса
                            node_tree.nodes.active.image = bpy.data.images[bake_target_label_N]#ставим в выбранную картинку
                            node_tree.nodes.active = texture_image_my#делаем активной основную для запекания обджект спейса
                            node_tree.nodes.active.image = bpy.data.images[bake_target_label_N]#ставим в выбранную картинку    
                            break
        context.scene.render.bake.use_selected_to_active = False#отключаем запекание с активного на выбранный
        bpy.ops.object.bake(type="NORMAL",use_clear= True) 
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_N:
                            found_node = node
                            node_tree.nodes.active = found_node
                            break
                        else:
                            output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                            principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                            if connected_node_n:
                                principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                                n_input = principled_node.inputs[5]#нашли вход normal
                                link_n = n_input.links[0]
                                node_tree.links.remove(link_n)
                            node_tree.links.new(node_normal_object.outputs['Normal'],principled_node.inputs[5])#соединяем с normal
                            break
        bpy.data.scenes["Scene"].render.bake.normal_space = 'TANGENT'#возвращаем тангенс спейс обратно
        context.scene.render.bake.use_selected_to_active = False#отключаем запекание с активного на выбранный
        bpy.ops.object.bake(type="NORMAL",use_clear= False)#второй проход запекания в тангенс спейсе
        ########удаление использованного из материала
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    # Ищем узел с указанным лейблом чтоб не создовать несколько
                    output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                    principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                    new_n_node = node_tree.nodes.get('NormalMapObject')#нашли ноду нормал мап
                    op_input = principled_node.inputs[3]#нашли вход op
                    if op_input.is_linked:
                        pass
                    else:
                        print(mats_ior[index])
                        if mats_ior[index]:#соединяем с тем op что был до запекания
                            node_tree.links.new(mats_ior[index][0].outputs[mats_ior[index][1]],principled_node.inputs[3])#соединяем с ior
                        if mats_n[index]:#соединяем с тем n что был до запекания
                            node_tree.links.new(mats_n[index][0].outputs[mats_n[index][1]],principled_node.inputs[5])#соединяем с normal
                    found_node = None
                    found_node1 = None
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_N:
                            found_node = node
                            node_tree.nodes.remove(found_node)

                    for node in node_tree.nodes:
                        if node == new_n_node:
                            found_node2 = node
                            node_tree.nodes.remove(found_node2)
            
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            node_tree.nodes.remove(found_node1)
        return {'FINISHED'}

class RenderEngineCycles(bpy.types.Operator):
    bl_idname = "object.re_cycles"
    bl_label = "Set Cycles"
    def execute(self, context):
        samples = int(context.active_object.samples)
        context.scene.render.engine = 'CYCLES'
        cyc_sett = context.scene.cycles
        cyc_sett = bpy.data.scenes["Scene"].cycles
        cyc_sett.device = "GPU"
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = samples
        return {'FINISHED'}
    
class RenderEngineEevee(bpy.types.Operator):
    bl_idname = "object.re_eevee"
    bl_label = "Set Eevee"
    def execute(self, context):
        context.scene.render.engine = 'BLENDER_EEVEE'#включаем еву
        context.scene.eevee.taa_render_samples = 16#настройки евы
        context.scene.eevee.use_shadows = False
        return {'FINISHED'}
    

class RenderSettRMA(bpy.types.Operator):##Запекание емисии
    bl_idname = "object.rendersettrma"
    bl_label = "Simple Bake RMAO"
    
    def execute(self,context):

        samples = int(context.active_object.samples)
        bake_target_label_R = context.active_object.simple_bake_image_name + '_R'
        bake_target_label_uv = bake_target_label_R + "_uv"
        cur_obj = bpy.context.active_object#находим выбранный объект
        cyc_sett = bpy.data.scenes["Scene"].cycles
        cyc_sett.bake_type = 'ROUGHNESS'
        cyc_sett = context.scene.cycles
        cyc_sett.device = "GPU"
        bpy.data.scenes["Scene"].render.bake.use_selected_to_active = False
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = samples
        context.scene.render.engine = 'CYCLES'
        bake_resolution = int(context.active_object.simple_bake_resolution)
        found_image = False
        mats_bc = [None] * len(cur_obj.data.materials)
        bake_img_r = None
        for image in bpy.data.images:
            if(image.name == bake_target_label_R):#если картинка уже существовала
                    img = bpy.data.images.get(bake_target_label_R)
                    bpy.data.images.remove(img)#удаляем ее
                    found_image = False
                    break
        if(found_image == False):
            bake_img_r = bpy.ops.image.new(name = bake_target_label_R,width=bake_resolution,height=bake_resolution,float = True)#создаем картинку
            bpy.data.images[bake_target_label_R].colorspace_settings.name = "Non-Color"#назначаем нужный цветовой профиль
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                    principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                    roughness_input = principled_node.inputs[2]#нашли вход roughness
                    metalic_input = principled_node.inputs.get("Metallic")#нашли вход металик
                    if roughness_input.is_linked == False or metalic_input.is_linked == False:
                        self.report({'ERROR'}, "Roughness or Metallic input is not connected on material "+cur_obj.data.materials[index].name)#если не подключен normal
                        return {'CANCELLED'}
                    else:
                        pass
                if node_tree:
                    # Ищем узел с указанным лейблом чтоб не создовать несколько
                    found_node = None
                    found_node1 = None
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_R:
                            found_node = node
                            node_tree.nodes.active = found_node
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            found_node1.uv_map = cur_obj.data.uv_layers.active.name
                            break
                        else:
                            ########################################################################################### Поиск и пересоединение Металика
                            output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                            principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                            roughness_input = principled_node.inputs[2]#нашли вход roughness
                            emission_input = principled_node.inputs[27]#нашли вход Emission
                            emission_str = principled_node.inputs[28]
                            def_emi_str = emission_str.default_value#сохранили стандартную эмиссию
                            emission_str_val = 1.0
                            connected_node_roughness= None#ищем подключенную ноду к металику
                            connected_socket_roughness = None#ищем ее название
                            emission_str.default_value = emission_str_val
                            if emission_input.is_linked:#если есть какоенибудь соединение
                                link = emission_input.links[0]  # Берём первое соединение
                                mats_bc[index] = ( link.from_node, link.from_socket.name )
                            if roughness_input.is_linked:#если есть какоенибудь соединение
                                link = roughness_input.links[0]  # Берём первое соединение
                                connected_node_roughness = link.from_node  # Нода, откуда идёт связь
                                connected_socket_roughness = link.from_socket.name  # имя, откуда идёт связь
                            else:
                                self.report({'ERROR'}, "Roughness input is not connected on material "+cur_obj.data.materials[index].name)#если не подключен roughness
                                return {'CANCELLED'}
                            if connected_node_roughness:#если существует подключенная нода
                                node_tree.links.new(connected_node_roughness.outputs[connected_socket_roughness],principled_node.inputs[27])#соединяем с emission color

                            texture_image_my = nodes.new(type="ShaderNodeTexImage")#создаем  ноду картинки
                            texture_image_my.label = bake_target_label_R
                            uv_map_node  = nodes.new(type="ShaderNodeUVMap")#создаем ноду юв
                            uv_map_node.label = bake_target_label_uv
                            uv_map_node.uv_map = cur_obj.data.uv_layers.active.name#выбираем юв
                            node_tree.links.new(uv_map_node.outputs['UV'],texture_image_my.inputs['Vector'])#соединяем юв и картинку
                            node_tree.nodes.active = texture_image_my#делаем активной
                            node_tree.nodes.active.image = bpy.data.images[bake_target_label_R]#ставим в выбранную картинку
                            break
        context.scene.render.bake.use_selected_to_active = False#отключаем запекание с активного на выбранный
        bpy.ops.object.bake(type="EMIT",use_clear= True) 
        bpy.types.Scene.r_name = bake_target_label_R
        ############################################################################################Вертаем взад
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                    principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                    emission_input_input = principled_node.inputs[27]#нашли вход emission
                    emission_str = principled_node.inputs[28]
                    emission_str.default_value = def_emi_str#возвращаем стандартную эмиссию
                    if emission_input_input.is_linked:#если есть какоенибудь соединение
                            link = emission_input_input.links[0]  # Берём первое соединение
                            node_tree.links.remove(link)
                            if mats_bc[index]:#соединяем с тем emi что был до запекания
                                node_tree.links.new(mats_bc[index][0].outputs[mats_bc[index][1]],principled_node.inputs[27])#соединяем с emission
        ###########################################################################################
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
                        if node.label == bake_target_label_R:
                            found_node = node
                            node_tree.nodes.remove(found_node)
                        
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            node_tree.nodes.remove(found_node1) 

        samples = int(context.active_object.samples)
        bake_target_label_m = context.active_object.simple_bake_image_name + '_M'
        bake_target_label_uv = bake_target_label_m + "_uv"
        cur_obj = context.active_object#находим выбранный объект
        #выставление настроек рендера
        cyc_sett = context.scene.cycles
        cyc_sett.device = "GPU"
        bpy.data.scenes["Scene"].render.bake.use_selected_to_active = False
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.samples = samples
        cyc_sett.bake_type = 'EMIT'
        context.scene.render.engine = 'CYCLES'
        context.scene.render.bake.use_pass_direct = False
        context.scene.render.bake.use_pass_indirect = False
        context.scene.render.bake.use_pass_color = True
        node_tree = None
        principled_node = None
        bake_resolution = int(context.active_object.simple_bake_resolution)
        found_image = False
        mats_bc = [None] * len(cur_obj.data.materials)
        for image in bpy.data.images:
            if(image.name == bake_target_label_m):#если картинка уже существовала
                img = bpy.data.images.get(bake_target_label_m)
                bpy.data.images.remove(img)#удаляем ее
                found_image = False
                break
        if(found_image == False):
            bake_img = bpy.ops.image.new(name = bake_target_label_m,width=bake_resolution,height=bake_resolution,float = True)#создаем картинку
            bpy.data.images[bake_target_label_m].colorspace_settings.name = "Non-Color"#назначаем нужный цветовой профиль
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
                        if node.label == bake_target_label_m:
                            found_node = node
                            node_tree.nodes.active = found_node
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            found_node1.uv_map = cur_obj.data.uv_layers.active.name
                            break
                        else:
                            ########################################################################################### Поиск и пересоединение Металика
                            output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                            principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                            metalic_input = principled_node.inputs.get("Metallic")#нашли вход металик
                            emission_input = principled_node.inputs[27]#нашли вход Emission
                            emission_str = principled_node.inputs[28]
                            def_emi_str = emission_str.default_value#сохранили стандартную эмиссию
                            emission_str_val = 1.0
                            connected_node_metalic= None#ищем подключенную ноду к металику
                            connected_socket_metalic = None#ищем ее название
                            emission_str.default_value = emission_str_val
                            if emission_input.is_linked:#если есть какоенибудь соединение
                                link = emission_input.links[0]  # Берём первое соединение
                                mats_bc[index] = ( link.from_node, link.from_socket.name )
                            if metalic_input.is_linked:#если есть какоенибудь соединение
                                link = metalic_input.links[0]  # Берём первое соединение
                                connected_node_metalic = link.from_node  # Нода, откуда идёт связь
                                connected_socket_metalic = link.from_socket.name  # имя, откуда идёт связь
                            else:
                                self.report({'ERROR'}, "Metallic input is not connected on material "+cur_obj.data.materials[index].name)#если не подключен металик
                                return {'CANCELLED'}
                            if connected_node_metalic:#если существует подключенная нода
                                node_tree.links.new(connected_node_metalic.outputs[connected_socket_metalic],principled_node.inputs[27])#соединяем с emission color

                            texture_image_my = nodes.new(type="ShaderNodeTexImage")#создаем  ноду картинки
                            texture_image_my.label = bake_target_label_m
                            uv_map_node  = nodes.new(type="ShaderNodeUVMap")#создаем ноду юв
                            uv_map_node.label = bake_target_label_uv
                            uv_map_node.uv_map = cur_obj.data.uv_layers.active.name#выбираем юв
                            node_tree.links.new(uv_map_node.outputs['UV'],texture_image_my.inputs['Vector'])#соединяем юв и картинку
                            node_tree.nodes.active = texture_image_my#делаем активной
                            node_tree.nodes.active.image = bpy.data.images[bake_target_label_m]#ставим в выбранную картинку
                            break
        context.scene.render.bake.use_selected_to_active = False#отключаем запекание с активного на выбранный
        bpy.ops.object.bake(type="EMIT",use_clear= True) 
        bpy.types.Scene.m_name = bake_target_label_m
        ############################################################################################Вертаем взад
        if(len(cur_obj.data.materials)>0):#если есть материал
            for index, material in enumerate(cur_obj.data.materials):
                #настройка материала
                node_tree = material.node_tree#лезем в ноды
                nodes = node_tree.nodes#и в дерево
                if node_tree:
                    output_node = node_tree.nodes.get("Material Output")#нашли общую ноду ##Material Output
                    principled_node = output_node.inputs[0].links[0].from_node#нашли ноду принциплед
                    emission_input_input = principled_node.inputs[27]#нашли вход emission
                    emission_str = principled_node.inputs[28]
                    emission_str.default_value = def_emi_str#возвращаем стандартную эмиссию
                    if emission_input_input.is_linked:#если есть какоенибудь соединение
                            link = emission_input_input.links[0]  # Берём первое соединение
                            node_tree.links.remove(link)
                            if mats_bc[index]:#соединяем с тем emi что был до запекания
                                node_tree.links.new(mats_bc[index][0].outputs[mats_bc[index][1]],principled_node.inputs[27])#соединяем с emission
        ###########################################################################################
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
                        if node.label == bake_target_label_m:
                            found_node = node
                            node_tree.nodes.remove(found_node)
                        
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            node_tree.nodes.remove(found_node1)

        bake_target_label_ao = context.active_object.simple_bake_image_name + '_AO'
        bake_target_label_uv = bake_target_label_ao + "_uv"
        cur_obj = context.active_object#находим выбранный объект
        #выставление настроек рендера
        cyc_sett = context.scene.cycles
        cyc_sett.device = "GPU"
        bpy.data.scenes["Scene"].render.bake.use_selected_to_active = False
        cyc_sett.use_adaptive_sampling = False
        cyc_sett.use_denoising = False
        cyc_sett.bake_type = 'AO'
        context.scene.render.engine = 'CYCLES'
        bake_resolution = int(context.active_object.simple_bake_resolution)
        found_image = False
        bake_img_ao = None
        for image in bpy.data.images:
            if(image.name == bake_target_label_ao):#если картинка уже существовала
                    img = bpy.data.images.get(bake_target_label_ao)
                    bpy.data.images.remove(img)#удаляем ее
                    found_image = False
                    break
        if(found_image == False):
            bake_img_ao = bpy.ops.image.new(name = bake_target_label_ao,width=bake_resolution,height=bake_resolution,float = True)#создаем картинку
            bpy.data.images[bake_target_label_ao].colorspace_settings.name = "Non-Color"#назначаем нужный цветовой профиль
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
                        if node.label == bake_target_label_ao:
                            found_node = node
                            node_tree.nodes.active = found_node
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            found_node1.uv_map = cur_obj.data.uv_layers.active.name
                            break
                        else:
                            texture_image_my = nodes.new(type="ShaderNodeTexImage")#создаем  ноду картинки
                            texture_image_my.label = bake_target_label_ao
                            uv_map_node  = nodes.new(type="ShaderNodeUVMap")#создаем ноду юв
                            uv_map_node.label = bake_target_label_uv
                            uv_map_node.uv_map = cur_obj.data.uv_layers.active.name#выбираем юв
                            node_tree.links.new(uv_map_node.outputs['UV'],texture_image_my.inputs['Vector'])#соединяем юв и картинку
                            node_tree.nodes.active = texture_image_my#делаем активной
                            node_tree.nodes.active.image = bpy.data.images[bake_target_label_ao]#ставим в выбранную картинку
                            break
        context.scene.render.bake.use_selected_to_active = False#отключаем запекание с активного на выбранный
        bpy.ops.object.bake(type="AO",use_clear= True) 
        bpy.types.Scene.ao_name = bake_target_label_ao
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
                        if node.label == bake_target_label_ao:
                            found_node = node
                            node_tree.nodes.remove(found_node)
                        
                    for node in node_tree.nodes:
                        if node.label == bake_target_label_uv:
                            found_node1 = node
                            node_tree.nodes.remove(found_node1)   

        return {'FINISHED'}

class CombineIMG(bpy.types.Operator):
    bl_idname = "object.combinator"
    bl_label = "Combine RMAO"
    def execute(self, context):

        image_paths_local = {
    "R":bpy.types.Scene.r_name,  # Красный канал
    "G":bpy.types.Scene.m_name,  # Зелёный канал
    "B":bpy.types.Scene.ao_name,  # Синий канал

}
        combined_image = None
        images = {channel: bpy.data.images[name] for channel, name in image_paths_local.items()}
        width, height = images["R"].size
        channels = {}
        for channel, img in images.items():
            pixels = np.array(img.pixels[:])  # Извлекаем пиксели
            channels[channel] = pixels[::4]  # Берём только нужный канал (каждый 4-й элемент)
        result_pixels = np.zeros((width * height * 4,), dtype=np.float32)
        result_pixels[0::4] = channels.get("R", 0)  # Красный
        result_pixels[1::4] = channels.get("G", 0)  # Зелёный
        result_pixels[2::4] = channels.get("B", 0)  # Синий
        result_pixels[3::4] = channels.get("A", 1)  # Альфа (по умолчанию 1)

        found_image = False
        for image in bpy.data.images:
            if(image.name == "CombinedImage"):#если картинка уже существовала
                    img = bpy.data.images.get("CombinedImage")
                    bpy.data.images.remove(img)#удаляем ее
                    found_image = False
                    break
        if(found_image == False):
            combined_image = bpy.data.images.new("CombinedImage", width=width, height=height,float_buffer = True)#создаем картинку
            combined_image.colorspace_settings.name = "Non-Color"#назначаем нужный цветовой профиль
        combined_image.pixels = result_pixels.tolist()

        return {'FINISHED'}

class CombineIMGop(bpy.types.Operator):
    bl_idname = "object.combinatorop"
    bl_label = "Combine RMAOP"
    def execute(self, context):

        image_paths_local = {
    "R":bpy.types.Scene.r_name,  # Красный канал
    "G":bpy.types.Scene.m_name,  # Зелёный канал
    "B":bpy.types.Scene.ao_name,  # Синий канал
    "A":bpy.types.Scene.op_name,  # Альфа канал

}
        combined_image = None
        images = {channel: bpy.data.images[name] for channel, name in image_paths_local.items()}
        width, height = images["R"].size
        channels = {}
        for channel, img in images.items():
            pixels = np.array(img.pixels[:])  # Извлекаем пиксели
            channels[channel] = pixels[::4]  # Берём только нужный канал (каждый 4-й элемент)
        result_pixels = np.zeros((width * height * 4,), dtype=np.float32)
        result_pixels[0::4] = channels.get("R", 0)  # Красный
        result_pixels[1::4] = channels.get("G", 0)  # Зелёный
        result_pixels[2::4] = channels.get("B", 0)  # Синий
        result_pixels[3::4] = channels.get("A", 0)  # Альфа (по умолчанию 1)

        found_image = False
        for image in bpy.data.images:
            if(image.name == "CombinedImageOP"):#если картинка уже существовала
                    img = bpy.data.images.get("CombinedImageOP")
                    bpy.data.images.remove(img)#удаляем ее
                    found_image = False
                    break
        if(found_image == False):
            combined_image = bpy.data.images.new("CombinedImageOP", width=width, height=height,float_buffer = True)#создаем картинку
            combined_image.colorspace_settings.name = "Non-Color"#назначаем нужный цветовой профиль
        combined_image.pixels = result_pixels.tolist()

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
        if bpy.context.active_object in bpy.context.selected_objects:
            #if(bpy.context.active_object.type != "CAMERA" and bpy.context.active_object.type != "LIGHT" and bpy.context.active_object.type != "ARMATURE" and bpy.context.active_object.type != "CURVE" and bpy.context.active_object.type != "EMPTY" and bpy.context.active_object.type != "FONT"):
            if bpy.context.active_object.type == "MESH":
                row = layout.row()
                row.prop(context.active_object, 'simple_bake_resolution', text='Resolution', icon='OBJECT_HIDDEN')
                row = layout.row()
                row.prop(context.active_object, 'simple_bake_image_name', text="Image name", icon= 'NODE_TEXTURE')
                row = layout.row()
                row.prop(context.active_object, 'samples', text="Samples")
                layout.prop(bpy.context.active_object.data.uv_layers,'active_index',text = "UV Map")
                layout.operator("object.rendersettsave", icon='COLLECTION_COLOR_01')
                layout.operator("object.rendersettselfemi", icon='RESTRICT_RENDER_OFF')
                layout.operator("object.rendersettbc", icon='RESTRICT_RENDER_OFF')
                layout.operator("object.rendersettemi", icon='RESTRICT_RENDER_OFF')
                layout.operator("object.rendersettnorm", icon='RESTRICT_RENDER_OFF')
                layout.operator("object.rendersettm", icon='RESTRICT_RENDER_OFF')
                layout.operator("object.rendersettrough", icon='RESTRICT_RENDER_OFF')
                layout.operator("object.rendersettop", icon='RESTRICT_RENDER_OFF')
                layout.operator("object.rendersettao", icon='RESTRICT_RENDER_OFF')
                layout.operator("object.rendersettrma", icon='RESTRICT_RENDER_OFF')
                layout.operator("object.combinator", icon='RESTRICT_RENDER_OFF')
                layout.operator("object.combinatorop", icon='RESTRICT_RENDER_OFF')
                #layout.prop(context.active_object, 'image_to_separate', text="Img_Name")
                #layout.operator("object.separator", icon='RESTRICT_RENDER_OFF')
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
    bpy.utils.register_class(RenderSettSave)
    bpy.utils.register_class(RenderSettEmi)
    bpy.utils.register_class(RenderSettSelfEmi)
    bpy.utils.register_class(RenderSettBC)
    bpy.utils.register_class(RenderSettNorm)
    bpy.utils.register_class(RenderSettM)
    bpy.utils.register_class(RenderSettRough)
    bpy.utils.register_class(RenderSettOp)
    bpy.utils.register_class(RenderSettAO)
    bpy.utils.register_class(RenderSettRMA)
    bpy.utils.register_class(CombineIMG)
    bpy.utils.register_class(CombineIMGop)
    bpy.utils.register_class(OBJECT_PT_CustomPanel)
    bpy.utils.register_class(RenderBC)
    bpy.utils.register_class(RenderEngineCycles)
    bpy.utils.register_class(RenderEngineEevee)
    register_properties()
    
    pass


def unregister():
    bpy.utils.unregister_class(RenderSettSave)
    bpy.utils.unregister_class(RenderSettEmi)
    bpy.utils.unregister_class(RenderSettSelfEmi)
    bpy.utils.unregister_class(RenderSettBC)
    bpy.utils.unregister_class(RenderSettNorm)
    bpy.utils.unregister_class(RenderSettM)
    bpy.utils.unregister_class(RenderSettRough)
    bpy.utils.unregister_class(RenderSettOp)
    bpy.utils.unregister_class(RenderSettAO)
    bpy.utils.unregister_class(RenderSettRMA)
    bpy.utils.unregister_class(CombineIMG)
    bpy.utils.unregister_class(CombineIMGop)
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

    bpy.types.Object.samples = StringProperty(
        name = "Samples",
        default="10"
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
    del bpy.types.Object.samples

    pass

if __name__ == "__main__":
    register()