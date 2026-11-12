#!/usr/bin/env python3
"""
Genera las texturas procedurales (repetibles) que usan los modelos.

    pip install numpy pillow
    python3 herramientas_dev/generar_texturas.py

Salida: assets/modelos/texturas/*.jpg|png  +  medias.json (color medio de cada
textura, que el generador de modelos usa para teñirlas con la paleta).

v2: el doble de resolución (1024 px en superficies), nudos y poros en la madera,
placas y musgo en la corteza, briznas pintadas en el césped, piedrecitas y
ramitas en la tierra, hojas con degradado, venas y borde, y alfa con antialias
(el corte del material sigue en 0,5, pero el borde queda suave al filtrar).
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "assets", "modelos", "texturas")
MEDIAS = {}
N = 1024  # resolución de las superficies repetibles


# ------------------------------------------------------------------ utilidades
def ruido(n, beta=2.0, semilla=0, ax=1.0, ay=1.0, m=None):
    """Ruido fractal repetible en [0,1]. ay>1 alarga los rasgos en vertical."""
    m = m or n
    rng = np.random.default_rng(semilla)
    F = np.fft.fft2(rng.normal(size=(m, n)))
    fx = np.fft.fftfreq(n)[None, :] * ax
    fy = np.fft.fftfreq(m)[:, None] * ay
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1
    F = F / f ** (beta / 2)
    F[0, 0] = 0
    r = np.real(np.fft.ifft2(F))
    lo, hi = np.percentile(r, [1, 99])
    return np.clip((r - lo) / (hi - lo), 0, 1)


def celdas(n, k, semilla, jitter=1.0, ky=None):
    """Voronoi repetible: (distancia al punto más cercano, al segundo, id de celda).
    k columnas x ky filas de celdas (ky < k da celdas alargadas en vertical)."""
    ky = ky or k
    rng = np.random.default_rng(semilla)
    gx, gy = np.meshgrid(np.arange(k), np.arange(ky), indexing="ij")
    pts = np.stack([(gx.ravel() + 0.5 + rng.uniform(-0.5, 0.5, k * ky) * jitter) / k,
                    (gy.ravel() + 0.5 + rng.uniform(-0.5, 0.5, k * ky) * jitter) / ky], -1)
    y, x = (np.mgrid[0:n, 0:n] + 0.5) / n
    d1 = np.full((n, n), 9.0)
    d2 = np.full((n, n), 9.0)
    ide = np.zeros((n, n), int)
    for i, (px, py) in enumerate(pts):
        dx = np.abs(x - px)
        dx = np.minimum(dx, 1 - dx)
        dy = np.abs(y - py)
        dy = np.minimum(dy, 1 - dy) * ky / k
        d = np.sqrt(dx * dx + dy * dy)
        nuevo = d < d1
        d2 = np.where(nuevo, d1, np.minimum(d2, d))
        ide = np.where(nuevo, i, ide)
        d1 = np.where(nuevo, d, d1)
    return d1 * k, d2 * k, ide


def mezcla(a, b, t):
    t = np.asarray(t)[..., None]
    return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t


def suavizar(h, r):
    im = Image.fromarray((np.clip(h, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im) / 255.0


def normal_de_altura(h, fuerza):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    n = np.dstack([-dx * fuerza, dy * fuerza, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def guardar(nombre, rgb, alfa=None, calidad=92):
    arr = (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)
    if alfa is None:
        Image.fromarray(arr, "RGB").save(os.path.join(SALIDA, nombre + ".jpg"), quality=calidad)
        lin = np.where(rgb <= 0.04045, rgb / 12.92, ((np.clip(rgb, 0, 1) + 0.055) / 1.055) ** 2.4)
        MEDIAS[nombre] = [float(x) for x in lin.reshape(-1, 3).mean(0)]
    else:
        a = (np.clip(alfa, 0, 1) * 255 + 0.5).astype(np.uint8)
        Image.fromarray(np.dstack([arr, a]), "RGBA").save(os.path.join(SALIDA, nombre + ".png"), optimize=True)


def guardar_normal(nombre, h, fuerza):
    # la fuerza está pensada para 512 px; a más resolución la pendiente por píxel es menor
    guardar(nombre, normal_de_altura(h, fuerza * h.shape[0] / 512), calidad=94)
    MEDIAS.pop(nombre, None)


# ------------------------------------------------------------------ superficies
def liso():
    v = 0.9 + 0.07 * ruido(512, 2.5, 1) + 0.03 * ruido(512, 1.0, 2)
    guardar("liso", np.dstack([v, v, v]))


def estuco():
    fino, grande = ruido(N, 1.0, 2), ruido(N, 3.0, 3)
    grumo = ruido(N, 2.0, 4)
    poro = np.clip((ruido(N, 0.3, 90) - 0.8) * 5, 0, 1)
    col = np.array([0.93, 0.885, 0.78]) * (0.93 + 0.07 * fino)[..., None] * (0.9 + 0.1 * grande)[..., None]
    # churretes de humedad verticales y suciedad en la parte baja de cada repetición
    ch = ruido(N, 2.2, 5, ax=1, ay=10)
    col *= (1 - 0.12 * np.clip(ch - 0.6, 0, 1) * 2.5)[..., None]
    col *= (1 - 0.18 * poro)[..., None]
    # grietas finas
    g = 1 - np.abs(2 * ruido(N, 2.0, 91) - 1)
    grieta = np.clip((g - 0.985) / 0.015, 0, 1) * np.clip((ruido(N, 3.0, 92) - 0.55) * 4, 0, 1)
    col *= (1 - 0.35 * grieta)[..., None]
    guardar("estuco", col)
    guardar_normal("estuco_n", 0.45 * fino + 0.45 * grumo - 0.4 * grieta - 0.15 * poro, 2.5)


def madera():
    n = N
    y, x = np.mgrid[0:n, 0:n] / n
    # nudos: deforman las vetas a su alrededor (distancia periódica)
    rng = np.random.default_rng(6)
    desv = np.zeros((n, n))
    oscuro = np.zeros((n, n))
    for _ in range(3):
        kx, ky = rng.uniform(0, 1, 2)
        rx, ry = rng.uniform(0.025, 0.04), rng.uniform(0.05, 0.08)
        dx = (x - kx + 0.5) % 1 - 0.5
        dy = (y - ky + 0.5) % 1 - 0.5
        d = np.sqrt((dx / rx) ** 2 + (dy / ry) ** 2)
        desv += np.sign(dx) * np.exp(-d * d / 8) * rx * 2.5
        # nudo: anillos concéntricos que se oscurecen hacia el centro
        oscuro += np.clip(1.4 - d, 0, 1) * (0.55 + 0.45 * np.sin(d * 9) ** 2) * 0.7
    onda = ruido(n, 3.0, 8, ax=1, ay=5)
    u = x + desv
    anillos = 0.5 + 0.5 * np.sin(2 * math.pi * (u * 9 + 1.6 * onda))
    veta = ruido(n, 2.0, 6, ax=1, ay=16)
    fina = ruido(n, 1.2, 7, ax=1, ay=30)
    poros = np.clip((ruido(n, 0.6, 9, ax=1, ay=40) - 0.75) * 4, 0, 1)
    val = np.clip(0.42 * veta + 0.18 * fina + 0.4 * anillos ** 1.4, 0, 1)
    col = mezcla((0.56, 0.45, 0.35), (1.0, 0.94, 0.84), val)
    col *= (1 - 0.2 * poros)[..., None]
    col *= (1 - 0.45 * np.clip(oscuro, 0, 1))[..., None]
    guardar("madera", col)
    guardar_normal("madera_n", val - 0.25 * poros - 0.4 * np.clip(oscuro, 0, 1), 2.2)


def tejas():
    n, alto, ancho = N, 128, 256
    rng = np.random.default_rng(9)
    y, x = np.mgrid[0:n, 0:n]
    fila = y // alto
    fy = (y % alto) / alto
    xs = (x + (fila % 2) * (ancho // 2)) % n
    colu = xs // ancho
    fx = (xs % ancho) / ancho
    forma = (n // alto, n // ancho)
    tono = rng.uniform(0.72, 1.12, forma)[fila, colu]
    matiz = rng.uniform(-1, 1, forma)[fila, colu]
    musgo_t = (rng.random(forma) < 0.16)[fila, colu]
    borde = rng.uniform(0.0, 0.08, forma)[fila, colu]
    base = np.array([0.40, 0.385, 0.47])[None, None, :] * tono[..., None]
    base[..., 0] += 0.03 * matiz
    base[..., 2] -= 0.03 * matiz
    # vetas de la pizarra
    base *= (0.86 + 0.28 * ruido(n, 1.5, 10, ax=1, ay=0.25))[..., None]
    # musgo que crece desde el borde inferior de algunas tejas
    m = np.clip((ruido(n, 1.8, 93) - 0.45) * 3, 0, 1) * np.clip((fy - 0.55) / 0.45, 0, 1)
    m = np.where(musgo_t, m, m * 0.25)
    base = base * (1 - m[..., None]) + np.array([0.36, 0.45, 0.2]) * m[..., None] * (0.8 + 0.4 * ruido(n, 1.0, 94))[..., None]
    sombra = np.clip(fy / 0.2, 0, 1)  # sombra bajo la hilada de arriba
    base *= (0.55 + 0.45 * sombra)[..., None]
    # esquinas redondeadas abajo y pequeños desconchones
    redondo = np.clip(1 - np.maximum(0, np.abs(fx - 0.5) * 2 - 0.86) / 0.14 * np.clip((fy - 0.8) / 0.2, 0, 1), 0, 1)
    hueco = (fx < 0.02) | (fx > 0.98) | (redondo < 0.4)
    base[hueco] *= 0.42
    canto = fy > (0.95 - borde)
    base[canto] *= 1.15
    h = fy.copy() + 0.08 * ruido(n, 1.5, 11)
    h[hueco] -= 0.5
    guardar("tejas", base)
    guardar_normal("tejas_n", h, 5.0)


def piedra_muro():
    n, alto = N, 128
    rng = np.random.default_rng(12)
    col = np.zeros((n, n, 3))
    h = np.zeros((n, n))
    x = np.arange(n)
    gr = ruido(n, 1.6, 13)
    fino = ruido(n, 0.8, 95)
    for f in range(n // alto):
        cortes = [0]
        while cortes[-1] < n - 140:
            cortes.append(cortes[-1] + int(rng.uniform(140, 300)))
        cortes = np.array(cortes)
        desfase = int(rng.uniform(0, 200))
        xs = (x + desfase) % n
        idx = np.searchsorted(cortes, xs, side="right") - 1
        izq = cortes[idx]
        der = np.where(idx + 1 < len(cortes), cortes[np.minimum(idx + 1, len(cortes) - 1)], n)
        dx = np.minimum(xs - izq, der - xs)
        tono = rng.uniform(0.74, 1.08, len(cortes))[idx]
        calido = rng.uniform(-1, 1, len(cortes))[idx]
        abombado = rng.uniform(0.7, 1.0, len(cortes))[idx]
        yy = np.arange(alto)[:, None]
        d = np.minimum(dx[None, :], np.minimum(yy, alto - 1 - yy))
        # borde irregular: el mortero entra un poco en la piedra según el ruido
        d = d - 5 * gr[f * alto:(f + 1) * alto]
        piedra = np.clip((d - 5) / 12, 0, 1)
        c = np.array([0.70, 0.67, 0.62])[None, None, :] * tono[None, :, None]
        c = np.broadcast_to(c, (alto, n, 3)).copy()
        c[..., 0] += 0.03 * calido
        c[..., 2] -= 0.03 * calido
        mortero = np.array([0.50, 0.47, 0.42])
        col[f * alto:(f + 1) * alto] = mortero * (1 - piedra[..., None]) + c * piedra[..., None]
        h[f * alto:(f + 1) * alto] = piedra ** 0.6 * abombado[None, :]
    col *= (0.84 + 0.22 * gr + 0.1 * fino)[..., None]
    guardar("piedra_muro", col)
    guardar_normal("piedra_muro_n", h + 0.2 * gr + 0.08 * fino, 4.0)


def roca():
    n = N
    a, b = ruido(n, 2.6, 14), ruido(n, 1.4, 15)
    fino = ruido(n, 0.8, 96)
    grieta = 1 - np.abs(2 * ruido(n, 2.2, 16) - 1)
    estratos = 0.5 + 0.5 * np.sin(2 * math.pi * (np.mgrid[0:n, 0:n][0] / n * 6 + 1.5 * a))
    val = 0.5 * a + 0.3 * b + 0.1 * fino + 0.1 * estratos
    col = mezcla((0.38, 0.37, 0.35), (0.75, 0.73, 0.68), val)
    col *= (1 - 0.55 * np.clip((grieta - 0.95) / 0.05, 0, 1))[..., None]
    # motas minerales y liquen
    mota = np.clip((ruido(n, 0.2, 97) - 0.85) * 8, 0, 1)
    col = col * (1 - 0.3 * mota[..., None]) + 0.3 * mota[..., None] * np.array([0.85, 0.83, 0.78])
    liquen = np.clip((ruido(n, 2.5, 17) - 0.7) * 5, 0, 1) * (0.4 + 0.3 * fino)
    col = col * (1 - liquen[..., None]) + np.array([0.58, 0.62, 0.38]) * liquen[..., None]
    guardar("roca", col)
    guardar_normal("roca_n", val - 0.35 * np.clip((grieta - 0.92) / 0.08, 0, 1) + 0.1 * liquen, 6.0)


def corteza():
    n = N
    # placas alargadas (Voronoi estirado en vertical) separadas por surcos
    d1, d2, ide = celdas(n, 9, 18, 0.9, ky=3)
    surco_v = np.clip((d2 - d1) / 0.25, 0, 1) ** 0.7
    a = ruido(n, 1.8, 18, ax=1, ay=9)
    fino = ruido(n, 1.2, 19, ax=1, ay=3)
    surco = np.abs(2 * a - 1) ** 0.6
    h = np.clip(0.6 * surco + 0.22 * surco_v + 0.18 * fino, 0, 1)
    col = mezcla((0.15, 0.1, 0.07), (0.58, 0.45, 0.33), h)
    col *= (0.85 + 0.3 * ruido(n, 2.5, 20))[..., None]
    # musgo en los surcos y algo de liquen claro
    musgo = np.clip((ruido(n, 2.2, 98) - 0.55) * 3, 0, 1) * (1 - h) ** 1.5
    col = col * (1 - musgo[..., None]) + np.array([0.3, 0.42, 0.15]) * musgo[..., None]
    liquen = np.clip((ruido(n, 1.0, 99) - 0.86) * 6, 0, 1) * h
    col = col * (1 - 0.5 * liquen[..., None]) + 0.5 * liquen[..., None] * np.array([0.7, 0.72, 0.6])
    guardar("corteza", col)
    guardar_normal("corteza_n", h, 6.0)


def cesped():
    n = N
    # poca variación a gran escala: el suelo entero repite esta textura y las manchas grandes
    # delatan la cuadrícula; el detalle va en las briznas pintadas
    a, b = ruido(n, 2.6, 21), ruido(n, 0.9, 22)
    val = 0.3 + 0.25 * a + 0.45 * b
    col = mezcla((0.17, 0.29, 0.09), (0.47, 0.6, 0.22), val)
    seco = np.clip((ruido(n, 1.6, 24) - 0.7) * 3, 0, 1) * 0.35
    col = col * (1 - seco[..., None]) + np.array([0.6, 0.56, 0.3]) * seco[..., None]
    # briznas pintadas: trazos cortos claros/oscuros (repetibles: se dibujan con desfase)
    im = Image.new("L", (n, n), 128)
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(23)
    for _ in range(26000):
        cx, cy = rng.uniform(0, n, 2)
        ang = rng.normal(-math.pi / 2, 0.5)
        L = rng.uniform(6, 16)
        v = int(rng.uniform(40, 230))
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                px, py = cx + ox, cy + oy
                if -20 < px < n + 20 and -20 < py < n + 20:
                    d.line([(px, py), (px + math.cos(ang) * L, py + math.sin(ang) * L)], fill=v, width=2)
    hebra = np.asarray(im) / 255.0
    col *= (0.78 + 0.44 * hebra)[..., None]
    # florecillas y tréboles sueltos
    flor = np.clip((ruido(n, 0.1, 100) - 0.93) * 30, 0, 1)
    col = col * (1 - flor[..., None]) + flor[..., None] * np.array([0.95, 0.93, 0.8])
    guardar("cesped", col)
    guardar_normal("cesped_n", 0.4 * b + 0.6 * hebra, 3.0)


def tierra():
    n = N
    a, b = ruido(n, 2.4, 25), ruido(n, 1.0, 26)
    val = 0.6 * a + 0.4 * b
    col = mezcla((0.26, 0.17, 0.11), (0.52, 0.39, 0.27), val)
    hum = np.clip((ruido(n, 3.0, 101) - 0.5) * 2, 0, 1)
    col *= (1 - 0.25 * hum)[..., None]
    # piedrecitas (Voronoi) y ramitas
    d1, d2, ide = celdas(n, 14, 27, 1.0)
    rng = np.random.default_rng(28)
    elegida = rng.random(14 * 14) < 0.3
    tam = rng.uniform(0.2, 0.42, 14 * 14)
    tono = rng.uniform(0.6, 1.0, 14 * 14)
    borde_irreg = 0.06 * (ruido(n, 1.5, 110) - 0.5)
    china = elegida[ide] * np.clip((tam[ide] + borde_irreg - d1) / 0.05, 0, 1)
    sombra_china = elegida[ide] * np.clip((tam[ide] + 0.08 - d1) / 0.08, 0, 1) * (1 - china)
    col *= (1 - 0.35 * sombra_china)[..., None]
    col = col * (1 - china[..., None]) + china[..., None] * np.array([0.5, 0.46, 0.4]) * tono[ide][..., None] \
        * (0.75 + 0.4 * (1 - d1 / tam[ide]).clip(0, 1) ** 0.5)[..., None] * (0.85 + 0.3 * ruido(n, 0.8, 111))[..., None]
    im = Image.new("L", (n, n), 0)
    dr = ImageDraw.Draw(im)
    for _ in range(45):
        cx, cy = rng.uniform(0, n, 2)
        ang = rng.uniform(0, math.pi)
        L = rng.uniform(40, 110)
        for ox in (-n, 0, n):
            for oy in (-n, 0, n):
                dr.line([(cx + ox, cy + oy), (cx + ox + math.cos(ang) * L, cy + oy + math.sin(ang) * L)], fill=255, width=5)
    rama = np.asarray(im.filter(ImageFilter.GaussianBlur(1.0))) / 255.0 * (1 - china)
    col = col * (1 - rama[..., None]) + rama[..., None] * np.array([0.45, 0.32, 0.2])
    guardar("tierra", col)
    guardar_normal("tierra_n", val + 0.6 * china * (1 - d1 / 0.4).clip(0, 1) + 0.3 * rama, 4.0)


def asfalto():
    n = N
    a, b = ruido(n, 0.4, 28), ruido(n, 2.8, 29)
    arido = np.clip((ruido(n, 0.15, 102) - 0.7) * 4, 0, 1)
    v = 0.19 + 0.08 * a + 0.06 * b + 0.12 * arido
    grieta = 1 - np.abs(2 * ruido(n, 2.0, 103) - 1)
    v *= 1 - 0.4 * np.clip((grieta - 0.985) / 0.015, 0, 1)
    guardar("asfalto", np.dstack([v, v, v * 1.03]))
    guardar_normal("asfalto_n", a + 0.5 * arido - 0.5 * np.clip((grieta - 0.985) / 0.015, 0, 1), 2.0)


def arrugas():
    n = N
    a = 1 - np.abs(2 * ruido(n, 2.0, 30) - 1)
    b = 1 - np.abs(2 * ruido(n, 2.4, 31, ax=1, ay=3) - 1)
    c = 1 - np.abs(2 * ruido(n, 1.4, 104) - 1)
    guardar_normal("arrugas_n", a ** 2 + 0.7 * b ** 2 + 0.25 * c ** 3, 5.0)


def anillos():
    n = 512
    y, x = np.mgrid[0:n, 0:n] / n - 0.5
    r = np.sqrt(x ** 2 + y ** 2) * (1 + 0.12 * (ruido(n, 3.0, 32) - 0.5))
    an = 0.5 + 0.5 * np.sin(r * 2 * math.pi * 26)
    an = an ** 2.2  # anillos de verano finos y oscuros
    val = np.clip(0.6 * (1 - an) + 0.4 * ruido(n, 1.5, 33), 0, 1)
    col = mezcla((0.55, 0.39, 0.24), (0.9, 0.75, 0.53), val)
    col *= (1 - 0.35 * np.clip((r - 0.36) / 0.1, 0, 1))[..., None]
    corteza_r = np.clip((r - 0.455) / 0.02, 0, 1)
    col = col * (1 - corteza_r[..., None]) + corteza_r[..., None] * np.array([0.3, 0.2, 0.13])
    ang = np.arctan2(y, x)
    grieta = (np.abs(np.sin(ang * 3.5 + 1.0)) < 0.015 + 0.02 * (r < 0.15)) & (r > 0.03) & (r < 0.32)
    col[grieta] *= 0.5
    # marcas de sierra
    sierra = 0.5 + 0.5 * np.sin((x * math.cos(0.4) + y * math.sin(0.4)) * 2 * math.pi * 70)
    col *= (0.95 + 0.05 * sierra)[..., None]
    guardar("anillos", col)


def girasol_centro():
    n = 1024
    im = Image.new("RGB", (n, n), (58, 36, 18))
    d = ImageDraw.Draw(im)
    Nn = 2200
    for i in range(Nn, 0, -1):
        r = 0.49 * n * math.sqrt(i / Nn)
        a = i * math.radians(137.508)
        cx, cy = n / 2 + r * math.cos(a), n / 2 + r * math.sin(a)
        s = 4.0 + 6.5 * (i / Nn)
        t = i / Nn
        if t < 0.25:  # centro verdoso con flores sin abrir
            col = (int(96 + 40 * (1 - t)), int(92 + 40 * (1 - t)), int(30))
        else:
            col = (int(60 + 70 * (1 - t)), int(38 + 55 * (1 - t)), int(16 + 10 * (1 - t)))
        d.ellipse([cx - s, cy - s, cx + s, cy + s], fill=(26, 15, 8))
        d.ellipse([cx - s * 0.72, cy - s * 0.82, cx + s * 0.62, cy + s * 0.5], fill=col)
        d.ellipse([cx - s * 0.35, cy - s * 0.55, cx + s * 0.05, cy - s * 0.15],
                  fill=tuple(min(255, int(c * 1.35 + 12)) for c in col))
    # anillo de florecillas amarillas en el borde
    for i in range(160):
        a = i * 2 * math.pi / 160
        r = n * (0.455 + 0.02 * math.sin(i * 1.7))
        cx, cy = n / 2 + r * math.cos(a), n / 2 + r * math.sin(a)
        d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=(214, 160, 40))
    im = im.resize((512, 512), Image.LANCZOS)
    guardar("girasol_centro", np.asarray(im) / 255.0)


def brizna():
    h, w = 512, 128
    t = (1 - np.arange(h) / (h - 1))[:, None] * np.ones((1, w))  # 0 base (abajo) → 1 punta
    col = mezcla((0.18, 0.33, 0.09), (0.58, 0.72, 0.28), t ** 0.8)
    u = np.abs(np.arange(w) / (w - 1) - 0.5)[None, :] * 2
    col *= (1.08 - 0.28 * u ** 1.5)[..., None]
    # nervio central claro y estrías longitudinales
    col *= (1 + 0.12 * np.exp(-(u / 0.07) ** 2))[..., None]
    col *= (0.9 + 0.2 * np.repeat(ruido(w, 1.5, 34)[:1, :], h, 0))[..., None]
    col *= (0.94 + 0.12 * ruido(w, 1.2, 105, ax=1, ay=20, m=h))[..., None]
    punta = np.clip((t - 0.82) / 0.18, 0, 1) * 0.55
    col = col * (1 - punta[..., None]) + np.array([0.76, 0.7, 0.36]) * punta[..., None]
    base = np.clip((0.12 - t) / 0.12, 0, 1)
    col *= (1 - 0.35 * base)[..., None]
    # 4 columnas: verde medio, claro, oscuro y seco (un único material para todas las briznas)
    tonos = [(0.85, 0.92, 0.78), (1.0, 1.0, 1.0), (0.66, 0.8, 0.6), (1.35, 1.0, 0.75)]
    guardar("brizna", np.hstack([col * np.array(t_) for t_ in tonos]))


def petalo():
    h, w = 512, 128
    t = (1 - np.arange(h) / (h - 1))[:, None] * np.ones((1, w))
    v = 0.5 + 0.5 * np.clip(t / 0.4, 0, 1) ** 0.8
    # venas en abanico desde la base
    u = np.arange(w) / (w - 1) - 0.5
    ang = u[None, :] / np.maximum(t, 0.05) ** 0.5
    vena = 0.5 + 0.5 * np.cos(ang * 2 * math.pi * 3.2)
    v = v * (0.9 + 0.1 * vena)
    raya = np.repeat(ruido(w, 1.8, 35)[:1, :], h, 0)
    v = v * (0.9 + 0.1 * raya)
    ua = np.abs(u)[None, :] * 2
    v = v * (1 - 0.1 * (1 - ua))
    borde = np.clip((ua - 0.85) / 0.15, 0, 1) * np.clip(t / 0.3, 0, 1)
    v = v * (1 + 0.08 * borde)
    guardar("petalo", np.dstack([v, v * (0.85 + 0.15 * np.clip(t / 0.5, 0, 1)), v]))


# ------------------------------------------------------------------ hojas (con alfa)
def poligono_hoja(cx, cy, ang, largo, ancho, n=14, dentado=0.0, rng=None, escala=1.0):
    """Hoja ovalada con punta; la base está en (cx,cy) y apunta hacia `ang`."""
    izq, der = [], []
    for i in range(n + 1):
        t = i / n
        w = ancho * 0.5 * math.sin(math.pi * t ** 0.75) ** 0.9 * escala
        if dentado and rng is not None and 0 < i < n:
            w *= 1 + rng.uniform(-dentado, dentado)
        izq.append((t * largo, w))
        der.append((t * largo, -w))
    pts = izq + der[::-1]
    c, s = math.cos(ang), math.sin(ang)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts]


def pintar_hoja(d, cx, cy, ang, largo, ancho, color, rng, venas=False, dentado=0.0, borde=True):
    r, g, b = color
    pts = poligono_hoja(cx, cy, ang, largo, ancho, dentado=dentado, rng=rng)
    oscuro = (int(r * 0.62), int(g * 0.66), int(b * 0.62), 255)
    d.polygon(pts, fill=(r, g, b, 255), outline=oscuro if borde else None)
    if borde and ancho > 24:
        d.line(pts + [pts[0]], fill=oscuro, width=max(1, int(ancho / 40)))
    # media hoja algo más oscura (da volumen) y brillo interior hacia la punta
    mitad = poligono_hoja(cx, cy, ang, largo, ancho)
    n = len(mitad) // 2
    eje = [(cx + math.cos(ang) * largo * i / 14, cy + math.sin(ang) * largo * i / 14) for i in range(15)]
    d.polygon(mitad[:n] + eje[::-1], fill=(int(r * 0.84), int(g * 0.86), int(b * 0.84), 255))
    brillo = poligono_hoja(cx + math.cos(ang) * largo * 0.25, cy + math.sin(ang) * largo * 0.25, ang, largo * 0.62, ancho, escala=0.45)
    nb = len(brillo) // 2
    d.polygon(brillo[nb:] + [eje[4]], fill=(min(255, int(r * 1.1 + 6)), min(255, int(g * 1.1 + 6)), min(255, int(b * 1.05 + 4)), 255))
    claro = (min(255, int(r * 1.25 + 14)), min(255, int(g * 1.2 + 14)), min(255, int(b * 1.15 + 8)), 255)
    d.line([eje[0], eje[-1]], fill=claro, width=max(1, int(ancho / 20)))
    if venas:
        for i in range(2, 13, 2):
            p = eje[i]
            for lado in (-1, 1):
                a2 = ang + lado * 0.85
                L = ancho * 0.45 * math.sin(math.pi * (i / 14) ** 0.75)
                d.line([p, (p[0] + math.cos(a2) * L, p[1] + math.sin(a2) * L)], fill=claro, width=max(1, int(ancho / 50)))


def _alfa_suave(arr):
    """Alfa con antialias (sin halos): el color bajo lo transparente se rellena con el vecino opaco."""
    alfa = arr[..., 3]
    rgb = arr[..., :3].copy()
    opaco = alfa > 0.5
    if (~opaco).any() and opaco.any():
        im = Image.fromarray((rgb * 255).astype(np.uint8))
        m = Image.fromarray((opaco * 255).astype(np.uint8))
        relleno = im.copy()
        for r in (2, 6, 16, 40):
            b = np.asarray(im.filter(ImageFilter.GaussianBlur(r))) / 255.0
            bm = np.asarray(m.filter(ImageFilter.GaussianBlur(r)))[..., None] / 255.0
            est = b / np.maximum(bm, 1e-3)
            cur = np.asarray(relleno) / 255.0
            falta = (~opaco)[..., None]
            relleno = Image.fromarray((np.where(falta, est, cur).clip(0, 1) * 255).astype(np.uint8))
        rgb = np.asarray(relleno) / 255.0
    return rgb, alfa


def racimo_hojas(nombre, paleta, semilla, n_hojas=700):
    """Racimo de hojas para las cartas de follaje. Muy tupido a propósito: Godot reduce la
    textura con mipmaps al alejarse y, si el racimo tiene muchos huecos, el alfa medio baja del
    corte (0,5) y la copa desaparece de lejos."""
    S = 2048
    rng = np.random.default_rng(semilla)
    fondo = tuple(int(x) for x in np.mean(paleta, 0))
    im = Image.new("RGBA", (S, S), fondo + (0,))
    d = ImageDraw.Draw(im)
    # relleno interior en sombra: hojas oscuras que tapan los huecos del centro
    for i in range(260):
        r = 0.36 * S * rng.uniform(0, 1) ** 0.6
        a = rng.uniform(0, 2 * math.pi)
        cx, cy = S / 2 + math.cos(a) * r, S / 2 + math.sin(a) * r
        base = np.array(paleta[rng.integers(len(paleta))], float) * rng.uniform(0.42, 0.55)
        L = rng.uniform(150, 220)
        pintar_hoja(d, cx, cy, rng.uniform(0, 2 * math.pi), L, L * 0.55, tuple(int(x) for x in base), rng, borde=False)
    # ramitas con ramificaciones
    for i in range(8):
        a = rng.uniform(0, 2 * math.pi)
        L = rng.uniform(500, 860)
        p0 = (S / 2, S / 2)
        p1 = (S / 2 + math.cos(a) * L, S / 2 + math.sin(a) * L)
        d.line([p0, p1], fill=(66, 46, 30, 255), width=14)
        for t in (0.4, 0.7):
            q = (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)
            a2 = a + rng.choice([-1, 1]) * rng.uniform(0.4, 0.8)
            d.line([q, (q[0] + math.cos(a2) * L * 0.3, q[1] + math.sin(a2) * L * 0.3)], fill=(74, 52, 34, 255), width=8)
    hojas = []
    for i in range(n_hojas):
        r = 0.45 * S * rng.uniform(0, 1) ** 0.45
        a = rng.uniform(0, 2 * math.pi)
        cx, cy = S / 2 + math.cos(a) * r, S / 2 + math.sin(a) * r
        ang = a + rng.normal(0, 1.1)
        largo = rng.uniform(140, 210)
        if max(abs(cx + math.cos(ang) * largo - S / 2), abs(cy + math.sin(ang) * largo - S / 2)) > S / 2 - 12:
            continue
        hojas.append((cx, cy, ang, largo, r))
    # las del centro (más tapadas) se pintan antes y más oscuras: oclusión pintada
    hojas.sort(key=lambda h: h[4] + rng.uniform(0, 300))
    for k, (cx, cy, ang, largo, r) in enumerate(hojas):
        base = np.array(paleta[rng.integers(len(paleta))], float)
        luz = 0.58 + 0.55 * k / len(hojas) + rng.uniform(-0.08, 0.08)
        col = tuple(int(min(255, x * luz)) for x in base)
        pintar_hoja(d, cx, cy, ang, largo, largo * rng.uniform(0.42, 0.55), col, rng, venas=largo > 165)
    im = im.resize((1024, 1024), Image.LANCZOS)
    arr = np.asarray(im) / 255.0
    rgb, alfa = _alfa_suave(arr)
    rgb = rgb * (0.92 + 0.16 * ruido(1024, 2.0, semilla + 300))[..., None]
    guardar(nombre, rgb, alfa)


def hoja_ancha():
    S = 1024
    rng = np.random.default_rng(40)
    im = Image.new("RGBA", (S, S * 2), (60, 110, 45, 0))
    d = ImageDraw.Draw(im)
    d.line([(S / 2, S * 2 - 4), (S / 2, S * 2 - 160)], fill=(88, 128, 60, 255), width=28)
    pintar_hoja(d, S / 2, S * 2 - 140, -math.pi / 2, S * 2 - 180, S * 0.92, (70, 128, 50), rng, venas=True, dentado=0.04)
    im = im.resize((512, 1024), Image.LANCZOS)
    arr = np.asarray(im) / 255.0
    rgb, alfa = _alfa_suave(arr)
    t = (1 - np.arange(1024) / 1023)[:, None]
    rgb = rgb * (0.8 + 0.3 * t)[..., None] * (0.9 + 0.2 * ruido(1024, 2.0, 41)[:, :512])[..., None]
    # pequeñas manchas y mordiscos de bichos
    mancha = np.clip((ruido(1024, 0.8, 106)[:, :512] - 0.88) * 8, 0, 1)
    rgb = rgb * (1 - 0.35 * mancha[..., None]) + 0.35 * mancha[..., None] * np.array([0.55, 0.5, 0.2])
    guardar("hoja_ancha", rgb, alfa)


def hojas_caidas():
    S = 2048
    rng = np.random.default_rng(42)
    cols = [(226, 128, 44), (238, 182, 62), (196, 70, 44), (150, 94, 48)]
    im = Image.new("RGBA", (S, S), (200, 120, 50, 0))
    d = ImageDraw.Draw(im)
    for k, col in enumerate(cols):
        ox, oy = (k % 2) * S / 2, (k // 2) * S / 2
        d.line([(ox + S / 4, oy + S / 2 - 24), (ox + S / 4, oy + S / 2 - 180)], fill=(110, 70, 40, 255), width=18)
        pintar_hoja(d, ox + S / 4, oy + S / 2 - 160, -math.pi / 2, S / 2 - 200, S * 0.33, col, rng, venas=True, dentado=0.1)
    im = im.resize((1024, 1024), Image.LANCZOS)
    arr = np.asarray(im) / 255.0
    rgb, alfa = _alfa_suave(arr)
    rgb = rgb * (0.85 + 0.25 * ruido(1024, 2.0, 43))[..., None]
    mancha = np.clip((ruido(1024, 1.0, 107) - 0.8) * 4, 0, 1)
    rgb = rgb * (1 - 0.4 * mancha[..., None]) + 0.4 * mancha[..., None] * np.array([0.35, 0.2, 0.1])
    guardar("hojas_caidas", rgb, alfa)


def hojarasca():
    S = 2048
    rng = np.random.default_rng(44)
    cols = [(214, 120, 44), (232, 172, 60), (186, 70, 44), (146, 92, 48), (120, 74, 40), (200, 150, 70)]
    im = Image.new("RGBA", (S, S), (60, 40, 24, 255))
    alt = Image.new("RGBA", (S, S), (0, 0, 0, 255))
    d, da = ImageDraw.Draw(im), ImageDraw.Draw(alt)
    Nh = 1100
    for i in range(Nh):
        cx, cy = rng.uniform(0, S, 2)
        ang = rng.uniform(0, 2 * math.pi)
        largo = rng.uniform(130, 230)
        luz = 0.55 + 0.55 * i / Nh + rng.uniform(-0.1, 0.1)
        col = tuple(int(min(255, x * luz)) for x in cols[rng.integers(len(cols))])
        g = int(255 * i / Nh)
        for ox in (-S, 0, S):
            for oy in (-S, 0, S):
                if -260 < cx + ox < S + 260 and -260 < cy + oy < S + 260:
                    pintar_hoja(d, cx + ox, cy + oy, ang, largo, largo * 0.55, col, rng, venas=True)
                    da.polygon(poligono_hoja(cx + ox, cy + oy, ang, largo, largo * 0.55), fill=(g, g, g, 255))
    rgb = np.asarray(im.resize((1024, 1024), Image.LANCZOS))[..., :3] / 255.0
    h = np.asarray(alt.resize((1024, 1024), Image.LANCZOS))[..., 0] / 255.0
    guardar("hojarasca", rgb)
    guardar_normal("hojarasca_n", h, 6.0)


def parches():
    """Parches con borde difuso (alfa): calva de tierra y césped recién sembrado."""
    n = 512
    y, x = np.mgrid[0:n, 0:n] / n - 0.5
    r = np.sqrt(x ** 2 + y ** 2) * 2 + 0.3 * (ruido(n, 2.2, 60) - 0.5) + 0.08 * (ruido(n, 1.0, 108) - 0.5)
    alfa = np.clip((0.88 - r) / 0.3, 0, 1)
    val = 0.6 * ruido(n, 2.4, 61) + 0.4 * ruido(n, 1.0, 62)
    col = mezcla((0.25, 0.165, 0.105), (0.52, 0.39, 0.27), val)
    grumo = np.clip((ruido(n, 0.5, 109) - 0.75) * 4, 0, 1)
    col = col * (1 - 0.25 * grumo[..., None]) + 0.25 * grumo[..., None] * np.array([0.6, 0.5, 0.4])
    col *= (0.8 + 0.2 * np.clip(r / 0.9, 0, 1))[..., None]  # el centro, recién removido, más oscuro
    guardar("calva", col, alfa)
    val = 0.5 * ruido(n, 2.4, 63) + 0.5 * ruido(n, 1.0, 64)
    im = Image.new("L", (n, n), 128)
    dr = ImageDraw.Draw(im)
    rng = np.random.default_rng(65)
    for _ in range(9000):
        cx, cy = rng.uniform(0, n, 2)
        ang = rng.normal(-math.pi / 2, 0.6)
        L = rng.uniform(4, 10)
        dr.line([(cx, cy), (cx + math.cos(ang) * L, cy + math.sin(ang) * L)], fill=int(rng.uniform(40, 240)), width=1)
    hebra = np.asarray(im) / 255.0
    col = mezcla((0.27, 0.45, 0.13), (0.52, 0.7, 0.27), val) * (0.8 + 0.4 * hebra)[..., None]
    guardar("cesped_parche", col, alfa)


def _recortar(im, fondo, nombre, ruido_sem=None, tam=None):
    """Guarda una imagen RGBA dibujada a doble tamaño, con alfa suave y color de relleno sin halos."""
    w, h = im.size
    im = im.resize(tam or (w // 2, h // 2), Image.LANCZOS)
    arr = np.asarray(im) / 255.0
    rgb, alfa = _alfa_suave(arr)
    if ruido_sem is not None:
        n = max(rgb.shape[:2])
        rgb = rgb * (0.88 + 0.24 * ruido(n, 2.0, ruido_sem)[:rgb.shape[0], :rgb.shape[1]])[..., None]
    guardar(nombre, rgb, alfa)


def hoja_dentada(nombre, color, n_dientes, fondo_diente, punta, semilla, espinas=False):
    """Hoja alargada con dientes (diente de león, cardo). Base abajo, punta arriba."""
    W, H = 1024, 2048
    rng = np.random.default_rng(semilla)
    im = Image.new("RGBA", (W, H), color + (0,))
    d = ImageDraw.Draw(im)
    izq, der = [], []
    y0, y1 = H - 60, 80
    for i in range(n_dientes * 2 + 1):
        t = i / (n_dientes * 2)
        y = y0 + (y1 - y0) * t
        env = math.sin(math.pi * (0.06 + 0.94 * t) ** 1.25) ** 0.7
        w = W * 0.46 * env * (1.0 if i % 2 else fondo_diente) * rng.uniform(0.85, 1.0)
        dy = -punta * (H / n_dientes) * (1 if i % 2 else 0)
        izq.append((W / 2 - w, y - dy))
        der.append((W / 2 + w, y - dy))
    oscuro = tuple(int(c * 0.62) for c in color) + (255,)
    d.polygon(izq + der[::-1], fill=color + (255,), outline=oscuro)
    d.line(izq + der[::-1] + [izq[0]], fill=oscuro, width=6)
    claro = tuple(min(255, int(c * 1.3 + 20)) for c in color)
    d.polygon(izq + [(W / 2, y1), (W / 2, y0)], fill=tuple(int(c * 0.86) for c in color) + (255,))
    d.line([(W / 2, H), (W / 2, y1)], fill=claro + (255,), width=32)
    for i in range(1, n_dientes * 2, 2):
        d.line([(W / 2, izq[i][1] + 60), izq[i]], fill=claro + (255,), width=10)
        d.line([(W / 2, der[i][1] + 60), der[i]], fill=claro + (255,), width=10)
        if espinas:
            for p_, sx in ((izq[i], -1), (der[i], 1)):
                d.line([p_, (p_[0] + sx * 68, p_[1] - 52)], fill=(235, 230, 190, 255), width=12)
    _recortar(im, color, nombre, semilla + 1)


def fronda():
    W, H = 1024, 2048
    col = (62, 122, 48)
    im = Image.new("RGBA", (W, H), col + (0,))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(70)
    d.line([(W / 2, H), (W / 2, 40)], fill=(96, 120, 60, 255), width=24)
    n = 26
    for i in range(n):
        t = i / (n - 1)
        y = H - 120 - (H - 220) * t
        largo = W * 0.47 * math.sin(math.pi * (0.1 + 0.9 * t) ** 0.7) ** 0.8
        for lado in (-1, 1):
            ang = -math.pi / 2 + lado * (math.pi / 2 - 0.35)
            c = tuple(int(x * rng.uniform(0.85, 1.15)) for x in col)
            pintar_hoja(d, W / 2, y, ang, largo, 88, c, rng)
    _recortar(im, col, "fronda", 71)


def trebol():
    S = 1024
    col = (70, 140, 58)
    im = Image.new("RGBA", (S, S), col + (0,))
    d = ImageDraw.Draw(im)
    for k in range(3):
        a = -math.pi / 2 + k * 2 * math.pi / 3
        cx, cy = S / 2 + math.cos(a) * 236, S / 2 + math.sin(a) * 236
        d.ellipse([cx - 236, cy - 236, cx + 236, cy + 236], fill=col + (255,), outline=(44, 96, 36, 255), width=6)
        # marca clara en forma de V
        for s_ in (-1, 1):
            b = a + s_ * 0.55
            d.line([(S / 2 + math.cos(a) * 120, S / 2 + math.sin(a) * 120), (cx + math.cos(b) * 140, cy + math.sin(b) * 140)],
                   fill=(150, 200, 130, 255), width=24)
        d.line([(S / 2, S / 2), (cx + math.cos(a) * 200, cy + math.sin(a) * 200)], fill=(52, 112, 44, 255), width=10)
    _recortar(im, col, "trebol", 72)


def flores_blancas():
    """Umbela vista desde arriba: radios verdes acabados en ramilletes de florecillas blancas."""
    S = 2048
    rng = np.random.default_rng(73)
    im = Image.new("RGBA", (S, S), (236, 236, 222, 0))
    d = ImageDraw.Draw(im)
    puntos = []
    for i in range(60):
        r = S * 0.44 * math.sqrt((i + 0.5) / 60)
        a = i * math.radians(137.5)
        puntos.append((S / 2 + math.cos(a) * r, S / 2 + math.sin(a) * r))
    for x, y in puntos:
        d.line([(S / 2, S / 2), (x, y)], fill=(110, 150, 70, 255), width=10)
    for x, y in puntos:
        for k in range(9):
            fx, fy = x + rng.normal(0, 44), y + rng.normal(0, 44)
            rr = rng.uniform(22, 32)
            tono = int(rng.uniform(225, 255))
            for p_ in range(5):
                a = p_ * 2 * math.pi / 5 + k
                d.ellipse([fx + math.cos(a) * rr * 0.7 - rr * 0.6, fy + math.sin(a) * rr * 0.7 - rr * 0.6,
                           fx + math.cos(a) * rr * 0.7 + rr * 0.6, fy + math.sin(a) * rr * 0.7 + rr * 0.6],
                          fill=(tono, tono, tono - 12, 255), outline=(200, 200, 186, 255))
            d.ellipse([fx - 8, fy - 8, fx + 8, fy + 8], fill=(225, 205, 90, 255))
    _recortar(im, (236, 236, 222), "flores_blancas")


def main():
    os.makedirs(SALIDA, exist_ok=True)
    for f in (liso, estuco, madera, tejas, piedra_muro, roca, corteza, cesped, tierra, asfalto,
              arrugas, anillos, girasol_centro, brizna, petalo, hoja_ancha, hojas_caidas, hojarasca, parches,
              fronda, trebol, flores_blancas):
        print("  ", f.__name__, flush=True)
        f()
    hoja_dentada("hoja_diente", (74, 138, 52), 7, 0.42, 0.35, 80)
    hoja_dentada("hoja_cardo", (88, 128, 92), 6, 0.35, 0.1, 82, espinas=True)
    racimo_hojas("hojas_verde", [(74, 128, 44), (96, 150, 52), (58, 108, 40), (118, 160, 60)], 50)
    racimo_hojas("hojas_otono", [(226, 124, 40), (240, 178, 56), (200, 76, 40), (214, 150, 48)], 51)
    with open(os.path.join(SALIDA, "medias.json"), "w") as f:
        json.dump(MEDIAS, f, indent=1)
    print(f"{len(os.listdir(SALIDA)) - 1} texturas en {SALIDA}")


if __name__ == "__main__":
    main()
