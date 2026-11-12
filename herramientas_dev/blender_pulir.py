"""
Pulido de los modelos con Blender: biselado de aristas duras y normales limpias.

Se ejecuta DESPUÉS de generar_modelos.py, sin abrir la ventana de Blender:
    blender -b --factory-startup -P herramientas_dev/blender_pulir.py -- [modelo ...] [--forzar]

Qué hace con cada assets/modelos/<modelo>.gltf:
  1. Lo importa (nodos, pivotes y materiales tal cual).
  2. En las piezas "duras" (madera, metal, plástico, UI...) une los vértices repetidos y bisela
     las aristas vivas (> 35°) con 2 segmentos: los bordes atrapan la luz y dejan de verse
     como cajas de cartón. El ancho del bisel se ajusta al tamaño del modelo.
  3. Recalcula las normales de esas piezas (suaves en el bisel, duras en las caras planas) y
     respeta las normales hechas a mano del resto (hojas, briznas, cartas de follaje...).
  4. Lo exporta a una carpeta temporal y monta el .gltf final (mismo formato que el original,
     un solo archivo con los datos dentro): piezas biseladas de Blender + todo lo demás del
     original. Actualiza los triángulos en indice.json.

Un modelo ya pulido (exportado por Blender) se salta salvo con --forzar: así se puede
volver a ejecutar sin biselar dos veces. Si regeneras un modelo con generar_modelos.py,
vuelve a pulirlo.
"""
import base64
import json
import math
import os
import shutil
import sys
import tempfile

import bmesh
import bpy
import numpy as np
from mathutils import Vector

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELOS = os.path.join(RAIZ, "assets", "modelos")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FORZAR = "--forzar" in argv
FILTRO = {a for a in argv if not a.startswith("--")}

# Materiales que NO se tocan: follaje con alfa, briznas, pétalos, suelos y piezas de doble cara
NO_BISELAR = {
    "brizna", "hierba", "hierba_clara", "hierba_osc", "seco", "hojas_verde", "hojas_osc", "hojas_otono",
    "hoja_ancha", "hoja_ancha_osc", "hojas_caidas", "hoja_diente", "hoja_cardo", "trebol", "fronda",
    "flores_blancas", "petalo_amarillo", "petalo_amarillo_osc", "petalo_rojo", "petalo_rojo_osc",
    "cesped", "cesped_parche", "calva", "tierra", "tierra_suelo", "hojarasca", "asfalto", "ala",
    "girasol_centro", "anillos", "musgo",
    # piezas orgánicas: ya son suaves; sus aristas "vivas" son de la teselación, no de diseño
    "caracol_cuerpo", "caracol_cuerpo_osc", "concha", "concha_osc", "caparazon", "caparazon_brillo",
    "bicho_osc", "avispa_amarilla", "avispa_negra", "ojo_blanco", "pupila", "ojo_avispa",
    "seta_roja", "seta_crema", "petalo_blanco", "mora", "tronco", "tronco_osc", "zarza", "roca",
    "hoja", "hoja_osc", "hoja_clara", "centro_flor", "plastico_negro", "plastico_negro_brillo",
    "saco", "saco_osc", "guante", "guante_osc", "puno_guante", "corteza_clara",
}
# Modelos que no se pulen (suelos enormes o planos: no ganan nada y pesan mucho)
SALTAR = {"parcela", "calva_tierra", "cesped_nuevo", "alfombra_hojas", "suelo_cesped"}
# Materiales que no se biselan en un modelo concreto (piezas pequeñas repetidas: muchos triángulos
# para un cambio que no se ve)
NO_BISELAR_EN = {"moneda": {"oro_osc", "oro_claro"}, "zarza": {"otono_rojo"}, "amapola_gigante": {"negro"},
                 "matorral": {"otono_rojo"}, "tocon": {"madera_clara"}}
ANGULO = math.radians(35)


def es_pulido(ruta):
    with open(ruta, encoding="utf-8") as f:
        cabeza = f.read(400)
    return "Blender" in cabeza


def limpiar():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def tam_modelo(objs):
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        if o.type == "MESH":
            for c in o.bound_box:
                p = o.matrix_world @ Vector(c)
                mn = Vector(map(min, mn, p))
                mx = Vector(map(max, mx, p))
    return (mx - mn).length


def pulir_objeto(o, ancho, excluir=()):
    me = o.data
    if not me.polygons:
        return 0
    mats = [s.material.name.split(".")[0] if s.material else "" for s in o.material_slots]
    duro = [m not in NO_BISELAR and m not in excluir for m in mats]
    if not any(duro):
        return 0
    # normales originales por esquina (las de glTF: hechas a mano) en un atributo que bmesh conserva
    orig = [0.0] * (len(me.loops) * 3)
    for i, n in enumerate(me.corner_normals):
        orig[i * 3:i * 3 + 3] = n.vector
    if "n_orig" in me.attributes:
        me.attributes.remove(me.attributes["n_orig"])
    at = me.attributes.new("n_orig", "FLOAT_VECTOR", "CORNER")
    at.data.foreach_set("vector", orig)

    bm = bmesh.new()
    bm.from_mesh(me)
    caras = [f for f in bm.faces if f.material_index < len(duro) and duro[f.material_index]]
    for f in caras:
        f.tag = True
    verts = list({v for f in caras for v in f.verts})
    bmesh.ops.remove_doubles(bm, verts=verts, dist=1e-5)
    # las caras planas vienen en abanicos de triángulos finos: se funden en polígonos limpios
    # (si no, el bisel se recorta a casi nada para no solaparse)
    caras = [f for f in bm.faces if f.tag]
    ar = list({e for f in caras for e in f.edges if all(g.tag for g in e.link_faces)})
    if ar:
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(0.5), use_dissolve_boundaries=False,
                                 verts=[], edges=ar, delimit={"MATERIAL", "UV"})
    for f in bm.faces:
        f.tag = f.material_index < len(duro) and duro[f.material_index]
    bm.edges.ensure_lookup_table()
    aristas = []
    for e in bm.edges:
        if len(e.link_faces) != 2:
            continue
        f0, f1 = e.link_faces
        if not (f0.tag and f1.tag) or f0.material_index != f1.material_index:
            continue
        if e.calc_face_angle(0.0) > ANGULO:
            aristas.append(e)
    if aristas:
        antes = len(bm.faces)
        bmesh.ops.bevel(bm, geom=aristas, offset=ancho, offset_type="OFFSET", segments=2, profile=0.5,
                        affect="EDGES", clamp_overlap=True, loop_slide=True, mark_sharp=False,
                        material=-1)  # -1: las caras del bisel heredan el material vecino
        if "--depurar" in argv:
            from collections import Counter
            print(f"   {o.name}: caras {antes} -> {len(bm.faces)}", Counter(f.material_index for f in bm.faces), mats)
    # las caras nuevas del bisel heredan el material; las marcamos duras para la normal recalculada
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(me)
    bm.free()

    # normales: auto-suavizado por ángulo para las piezas duras, originales para el resto
    me.normals_split_custom_set([(0.0, 0.0, 0.0)] * len(me.loops))  # sin normales a mano
    if hasattr(me, "free_normals_split"):
        pass
    for e in me.edges:
        e.use_edge_sharp = False
    # aristas vivas = ángulo entre caras > ANGULO
    bm = bmesh.new()
    bm.from_mesh(me)
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0.0) > ANGULO) and len(e.link_faces) == 2
    bm.to_mesh(me)
    bm.free()
    try:
        bpy.context.view_layer.objects.active = o
        with bpy.context.temp_override(object=o, active_object=o, selected_objects=[o]):
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception:
        pass
    auto = [Vector(n.vector) for n in me.corner_normals]
    org = [0.0] * (len(me.loops) * 3)
    me.attributes["n_orig"].data.foreach_get("vector", org)
    final = []
    for p in me.polygons:
        d = p.material_index < len(duro) and duro[p.material_index]
        for li in p.loop_indices:
            if d:
                final.append(tuple(auto[li]))
            else:
                v = Vector(org[li * 3:li * 3 + 3])
                final.append(tuple(v.normalized()) if v.length > 1e-6 else tuple(auto[li]))
    me.normals_split_custom_set(final)
    me.attributes.remove(me.attributes["n_orig"])
    return len(aristas)


def exportar(ruta):
    kw = dict(filepath=ruta, export_format="GLTF_SEPARATE", export_keep_originals=True, export_yup=True,
              export_apply=False, export_texcoords=True, export_normals=True, export_tangents=False,
              export_materials="EXPORT", export_cameras=False, export_lights=False, export_extras=False,
              export_animations=False, use_selection=False)
    try:
        bpy.ops.export_scene.gltf(**kw, export_attributes=False)
    except TypeError:
        bpy.ops.export_scene.gltf(**kw)


# ---------------------------------------------------------------- fusión de glTF
# Blender, al importar, descarta las caras duplicadas con el giro invertido (las hojas llevan las
# dos caras con las mismas normales a propósito). Por eso el archivo final se monta así: la
# estructura, los materiales y las piezas blandas salen del glTF original, y solo las piezas
# biseladas salen de Blender.
_TIPOS = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}
_COMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def _cargar(ruta):
    with open(ruta, encoding="utf-8") as f:
        g = json.load(f)
    bufs = []
    for b in g.get("buffers", []):
        uri = b["uri"]
        if uri.startswith("data:"):
            bufs.append(base64.b64decode(uri.split(",", 1)[1]))
        else:
            with open(os.path.join(os.path.dirname(ruta), uri), "rb") as fb:
                bufs.append(fb.read())
    return g, bufs


def _leer(g, bufs, i):
    a = g["accessors"][i]
    bv = g["bufferViews"][a["bufferView"]]
    dt = np.dtype(_TIPOS[a["componentType"]])
    nc = _COMP[a["type"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    paso = bv.get("byteStride", dt.itemsize * nc)
    raw = np.frombuffer(bufs[bv["buffer"]], np.uint8, count=paso * (a["count"] - 1) + dt.itemsize * nc, offset=off)
    if paso == dt.itemsize * nc:
        arr = raw.view(dt).reshape(a["count"], nc) if nc > 1 else raw.view(dt)
    else:
        arr = np.lib.stride_tricks.as_strided(raw.view(dt), (a["count"], nc), (paso, dt.itemsize))
    return np.array(arr)


def materiales_doble_cara(ruta):
    """Materiales con triángulos repetidos (las dos caras): no pueden pasar por Blender."""
    g, bufs = _cargar(ruta)
    res = set()
    for me in g["meshes"]:
        for p in me["primitives"]:
            idx = _leer(g, bufs, p["indices"]).astype(np.int64).reshape(-1, 3)
            idx = idx[(idx[:, 0] != idx[:, 1]) & (idx[:, 1] != idx[:, 2]) & (idx[:, 0] != idx[:, 2])]

            def canon(t):  # misma orientación, empezando por el índice menor
                r = np.argmin(t, axis=1)[:, None]
                return np.take_along_axis(t, (r + np.arange(3)[None, :]) % 3, axis=1)
            fwd = {tuple(x) for x in canon(idx)}
            rev = canon(idx[:, [0, 2, 1]])
            if sum(tuple(x) in fwd for x in rev) > 0.05 * len(idx):
                res.add(g["materials"][p["material"]]["name"])
    return res


def fusionar(ruta_orig, ruta_blender, duros):
    B, bb = _cargar(ruta_orig)
    A, ab = _cargar(ruta_blender)
    nombre_mat_A = [m.get("name", "").split(".")[0] for m in A.get("materials", [])]
    prims_A = {}
    for me in A["meshes"]:
        for p in me["primitives"]:
            if "material" in p:
                prims_A[(me["name"], nombre_mat_A[p["material"]])] = p
    if "--depurar" in argv:
        print("   prims_A:", {k: A["accessors"][p["indices"]]["count"] // 3 for k, p in prims_A.items()})
    nuevo = bytearray()
    accs, vistas = [], []

    def poner(arr, comp, tipo, destino, limites=False):
        while len(nuevo) % 4:
            nuevo.append(0)
        arr = np.ascontiguousarray(arr)
        datos = arr.tobytes()
        vistas.append({"buffer": 0, "byteOffset": len(nuevo), "byteLength": len(datos), "target": destino})
        nuevo.extend(datos)
        a = {"bufferView": len(vistas) - 1, "componentType": comp, "count": len(arr), "type": tipo}
        if limites:
            a["min"], a["max"] = [float(x) for x in arr.min(0)], [float(x) for x in arr.max(0)]
        accs.append(a)
        return len(accs) - 1

    tris = 0
    for me in B["meshes"]:
        for p in me["primitives"]:
            mat = B["materials"][p["material"]]["name"]
            fuente, gb, bufs = p, B, bb
            if mat in duros and (me["name"], mat) in prims_A:
                fuente, gb, bufs = prims_A[(me["name"], mat)], A, ab
            at = fuente["attributes"]
            pos = _leer(gb, bufs, at["POSITION"]).astype(np.float32)
            nor = _leer(gb, bufs, at["NORMAL"]).astype(np.float32)
            uv = _leer(gb, bufs, at["TEXCOORD_0"]).astype(np.float32) if "TEXCOORD_0" in at else np.zeros((len(pos), 2), np.float32)
            idx = _leer(gb, bufs, fuente["indices"]).astype(np.uint32).ravel()
            tris += len(idx) // 3
            p["attributes"] = {"POSITION": poner(pos, 5126, "VEC3", 34962, True),
                               "NORMAL": poner(nor, 5126, "VEC3", 34962),
                               "TEXCOORD_0": poner(uv, 5126, "VEC2", 34962)}
            p["indices"] = poner(idx, 5125, "SCALAR", 34963)
    B["accessors"], B["bufferViews"] = accs, vistas
    B["buffers"] = [{"byteLength": len(nuevo),
                     "uri": "data:application/octet-stream;base64," + base64.b64encode(bytes(nuevo)).decode()}]
    B["asset"]["generator"] = "Jugo generar_modelos.py + blender_pulir.py (Blender)"
    with open(ruta_orig, "w", encoding="utf-8") as f:
        json.dump(B, f, separators=(",", ":"))
    return tris


def main():
    with open(os.path.join(MODELOS, "indice.json"), encoding="utf-8") as f:
        indice = json.load(f)
    for nombre in indice:
        if FILTRO and nombre not in FILTRO:
            continue
        ruta = os.path.join(MODELOS, nombre + ".gltf")
        if nombre in SALTAR or not os.path.exists(ruta):
            continue
        if es_pulido(ruta) and not FORZAR:
            print(f"   {nombre}: ya pulido (usa --forzar)")
            continue
        limpiar()
        bpy.ops.import_scene.gltf(filepath=ruta)
        objs = list(bpy.data.objects)
        diag = tam_modelo(objs)
        ancho = min(0.025, max(0.0015, 0.0042 * diag))
        biseladas = 0
        duros = set()
        excluir = materiales_doble_cara(ruta) | NO_BISELAR_EN.get(nombre, set())
        for o in objs:
            if o.type == "MESH":
                biseladas += pulir_objeto(o, ancho, excluir)
                duros |= {s.material.name.split(".")[0] for s in o.material_slots
                          if s.material and s.material.name.split(".")[0] not in NO_BISELAR | excluir}
        if not biseladas:
            print(f"   {nombre}: sin aristas duras, se queda como está")
            continue
        if "--depurar" in argv:
            print("   excluir:", sorted(excluir), "duros:", sorted(duros))
        tmp = tempfile.mkdtemp(prefix="jugo_pulir_")
        try:
            exportar(os.path.join(tmp, nombre + ".gltf"))
            tris = fusionar(ruta, os.path.join(tmp, nombre + ".gltf"), duros)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        indice[nombre]["tris"] = tris
        print(f">> {nombre:18s} bisel {ancho * 1000:5.1f} mm  {biseladas:5d} aristas  {tris:7d} tris", flush=True)
    with open(os.path.join(MODELOS, "indice.json"), "w", encoding="utf-8") as f:
        json.dump(indice, f, indent=1)


main()
