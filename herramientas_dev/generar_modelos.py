#!/usr/bin/env python3
"""
Generador procedural de modelos low-poly para "Jugo" (juego incremental de jardín).

Cada modelo se construye a base de primitivas convexas (cajas, troncos de cono,
esferas deformadas...) con sombreado plano y una paleta de colores común, y se
exporta a .glb (glTF binario), que Godot 4 importa directamente.

Uso:
    pip install trimesh numpy scipy
    python3 herramientas_dev/generar_modelos.py            # genera todo
    python3 herramientas_dev/generar_modelos.py casa moneda # solo esos

Convenciones:
    - Unidades en metros, eje Y hacia arriba.
    - El frente de los modelos mira hacia +Z.
    - El origen está en la base (en el suelo) salvo en herramientas (origen en
      el agarre) y UI (origen en el centro).
    - Las piezas que se animan (ruedas, tapas, alas, patas, puertas...) son
      nodos hijos con su origen en el punto de giro.
"""
import math
import os
import sys

import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix, translation_matrix
from trimesh.visual.material import PBRMaterial

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "assets", "modelos")

# --------------------------------------------------------------------------
# Paleta (colores sRGB en hex). Se convierten a lineal al exportar.
# --------------------------------------------------------------------------
PALETA = {
    # casa
    "estuco": "#EADFC4", "estuco_osc": "#D8CBAA",
    "madera": "#C07F43", "madera_clara": "#D9A066", "madera_osc": "#7E4C26",
    "tejado": "#5F5A72", "tejado_osc": "#46425A",
    "piedra": "#B3ACA2", "piedra_osc": "#8C857C",
    "cristal": "#3E5568", "cristal_luz": "#7FA3BF",
    "metal": "#A7AFB6", "metal_osc": "#5D656C",
    # vegetación
    "hoja": "#6AAA3A", "hoja_clara": "#94C94B", "hoja_osc": "#3F7A2E",
    "hoja_muy_osc": "#2C5A28",
    "hierba": "#7DB443", "hierba_clara": "#A9CF57", "hierba_osc": "#4E8A30",
    "seco": "#CDB46A", "tierra": "#7A5236", "tierra_osc": "#5A3B26",
    "tronco": "#8A5A36", "tronco_osc": "#5E3C24", "corteza_clara": "#B88B5C",
    "otono_naranja": "#E8822E", "otono_amarillo": "#F2B33D",
    "otono_rojo": "#C9452E", "otono_marron": "#A0612E",
    "petalo_amarillo": "#F6C72F", "petalo_amarillo_osc": "#E3A51F",
    "petalo_rojo": "#D93A35", "petalo_rojo_osc": "#A82828",
    "petalo_blanco": "#F4F1E6", "centro_flor": "#5A3A1E", "negro": "#1E1C22",
    "zarza": "#4A3B4E", "zarza_hoja": "#4F7D34", "mora": "#3A1D4A",
    "seta_roja": "#D8453A", "seta_crema": "#F1E6CC",
    "musgo": "#6E9A3A",
    # jugabilidad
    "plastico_negro": "#2B2B33", "plastico_negro_brillo": "#43434F",
    "lazo_amarillo": "#F2C230",
    "contenedor": "#3F7F52", "contenedor_osc": "#2D5E3C",
    "camion": "#E8762C", "camion_osc": "#B9561D", "blanco": "#F0EEE8",
    "goma": "#26262B", "faro": "#FFE6A0", "rojo_luz": "#D8352E",
    "oro": "#F2C14E", "oro_osc": "#C9922B", "oro_claro": "#FBE08A",
    # herramientas
    "guante": "#7FB8A0", "guante_osc": "#5C9580", "puno_guante": "#E6D9B8",
    "acero": "#C9D0D6", "acero_osc": "#7E878F", "mango_rojo": "#C8372D",
    "mango_negro": "#2E2E35", "naranja_motor": "#EE7A22", "verde_rastrillo": "#58A85A",
    "amarillo_hilo": "#F5D33A",
    # bichos
    "caparazon": "#3B6FB5", "caparazon_brillo": "#5E93D6", "bicho_osc": "#232533",
    "ojo_blanco": "#FFFFFF", "pupila": "#141418",
    "caracol_cuerpo": "#B9C46C", "caracol_cuerpo_osc": "#97A355",
    "concha": "#C98A4B", "concha_osc": "#9C6334",
    "avispa_amarilla": "#F4C430", "avispa_negra": "#26232A", "ala": "#DDEFFF",
    "ojo_avispa": "#7A1E2A",
    # ui
    "ui_madera": "#B8773C", "ui_madera_clara": "#E0AE72", "ui_madera_osc": "#6E4122",
    "ui_verde": "#5DBB4F", "ui_verde_osc": "#3A7F33", "ui_papel": "#F3E6C8",
    "ui_cuerda": "#B79B6B", "ui_fondo_barra": "#3A2A1E",
}

# Materiales con propiedades especiales: (metallic, roughness, alpha)
ESPECIALES = {
    "cristal": (0.1, 0.25, 1.0), "cristal_luz": (0.1, 0.2, 1.0),
    # metalizado moderado: se ve bien incluso sin mapa de entorno
    "metal": (0.3, 0.45, 1.0), "metal_osc": (0.3, 0.5, 1.0),
    "acero": (0.35, 0.3, 1.0), "acero_osc": (0.3, 0.4, 1.0),
    "oro": (0.3, 0.35, 1.0), "oro_osc": (0.3, 0.4, 1.0), "oro_claro": (0.25, 0.3, 1.0),
    "plastico_negro": (0.0, 0.35, 1.0), "plastico_negro_brillo": (0.0, 0.3, 1.0),
    "caparazon": (0.25, 0.3, 1.0), "caparazon_brillo": (0.25, 0.25, 1.0),
    "ala": (0.0, 0.2, 0.45), "ojo_blanco": (0.0, 0.3, 1.0), "pupila": (0.0, 0.2, 1.0),
    "faro": (0.0, 0.2, 1.0), "mora": (0.0, 0.3, 1.0),
}


def hex_a_lineal(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def material(nombre):
    met, rough, alpha = ESPECIALES.get(nombre, (0.0, 0.85, 1.0))
    col = hex_a_lineal(PALETA[nombre]) + [alpha]
    return PBRMaterial(
        name=nombre, baseColorFactor=col, metallicFactor=met, roughnessFactor=rough,
        alphaMode="BLEND" if alpha < 1.0 else "OPAQUE", doubleSided=alpha < 1.0,
    )


# --------------------------------------------------------------------------
# Primitivas
# --------------------------------------------------------------------------
def hull(puntos):
    return trimesh.convex.convex_hull(np.asarray(puntos, dtype=float))


def caja(sx, sy, sz):
    return trimesh.creation.box((sx, sy, sz))


def cilindro(r0, r1, h, n=8, rot=0.0):
    """Tronco de cono a lo largo de Y, base en y=0."""
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n + rot
        pts.append((r0 * math.cos(a), 0, r0 * math.sin(a)))
        if r1 > 1e-5:
            pts.append((r1 * math.cos(a), h, r1 * math.sin(a)))
    if r1 <= 1e-5:
        pts.append((0, h, 0))
    return hull(pts)


def bola(r, sub=1, jitter=0.0, semilla=0, escala=(1, 1, 1)):
    m = trimesh.creation.icosphere(subdivisions=sub, radius=r)
    if jitter > 0:
        rng = np.random.default_rng(semilla)
        f = 1 + rng.uniform(-jitter, jitter, size=(len(m.vertices), 1))
        m.vertices = m.vertices * f
    m.vertices = m.vertices * np.asarray(escala)
    return m


def prisma(poligono, prof):
    """Prisma convexo: polígono en el plano XY extruido en Z (centrado)."""
    pts = [(x, y, -prof / 2) for x, y in poligono] + [(x, y, prof / 2) for x, y in poligono]
    return hull(pts)


def caja_redondeada(sx, sy, sz, r, n=6):
    """Caja con esquinas redondeadas en el plano XY (grosor en Z)."""
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


def T(m, t=(0, 0, 0), r=(0, 0, 0), s=1.0):
    m = m.copy()
    m.apply_transform(M_trs(t, r, s))
    return m


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
    A = trimesh.geometry.align_vectors([0, 1, 0], d / L)
    m.apply_transform(A)
    m.apply_translation(p0)
    return m


def hoja_plana(largo, ancho, grosor=0.02):
    """Hoja con forma de rombo apuntando a +Z, base en el origen."""
    return hull([(0, 0, 0), (0, 0, largo), (ancho / 2, 0, largo * 0.4),
                 (-ancho / 2, 0, largo * 0.4), (0, grosor, largo * 0.4),
                 (0, -grosor, largo * 0.4)])


def brizna(alto, ancho, inclinacion=(0.0, 0.0), curva=0.35):
    """Brizna de hierba en dos tramos (se dobla hacia `inclinacion`)."""
    dx, dz = inclinacion
    base = [(-ancho, 0, 0), (ancho, 0, 0), (0, 0, ancho * 0.5)]
    mid_y = alto * 0.55
    mid = [(x * 0.6 + dx * curva, mid_y, z * 0.6 + dz * curva) for x, _, z in base]
    punta = (dx, alto, dz)
    return [hull(base + mid), hull(mid + [punta])]


# --------------------------------------------------------------------------
# Modelo (árbol de nodos con mallas agrupadas por material)
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

    def _volcar(self, escena, padre):
        escena.graph.update(frame_from=padre, frame_to=self.nombre, matrix=self.matriz)
        for color, lista in sorted(self.mallas.items()):
            m = trimesh.util.concatenate(lista)
            m.unmerge_vertices()  # sombreado plano
            m.visual = trimesh.visual.TextureVisuals(
                uv=np.zeros((len(m.vertices), 2)), material=material(color))
            nombre = f"{self.nombre}_{color}"
            escena.add_geometry(m, node_name=nombre, geom_name=nombre,
                                parent_node_name=self.nombre)
        for h in self.hijos:
            h._volcar(escena, self.nombre)

    def exportar(self, ruta):
        escena = trimesh.Scene()
        self._volcar(escena, escena.graph.base_frame)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "wb") as f:
            f.write(escena.export(file_type="glb", include_normals=True))
        return escena


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
    m.add(viga(base, top, 0.015, n=4), "hoja_osc")
    m.add(T(hoja_plana(0.12, 0.06), (x, y + alto * 0.4, z), (0, rng.uniform(0, 360), -20)), "hoja")
    for i in range(6):
        a = i * 60 + rng.uniform(0, 20)
        m.add(T(hoja_plana(0.08, 0.06, 0.01), top, (0, a, 0)), color)
    m.add(T(bola(0.035, 0), top), "centro_flor")


def casa():
    m = Modelo("casa")
    rng = np.random.default_rng(7)
    W, D, H, base = 8.0, 6.0, 3.0, 0.45
    top = base + H
    m.add(T(caja(W + 0.3, base, D + 0.3), (0, base / 2, 0)), "piedra")
    # hiladas de piedra del zócalo
    for i in range(26):
        lado = rng.integers(4)
        u = rng.uniform(-0.48, 0.48)
        yy = rng.choice([0.12, 0.32])
        if lado < 2:
            p = (u * W, yy, (D / 2 + 0.16) * (1 if lado == 0 else -1))
            s = (rng.uniform(0.3, 0.6), 0.15, 0.04)
        else:
            p = ((W / 2 + 0.16) * (1 if lado == 2 else -1), yy, u * D)
            s = (0.04, 0.15, rng.uniform(0.3, 0.6))
        m.add(T(caja(*s), p), "piedra_osc")
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
    for lado in (1, -1):
        n = np.array([0, math.cos(th), lado * math.sin(th)])
        mid = np.array([0, ridge_y - (D / 2 + over) * math.tan(th) / 2, lado * (D / 2 + over) / 2]) + n * t / 2
        Mr = M_trs(mid, (math.degrees(th) * lado, 0, 0))
        losa = caja(W + 0.9, t, L)
        losa.apply_transform(Mr)
        m.add(losa, "tejado")
        for _ in range(34):
            tej = T(caja(rng.uniform(0.35, 0.6), 0.05, rng.uniform(0.25, 0.4)),
                    (rng.uniform(-W / 2, W / 2), t / 2 + 0.02, rng.uniform(-L / 2 + 0.2, L / 2 - 0.2)),
                    (0, rng.uniform(-6, 6), 0))
            tej.apply_transform(Mr)
            m.add(tej, "tejado_osc")
        # tablas del alero
        eave = (D / 2 + over)
        for sx in (-1, 1):
            m.add(viga((sx * (W / 2 + 0.47), ridge_y + 0.12, 0),
                       (sx * (W / 2 + 0.47), ridge_y + 0.12 - eave * math.tan(th), lado * eave),
                       0.1, cuadrada=True), "madera")
    m.add(T(caja(W + 1.0, 0.2, 0.34), (0, ridge_y + 0.12, 0)), "tejado_osc")
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
    for i in range(8):
        m.add(T(caja(0.3, 0.12, 0.05), (2.5 + rng.uniform(-0.25, 0.25), top + 1.2 + i * 0.27, -1.2 + 0.44)), "piedra_osc")
    m.add(T(caja(1.05, 0.16, 1.05), (2.5, top + 3.45, -1.2)), "piedra_osc")
    # puerta
    dz = D / 2
    dx = 1.6
    m.add(T(caja(1.1, 2.2, 0.1), (dx, base + 1.1, dz + 0.04)), "madera")
    for i in range(4):
        m.add(T(caja(0.02, 2.1, 0.11), (dx - 0.4 + i * 0.27, base + 1.1, dz + 0.045)), "madera_osc")
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
def arbol(nombre, colores, semilla=1):
    m = Modelo(nombre)
    rng = np.random.default_rng(semilla)
    pts = [(0, 0, 0), (0.2, 2.0, 0.1), (-0.1, 4.0, 0.0), (0.15, 6.0, -0.1), (0.0, 7.5, 0.0)]
    rad = [0.95, 0.75, 0.62, 0.5, 0.38]
    for i in range(len(pts) - 1):
        m.add(viga(pts[i], pts[i + 1], rad[i], rad[i + 1], n=7), "tronco")
    for i in range(6):
        a = i * 60 + rng.uniform(-15, 15)
        d = np.array([math.cos(math.radians(a)), 0, math.sin(math.radians(a))])
        m.add(viga((d[0] * 0.3, 0.6, d[2] * 0.3), tuple(d * 1.7 + np.array([0, -0.1, 0])), 0.42, 0.08, n=5), "tronco_osc")
    for i in range(10):
        a = rng.uniform(0, 2 * math.pi)
        y = rng.uniform(0.5, 6.5)
        r = np.interp(y, [0, 7.5], [0.95, 0.38])
        m.add(T(caja(0.12, rng.uniform(0.4, 0.9), 0.05), (math.cos(a) * r, y, math.sin(a) * r),
                (0, -math.degrees(a) + 90, 0)), "tronco_osc")
    ramas = []
    for i in range(4):
        a = i * 90 + rng.uniform(0, 40)
        y = rng.uniform(4.5, 6.5)
        d = np.array([math.cos(math.radians(a)), 0.8, math.sin(math.radians(a))])
        fin = np.array([0, y, 0]) + d * rng.uniform(2.6, 3.4)
        m.add(viga((0, y, 0), fin, 0.35, 0.14, n=6), "tronco")
        ramas.append(fin)
    copa = ramas + [np.array([0, 9.3, 0])]
    for i, c in enumerate(copa):
        r = rng.uniform(2.2, 2.9)
        m.add(T(bola(r, 1, 0.18, semilla * 10 + i), tuple(c + np.array([0, 0.5, 0]))), colores[i % 2])
        for k in range(3):
            off = rng.normal(0, 1, 3)
            off = off / np.linalg.norm(off) * r * 0.85
            m.add(T(bola(r * 0.45, 1, 0.2, semilla * 100 + i * 7 + k), tuple(c + off + np.array([0, 0.5, 0]))), colores[(i + k + 1) % 3])
    return m


def hierbajo():
    m = Modelo("hierbajo")
    rng = np.random.default_rng(11)
    cols = ["hierba", "hierba_osc", "hierba_clara"]
    for i in range(16):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(0, 0.28)
        h = rng.uniform(0.55, 1.1)
        b = brizna(h, rng.uniform(0.035, 0.06), (math.cos(a) * h * 0.35, math.sin(a) * h * 0.35))
        m.add([T(x, (math.cos(a) * r, 0, math.sin(a) * r), (0, rng.uniform(0, 360), 0)) for x in b], cols[i % 3])
    for i in range(3):
        a = rng.uniform(0, 2 * math.pi)
        top = (math.cos(a) * 0.25, rng.uniform(1.0, 1.3), math.sin(a) * 0.25)
        m.add(viga((0, 0, 0), top, 0.012, n=4), "hierba_osc")
        m.add(T(bola(0.05, 0, escala=(1, 2.2, 1)), top), "seco")
    return m


def hierbajo_grande():
    m = Modelo("hierbajo_grande")
    rng = np.random.default_rng(12)
    cols = ["hierba", "hierba_osc", "hierba_clara", "hoja_osc"]
    for i in range(18):
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(0, 0.55)
        h = rng.uniform(1.4, 2.7)
        b = brizna(h, rng.uniform(0.08, 0.14), (math.cos(a) * h * 0.4, math.sin(a) * h * 0.4))
        m.add([T(x, (math.cos(a) * r, 0, math.sin(a) * r), (0, rng.uniform(0, 360), 0)) for x in b], cols[i % 4])
    for i in range(7):
        a = i * 51
        m.add(T(hoja_plana(0.9, 0.45, 0.04), (0, 0.15, 0), (-20, a, 0)), "hoja")
    for i in range(3):
        a = rng.uniform(0, 2 * math.pi)
        top = (math.cos(a) * 0.7, rng.uniform(2.6, 3.1), math.sin(a) * 0.7)
        m.add(viga((0, 0, 0), top, 0.03, 0.02, n=5), "hierba_osc")
        m.add(T(bola(0.22, 1, 0.12, i), top), "petalo_blanco")
        m.add(T(bola(0.07, 0), top), "seco")
    return m


def matorral():
    m = Modelo("matorral")
    rng = np.random.default_rng(13)
    cols = ["hoja", "hoja_osc", "hoja_clara", "hoja_muy_osc"]
    centros = [(0, 0.75, 0, 0.9), (0.7, 0.55, 0.2, 0.7), (-0.6, 0.6, 0.3, 0.75),
               (0.2, 0.5, -0.6, 0.7), (-0.3, 1.35, -0.1, 0.65), (0.4, 1.2, 0.4, 0.55), (-0.8, 0.4, -0.4, 0.5)]
    for i, (x, y, z, r) in enumerate(centros):
        m.add(T(bola(r, 1, 0.2, i + 30), (x, y, z)), cols[i % 4])
    for i in range(24):
        n = rng.normal(0, 1, 3)
        n[1] = abs(n[1])
        n /= np.linalg.norm(n)
        p = np.array([0, 0.75, 0]) + n * 1.0
        yaw = math.degrees(math.atan2(n[0], n[2]))
        m.add(T(hoja_plana(0.35, 0.18, 0.02), tuple(p), (-math.degrees(math.asin(n[1])) + 10, yaw, 0)), cols[i % 3])
    for i in range(9):
        n = rng.normal(0, 1, 3)
        n[1] = abs(n[1]) + 0.3
        n /= np.linalg.norm(n)
        p = np.array([0, 0.75, 0]) + n * 1.02
        for k in range(5):
            m.add(T(hoja_plana(0.07, 0.06, 0.01), tuple(p), (-math.degrees(math.asin(n[1])), k * 72, 0)), "petalo_blanco")
        m.add(T(bola(0.03, 0), tuple(p)), "petalo_amarillo")
    return m


def zarza():
    m = Modelo("zarza")
    rng = np.random.default_rng(14)
    for s in range(8):
        a = s * 45 + rng.uniform(-15, 15)
        d = np.array([math.cos(math.radians(a)), 0, math.sin(math.radians(a))])
        alcance = rng.uniform(1.0, 1.7)
        alto = rng.uniform(1.2, 2.0)
        prev = None
        N = 9
        for i in range(N + 1):
            f = i / N
            p = d * alcance * f + np.array([0, math.sin(f * math.pi * 0.85) * alto, 0])
            p += np.array([math.sin(f * 7 + s) * 0.08, 0, math.cos(f * 6 + s) * 0.08])
            if prev is not None:
                r = 0.075 * (1 - f * 0.55)
                m.add(viga(prev, p, r, n=5), "zarza")
                for _ in range(1):
                    dirr = rng.normal(0, 1, 3)
                    dirr /= np.linalg.norm(dirr)
                    q = (prev + p) / 2
                    m.add(viga(q, q + dirr * 0.11, 0.022, 0.0, n=3), "petalo_blanco" if rng.random() < 0.15 else "zarza")
                if i % 2 == 0:
                    m.add(T(hoja_plana(0.3, 0.2, 0.015), tuple(p), (rng.uniform(-40, 10), rng.uniform(0, 360), 0)), "zarza_hoja")
                if i in (5, 7) and rng.random() < 0.7:
                    for k in range(4):
                        m.add(T(bola(0.045, 1), tuple(p + rng.normal(0, 0.04, 3) + np.array([0, -0.06, 0]))), "mora")
            prev = p
    for i in range(14):
        a = rng.uniform(0, 360)
        m.add(T(hoja_plana(0.45, 0.28, 0.02), (0, 0.1, 0), (-15, a, 0)), "zarza_hoja" if i % 2 else "hoja_muy_osc")
    for i, (x, z, r) in enumerate([(0.0, 0.0, 0.55), (0.5, 0.3, 0.4), (-0.4, -0.3, 0.45)]):
        m.add(T(bola(r, 1, 0.2, 40 + i), (x, r * 0.6, z)), "hoja_muy_osc")
    return m


def girasol_gigante():
    m = Modelo("girasol_gigante")
    pts = [(0, 0, 0), (0.12, 1.5, -0.05), (0.05, 2.8, 0.1), (0.0, 3.5, 0.3)]
    for i in range(3):
        m.add(viga(pts[i], pts[i + 1], 0.14 - i * 0.025, 0.12 - i * 0.025, n=6), "hoja_osc")
    for i, (y, a) in enumerate([(0.8, 20), (1.4, 150), (2.0, 260), (2.6, 60)]):
        m.add(T(hoja_plana(0.9 - i * 0.1, 0.6, 0.03), (0.08, y, 0), (-25, a, 0)), "hoja" if i % 2 else "hoja_clara")
    cab = []
    cab.append(("centro_flor", T(cilindro(0.55, 0.5, 0.18, 14), (0, 0, 0), (90, 0, 0))))
    cab.append(("tronco_osc", T(cilindro(0.35, 0.3, 0.2, 10), (0, 0, 0.02), (90, 0, 0))))
    cab.append(("hoja_osc", T(cilindro(0.45, 0.3, 0.2, 10), (0, 0, -0.18), (90, 0, 0))))
    Mh = M_trs((0.0, 3.55, 0.35), (25, 0, 0))
    for i in range(18):
        a = math.radians(i * 20)
        p = T(hoja_plana(0.6, 0.3, 0.03), (0, 0, 0.42))  # hacia +Z
        p.apply_transform(rotation_matrix(-math.pi / 2, (1, 0, 0)))  # ahora hacia +Y, plano XY
        p.apply_transform(rotation_matrix(a, (0, 0, 1)))
        p.apply_translation((0, 0, 0.09 + 0.015 * (i % 2)))
        cab.append(("petalo_amarillo" if i % 2 else "petalo_amarillo_osc", p))
    for col, malla in cab:
        malla.apply_transform(Mh)
        m.add(malla, col)
    return m


def amapola_gigante():
    m = Modelo("amapola_gigante")
    pts = [(0, 0, 0), (-0.15, 1.0, 0.05), (0.05, 2.0, -0.05), (0.2, 2.6, 0.15)]
    for i in range(3):
        m.add(viga(pts[i], pts[i + 1], 0.07, 0.06, n=5), "hoja_osc")
    for i, (y, a) in enumerate([(0.4, 30), (0.8, 200), (1.3, 110)]):
        m.add(T(hoja_plana(0.7, 0.35, 0.03), (0, y, 0), (-30, a, 0)), "hoja")
    top = np.array(pts[-1])
    for i in range(6):
        a = math.radians(i * 60)
        p = bola(0.42, 1, 0.12, i, escala=(0.8, 0.12, 1.0))
        p.apply_translation((0, 0, 0.38))
        p.apply_transform(rotation_matrix(math.radians(-38 if i % 2 else -52), (1, 0, 0)))
        p.apply_transform(rotation_matrix(a, (0, 1, 0)))
        p.apply_translation(top + np.array([0, 0.05, 0]))
        m.add(p, "petalo_rojo" if i % 2 else "petalo_rojo_osc")
    m.add(T(bola(0.16, 1, escala=(1, 0.7, 1)), tuple(top + np.array([0, 0.15, 0]))), "negro")
    m.add(T(bola(0.1, 1, escala=(1, 0.6, 1)), tuple(top + np.array([0, 0.24, 0]))), "hoja_osc")
    for i in range(12):
        a = math.radians(i * 30)
        q = top + np.array([math.cos(a) * 0.22, 0.28, math.sin(a) * 0.22])
        m.add(viga(top + np.array([0, 0.12, 0]), q, 0.01, n=3), "negro")
        m.add(T(bola(0.025, 0), tuple(q)), "negro")
    return m


def seta_gigante():
    m = Modelo("seta_gigante")
    rng = np.random.default_rng(15)
    m.add(viga((0, 0, 0), (0.05, 1.4, 0), 0.38, 0.27, n=9), "seta_crema")
    m.add(T(cilindro(0.42, 0.36, 0.1, 9), (0, 0.85, 0)), "petalo_blanco")
    R, Hc = 1.25, 0.8
    pts = []
    for i in range(16):
        a = 2 * math.pi * i / 16
        for k in range(5):
            e = math.pi / 2 * k / 4
            pts.append((R * math.cos(e) * math.cos(a), Hc * math.sin(e), R * math.cos(e) * math.sin(a)))
    cap = hull(pts)
    m.add(T(cap, (0.05, 1.3, 0)), "seta_roja")
    m.add(T(cilindro(R * 0.98, 0.3, 0.12, 16), (0.05, 1.18, 0)), "seta_crema")
    for i in range(11):
        a = rng.uniform(0, 2 * math.pi)
        e = rng.uniform(0.25, 1.3)
        n = np.array([R * math.cos(e) * math.cos(a), Hc * math.sin(e), R * math.cos(e) * math.sin(a)])
        nn = n / np.array([R, Hc, R]) ** 2
        nn /= np.linalg.norm(nn)
        p = n + np.array([0.05, 1.3, 0])
        s = rng.uniform(0.09, 0.18)
        mm = bola(s, 1, 0.1, i, escala=(1, 0.35, 1))
        mm.apply_transform(trimesh.geometry.align_vectors([0, 1, 0], nn))
        mm.apply_translation(p)
        m.add(mm, "petalo_blanco")
    for i in range(3):
        a = rng.uniform(0, 2 * math.pi)
        p = (math.cos(a) * 0.7, 0, math.sin(a) * 0.7)
        m.add(viga(p, (p[0], 0.3, p[2]), 0.06, 0.05, n=6), "seta_crema")
        m.add(T(hull([(0.17 * math.cos(b), 0, 0.17 * math.sin(b)) for b in np.linspace(0, 6.28, 9)] + [(0, 0.13, 0)]),
                (p[0], 0.28, p[2])), "seta_roja")
    return m


def tocon():
    m = Modelo("tocon")
    rng = np.random.default_rng(16)
    m.add(cilindro(0.75, 0.62, 0.75, 9), "tronco")
    m.add(T(cilindro(0.6, 0.58, 0.04, 9), (0, 0.75, 0)), "corteza_clara")
    m.add(T(cilindro(0.4, 0.4, 0.045, 9), (0, 0.752, 0)), "madera_clara")
    m.add(T(cilindro(0.18, 0.18, 0.05, 7), (0, 0.754, 0)), "corteza_clara")
    for i in range(5):
        a = math.radians(i * 72 + 20)
        d = np.array([math.cos(a), 0, math.sin(a)])
        m.add(viga(tuple(d * 0.4 + np.array([0, 0.35, 0])), tuple(d * 1.15 + np.array([0, -0.05, 0])), 0.25, 0.06, n=5), "tronco_osc")
    for i in range(8):
        a = rng.uniform(0, 2 * math.pi)
        m.add(T(caja(0.1, rng.uniform(0.2, 0.5), 0.05), (math.cos(a) * 0.7, rng.uniform(0.2, 0.5), math.sin(a) * 0.7),
                (0, -math.degrees(a) + 90, 0)), "tronco_osc")
    m.add(T(bola(0.35, 1, 0.2, 2, escala=(1, 0.4, 1)), (-0.35, 0.72, 0.2)), "musgo")
    for i in range(3):
        y = 0.25 + i * 0.13
        m.add(T(cilindro(0.12 - i * 0.02, 0.02, 0.05, 7), (0.66, y, 0.15 + i * 0.06)), "seta_crema")
    return m


def roca():
    m = Modelo("roca")
    m.add(T(bola(0.9, 1, 0.25, 4, escala=(1.2, 0.7, 1.0)), (0, 0.45, 0)), "piedra")
    m.add(T(bola(0.55, 1, 0.25, 5, escala=(1.0, 0.8, 1.0)), (0.9, 0.3, 0.4)), "piedra_osc")
    m.add(T(bola(0.35, 1, 0.25, 6), (-0.8, 0.2, 0.5)), "piedra")
    m.add(T(bola(0.55, 1, 0.2, 7, escala=(1.2, 0.3, 1.0)), (-0.1, 0.95, -0.1)), "musgo")
    return m


def monton_hojas():
    m = Modelo("monton_hojas")
    rng = np.random.default_rng(17)
    cols = ["otono_naranja", "otono_amarillo", "otono_rojo", "otono_marron"]
    m.add(T(bola(1.0, 1, 0.2, 8, escala=(1.2, 0.42, 1.0)), (0, 0.15, 0)), "otono_naranja")
    m.add(T(bola(0.6, 1, 0.2, 9, escala=(1.0, 0.5, 1.0)), (0.3, 0.35, -0.2)), "otono_amarillo")
    for i in range(70):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0, 1.6) ** 0.8
        y = max(0.01, 0.55 * (1 - (r / 1.3) ** 2)) if r < 1.3 else 0.01
        m.add(T(hoja_plana(0.2, 0.14, 0.008), (math.cos(a) * r, y + 0.02, math.sin(a) * r),
                (rng.uniform(-25, 25), rng.uniform(0, 360), rng.uniform(-25, 25))), cols[i % 4])
    return m


def suelo_cesped():
    m = Modelo("suelo_cesped")
    rng = np.random.default_rng(18)
    N, S = 8, 4.0
    alt = rng.uniform(-0.03, 0.05, (N + 1, N + 1))
    alt[0, :] = alt[-1, :] = alt[:, 0] = alt[:, -1] = 0
    v = [(-S / 2 + i * S / N, alt[i, j], -S / 2 + j * S / N) for i in range(N + 1) for j in range(N + 1)]
    caras = {"hierba": [], "hierba_osc": []}
    for i in range(N):
        for j in range(N):
            a, b, c, d = i * (N + 1) + j, (i + 1) * (N + 1) + j, (i + 1) * (N + 1) + j + 1, i * (N + 1) + j + 1
            for tri in ((a, d, b), (b, d, c)):
                caras["hierba" if rng.random() < 0.7 else "hierba_osc"].append(tri)
    for col, f in caras.items():
        m.add(trimesh.Trimesh(vertices=v, faces=f, process=False), col)
    m.add(T(caja(S, 0.3, S), (0, -0.19, 0)), "tierra")
    for i in range(14):
        x, z = rng.uniform(-1.8, 1.8, 2)
        for k in range(4):
            h = rng.uniform(0.12, 0.25)
            b = brizna(h, 0.02, (rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05)))
            m.add([T(q, (x + rng.uniform(-0.05, 0.05), 0, z + rng.uniform(-0.05, 0.05)), (0, rng.uniform(0, 360), 0)) for q in b], "hierba_clara")
    return m


def camino_piedra():
    m = Modelo("camino_piedra")
    rng = np.random.default_rng(19)
    for i in range(7):
        cx, cz = rng.uniform(-0.3, 0.3), -1.3 + i * 0.45 + rng.uniform(-0.05, 0.05)
        r = rng.uniform(0.25, 0.38)
        pts = []
        n = rng.integers(5, 8)
        for k in range(n):
            a = 2 * math.pi * k / n + rng.uniform(-0.2, 0.2)
            rr = r * rng.uniform(0.8, 1.15)
            pts.append((cx + math.cos(a) * rr, cz + math.sin(a) * rr))
        losa = prisma(pts, 0.08)
        losa.apply_transform(rotation_matrix(math.pi / 2, (1, 0, 0)))
        m.add(T(losa, (0, 0.03, 0)), "piedra" if i % 2 else "piedra_osc")
    return m


# --------------------------------------------------------------------------
# JUGABILIDAD
# --------------------------------------------------------------------------
def bolsa_basura():
    m = Modelo("bolsa_basura")
    b = bola(1.0, 2, 0.07, 21, escala=(0.42, 0.42, 0.38))
    v = b.vertices.copy()
    v[:, 1] = np.maximum(v[:, 1], -0.36)
    v[:, 1] += 0.36 + 0.0
    v[:, 1] *= 1.15
    b.vertices = v
    m.add(b, "plastico_negro")
    m.add(T(cilindro(0.14, 0.06, 0.12, 7), (0, 0.9, 0)), "plastico_negro")
    m.add(T(cilindro(0.075, 0.075, 0.05, 8), (0, 1.0, 0)), "lazo_amarillo")
    for i in range(4):
        a = i * 90 + 30
        m.add(T(cilindro(0.06, 0.0, 0.17, 4), (0, 1.02, 0), (35, a, 0)), "plastico_negro_brillo")
    # pliegues brillantes
    for i in range(6):
        a = math.radians(i * 60 + 10)
        m.add(viga((math.cos(a) * 0.3, 0.3, math.sin(a) * 0.27), (math.cos(a) * 0.12, 0.84, math.sin(a) * 0.1), 0.02, n=3), "plastico_negro_brillo")
    # hoja impresa
    hoja = T(hoja_plana(0.24, 0.17, 0.01), (0, -0.12, 0))
    hoja.apply_transform(rotation_matrix(-math.pi / 2, (1, 0, 0)))
    m.add(T(hoja, (0.0, 0.48, 0.4), (-12, 0, 0)), "otono_naranja")
    # hierbajos asomando
    for i in range(3):
        bz = brizna(0.3, 0.025, (0.08 * (i - 1), 0.05))
        m.add([T(q, (0.02 * (i - 1), 1.02, 0), (0, i * 60, 0)) for q in bz], "hierba")
    return m


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
    m.add(T(cilindro(0.5, 0.5, 0.12, 20), (0, 0.5, -0.06), (90, 0, 0)), "oro_osc")
    m.add(T(cilindro(0.42, 0.42, 0.14, 20), (0, 0.5, -0.07), (90, 0, 0)), "oro")
    for sz in (1, -1):
        hoja = T(hoja_plana(0.5, 0.34, 0.03), (0, 0, -0.25))
        hoja.apply_transform(rotation_matrix(-math.pi / 2, (1, 0, 0)))
        hoja.apply_transform(rotation_matrix(math.radians(-30), (0, 0, 1)))
        m.add(T(hoja, (0, 0.5, sz * 0.08)), "oro_claro")
        a = math.radians(-30)
        d = np.array([-math.sin(a), math.cos(a), 0])
        m.add(viga(tuple(np.array([0, 0.5, sz * 0.1]) - d * 0.3), tuple(np.array([0, 0.5, sz * 0.1]) + d * 0.22), 0.014, n=4), "oro_osc")
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
    m.add(T(cilindro(0.024, 0.02, 0.32, 8), (0, -0.28, 0)), "madera")
    m.add(T(cilindro(0.027, 0.027, 0.03, 8), (0, -0.28, 0)), "madera_osc")
    m.add(T(cilindro(0.023, 0.023, 0.06, 8), (0, 0.03, 0)), "metal_osc")
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


def machete():
    m = Modelo("machete")
    m.add(hull([(sx * 0.02, y, sz * 0.014) for sx in (-1, 1) for sz in (-1, 1) for y in (-0.06, 0.07)]), "mango_negro")
    for y in (-0.03, 0.03):
        m.add(T(cilindro(0.006, 0.006, 0.032, 6), (0, y, -0.016), (90, 0, 0)), "metal")
    m.add(T(caja(0.06, 0.012, 0.03), (0.0, 0.08, 0)), "acero_osc")
    pts = [(-0.018, 0.085), (0.02, 0.085), (0.05, 0.45), (0.03, 0.55), (-0.02, 0.52), (-0.022, 0.2)]
    m.add(prisma(pts, 0.006), "acero")
    m.add(prisma([(-0.02, 0.09), (-0.012, 0.09), (-0.012, 0.5), (-0.02, 0.5)], 0.008), "acero_osc")
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
    return m


# --------------------------------------------------------------------------
# BICHOS (frente hacia +Z)
# --------------------------------------------------------------------------
def ojos(m, centro, sep, r, mirada=(0, 0, 1), col_ojo="ojo_blanco"):
    d = np.asarray(mirada, float)
    d /= np.linalg.norm(d)
    for sx in (-1, 1):
        c = np.asarray(centro) + np.array([sx * sep, 0, 0])
        m.add(T(bola(r, 1), tuple(c)), col_ojo)
        m.add(T(bola(r * 0.55, 1), tuple(c + d * r * 0.6)), "pupila")
        m.add(T(bola(r * 0.18, 0), tuple(c + d * r * 0.95 + np.array([r * 0.2, r * 0.3, 0]))), "ojo_blanco")


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
    ojos(m, (0, y + 0.08, 0.29), 0.055, 0.042)
    for sx in (-1, 1):
        m.add(viga((sx * 0.03, y + 0.1, 0.3), (sx * 0.1, y + 0.3, 0.4), 0.008, n=4), "bicho_osc")
        m.add(T(bola(0.02, 0), (sx * 0.1, y + 0.3, 0.4)), "bicho_osc")
        m.add(viga((sx * 0.035, y - 0.02, 0.31), (sx * 0.01, y - 0.03, 0.37), 0.014, 0.0, n=4), "bicho_osc")
    for i, z in enumerate((0.1, 0.0, -0.1)):
        for sx in (-1, 1):
            p = m.hijo(f"pata_{'izq' if sx < 0 else 'der'}_{i + 1}", (sx * 0.12, y - 0.02, z))
            rod = (sx * 0.08, 0.06, z * 0.5)
            p.add(viga((0, 0, 0), rod, 0.024, 0.02, n=5), "bicho_osc")
            p.add(viga(rod, (sx * 0.12, -y + 0.01, z * 0.7), 0.02, 0.012, n=5), "bicho_osc")
            p.add(T(bola(0.018, 0), (sx * 0.12, -y + 0.015, z * 0.7)), "bicho_osc")
    return m


def caracol():
    m = Modelo("caracol")
    # cuerpo
    for i in range(7):
        f = i / 6
        z = -0.35 + f * 0.6
        r = 0.08 + 0.05 * math.sin(f * math.pi * 0.9)
        m.add(T(bola(r, 1, escala=(1.1, 0.75, 1.3)), (0, r * 0.7, z)), "caracol_cuerpo")
    m.add(T(bola(0.1, 1), (0, 0.17, 0.27)), "caracol_cuerpo")
    m.add(T(bola(0.25, 1, escala=(0.6, 0.08, 1.4)), (0, 0.015, -0.05)), "caracol_cuerpo_osc")
    for sx in (-1, 1):
        tip = (sx * 0.07, 0.42, 0.36)
        m.add(viga((sx * 0.03, 0.22, 0.29), tip, 0.018, 0.012, n=5), "caracol_cuerpo")
        m.add(T(bola(0.04, 1), tip), "ojo_blanco")
        m.add(T(bola(0.022, 1), (tip[0], tip[1] + 0.005, tip[2] + 0.025)), "pupila")
        m.add(viga((sx * 0.04, 0.13, 0.34), (sx * 0.08, 0.1, 0.42), 0.012, 0.006, n=4), "caracol_cuerpo_osc")
    # concha en espiral (plano YZ)
    c0 = np.array([0, 0.36, -0.08])
    for i in range(22):
        t = i / 21
        ang = t * math.pi * 3.2
        rr = 0.2 * math.exp(-1.0 * ang / math.pi * 0.75)
        p = c0 + np.array([0, math.sin(ang) * rr, -math.cos(ang) * rr])
        s = 0.16 * math.exp(-1.0 * ang / math.pi * 0.62)
        m.add(T(bola(s, 1, escala=(0.85, 1, 1)), tuple(p)), "concha" if (i // 3) % 2 == 0 else "concha_osc")
    return m


def avispa():
    m = Modelo("avispa")
    y = 0.6  # vuela; el origen queda en el suelo, bajo el cuerpo
    m.add(T(bola(0.11, 1, escala=(1, 0.95, 1.1)), (0, y, 0)), "avispa_negra")
    m.add(T(bola(0.075, 1, escala=(1.0, 0.9, 1.1)), (0, y + 0.03, 0.06)), "avispa_amarilla")
    m.add(T(bola(0.1, 1), (0, y + 0.03, 0.16)), "avispa_amarilla")
    for sx in (-1, 1):
        m.add(T(bola(0.05, 1, escala=(0.8, 1.1, 0.8)), (sx * 0.065, y + 0.05, 0.2)), "ojo_avispa")
        m.add(T(bola(0.012, 0), (sx * 0.07, y + 0.08, 0.235)), "ojo_blanco")
        m.add(viga((sx * 0.03, y + 0.11, 0.22), (sx * 0.08, y + 0.24, 0.3), 0.008, n=4), "avispa_negra")
        m.add(viga((sx * 0.08, y + 0.24, 0.3), (sx * 0.1, y + 0.24, 0.36), 0.008, n=4), "avispa_negra")
        m.add(viga((sx * 0.025, y - 0.03, 0.24), (sx * 0.005, y - 0.05, 0.27), 0.012, 0.0, n=4), "avispa_negra")
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
    "entorno": [casa, valla, puerta_jardin, suelo_cesped, camino_piedra],
    "vegetacion": [lambda: arbol("arbol_gigante", ["hoja", "hoja_osc", "hoja_clara"], 1),
                   lambda: arbol("arbol_otono", ["otono_naranja", "otono_amarillo", "otono_rojo"], 2),
                   hierbajo, hierbajo_grande, matorral, zarza, girasol_gigante,
                   amapola_gigante, seta_gigante, tocon, roca, monton_hojas],
    "jugabilidad": [bolsa_basura, cubo_basura, contenedor, camion_basura, moneda],
    "herramientas": [guantes, hoz, tijeras_podar, rastrillo, machete, desbrozadora, motosierra],
    "enemigos": [escarabajo, caracol, avispa],
    "ui": [cartel_tienda, panel_madera, boton_madera, boton_verde, flecha_mejora,
           icono_hoja, etiqueta_precio, barra_progreso],
}


def main(filtro):
    total = 0
    for carpeta, fns in CATALOGO.items():
        for fn in fns:
            mod = fn()
            if filtro and mod.nombre not in filtro:
                continue
            ruta = os.path.join(SALIDA, carpeta, mod.nombre + ".glb")
            esc = mod.exportar(ruta)
            caras = sum(len(g.faces) for g in esc.geometry.values())
            print(f"{carpeta:13s} {mod.nombre:18s} {caras:6d} tris")
            total += 1
    print(f"{total} modelos generados en {SALIDA}")


if __name__ == "__main__":
    main(set(sys.argv[1:]))
