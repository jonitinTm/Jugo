#!/usr/bin/env python3
"""
Genera las texturas procedurales (repetibles) que usan los modelos.

    pip install numpy pillow
    python3 herramientas_dev/generar_texturas.py

Salida: assets/modelos/texturas/*.jpg|png  +  medias.json (color medio de cada
textura, que el generador de modelos usa para teñirlas con la paleta).
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "assets", "modelos", "texturas")
MEDIAS = {}


# ------------------------------------------------------------------ utilidades
def ruido(n, beta=2.0, semilla=0, ax=1.0, ay=1.0):
    """Ruido fractal repetible en [0,1]. ay>1 alarga los rasgos en vertical."""
    rng = np.random.default_rng(semilla)
    F = np.fft.fft2(rng.normal(size=(n, n)))
    fx = np.fft.fftfreq(n)[None, :] * ax
    fy = np.fft.fftfreq(n)[:, None] * ay
    f = np.sqrt(fx ** 2 + fy ** 2)
    f[0, 0] = 1
    F = F / f ** (beta / 2)
    F[0, 0] = 0
    r = np.real(np.fft.ifft2(F))
    lo, hi = np.percentile(r, [1, 99])
    return np.clip((r - lo) / (hi - lo), 0, 1)


def mezcla(a, b, t):
    t = np.asarray(t)[..., None]
    return np.asarray(a, float) * (1 - t) + np.asarray(b, float) * t


def normal_de_altura(h, fuerza):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    n = np.dstack([-dx * fuerza, dy * fuerza, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def guardar(nombre, rgb, alfa=None, calidad=90):
    arr = (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)
    if alfa is None:
        Image.fromarray(arr, "RGB").save(os.path.join(SALIDA, nombre + ".jpg"), quality=calidad)
        lin = np.where(rgb <= 0.04045, rgb / 12.92, ((np.clip(rgb, 0, 1) + 0.055) / 1.055) ** 2.4)
        MEDIAS[nombre] = [float(x) for x in lin.reshape(-1, 3).mean(0)]
    else:
        a = (np.clip(alfa, 0, 1) * 255 + 0.5).astype(np.uint8)
        Image.fromarray(np.dstack([arr, a]), "RGBA").save(os.path.join(SALIDA, nombre + ".png"), optimize=True)


def guardar_normal(nombre, h, fuerza):
    guardar(nombre, normal_de_altura(h, fuerza), calidad=92)
    MEDIAS.pop(nombre, None)


# ------------------------------------------------------------------ superficies
def liso():
    v = 0.9 + 0.1 * ruido(256, 2.5, 1)
    guardar("liso", np.dstack([v, v, v]))


def estuco():
    fino, grande = ruido(512, 1.0, 2), ruido(512, 3.0, 3)
    grumo = ruido(512, 2.0, 4)
    col = np.array([0.93, 0.885, 0.78]) * (0.92 + 0.08 * fino)[..., None] * (0.9 + 0.1 * grande)[..., None]
    # churretes de humedad verticales
    ch = ruido(512, 2.2, 5, ax=1, ay=10)
    col *= (1 - 0.1 * np.clip(ch - 0.6, 0, 1) * 2.5)[..., None]
    guardar("estuco", col)
    guardar_normal("estuco_n", 0.5 * fino + 0.5 * grumo, 2.5)


def madera():
    n = 512
    u = np.arange(n)[None, :] / n
    veta = ruido(n, 2.0, 6, ax=1, ay=16)
    fina = ruido(n, 1.2, 7, ax=1, ay=30)
    onda = ruido(n, 3.0, 8, ax=1, ay=5)
    anillos = 0.5 + 0.5 * np.sin(2 * math.pi * (u * 7 + 1.6 * onda))
    val = np.clip(0.45 * veta + 0.2 * fina + 0.35 * anillos, 0, 1)
    col = mezcla((0.58, 0.47, 0.37), (1.0, 0.94, 0.84), val)
    guardar("madera", col)
    guardar_normal("madera_n", val, 2.0)


def tejas():
    n, alto, ancho = 512, 64, 128
    rng = np.random.default_rng(9)
    y, x = np.mgrid[0:n, 0:n]
    fila = y // alto
    fy = (y % alto) / alto
    xs = (x + (fila % 2) * (ancho // 2)) % n
    colu = xs // ancho
    fx = (xs % ancho) / ancho
    tono = rng.uniform(0.72, 1.12, (n // alto, n // ancho))[fila, colu]
    matiz = rng.uniform(-1, 1, (n // alto, n // ancho))[fila, colu]
    musgo = (rng.random((n // alto, n // ancho)) < 0.12)[fila, colu]
    borde = rng.uniform(0.0, 0.08, (n // alto, n // ancho))[fila, colu]
    base = np.array([0.40, 0.385, 0.47])[None, None, :] * tono[..., None]
    base[..., 0] += 0.03 * matiz
    base[..., 2] -= 0.03 * matiz
    base = np.where(musgo[..., None], base * np.array([0.9, 1.08, 0.8]), base)
    base *= (0.9 + 0.2 * ruido(n, 1.5, 10))[..., None]
    sombra = np.clip(fy / 0.22, 0, 1)  # sombra bajo la hilada de arriba
    base *= (0.6 + 0.4 * sombra)[..., None]
    hueco = (fx < 0.025) | (fx > 0.975)
    base[hueco] *= 0.45
    canto = fy > (0.94 - borde)
    base[canto] *= 1.18
    h = fy.copy()
    h[hueco] -= 0.5
    guardar("tejas", base)
    guardar_normal("tejas_n", h + 0.05 * ruido(n, 1.5, 11), 5.0)


def piedra_muro():
    n, alto = 512, 64
    rng = np.random.default_rng(12)
    col = np.zeros((n, n, 3))
    h = np.zeros((n, n))
    x = np.arange(n)
    gr = ruido(n, 1.6, 13)
    for f in range(n // alto):
        cortes = [0]
        while cortes[-1] < n - 70:
            cortes.append(cortes[-1] + int(rng.uniform(70, 150)))
        cortes = np.array(cortes)
        desfase = int(rng.uniform(0, 100))
        xs = (x + desfase) % n
        idx = np.searchsorted(cortes, xs, side="right") - 1
        izq = cortes[idx]
        der = np.where(idx + 1 < len(cortes), cortes[np.minimum(idx + 1, len(cortes) - 1)], n)
        dx = np.minimum(xs - izq, der - xs)
        tono = rng.uniform(0.74, 1.08, len(cortes))[idx]
        calido = rng.uniform(-1, 1, len(cortes))[idx]
        for yy in range(alto):
            d = np.minimum(dx, min(yy, alto - 1 - yy))
            piedra = np.clip((d - 3) / 7, 0, 1)
            c = np.array([0.70, 0.67, 0.62])[None, :] * tono[:, None]
            c[:, 0] += 0.03 * calido
            c[:, 2] -= 0.03 * calido
            mortero = np.array([0.50, 0.47, 0.42])
            col[f * alto + yy] = mortero * (1 - piedra[:, None]) + c * piedra[:, None]
            h[f * alto + yy] = piedra
    col *= (0.85 + 0.3 * gr)[..., None]
    guardar("piedra_muro", col)
    guardar_normal("piedra_muro_n", h + 0.25 * gr, 4.0)


def roca():
    n = 512
    a, b = ruido(n, 2.6, 14), ruido(n, 1.4, 15)
    grieta = 1 - np.abs(2 * ruido(n, 2.2, 16) - 1)
    val = 0.6 * a + 0.4 * b
    col = mezcla((0.40, 0.39, 0.37), (0.74, 0.72, 0.67), val)
    col *= (1 - 0.55 * np.clip((grieta - 0.93) / 0.07, 0, 1))[..., None]
    liquen = np.clip((ruido(n, 2.5, 17) - 0.72) * 5, 0, 1) * 0.5
    col = col * (1 - liquen[..., None]) + np.array([0.55, 0.6, 0.38]) * liquen[..., None]
    guardar("roca", col)
    guardar_normal("roca_n", val - 0.3 * np.clip((grieta - 0.9) / 0.1, 0, 1), 6.0)


def corteza():
    n = 512
    a = ruido(n, 1.8, 18, ax=1, ay=9)
    fino = ruido(n, 1.2, 19, ax=1, ay=3)
    surco = np.abs(2 * a - 1) ** 0.6
    h = np.clip(0.8 * surco + 0.2 * fino, 0, 1)
    col = mezcla((0.17, 0.115, 0.08), (0.56, 0.43, 0.31), h)
    col *= (0.85 + 0.3 * ruido(n, 2.5, 20))[..., None]
    guardar("corteza", col)
    guardar_normal("corteza_n", h, 6.0)


def cesped():
    n = 512
    a, b = ruido(n, 2.6, 21), ruido(n, 0.9, 22)
    hebra = ruido(n, 1.3, 23, ax=1, ay=5)
    val = 0.45 * a + 0.3 * b + 0.25 * hebra
    col = mezcla((0.17, 0.29, 0.09), (0.47, 0.6, 0.22), val)
    seco = np.clip((ruido(n, 3.0, 24) - 0.62) * 3, 0, 1) * 0.55
    col = col * (1 - seco[..., None]) + np.array([0.6, 0.56, 0.3]) * seco[..., None]
    guardar("cesped", col)
    guardar_normal("cesped_n", 0.5 * b + 0.5 * hebra, 3.0)


def tierra():
    n = 512
    a, b = ruido(n, 2.4, 25), ruido(n, 1.0, 26)
    val = 0.6 * a + 0.4 * b
    col = mezcla((0.27, 0.18, 0.115), (0.52, 0.39, 0.27), val)
    china = np.clip((ruido(n, 0.6, 27) - 0.86) * 12, 0, 1)
    col = col * (1 - china[..., None]) + np.array([0.62, 0.58, 0.52]) * china[..., None]
    guardar("tierra", col)
    guardar_normal("tierra_n", val + 0.4 * china, 4.0)


def asfalto():
    n = 512
    a, b = ruido(n, 0.4, 28), ruido(n, 2.8, 29)
    v = 0.2 + 0.1 * a + 0.06 * b
    guardar("asfalto", np.dstack([v, v, v * 1.03]))
    guardar_normal("asfalto_n", a, 2.0)


def arrugas():
    n = 512
    a = 1 - np.abs(2 * ruido(n, 2.0, 30) - 1)
    b = 1 - np.abs(2 * ruido(n, 2.4, 31, ax=1, ay=3) - 1)
    guardar_normal("arrugas_n", a ** 2 + 0.7 * b ** 2, 5.0)


def anillos():
    n = 256
    y, x = np.mgrid[0:n, 0:n] / n - 0.5
    r = np.sqrt(x ** 2 + y ** 2) * (1 + 0.12 * (ruido(n, 3.0, 32) - 0.5))
    an = 0.5 + 0.5 * np.sin(r * 2 * math.pi * 22)
    val = np.clip(0.6 * an + 0.4 * ruido(n, 1.5, 33), 0, 1)
    col = mezcla((0.55, 0.39, 0.24), (0.87, 0.72, 0.5), val)
    col *= (1 - 0.35 * np.clip((r - 0.36) / 0.1, 0, 1))[..., None]
    ang = np.arctan2(y, x)
    grieta = (np.abs(np.sin(ang * 3.5 + 1.0)) < 0.02) & (r > 0.05) & (r < 0.3)
    col[grieta] *= 0.55
    guardar("anillos", col)


def girasol_centro():
    n = 512
    im = Image.new("RGB", (n, n), (58, 36, 18))
    d = ImageDraw.Draw(im)
    N = 900
    for i in range(N, 0, -1):
        r = 0.49 * n * math.sqrt(i / N)
        a = i * math.radians(137.508)
        cx, cy = n / 2 + r * math.cos(a), n / 2 + r * math.sin(a)
        s = 3.5 + 4.5 * (i / N)
        t = i / N
        col = (int(60 + 70 * (1 - t)), int(38 + 60 * (1 - t)), int(16 + 10 * (1 - t)))
        d.ellipse([cx - s, cy - s, cx + s, cy + s], fill=(30, 18, 10))
        d.ellipse([cx - s * 0.7, cy - s * 0.8, cx + s * 0.6, cy + s * 0.5], fill=col)
    im = im.resize((256, 256), Image.LANCZOS)
    guardar("girasol_centro", np.asarray(im) / 255.0)


def brizna():
    h, w = 256, 64
    t = (1 - np.arange(h) / (h - 1))[:, None] * np.ones((1, w))  # 0 base (abajo) → 1 punta
    col = mezcla((0.2, 0.36, 0.1), (0.58, 0.72, 0.28), t ** 0.8)
    u = np.abs(np.arange(w) / (w - 1) - 0.5)[None, :] * 2
    col *= (1.08 - 0.25 * u ** 1.5)[..., None]
    col *= (0.9 + 0.2 * np.repeat(ruido(64, 1.5, 34)[:1, :], h, 0))[..., None]
    punta = np.clip((t - 0.85) / 0.15, 0, 1) * 0.5
    col = col * (1 - punta[..., None]) + np.array([0.75, 0.7, 0.35]) * punta[..., None]
    guardar("brizna", col)


def petalo():
    h, w = 256, 64
    t = (1 - np.arange(h) / (h - 1))[:, None] * np.ones((1, w))
    v = 0.5 + 0.5 * np.clip(t / 0.4, 0, 1) ** 0.8
    raya = np.repeat(ruido(64, 1.8, 35)[:1, :], h, 0)
    v = v * (0.88 + 0.12 * raya)
    u = np.abs(np.arange(w) / (w - 1) - 0.5)[None, :] * 2
    v = v * (1 - 0.1 * (1 - u))
    guardar("petalo", np.dstack([v, v * (0.85 + 0.15 * np.clip(t / 0.5, 0, 1)), v]))


# ------------------------------------------------------------------ hojas (con alfa)
def poligono_hoja(cx, cy, ang, largo, ancho, n=9, dentado=0.0, rng=None):
    """Hoja ovalada con punta; la base está en (cx,cy) y apunta hacia `ang`."""
    izq, der = [], []
    for i in range(n + 1):
        t = i / n
        w = ancho * 0.5 * math.sin(math.pi * t ** 0.75) ** 0.9
        if dentado and rng is not None and 0 < i < n:
            w *= 1 + rng.uniform(-dentado, dentado)
        izq.append((t * largo, w))
        der.append((t * largo, -w))
    pts = izq + der[::-1]
    c, s = math.cos(ang), math.sin(ang)
    return [(cx + x * c - y * s, cy + x * s + y * c) for x, y in pts]


def pintar_hoja(d, cx, cy, ang, largo, ancho, color, rng, venas=False, dentado=0.0):
    r, g, b = color
    pts = poligono_hoja(cx, cy, ang, largo, ancho, dentado=dentado, rng=rng)
    d.polygon(pts, fill=(r, g, b, 255))
    # media hoja algo más oscura (da volumen)
    mitad = poligono_hoja(cx, cy, ang, largo, ancho)
    n = len(mitad) // 2
    eje = [(cx + math.cos(ang) * largo * i / 9, cy + math.sin(ang) * largo * i / 9) for i in range(10)]
    d.polygon(mitad[:n] + eje[::-1], fill=(int(r * 0.84), int(g * 0.86), int(b * 0.84), 255))
    claro = (min(255, int(r * 1.25 + 14)), min(255, int(g * 1.2 + 14)), min(255, int(b * 1.15 + 8)), 255)
    d.line([eje[0], eje[-1]], fill=claro, width=max(1, int(ancho / 22)))
    if venas:
        for i in range(2, 9):
            p = eje[i]
            for lado in (-1, 1):
                a2 = ang + lado * 0.9
                L = ancho * 0.42 * math.sin(math.pi * (i / 9) ** 0.75)
                d.line([p, (p[0] + math.cos(a2) * L, p[1] + math.sin(a2) * L)], fill=claro, width=max(1, int(ancho / 45)))


def racimo_hojas(nombre, paleta, semilla, n_hojas=300):
    S = 1024
    rng = np.random.default_rng(semilla)
    fondo = tuple(int(x) for x in np.mean(paleta, 0))
    im = Image.new("RGBA", (S, S), fondo + (0,))
    d = ImageDraw.Draw(im)
    # ramitas
    for i in range(7):
        a = rng.uniform(0, 2 * math.pi)
        L = rng.uniform(250, 430)
        d.line([(S / 2, S / 2), (S / 2 + math.cos(a) * L, S / 2 + math.sin(a) * L)], fill=(70, 50, 34, 255), width=7)
    hojas = []
    for i in range(n_hojas):
        r = 0.44 * S * rng.uniform(0, 1) ** 0.62
        a = rng.uniform(0, 2 * math.pi)
        cx, cy = S / 2 + math.cos(a) * r, S / 2 + math.sin(a) * r
        ang = a + rng.normal(0, 1.1)
        largo = rng.uniform(70, 105)
        if max(abs(cx + math.cos(ang) * largo - S / 2), abs(cy + math.sin(ang) * largo - S / 2)) > S / 2 - 6:
            continue
        hojas.append((cx, cy, ang, largo))
    for k, (cx, cy, ang, largo) in enumerate(hojas):
        base = np.array(paleta[rng.integers(len(paleta))], float)
        luz = 0.62 + 0.5 * k / len(hojas) + rng.uniform(-0.08, 0.08)
        col = tuple(int(min(255, x * luz)) for x in base)
        pintar_hoja(d, cx, cy, ang, largo, largo * rng.uniform(0.42, 0.55), col, rng)
    im = im.resize((512, 512), Image.LANCZOS)
    arr = np.asarray(im) / 255.0
    alfa = (arr[..., 3] > 0.5).astype(float)
    rgb = arr[..., :3] * alfa[..., None] + np.array(fondo) / 255.0 * (1 - alfa[..., None])
    guardar(nombre, rgb, alfa)


def hoja_ancha():
    S = 512
    rng = np.random.default_rng(40)
    im = Image.new("RGBA", (S, S * 2), (60, 110, 45, 0))
    d = ImageDraw.Draw(im)
    d.line([(S / 2, S * 2 - 2), (S / 2, S * 2 - 80)], fill=(88, 128, 60, 255), width=14)
    pintar_hoja(d, S / 2, S * 2 - 70, -math.pi / 2, S * 2 - 90, S * 0.92, (70, 128, 50), rng, venas=True, dentado=0.05)
    im = im.resize((256, 512), Image.LANCZOS)
    arr = np.asarray(im) / 255.0
    alfa = (arr[..., 3] > 0.5).astype(float)
    t = (1 - np.arange(512) / 511)[:, None]
    rgb = arr[..., :3] * (0.8 + 0.3 * t)[..., None] * (0.9 + 0.2 * ruido(512, 2.0, 41)[:, :256])[..., None]
    rgb = rgb * alfa[..., None] + np.array([60, 110, 45]) / 255.0 * (1 - alfa[..., None])
    guardar("hoja_ancha", rgb, alfa)


def hojas_caidas():
    S = 1024
    rng = np.random.default_rng(42)
    cols = [(226, 128, 44), (238, 182, 62), (196, 70, 44), (150, 94, 48)]
    im = Image.new("RGBA", (S, S), (200, 120, 50, 0))
    d = ImageDraw.Draw(im)
    for k, col in enumerate(cols):
        ox, oy = (k % 2) * S / 2, (k // 2) * S / 2
        d.line([(ox + S / 4, oy + S / 2 - 12), (ox + S / 4, oy + S / 2 - 90)], fill=(110, 70, 40, 255), width=9)
        pintar_hoja(d, ox + S / 4, oy + S / 2 - 80, -math.pi / 2, S / 2 - 100, S * 0.33, col, rng, venas=True, dentado=0.1)
    im = im.resize((512, 512), Image.LANCZOS)
    arr = np.asarray(im) / 255.0
    alfa = (arr[..., 3] > 0.5).astype(float)
    rgb = arr[..., :3] * (0.85 + 0.25 * ruido(512, 2.0, 43))[..., None]
    rgb = rgb * alfa[..., None] + np.array([200, 120, 50]) / 255.0 * (1 - alfa[..., None])
    guardar("hojas_caidas", rgb, alfa)


def hojarasca():
    S = 1024
    rng = np.random.default_rng(44)
    cols = [(214, 120, 44), (232, 172, 60), (186, 70, 44), (146, 92, 48), (120, 74, 40), (200, 150, 70)]
    im = Image.new("RGBA", (S, S), (70, 46, 28, 255))
    alt = Image.new("RGBA", (S, S), (0, 0, 0, 255))
    d, da = ImageDraw.Draw(im), ImageDraw.Draw(alt)
    N = 900
    for i in range(N):
        cx, cy = rng.uniform(0, S, 2)
        ang = rng.uniform(0, 2 * math.pi)
        largo = rng.uniform(70, 120)
        luz = 0.6 + 0.5 * i / N + rng.uniform(-0.1, 0.1)
        col = tuple(int(min(255, x * luz)) for x in cols[rng.integers(len(cols))])
        g = int(255 * i / N)
        for ox in (-S, 0, S):
            for oy in (-S, 0, S):
                if -130 < cx + ox < S + 130 and -130 < cy + oy < S + 130:
                    pintar_hoja(d, cx + ox, cy + oy, ang, largo, largo * 0.55, col, rng, venas=True)
                    da.polygon(poligono_hoja(cx + ox, cy + oy, ang, largo, largo * 0.55), fill=(g, g, g, 255))
    rgb = np.asarray(im.resize((512, 512), Image.LANCZOS))[..., :3] / 255.0
    h = np.asarray(alt.resize((512, 512), Image.LANCZOS))[..., 0] / 255.0
    guardar("hojarasca", rgb)
    guardar_normal("hojarasca_n", h, 6.0)


def main():
    os.makedirs(SALIDA, exist_ok=True)
    for f in (liso, estuco, madera, tejas, piedra_muro, roca, corteza, cesped, tierra, asfalto,
              arrugas, anillos, girasol_centro, brizna, petalo, hoja_ancha, hojas_caidas, hojarasca):
        f()
    racimo_hojas("hojas_verde", [(74, 128, 44), (96, 150, 52), (58, 108, 40), (118, 160, 60)], 50)
    racimo_hojas("hojas_otono", [(226, 124, 40), (240, 178, 56), (200, 76, 40), (214, 150, 48)], 51)
    with open(os.path.join(SALIDA, "medias.json"), "w") as f:
        json.dump(MEDIAS, f, indent=1)
    print(f"{len(os.listdir(SALIDA)) - 1} texturas en {SALIDA}")


if __name__ == "__main__":
    main()
