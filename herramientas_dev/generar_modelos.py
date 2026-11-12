#!/usr/bin/env python3
"""
Generador procedural de los modelos de "Jugo" (juego incremental de jardín).

Los modelos se construyen por código (primitivas, tubos, superficies de
revolución, tiras curvas para hojas y briznas, cartas de follaje...) con UVs,
normales suaves y materiales PBR que usan las texturas de
assets/modelos/texturas (ver generar_texturas.py). Se exportan a .gltf, que
Godot 4 importa directamente; las texturas son archivos externos compartidos
por todos los modelos.

Uso:
    pip install trimesh numpy scipy pillow
    python3 herramientas_dev/generar_texturas.py
    python3 herramientas_dev/generar_modelos.py            # genera todo
    python3 herramientas_dev/generar_modelos.py casa zarza # solo esos

Convenciones:
    - Unidades en metros, eje Y hacia arriba; el frente mira hacia +Z.
    - Origen en la base (en el suelo); herramientas: en el agarre; UI: centro.
    - Las piezas animables (ruedas, tapas, alas, patas, puertas...) son nodos
      hijos con su origen en el punto de giro.
"""
import base64
import json
import math
import os
import sys

import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix, translation_matrix

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "assets", "modelos")
TEXTURAS = os.path.join(SALIDA, "texturas")
UP = np.array([0.0, 1.0, 0.0])
# Multiplicador de lados de las piezas redondas (tubos, tornos, discos, cilindros): más = más suave
DETALLE = 1.5


def _lados(n, minimo=3):
    return max(minimo, int(round(n * DETALLE)))

# --------------------------------------------------------------------------
# Paleta (colores sRGB en hex)
# --------------------------------------------------------------------------
PALETA = {
    # casa
    "estuco": "#EADFC4",
    "madera": "#B9783F", "madera_clara": "#D2A06A", "madera_osc": "#74472A",
    "tejado": "#5F5A72", "tejado_osc": "#46425A",
    "piedra": "#B3ACA2", "piedra_osc": "#8C857C", "roca": "#A9A49B",
    "cristal": "#31475A", "cristal_luz": "#7FA3BF",
    "metal": "#A7AFB6", "metal_osc": "#5D656C",
    # vegetación
    "hoja": "#5E9E3A", "hoja_clara": "#8DBF4A", "hoja_osc": "#3F7A2E", "hoja_muy_osc": "#2C5A28",
    "hierba": "#7DB443", "hierba_clara": "#A9CF57", "hierba_osc": "#4E8A30",
    "seco": "#CDB46A", "tierra": "#7A5236",
    "tronco": "#8A5A36", "tronco_osc": "#5E3C24", "corteza_clara": "#B88B5C",
    "otono_naranja": "#E8822E", "otono_amarillo": "#F2B33D", "otono_rojo": "#C9452E", "otono_marron": "#A0612E",
    "petalo_amarillo": "#F8C61E", "petalo_amarillo_osc": "#EDA512",
    "petalo_rojo": "#DC3028", "petalo_rojo_osc": "#B02222",
    "petalo_blanco": "#F4F1E6", "centro_flor": "#5A3A1E", "negro": "#1E1C22",
    "zarza": "#4A3B4E", "mora": "#3A1D4A",
    "seta_roja": "#C9342B", "seta_crema": "#EFE3C8", "musgo": "#55782E",
    # materiales con textura propia (el color es solo orientativo)
    "hojas_verde": "#5E9E3A", "hojas_osc": "#3F7A2E", "hojas_otono": "#E8822E",
    "hoja_ancha": "#4F8A34", "hoja_ancha_osc": "#3A6A2A", "hojas_caidas": "#E8822E",
    "hojarasca": "#C98A3A", "girasol_centro": "#4A2E14", "anillos": "#C9A070",
    "calva": "#6E4E34", "cesped_parche": "#6FA03A",
    "hoja_diente": "#4A8A34", "hoja_cardo": "#58805C", "trebol": "#468C3A", "fronda": "#3E7A30",
    "flores_blancas": "#ECECDE",
    "cesped": "#5E8A30", "tierra_suelo": "#6E4E34", "asfalto": "#3A3A3E",
    # jugabilidad
    "saco": "#C8A66E", "saco_osc": "#9A7B4A",
    "plastico_negro": "#25252B", "plastico_negro_brillo": "#3A3A44", "lazo_amarillo": "#F2C230",
    "contenedor": "#3A7A4E", "contenedor_osc": "#2A5A3A",
    "camion": "#E8762C", "camion_osc": "#B9561D", "blanco": "#F0EEE8",
    "goma": "#232327", "faro": "#FFE6A0", "rojo_luz": "#D8352E",
    "oro": "#F2C14E", "oro_osc": "#C9922B", "oro_claro": "#FBE08A",
    # herramientas
    "guante": "#7FB8A0", "guante_osc": "#5C9580", "puno_guante": "#E6D9B8",
    "acero": "#C9D0D6", "acero_osc": "#7E878F", "mango_rojo": "#C8372D",
    "mango_negro": "#2E2E35", "naranja_motor": "#EE7A22", "verde_rastrillo": "#58A85A",
    "amarillo_hilo": "#F5D33A", "rojo_cortacesped": "#D8402E", "rojo_cortacesped_osc": "#A82E22",
    # basurero
    "piel": "#E8B48A", "piel_osc": "#C98E66", "pelo": "#4A3324", "chaleco": "#F07A1E", "reflectante": "#E8EEF0",
    "pantalon": "#2E4A6E", "bota": "#2A2420", "gorra": "#3A7A4E",
    # bichos
    "caparazon": "#2F62A8", "caparazon_brillo": "#5E93D6", "bicho_osc": "#232533",
    "ojo_blanco": "#FFFFFF", "pupila": "#141418",
    "caracol_cuerpo": "#B9C46C", "caracol_cuerpo_osc": "#97A355",
    "concha": "#C98A4B", "concha_osc": "#9C6334",
    "avispa_amarilla": "#F4C430", "avispa_negra": "#26232A", "ala": "#DDEFFF", "ojo_avispa": "#7A1E2A",
    # ui
    "ui_madera": "#B8773C", "ui_madera_clara": "#E0AE72", "ui_madera_osc": "#6E4122",
    "ui_verde": "#5DBB4F", "ui_verde_osc": "#3A7F33", "ui_papel": "#F3E6C8",
    "ui_cuerda": "#B79B6B", "ui_fondo_barra": "#3A2A1E",
}

# Definición de materiales. Por defecto: textura "liso" teñida con el color de la paleta.
#   tex/normal: texturas · esc: repeticiones por metro · tinte: "media" (tiñe hasta el color
#   de la paleta), None (textura tal cual) o (r,g,b) lineal · fijo: UV sin orientar a la pieza
_MADERA = dict(tex="madera", normal="madera_n", esc=1.1, rug=0.7)
_PIEDRA = dict(tex="piedra_muro", normal="piedra_muro_n", esc=0.8, fijo=True, tinte=None, rug=0.9)
_TEJA = dict(tex="tejas", normal="tejas_n", esc=0.62, fijo=True, tinte=None, rug=0.8)
_CORTEZA = dict(tex="corteza", normal="corteza_n", esc=0.6, rug=0.95)
_BRIZNA = dict(tex="brizna", rug=0.6, esc=1.0, tinte=None, alias="brizna")
_PETALO = dict(tex="petalo", rug=0.55, tinte="color")
_HOJAS = dict(alfa="MASK", tinte=None, rug=0.6)
MATS = {
    "estuco": dict(tex="estuco", normal="estuco_n", esc=0.45, fijo=True, tinte=None, rug=0.95),
    "madera": _MADERA, "madera_clara": _MADERA, "madera_osc": _MADERA, "corteza_clara": _MADERA,
    "ui_madera": _MADERA, "ui_madera_clara": _MADERA, "ui_madera_osc": _MADERA,
    "tejado": _TEJA, "tejado_osc": dict(_TEJA, tinte=(0.6, 0.6, 0.62)),
    "piedra": _PIEDRA, "piedra_osc": dict(_PIEDRA, tinte=(0.62, 0.6, 0.58)),
    "roca": dict(tex="roca", normal="roca_n", esc=0.6, tinte=None, rug=0.95, fijo=True),
    "tronco": dict(_CORTEZA, tinte=None), "tronco_osc": dict(_CORTEZA, tinte=(0.6, 0.58, 0.55)),
    "zarza": dict(_CORTEZA, tinte=(0.75, 0.6, 0.72), esc=2.0),
    # los 4 tonos de brizna comparten material (menos llamadas de dibujado): la textura
    # tiene 4 columnas y "col" elige cuál
    "hierba": dict(_BRIZNA, col=0), "hierba_clara": dict(_BRIZNA, col=1),
    "hierba_osc": dict(_BRIZNA, col=2), "seco": dict(_BRIZNA, col=3),
    "petalo_amarillo": _PETALO, "petalo_amarillo_osc": _PETALO, "petalo_rojo": _PETALO,
    "petalo_rojo_osc": _PETALO, "petalo_blanco": dict(rug=0.6),
    "hojas_verde": dict(_HOJAS, tex="hojas_verde"),
    "hojas_osc": dict(_HOJAS, tex="hojas_verde", tinte=(0.62, 0.74, 0.58)),
    "hojas_otono": dict(_HOJAS, tex="hojas_otono"),
    "hoja_ancha": dict(_HOJAS, tex="hoja_ancha"),
    "hoja_ancha_osc": dict(_HOJAS, tex="hoja_ancha", tinte=(0.6, 0.7, 0.58)),
    "hojas_caidas": dict(_HOJAS, tex="hojas_caidas"),
    "hoja_diente": dict(_HOJAS, tex="hoja_diente"), "hoja_cardo": dict(_HOJAS, tex="hoja_cardo"),
    "trebol": dict(_HOJAS, tex="trebol"), "fronda": dict(_HOJAS, tex="fronda"),
    "flores_blancas": dict(_HOJAS, tex="flores_blancas"),
    "hojarasca": dict(tex="hojarasca", normal="hojarasca_n", esc=0.7, tinte=None, fijo=True, rug=0.9),
    "girasol_centro": dict(tex="girasol_centro", tinte=None, rug=0.9),
    "anillos": dict(tex="anillos", tinte=None, rug=0.8),
    "cesped": dict(tex="cesped", normal="cesped_n", esc=0.3, tinte=None, fijo=True, rug=1.0),
    "calva": dict(tex="calva", alfa="BLEND", tinte=None, rug=1.0),
    "cesped_parche": dict(tex="cesped_parche", alfa="BLEND", tinte=None, rug=1.0),
    "tierra": dict(tex="tierra", normal="tierra_n", esc=0.6, tinte=None, fijo=True, rug=1.0),
    "tierra_suelo": dict(tex="tierra", normal="tierra_n", esc=0.4, tinte=None, fijo=True, rug=1.0),
    "asfalto": dict(tex="asfalto", normal="asfalto_n", esc=0.3, tinte=None, fijo=True, rug=0.9),
    "saco": dict(normal="arrugas_n", esc=4.0, rug=0.95), "saco_osc": dict(rug=0.9),
    "plastico_negro": dict(normal="arrugas_n", esc=2.5, rug=0.3),
    "plastico_negro_brillo": dict(normal="arrugas_n", esc=2.5, rug=0.25),
    "cristal": dict(tex=None, rug=0.08, met=0.2), "cristal_luz": dict(tex=None, rug=0.08, met=0.2),
    "metal": dict(met=0.5, rug=0.4), "metal_osc": dict(met=0.5, rug=0.45),
    "acero": dict(met=0.6, rug=0.28), "acero_osc": dict(met=0.5, rug=0.4),
    "oro": dict(met=0.45, rug=0.3), "oro_osc": dict(met=0.45, rug=0.35), "oro_claro": dict(met=0.35, rug=0.3),
    "caparazon": dict(met=0.3, rug=0.2), "caparazon_brillo": dict(met=0.3, rug=0.15),
    "ala": dict(tex=None, rug=0.2, alfa="BLEND", opacidad=0.45, doble=True),
    "ojo_blanco": dict(tex=None, rug=0.15), "pupila": dict(tex=None, rug=0.1),
    "faro": dict(tex=None, rug=0.2), "mora": dict(tex=None, rug=0.25),
    "camion": dict(rug=0.4), "camion_osc": dict(rug=0.5), "blanco": dict(rug=0.45),
    "contenedor": dict(rug=0.5), "contenedor_osc": dict(rug=0.55),
    "goma": dict(rug=0.9), "naranja_motor": dict(rug=0.4), "mango_rojo": dict(rug=0.45),
    "caracol_cuerpo": dict(rug=0.3), "caracol_cuerpo_osc": dict(rug=0.3),
    "concha": dict(rug=0.35), "concha_osc": dict(rug=0.35),
    "seta_roja": dict(rug=0.35), "avispa_amarilla": dict(rug=0.5), "avispa_negra": dict(rug=0.4),
    "musgo": dict(tex="cesped", normal="cesped_n", esc=1.6, fijo=True, rug=1.0),
    "rojo_cortacesped": dict(rug=0.35), "rojo_cortacesped_osc": dict(rug=0.4),
    "piel": dict(rug=0.6), "piel_osc": dict(rug=0.6), "pelo": dict(rug=0.8),
    "chaleco": dict(normal="arrugas_n", esc=3.0, rug=0.7), "reflectante": dict(rug=0.2, met=0.3),
    "pantalon": dict(normal="arrugas_n", esc=3.0, rug=0.85), "bota": dict(rug=0.6), "gorra": dict(rug=0.8),
}

with open(os.path.join(TEXTURAS, "medias.json")) as _f:
    MEDIAS = json.load(_f)


def hex_a_lineal(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def def_material(nombre):
    d = dict(tex="liso", normal=None, esc=1.0, rug=0.8, met=0.0, alfa=None, doble=False,
             tinte="media", fijo=False, opacidad=1.0)
    d.update(MATS.get(nombre, {}))
    col = hex_a_lineal(PALETA[nombre])
    if d["tex"] is None or d["tinte"] == "color":
        d["factor"] = col
    elif d["tinte"] == "media":
        d["factor"] = [min(1.0, c / m) for c, m in zip(col, MEDIAS[d["tex"]])]
    elif d["tinte"] is None:
        d["factor"] = [1.0, 1.0, 1.0]
    else:
        d["factor"] = list(d["tinte"])
    return d


# --------------------------------------------------------------------------
# Mallas: trimesh con vértices sin compartir + UV; metadatos:
#   suave: ángulo de suavizado · N: normales explícitas · circ: perímetro (UV cilíndrico)
#   uv_fijo: UV alternativo no orientado a la pieza (muros, tejados, suelos)
# --------------------------------------------------------------------------
def _malla(V, UV, suave=40.0, N=None, circ=None, uv_fijo=None):
    V = np.asarray(V, float).reshape(-1, 3)
    m = trimesh.Trimesh(vertices=V, faces=np.arange(len(V)).reshape(-1, 3), process=False)
    m.visual = trimesh.visual.TextureVisuals(uv=np.asarray(UV, float).reshape(-1, 2))
    m.metadata["suave"] = suave
    if N is not None:
        m.metadata["N"] = np.asarray(N, float).reshape(-1, 3)
    if circ:
        m.metadata["circ"] = circ
    if uv_fijo is not None:
        m.metadata["uv_fijo"] = uv_fijo
    return m


def _uv_planar(tri, fn, fijo):
    e = tri.reshape(-1, 3).max(0) - tri.reshape(-1, 3).min(0)
    eje = np.abs(fn).argmax(1)
    uv = np.zeros((len(tri), 3, 2))
    for a, (iu, iv) in {0: (2, 1), 1: (0, 2), 2: (0, 1)}.items():
        if not fijo and e[iu] > e[iv] * 1.01:
            iu, iv = iv, iu  # la veta (V) sigue el lado largo de la pieza
        s = eje == a
        uv[s, :, 0] = tri[s][:, :, iu]
        uv[s, :, 1] = tri[s][:, :, iv]
    return uv.reshape(-1, 2)


def _de_trimesh(tm, suave=40.0):
    tri = np.asarray(tm.vertices)[np.asarray(tm.faces)]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    return _malla(tri, _uv_planar(tri, fn, False), suave, uv_fijo=_uv_planar(tri, fn, True))


def hull(puntos, suave=40.0):
    return _de_trimesh(trimesh.convex.convex_hull(np.asarray(puntos, dtype=float)), suave)


def caja(sx, sy, sz):
    return _de_trimesh(trimesh.creation.box((sx, sy, sz)))


def cilindro(r0, r1, h, n=8, rot=0.0):
    """Tronco de cono a lo largo de Y, base en y=0."""
    if n >= 5:
        n = max(_lados(n), 16)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n + rot
        pts.append((r0 * math.cos(a), 0, r0 * math.sin(a)))
        if r1 > 1e-5:
            pts.append((r1 * math.cos(a), h, r1 * math.sin(a)))
    if r1 <= 1e-5:
        pts.append((0, h, 0))
    tm = trimesh.convex.convex_hull(np.asarray(pts))
    if n < 5:
        return _de_trimesh(tm)
    tri = np.asarray(tm.vertices)[np.asarray(tm.faces)]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    circ = 2 * math.pi * max(r0, r1)
    ang = np.arctan2(tri[..., 2], tri[..., 0])
    eje = np.hypot(tri[..., 0], tri[..., 2]) < 1e-6
    for k in range(3):
        ang[:, k] = np.where(eje[:, k], np.where(eje[:, (k + 1) % 3], ang[:, (k + 2) % 3], ang[:, (k + 1) % 3]), ang[:, k])
    amp = ang.max(1) - ang.min(1) > math.pi
    ang[amp] = np.where(ang[amp] < 0, ang[amp] + 2 * math.pi, ang[amp])
    uv = np.stack([ang / (2 * math.pi) * circ, tri[..., 1]], -1)
    tapa = np.abs(fn[:, 1]) > 0.9
    uv[tapa] = tri[tapa][:, :, [0, 2]]
    return _malla(tri, uv, 50.0, circ=circ)


def bola(r, sub=1, jitter=0.0, semilla=0, escala=(1, 1, 1)):
    m = trimesh.creation.icosphere(subdivisions=min(sub + 1, 3) if sub >= 0 else 0, radius=r)
    if jitter > 0:
        rng = np.random.default_rng(semilla)
        m.vertices = m.vertices * (1 + rng.uniform(-jitter, jitter, size=(len(m.vertices), 1)))
    m.vertices = m.vertices * np.asarray(escala)
    return _de_trimesh(m, 180.0)


def bola_ruido(r, sub=3, amp=0.2, semilla=0, escala=(1, 1, 1), cortes=0):
    """Esfera deformada con ruido coherente (y planos de corte) para rocas y montones."""
    rng = np.random.default_rng(semilla)
    m = trimesh.creation.icosphere(subdivisions=sub, radius=1.0)
    d = np.asarray(m.vertices)
    desp = np.zeros(len(d))
    for k in range(7):
        f = rng.normal(0, 1, 3) * rng.uniform(1.2, 4.0)
        desp += np.sin(d @ f + rng.uniform(0, 6.28)) / (1 + k * 0.5)
    v = d * (1 + amp * desp / 2.5)[:, None]
    for _ in range(cortes):
        n = rng.normal(0, 1, 3)
        n /= np.linalg.norm(n)
        c = rng.uniform(0.6, 0.85)
        exc = np.maximum(v @ n - c, 0)
        v = v - np.outer(exc, n)
    m.vertices = v * r * np.asarray(escala)
    return _de_trimesh(m, 55.0 if cortes else 180.0)


def prisma(poligono, prof):
    """Prisma convexo: polígono en el plano XY extruido en Z (centrado)."""
    return hull([(x, y, -prof / 2) for x, y in poligono] + [(x, y, prof / 2) for x, y in poligono])


def caja_redondeada(sx, sy, sz, r, n=6):
    pts = []
    for cx in (-sx / 2 + r, sx / 2 - r):
        for cy in (-sy / 2 + r, sy / 2 - r):
            for i in range(n * 4):
                a = 2 * math.pi * i / (n * 4)
                for z in (-sz / 2, sz / 2):
                    pts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
    return hull(pts)


def M_trs(t=(0, 0, 0), r=(0, 0, 0), s=1.0):
    """Matriz: escala, luego rotación X, Y, Z (grados), luego traslación."""
    S = np.eye(4)
    S[:3, :3] *= np.asarray(s if np.ndim(s) else (s, s, s), dtype=float)
    R = (rotation_matrix(math.radians(r[2]), (0, 0, 1))
         @ rotation_matrix(math.radians(r[1]), (0, 1, 0))
         @ rotation_matrix(math.radians(r[0]), (1, 0, 0)))
    return translation_matrix(t) @ R @ S


def aplicar(m, M):
    """Transforma una malla (también sus normales explícitas, si las tiene)."""
    m.apply_transform(M)
    if "N" in m.metadata:
        N = m.metadata["N"] @ np.linalg.inv(M[:3, :3])
        m.metadata["N"] = N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
    return m


def T(m, t=(0, 0, 0), r=(0, 0, 0), s=1.0):
    return aplicar(m.copy(), M_trs(t, r, s))


def viga(p0, p1, r0, r1=None, n=6, cuadrada=False):
    """Cilindro (o listón) entre dos puntos."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    L = float(np.linalg.norm(d))
    r1 = r0 if r1 is None else r1
    if cuadrada:
        m = hull([(sx * r0, 0, sz * r0) for sx in (-1, 1) for sz in (-1, 1)]
                 + [(sx * r1, L, sz * r1) for sx in (-1, 1) for sz in (-1, 1)])
    else:
        m = cilindro(r0, r1, L, n)
    m.apply_transform(trimesh.geometry.align_vectors([0, 1, 0], d / L))
    m.apply_translation(p0)
    return m


def hoja_plana(largo, ancho, grosor=0.02):
    """Rombo plano apuntando a +Z (emblemas y hojitas sueltas)."""
    return hull([(0, 0, 0), (0, 0, largo), (ancho / 2, 0, largo * 0.4), (-ancho / 2, 0, largo * 0.4),
                 (0, grosor, largo * 0.4), (0, -grosor, largo * 0.4)])


def tubo(pts, radios, lados=8, mod=None, tapa=True):
    """Tubo suave a lo largo de una curva (troncos, ramas, tallos)."""
    pts = np.asarray(pts, float)
    n = len(pts)
    radios = np.broadcast_to(np.asarray(radios, float), (n,))
    if lados >= 5:
        lados = _lados(lados)
    if n >= 3 and n < 12 and radios.max() > 0.02:
        # curva más fina (Catmull-Rom): troncos y tallos sin codos
        t = np.linspace(0, n - 1, (n - 1) * 2 + 1)
        i0 = np.clip(np.floor(t).astype(int), 0, n - 2)
        f = (t - i0)[:, None]
        P = lambda k: pts[np.clip(k, 0, n - 1)]
        p0, p1, p2, p3 = P(i0 - 1), P(i0), P(i0 + 1), P(i0 + 2)
        pts = 0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3)
        radios = np.interp(t, np.arange(n), radios)
        if mod is not None:
            mod0 = mod
            mod = lambda i, a: mod0(min(int(round(i / 2)), n - 1), a)
        n = len(pts)
    tg = np.gradient(pts, axis=0)
    tg /= np.linalg.norm(tg, axis=1, keepdims=True)
    largo = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    nr = np.eye(3)[np.abs(tg[0]).argmin()]
    circ = 2 * math.pi * radios.max()
    P, Nn, UV = [], [], []
    for i in range(n):
        nr = nr - tg[i] * (nr @ tg[i])
        nr /= np.linalg.norm(nr)
        b = np.cross(tg[i], nr)
        fp, fn_, fu = [], [], []
        for k in range(lados + 1):
            a = 2 * math.pi * k / lados
            d = nr * math.cos(a) + b * math.sin(a)
            r = radios[i] * (mod(i, a) if mod else 1.0)
            fp.append(pts[i] + d * r)
            fn_.append(d)
            fu.append((k / lados * circ, largo[i]))
        P.append(fp), Nn.append(fn_), UV.append(fu)
    P, Nn, UV = np.array(P), np.array(Nn), np.array(UV)
    V, N, U = [], [], []
    for i in range(n - 1):
        for k in range(lados):
            q = [(i, k), (i, k + 1), (i + 1, k + 1), (i + 1, k)]
            for idx in (q[0], q[1], q[2], q[0], q[2], q[3]):
                V.append(P[idx]), N.append(Nn[idx]), U.append(UV[idx])
    if tapa and radios[-1] > 0.015:
        for k in range(lados):
            for p_, uv_ in ((pts[-1], (0, 0)), (P[-1, k + 1], (radios[-1], 0)), (P[-1, k], (0, radios[-1]))):
                V.append(p_), N.append(tg[-1]), U.append(uv_)
    return _malla(V, U, N=N, circ=circ)


def torno(perfil, lados=16, mod=None, suave=70.0):
    """Superficie de revolución alrededor de Y. perfil = [(radio, y), ...]."""
    perfil = np.asarray(perfil, float)
    lados = _lados(lados)
    largo = np.r_[0, np.cumsum(np.linalg.norm(np.diff(perfil, axis=0), axis=1))]
    circ = 2 * math.pi * perfil[:, 0].max()
    P = np.zeros((len(perfil), lados + 1, 3))
    UV = np.zeros((len(perfil), lados + 1, 2))
    for j, (r, y) in enumerate(perfil):
        for k in range(lados + 1):
            a = 2 * math.pi * (k % lados) / lados
            rr = r * (mod(a, j) if mod else 1.0)
            P[j, k] = (rr * math.cos(a), y, rr * math.sin(a))
            UV[j, k] = (k / lados * circ, largo[j])
    V, U = [], []
    for j in range(len(perfil) - 1):
        for k in range(lados):
            q = [(j, k), (j, k + 1), (j + 1, k + 1), (j + 1, k)]
            for idx in (q[0], q[2], q[1], q[0], q[3], q[2]):
                V.append(P[idx]), U.append(UV[idx])
    V, U = np.array(V).reshape(-1, 3, 3), np.array(U).reshape(-1, 3, 2)
    ok = np.linalg.norm(np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0]), axis=1) > 1e-10
    return _malla(V[ok], U[ok], suave, circ=circ)


def disco(r, y=0.0, lados=16, mod=None, domo=0.0):
    """Disco horizontal con UV plano que ocupa toda la textura (anillos, centro de flor)."""
    V, U = [], []
    lados = _lados(lados)
    anillos = [0.0, 0.5, 1.0]

    def p(f, k):
        a = 2 * math.pi * (k % lados) / lados
        rr = r * f * (mod(a, 0) if mod else 1.0)
        return (rr * math.cos(a), y + domo * (1 - f * f), rr * math.sin(a)), (0.5 + 0.5 * f * math.cos(a), 0.5 + 0.5 * f * math.sin(a))
    for i in range(2):
        for k in range(lados):
            q = [p(anillos[i], k), p(anillos[i], k + 1), p(anillos[i + 1], k + 1), p(anillos[i + 1], k)]
            for idx in (0, 1, 2, 0, 2, 3):
                V.append(q[idx][0]), U.append(q[idx][1])
    V, U = np.array(V).reshape(-1, 3, 3), np.array(U).reshape(-1, 3, 2)
    ok = np.linalg.norm(np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0]), axis=1) > 1e-10
    return _malla(V[ok], U[ok], 180.0)


PERFILES = {
    "brizna": lambda t: (1 - t) ** 0.6,
    "recto": lambda t: 1.0,
    "petalo": lambda t: math.sin(math.pi * (0.12 + 0.88 * t)) ** 0.7 if t < 1 else 0.0,
    "ancho": lambda t: math.sin(math.pi * (0.1 + 0.8 * t)) ** 0.5,
    # pétalo ancho y redondeado, más ancho hacia la punta (amapola)
    "redondo": lambda t: (math.sin(math.pi * (0.06 + 0.93 * t)) ** 0.42) * (0.35 + 0.65 * t ** 0.7) if t < 1 else 0.0,
}


def tira(base, rumbo, largo, ancho, a0=80.0, a1=40.0, segs=4, perfil="brizna", pliegue=0.0,
         arriba=0.4, rollo=0.0, uv=(0, 0, 1, 1)):
    """Tira curva (brizna, hoja, pétalo). Sale de `base` hacia `rumbo` (grados en planta),
    con inclinación a0 (grados sobre la horizontal) que acaba en a1. UV: base abajo, punta arriba."""
    hx, hz = math.cos(math.radians(rumbo)), math.sin(math.radians(rumbo))
    hv, s0 = np.array([hx, 0, hz]), np.array([-hz, 0, hx])
    cr, sr = math.cos(math.radians(rollo)), math.sin(math.radians(rollo))
    fw = PERFILES[perfil]
    p = np.asarray(base, float).copy()
    filas = []
    for i in range(segs + 1):
        t = i / segs
        a = math.radians(a0 + (a1 - a0) * t)
        d = hv * math.cos(a) + UP * math.sin(a)
        n0 = np.cross(s0, d)
        s = s0 * cr + n0 * sr
        n = np.cross(s, d)
        w = ancho * fw(t)
        pos = (p - s * w / 2, p - n * pliegue * w, p + s * w / 2)
        nor = [n + s * pliegue * 1.5, n, n - s * pliegue * 1.5]
        nor = [x * (1 - arriba) + UP * arriba for x in nor]
        nor = [x / np.linalg.norm(x) for x in nor]
        v = uv[3] - (uv[3] - uv[1]) * t
        uvs = [(uv[0], v), ((uv[0] + uv[2]) / 2, v), (uv[2], v)]
        filas.append((pos, nor, uvs))
        p = p + d * largo / segs
    V, N, U = [], [], []
    for i in range(segs):
        A, B = filas[i], filas[i + 1]
        for c in (0, 1):
            q = [(A, c), (A, c + 1), (B, c + 1), (B, c)]
            for f, k in (q[0], q[1], q[2], q[0], q[2], q[3]):
                V.append(f[0][k]), N.append(f[1][k]), U.append(f[2][k])
    V, N, U = np.array(V).reshape(-1, 3, 3), np.array(N).reshape(-1, 3, 3), np.array(U).reshape(-1, 3, 2)
    ok = np.linalg.norm(np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0]), axis=1) > 1e-12
    V, N, U = _dos_caras(V[ok], N[ok], U[ok])
    return _malla(V, U, N=N)


def cartas(centros, tam, centro_copa, rng, por=3, dispersion=0.4, arriba=0.25):
    """Cartas de follaje (racimos de hojas con alfa) con normales 'esféricas' para un sombreado suave."""
    V, N, U = [], [], []
    centro_copa = np.asarray(centro_copa, float)
    for c in centros:
        for _ in range(por):
            o = np.asarray(c, float) + rng.normal(0, dispersion, 3)
            # orientadas más bien hacia fuera de la copa (menos cartas vistas de canto)
            fuera = o - centro_copa
            n = fuera / max(np.linalg.norm(fuera), 1e-6) + rng.normal(0, 0.55, 3)
            n /= np.linalg.norm(n)
            t1 = np.cross(n, rng.normal(0, 1, 3))
            t1 /= np.linalg.norm(t1)
            t2 = np.cross(n, t1)
            h = tam * rng.uniform(0.75, 1.2) / 2
            q = [o - t1 * h - t2 * h, o + t1 * h - t2 * h, o + t1 * h + t2 * h, o - t1 * h + t2 * h]
            uq = [(0, 1), (1, 1), (1, 0), (0, 0)]
            for k in (0, 1, 2, 0, 2, 3):
                V.append(q[k]), U.append(uq[k])
                nn = q[k] - centro_copa
                nn = nn / max(np.linalg.norm(nn), 1e-6) + UP * arriba
                N.append(nn / np.linalg.norm(nn))
    V, N, U = _dos_caras(V, N, U)
    return _malla(V, U, N=N)


def _dos_caras(V, N, U):
    """Duplica los triángulos con el giro invertido y LAS MISMAS normales: así las hojas se
    iluminan igual por delante y por detrás (con material de doble cara, el dorso sale oscuro)."""
    V, N, U = (np.asarray(x, float).reshape(-1, 3, x_) for x, x_ in ((V, 3), (N, 3), (U, 2)))
    inv = [0, 2, 1]
    return np.vstack([V, V[:, inv]]), np.vstack([N, N[:, inv]]), np.vstack([U, U[:, inv]])


def normales(V, suave):
    """Normales por vértice con auto-suavizado: se promedian las caras vecinas cuyo ángulo es < suave."""
    tri = V.reshape(-1, 3, 3)
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    fu = fn / np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    fa, fuc = np.repeat(fn, 3, 0), np.repeat(fu, 3, 0)
    _, inv = np.unique(np.round(V / 2e-4).astype(np.int64), axis=0, return_inverse=True)
    inv = inv.ravel()
    if suave >= 179:
        acc = np.zeros((inv.max() + 1, 3))
        np.add.at(acc, inv, fa)
        N = acc[inv]
    else:
        cosl = math.cos(math.radians(suave))
        orden = np.argsort(inv, kind="stable")
        si = inv[orden]
        ini = np.flatnonzero(np.r_[True, si[1:] != si[:-1]])
        cuenta = np.diff(np.r_[ini, len(si)])
        N = np.zeros_like(V)
        for k in np.unique(cuenta):
            g = ini[cuenta == k]
            idx = orden[g[:, None] + np.arange(k)[None, :]]
            A, Un = fa[idx], fuc[idx]
            mask = np.einsum("gid,gjd->gij", Un, Un) >= cosl
            N[idx] = np.einsum("gij,gjd->gid", mask.astype(float), A)
    ln = np.linalg.norm(N, axis=1, keepdims=True)
    return np.where(ln > 1e-12, N / np.maximum(ln, 1e-12), fuc)


# --------------------------------------------------------------------------
# Modelo (árbol de nodos con mallas agrupadas por material) y exportación glTF
# --------------------------------------------------------------------------
class Modelo:
    def __init__(self, nombre, matriz=None):
        self.nombre = nombre
        self.matriz = np.eye(4) if matriz is None else matriz
        self.mallas = {}
        self.hijos = []

    def add(self, malla, color):
        if isinstance(malla, (list, tuple)):
            for m in malla:
                self.add(m, color)
            return self
        assert color in PALETA, color
        self.mallas.setdefault(color, []).append(malla)
        return self

    def hijo(self, nombre, t=(0, 0, 0), r=(0, 0, 0)):
        h = Modelo(nombre, M_trs(t, r))
        self.hijos.append(h)
        return h

    def limites(self, M=None):
        M = self.matriz if M is None else M @ self.matriz
        pts = [trimesh.transform_points(m.vertices, M) for l in self.mallas.values() for m in l]
        lo = [p.min(0) for p in pts]
        hi = [p.max(0) for p in pts]
        for h in self.hijos:
            a, b = h.limites(M)
            lo.append(a), hi.append(b)
        return np.min(lo, 0), np.max(hi, 0)

    def exportar(self, ruta):
        g = _GLTF()
        g.j["scenes"][0]["nodes"].append(self._volcar(g))
        return g.guardar(ruta)

    def _volcar(self, g):
        nodo = {"name": self.nombre}
        if not np.allclose(self.matriz, np.eye(4)):
            nodo["matrix"] = [float(x) for x in self.matriz.T.flatten()]
        prims = []
        grupos = {}
        for color, lista in sorted(self.mallas.items()):
            d = def_material(color)
            _, Vs, Ns, Us = grupos.setdefault(d.get("alias", color), (d, [], [], []))
            for m in lista:
                V = np.asarray(m.vertices)
                uv = np.array(m.metadata["uv_fijo"] if d["fijo"] and "uv_fijo" in m.metadata else m.visual.uv, float)
                if "circ" in m.metadata:
                    c = m.metadata["circ"] * d["esc"]
                    uv = uv * [max(1.0, round(c)) / c * d["esc"], d["esc"]]
                elif "N" not in m.metadata:
                    uv = uv * d["esc"]
                if "col" in d:
                    if "N" in m.metadata and "circ" not in m.metadata:
                        uv[:, 0] = (d["col"] + 0.06 + 0.88 * uv[:, 0]) / 4
                    else:
                        uv = np.tile([(d["col"] + 0.5) / 4, 0.5], (len(V), 1))
                Vs.append(V), Us.append(uv)
                Ns.append(m.metadata["N"] if "N" in m.metadata else normales(V, m.metadata.get("suave", 40.0)))
        for nombre, (d, Vs, Ns, Us) in grupos.items():
            prims.append(g.primitiva(np.vstack(Vs), np.vstack(Ns), np.vstack(Us), nombre, d))
        if prims:
            g.j["meshes"].append({"name": self.nombre, "primitives": prims})
            nodo["mesh"] = len(g.j["meshes"]) - 1
        hijos = [h._volcar(g) for h in self.hijos]
        if hijos:
            nodo["children"] = hijos
        g.j["nodes"].append(nodo)
        return len(g.j["nodes"]) - 1


class _GLTF:
    def __init__(self):
        self.bin = bytearray()
        self.j = {"asset": {"version": "2.0", "generator": "Jugo generar_modelos.py"}, "scene": 0,
                  "scenes": [{"nodes": []}], "nodes": [], "meshes": [], "materials": [], "textures": [],
                  "images": [], "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}],
                  "accessors": [], "bufferViews": []}
        self._mat, self._tex, self.tris = {}, {}, 0

    def _acc(self, arr, comp, tipo, destino, limites=False):
        while len(self.bin) % 4:
            self.bin.append(0)
        datos = arr.tobytes()
        self.j["bufferViews"].append({"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(datos), "target": destino})
        self.bin += datos
        a = {"bufferView": len(self.j["bufferViews"]) - 1, "componentType": comp, "count": len(arr), "type": tipo}
        if limites:
            a["min"], a["max"] = [float(x) for x in arr.min(0)], [float(x) for x in arr.max(0)]
        self.j["accessors"].append(a)
        return len(self.j["accessors"]) - 1

    def _textura(self, nombre):
        if nombre not in self._tex:
            ext = "png" if os.path.exists(os.path.join(TEXTURAS, nombre + ".png")) else "jpg"
            self.j["images"].append({"uri": f"texturas/{nombre}.{ext}", "name": nombre})
            self.j["textures"].append({"sampler": 0, "source": len(self.j["images"]) - 1, "name": nombre})
            self._tex[nombre] = len(self.j["textures"]) - 1
        return {"index": self._tex[nombre]}

    def _material(self, nombre, d):
        if nombre not in self._mat:
            pbr = {"baseColorFactor": [float(x) for x in d["factor"]] + [d["opacidad"]],
                   "metallicFactor": d["met"], "roughnessFactor": d["rug"]}
            mat = {"name": nombre, "pbrMetallicRoughness": pbr}
            if d["tex"]:
                pbr["baseColorTexture"] = self._textura(d["tex"])
            if d["normal"]:
                mat["normalTexture"] = self._textura(d["normal"])
            if d["alfa"]:
                mat["alphaMode"] = d["alfa"]
                if d["alfa"] == "MASK":
                    mat["alphaCutoff"] = 0.5
            if d["doble"]:
                mat["doubleSided"] = True
            self.j["materials"].append(mat)
            self._mat[nombre] = len(self.j["materials"]) - 1
        return self._mat[nombre]

    def primitiva(self, V, N, UV, color, d):
        todo = np.hstack([V, N, UV])
        _, primero, inv = np.unique(np.round(todo, 4), axis=0, return_index=True, return_inverse=True)
        todo = todo[primero].astype(np.float32)
        idx = inv.ravel().astype(np.uint32)
        self.tris += len(idx) // 3
        nn = todo[:, 3:6]
        nn = nn / np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-12)
        return {"attributes": {"POSITION": self._acc(np.ascontiguousarray(todo[:, :3]), 5126, "VEC3", 34962, True),
                               "NORMAL": self._acc(np.ascontiguousarray(nn.astype(np.float32)), 5126, "VEC3", 34962),
                               "TEXCOORD_0": self._acc(np.ascontiguousarray(todo[:, 6:8]), 5126, "VEC2", 34962)},
                "indices": self._acc(idx, 5125, "SCALAR", 34963), "material": self._material(color, d)}

    def guardar(self, ruta):
        self.j["buffers"] = [{"byteLength": len(self.bin),
                              "uri": "data:application/octet-stream;base64," + base64.b64encode(bytes(self.bin)).decode()}]
        if not self.j["textures"]:
            for k in ("textures", "images", "samplers"):
                del self.j[k]
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w") as f:
            json.dump(self.j, f, separators=(",", ":"))
        return self.tris


# --------------------------------------------------------------------------
# ENTORNO
# --------------------------------------------------------------------------
def ventana(m, w, h, centro, cara="z+", cruz=True):
    piezas_madera, piezas_cristal = [], []
    f = 0.09
    piezas_madera += [T(caja(w + 2 * f, f, 0.14), (0, h / 2 + f / 2, 0.04)),
                      T(caja(w + 2 * f, f, 0.14), (0, -h / 2 - f / 2, 0.04)),
                      T(caja(f, h, 0.14), (w / 2 + f / 2, 0, 0.04)),
                      T(caja(f, h, 0.14), (-w / 2 - f / 2, 0, 0.04)),
                      T(caja(w + 0.35, 0.08, 0.24), (0, -h / 2 - f - 0.04, 0.09))]
    if cruz:
        piezas_madera += [T(caja(0.05, h, 0.08), (0, 0, 0.04)),
                          T(caja(w, 0.05, 0.08), (0, h * 0.1, 0.04))]
    piezas_cristal.append(T(caja(w, h, 0.05), (0, 0, 0.0)))
    brillo = T(caja(w * 0.18, h * 0.5, 0.052), (-w * 0.25, h * 0.12, 0.003), (0, 0, -20))
    rot = {"z+": 0, "x+": 90, "x-": -90, "z-": 180}[cara]
    M = M_trs(centro, (0, rot, 0))
    for p in piezas_madera:
        p.apply_transform(M)
    for p in piezas_cristal:
        p.apply_transform(M)
    brillo.apply_transform(M)
    m.add(piezas_madera, "madera").add(piezas_cristal, "cristal").add(brillo, "cristal_luz")


def flor_mini(m, base, alto, color, semilla):
    rng = np.random.default_rng(semilla)
    x, y, z = base
    top = (x + rng.uniform(-0.05, 0.05), y + alto, z + rng.uniform(-0.05, 0.05))
    m.add(viga(base, top, 0.012, n=5), "hoja_osc")
    m.add(tira((x, y + alto * 0.35, z), rng.uniform(0, 360), 0.16, 0.08, 40, -10, 3, "recto", pliegue=0.1), "hoja_ancha")
    for i in range(6):
        a = i * 60 + rng.uniform(0, 20)
        m.add(tira(top, a, 0.09, 0.06, 15, -15, 2, "petalo"), color)
    m.add(T(bola(0.035, 0), top), "centro_flor")


def casa():
    m = Modelo("casa")
    rng = np.random.default_rng(7)
    W, D, H, base = 8.0, 6.0, 3.0, 0.45
    top = base + H
    m.add(T(caja(W + 0.3, base, D + 0.3), (0, base / 2, 0)), "piedra")
    m.add(T(caja(W, H, D), (0, base + H / 2, 0)), "estuco")
    m.add(T(caja(W + 0.18, 0.22, D + 0.18), (0, top - 0.08, 0)), "madera")
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add(T(caja(0.24, H, 0.24), (sx * W / 2, base + H / 2, sz * D / 2)), "madera")
    # hastiales
    rise = 2.4
    gable = prisma([(-D / 2, 0), (D / 2, 0), (0, rise)], W - 0.02)
    m.add(T(gable, (0, top, 0), (0, 90, 0)), "estuco")
    # tejado a dos aguas
    over, t = 0.45, 0.2
    th = math.atan(rise / (D / 2))
    L = (D / 2 + over) / math.cos(th)
    ridge_y = top + rise
    eave = D / 2 + over
    n = np.array([0, math.cos(th), math.sin(th)])
    mid = np.array([0, ridge_y - eave * math.tan(th) / 2, eave / 2]) + n * t / 2
    for lado in (1, -1):
        Mr = M_trs(r=(0, 0 if lado == 1 else 180, 0)) @ M_trs(mid, (math.degrees(th), 0, 0))
        m.add(aplicar(caja(W + 0.9, t, L), Mr), "tejado")
        m.add(aplicar(T(caja(W + 0.9, 0.06, 0.1), (0, -t / 2 + 0.03, L / 2 + 0.03)), Mr), "madera_osc")
        for sx in (-1, 1):
            m.add(viga((sx * (W / 2 + 0.47), ridge_y + 0.1, 0),
                       (sx * (W / 2 + 0.47), ridge_y + 0.1 - eave * math.tan(th), lado * eave),
                       0.1, cuadrada=True), "madera")
    m.add(T(caja(W + 1.0, 0.16, 0.36), (0, ridge_y + 0.14, 0)), "metal_osc")
    # buhardilla
    bx, bw, bz0, bz1 = -1.7, 1.7, 0.6, D / 2 - 0.25
    by0, by1 = top - 0.2, top + 1.55
    m.add(T(caja(bw, by1 - by0, bz1 - bz0), (bx, (by0 + by1) / 2, (bz0 + bz1) / 2)), "estuco")
    m.add(T(prisma([(-bw / 2, 0), (bw / 2, 0), (0, 0.75)], bz1 - bz0), (bx, by1, (bz0 + bz1) / 2)), "estuco")
    ph = math.atan(0.75 / (bw / 2))
    L2 = (bw / 2 + 0.2) / math.cos(ph)
    for lado in (1, -1):
        c = (bx + lado * (bw / 2 + 0.2) / 2 - lado * 0.05 * math.sin(ph) + 0,
             by1 + 0.75 - (bw / 2 + 0.2) * math.tan(ph) / 2 + 0.06, (bz0 + bz1) / 2 + 0.1)
        m.add(T(caja(L2, 0.14, bz1 - bz0 + 0.3), c, (0, 0, -lado * math.degrees(ph))), "tejado_osc")
    for sx in (-1, 1):
        m.add(T(caja(0.12, by1 - by0, 0.12), (bx + sx * bw / 2, (by0 + by1) / 2, bz1)), "madera")
    ventana(m, 0.6, 0.75, (bx, top + 0.7, bz1 + 0.01), cruz=True)
    # chimenea
    m.add(T(caja(0.85, 3.4, 0.85), (2.5, top + 1.7, -1.2)), "piedra")
    m.add(T(caja(1.05, 0.16, 1.05), (2.5, top + 3.45, -1.2)), "piedra_osc")
    # puerta
    dz = D / 2
    dx = 1.6
    m.add(T(caja(1.1, 2.2, 0.1), (dx, base + 1.1, dz + 0.04)), "madera")
    for i in range(4):
        m.add(T(caja(0.015, 2.1, 0.11), (dx - 0.4 + i * 0.27, base + 1.1, dz + 0.042)), "madera_osc")
    for p in [(caja(1.4, 0.14, 0.18), (dx, base + 2.27, dz + 0.06)),
              (caja(0.14, 2.3, 0.18), (dx - 0.62, base + 1.15, dz + 0.06)),
              (caja(0.14, 2.3, 0.18), (dx + 0.62, base + 1.15, dz + 0.06))]:
        m.add(T(*p), "madera_osc")
    m.add(T(caja(0.28, 0.28, 0.04), (dx, base + 1.65, dz + 0.1), (0, 0, 45)), "cristal")
    m.add(T(caja(0.4, 0.4, 0.03), (dx, base + 1.65, dz + 0.095), (0, 0, 45)), "madera_osc")
    m.add(T(bola(0.05, 1), (dx + 0.38, base + 1.05, dz + 0.13)), "metal")
    # ventanas
    ventana(m, 1.1, 0.95, (-0.6, base + 1.7, dz + 0.01))
    ventana(m, 1.1, 0.95, (-2.6, base + 1.7, dz + 0.01))
    ventana(m, 0.7, 0.95, (3.15, base + 1.7, dz + 0.01), cruz=False)
    for cara, x in (("x+", W / 2 + 0.01), ("x-", -W / 2 - 0.01)):
        ventana(m, 1.0, 0.95, (x, base + 1.7, -0.9), cara)
        ventana(m, 0.7, 0.7, (x, top + 1.0, 0), cara)
    ventana(m, 1.1, 0.95, (-2, base + 1.7, -dz - 0.01), "z-")
    ventana(m, 1.1, 0.95, (1.5, base + 1.7, -dz - 0.01), "z-")
    # porche
    pw, pd = 3.4, 1.7
    pcx = dx + 0.2
    m.add(T(caja(pw, base - 0.1, pd), (pcx, (base - 0.1) / 2, dz + pd / 2)), "piedra")
    for i in range(int(pw / 0.3)):
        m.add(T(caja(0.28, 0.1, pd), (pcx - pw / 2 + 0.15 + i * 0.3, base - 0.05, dz + pd / 2)),
              "madera_clara" if i % 2 else "madera")
    for k, (h_, zz) in enumerate([(0.3, 0.2), (0.15, 0.55)]):
        m.add(T(caja(1.5, h_, 0.38), (dx, h_ / 2, dz + pd + zz - 0.02)), "piedra")
        m.add(T(caja(1.52, 0.04, 0.4), (dx, h_ - 0.01, dz + pd + zz - 0.02)), "piedra_osc")
    postes = [(pcx - pw / 2 + 0.08, dz + pd - 0.08), (pcx + pw / 2 - 0.08, dz + pd - 0.08),
              (dx - 0.85, dz + pd - 0.08), (dx + 0.85, dz + pd - 0.08),
              (pcx - pw / 2 + 0.08, dz + 0.1), (pcx + pw / 2 - 0.08, dz + 0.1)]
    for px, pz in postes:
        m.add(T(caja(0.12, 1.0, 0.12), (px, base + 0.5, pz)), "madera_osc")
    rails = [((pcx - pw / 2 + 0.08, dz + pd - 0.08), (dx - 0.85, dz + pd - 0.08)),
             ((dx + 0.85, dz + pd - 0.08), (pcx + pw / 2 - 0.08, dz + pd - 0.08)),
             ((pcx - pw / 2 + 0.08, dz + 0.1), (pcx - pw / 2 + 0.08, dz + pd - 0.08)),
             ((pcx + pw / 2 - 0.08, dz + 0.1), (pcx + pw / 2 - 0.08, dz + pd - 0.08))]
    for (x0, z0), (x1, z1) in rails:
        for yy in (base + 0.95, base + 0.5):
            m.add(viga((x0, yy, z0), (x1, yy, z1), 0.04, cuadrada=True), "madera")
        n = max(2, int(math.hypot(x1 - x0, z1 - z0) / 0.22))
        for i in range(1, n):
            f = i / n
            m.add(T(caja(0.05, 0.45, 0.05), (x0 + (x1 - x0) * f, base + 0.72, z0 + (z1 - z0) * f)), "madera_clara")
    # jardinera con flores
    jx, jz = -1.6, dz + 0.45
    m.add(T(caja(3.6, 0.45, 0.6), (jx, 0.225, jz)), "madera")
    m.add(T(caja(3.7, 0.08, 0.7), (jx, 0.45, jz)), "madera_osc")
    m.add(T(caja(3.4, 0.05, 0.45), (jx, 0.46, jz)), "tierra")
    cols = ["petalo_amarillo", "petalo_rojo", "petalo_amarillo", "petalo_blanco"]
    for i in range(14):
        flor_mini(m, (jx - 1.6 + i * 0.24, 0.47, jz + rng.uniform(-0.12, 0.12)),
                  rng.uniform(0.35, 0.75), cols[i % 4], i)
    for i in range(8):
        mata(m, (jx - 1.5 + i * 0.43, 0.47, jz), 6, 0.12, (0.2, 0.45), (0.015, 0.025), rng)
    # contraventanas
    for wx in (-0.6, -2.6):
        for sx in (-1, 1):
            m.add(T(caja(0.42, 1.1, 0.05), (wx + sx * 0.88, base + 1.7, dz + 0.04)), "madera_osc")
            for k in range(3):
                m.add(T(caja(0.34, 0.03, 0.06), (wx + sx * 0.88, base + 1.35 + k * 0.35, dz + 0.045)), "madera")
    # bajante
    m.add(viga((W / 2 + 0.15, 0.1, D / 2 + 0.1), (W / 2 + 0.15, top, D / 2 + 0.1), 0.06), "metal_osc")
    m.add(T(caja(W + 0.6, 0.12, 0.16), (0, top - 0.02, D / 2 + 0.5)), "metal_osc")
    m.add(T(caja(W + 0.6, 0.12, 0.16), (0, top - 0.02, -D / 2 - 0.5)), "metal_osc")
    return m


def valla():
    m = Modelo("valla")
    rng = np.random.default_rng(3)
    for sx in (-1, 1):
        m.add(T(caja(0.16, 2.1, 0.16), (sx, 1.05, 0)), "madera_osc")
        m.add(T(cilindro(0.11, 0.0, 0.1, 4, rot=math.pi / 4), (sx, 2.1, 0)), "madera_osc")
    for yy in (0.35, 1.15):
        m.add(T(caja(2.0, 0.1, 0.06), (0, yy, -0.07)), "madera_osc")
    n = 8
    ancho = 1.84 / n
    for i in range(n):
        h = 1.45 + rng.uniform(-0.03, 0.03)
        m.add(T(caja(ancho - 0.025, h, 0.05), (-0.92 + ancho / 2 + i * ancho, h / 2 + 0.03, 0),
                (0, 0, rng.uniform(-1, 1))), "madera" if i % 2 else "madera_clara")
    y0, y1 = 1.52, 2.0
    for yy in (y0, y1):
        m.add(T(caja(1.84, 0.07, 0.07), (0, yy, 0)), "madera_osc")
    hgt = y1 - y0
    for c in np.arange(-1.4, 1.0, 0.16):
        for sgn in (1, -1):
            # línea x = c + t, y = y0 + t (o espejo) recortada al marco
            t0 = max(-0.92 - c, 0.0)
            t1 = min(0.92 - c, hgt)
            if t1 - t0 < 0.03:
                continue
            p0 = (sgn * (c + t0), y0 + t0, 0.02 * sgn)
            p1 = (sgn * (c + t1), y0 + t1, 0.02 * sgn)
            m.add(viga(p0, p1, 0.018, cuadrada=True), "madera_clara")
    return m


def puerta_jardin():
    m = Modelo("puerta_jardin")
    hw = 1.0
    for sx in (-1, 1):
        m.add(T(caja(0.2, 2.6, 0.2), (sx * (hw + 0.1), 1.3, 0)), "madera_osc")
        m.add(T(cilindro(0.14, 0.0, 0.12, 4, rot=math.pi / 4), (sx * (hw + 0.1), 2.6, 0)), "madera_osc")
    # arco
    pts = []
    for i in range(13):
        a = math.pi * i / 12
        pts.append((math.cos(a) * (hw + 0.1), 2.15 + math.sin(a) * 0.55, 0))
    for p0, p1 in zip(pts[:-1], pts[1:]):
        m.add(viga(p0, p1, 0.09, cuadrada=True), "madera")
    for p in pts[1:-1:2]:
        m.add(viga((p[0], 2.15, 0), p, 0.03, cuadrada=True), "madera_clara")
    m.add(T(caja(2 * hw + 0.2, 0.12, 0.16), (0, 2.15, 0)), "madera")
    # hojas de la puerta (nodos animables, origen en la bisagra)
    for lado, nombre in ((-1, "hoja_izq"), (1, "hoja_der")):
        h = m.hijo(nombre, (lado * hw, 0, 0))
        w = hw - 0.02
        for i in range(4):
            x = -lado * (w / 8 + i * w / 4)
            h.add(T(caja(w / 4 - 0.02, 1.8, 0.06), (x, 1.05, 0)), "madera" if i % 2 else "madera_clara")
        for yy in (0.45, 1.65):
            h.add(T(caja(w, 0.14, 0.05), (-lado * w / 2, yy, 0.05)), "madera_osc")
        h.add(viga((-lado * 0.08, 0.5, 0.05), (-lado * (w - 0.08), 1.6, 0.05), 0.05, cuadrada=True), "madera_osc")
        for yy in (0.45, 1.65):
            h.add(T(caja(0.3, 0.06, 0.03), (-lado * 0.18, yy, 0.09)), "metal_osc")
        h.add(T(caja(0.05, 0.3, 0.05), (-lado * (w - 0.12), 1.05, 0.1)), "metal_osc")
    return m


# --------------------------------------------------------------------------
# VEGETACIÓN
# --------------------------------------------------------------------------
def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _desviar(d, grados, rng):
    """Dirección girada `grados` respecto a d, en un acimut aleatorio."""
    p = np.cross(d, rng.normal(0, 1, 3))
    p /= np.linalg.norm(p)
    a = math.radians(grados)
    return _unit(d * math.cos(a) + p * math.sin(a))


def arbol(nombre, mat_hojas, semilla, alto=7.5, r0=0.55, tam_carta=2.0):
    m = Modelo(nombre)
    rng = np.random.default_rng(semilla)
    # tronco: curva suave con ensanche y contrafuertes en la base
    nseg = 12
    pts, p, d = [], np.zeros(3), UP.copy()
    for i in range(nseg + 1):
        pts.append(p.copy())
        d = _unit(d + rng.normal(0, 0.07, 3) * [1, 0.1, 1])
        p = p + d * alto / nseg
    pts = np.array(pts)
    ys = pts[:, 1]
    radios = r0 * (1 - 0.62 * ys / alto) + r0 * 0.8 * np.exp(-ys / 0.4)
    fase = rng.uniform(0, 6.28)
    m.add(tubo(pts, radios, 14, mod=lambda i, a: 1 + 0.3 * math.exp(-ys[i] / 0.45) * math.sin(5 * a + fase)
               + 0.04 * math.sin(3 * a + i)), "tronco")
    follaje = [pts[-1] + UP * 0.3]

    def rama(origen, d, largo, radio, nivel):
        n = 6
        pr, q = [np.asarray(origen, float)], np.asarray(origen, float)
        for i in range(n):
            d = _unit(d + UP * 0.1 + rng.normal(0, 0.12, 3))
            q = q + d * largo / n
            pr.append(q.copy())
        pr = np.array(pr)
        rr = radio * (1 - 0.7 * np.linspace(0, 1, n + 1))
        m.add(tubo(pr, rr, 8 if nivel == 0 else 6), "tronco")
        if nivel < 1:
            for t in rng.uniform(0.35, 0.95, 3):
                i = int(t * n)
                rama(pr[i], _desviar(d, rng.uniform(35, 60), rng), largo * rng.uniform(0.5, 0.7), rr[i] * 0.75, nivel + 1)
            follaje.extend([pr[-1], pr[-2], pr[-3]])
        else:
            follaje.extend([pr[2], pr[3], pr[4], pr[5], pr[6]])

    n_ramas = 9
    for k in range(n_ramas):
        f = 0.42 + 0.55 * k / (n_ramas - 1)
        i = int(f * nseg)
        ac = k * 2.4 + rng.uniform(-0.3, 0.3)
        elev = math.radians(rng.uniform(10, 30) + 35 * f)
        d0 = np.array([math.cos(ac) * math.cos(elev), math.sin(elev), math.sin(ac) * math.cos(elev)])
        rama(pts[i], d0, alto * (0.7 - 0.3 * f), radios[i] * 0.6, 0)
    centro = np.mean(follaje, 0) - UP * 1.5
    mitad = len(follaje) // 2
    orden = rng.permutation(len(follaje))
    fol = [follaje[i] for i in orden]
    # copa en dos escalas: racimos grandes que dan volumen y pequeños que rompen la silueta
    m.add(cartas(fol[:mitad], tam_carta, centro, rng, por=3, dispersion=0.55, arriba=0.4), mat_hojas[0])
    m.add(cartas(fol[mitad:], tam_carta, centro, rng, por=3, dispersion=0.55, arriba=0.4), mat_hojas[1])
    m.add(cartas(fol[::2], tam_carta * 0.6, centro, rng, por=2, dispersion=0.45, arriba=0.45), mat_hojas[0])
    # raíces que asoman del suelo
    for k in range(7):
        a = k * 2 * math.pi / 7 + rng.uniform(-0.25, 0.25)
        d = np.array([math.cos(a), 0, math.sin(a)])
        L = rng.uniform(1.1, 1.8) * r0 / 0.55
        rp = [d * r0 * 0.6 + UP * 0.35, d * (r0 + L * 0.4) + UP * 0.08, d * (r0 + L) - UP * 0.06]
        m.add(tubo(rp, [r0 * 0.38, r0 * 0.2, r0 * 0.05], 8, tapa=False), "tronco")
    return m


def mata(m, centro, n, radio, alto, ancho, rng, mats=("hierba", "hierba_clara", "hierba_osc"), segs=4):
    """Añade n briznas curvas alrededor de `centro`."""
    centro = np.asarray(centro, float)
    for i in range(n):
        a, r = rng.uniform(0, 2 * math.pi), radio * math.sqrt(rng.uniform())
        base = centro + [math.cos(a) * r, 0, math.sin(a) * r]
        a0 = rng.uniform(68, 88)
        m.add(tira(base, math.degrees(a) + rng.uniform(-60, 60), rng.uniform(*alto), rng.uniform(*ancho), a0,
                   a0 - rng.uniform(15, 65), segs, pliegue=0.18, arriba=0.45, rollo=rng.uniform(-35, 35)), mats[i % len(mats)])


def carta_plana(centro, tam, normal=(0, 1, 0), giro=0.0, arriba=0.6):
    """Cuadrado de doble cara con la textura entera (rosetas, tréboles, umbelas vistas desde arriba)."""
    n = _unit(normal)
    t1 = np.cross(n, [0, 0, 1] if abs(n[2]) < 0.9 else [1, 0, 0])
    t1 = _unit(t1)
    t2 = np.cross(n, t1)
    c, s = math.cos(giro), math.sin(giro)
    t1, t2 = t1 * c + t2 * s, -t1 * s + t2 * c
    o = np.asarray(centro, float)
    h = tam / 2
    q = [o - t1 * h - t2 * h, o + t1 * h - t2 * h, o + t1 * h + t2 * h, o - t1 * h + t2 * h]
    uq = [(0, 1), (1, 1), (1, 0), (0, 0)]
    nn = _unit(n * (1 - arriba) + UP * arriba)
    V, N, U = [], [], []
    for k in (0, 1, 2, 0, 2, 3):
        V.append(q[k]), U.append(uq[k]), N.append(nn)
    V, N, U = _dos_caras(V, N, U)
    return _malla(V, U, N=N)


def diente_de_leon(m, base, rng, alto=0.45):
    """Flor amarilla de diente de león: tallo, cabezuela y lígulas."""
    base = np.asarray(base, float)
    a = rng.uniform(0, 2 * math.pi)
    top = base + np.array([math.cos(a) * 0.08, alto, math.sin(a) * 0.08])
    m.add(tubo([base, base + (top - base) * 0.5 + [0.02, 0, 0], top], [0.008, 0.007, 0.006], 5), "hierba_osc")
    for anillo, (n, largo, inc) in enumerate([(16, 0.075, 18), (12, 0.055, 45)]):
        for i in range(n):
            ang = 360 * (i + 0.5 * anillo) / n + rng.uniform(-6, 6)
            m.add(tira(top, ang, largo, 0.022, inc, inc - 25, 2, "petalo", pliegue=0.15, arriba=0.4),
                  "petalo_amarillo" if anillo else "petalo_amarillo_osc")
    m.add(T(bola(0.028, 1, escala=(1, 0.6, 1)), tuple(top + UP * 0.012)), "petalo_amarillo_osc")
    m.add(T(bola(0.03, 0, escala=(1, 0.7, 1)), tuple(top - UP * 0.02)), "hierba_osc")


def roseta(m, centro, n, largo, ancho, mat, rng, inc=(8, 30)):
    for i in range(n):
        a = 360 * i / n + rng.uniform(-14, 14)
        a0 = rng.uniform(*inc)
        m.add(tira(tuple(np.asarray(centro) + [0, 0.01, 0]), a, largo * rng.uniform(0.8, 1.15), ancho * rng.uniform(0.85, 1.1),
                   a0, a0 - rng.uniform(25, 45), 4, "recto", pliegue=0.12, arriba=0.35), mat)


def hierbajo():
    m = Modelo("hierbajo")
    rng = np.random.default_rng(11)
    mata(m, (0, 0, 0), 36, 0.3, (0.35, 1.0), (0.026, 0.05), rng, segs=3)
    mata(m, (0, 0, 0), 8, 0.25, (0.5, 0.9), (0.022, 0.038), rng, mats=("seco",), segs=3)
    roseta(m, (0.08, 0, 0.1), 7, 0.36, 0.13, "hoja_diente", rng)
    for i in range(2):
        diente_de_leon(m, (0.08 + 0.05 * i, 0, 0.1 - 0.04 * i), rng, rng.uniform(0.38, 0.55))
    for i in range(3):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.2, 0.4)
        m.add(carta_plana((math.cos(a) * r, 0.035 + 0.02 * i, math.sin(a) * r), rng.uniform(0.11, 0.16),
                          _desviar(UP, 18, rng), rng.uniform(0, 6.28)), "trebol")
    for i in range(4):
        a = rng.uniform(0, 2 * math.pi)
        h = rng.uniform(1.0, 1.35)
        pts = [(0, 0, 0), (math.cos(a) * 0.08, h * 0.5, math.sin(a) * 0.08), (math.cos(a) * 0.28, h, math.sin(a) * 0.28)]
        m.add(tubo(pts, [0.009, 0.007, 0.005], 5), "hierba_osc")
        d = _unit(np.array(pts[2]) - np.array(pts[1]))
        espiga = torno([(0.0, 0.0), (0.02, 0.03), (0.024, 0.09), (0.014, 0.17), (0.0, 0.21)], 6)
        espiga.apply_transform(trimesh.geometry.align_vectors([0, 1, 0], d))
        espiga.apply_translation(np.array(pts[2]) - d * 0.03)
        m.add(espiga, "seco")
    return m


def umbela(m, tallo_fin, direccion, R, rng, n=9):
    for i in range(n):
        d = _desviar(direccion, rng.uniform(8, 62), rng)
        fin = np.asarray(tallo_fin) + d * R * rng.uniform(0.75, 1.0)
        m.add(viga(tallo_fin, fin, 0.007, n=3), "hierba")
        for k in range(2):
            m.add(T(bola(R * 0.17, -1), tuple(fin + rng.normal(0, R * 0.07, 3))), "petalo_blanco")


def hierbajo_grande():
    m = Modelo("hierbajo_grande")
    rng = np.random.default_rng(12)
    mata(m, (0, 0, 0), 26, 0.5, (1.0, 2.3), (0.055, 0.1), rng, segs=4)
    for i in range(9):
        a = i * 40 + rng.uniform(-15, 15)
        r = rng.uniform(0.05, 0.3)
        m.add(tira((math.cos(math.radians(a)) * r, 0.02, math.sin(math.radians(a)) * r), a, rng.uniform(0.8, 1.25),
                   rng.uniform(0.38, 0.55), rng.uniform(45, 70), rng.uniform(-25, 5), 6, "recto", pliegue=0.1, arriba=0.3),
              "hoja_ancha" if i % 3 else "hoja_ancha_osc")
    for i in range(3):
        a = rng.uniform(0, 2 * math.pi)
        h = rng.uniform(2.3, 3.0)
        pts = np.array([(0, 0, 0), (math.cos(a) * 0.1, h * 0.4, math.sin(a) * 0.1),
                        (math.cos(a) * 0.3, h * 0.75, math.sin(a) * 0.3), (math.cos(a) * 0.55, h, math.sin(a) * 0.55)])
        m.add(tubo(pts, [0.035, 0.03, 0.022, 0.015], 6), "hierba_osc")
        umbela(m, pts[-1], _unit(pts[-1] - pts[-2]), 0.34, rng)
        # la umbela vista desde arriba (carta) rellena el ramillete de florecillas
        d = _unit(pts[-1] - pts[-2])
        m.add(carta_plana(pts[-1] + d * 0.3, 0.62, d * 0.4 + UP, rng.uniform(0, 6.28), arriba=0.7), "flores_blancas")
        m.add(tira(pts[1], math.degrees(a) + 90, 0.5, 0.26, 30, -20, 4, "recto", pliegue=0.1), "hoja_ancha")
    roseta(m, (0, 0, 0), 6, 0.85, 0.32, "hoja_cardo", rng, inc=(15, 40))
    for i in range(4):
        a = rng.uniform(0, 360)
        m.add(tira((0, 0.02, 0), a, rng.uniform(0.9, 1.3), 0.3, rng.uniform(55, 75), rng.uniform(10, 30), 5, "recto",
                   pliegue=0.08, arriba=0.3), "fronda")
    return m


def matorral():
    m = Modelo("matorral")
    rng = np.random.default_rng(13)
    fol = []
    for i in range(9):
        a = i * 40 + rng.uniform(-15, 15)
        d = _unit([math.cos(math.radians(a)) * 0.75, rng.uniform(0.7, 1.4), math.sin(math.radians(a)) * 0.75])
        L = rng.uniform(1.0, 1.5)
        pts, q = [np.zeros(3)], np.zeros(3)
        for k in range(5):
            d = _unit(d + rng.normal(0, 0.12, 3))
            q = q + d * L / 5
            pts.append(q.copy())
        m.add(tubo(pts, np.linspace(0.04, 0.012, 6), 5), "tronco_osc")
        fol += pts[2:]
        for t in (2, 4):
            lado = pts[t] + _desviar(d, 60, rng) * 0.4
            m.add(viga(pts[t], lado, 0.012, 0.006, n=3), "tronco_osc")
            fol.append(lado)
    fol.append(np.array([0, 0.6, 0]))
    centro = np.array([0, 0.45, 0])
    orden = rng.permutation(len(fol))
    fol = [fol[i] for i in orden]
    k = len(fol) * 2 // 3
    m.add(cartas(fol[:k], 0.9, centro, rng, por=4, dispersion=0.18, arriba=0.45), "hojas_verde")
    m.add(cartas(fol[k:], 0.9, centro, rng, por=4, dispersion=0.18, arriba=0.45), "hojas_osc")
    # florecillas blancas y bayas rojas salpicadas por fuera de la mata
    for i in range(26):
        p = fol[rng.integers(len(fol))] + rng.normal(0, 0.15, 3)
        d = _unit(p - centro)
        q = centro + d * (np.linalg.norm(p - centro) + 0.18)
        if i % 3:
            for k2 in range(5):
                m.add(tira(tuple(q), k2 * 72 + i * 13, 0.085, 0.07, 25, -5, 2, "petalo", arriba=0.5), "petalo_blanco")
            m.add(T(bola(0.024, 0), tuple(q + UP * 0.012)), "petalo_amarillo_osc")
        else:
            for k2 in range(4):
                m.add(T(bola(0.035, 0), tuple(q + rng.normal(0, 0.035, 3))), "otono_rojo")
    return m


def zarza():
    m = Modelo("zarza")
    rng = np.random.default_rng(14)
    for s in range(9):
        a = s * 40 + rng.uniform(-15, 15)
        d = np.array([math.cos(math.radians(a)), 0, math.sin(math.radians(a))])
        alcance, alto = rng.uniform(1.0, 1.7), rng.uniform(1.0, 1.9)
        N = 10
        pts = []
        for i in range(N + 1):
            f = i / N
            p = d * alcance * f + UP * math.sin(f * math.pi * 0.85) * alto
            pts.append(p + [math.sin(f * 7 + s) * 0.08, 0, math.cos(f * 6 + s) * 0.08])
        pts = np.array(pts)
        m.add(tubo(pts, 0.05 * (1 - 0.65 * np.linspace(0, 1, N + 1)), 6), "zarza")
        for i in range(1, N + 1):
            q = (pts[i - 1] + pts[i]) / 2
            for k in range(2):  # espinas
                q2 = pts[i - 1] + (pts[i] - pts[i - 1]) * (0.25 + 0.5 * k)
                m.add(viga(q2, q2 + _unit(rng.normal(0, 1, 3) + UP * 0.3) * 0.085, 0.014, 0.0, n=4), "seco")
            for _ in range(3):
                rumbo = rng.uniform(0, 360)
                m.add(tira(pts[i], rumbo, rng.uniform(0.22, 0.36), rng.uniform(0.15, 0.22), rng.uniform(-10, 40), rng.uniform(-40, 0),
                           2, "recto", pliegue=0.14, arriba=0.35), "hoja_ancha_osc" if (i + s) % 3 else "hoja_ancha")
            if i in (5, 7, 9) and rng.random() < 0.8:
                # racimo de moras: drupas juntas, maduras (negras) y verdes/rojas
                c = pts[i] - UP * 0.07
                col = "mora" if rng.random() < 0.65 else "otono_rojo"
                for k in range(1):
                    cm = c + rng.normal(0, 0.05, 3)
                    m.add(T(bola(0.022, -1), tuple(cm)), col)
                    for d in range(7):
                        m.add(T(bola(0.017, -1), tuple(cm + _unit(rng.normal(0, 1, 3)) * 0.022 * np.array([1, 1.3, 1]))), col)
    for i in range(16):
        m.add(tira((0, 0.03, 0), rng.uniform(0, 360), rng.uniform(0.3, 0.5), rng.uniform(0.2, 0.3), rng.uniform(15, 55), rng.uniform(-20, 10),
                   4, "recto", pliegue=0.12, arriba=0.3), "hoja_ancha_osc" if i % 2 else "hoja_ancha")
    return m


def girasol_gigante():
    m = Modelo("girasol_gigante")
    rng = np.random.default_rng(15)
    pts = np.array([(0, 0, 0), (0.06, 0.8, -0.03), (0.1, 1.7, 0.0), (0.06, 2.6, 0.08), (0.0, 3.3, 0.22), (0.0, 3.5, 0.34)])
    m.add(tubo(pts, [0.085, 0.075, 0.07, 0.062, 0.055, 0.06], 8), "hoja_osc")
    for i, (y, a) in enumerate([(0.7, 20), (1.15, 160), (1.6, 290), (2.05, 80), (2.5, 215), (2.9, 340)]):
        base = np.array([np.interp(y, pts[:, 1], pts[:, 0]), y, np.interp(y, pts[:, 1], pts[:, 2])])
        dirv = np.array([math.cos(math.radians(a)), 0.5, math.sin(math.radians(a))])
        fin = base + dirv * 0.18
        m.add(viga(base, fin, 0.018, 0.012, n=5), "hoja_osc")
        m.add(tira(fin, a, 0.85 - i * 0.07, 0.62 - i * 0.05, 30, -35, 6, "recto", pliegue=0.1, arriba=0.3),
              "hoja_ancha" if i % 2 else "hoja_ancha_osc")
    # cabeza (se modela mirando hacia +Y y luego se gira hacia el frente)
    cab = []
    cab.append((disco(0.4, 0.05, 20, domo=0.05), "girasol_centro"))
    cab.append((torno([(0.0, -0.2), (0.07, -0.2), (0.36, -0.1), (0.44, 0.0), (0.4, 0.05)], 20), "hoja_osc"))
    for anillo, (n, largo, a0, y) in enumerate([(24, 0.55, 2, 0.015), (24, 0.5, 12, 0.025), (21, 0.42, 26, 0.038)]):
        for i in range(n):
            a = 360 * (i + 0.5 * anillo) / n + rng.uniform(-3, 3)
            b = (math.cos(math.radians(a)) * 0.37, y, math.sin(math.radians(a)) * 0.37)
            cab.append((tira(b, a, largo * rng.uniform(0.9, 1.08), 0.17, a0 + rng.uniform(-6, 6), a0 - rng.uniform(5, 25), 5,
                             "petalo", pliegue=0.16, arriba=0.25, rollo=rng.uniform(-15, 15)),
                        "petalo_amarillo" if anillo else "petalo_amarillo_osc"))
    for i in range(14):
        a = i * 360 / 14
        b = (math.cos(math.radians(a)) * 0.38, -0.04, math.sin(math.radians(a)) * 0.38)
        cab.append((tira(b, a, 0.24, 0.12, -5, -30, 3, "brizna", arriba=0.1), "hierba_osc"))
    Mh = M_trs((0.0, 3.56, 0.42), (68, 0, 0))
    for malla, col in cab:
        m.add(aplicar(malla, Mh), col)
    return m


def amapola_gigante():
    m = Modelo("amapola_gigante")
    rng = np.random.default_rng(16)
    pts = np.array([(0, 0, 0), (-0.1, 0.7, 0.04), (-0.05, 1.4, -0.03), (0.08, 2.1, 0.02), (0.2, 2.55, 0.1)])
    m.add(tubo(pts, [0.045, 0.04, 0.035, 0.03, 0.03], 7), "hoja_osc")
    for i, (y, a) in enumerate([(0.15, 30), (0.35, 150), (0.55, 260), (0.9, 80), (1.3, 200)]):
        base = (np.interp(y, pts[:, 1], pts[:, 0]), y, np.interp(y, pts[:, 1], pts[:, 2]))
        m.add(tira(base, a, 0.75 - i * 0.08, 0.3, 55, -20, 6, "recto", pliegue=0.12, arriba=0.3), "hoja_ancha" if i % 2 else "hoja_ancha_osc")
    top = pts[-1]
    # pétalos anchos y arrugados en dos coronas, formando una copa
    for anillo, (n, a0, a1, largo, ancho) in enumerate([(4, 30, -2, 0.62, 0.78), (4, 62, 38, 0.52, 0.66)]):
        for i in range(n):
            a = 360 * i / n + anillo * 45 + rng.uniform(-8, 8)
            m.add(tira(top - UP * 0.02, a, largo * rng.uniform(0.92, 1.05), ancho * 1.25, a0 + rng.uniform(-5, 5), a1, 10, "redondo",
                       pliegue=0.22, arriba=0.12, rollo=rng.uniform(-10, 10)),
                  "petalo_rojo" if (i + anillo) % 2 else "petalo_rojo_osc")
            # mancha negra en la base del pétalo
            m.add(tira(top + UP * 0.005, a, largo * 0.22, ancho * 0.42, a0 + 4, a0, 2, "petalo", pliegue=0.3, arriba=0.12), "negro")
    m.add(T(bola(0.1, 2, escala=(1, 1.1, 1)), tuple(top + UP * 0.1)), "hoja_osc")
    m.add(T(disco(0.095, 0.0, 12, domo=0.03), tuple(top + UP * 0.205)), "petalo_amarillo_osc")
    for i in range(10):  # estrella del estigma
        a = i * 36
        m.add(tira(tuple(top + UP * 0.215), a, 0.09, 0.018, 8, -10, 2, "recto"), "centro_flor")
    for i in range(40):
        a = math.radians(i * 360 / 40 + rng.uniform(-4, 4))
        r = rng.uniform(0.14, 0.2)
        q = top + [math.cos(a) * r, 0.15 + rng.uniform(0, 0.06), math.sin(a) * r]
        m.add(viga(top + UP * 0.06, q, 0.005, n=3), "negro")
        m.add(T(bola(0.014, 0), tuple(q)), "negro")
    # capullo
    cap = np.array([(-0.05, 1.4, -0.03), (-0.3, 1.9, -0.2), (-0.42, 1.95, -0.3), (-0.48, 1.85, -0.36)])
    m.add(tubo(cap, 0.018, 5), "hoja_osc")
    m.add(T(bola(0.08, 1, escala=(1, 1.5, 1)), tuple(cap[-1] - UP * 0.08)), "hoja")
    return m


def _seta(m, base, e, rng, motas=10, lados=18):
    base = np.asarray(base, float)
    M = M_trs(base, (rng.uniform(-6, 6), rng.uniform(0, 360), rng.uniform(-6, 6)), e)
    add = lambda malla, col: m.add(aplicar(malla, M), col)
    add(torno([(0.0, 0), (0.36, 0), (0.33, 0.12), (0.26, 0.5), (0.23, 1.15), (0.0, 1.2)], lados), "seta_crema")
    add(torno([(0.25, 0.88), (0.42, 0.78), (0.4, 0.8), (0.25, 0.92)], lados), "petalo_blanco")
    add(torno([(0.2, 1.12), (0.7, 1.13), (1.16, 1.1), (1.22, 1.16)], lados), "seta_crema")
    # láminas bajo el sombrero
    nl = 40 if lados > 12 else 18
    for i in range(nl):
        a = 360 * i / nl
        c_, s_ = math.cos(math.radians(a)), math.sin(math.radians(a))
        add(hull([(c_ * 0.25, 1.12, s_ * 0.25), (c_ * 1.17, 1.11, s_ * 1.17), (c_ * 1.0, 1.25, s_ * 1.0), (c_ * 0.3, 1.2, s_ * 0.3),
                  (c_ * 0.6 - s_ * 0.012, 1.15, s_ * 0.6 + c_ * 0.012)]), "seta_crema")
    # volva (bolsa en la base del pie)
    add(torno([(0.0, 0.0), (0.42, 0.0), (0.46, 0.08), (0.4, 0.2), (0.36, 0.24)], lados), "petalo_blanco")
    domo = [(1.22, 1.16), (1.24, 1.24), (1.2, 1.36), (1.08, 1.53), (0.85, 1.72), (0.5, 1.87), (0.2, 1.935), (0.0, 1.95)]
    add(torno(domo, lados), "seta_roja")
    d = np.array(domo)
    for i in range(motas):
        j = rng.integers(1, len(d) - 2)
        f = rng.uniform()
        r, y = d[j] * (1 - f) + d[j + 1] * f
        tg = d[j + 1] - d[j]
        n2 = _unit([-tg[1], tg[0]]) * -1
        a = rng.uniform(0, 2 * math.pi)
        n3 = _unit([n2[0] * math.cos(a), n2[1], n2[0] * math.sin(a)])
        mm = bola(rng.uniform(0.07, 0.14), 0, escala=(1, 0.3, 1))
        mm.apply_transform(trimesh.geometry.align_vectors([0, 1, 0], n3))
        mm.apply_translation((r * math.cos(a), y, r * math.sin(a)))
        add(mm, "petalo_blanco")


def seta_gigante():
    m = Modelo("seta_gigante")
    rng = np.random.default_rng(17)
    _seta(m, (0, 0, 0), 1.0, rng, 12)
    _seta(m, (0.85, 0, 0.5), 0.3, rng, 5, 12)
    _seta(m, (0.6, 0, 0.85), 0.2, rng, 4, 12)
    _seta(m, (-0.8, 0, 0.45), 0.25, rng, 4, 12)
    mata(m, (0.3, 0, 0.6), 14, 0.5, (0.15, 0.35), (0.015, 0.03), rng)
    return m


def tocon():
    m = Modelo("tocon")
    rng = np.random.default_rng(18)
    lob = lambda a, j: 1 + 0.07 * math.sin(5 * a + 1) + 0.04 * math.sin(9 * a + 2) + 0.03 * math.sin(14 * a)
    m.add(torno([(1.0, 0), (0.82, 0.1), (0.7, 0.35), (0.64, 0.78), (0.6, 0.82)], 28, mod=lob), "tronco")
    m.add(disco(0.61, 0.815, 28, mod=lob), "anillos")
    for i in range(6):
        a = math.radians(i * 60 + rng.uniform(-12, 12))
        d = np.array([math.cos(a), 0, math.sin(a)])
        pts = [d * 0.45 + UP * 0.32, d * 0.85 + UP * 0.12, d * 1.25 + UP * 0.02, d * 1.6 - UP * 0.05]
        m.add(tubo(pts, [0.26, 0.19, 0.12, 0.05], 8, tapa=False), "tronco")
    m.add(T(bola_ruido(0.4, 2, 0.25, 3, escala=(1, 0.3, 0.8)), (-0.3, 0.8, 0.15)), "musgo")
    m.add(T(bola_ruido(0.3, 2, 0.25, 4, escala=(1, 0.6, 0.4)), (0.55, 0.25, 0.5)), "musgo")
    for i in range(4):
        _seta(m, (0.72 * math.cos(0.5 + i * 0.35), 0.0, 0.9 * math.sin(0.5 + i * 0.35) + 0.25), 0.09 + 0.03 * (i % 2), rng, 0, 10)
    # yesqueros (hongos de repisa) en el lado de atrás
    for i in range(3):
        a = math.radians(200 + i * 25)
        p = (math.cos(a) * 0.66, 0.3 + i * 0.14, math.sin(a) * 0.66)
        m.add(T(torno([(0.0, 0.0), (0.2, -0.01), (0.22, 0.02), (0.15, 0.06), (0.0, 0.07)], 10), p, (0, -math.degrees(a), 0),
                s=(1, 1, 0.6)), "corteza_clara")
    # helechos y astillas
    for i in range(6):
        a = rng.uniform(-40, 40) + 120
        m.add(tira((math.cos(math.radians(a)) * 0.9, 0.0, math.sin(math.radians(a)) * 0.9), a + rng.uniform(-50, 50), rng.uniform(0.5, 0.75),
                   0.24, rng.uniform(55, 75), rng.uniform(5, 25), 5, "recto", pliegue=0.06, arriba=0.3), "fronda")
    for i in range(8):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(1.2, 1.9)
        p = np.array([math.cos(a) * r, 0.02, math.sin(a) * r])
        m.add(viga(p, p + [rng.uniform(-0.2, 0.2), 0.01, rng.uniform(-0.2, 0.2)], 0.02, 0.012, n=5), "madera_clara")
    mata(m, (0, 0, 0), 26, 1.1, (0.15, 0.4), (0.015, 0.03), rng)
    return m


def roca():
    m = Modelo("roca")
    rng = np.random.default_rng(19)
    m.add(T(bola_ruido(0.9, 3, 0.22, 4, escala=(1.2, 0.72, 1.0), cortes=6), (0, 0.42, 0)), "roca")
    m.add(T(bola_ruido(0.55, 3, 0.22, 5, escala=(1.0, 0.8, 1.0), cortes=5), (0.95, 0.27, 0.4)), "roca")
    m.add(T(bola_ruido(0.33, 2, 0.22, 6, cortes=4), (-0.85, 0.16, 0.5)), "roca")
    # musgo: cojines bajos y bultosos que se pegan a la parte alta de la roca
    for i, (p, r) in enumerate([((-0.2, 0.92, -0.15), 0.42), ((0.2, 0.9, 0.05), 0.3), ((-0.55, 0.78, 0.1), 0.25),
                                ((1.0, 0.62, 0.3), 0.22), ((0.1, 0.85, -0.45), 0.2)]):
        m.add(T(bola_ruido(r, 3, 0.45, 40 + i, escala=(1.2, 0.3, 1.0)), p, (rng.uniform(-8, 8), rng.uniform(0, 360), rng.uniform(-8, 8))), "musgo")
    # helechos y piedrecitas alrededor
    for i in range(7):
        a = rng.uniform(150, 260) + i * 4
        m.add(tira((-0.95 + rng.normal(0, 0.1), 0.0, -0.35 + rng.normal(0, 0.1)), a + rng.uniform(-60, 60), rng.uniform(0.55, 0.8), 0.26,
                   rng.uniform(55, 75), rng.uniform(5, 25), 5, "recto", pliegue=0.06, arriba=0.3), "fronda")
    for i in range(9):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(1.2, 1.7)
        m.add(T(bola_ruido(rng.uniform(0.05, 0.11), 1, 0.25, 60 + i, escala=(1.2, 0.6, 1.0), cortes=1),
                (math.cos(a) * r, 0.02, math.sin(a) * r)), "roca")
    mata(m, (0.2, 0, 0.9), 16, 0.4, (0.15, 0.4), (0.015, 0.03), rng)
    mata(m, (-0.9, 0, -0.3), 12, 0.3, (0.15, 0.35), (0.015, 0.03), rng)
    return m


def hojas_sueltas(m, n, radio, rng, altura=lambda r: 0.0, radio_min=0.0):
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi)
        r = radio_min + (radio - radio_min) * rng.uniform() ** 0.7
        k = int(rng.integers(4))
        uv = ((k % 2) / 2, (k // 2) / 2, (k % 2) / 2 + 0.5, (k // 2) / 2 + 0.5)
        inc = rng.uniform(-12, 25)
        m.add(tira((math.cos(a) * r, altura(r) + 0.02 + rng.uniform(0, 0.03), math.sin(a) * r), rng.uniform(0, 360),
                   rng.uniform(0.16, 0.26), rng.uniform(0.12, 0.18), inc, inc - rng.uniform(0, 30), 2, "recto", arriba=0.5), "hojas_caidas")


def monton_hojas():
    m = Modelo("monton_hojas")
    rng = np.random.default_rng(20)
    b = bola_ruido(1.0, 3, 0.18, 8, escala=(1.25, 0.5, 1.05))
    v = b.vertices.copy()
    v[:, 1] = np.maximum(v[:, 1], -0.05)
    b.vertices = v
    m.add(T(b, (0, 0.05, 0)), "hojarasca")
    alt = lambda r: 0.55 * max(0.0, 1 - (r / 1.15) ** 2)
    hojas_sueltas(m, 150, 1.15, rng, alt)
    hojas_sueltas(m, 80, 2.1, rng, radio_min=1.0)
    # ramitas que asoman del montón
    for i in range(7):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.2, 0.9)
        p = np.array([math.cos(a) * r, alt(r) + 0.02, math.sin(a) * r])
        d = _unit([math.cos(a + rng.uniform(-1, 1)), rng.uniform(0.1, 0.5), math.sin(a + rng.uniform(-1, 1))])
        m.add(tubo([p - d * 0.2, p + d * 0.15, p + d * 0.45 + UP * 0.03], [0.022, 0.016, 0.008], 5), "tronco_osc")
    return m


def alfombra_hojas():
    """Mancha de hojarasca en el suelo (para poner bajo los árboles de otoño)."""
    m = Modelo("alfombra_hojas")
    rng = np.random.default_rng(21)
    lob = lambda a, j: 1 + 0.18 * math.sin(3 * a + 1) + 0.12 * math.sin(7 * a + 2) + 0.06 * math.sin(13 * a)
    d = disco(2.6, 0.03, 28, mod=lob)
    d.metadata["uv_fijo"] = np.asarray(d.vertices)[:, [0, 2]].copy()
    m.add(d, "hojarasca")
    hojas_sueltas(m, 110, 3.6, rng, radio_min=1.8)
    return m


# --------------------------------------------------------------------------
# ENTORNO NUEVO
# --------------------------------------------------------------------------
def suelo_cesped():
    m = Modelo("suelo_cesped")
    rng = np.random.default_rng(22)
    m.add(T(caja(4.0, 0.3, 4.0), (0, -0.15, 0)), "tierra")
    m.add(T(caja(4.0, 0.02, 4.0), (0, 0.0, 0)), "cesped")
    for i in range(18):
        x, z = rng.uniform(-1.8, 1.8, 2)
        mata(m, (x, 0.01, z), 7, 0.1, (0.1, 0.25), (0.012, 0.022), rng)
    return m


def camino_piedra():
    m = Modelo("camino_piedra")
    rng = np.random.default_rng(23)
    for i in range(7):
        cx, cz = rng.uniform(-0.3, 0.3), -1.3 + i * 0.45 + rng.uniform(-0.05, 0.05)
        r = rng.uniform(0.25, 0.36)
        n = int(rng.integers(6, 9))
        pts = []
        for k in range(n):
            a = 2 * math.pi * k / n + rng.uniform(-0.2, 0.2)
            rr = r * rng.uniform(0.8, 1.15)
            for y, f in ((0.0, 1.0), (0.05, 1.0), (0.07, 0.9)):
                pts.append((cx + math.cos(a) * rr * f, y, cz + math.sin(a) * rr * f))
        m.add(hull(pts, 60.0), "roca")
    return m


def _parche(mat):
    q = [(-1, 0, -1), (-1, 0, 1), (1, 0, 1), (1, 0, -1)]
    uv = [(0, 0), (0, 1), (1, 1), (1, 0)]
    orden = (0, 1, 2, 0, 2, 3)
    return _malla([q[k] for k in orden], [uv[k] for k in orden], N=[UP] * 6)


def calva_tierra():
    """Calva de tierra (radio 1, se escala en el juego) que queda al quitar una planta."""
    m = Modelo("calva_tierra")
    m.add(_parche("calva"), "calva")
    return m


def cesped_nuevo():
    """Césped recién sembrado (radio 1, se escala en el juego)."""
    m = Modelo("cesped_nuevo")
    rng = np.random.default_rng(26)
    m.add(T(_parche("cesped_parche"), (0, 0.01, 0)), "cesped_parche")
    mata(m, (0, 0, 0), 16, 0.75, (0.07, 0.15), (0.02, 0.03), rng, mats=("hierba_clara", "hierba"), segs=2)
    return m


PARCELA = dict(x0=-50.0, x1=45.0, z0=-45.0, z1=23.0, puerta_x=1.6, casa_frente=3.0)  # todo el mapa (ver ZONAS en economia.py)


def parcela():
    """Terreno de la escena principal: césped, sendero de tierra, acera y calle."""
    m = Modelo("parcela")
    rng = np.random.default_rng(24)
    P = PARCELA
    x0, x1, z0, z1 = P["x0"] - 9, P["x1"] + 9, P["z0"] - 9, P["z1"]
    nx, nz = int(x1 - x0), int(z1 - z0)
    xs, zs = np.linspace(x0, x1, nx + 1), np.linspace(z0, z1, nz + 1)
    alt = rng.uniform(-0.03, 0.03, (nx + 1, nz + 1))
    alt[:, -1] = 0
    V, U = [], []
    for i in range(nx):
        for j in range(nz):
            q = [(xs[i], alt[i, j], zs[j]), (xs[i], alt[i, j + 1], zs[j + 1]),
                 (xs[i + 1], alt[i + 1, j + 1], zs[j + 1]), (xs[i + 1], alt[i + 1, j], zs[j])]
            for k in (0, 1, 2, 0, 2, 3):
                V.append(q[k]), U.append((q[k][0], q[k][2]))
    cesped = _malla(V, U, 180.0)
    cesped.metadata["uv_fijo"] = np.array(U)
    m.add(cesped, "cesped")
    # sendero de la puerta de casa a la puerta del jardín
    V, U = [], []
    za, zb, n = P["casa_frente"] + 2.3, z1, 24
    borde = lambda t, lado: P["puerta_x"] + 0.5 * math.sin(t * 5.0) * (1 - t) * t * 4 + lado * (0.85 + 0.15 * math.sin(t * 23 + lado))
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        q = [(borde(t0, -1), 0.045, za + (zb - za) * t0), (borde(t0, 1), 0.045, za + (zb - za) * t0),
             (borde(t1, 1), 0.045, za + (zb - za) * t1), (borde(t1, -1), 0.045, za + (zb - za) * t1)]
        for k in (0, 2, 1, 0, 3, 2):
            V.append(q[k]), U.append((q[k][0], q[k][2]))
    senda = _malla(V, U, 180.0)
    senda.metadata["uv_fijo"] = np.array(U)
    m.add(senda, "tierra_suelo")
    # acera, bordillo y calle
    m.add(T(caja(180, 0.16, 2.2), (0, 0.06, z1 + 1.1)), "piedra")
    m.add(T(caja(180, 0.2, 0.2), (0, 0.05, z1 + 2.3)), "piedra_osc")
    m.add(T(caja(180, 0.1, 9.0), (0, -0.03, z1 + 6.9)), "asfalto")
    for x in np.arange(-88, 88, 4.0):
        m.add(T(caja(1.8, 0.012, 0.14), (x, 0.025, z1 + 6.9)), "blanco")
    return m


def saco_semillas():
    """Saco de semillas de césped (icono de la tienda y del HUD)."""
    m = Modelo("saco_semillas")
    rng = np.random.default_rng(27)
    m.add(torno([(0.0, 0.0), (0.2, 0.0), (0.26, 0.07), (0.27, 0.28), (0.22, 0.44), (0.12, 0.5), (0.11, 0.54), (0.17, 0.62)], 14), "saco")
    m.add(torno([(0.115, 0.5), (0.135, 0.515), (0.135, 0.535), (0.115, 0.55)], 12), "saco_osc")
    m.add(disco(0.15, 0.585, 12, domo=0.02), "tierra")
    hoja = T(hoja_plana(0.2, 0.15, 0.01), (0, -0.1, 0))
    hoja.apply_transform(rotation_matrix(-math.pi / 2, (1, 0, 0)))
    m.add(T(hoja, (0.0, 0.25, 0.268)), "hoja")
    for i in range(5):
        m.add(tira((rng.uniform(-0.05, 0.05), 0.59, rng.uniform(-0.05, 0.05)), i * 72 + rng.uniform(-20, 20), rng.uniform(0.14, 0.24), 0.035,
                   rng.uniform(65, 85), rng.uniform(20, 50), 3, pliegue=0.2), "hierba_clara" if i % 2 else "hierba")
    return m


def corazon():
    """Corazón para la vida del jugador en la interfaz (origen en el centro)."""
    m = Modelo("corazon")
    # silueta clásica de corazón, "inflada" como un cojín (forma estrellada desde el centro)
    nt, nv = 72, 14
    t = np.linspace(0, 2 * math.pi, nt + 1)
    ox = 16 * np.sin(t) ** 3
    oy = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    ox, oy = ox / 34.0 * 0.94, (oy + 2.0) / 34.0 * 0.94
    c = np.array([0.0, 0.0])
    prof = 0.2
    # contorno redondeado (sin hendidura) para las capas interiores: el surco se suaviza hacia el centro
    rad = np.hypot(ox, oy)
    radk = np.convolve(np.r_[rad[-9:-1], rad, rad[1:9]], np.ones(17) / 17, "valid")
    P = np.zeros((nv + 1, nt + 1, 3))
    UVg = np.zeros((nv + 1, nt + 1, 2))
    for j in range(nv + 1):
        v = -1 + 2 * j / nv
        r = math.cos(v * math.pi / 2) ** 0.55
        z = prof * math.sin(v * math.pi / 2)
        mezcla_ = r ** 3
        esc = (rad * mezcla_ + radk * (1 - mezcla_)) / np.maximum(rad, 1e-6)
        P[j, :, 0] = c[0] + (ox - c[0]) * r * esc
        P[j, :, 1] = c[1] + (oy - c[1]) * r * esc
        P[j, :, 2] = z
        UVg[j, :, 0] = t / (2 * math.pi)
        UVg[j, :, 1] = j / nv
    V, U = [], []
    for j in range(nv):
        for k in range(nt):
            q = [(j, k), (j, k + 1), (j + 1, k + 1), (j + 1, k)]
            for idx in (q[0], q[1], q[2], q[0], q[2], q[3]):
                V.append(P[idx]), U.append(UVg[idx])
    V, U = np.array(V).reshape(-1, 3, 3), np.array(U).reshape(-1, 3, 2)
    ok = np.linalg.norm(np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0]), axis=1) > 1e-12
    V, U = V[ok], U[ok]
    fn = np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0])
    if np.mean(np.einsum("ij,ij->i", fn, V.mean(1))) < 0:
        V, U = V[:, [0, 2, 1]], U[:, [0, 2, 1]]
    m.add(_malla(V, U, 75.0), "rojo_luz")
    # brillo de caramelo en el lóbulo izquierdo
    m.add(T(bola(0.075, 2, escala=(1.5, 0.75, 0.3)), (-0.22, 0.2, 0.16), (0, 0, 25)), "blanco")
    m.add(T(bola(0.03, 1, escala=(1, 1, 0.3)), (-0.33, 0.08, 0.135)), "blanco")
    return m


def bolsa_basura():
    m = Modelo("bolsa_basura")
    rng = np.random.default_rng(25)
    b = bola_ruido(1.0, 3, 0.1, 21, escala=(0.42, 0.42, 0.38))
    v = b.vertices.copy()
    v[:, 1] = (np.maximum(v[:, 1], -0.36) + 0.36) * 1.15
    estrecha = np.clip((v[:, 1] - 0.62) / 0.3, 0, 1)
    v[:, 0] *= 1 - 0.55 * estrecha
    v[:, 2] *= 1 - 0.55 * estrecha
    b.vertices = v
    m.add(b, "plastico_negro")
    m.add(torno([(0.13, 0.84), (0.07, 0.95), (0.06, 1.0)], 10), "plastico_negro")
    m.add(torno([(0.066, 0.97), (0.08, 0.985), (0.08, 1.005), (0.066, 1.02)], 10), "lazo_amarillo")
    for i in range(7):
        m.add(tira((0, 1.0, 0), i * 51 + rng.uniform(-10, 10), rng.uniform(0.13, 0.2), 0.11, rng.uniform(40, 75), rng.uniform(0, 40), 3,
                   "brizna", pliegue=0.25, arriba=0.2), "plastico_negro_brillo")
    hoja = T(hoja_plana(0.24, 0.17, 0.01), (0, -0.12, 0))
    hoja.apply_transform(rotation_matrix(-math.pi / 2, (1, 0, 0)))
    m.add(T(hoja, (0.0, 0.46, 0.385), (-10, 0, 0)), "otono_naranja")
    mata(m, (0, 1.0, 0), 6, 0.02, (0.2, 0.35), (0.015, 0.025), rng)
    return m


# --------------------------------------------------------------------------
# JUGABILIDAD
# --------------------------------------------------------------------------
def cubo_basura():
    m = Modelo("cubo_basura")
    w0, d0, w1, d1, h = 0.5, 0.55, 0.6, 0.68, 1.0
    m.add(hull([(sx * w0 / 2, 0.06, sz * d0 / 2) for sx in (-1, 1) for sz in (-1, 1)]
               + [(sx * w1 / 2, h, sz * d1 / 2) for sx in (-1, 1) for sz in (-1, 1)]), "contenedor")
    m.add(T(caja(w1 + 0.04, 0.06, d1 + 0.04), (0, h - 0.03, 0)), "contenedor_osc")
    for yy in (0.35, 0.65):
        m.add(T(caja(0.02, 0.4, 0.02), (0, yy + 0.05, d0 / 2 + (yy / h) * (d1 - d0) / 2 + 0.005)), "contenedor_osc")
    hoja = hoja_plana(0.18, 0.13, 0.01)
    hoja.apply_transform(rotation_matrix(-math.pi / 2, (1, 0, 0)))
    m.add(T(hoja, (0, 0.62, 0.32)), "blanco")
    m.add(viga((-0.24, 0.92, -0.38), (0.24, 0.92, -0.38), 0.025, n=6), "contenedor_osc")
    for sx in (-1, 1):
        m.add(T(caja(0.04, 0.15, 0.06), (sx * 0.22, 0.86, -0.36)), "contenedor_osc")
    for sx in (-1, 1):
        r = m.hijo(f"rueda_{'izq' if sx < 0 else 'der'}", (sx * 0.27, 0.1, -0.24))
        r.add(T(cilindro(0.1, 0.1, 0.06, 10), (-0.03, 0, 0), (0, 0, -90)), "goma")
        r.add(T(cilindro(0.04, 0.04, 0.065, 6), (-0.032, 0, 0), (0, 0, -90)), "metal")
    m.add(viga((-0.3, 0.1, -0.24), (0.3, 0.1, -0.24), 0.02, n=6), "metal_osc")
    tapa = m.hijo("tapa", (0, h, -d1 / 2 - 0.02))
    tapa.add(T(caja(w1 + 0.06, 0.06, d1 + 0.06), (0, 0.03, d1 / 2 + 0.02)), "contenedor")
    tapa.add(T(caja(w1 * 0.6, 0.03, 0.08), (0, 0.06, d1 + 0.02)), "contenedor_osc")
    return m


def contenedor():
    m = Modelo("contenedor")
    w0, d0, w1, d1, h = 1.8, 1.0, 2.0, 1.3, 1.3
    m.add(hull([(sx * w0 / 2, 0.15, sz * d0 / 2) for sx in (-1, 1) for sz in (-1, 1)]
               + [(sx * w1 / 2, h, sz * d1 / 2) for sx in (-1, 1) for sz in (-1, 1)]), "contenedor")
    m.add(T(caja(w1 + 0.08, 0.1, d1 + 0.08), (0, h - 0.05, 0)), "contenedor_osc")
    for x in (-0.6, 0, 0.6):
        m.add(hull([(x + sx * 0.03, 0.2, d0 / 2 + 0.01) for sx in (-1, 1)]
                   + [(x + sx * 0.03, h - 0.1, d1 / 2 + 0.01) for sx in (-1, 1)]
                   + [(x, 0.2, d0 / 2 + 0.05), (x, h - 0.1, d1 / 2 + 0.05)]), "contenedor_osc")
    # panel frontal con hoja
    m.add(T(caja(0.55, 0.4, 0.04), (-0.3, 0.75, (d0 + d1) / 4 + 0.03), (-6.5, 0, 0)), "lazo_amarillo")
    hoja = hoja_plana(0.3, 0.22, 0.01)
    hoja.apply_transform(rotation_matrix(-math.pi / 2, (1, 0, 0)))
    m.add(T(hoja, (-0.3, 0.6, (d0 + d1) / 4 + 0.06), (-6.5, 0, 0)), "contenedor_osc")
    # barras laterales para el camión
    for sx in (-1, 1):
        m.add(T(caja(0.12, 0.12, 0.9), (sx * (w1 / 2 + 0.02), 0.95, 0)), "metal_osc")
        m.add(viga((sx * (w1 / 2 + 0.12), 0.95, 0), (sx * (w1 / 2 + 0.25), 0.95, 0), 0.05, n=6), "metal")
    for sx in (-1, 1):
        for sz in (-1, 1):
            r = m.hijo(f"rueda_{'d' if sz > 0 else 't'}{'i' if sx < 0 else 'd'}", (sx * 0.75, 0.09, sz * 0.35))
            r.add(T(caja(0.06, 0.08, 0.06), (0, 0.06, 0)), "metal_osc")
            r.add(T(cilindro(0.08, 0.08, 0.05, 8), (-0.025, 0, 0), (0, 0, -90)), "goma")
    for k, (nombre, x) in enumerate((("tapa_izq", -w1 / 4), ("tapa_der", w1 / 4))):
        t = m.hijo(nombre, (x, h, -d1 / 2 - 0.04))
        t.add(hull([(sx * (w1 / 4 - 0.01), 0, 0) for sx in (-1, 1)] + [(sx * (w1 / 4 - 0.01), 0, d1 + 0.1) for sx in (-1, 1)]
                   + [(sx * (w1 / 4 - 0.01), 0.07, 0.05) for sx in (-1, 1)] + [(sx * (w1 / 4 - 0.01), 0.07, d1 + 0.05) for sx in (-1, 1)]),
              "contenedor_osc")
        t.add(T(caja(0.2, 0.05, 0.06), (0, 0.08, d1 + 0.04)), "metal_osc")
    return m


def camion_basura():
    m = Modelo("camion_basura")
    # chasis
    m.add(T(caja(2.1, 0.35, 6.4), (0, 0.75, 0)), "metal_osc")
    # cabina (frente hacia +Z)
    cz = 2.3
    m.add(hull([(sx * 1.15, 0.9, cz - 0.8) for sx in (-1, 1)] + [(sx * 1.15, 0.9, cz + 0.9) for sx in (-1, 1)]
               + [(sx * 1.15, 2.9, cz - 0.8) for sx in (-1, 1)] + [(sx * 1.1, 2.9, cz + 0.55) for sx in (-1, 1)]
               + [(sx * 1.15, 1.9, cz + 0.92) for sx in (-1, 1)]), "blanco")
    m.add(T(caja(2.34, 0.25, 1.75), (0, 1.05, cz + 0.07)), "camion")
    m.add(hull([(sx * 0.98, 2.0, cz + 0.93) for sx in (-1, 1)] + [(sx * 0.95, 2.75, cz + 0.6) for sx in (-1, 1)]
               + [(sx * 0.98, 2.0, cz + 0.88) for sx in (-1, 1)] + [(sx * 0.95, 2.75, cz + 0.55) for sx in (-1, 1)]), "cristal")
    for sx in (-1, 1):
        m.add(T(caja(0.04, 0.7, 0.9), (sx * 1.16, 2.35, cz + 0.05)), "cristal")
        m.add(T(caja(0.05, 0.85, 0.06), (sx * 1.17, 1.4, cz - 0.42)), "metal_osc")
        m.add(viga((sx * 1.15, 2.4, cz + 0.6), (sx * 1.45, 2.4, cz + 0.7), 0.025, n=4), "metal_osc")
        m.add(T(caja(0.08, 0.35, 0.18), (sx * 1.48, 2.3, cz + 0.7)), "negro")
        m.add(T(caja(0.35, 0.22, 0.05), (sx * 0.78, 1.35, cz + 0.93)), "faro")
    m.add(T(caja(2.4, 0.3, 0.25), (0, 0.9, cz + 1.02)), "metal_osc")
    for i in range(5):
        m.add(T(caja(1.0, 0.05, 0.04), (0, 1.45 + i * 0.09, cz + 0.925)), "metal_osc")
    m.add(T(caja(1.2, 0.12, 0.25), (0, 2.98, cz + 0.1)), "camion")
    m.add(T(caja(0.25, 0.12, 0.2), (0, 3.08, cz + 0.1)), "faro")
    m.add(viga((1.0, 1.2, cz - 0.9), (1.0, 3.4, cz - 0.9), 0.06, n=6), "metal")
    # caja compactadora
    bz0, bz1 = -2.95, 1.35
    pts = []
    for z in (bz0, bz1):
        for sx in (-1, 1):
            pts += [(sx * 1.2, 0.95, z), (sx * 1.2, 2.9, z), (sx * 1.0, 3.25, z)]
    m.add(hull(pts), "camion")
    for sx in (-1, 1):
        m.add(T(caja(0.03, 0.25, bz1 - bz0 - 0.2), (sx * 1.21, 1.5, (bz0 + bz1) / 2)), "blanco")
        m.add(T(caja(0.03, 0.1, bz1 - bz0 - 0.2), (sx * 1.21, 1.75, (bz0 + bz1) / 2)), "lazo_amarillo")
        for z in np.linspace(bz0 + 0.4, bz1 - 0.4, 4):
            m.add(T(caja(0.04, 1.8, 0.07), (sx * 1.215, 2.0, z)), "camion_osc")
        hoja = hoja_plana(0.7, 0.5, 0.01)
        hoja.apply_transform(rotation_matrix(-math.pi / 2, (1, 0, 0)))
        hoja.apply_transform(rotation_matrix(sx * math.pi / 2, (0, 1, 0)))
        m.add(T(hoja, (sx * 1.24, 2.35, -0.8)), "blanco")
    # tolva trasera
    pts = []
    for sx in (-1, 1):
        pts += [(sx * 1.2, 0.8, bz0), (sx * 1.2, 3.1, bz0), (sx * 1.15, 2.6, bz0 - 1.1), (sx * 1.15, 0.9, bz0 - 0.75)]
    m.add(hull(pts), "camion_osc")
    m.add(hull([(sx * 0.9, 1.15, bz0 - 0.78) for sx in (-1, 1)] + [(sx * 0.9, 2.0, bz0 - 1.0) for sx in (-1, 1)]
               + [(sx * 0.9, 1.15, bz0 - 0.7) for sx in (-1, 1)] + [(sx * 0.9, 2.0, bz0 - 0.92) for sx in (-1, 1)]), "negro")
    for sx in (-1, 1):
        m.add(T(caja(0.15, 0.3, 0.06), (sx * 1.0, 2.75, bz0 - 1.0)), "rojo_luz")
        m.add(T(caja(0.6, 0.06, 0.4), (sx * 0.7, 0.75, bz0 - 0.9)), "metal")
    # brazo elevador (animable)
    brazo = m.hijo("brazo", (0, 1.1, bz0 - 0.9))
    for sx in (-1, 1):
        brazo.add(viga((sx * 0.85, 0, 0), (sx * 0.85, 0.1, -0.6), 0.06, cuadrada=True), "metal_osc")
    brazo.add(viga((-0.85, 0.1, -0.6), (0.85, 0.1, -0.6), 0.05, cuadrada=True), "metal_osc")
    for sx in (-1, 1):
        brazo.add(T(caja(0.08, 0.06, 0.5), (sx * 0.5, 0.1, -0.85)), "metal")
    # ruedas (nodos animables, giran sobre X)
    for nombre_eje, z in (("del", cz + 0.15), ("tras1", -1.3), ("tras2", -2.4)):
        for sx in (-1, 1):
            r = m.hijo(f"rueda_{nombre_eje}_{'izq' if sx < 0 else 'der'}", (sx * 1.05, 0.55, z))
            r.add(T(cilindro(0.55, 0.55, 0.42, 12), (-0.21, 0, 0), (0, 0, -90)), "goma")
            r.add(T(cilindro(0.3, 0.3, 0.44, 8), (-0.22, 0, 0), (0, 0, -90)), "metal")
            r.add(T(cilindro(0.1, 0.1, 0.48, 6), (-0.24, 0, 0), (0, 0, -90)), "metal_osc")
        m.add(T(caja(2.6, 0.08, 1.35), (0, 1.17, z)), "negro")
    return m


def moneda():
    m = Modelo("moneda")
    # canto hacia Y (de pie), caras hacia ±Z; gira sobre Y en el juego
    Mc = M_trs((0, 0.5, 0), (90, 0, 0))
    # cuerpo de la moneda: borde elevado y redondeado, cara rehundida
    perfil = [(0.0, -0.05), (0.37, -0.05), (0.395, -0.068), (0.45, -0.07), (0.485, -0.058), (0.5, -0.03),
              (0.5, 0.03), (0.485, 0.058), (0.45, 0.07), (0.395, 0.068), (0.37, 0.05), (0.0, 0.05)]
    m.add(aplicar(torno(perfil, 32, suave=50.0), Mc), "oro")
    # estriado del canto
    for i in range(72):
        a = 2 * math.pi * i / 72
        p = np.array([math.cos(a) * 0.5, 0, math.sin(a) * 0.5])
        m.add(aplicar(T(caja(0.012, 0.05, 0.014), tuple(p), (0, -math.degrees(a), 0)), Mc), "oro_osc")
    # anillo fino de puntos junto al borde
    for sz in (1, -1):
        for i in range(28):
            a = 2 * math.pi * (i + 0.5) / 28
            m.add(T(bola(0.013, -1, escala=(1, 1, 0.5)), (math.cos(a) * 0.345, 0.5 + math.sin(a) * 0.345, sz * 0.05)), "oro_claro")
    # hoja en relieve (contorno curvo con punta) y su nervio
    contorno = []
    for i in range(17):
        tt = i / 16
        w = 0.15 * math.sin(math.pi * tt ** 0.8) ** 0.85
        contorno.append((w, -0.27 + 0.52 * tt))
    contorno += [(-x, y) for x, y in contorno[::-1][1:-1]]
    for sz in (1, -1):
        Mh = M_trs((0, 0.5, sz * 0.05), (0, 0 if sz > 0 else 180, -30))
        m.add(aplicar(T(prisma(contorno, 0.03), (0, 0, 0.0)), Mh), "oro_claro")
        m.add(aplicar(viga((0, -0.33, 0.016), (0, 0.2, 0.016), 0.011, 0.005, n=6), Mh), "oro_osc")
        for k, y in enumerate((-0.12, -0.02, 0.08)):
            for sx in (-1, 1):
                m.add(aplicar(viga((0, y, 0.016), (sx * 0.09, y + 0.08, 0.016), 0.006, 0.003, n=5), Mh), "oro_osc")
    return m


# --------------------------------------------------------------------------
# HERRAMIENTAS (origen en el agarre principal)
# --------------------------------------------------------------------------
def guantes():
    m = Modelo("guantes")
    for lado, nombre in ((-1, "guante_izq"), (1, "guante_der")):
        g = m.hijo(nombre, (lado * 0.11, 0, 0), (0, 0, lado * -8))
        g.add(hull([(sx * 0.045, sy * 0.05, sz * 0.02) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
                   + [(sx * 0.04, 0.06, 0) for sx in (-1, 1)] + [(0, 0, 0.028)]), "guante")
        for i, (x, L) in enumerate([(-0.032, 0.065), (-0.011, 0.078), (0.011, 0.075), (0.032, 0.06)]):
            g.add(viga((x, 0.05, 0), (x * 1.15, 0.05 + L, 0.008), 0.012, 0.011, n=6), "guante")
            g.add(T(bola(0.011, 0), (x * 1.15, 0.05 + L, 0.008)), "guante")
        g.add(viga((lado * 0.042, -0.01, 0.01), (lado * 0.085, 0.04, 0.02), 0.013, 0.012, n=6), "guante")
        g.add(T(bola(0.012, 0), (lado * 0.085, 0.04, 0.02)), "guante")
        g.add(T(cilindro(0.055, 0.062, 0.07, 10), (0, -0.12, 0), s=(1, 1, 0.55)), "puno_guante")
        g.add(T(cilindro(0.052, 0.052, 0.012, 10), (0, -0.05, 0), s=(1, 1, 0.5)), "guante_osc")
        for x in (-0.02, 0.02):
            g.add(T(caja(0.012, 0.05, 0.005), (x, 0.0, 0.022)), "guante_osc")
    return m


def hoz():
    m = Modelo("hoz")
    m.add(tubo([(0, -0.28, 0), (0, -0.18, 0), (0, -0.05, 0), (0, 0.04, 0)], [0.024, 0.026, 0.023, 0.02], 10, tapa=False), "madera")
    m.add(T(bola(0.026, 2, escala=(1, 0.6, 1)), (0, -0.282, 0)), "madera_osc")
    m.add(T(cilindro(0.023, 0.023, 0.06, 8), (0, 0.03, 0)), "metal_osc")
    for y in (0.035, 0.075):
        m.add(T(torno([(0.022, -0.004), (0.025, 0.0), (0.022, 0.004)], 10), (0, y, 0)), "metal")
    # cordón de cuero en la base del mango
    for k in range(6):
        m.add(T(torno([(0.025, -0.005), (0.029, 0.0), (0.025, 0.005)], 10), (0, -0.24 + k * 0.011, 0), (0, 0, 8)), "madera_osc")
    c = np.array([0.17, 0.12, 0])
    R = 0.18
    prev = None
    N = 14
    for i in range(N + 1):
        f = i / N
        a = math.radians(200 - f * 230)
        p = c + np.array([math.cos(a) * R, math.sin(a) * R, 0])
        w = 0.045 * (1 - f) + 0.004
        if prev is not None:
            pa, wa = prev
            # cuchilla: hacia el centro del arco
            na = (c - pa) / np.linalg.norm(c - pa)
            nb = (c - p) / np.linalg.norm(c - p)
            q = [pa, p, pa + na * wa, p + nb * w]
            pts = [tuple(x + np.array([0, 0, dz])) for x in q for dz in (-0.004, 0.004)]
            m.add(hull(pts), "acero")
            m.add(hull([tuple(x + np.array([0, 0, dz])) for x in (pa, p, pa - na * 0.008, p - nb * 0.008) for dz in (-0.006, 0.006)]), "acero_osc")
        prev = (p, w)
    m.add(viga((0, 0.08, 0), tuple(c + np.array([math.cos(math.radians(200)) * R, math.sin(math.radians(200)) * R, 0])), 0.012, n=5), "acero_osc")
    return m


def tijeras_podar():
    m = Modelo("tijeras_podar")
    piv = np.array([0, 0.55, 0])
    for lado in (-1, 1):
        base = np.array([lado * 0.09, 0, 0])
        m.add(viga(base, piv + np.array([lado * 0.015, -0.03, lado * 0.008]), 0.012, n=6), "acero_osc")
        m.add(viga(base + np.array([0, -0.03, 0]), base + np.array([lado * 0.02, 0.2, 0]), 0.022, n=8), "mango_rojo")
        m.add(T(cilindro(0.026, 0.026, 0.02, 8), tuple(base + np.array([0, -0.04, 0]))), "mango_negro")
        # estrías de agarre y virola metálica
        for k in range(5):
            p = base + np.array([lado * 0.02 * (0.1 + k * 0.17), 0.02 + k * 0.03, 0])
            m.add(T(torno([(0.0225, -0.004), (0.0245, 0.0), (0.0225, 0.004)], 10), tuple(p), (0, 0, -lado * 5.7)), "mango_negro")
        m.add(T(cilindro(0.017, 0.015, 0.035, 10), tuple(base + np.array([lado * 0.02, 0.2, 0])), (0, 0, -lado * 5.7)), "metal")
    # cuchillas
    m.add(hull([tuple(piv + np.array(p)) for p in [(-0.02, -0.01, 0.005), (0.02, -0.01, 0.005), (0.035, 0.12, 0.005), (0.0, 0.2, 0.005),
                                                   (-0.02, -0.01, 0.0), (0.035, 0.12, 0.0), (0.0, 0.2, 0.0)]]), "acero")
    m.add(hull([tuple(piv + np.array(p)) for p in [(0.02, -0.01, -0.005), (-0.02, -0.01, -0.005), (-0.03, 0.1, -0.005), (-0.005, 0.16, -0.005),
                                                   (0.02, -0.01, -0.012), (-0.03, 0.1, -0.012), (-0.005, 0.16, -0.012)]]), "acero_osc")
    m.add(T(cilindro(0.015, 0.015, 0.03, 8), tuple(piv + np.array([0, 0, -0.015])), (90, 0, 0)), "metal_osc")
    return m


def rastrillo():
    m = Modelo("rastrillo")
    m.add(T(cilindro(0.018, 0.018, 1.45, 8), (0, -0.2, 0)), "madera")
    m.add(T(cilindro(0.022, 0.022, 0.15, 8), (0, 1.1, 0)), "verde_rastrillo")
    m.add(T(cilindro(0.025, 0.016, 0.12, 8), (0, -0.32, 0)), "verde_rastrillo")
    cuello = np.array([0, -0.32, 0])
    n = 15
    for i in range(n):
        a = math.radians(-38 + 76 * i / (n - 1))
        d = np.array([math.sin(a), -math.cos(a), 0])
        fin = cuello + d * 0.48
        m.add(viga(cuello + d * 0.03, fin, 0.008, 0.006, n=4, cuadrada=True), "verde_rastrillo")
        m.add(viga(fin, fin + np.array([0, -0.01, 0.05]), 0.006, n=4, cuadrada=True), "verde_rastrillo")
    prev = None
    for i in range(9):
        a = math.radians(-36 + 72 * i / 8)
        p = cuello + np.array([math.sin(a), -math.cos(a), 0]) * 0.28 + np.array([0, 0, 0.008])
        if prev is not None:
            m.add(viga(prev, p, 0.008, n=4, cuadrada=True), "metal")
        prev = p
    return m


def extruir(poligono, prof, z0=0.0):
    """Polígono (estrellado desde su centroide, no hace falta que sea convexo) extruido en Z."""
    P = np.asarray(poligono, float)
    c = P.mean(0)
    n = len(P)
    V, U = [], []
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        for z, orden in ((z0 + prof / 2, (0, 1, 2)), (z0 - prof / 2, (0, 2, 1))):
            tri = [(c[0], c[1], z), (a[0], a[1], z), (b[0], b[1], z)]
            V += [tri[k] for k in orden]
            U += [(tri[k][0], tri[k][1]) for k in orden]
        q = [(a[0], a[1], z0 + prof / 2), (a[0], a[1], z0 - prof / 2), (b[0], b[1], z0 - prof / 2), (b[0], b[1], z0 + prof / 2)]
        for k in (0, 1, 2, 0, 2, 3):
            V.append(q[k]), U.append((q[k][0] + q[k][1], q[k][2]))
    V, U = np.array(V).reshape(-1, 3, 3), np.array(U).reshape(-1, 3, 2)
    fn = np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0])
    if np.sum(fn[:, 2] * np.sign(V[:, 0, 2] - z0 + 1e-9)) < 0:  # polígono en sentido horario
        V, U = V[:, [0, 2, 1]], U[:, [0, 2, 1]]
    return _malla(V, U, 30.0)


def machete():
    m = Modelo("machete")
    # mango ergonómico (sección ovalada, abultado en el centro) con remaches y pomo
    ov = lambda i, a: 1.0 / math.sqrt(math.cos(a) ** 2 + (math.sin(a) / 0.62) ** 2)
    m.add(tubo([(0, -0.075, 0), (0, -0.04, 0), (0, 0.0, 0), (0, 0.04, 0), (0, 0.075, 0)],
               [0.021, 0.024, 0.022, 0.023, 0.02], 12, mod=ov), "mango_negro")
    m.add(T(bola(0.024, 2, escala=(1, 0.6, 0.7)), (0, -0.078, 0)), "mango_negro")
    for y in (-0.035, 0.0, 0.035):
        for sz in (-1, 1):
            m.add(T(cilindro(0.0055, 0.0055, 0.004, 8), (0, y, sz * 0.0145), (90 * sz, 0, 0)), "metal")
    m.add(T(caja_redondeada(0.062, 0.03, 0.014, 0.006), (0.0, 0.082, 0), (90, 0, 0)), "acero_osc")
    # hoja con punta de clip: lomo recto, vientre curvo
    hoja = [(-0.021, 0.09), (0.022, 0.09), (0.03, 0.2), (0.041, 0.32), (0.05, 0.43), (0.047, 0.5),
            (0.028, 0.548), (0.002, 0.566), (-0.012, 0.535), (-0.02, 0.47), (-0.021, 0.3)]
    m.add(extruir(hoja, 0.006), "acero")
    # filo: tira más clara a lo largo del vientre
    filo = [(0.017, 0.1), (0.022, 0.09), (0.03, 0.2), (0.041, 0.32), (0.05, 0.43), (0.047, 0.5), (0.028, 0.548),
            (0.02, 0.54), (0.038, 0.495), (0.041, 0.43), (0.032, 0.32), (0.022, 0.2)]
    m.add(extruir(filo, 0.0068), "metal")
    m.add(extruir([(-0.021, 0.095), (-0.012, 0.095), (-0.012, 0.47), (-0.02, 0.47)], 0.0075), "acero_osc")
    return m


def desbrozadora():
    m = Modelo("desbrozadora")
    # eje inclinado a lo largo de Y; origen en el manillar
    m.add(T(cilindro(0.017, 0.017, 1.5, 8), (0, -1.0, 0)), "metal_osc")
    top = np.array([0, 0.5, 0])
    m.add(T(hull([(sx * 0.07, y, sz * 0.09) for sx in (-1, 1) for sz in (-1, 1) for y in (0, 0.18)] + [(0, 0.24, 0)]), tuple(top)), "naranja_motor")
    m.add(T(cilindro(0.06, 0.06, 0.12, 10), tuple(top + np.array([-0.06, 0.08, 0])), (0, 0, 90)), "mango_negro")
    m.add(T(caja(0.1, 0.06, 0.1), tuple(top + np.array([0, 0.2, -0.04]))), "mango_negro")
    m.add(T(cilindro(0.03, 0.03, 0.02, 8), tuple(top + np.array([0.0, 0.1, 0.09])), (90, 0, 0)), "rojo_luz")
    # manillar de bicicleta
    m.add(T(cilindro(0.02, 0.02, 0.06, 6), (0, -0.03, 0)), "mango_negro")
    for sx in (-1, 1):
        m.add(viga((0, 0.0, 0), (sx * 0.28, 0.06, 0.1), 0.012, n=6), "metal_osc")
        m.add(viga((sx * 0.28, 0.06, 0.1), (sx * 0.34, 0.08, 0.15), 0.02, n=8), "mango_negro")
    m.add(T(cilindro(0.025, 0.025, 0.25, 8), (0, 0.15, 0)), "mango_negro")
    # cabezal y protector
    hb = np.array([0, -1.0, 0])
    m.add(T(cilindro(0.03, 0.05, 0.08, 8), tuple(hb + np.array([0, -0.08, 0]))), "naranja_motor")
    m.add(T(cilindro(0.06, 0.06, 0.05, 10), tuple(hb + np.array([0, -0.13, 0]))), "mango_negro")
    pts = []
    for i in range(9):
        a = math.radians(180 * i / 8)
        pts += [(math.cos(a) * 0.17, -0.11, -math.sin(a) * 0.17 + 0.0), (math.cos(a) * 0.17, -0.06, -math.sin(a) * 0.17)]
    pts += [(0.17, -0.11, 0.02), (-0.17, -0.11, 0.02)]
    m.add(T(hull(pts), tuple(hb)), "naranja_motor")
    for a in (0, 180):
        m.add(T(caja(0.2, 0.006, 0.006), tuple(hb + np.array([math.cos(math.radians(a)) * 0.1, -0.125, 0.05]))), "amarillo_hilo")
    # carrete del hilo con su tapa y nervios del protector
    m.add(T(cilindro(0.045, 0.045, 0.02, 12), tuple(hb + np.array([0, -0.15, 0]))), "amarillo_hilo")
    m.add(T(cilindro(0.05, 0.03, 0.02, 12), tuple(hb + np.array([0, -0.17, 0]))), "mango_negro")
    for i in range(5):
        a = math.radians(20 + i * 35)
        m.add(T(caja(0.012, 0.012, 0.16), tuple(hb + np.array([math.cos(a) * 0.08, -0.055, -math.sin(a) * 0.08])), (0, math.degrees(a) + 90, 0)),
              "naranja_motor")
    # motor: depósito translúcido, tapa del filtro, bujía y arrancador
    m.add(T(caja_redondeada(0.12, 0.08, 0.1, 0.025), tuple(top + np.array([0.0, 0.02, 0.0]))), "blanco")
    m.add(T(cilindro(0.018, 0.018, 0.02, 10), tuple(top + np.array([0.04, 0.06, 0.0]))), "mango_negro")
    m.add(T(caja_redondeada(0.1, 0.06, 0.03, 0.015), tuple(top + np.array([0.0, 0.14, 0.095])), (90, 0, 0)), "mango_negro")
    for k in range(4):
        m.add(T(caja(0.07, 0.006, 0.004), tuple(top + np.array([0, 0.125 + k * 0.012, 0.112]))), "naranja_motor")
    m.add(T(cilindro(0.012, 0.012, 0.03, 8), tuple(top + np.array([0.0, 0.24, -0.02]))), "blanco")
    m.add(T(cilindro(0.016, 0.016, 0.025, 8), tuple(top + np.array([0.0, 0.265, -0.02]))), "mango_negro")
    m.add(T(cilindro(0.015, 0.015, 0.05, 8), tuple(top + np.array([-0.12, 0.08, 0.0])), (0, 0, 90)), "mango_rojo")
    # anilla del arnés y gatillo
    m.add(T(torno([(0.026, -0.006), (0.032, 0.0), (0.026, 0.006)], 12), (0.0, -0.25, 0.0)), "metal")
    m.add(T(caja(0.012, 0.035, 0.02), (0.31, 0.04, 0.1)), "mango_rojo")
    return m


def motosierra():
    m = Modelo("motosierra")
    # cuerpo
    m.add(hull([(sx * 0.08, y, z) for sx in (-1, 1) for y in (0, 0.2) for z in (-0.18, 0.12)] + [(sx * 0.07, 0.24, -0.1) for sx in (-1, 1)]), "naranja_motor")
    m.add(T(caja(0.17, 0.08, 0.2), (0, 0.04, -0.02)), "mango_negro")
    m.add(T(cilindro(0.07, 0.07, 0.03, 10), (0.085, 0.12, -0.05), (0, 0, -90)), "mango_negro")
    m.add(T(cilindro(0.02, 0.02, 0.04, 6), (0.12, 0.12, -0.05), (0, 0, -90)), "mango_rojo")
    for i in range(4):
        m.add(T(caja(0.005, 0.12, 0.012), (-0.082, 0.11, -0.12 + i * 0.03)), "mango_negro")
    # asa superior
    pts = [(0, 0.2, -0.15), (0, 0.32, -0.12), (0, 0.34, 0.0), (0.0, 0.26, 0.1)]
    for a, b in zip(pts[:-1], pts[1:]):
        m.add(viga(a, b, 0.018, n=6), "mango_negro")
    # asa trasera
    m.add(viga((0, 0.08, -0.18), (0, 0.12, -0.36), 0.02, n=6), "mango_negro")
    m.add(viga((0, 0.02, -0.18), (0, 0.06, -0.36), 0.016, n=6), "mango_negro")
    m.add(viga((0, 0.06, -0.36), (0, 0.12, -0.36), 0.02, n=6), "mango_negro")
    m.add(T(caja(0.015, 0.05, 0.03), (0, 0.06, -0.3)), "mango_rojo")
    # freno de cadena
    m.add(T(caja(0.16, 0.12, 0.015), (0, 0.24, 0.13), (20, 0, 0)), "mango_negro")
    # espada y cadena
    m.add(T(caja(0.012, 0.075, 0.5), (0.0, 0.08, 0.36)), "acero")
    m.add(T(cilindro(0.0375, 0.0375, 0.012, 10), (0.006, 0.08, 0.61), (0, 0, 90)), "acero")
    m.add(T(caja(0.008, 0.09, 0.53), (0.0, 0.08, 0.36)), "acero_osc")
    m.add(T(cilindro(0.045, 0.045, 0.008, 10), (0.004, 0.08, 0.62), (0, 0, 90)), "acero_osc")
    # cadena: dientes a lo largo del contorno de la espada
    for z in np.linspace(0.13, 0.6, 22):
        for sy in (-1, 1):
            m.add(T(caja(0.011, 0.012, 0.014), (0.0, 0.08 + sy * 0.048, z), (0, 0, 0)), "acero_osc")
            m.add(T(hull([(-0.004, 0, 0), (0.004, 0, 0), (-0.004, 0, 0.012), (0.004, 0, 0.012), (0, sy * 0.01, 0.002)]),
                    (0.0, 0.08 + sy * 0.054, z - 0.004)), "metal")
    for i in range(9):
        a = math.radians(-90 + i * 22.5)
        m.add(T(caja(0.011, 0.012, 0.012), (0.0, 0.08 + math.sin(a) * 0.05, 0.62 + math.cos(a) * 0.05), (-math.degrees(a), 0, 0)), "acero_osc")
    # remaches de la espada, escape con rejilla, tirador de arranque y tapón de gasolina
    for z in (0.16, 0.2):
        m.add(T(cilindro(0.008, 0.008, 0.016, 8), (-0.008, 0.08, z), (0, 0, 90)), "metal")
    m.add(T(caja_redondeada(0.05, 0.09, 0.04, 0.01), (0.075, 0.1, 0.06), (0, 90, 0)), "metal_osc")
    for k in range(4):
        m.add(T(caja(0.006, 0.07, 0.004), (0.1, 0.1, 0.045 + k * 0.01)), "negro")
    m.add(T(cilindro(0.022, 0.022, 0.012, 10), (-0.09, 0.16, -0.08), (0, 0, 90)), "mango_negro")
    m.add(viga((-0.11, 0.16, -0.08), (-0.11, 0.16, -0.12), 0.006, n=5), "mango_negro")
    m.add(T(cilindro(0.012, 0.012, 0.05, 8), (-0.11, 0.16, -0.12), (0, 90, 90)), "mango_rojo")
    m.add(T(cilindro(0.022, 0.024, 0.02, 12), (0.0, 0.24, -0.13)), "mango_rojo")
    # franja decorativa
    for sx in (-1, 1):
        m.add(T(caja(0.004, 0.035, 0.22), (sx * 0.081, 0.15, -0.03)), "negro")
    return m


def cortacesped():
    """Cortacésped de empuje. Origen en el manillar (agarre); el suelo queda en y = -0.9 y la
    máquina hacia +Z, delante de las manos."""
    m = Modelo("cortacesped")
    s = -0.9  # suelo
    # carcasa con esquinas redondeadas en planta y faldón
    m.add(T(caja_redondeada(0.52, 0.6, 0.12, 0.1), (0, s + 0.17, 0.68), (90, 0, 0)), "rojo_cortacesped")
    m.add(T(caja_redondeada(0.56, 0.64, 0.05, 0.11), (0, s + 0.1, 0.68), (90, 0, 0)), "rojo_cortacesped_osc")
    m.add(T(caja_redondeada(0.3, 0.12, 0.03, 0.04), (0, s + 0.235, 0.98), (90, 0, 0)), "mango_negro")
    # motor, tapa del filtro y tirador de arranque
    m.add(T(cilindro(0.115, 0.1, 0.14, 16), (0, s + 0.23, 0.7)), "mango_negro")
    m.add(T(cilindro(0.1, 0.06, 0.06, 16), (0, s + 0.37, 0.7)), "rojo_cortacesped")
    for k in range(6):
        a = math.radians(k * 60)
        m.add(T(caja(0.01, 0.1, 0.03), (math.cos(a) * 0.112, s + 0.29, 0.7 + math.sin(a) * 0.112), (0, -k * 60, 0)), "metal_osc")
    m.add(T(cilindro(0.022, 0.022, 0.04, 8), (0.09, s + 0.42, 0.62)), "rojo_luz")
    m.add(viga((0.09, s + 0.44, 0.62), (0.12, s + 0.44, 0.5), 0.004, n=4), "mango_negro")
    m.add(T(cilindro(0.012, 0.012, 0.06, 8), (0.12, s + 0.44, 0.5), (0, 0, 90)), "mango_rojo")
    # ruedas
    for sx in (-1, 1):
        for z, r in ((0.45, 0.1), (0.92, 0.085)):
            m.add(T(cilindro(r, r, 0.045, 16), (sx * 0.29 - 0.0225, s + r, z), (0, 0, -90)), "goma")
            m.add(T(cilindro(r * 0.55, r * 0.55, 0.05, 12), (sx * 0.29 - 0.025, s + r, z), (0, 0, -90)), "metal")
            m.add(T(cilindro(r * 0.2, r * 0.2, 0.055, 8), (sx * 0.29 - 0.0275, s + r, z), (0, 0, -90)), "rojo_cortacesped_osc")
    # saco recogedor detrás de la carcasa
    m.add(hull([(sx * 0.2, s + y, z) for sx in (-1, 1) for (y, z) in ((0.12, 0.38), (0.36, 0.38), (0.12, 0.1), (0.3, 0.08))]), "pantalon")
    m.add(T(caja(0.42, 0.02, 0.3), (0, s + 0.37, 0.24)), "mango_negro")
    # manillar: dos tubos desde la carcasa hasta las manos, travesaño con espuma y palanca
    for sx in (-1, 1):
        m.add(tubo([(sx * 0.22, s + 0.2, 0.42), (sx * 0.22, s + 0.5, 0.25), (sx * 0.22, 0.0, 0.0)], 0.013, 8), "metal_osc")
        m.add(T(caja(0.03, 0.03, 0.04), (sx * 0.22, s + 0.2, 0.42)), "mango_negro")
    m.add(viga((-0.23, 0.0, 0.0), (0.23, 0.0, 0.0), 0.017, n=10), "mango_negro")
    m.add(tubo([(-0.2, -0.02, 0.0), (-0.18, -0.06, 0.07), (0.18, -0.06, 0.07), (0.2, -0.02, 0.0)], 0.007, 6), "metal")
    m.add(T(caja(0.06, 0.03, 0.02), (0.15, -0.12, 0.05), (30, 0, 0)), "mango_rojo")
    return m


def basurero():
    """Basurero (el que vacía el contenedor). Origen en los pies, frente a +Z.
    Nodos animables: pierna_izq/der (cadera), brazo_izq/der (hombro)."""
    m = Modelo("basurero")
    # piernas con bota y banda reflectante
    for sx, nombre in ((-1, "pierna_izq"), (1, "pierna_der")):
        p = m.hijo(nombre, (sx * 0.1, 0.9, 0))
        p.add(tubo([(0, 0.02, 0), (0, -0.4, 0.01), (0, -0.78, 0)], [0.085, 0.075, 0.07], 12), "pantalon")
        p.add(T(torno([(0.074, -0.02), (0.08, 0.0), (0.074, 0.02)], 12), (0, -0.55, 0.0)), "reflectante")
        p.add(T(bola(0.08, 2, escala=(1.0, 0.65, 1.55)), (0, -0.84, 0.05)), "bota")
        p.add(T(cilindro(0.075, 0.075, 0.06, 12), (0, -0.86, 0.0)), "bota")
    # cuerpo: barriguita con chaleco naranja y bandas reflectantes
    m.add(torno([(0.0, 0.82), (0.17, 0.84), (0.21, 0.95), (0.23, 1.12), (0.22, 1.3), (0.19, 1.42), (0.1, 1.48), (0.0, 1.49)], 16), "chaleco")
    for y in (1.02, 1.2):
        m.add(T(torno([(0.23, -0.022), (0.238, 0.0), (0.231, 0.022)], 16, ), (0, y, 0), s=(1.0, 1.0, 1.0)), "reflectante")
    m.add(T(torno([(0.165, -0.03), (0.178, 0.0), (0.165, 0.03)], 16), (0, 0.86, 0)), "bota")  # cinturón
    m.add(T(caja(0.06, 0.05, 0.02), (0, 0.86, 0.172)), "metal")
    m.add(T(cilindro(0.06, 0.07, 0.06, 12), (0, 1.46, 0)), "piel")  # cuello
    # brazos (hombro como pivote) con guantes
    for sx, nombre in ((-1, "brazo_izq"), (1, "brazo_der")):
        b = m.hijo(nombre, (sx * 0.24, 1.38, 0))
        b.add(T(bola(0.075, 2), (0, 0, 0)), "chaleco")
        b.add(tubo([(0, 0, 0), (sx * 0.04, -0.26, 0.02), (sx * 0.05, -0.5, 0.06)], [0.065, 0.055, 0.048], 10), "piel")
        b.add(T(torno([(0.06, -0.035), (0.066, 0.0), (0.058, 0.04)], 10), (sx * 0.02, -0.12, 0.01)), "chaleco")
        b.add(T(bola(0.065, 2, escala=(0.85, 1.0, 1.1)), (sx * 0.05, -0.56, 0.07)), "guante")
    # cabeza: nariz, orejas, ojos de dibujo, bigote, sonrisa y gorra
    cab = np.array([0, 1.66, 0])
    m.add(T(bola(0.16, 3, escala=(1.0, 1.05, 0.98)), tuple(cab)), "piel")
    m.add(T(bola(0.045, 2, escala=(1.0, 0.9, 1.1)), tuple(cab + [0, -0.01, 0.16])), "piel_osc")
    for sx in (-1, 1):
        m.add(T(bola(0.04, 1, escala=(0.5, 1.0, 0.8)), tuple(cab + [sx * 0.158, 0.0, 0.0])), "piel_osc")
    ojos(m, tuple(cab + [0, 0.045, 0.135]), 0.055, 0.032)
    for sx in (-1, 1):
        m.add(tubo([cab + [sx * 0.005, -0.045, 0.172], cab + [sx * 0.05, -0.055, 0.16], cab + [sx * 0.085, -0.075, 0.135]],
                   [0.022, 0.018, 0.008], 8), "pelo")
    m.add(tubo([cab + [-0.04, -0.09, 0.148], cab + [0, -0.1, 0.155], cab + [0.04, -0.09, 0.148]], 0.006, 6), "pupila")
    m.add(T(torno([(0.0, 0.0), (0.168, 0.0), (0.166, 0.05), (0.14, 0.11), (0.08, 0.15), (0.0, 0.16)], 16), tuple(cab + [0, 0.06, 0])), "gorra")
    m.add(T(cilindro(0.12, 0.12, 0.012, 16), tuple(cab + [0, 0.06, 0.13]), s=(1.0, 1.0, 0.9)), "gorra")
    m.add(T(bola(0.02, 1), tuple(cab + [0, 0.22, 0])), "gorra")
    m.add(T(caja(0.08, 0.04, 0.01), tuple(cab + [0, 0.14, 0.152]), (-30, 0, 0)), "reflectante")
    return m


# --------------------------------------------------------------------------
# BICHOS (frente hacia +Z)
# --------------------------------------------------------------------------
def ojos(m, centro, sep, r, mirada=(0, 0, 1), col_ojo="ojo_blanco", cejas=None):
    """Ojos de dibujo animado: globo, pupila y brillo. cejas: color de unas cejas enfadadas."""
    d = np.asarray(mirada, float)
    d /= np.linalg.norm(d)
    for sx in (-1, 1):
        c = np.asarray(centro) + np.array([sx * sep, 0, 0])
        m.add(T(bola(r, 1), tuple(c)), col_ojo)
        m.add(T(bola(r * 0.55, 1), tuple(c + d * r * 0.6)), "pupila")
        m.add(T(bola(r * 0.18, 0), tuple(c + d * r * 0.95 + np.array([r * 0.2, r * 0.3, 0]))), "ojo_blanco")
        if cejas:
            a = c + np.array([sx * r * 0.95, r * 1.25, r * 0.25])
            b = c + np.array([-sx * r * 0.55, r * 0.95, r * 0.7])
            m.add(tubo([a, (a + b) / 2 + [0, r * 0.12, 0], b], [r * 0.16, r * 0.2, r * 0.15], 6), cejas)


def escarabajo():
    m = Modelo("escarabajo")
    y = 0.17
    m.add(T(bola(0.2, 2, escala=(0.9, 0.5, 1.15)), (0, y, 0)), "bicho_osc")
    for sx in (-1, 1):
        pts = []
        for i in range(12):
            a = math.pi * i / 11
            for k in range(6):
                e = math.pi / 2 * k / 5
                x = abs(math.cos(e) * math.sin(a)) * 0.2 + 0.006
                pts.append((sx * x, math.sin(e) * 0.16, math.cos(e) * math.cos(a) * 0.26))
        m.add(T(hull(pts), (0, y, -0.03)), "caparazon")
        m.add(T(bola(0.035, 1, escala=(1, 0.5, 2)), (sx * 0.09, y + 0.15, -0.06), (-20, 0, 0)), "caparazon_brillo")
    m.add(T(bola(0.11, 1, escala=(1.1, 0.8, 0.9)), (0, y + 0.02, 0.23)), "bicho_osc")
    ojos(m, (0, y + 0.08, 0.29), 0.055, 0.042, cejas="caparazon")
    # pronoto (escudo entre cabeza y élitros)
    m.add(T(bola(0.13, 2, escala=(1.15, 0.6, 0.6)), (0, y + 0.06, 0.17)), "caparazon")
    for sx in (-1, 1):
        # antenas acodadas con maza
        m.add(tubo([(sx * 0.03, y + 0.1, 0.3), (sx * 0.07, y + 0.2, 0.33), (sx * 0.1, y + 0.3, 0.4)], [0.009, 0.008, 0.007], 6), "bicho_osc")
        m.add(T(bola(0.024, 1, escala=(1, 1, 1.4)), (sx * 0.1, y + 0.3, 0.41)), "bicho_osc")
        # mandíbulas curvas
        m.add(tubo([(sx * 0.035, y - 0.02, 0.31), (sx * 0.04, y - 0.03, 0.36), (sx * 0.008, y - 0.035, 0.39)],
                   [0.014, 0.01, 0.004], 6, tapa=False), "bicho_osc")
    for i, z in enumerate((0.1, 0.0, -0.1)):
        for sx in (-1, 1):
            p = m.hijo(f"pata_{'izq' if sx < 0 else 'der'}_{i + 1}", (sx * 0.12, y - 0.02, z))
            rod = np.array((sx * 0.09, 0.07, z * 0.5))
            pie = np.array((sx * 0.13, -y + 0.012, z * 0.75))
            p.add(T(bola(0.026, 0), (0, 0, 0)), "bicho_osc")
            p.add(tubo([(0, 0, 0), rod * 0.5 + [0, 0.02, 0], rod], [0.024, 0.022, 0.018], 7), "bicho_osc")
            p.add(T(bola(0.019, 0), tuple(rod)), "caparazon")
            p.add(tubo([rod, (rod + pie) / 2 + [sx * 0.012, 0, 0], pie], [0.017, 0.014, 0.011], 7), "bicho_osc")
            p.add(T(bola(0.016, 0, escala=(1.2, 0.6, 1.4)), tuple(pie + [sx * 0.008, 0.004, 0.006])), "bicho_osc")
    return m


def caracol():
    m = Modelo("caracol")
    # cuerpo: un solo tubo blando que se estrecha hacia la cola y se levanta en la cabeza
    pts = np.array([(0, 0.035, -0.44), (0, 0.06, -0.34), (0, 0.085, -0.18), (0, 0.095, 0.0),
                    (0, 0.11, 0.14), (0, 0.16, 0.24), (0, 0.21, 0.29)])
    rad = [0.012, 0.05, 0.085, 0.1, 0.1, 0.092, 0.08]
    cuerpo = tubo(pts, rad, 14, mod=lambda i, a: 1.0 + 0.12 * math.cos(2 * a), tapa=False)
    aplicar(cuerpo, M_trs(s=(1.0, 1.0, 1.0)))
    m.add(cuerpo, "caracol_cuerpo")
    m.add(T(bola(0.08, 2, escala=(1.05, 1.0, 1.0)), tuple(pts[-1])), "caracol_cuerpo")
    # arrugas de la piel (anillos algo más oscuros) y el pie
    for z in np.linspace(-0.3, 0.12, 6):
        y = np.interp(z, pts[:, 2], pts[:, 1])
        r = np.interp(z, pts[:, 2], rad)
        m.add(T(torno([(r * 1.01, -0.006), (r * 1.04, 0.0), (r * 1.01, 0.006)], 12), (0, y, z), (90, 0, 0)), "caracol_cuerpo_osc")
    m.add(T(bola(0.25, 2, escala=(0.62, 0.07, 1.5)), (0, 0.016, -0.06)), "caracol_cuerpo_osc")
    for sx in (-1, 1):
        base = np.array([sx * 0.035, 0.25, 0.3])
        tip = np.array([sx * 0.085, 0.43, 0.36])
        m.add(tubo([base, (base + tip) / 2 + [sx * 0.005, 0, -0.01], tip], [0.02, 0.016, 0.013], 8), "caracol_cuerpo")
        m.add(T(bola(0.042, 2), tuple(tip)), "ojo_blanco")
        m.add(T(bola(0.024, 1), (tip[0] + sx * 0.004, tip[1] + 0.004, tip[2] + 0.028)), "pupila")
        m.add(T(bola(0.008, 0), (tip[0] + sx * 0.012, tip[1] + 0.016, tip[2] + 0.042)), "ojo_blanco")
        m.add(tubo([(sx * 0.04, 0.17, 0.34), (sx * 0.065, 0.14, 0.39), (sx * 0.085, 0.125, 0.42)], [0.013, 0.009, 0.006], 6),
              "caracol_cuerpo_osc")
    # sonrisa
    m.add(tubo([(-0.035, 0.19, 0.362), (0.0, 0.178, 0.37), (0.035, 0.19, 0.362)], 0.005, 5), "pupila")
    # concha: volumen de caracola (esfera achatada por los lados) con la espiral marcada
    # en relieve en las dos caras y un labio en la boca
    c0 = np.array([0, 0.36, -0.08])
    R, ax = 0.215, 0.64
    m.add(T(bola(R, 3, escala=(ax, 1, 1.02)), tuple(c0)), "concha")
    for sx in (-1, 1):
        sp = []
        for i in range(60):
            t = i / 59
            ang = 0.3 + t * math.pi * 4.2
            rr = 0.012 * math.exp(0.2 * ang) * 1.0
            rr = min(rr, R * 0.93)
            y, z = math.sin(ang) * rr, -math.cos(ang) * rr
            x = ax * math.sqrt(max(R * R - y * y - z * z, 0.0)) + 0.002
            sp.append(c0 + np.array([sx * x, y, z]))
        rs = np.linspace(0.006, 0.016, 60)
        m.add(tubo(sp, rs, 6, tapa=False), "concha_osc")
        m.add(T(bola(0.02, 1, escala=(0.5, 1, 1)), tuple(sp[0])), "concha_osc")
    # labio de la boca, apoyado en el lomo
    m.add(T(torno([(0.11, -0.012), (0.125, 0.0), (0.11, 0.012)], 16), tuple(c0 + [0, -R * 0.88, 0.06]), (8, 0, 0), s=(0.62, 1, 1)), "concha_osc")
    return m


def avispa():
    m = Modelo("avispa")
    y = 0.6  # vuela; el origen queda en el suelo, bajo el cuerpo
    m.add(T(bola(0.11, 1, escala=(1, 0.95, 1.1)), (0, y, 0)), "avispa_negra")
    m.add(T(bola(0.075, 1, escala=(1.0, 0.9, 1.1)), (0, y + 0.03, 0.06)), "avispa_amarilla")
    m.add(T(bola(0.1, 1), (0, y + 0.03, 0.16)), "avispa_amarilla")
    # ojos compuestos (rojos) a los lados y ojos de dibujo delante, con cejas de enfado
    for sx in (-1, 1):
        m.add(T(bola(0.045, 1, escala=(0.7, 1.15, 0.85)), (sx * 0.078, y + 0.045, 0.17)), "ojo_avispa")
    ojos(m, (0, y + 0.06, 0.238), 0.042, 0.034, cejas="avispa_negra")
    for sx in (-1, 1):
        m.add(tubo([(sx * 0.03, y + 0.11, 0.22), (sx * 0.065, y + 0.2, 0.27), (sx * 0.08, y + 0.24, 0.3),
                    (sx * 0.1, y + 0.245, 0.36)], [0.008, 0.007, 0.007, 0.006], 6), "avispa_negra")
        m.add(tubo([(sx * 0.025, y - 0.03, 0.24), (sx * 0.02, y - 0.05, 0.265), (sx * 0.005, y - 0.055, 0.28)],
                   [0.012, 0.008, 0.002], 6), "avispa_negra")
    # abdomen a rayas, inclinado hacia abajo-atrás
    d = np.array([0, -0.45, -1.0])
    d /= np.linalg.norm(d)
    base = np.array([0, y - 0.02, -0.08])
    segs = [0.11, 0.13, 0.13, 0.11, 0.085, 0.055]
    for i, r in enumerate(segs):
        p = base + d * (0.06 + i * 0.065)
        m.add(T(bola(r, 1, escala=(1, 0.9, 0.7)), tuple(p)), "avispa_amarilla" if i % 2 == 0 else "avispa_negra")
    tip = base + d * (0.06 + 6 * 0.065)
    m.add(viga(tuple(tip - d * 0.04), tuple(tip + d * 0.08), 0.02, 0.0, n=4), "avispa_negra")
    for i in range(3):
        for sx in (-1, 1):
            a = (sx * 0.05, y - 0.08, 0.04 - i * 0.05)
            b = (sx * 0.1, y - 0.2, 0.06 - i * 0.07)
            m.add(viga(a, b, 0.01, n=4), "avispa_negra")
            m.add(viga(b, (sx * 0.11, y - 0.3, 0.02 - i * 0.07), 0.008, n=4), "avispa_amarilla")
    for sx, nombre in ((-1, "ala_izq"), (1, "ala_der")):
        ala = m.hijo(nombre, (sx * 0.06, y + 0.1, 0.0))
        ala.add(T(bola(0.2, 1, escala=(1, 0.06, 0.38)), (sx * 0.19, 0.03, -0.04), (0, sx * 15, sx * 12)), "ala")
        ala.add(T(bola(0.13, 1, escala=(1, 0.06, 0.35)), (sx * 0.13, 0.0, -0.1), (0, sx * 35, sx * 8)), "ala")
    return m


# --------------------------------------------------------------------------
# UI EN 3D (origen en el centro; la cara visible mira a +Z)
# --------------------------------------------------------------------------
def cartel_tienda():
    m = Modelo("cartel_tienda")
    rng = np.random.default_rng(31)
    for sx in (-1, 1):
        m.add(T(caja(0.14, 2.3, 0.14), (sx * 1.0, 1.15, -0.06)), "ui_madera_osc")
    for i in range(3):
        m.add(T(caja(2.3, 0.36, 0.08), (0, 1.25 + i * 0.37, 0), (0, 0, rng.uniform(-1.2, 1.2))),
              "ui_madera" if i % 2 else "ui_madera_clara")
    for i in range(3):
        for sx in (-1, 1):
            m.add(T(cilindro(0.025, 0.025, 0.02, 6), (sx * 1.0, 1.25 + i * 0.37, 0.04), (90, 0, 0)), "metal_osc")
    m.add(T(prisma([(-1.35, 0), (1.35, 0), (0, 0.4)], 0.3), (0, 2.28, -0.03)), "ui_madera_osc")
    m.add(T(caja(2.8, 0.08, 0.36), (0, 2.26, -0.03)), "ui_madera_osc")
    m.add(T(caja(0.9, 0.36, 0.04), (0, 0.65, 0.0)), "ui_papel")
    for sx in (-1, 1):
        m.add(viga((sx * 0.35, 0.85, 0.0), (sx * 0.35, 1.07, 0.0), 0.01, n=4), "ui_cuerda")
    return m


def boton_madera():
    m = Modelo("boton_madera")
    m.add(caja_redondeada(1.6, 0.55, 0.14, 0.14), "ui_madera_osc")
    m.add(T(caja_redondeada(1.48, 0.43, 0.06, 0.1), (0, 0.0, 0.08)), "ui_madera")
    m.add(T(caja_redondeada(1.3, 0.12, 0.02, 0.05), (0, 0.11, 0.115)), "ui_madera_clara")
    for sx in (-1, 1):
        m.add(T(cilindro(0.03, 0.03, 0.02, 6), (sx * 0.66, 0, 0.11), (90, 0, 0)), "metal_osc")
    return m


def boton_verde():
    m = Modelo("boton_verde")
    m.add(caja_redondeada(1.6, 0.55, 0.14, 0.2), "ui_verde_osc")
    m.add(T(caja_redondeada(1.48, 0.43, 0.06, 0.16), (0, 0.0, 0.08)), "ui_verde")
    m.add(T(caja_redondeada(1.2, 0.1, 0.02, 0.05), (0, 0.12, 0.115)), "hoja_clara")
    return m


def panel_madera():
    m = Modelo("panel_madera")
    m.add(caja_redondeada(3.0, 2.0, 0.12, 0.18), "ui_madera_osc")
    for i in range(4):
        m.add(T(caja(2.7, 0.42, 0.06), (0, -0.66 + i * 0.44, 0.07)), "ui_madera" if i % 2 else "ui_madera_clara")
    for sx in (-1, 1):
        for sy in (-1, 1):
            m.add(T(cilindro(0.04, 0.04, 0.03, 6), (sx * 1.3, sy * 0.85, 0.1), (90, 0, 0)), "metal_osc")
    return m


def flecha_mejora():
    m = Modelo("flecha_mejora")
    for col, s, z in (("ui_verde_osc", 1.12, -0.03), ("ui_verde", 1.0, 0.03)):
        m.add(T(prisma([(-0.18 * s, -0.5 * s), (0.18 * s, -0.5 * s), (0.18 * s, 0.05), (-0.18 * s, 0.05)], 0.12), (0, -0.05 * (s - 1), z)), col)
        m.add(T(prisma([(-0.45 * s, 0.0), (0.45 * s, 0.0), (0, 0.5 * s)], 0.12), (0, -0.05 * (s - 1), z)), col)
    m.add(T(prisma([(-0.06, -0.4), (0.0, -0.4), (0.0, 0.0), (-0.06, 0.0)], 0.02), (-0.06, 0, 0.1)), "hoja_clara")
    return m


def icono_hoja():
    m = Modelo("icono_hoja")
    pts = [(0, -0.5), (0.25, -0.3), (0.35, 0.0), (0.25, 0.3), (0, 0.55), (-0.25, 0.3), (-0.35, 0.0), (-0.25, -0.3)]
    m.add(prisma(pts, 0.08), "otono_naranja")
    m.add(T(prisma([(x * 1.12, y * 1.08) for x, y in pts], 0.04), (0, 0, -0.03)), "otono_marron")
    m.add(T(prisma([(-0.02, -0.7), (0.02, -0.7), (0.02, 0.4), (-0.02, 0.4)], 0.1), (0, 0, 0.01)), "otono_marron")
    for y, sgn in ((-0.15, 1), (-0.15, -1), (0.12, 1), (0.12, -1)):
        m.add(viga((0, y, 0.05), (sgn * 0.2, y + 0.15, 0.05), 0.012, n=4, cuadrada=True), "otono_marron")
    return m


def etiqueta_precio():
    m = Modelo("etiqueta_precio")
    m.add(prisma([(-0.3, -0.4), (0.3, -0.4), (0.3, 0.25), (0, 0.45), (-0.3, 0.25)], 0.05), "ui_papel")
    m.add(T(cilindro(0.06, 0.06, 0.052, 10), (0, 0.27, -0.026), (90, 0, 0)), "ui_madera_osc")
    m.add(T(cilindro(0.035, 0.035, 0.054, 10), (0, 0.27, -0.027), (90, 0, 0)), "ui_fondo_barra")
    m.add(viga((0, 0.27, 0.03), (0.15, 0.65, 0.0), 0.01, n=4), "ui_cuerda")
    m.add(T(caja(0.5, 0.03, 0.01), (0, -0.25, 0.03)), "ui_madera_clara")
    return m


def barra_progreso():
    m = Modelo("barra_progreso")
    m.add(caja_redondeada(3.0, 0.45, 0.12, 0.2), "ui_madera_osc")
    m.add(T(caja_redondeada(2.8, 0.3, 0.04, 0.13), (0, 0, 0.06)), "ui_fondo_barra")
    # el relleno tiene el origen a la izquierda: escala X de 0 a 1 = progreso
    r = m.hijo("relleno", (-1.38, 0, 0.09))
    r.add(T(caja(2.76, 0.24, 0.04), (1.38, 0, 0)), "ui_verde")
    r.add(T(caja(2.76, 0.06, 0.042), (1.38, 0.06, 0.002)), "hoja_clara")
    m.add(T(T(icono_hoja_malla(), s=0.5), (-1.55, 0, 0.1)), "otono_naranja")
    return m


def icono_hoja_malla():
    pts = [(0, -0.5), (0.25, -0.3), (0.35, 0.0), (0.25, 0.3), (0, 0.55), (-0.25, 0.3), (-0.35, 0.0), (-0.25, -0.3)]
    return prisma(pts, 0.1)


# --------------------------------------------------------------------------
CATALOGO = {
    "entorno": [casa, valla, puerta_jardin, parcela, suelo_cesped, camino_piedra, calva_tierra, cesped_nuevo],
    "vegetacion": [lambda: arbol("arbol_gigante", ("hojas_verde", "hojas_osc"), 1, alto=8.5, r0=0.62, tam_carta=2.2),
                   lambda: arbol("arbol_otono", ("hojas_otono", "hojas_otono"), 2, alto=7.0, r0=0.5),
                   hierbajo, hierbajo_grande, matorral, zarza, girasol_gigante, amapola_gigante,
                   seta_gigante, tocon, roca, monton_hojas, alfombra_hojas],
    "jugabilidad": [bolsa_basura, saco_semillas, cubo_basura, contenedor, camion_basura, moneda, basurero],
    "herramientas": [guantes, hoz, tijeras_podar, rastrillo, machete, cortacesped, desbrozadora, motosierra],
    "enemigos": [escarabajo, caracol, avispa],
    "ui": [corazon, cartel_tienda, panel_madera, boton_madera, boton_verde, flecha_mejora,
           icono_hoja, etiqueta_precio, barra_progreso],
}


def main(filtro):
    ruta_indice = os.path.join(SALIDA, "indice.json")
    indice = json.load(open(ruta_indice)) if os.path.exists(ruta_indice) else {}
    for categoria, fns in CATALOGO.items():
        for fn in fns:
            if filtro and getattr(fn, "__name__", "") not in filtro and fn.__name__ != "<lambda>":
                continue
            mod = fn()
            if filtro and mod.nombre not in filtro:
                continue
            tris = mod.exportar(os.path.join(SALIDA, mod.nombre + ".gltf"))
            lo, hi = mod.limites()
            indice[mod.nombre] = {"categoria": categoria, "min": [round(float(x), 3) for x in lo],
                                  "max": [round(float(x), 3) for x in hi], "tris": tris}
            print(f"{categoria:13s} {mod.nombre:18s} {tris:7d} tris")
    with open(ruta_indice, "w") as f:
        json.dump(indice, f, indent=1)
    print(f"{len(indice)} modelos en {SALIDA}")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
