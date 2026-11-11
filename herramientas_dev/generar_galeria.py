#!/usr/bin/env python3
"""Genera escenas/galeria.tscn: todos los modelos de assets/modelos expuestos en filas."""
import math
import os

import numpy as np
import trimesh

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELOS = os.path.join(RAIZ, "assets", "modelos")
ORDEN = ["entorno", "vegetacion", "jugabilidad", "herramientas", "enemigos", "ui"]
ESCALA = {"herramientas": 4.0, "enemigos": 3.0}  # solo para verlos mejor en la galería
ALTURA = {"ui": 0.8}


def tr(R, o):
    c = [R[:, 0], R[:, 1], R[:, 2]]
    v = [f"{x:.4f}" for col in c for x in col] + [f"{x:.3f}" for x in o]
    return "Transform3D(" + ", ".join(v) + ")"


def main():
    ext, nodos = [], []
    z = 0.0
    for fila, carpeta in enumerate(ORDEN):
        archivos = sorted(f for f in os.listdir(os.path.join(MODELOS, carpeta)) if f.endswith(".glb"))
        s = ESCALA.get(carpeta, 1.0)
        tam = []
        for f in archivos:
            b = trimesh.load(os.path.join(MODELOS, carpeta, f)).bounds
            tam.append((b[1] - b[0]) * s)
        prof = max(t[2] for t in tam)
        x = 0.0
        z -= prof / 2 + 2.0
        for f, t in zip(archivos, tam):
            nombre = f[:-4]
            rid = f"{len(ext) + 1}_{nombre}"
            ext.append(f'[ext_resource type="PackedScene" path="res://assets/modelos/{carpeta}/{f}" id="{rid}"]')
            x += t[0] / 2
            pos = (x, ALTURA.get(carpeta, 0.0), z)
            nodos.append(f'[node name="{nombre}" parent="Modelos" instance=ExtResource("{rid}")]\n'
                         f"transform = {tr(np.eye(3) * s, pos)}\n")
            nodos.append(f'[node name="Etiqueta_{nombre}" type="Label3D" parent="Etiquetas"]\n'
                         f"transform = {tr(np.eye(3), (x, ALTURA.get(carpeta, 0.0) + t[1] + 0.4, z))}\n"
                         f'billboard = 1\nfont_size = 48\noutline_size = 12\ntext = "{nombre}"\n')
            x += t[0] / 2 + 1.5
        z -= prof / 2 + 2.0

    def rot(rx, ry):
        a, b = math.radians(rx), math.radians(ry)
        Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]])
        Ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]])
        return Ry @ Rx

    cab = f"""[gd_scene format=3]

{chr(10).join(ext)}
[ext_resource type="Script" path="res://scripts/camara_orbital.gd" id="camara"]

[sub_resource type="ProceduralSkyMaterial" id="cielo_mat"]
sky_top_color = Color(0.38, 0.6, 0.85, 1)
sky_horizon_color = Color(0.85, 0.82, 0.74, 1)
ground_bottom_color = Color(0.36, 0.3, 0.22, 1)
ground_horizon_color = Color(0.85, 0.82, 0.74, 1)
sun_angle_max = 20.0

[sub_resource type="Sky" id="cielo"]
sky_material = SubResource("cielo_mat")

[sub_resource type="Environment" id="entorno"]
background_mode = 2
sky = SubResource("cielo")
ambient_light_source = 3
ambient_light_energy = 0.9
reflected_light_source = 2
tonemap_mode = 2
ssao_enabled = true
glow_enabled = true
glow_intensity = 0.3

[sub_resource type="StandardMaterial3D" id="suelo_mat"]
albedo_color = Color(0.55, 0.68, 0.33, 1)
roughness = 1.0

[sub_resource type="PlaneMesh" id="suelo"]
material = SubResource("suelo_mat")
size = Vector2(200, 200)

[node name="Galeria" type="Node3D"]

[node name="WorldEnvironment" type="WorldEnvironment" parent="."]
environment = SubResource("entorno")

[node name="Sol" type="DirectionalLight3D" parent="."]
transform = {tr(rot(-50, -35), (0, 20, 0))}
light_color = Color(1, 0.95, 0.85, 1)
light_energy = 1.3
shadow_enabled = true
directional_shadow_max_distance = 150.0

[node name="Suelo" type="MeshInstance3D" parent="."]
transform = {tr(np.eye(3), (30, -0.01, -30))}
mesh = SubResource("suelo")

[node name="Camara" type="Camera3D" parent="."]
script = ExtResource("camara")
objetivo = Vector3(10, 1, -6)
distancia = 22.0

[node name="Modelos" type="Node3D" parent="."]

[node name="Etiquetas" type="Node3D" parent="."]

"""
    with open(os.path.join(RAIZ, "escenas", "galeria.tscn"), "w") as f:
        f.write(cab + "\n".join(nodos))
    print(f"galeria.tscn con {len(ext)} modelos")


if __name__ == "__main__":
    main()
