#!/usr/bin/env python3
"""
Genera escenas/principal.tscn: la escena principal del juego (casa, parcela vallada,
jardín salvaje, calle con contenedor y camión, y un jugador en primera persona).

    python3 herramientas_dev/generar_escena.py [--json ruta.json]

La colocación es procedural (semilla fija): cambia SEMILLA o las cantidades y regenera.
"""
import json
import math
import os
import sys

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEMILLA = 7
X0, X1, Z0, Z1 = -15.0, 15.0, -11.0, 23.0   # límites de la parcela (ver PARCELA en generar_modelos.py)
PUERTA_X = 1.6
ZONA_LIMPIA = (1.6, 8.5, 3.4)                # (x, z, radio): lo que el jugador "ya ha despejado"

rng = np.random.default_rng(SEMILLA)
items = []       # (modelo, grupo, x, y, z, rx, ry, escala_xyz)
ocupado = []     # (x, z, radio)


def poner(modelo, grupo, x, z, ry=None, s=1.0, y=0.0, rx=0.0):
    ry = rng.uniform(0, 360) if ry is None else ry
    s3 = (s, s, s) if np.ndim(s) == 0 else tuple(s)
    items.append((modelo, grupo, float(x), float(y), float(z), float(rx), float(ry), s3))


def libre(x, z, r, margen_valla=0.6):
    if not (X0 + margen_valla < x < X1 - margen_valla and Z0 + margen_valla < z < Z1 - margen_valla):
        return False
    if -5.0 - r < x < 5.9 + r and -3.8 - r < z < 5.6 + r:       # casa y porche
        return False
    if abs(x - PUERTA_X) < 1.1 + r and z > 5.0:                 # sendero
        return False
    if math.hypot(x - ZONA_LIMPIA[0], z - ZONA_LIMPIA[1]) < ZONA_LIMPIA[2] + r:
        return False
    return all(math.hypot(x - ox, z - oz) > r + orad for ox, oz, orad in ocupado)


def esparcir(modelo, grupo, n, radio, escala=(0.85, 1.25), zona=None, intentos=60):
    hechos = 0
    for _ in range(n * intentos):
        if hechos >= n:
            break
        if zona:
            x, z = zona()
        else:
            x, z = rng.uniform(X0, X1), rng.uniform(Z0, Z1)
        if libre(x, z, radio):
            poner(modelo, grupo, x, z, s=rng.uniform(*escala))
            ocupado.append((x, z, radio))
            hechos += 1
    return hechos


def junto_a_valla():
    lado = rng.integers(4)
    t = rng.uniform()
    d = rng.uniform(0.9, 2.2)
    return [(X0 + d, Z0 + t * (Z1 - Z0)), (X1 - d, Z0 + t * (Z1 - Z0)),
            (X0 + t * (X1 - X0), Z0 + d), (X0 + t * (X1 - X0), Z1 - d)][lado]


def cerca_de(cx, cz, r0, r1):
    def f():
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(r0, r1)
        return cx + math.cos(a) * r, cz + math.sin(a) * r
    return f


def tramo_valla(xa, za, xb, zb):
    largo = math.hypot(xb - xa, zb - za)
    n = max(1, round(largo / 2.0))
    ry = math.degrees(math.atan2(-(zb - za), xb - xa))
    for i in range(n):
        f = (i + 0.5) / n
        poner("valla", "Vallas", xa + (xb - xa) * f, za + (zb - za) * f, ry=ry, s=(largo / (2.0 * n), 1, 1))


def componer():
    poner("parcela", "Entorno", 0, 0, ry=0)
    poner("casa", "Entorno", 0, 0, ry=0)
    # valla perimetral con la puerta al frente
    tramo_valla(X0, Z1, PUERTA_X - 1.2, Z1)
    tramo_valla(PUERTA_X + 1.2, Z1, X1, Z1)
    tramo_valla(X1, Z1, X1, Z0)
    tramo_valla(X1, Z0, X0, Z0)
    tramo_valla(X0, Z0, X0, Z1)
    poner("puerta_jardin", "Entorno", PUERTA_X, Z1, ry=0)
    for z in (7.2, 10.4, 13.6, 16.8, 20.0):
        poner("camino_piedra", "Entorno", PUERTA_X + rng.uniform(-0.15, 0.15), z, ry=rng.uniform(-8, 8), y=0.045)
    # árboles
    arboles = [("arbol_gigante", -9.5, 12.5, 1.15), ("arbol_gigante", 9.5, -6.0, 1.0), ("arbol_gigante", -10.5, -5.5, 0.9),
               ("arbol_otono", 9.0, 14.0, 1.15), ("arbol_otono", -6.0, 19.0, 0.85)]
    for nombre, x, z, s in arboles:
        poner(nombre, "Arboles", x, z, s=s)
        ocupado.append((x, z, 0.9))
        if nombre == "arbol_otono":
            poner("alfombra_hojas", "Hojas", x, z, s=1.2 * s)
            esparcir("monton_hojas", "Hojas", 2, 1.3, (0.7, 1.0), cerca_de(x, z, 1.8, 3.8))
    esparcir("tocon", "Vegetacion", 3, 1.6, (0.8, 1.1))
    esparcir("roca", "Vegetacion", 7, 1.3, (0.5, 1.1))
    for nombre, x, z, s in arboles[:3]:
        esparcir("seta_gigante", "Vegetacion", 2, 1.2, (0.5, 0.9), cerca_de(x, z, 1.5, 3.2))
    esparcir("zarza", "Vegetacion", 20, 1.1, (0.8, 1.3), junto_a_valla)
    esparcir("matorral", "Vegetacion", 26, 1.0, (0.7, 1.3))
    esparcir("girasol_gigante", "Vegetacion", 14, 0.45, (0.75, 1.15))
    esparcir("amapola_gigante", "Vegetacion", 12, 0.4, (0.7, 1.1))
    esparcir("hierbajo_grande", "Hierba", 70, 0.5, (0.7, 1.2))
    esparcir("hierbajo", "Hierba", 330, 0.3, (0.8, 1.6))
    # zona despejada: bolsas y herramientas
    cx, cz, _ = ZONA_LIMPIA
    poner("bolsa_basura", "Jugabilidad", cx + 2.0, cz - 1.6, s=1.0)
    poner("bolsa_basura", "Jugabilidad", cx + 2.6, cz - 1.2, s=0.9)
    poner("bolsa_basura", "Jugabilidad", cx - 2.2, cz + 0.6, s=1.0)
    poner("monton_hojas", "Hojas", cx - 1.8, cz - 1.6, s=0.55)
    poner("rastrillo", "Jugabilidad", cx - 1.2, cz - 0.6, ry=35, rx=90, y=0.06)
    poner("guantes", "Jugabilidad", 2.4, 4.9, ry=20, rx=-90, y=0.47)
    poner("hoz", "Jugabilidad", cx + 1.3, cz + 0.9, ry=120, rx=90, y=0.04)
    poner("cartel_tienda", "Jugabilidad", 5.3, 7.0, ry=-25)
    poner("cubo_basura", "Jugabilidad", PUERTA_X + 2.3, Z1 - 1.0, ry=185)
    poner("bolsa_basura", "Jugabilidad", PUERTA_X + 3.2, Z1 - 0.9, s=0.95)
    # calle
    poner("contenedor", "Jugabilidad", PUERTA_X + 4.6, Z1 + 1.1, ry=180, y=0.14)
    poner("bolsa_basura", "Jugabilidad", PUERTA_X + 6.2, Z1 + 1.0, s=1.0, y=0.14)
    poner("camion_basura", "Jugabilidad", -8.0, Z1 + 4.9, ry=90, y=0.02)
    # bichos
    for nombre, n, esc in (("escarabajo", 6, (0.8, 1.3)), ("caracol", 5, (0.6, 1.0)), ("avispa", 4, (0.7, 1.0))):
        for _ in range(n):
            for _ in range(50):
                x, z = rng.uniform(X0 + 1, X1 - 1), rng.uniform(Z0 + 1, Z1 - 1)
                if not (-5.5 < x < 6.4 and -4.3 < z < 6.1) and all(math.hypot(x - a, z - b) > 0.8 for a, b, r in ocupado if r > 0.8):
                    poner(nombre, "Bichos", x, z, s=rng.uniform(*esc), y=rng.uniform(0.3, 1.2) if nombre == "avispa" else 0.0)
                    break


def transform(x, y, z, rx, ry, s):
    a, b = math.radians(rx), math.radians(ry)
    Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
    Ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
    B = Ry @ Rx @ np.diag(s)
    v = [f"{c:.5g}" for col in range(3) for c in B[:, col]] + [f"{c:.4g}" for c in (x, y, z)]
    return "Transform3D(" + ", ".join(v) + ")"


def caja_col(nombre, tam, pos, ry=0.0):
    rid = f"col_{nombre}"
    sub = f'[sub_resource type="BoxShape3D" id="{rid}"]\nsize = Vector3({tam[0]}, {tam[1]}, {tam[2]})\n'
    nodo = (f'[node name="{nombre}" type="CollisionShape3D" parent="Colisiones"]\n'
            f'transform = {transform(pos[0], pos[1], pos[2], 0, ry, (1, 1, 1))}\nshape = SubResource("{rid}")\n')
    return sub, nodo


def escribir_tscn():
    modelos = sorted({i[0] for i in items})
    ext = [f'[ext_resource type="PackedScene" path="res://assets/modelos/{m}.gltf" id="m_{m}"]' for m in modelos]
    ext.append('[ext_resource type="Script" path="res://scripts/jugador.gd" id="jugador"]')
    cols = [caja_col("Casa", (8.3, 7.0, 6.3), (0, 3.5, 0)),
            caja_col("Porche", (3.4, 0.45, 1.7), (1.8, 0.225, 3.85)),
            caja_col("Escalon", (1.5, 0.22, 0.8), (1.6, 0.11, 5.05)),
            caja_col("VallaFrenteIzq", (PUERTA_X - 1.1 - X0, 2.2, 0.2), ((X0 + PUERTA_X - 1.1) / 2, 1.1, Z1)),
            caja_col("VallaFrenteDer", (X1 - PUERTA_X - 1.1, 2.2, 0.2), ((X1 + PUERTA_X + 1.1) / 2, 1.1, Z1)),
            caja_col("VallaFondo", (X1 - X0, 2.2, 0.2), (0, 1.1, Z0)),
            caja_col("VallaIzq", (0.2, 2.2, Z1 - Z0), (X0, 1.1, (Z0 + Z1) / 2)),
            caja_col("VallaDer", (0.2, 2.2, Z1 - Z0), (X1, 1.1, (Z0 + Z1) / 2)),
            caja_col("Contenedor", (2.1, 1.4, 1.4), (PUERTA_X + 4.6, 0.8, Z1 + 1.1)),
            caja_col("Camion", (2.6, 3.4, 7.6), (-8.0, 1.7, Z1 + 4.9), 90)]
    for k, (m, g, x, y, z, rx, ry, s) in enumerate(i for i in items if i[0].startswith("arbol")):
        cols.append(caja_col(f"Tronco{k + 1}", (1.0 * s[0], 5.0, 1.0 * s[0]), (x, 2.5, z), ry))
    cab = f"""[gd_scene format=3]

{chr(10).join(ext)}

[sub_resource type="ProceduralSkyMaterial" id="cielo_mat"]
sky_top_color = Color(0.3, 0.52, 0.82, 1)
sky_horizon_color = Color(0.86, 0.8, 0.68, 1)
ground_bottom_color = Color(0.3, 0.26, 0.2, 1)
ground_horizon_color = Color(0.86, 0.8, 0.68, 1)
sun_angle_max = 25.0

[sub_resource type="Sky" id="cielo"]
sky_material = SubResource("cielo_mat")

[sub_resource type="Environment" id="entorno"]
background_mode = 2
sky = SubResource("cielo")
ambient_light_source = 3
ambient_light_energy = 1.0
reflected_light_source = 2
tonemap_mode = 2
tonemap_white = 6.0
ssao_enabled = true
ssao_radius = 1.5
ssao_intensity = 2.5
ssil_enabled = true
glow_enabled = true
glow_intensity = 0.35
glow_bloom = 0.05
fog_enabled = true
fog_light_color = Color(0.86, 0.8, 0.7, 1)
fog_density = 0.004
fog_sky_affect = 0.2
adjustment_enabled = true
adjustment_saturation = 1.08

[sub_resource type="WorldBoundaryShape3D" id="col_suelo"]

[sub_resource type="CapsuleShape3D" id="capsula"]
radius = 0.32
height = 1.7

{chr(10).join(c[0] for c in cols)}
[node name="Principal" type="Node3D"]

[node name="WorldEnvironment" type="WorldEnvironment" parent="."]
environment = SubResource("entorno")

[node name="Sol" type="DirectionalLight3D" parent="."]
transform = {transform(0, 30, 0, -42, -35, (1, 1, 1))}
light_color = Color(1, 0.93, 0.8, 1)
light_energy = 1.5
shadow_enabled = true
shadow_blur = 1.5
directional_shadow_max_distance = 70.0

[node name="Colisiones" type="StaticBody3D" parent="."]

[node name="Suelo" type="CollisionShape3D" parent="Colisiones"]
shape = SubResource("col_suelo")

{chr(10).join(c[1] for c in cols)}
[node name="Jugador" type="CharacterBody3D" parent="."]
transform = {transform(PUERTA_X, 0.05, 19.0, 0, 0, (1, 1, 1))}
script = ExtResource("jugador")

[node name="Colision" type="CollisionShape3D" parent="Jugador"]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0.85, 0)
shape = SubResource("capsula")

[node name="Camara" type="Camera3D" parent="Jugador"]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 1.6, 0)
fov = 70.0
far = 300.0

"""
    grupos, nodos, cuenta = [], [], {}
    for m, g, x, y, z, rx, ry, s in items:
        if g not in grupos:
            grupos.append(g)
            nodos.append(f'[node name="{g}" type="Node3D" parent="."]\n')
        cuenta[m] = cuenta.get(m, 0) + 1
        nodos.append(f'[node name="{m}_{cuenta[m]}" parent="{g}" instance=ExtResource("m_{m}")]\n'
                     f"transform = {transform(x, y, z, rx, ry, s)}\n")
    with open(os.path.join(RAIZ, "escenas", "principal.tscn"), "w") as f:
        f.write(cab + "\n".join(nodos))
    print(f"principal.tscn: {len(items)} objetos, {len(modelos)} modelos distintos")


if __name__ == "__main__":
    componer()
    escribir_tscn()
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as f:
            json.dump([dict(m=i[0], p=i[2:5], rx=i[5], ry=i[6], s=i[7]) for i in items], f)
