#!/usr/bin/env python3
"""
Sonidos del juego, sintetizados por código (sin archivos de fuera).

    pip install numpy
    python3 herramientas_dev/generar_sonidos.py

Salida: assets/sonidos/*.wav (mono, 16 bits, 44,1 kHz).
  camion_motor   motor diésel en bucle (el juego lo repite mientras el camión se mueve)
  claxon         dos bocinazos al llegar
  marcha_atras   pitido de marcha atrás (se repite mientras el basurero trabaja)
  compactador    hidráulico + crujido al vaciar el contenedor
  caja           "¡ka-ching!" al cobrar
  arrancar       arrancar una planta con las manos
  corte          tijeretazo / golpe de hoja
  motor_herramienta  zumbido corto (desbrozadora, cortacésped, motosierra)
  bolsa          meter algo en la bolsa
  tirar          la bolsa cae en el cubo
  soltar         dejar la bolsa en el suelo
  compra         mejora comprada
  error          no hay dinero / no se puede
  paso           pisada sobre hierba
"""
import os
import wave

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(RAIZ, "assets", "sonidos")
SR = 44100
rng = np.random.default_rng(7)


def t_(seg):
    return np.arange(int(SR * seg)) / SR


def ruido(n):
    return rng.uniform(-1, 1, n)


def paso_bajo(x, corte):
    """Filtro de un polo (suficiente para darle cuerpo al ruido)."""
    a = np.exp(-2 * np.pi * corte / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def paso_alto(x, corte):
    return x - paso_bajo(x, corte)


def env(n, ataque=0.01, caida=0.1):
    e = np.ones(n)
    na, nc = int(SR * ataque), int(SR * caida)
    if na:
        e[:na] = np.linspace(0, 1, na)
    if nc:
        e[-nc:] *= np.linspace(1, 0, nc)
    return e


def guardar(nombre, x, vol=0.8):
    x = np.asarray(x, float)
    x = x / max(1e-6, np.abs(x).max()) * vol
    datos = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(os.path.join(SALIDA, nombre + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(datos.tobytes())


def camion_motor():
    # 1 segundo exacto con frecuencias enteras: el bucle no tiene salto
    t = t_(1.0)
    base = 36.0
    pulsos = sum(np.sin(2 * np.pi * base * k * t + k) / k for k in range(1, 9))
    tableteo = (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * base * 0.5 * t))) * 0.4
    rugido = paso_bajo(ruido(len(t)), 300) * 3.0
    x = pulsos * (0.7 + tableteo) + rugido * (0.6 + 0.4 * np.sin(2 * np.pi * 6 * t))
    guardar("camion_motor", paso_bajo(x, 900), 0.7)


def claxon():
    def toque(seg):
        t = t_(seg)
        x = sum(np.sign(np.sin(2 * np.pi * f * t)) * a for f, a in ((349, 1.0), (440, 0.8), (698, 0.25)))
        return paso_bajo(x, 2500) * env(len(t), 0.015, 0.05)
    guardar("claxon", np.concatenate([toque(0.22), np.zeros(int(SR * 0.09)), toque(0.5)]), 0.75)


def marcha_atras():
    t = t_(0.9)
    on = (t < 0.4).astype(float)
    x = np.sin(2 * np.pi * 1050 * t) * on * env(len(t), 0.005, 0.5)
    guardar("marcha_atras", x, 0.5)


def compactador():
    t = t_(2.2)
    gemido = np.sin(2 * np.pi * (180 + 120 * np.minimum(t, 1.2)) * t) * 0.5
    hidraulico = paso_bajo(ruido(len(t)), 600) * 2.0
    crujido = paso_alto(ruido(len(t)), 1500) * (rng.random(len(t)) < 0.02) * 3.0
    crujido = paso_bajo(crujido, 4000) * np.clip((t - 0.9) * 3, 0, 1)
    golpe = np.exp(-np.maximum(t - 1.8, 0) * 18) * (t > 1.8) * np.sin(2 * np.pi * 60 * t) * 1.5
    guardar("compactador", (gemido + hidraulico + crujido + golpe) * env(len(t), 0.1, 0.25), 0.7)


def caja():
    t = t_(1.1)
    clic = paso_alto(ruido(len(t)), 2000) * np.exp(-t * 80) * 1.2
    cajon = paso_bajo(ruido(len(t)), 500) * np.exp(-np.maximum(t - 0.08, 0) * 25) * (t > 0.08)
    campana = sum(np.sin(2 * np.pi * f * t) * a * np.exp(-np.maximum(t - 0.12, 0) * d) * (t > 0.12)
                  for f, a, d in ((1568, 1.0, 4.5), (2093, 0.7, 5.5), (3136, 0.4, 7), (4186, 0.25, 9)))
    guardar("caja", clic + cajon * 0.8 + campana, 0.8)


def arrancar():
    t = t_(0.32)
    x = paso_bajo(paso_alto(ruido(len(t)), 300), 3500)
    rasgado = 0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 38 * t + 3 * np.sin(2 * np.pi * 7 * t)))
    tierra = paso_bajo(ruido(len(t)), 250) * np.exp(-t * 12) * 2
    guardar("arrancar", (x * rasgado + tierra) * env(len(t), 0.01, 0.12), 0.7)


def corte():
    t = t_(0.18)
    def clic(t0, f):
        tt = np.maximum(t - t0, 0)
        return (paso_alto(ruido(len(t)), 3000) * 0.6 + np.sin(2 * np.pi * f * tt) * 0.5) * np.exp(-tt * 60) * (t > t0)
    guardar("corte", clic(0.0, 2800) + clic(0.06, 2300), 0.7)


def motor_herramienta():
    t = t_(0.4)
    f = 115 + 25 * np.sin(2 * np.pi * 3 * t)
    fase = 2 * np.pi * np.cumsum(f) / SR
    sierra = 2 * ((fase / (2 * np.pi)) % 1) - 1
    x = paso_bajo(sierra + 0.4 * ruido(len(t)), 2200)
    guardar("motor_herramienta", x * env(len(t), 0.02, 0.1), 0.55)


def bolsa():
    t = t_(0.35)
    x = paso_alto(ruido(len(t)), 1800) * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 23 * t)))
    guardar("bolsa", paso_bajo(x, 6000) * env(len(t), 0.02, 0.15), 0.5)


def tirar():
    t = t_(0.5)
    golpe = np.sin(2 * np.pi * (90 - 40 * t) * t) * np.exp(-t * 9)
    hueco = paso_bajo(ruido(len(t)), 400) * np.exp(-t * 14) * 1.5
    plastico = paso_alto(ruido(len(t)), 2500) * np.exp(-t * 20) * 0.5
    guardar("tirar", golpe + hueco + plastico, 0.85)


def soltar():
    t = t_(0.3)
    x = np.sin(2 * np.pi * 70 * t) * np.exp(-t * 16) + paso_bajo(ruido(len(t)), 900) * np.exp(-t * 18)
    guardar("soltar", x, 0.7)


def compra():
    notas = [523, 659, 784, 1047]
    trozos = []
    for i, f in enumerate(notas):
        t = t_(0.09 if i < 3 else 0.35)
        trozos.append((np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * (14 if i < 3 else 6)))
    guardar("compra", np.concatenate(trozos), 0.6)


def error():
    t = t_(0.25)
    x = np.sign(np.sin(2 * np.pi * 140 * t)) * 0.6 + np.sin(2 * np.pi * 147 * t) * 0.4
    guardar("error", paso_bajo(x, 1500) * env(len(t), 0.01, 0.08), 0.45)


def paso():
    t = t_(0.14)
    x = paso_bajo(ruido(len(t)), 1200) * np.exp(-t * 35) + paso_alto(ruido(len(t)), 3000) * np.exp(-t * 50) * 0.3
    guardar("paso", x, 0.35)


def main():
    os.makedirs(SALIDA, exist_ok=True)
    for f in (camion_motor, claxon, marcha_atras, compactador, caja, arrancar, corte, motor_herramienta,
              bolsa, tirar, soltar, compra, error, paso):
        f()
    print(f"{len(os.listdir(SALIDA))} sonidos en {SALIDA}")


if __name__ == "__main__":
    main()
