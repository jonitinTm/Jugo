"""
Capturas de los modelos con Blender (render EEVEE, cielo físico, sol y suelo).

Uso (sin abrir la ventana de Blender):
    blender -b --factory-startup -P herramientas_dev/blender_capturas.py -- <carpeta_salida> [modelo ...]

Genera una imagen por modelo y una hoja de contactos por categoría
(entorno, vegetacion, jugabilidad, herramientas, enemigos, ui).
"""
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELOS = os.path.join(RAIZ, "assets", "modelos")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if "--modelos" in argv:  # carpeta alternativa (p. ej. una copia antigua para comparar)
    i = argv.index("--modelos")
    MODELOS = os.path.abspath(argv[i + 1])
    del argv[i:i + 2]
SALIDA = os.path.abspath(argv[0]) if argv else os.path.join(RAIZ, "docs", "previews", "blender")
FILTRO = set(argv[1:])
os.makedirs(SALIDA, exist_ok=True)
TAM = 640

with open(os.path.join(MODELOS, "indice.json"), encoding="utf-8") as f:
    INDICE = json.load(f)

# Modelos muy grandes o planos: encuadre especial (elevación, distancia extra)
ENCUADRE = {
    "parcela": (55, 0.55), "suelo_cesped": (40, 1.0), "alfombra_hojas": (45, 1.0),
    "calva_tierra": (55, 1.2), "cesped_nuevo": (45, 1.2), "camino_piedra": (50, 1.1),
}
CATEGORIA_UI = "ui"


def limpiar():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def preparar_escena():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [
        e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    sc.render.resolution_x = sc.render.resolution_y = TAM
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 92
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Base Contrast" if True else "None"
    try:
        sc.eevee.taa_render_samples = 64
        sc.eevee.use_shadows = True
        sc.eevee.use_raytracing = True
        sc.eevee.ray_tracing_options.resolution_scale = "1"
        sc.eevee.use_fast_gi = True
    except Exception:
        pass
    # Mundo: cielo físico
    w = bpy.data.worlds.new("cielo")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    try:
        sky.sky_type = "NISHITA"
    except Exception:
        pass
    try:
        sky.sun_elevation = math.radians(38)
        sky.sun_rotation = math.radians(150)
    except Exception:
        pass
    bg.inputs["Strength"].default_value = 0.12
    sc.view_settings.exposure = -0.2
    nt.links.new(sky.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs[0])
    # Sol
    sol = bpy.data.lights.new("sol", "SUN")
    sol.energy = 3.2
    sol.angle = math.radians(4)
    sol.color = (1.0, 0.95, 0.86)
    o = bpy.data.objects.new("sol", sol)
    o.rotation_euler = (math.radians(50), math.radians(-10), math.radians(-35))
    sc.collection.objects.link(o)
    # Suelo neutro
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
    suelo = bpy.context.active_object
    suelo.name = "suelo_captura"
    m = bpy.data.materials.new("suelo_captura")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.22, 0.2, 0.17, 1)
    b.inputs["Roughness"].default_value = 0.95
    suelo.data.materials.append(m)
    return suelo


def importar(nombre):
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(MODELOS, nombre + ".gltf"))
    nuevos = [o for o in bpy.data.objects if o not in antes]
    # Las hojas y pétalos llevan las dos caras en la geometría (Godot pinta la que mira a la
    # cámara), pero Blender descarta esas caras repetidas al importar: sin descarte de caras
    # traseras se ven igual que en el juego.
    for o in nuevos:
        for s in getattr(o, "material_slots", []):
            if s.material is not None:
                s.material.use_backface_culling = False
    return nuevos


def limites(objs):
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        if o.type != "MESH":
            continue
        for c in o.bound_box:
            p = o.matrix_world @ Vector(c)
            mn = Vector(map(min, mn, p))
            mx = Vector(map(max, mx, p))
    return mn, mx


def camara(objs, nombre, categoria):
    mn, mx = limites(objs)
    centro = (mn + mx) / 2
    radio = max((mx - mn).length / 2, 0.05)
    elev, extra = ENCUADRE.get(nombre, (22, 1.0))
    if categoria == CATEGORIA_UI:
        elev = 8
    cam = bpy.data.cameras.new("cam")
    cam.lens = 50
    cam.clip_start = 0.01
    cam.clip_end = 2000
    o = bpy.data.objects.new("cam", cam)
    bpy.context.scene.collection.objects.link(o)
    # Blender: Z arriba; el frente del glTF (+Z) pasa a -Y
    az = math.radians(-32 if categoria != CATEGORIA_UI else -14)
    el = math.radians(elev)
    d = radio / math.sin(math.radians(36) / 2) * 0.82 * extra
    dirv = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    o.location = centro + dirv * d
    o.rotation_euler = (-dirv).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = o
    return o


def render(nombre, categoria, suelo):
    objs = importar(nombre)
    mn, _ = limites(objs)
    suelo.location.z = min(0.0, mn.z) - 0.001
    suelo.hide_render = categoria == CATEGORIA_UI
    cam = camara(objs, nombre, categoria)
    ruta = os.path.join(SALIDA, nombre + ".jpg")
    bpy.context.scene.render.filepath = ruta
    bpy.ops.render.render(write_still=True)
    for o in objs + [cam]:
        bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.cameras):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)
    return ruta


def hoja_contactos(nombres, ruta, columnas=4):
    import OpenImageIO as oiio
    imgs = []
    for n in nombres:
        p = os.path.join(SALIDA, n + ".jpg")
        if os.path.exists(p):
            buf = oiio.ImageBuf(p)
            imgs.append((n, buf.get_pixels(oiio.FLOAT)))
    if not imgs:
        return
    t = 320
    filas = math.ceil(len(imgs) / columnas)
    hoja = np.ones((filas * t, columnas * t, 3), np.float32) * 0.12
    for i, (n, px) in enumerate(imgs):
        px = px[:, :, :3]
        h, w = px.shape[:2]
        paso = h // t
        peq = px[: t * paso, : t * paso].reshape(t, paso, t, paso, 3).mean((1, 3))
        r, c = divmod(i, columnas)
        hoja[r * t:(r + 1) * t, c * t:(c + 1) * t] = peq
        hoja[r * t:(r + 1) * t, c * t:c * t + 2] = 0.12
        hoja[r * t:r * t + 2, c * t:(c + 1) * t] = 0.12
    spec = oiio.ImageSpec(hoja.shape[1], hoja.shape[0], 3, oiio.FLOAT)
    out = oiio.ImageOutput.create(ruta)
    spec.attribute("Compression", "jpeg:90")
    out.open(ruta, spec)
    out.write_image(hoja)
    out.close()


def main():
    limpiar()
    suelo = preparar_escena()
    por_cat = {}
    for nombre, info in INDICE.items():
        por_cat.setdefault(info["categoria"], []).append(nombre)
        if FILTRO and nombre not in FILTRO:
            continue
        print(">> render", nombre, flush=True)
        render(nombre, info["categoria"], suelo)
    if not FILTRO:
        for cat, nombres in por_cat.items():
            hoja_contactos(nombres, os.path.join(SALIDA, "_hoja_" + cat + ".jpg"))


main()
