#!/usr/bin/env python3
"""
Genera escenas/principal.tscn: la escena principal del juego.

El mapa tiene varias ZONAS (definidas en economia.py) separadas por vallas; cada zona tiene
una puerta que el jugador desbloquea pagando. Aquí se colocan la casa, el terreno, las
vallas y puertas, la vegetación y los bichos de cada zona, las colisiones y el jugador.

    python3 herramientas_dev/generar_escena.py [--json ruta.json]

La colocación es procedural (semilla fija): cambia SEMILLA o el "contenido" de cada zona
en economia.py y regenera.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import economia as eco  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEMILLA = 7
PUERTA_X = 1.6                               # puerta principal (a la calle)
Z_CALLE = 23.0
ZONA_LIMPIA = (1.6, 8.5, 3.4)                # (x, z, radio): lo que el jugador "ya ha despejado"
# límites de todo el mapa (unión de las zonas)
X0 = min(z["rect"][0] for z in eco.ZONAS)
Z0 = min(z["rect"][1] for z in eco.ZONAS)
X1 = max(z["rect"][2] for z in eco.ZONAS)
Z1 = max(z["rect"][3] for z in eco.ZONAS)

GRUPO = {"hierbajo": "Hierba", "hierbajo_grande": "Hierba", "monton_hojas": "Hojas", "alfombra_hojas": "Hojas",
         "arbol_gigante": "Arboles", "arbol_otono": "Arboles", "caracol": "Bichos", "escarabajo": "Bichos", "avispa": "Bichos"}
# (radio que ocupa, escala mínima, escala máxima), en el orden en que se colocan
COLOCACION = [("arbol_gigante", 0.9, 0.9, 1.15), ("arbol_otono", 0.9, 0.85, 1.15), ("tocon", 1.6, 0.8, 1.1),
              ("roca", 1.3, 0.5, 1.1), ("seta_gigante", 1.2, 0.5, 0.9), ("zarza", 1.1, 0.8, 1.3),
              ("matorral", 1.0, 0.7, 1.3), ("girasol_gigante", 0.45, 0.75, 1.15), ("amapola_gigante", 0.4, 0.7, 1.1),
              ("monton_hojas", 1.3, 0.7, 1.0), ("hierbajo_grande", 0.5, 0.7, 1.2), ("hierbajo", 0.3, 0.8, 1.6)]
BICHOS = [("caracol", 0.6, 1.0), ("escarabajo", 0.8, 1.3), ("avispa", 0.7, 1.0)]

rng = np.random.default_rng(SEMILLA)
items = []       # (modelo, grupo, x, y, z, rx, ry, escala_xyz)
ocupado = []     # (x, z, radio)
vallas_col = []  # (nombre, tamaño, posición, giro) de las colisiones de las vallas
rotulos = []     # (id_zona, texto, x, y, z, giro)


def reiniciar():
    global rng
    rng = np.random.default_rng(SEMILLA)
    items.clear(), ocupado.clear(), vallas_col.clear(), rotulos.clear()


def poner(modelo, grupo, x, z, ry=None, s=1.0, y=0.0, rx=0.0):
    ry = rng.uniform(0, 360) if ry is None else ry
    s3 = (s, s, s) if np.ndim(s) == 0 else tuple(s)
    items.append((modelo, grupo, float(x), float(y), float(z), float(rx), float(ry), s3))


def libre(x, z, r, rect, margen=0.7):
    x0, z0, x1, z1 = rect
    if not (x0 + margen < x < x1 - margen and z0 + margen < z < z1 - margen):
        return False
    if -5.0 - r < x < 5.9 + r and -3.8 - r < z < 5.6 + r:       # casa y porche
        return False
    if abs(x - PUERTA_X) < 1.1 + r and 5.0 < z < Z_CALLE:       # sendero
        return False
    if math.hypot(x - ZONA_LIMPIA[0], z - ZONA_LIMPIA[1]) < ZONA_LIMPIA[2] + r:
        return False
    for zo in eco.ZONAS:                                        # paso libre junto a las puertas
        if zo["puerta"] and math.hypot(x - zo["puerta"][0], z - zo["puerta"][1]) < 2.4 + r:
            return False
    return all(math.hypot(x - ox, z - oz) > r + orad for ox, oz, orad in ocupado)


def esparcir(modelo, n, radio, escala, rect, zona=None, intentos=80, ocupa=True):
    hechos = []
    for _ in range(n * intentos):
        if len(hechos) >= n:
            break
        x, z = zona() if zona else (rng.uniform(rect[0], rect[2]), rng.uniform(rect[1], rect[3]))
        if libre(x, z, radio, rect):
            poner(modelo, GRUPO.get(modelo, "Vegetacion"), x, z, s=rng.uniform(*escala))
            if ocupa:
                ocupado.append((x, z, radio))
            hechos.append((x, z))
    return hechos


def cerca_de(cx, cz, r0, r1):
    def f():
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(r0, r1)
        return cx + math.cos(a) * r, cz + math.sin(a) * r
    return f


def tramo_valla(xa, za, xb, zb):
    largo = math.hypot(xb - xa, zb - za)
    if largo < 0.3:
        return
    n = max(1, round(largo / 2.0))
    ry = math.degrees(math.atan2(-(zb - za), xb - xa))
    for i in range(n):
        f = (i + 0.5) / n
        poner("valla", "Vallas", xa + (xb - xa) * f, za + (zb - za) * f, ry=ry, s=(largo / (2.0 * n), 1, 1))
    horizontal = abs(zb - za) < 1e-6
    vallas_col.append((f"Valla{len(vallas_col) + 1}", (largo, 2.2, 0.2) if horizontal else (0.2, 2.2, largo),
                       ((xa + xb) / 2, 1.1, (za + zb) / 2), 0.0))


def linea_valla(fijo, a, b, horizontal, huecos=()):
    """Valla a lo largo de z=fijo (horizontal) o x=fijo, de a a b, dejando huecos (centro, ancho)."""
    cortes = [a]
    for centro, ancho in sorted(huecos):
        cortes += [centro - ancho / 2, centro + ancho / 2]
    cortes.append(b)
    for i in range(0, len(cortes), 2):
        if horizontal:
            tramo_valla(cortes[i], fijo, cortes[i + 1], fijo)
        else:
            tramo_valla(fijo, cortes[i], fijo, cortes[i + 1])


def vallas_y_puertas():
    H = 2.4  # ancho del hueco de una puerta
    p = {z["id"]: z["puerta"] for z in eco.ZONAS}
    linea_valla(Z_CALLE, X0, X1, True, [(PUERTA_X, H)])
    linea_valla(1.0, -15, -4.1, True, [(p["patio"][0], H)])
    linea_valla(1.0, 4.1, 15, True)
    linea_valla(-11.0, -15, 45, True, [(p["arboleda"][0], H)])
    linea_valla(Z0, X0, X1, True)
    linea_valla(X0, Z0, Z_CALLE, False)
    linea_valla(-15.0, Z0, Z_CALLE, False, [(p["zarzal"][1], H)])
    linea_valla(15.0, -11, Z_CALLE, False, [(p["huerto"][1], H)])
    linea_valla(X1, Z0, Z_CALLE, False)
    poner("puerta_jardin", "Entorno", PUERTA_X, Z_CALLE, ry=0)          # puerta_jardin_1: la de la calle
    # hacia qué lado mira el cartel de cada puerta (desde donde llega el jugador)
    lado = {"patio": (0, 1, 0), "huerto": (-1, 0, -90), "arboleda": (0, 1, 0), "zarzal": (1, 0, 90)}
    for zo in eco.ZONAS:
        if not zo["puerta"]:
            continue
        x, z, giro = zo["puerta"]
        poner("puerta_jardin", "Entorno", x, z, ry=giro)                # puerta_jardin_N en el orden de las zonas
        dx, dz, ry = lado[zo["id"]]
        # cartel a un lado de la puerta, del lado del jugador
        cx, cz = x + dx * 1.2 + (2.6 if dz else 0), z + dz * 1.2 + (2.6 if dx else 0)
        poner("cartel_tienda", "Entorno", cx, cz, ry=ry, s=0.85)
        a = math.radians(ry)
        rotulos.append((zo["id"], f"{zo['nombre'].upper()}\n{zo['precio']} monedas",
                        cx + math.sin(a) * 0.06, 1.62 * 0.85, cz + math.cos(a) * 0.06, ry))


def componer():
    poner("parcela", "Entorno", 0, 0, ry=0)
    poner("casa", "Entorno", 0, 0, ry=0)
    poner("cartel_tienda", "Jugabilidad", 5.3, 7.0, ry=-25)   # cartel_tienda_1 = la tienda (juego.gd)
    vallas_y_puertas()
    for z in (7.2, 10.4, 13.6, 16.8, 20.0):
        poner("camino_piedra", "Entorno", PUERTA_X + rng.uniform(-0.15, 0.15), z, ry=rng.uniform(-8, 8), y=0.045)
    for zo in eco.ZONAS:
        rect, cont = zo["rect"], zo["contenido"]
        x0, z0, x1, z1 = rect

        def junto_a_valla():
            lado, t, d = rng.integers(4), rng.uniform(), rng.uniform(0.9, 2.4)
            return [(x0 + d, z0 + t * (z1 - z0)), (x1 - d, z0 + t * (z1 - z0)),
                    (x0 + t * (x1 - x0), z0 + d), (x0 + t * (x1 - x0), z1 - d)][lado]

        arboles = []
        for modelo, radio, e0, e1 in COLOCACION:
            n = cont.get(modelo, 0)
            if n == 0:
                continue
            if modelo == "seta_gigante" and arboles:
                puestos = []
                for k in range(n):
                    ax, az = arboles[k % len(arboles)]
                    puestos += esparcir(modelo, 1, radio, (e0, e1), rect, cerca_de(ax, az, 1.5, 3.5))
            elif modelo == "zarza" and zo["id"] != "zarzal":
                puestos = esparcir(modelo, n, radio, (e0, e1), rect, junto_a_valla)
            else:
                puestos = esparcir(modelo, n, radio, (e0, e1), rect)
            if modelo.startswith("arbol"):
                arboles += puestos
                if modelo == "arbol_otono":
                    for ax, az in puestos:
                        poner("alfombra_hojas", "Hojas", ax, az, s=1.2)
        for modelo, e0, e1 in BICHOS:
            esparcir(modelo, cont.get(modelo, 0), 0.6, (e0, e1), rect, ocupa=False)
    # zona despejada junto al porche: bolsas y herramientas
    cx, cz, _ = ZONA_LIMPIA
    poner("bolsa_basura", "Jugabilidad", cx + 2.0, cz - 1.6, s=1.0)
    poner("bolsa_basura", "Jugabilidad", cx + 2.6, cz - 1.2, s=0.9)
    poner("bolsa_basura", "Jugabilidad", cx - 2.2, cz + 0.6, s=1.0)
    poner("rastrillo", "Jugabilidad", cx - 1.2, cz - 0.6, ry=35, rx=90, y=0.06)
    poner("hoz", "Jugabilidad", cx + 1.3, cz + 0.9, ry=120, rx=90, y=0.04)
    poner("cubo_basura", "Jugabilidad", PUERTA_X + 2.3, Z_CALLE - 1.0, ry=185)
    poner("bolsa_basura", "Jugabilidad", PUERTA_X + 3.2, Z_CALLE - 0.9, s=0.95)
    # calle
    poner("contenedor", "Jugabilidad", PUERTA_X + 4.6, Z_CALLE + 1.1, ry=180, y=0.14)
    poner("bolsa_basura", "Jugabilidad", PUERTA_X + 6.2, Z_CALLE + 1.0, s=1.0, y=0.14)
    poner("camion_basura", "Jugabilidad", -8.0, Z_CALLE + 4.9, ry=90, y=0.02)


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
    ext.append('[ext_resource type="Script" path="res://scripts/juego.gd" id="juego"]')
    ext.append('[ext_resource type="Script" path="res://scripts/hud.gd" id="hud"]')
    cols = [caja_col("Casa", (8.3, 7.0, 6.3), (0, 3.5, 0)),
            caja_col("Porche", (3.4, 0.45, 1.7), (1.8, 0.225, 3.85)),
            caja_col("Escalon", (1.5, 0.22, 0.8), (1.6, 0.11, 5.05)),
            caja_col("Contenedor", (2.1, 1.4, 1.4), (PUERTA_X + 4.6, 0.8, Z_CALLE + 1.1))]
    cols += [caja_col(*v) for v in vallas_col]
    for zo in eco.ZONAS:   # barrera de cada puerta cerrada: juego.gd la quita al comprar la zona
        if zo["puerta"]:
            x, z, giro = zo["puerta"]
            cols.append(caja_col(f"Puerta_{zo['id']}", (2.4, 2.4, 0.3), (x, 1.2, z), giro))
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
[sub_resource type="StandardMaterial3D" id="lejos_mat"]
albedo_color = Color(0.3, 0.42, 0.17, 1)
roughness = 1.0

[sub_resource type="PlaneMesh" id="lejos"]
material = SubResource("lejos_mat")
size = Vector2(1200, 1200)

[node name="Principal" type="Node3D"]
script = ExtResource("juego")

[node name="HUD" type="CanvasLayer" parent="."]
script = ExtResource("hud")

[node name="SueloLejano" type="MeshInstance3D" parent="."]
transform = Transform3D(1, 0, 0, 0, 1, 0, 0, 0, 1, 0, -0.08, 0)
mesh = SubResource("lejos")

[node name="WorldEnvironment" type="WorldEnvironment" parent="."]
environment = SubResource("entorno")

[node name="Sol" type="DirectionalLight3D" parent="."]
transform = {transform(0, 30, 0, -42, -35, (1, 1, 1))}
light_color = Color(1, 0.93, 0.8, 1)
light_energy = 1.5
shadow_enabled = true
shadow_blur = 1.5
directional_shadow_max_distance = 55.0

[node name="Colisiones" type="StaticBody3D" parent="."]

[node name="Suelo" type="CollisionShape3D" parent="Colisiones"]
shape = SubResource("col_suelo")

{chr(10).join(c[1] for c in cols)}
[node name="Jugador" type="CharacterBody3D" parent="."]
transform = {transform(PUERTA_X, 0.05, 9.5, 0, 0, (1, 1, 1))}
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
    nodos.append('[node name="Rotulos" type="Node3D" parent="."]\n')
    for zid, texto, x, y, z, ry in rotulos:
        nodos.append(f'[node name="Rotulo_{zid}" type="Label3D" parent="Rotulos"]\n'
                     f"transform = {transform(x, y, z, 0, ry, (1, 1, 1))}\n"
                     f'pixel_size = 0.0045\nfont_size = 56\noutline_size = 14\n'
                     f'modulate = Color(1, 0.95, 0.8, 1)\noutline_modulate = Color(0.2, 0.1, 0.04, 1)\n'
                     f'text = "{texto.replace(chr(10), chr(92) + "n")}"\n')
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
    reiniciar()
    componer()
    escribir_tscn()
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w") as f:
            json.dump([dict(m=i[0], p=i[2:5], rx=i[5], ry=i[6], s=i[7]) for i in items], f)
