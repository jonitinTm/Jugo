# Jugo 🌿

Juego incremental en Godot 4: llegas a una casa con un jardín abandonado y salvaje
(árboles gigantes, hierbajos enormes, zarzas, setas, bichos...). Lo vas despejando,
metes la vegetación en bolsas, las tiras al contenedor y, cuando se llena, llega el
camión de la basura y te paga. Con ese dinero compras mejores herramientas que te
dejan romper elementos más duros, abrir zonas nuevas y acabar con bichos más fuertes.

## Estado actual

- **Escena principal** (`escenas/principal.tscn`): la casa, la parcela vallada con su puerta,
  el jardín salvaje (unas 600 piezas colocadas por código), la calle con el contenedor y el
  camión, y un jugador en primera persona para recorrerlo.
- **42 modelos 3D** con texturas (madera, estuco, tejas, piedra, corteza, hojas con
  transparencia...), sombreado suave y mapas de normales.
- **Galería** (`escenas/galeria.tscn`) para ver cada modelo por separado.

| | |
|---|---|
| ![](docs/previews/escena_1_entrada.jpg) | ![](docs/previews/escena_4_porche.jpg) |
| ![](docs/previews/escena_2_aerea.jpg) | ![](docs/previews/escena_3_calle.jpg) |

Las capturas están hechas con un visor glTF (three.js), no con Godot: la luz y el cielo
de Godot serán algo distintos.

| Entorno | Vegetación |
|---|---|
| ![](docs/previews/entorno.jpg) | ![](docs/previews/vegetacion.jpg) |
| **Jugabilidad** | **Herramientas** |
| ![](docs/previews/jugabilidad.jpg) | ![](docs/previews/herramientas.jpg) |
| **Bichos** | **UI en 3D** |
| ![](docs/previews/enemigos.jpg) | ![](docs/previews/ui.jpg) |

## Cómo abrirlo y jugar

1. Abre Godot 4.3 o superior → *Importar* → elige `project.godot` (la primera importación
   tarda un poco).
2. Dale a ▶. Se abre la escena principal.

| Control | Acción |
|---|---|
| WASD / flechas, ratón | moverse y mirar |
| Shift / Espacio | correr / saltar |
| Clic izquierdo (mantener) | quitar la planta o atacar al bicho al que apuntas · empujar el cortacésped |
| Clic derecho (mantener) | sembrar césped en las calvas de tierra cercanas |
| E | tirar las bolsas (cubo o contenedor) · coger una bolsa del suelo · abrir una zona (en su puerta) |
| Q | dejar una bolsa en el suelo (para seguir trabajando y volver a por ella) |
| 1 – 9 | comprar en la tienda (de pie junto al cartel) |
| F5 / F9 | guardar · borrar la partida y empezar de cero |
| Esc | soltar el ratón |

**El bucle:**

1. Empiezas con las **manos** y andando despacio, arrancando hierbajos de uno en uno. Lo que
   quitas **sale volando a la bolsa** que llevas en la mano izquierda, que se va hinchando.
2. Cuando la bolsa se llena: la llevas al **cubo** (junto a la puerta del jardín) o al
   **contenedor** de la calle, o la **dejas en el suelo (Q)** y vuelves luego a por ella (E).
   Con una **carretilla** la bolsa llena se carga sola y sigues con otra.
3. Cuando el contenedor se llena **viene el camión**: se oye el motor, pita al llegar, el
   **basurero** baja del estribo, vacía el contenedor (con su pitido de marcha atrás y el
   compactador), saluda, vuelve a subir y **te paga** (¡ka-ching!).
4. En la **tienda** (cartel de madera junto al porche) compras con las teclas 1-9:
   herramientas, bolsa más grande, carretilla, botas (velocidad), ritmo (golpes más rápidos),
   alcance, afilado (daño), reciclaje (el camión paga más) y semillas.
   **La herramienta se elige sola** según a qué apuntes.
5. Cada planta quitada deja una **calva de tierra**: con clic derecho siembras césped en todas
   las cercanas. Una calva sin sembrar acaba echando otro hierbajo.
6. Con lo ganado **abres la puerta de la zona siguiente**, con plantas más duras y valiosas.

La partida se guarda sola cada 30 segundos y en cada compra (`user://partida.json`).

## Mapa por zonas

![](docs/previews/mapa_zonas.jpg)

| Zona | Precio | Vida de plantas y bichos | Valor | Bichos |
|---|---|---|---|---|
| Jardín delantero | — | x1 | x1 | caracoles |
| Patio trasero | 250 | x2 | x2,5 | caracoles, escarabajos |
| Huerto abandonado | 1.900 | x4 | x6 | + avispas |
| Arboleda | 8.000 | x8 | x14 | escarabajos, avispas |
| El Zarzal | 80.000 | x16 | x32 | de todo, y muchas zarzas |

Cada zona está vallada; su puerta tiene un cartel con el precio y se abre con E.

## Bichos

Solo se activan en las zonas abiertas. Deambulan cerca de su sitio y, si te acercas, te
persiguen y muerden. Si tu vida llega a cero reapareces junto al porche y pierdes lo que
llevabas en la bolsa; la vida se recupera sola tras unos segundos sin recibir daño.

| Bicho | Arma mínima | Comportamiento |
|---|---|---|
| Caracol | Rastrillo | lento, muerde flojo |
| Escarabajo | Hoz | rápido |
| Avispa | Machete | vuela, muy rápida y hace más daño |

Matarlos da monedas directamente.

## Economía

Toda la economía está en `herramientas_dev/economia.py`, que además **simula una partida**
(un jugador que siempre quita lo más rentable y compra en cuanto puede) y genera
`scripts/datos.gd`. Para ajustar el juego: cambia números allí y ejecútalo.

- **Ingresos:** camión (valor de la planta x valor de la zona x reciclaje), césped y bichos.
- **Gastos:** herramientas (12 → 60.000), bolsa (15 → 500), reciclaje (x1 → x2,5), afilado
  (24 niveles, +20 % de daño cada uno), zonas, semillas y el **trofeo final** (620.000).
- **Mejoras del jugador** (tablas `VELOCIDAD`, `RITMO`, `ALCANCE` y `CARRETILLA`):

  | Mejora | De | A | Precios |
  |---|---|---|---|
  | Botas (velocidad) | 3,2 m/s andando | x1,85 | 25 → 40.000 |
  | Ritmo (cadencia de los golpes) | x1 | x0,48 (el doble de rápido) | 35 → 90.000 |
  | Alcance | 2,6 m | 4,4 m | 90 → 18.000 |
  | Carretilla (bolsas llenas que llevas) | 0 | 8 (furgoneta) | 70 → 45.000 |

- **Duración:** el jugador perfecto del simulador abre la última zona en el minuto 44, compra
  el trofeo en el 51 y lo tiene todo en 60. Una persona real debería rondar 1,5–2 horas.

## Interfaz 3D

`scripts/hud.gd` monta la interfaz con los propios modelos: moneda que gira, bolsa,
contenedor, saco de semillas y hoja sobre tablones de madera; pista y barra de vida abajo;
y el panel de la tienda con el modelo de cada compra. Viven en un visor 3D aparte (cámara
ortográfica, fondo transparente) que se pinta encima del juego.

| | |
|---|---|
| ![](docs/previews/ui_juego.jpg) | ![](docs/previews/ui_tienda.jpg) |

Estas dos imágenes son una recreación en el visor glTF con los mismos modelos y medidas que
usa `hud.gd`, no capturas de Godot.

Para ver los modelos sueltos, abre `escenas/galeria.tscn` y pulsa F6
(clic derecho + arrastrar: girar · rueda: zoom · WASD / Q E: moverse).

## Estructura

```
assets/modelos/*.gltf      los modelos (indice.json dice la categoría y el tamaño de cada uno)
  entorno:       casa, valla, puerta_jardin, parcela, suelo_cesped, camino_piedra,
                 calva_tierra, cesped_nuevo
  vegetación:    arbol_gigante, arbol_otono, hierbajo, hierbajo_grande, matorral, zarza,
                 girasol_gigante, amapola_gigante, seta_gigante, tocon, roca,
                 monton_hojas, alfombra_hojas
  jugabilidad:   bolsa_basura, saco_semillas, cubo_basura, contenedor, camion_basura, moneda,
                 basurero
  herramientas:  guantes, hoz, tijeras_podar, rastrillo, machete, cortacesped, desbrozadora,
                 motosierra
  bichos:        escarabajo, caracol, avispa
  ui:            cartel_tienda, panel_madera, boton_madera, boton_verde,
                 flecha_mejora, icono_hoja, etiqueta_precio, barra_progreso, corazon
assets/modelos/texturas/   texturas compartidas por todos los modelos
escenas/principal.tscn     escena principal del juego
escenas/galeria.tscn       escena de prueba con todos los modelos
scripts/juego.gd           lógica: cortar, bolsa, contenedor, camión, tienda
scripts/datos.gd           tablas del juego (lo genera herramientas_dev/economia.py)
scripts/hud.gd             interfaz hecha con modelos 3D
scripts/jugador.gd         jugador en primera persona y herramienta en la mano
scripts/camara_orbital.gd  cámara de la galería
assets/sonidos/*.wav       efectos (los genera herramientas_dev/generar_sonidos.py)
herramientas_dev/          scripts que generan texturas, modelos, sonidos y escenas, y pruebas
docs/previews/             capturas
```

## Progresión (herramientas → qué rompen)

| Nivel | Herramienta | Precio | Despeja | Contra bichos |
|---|---|---|---|---|
| 0 | Manos (guantes) | — | hierbajo pequeño, montón de hojas | — |
| 1 | Rastrillo | 12 | montones de hojas grandes y rápido | caracol |
| 2 | Hoz | 60 | hierbajo grande, flores gigantes | escarabajo |
| 3 | Tijeras de podar | 200 | matorral, setas | sí |
| 4 | Machete | 1.000 | zarza | avispa |
| 5 | Cortacésped | 3.500 | **se empuja**: siega toda la hierba y las hojas que pisa, sin apuntar | — |
| 6 | Desbrozadora | 9.000 | todo lo verde en área | todos (área) |
| 7 | Motosierra | 60.000 | tocones y árboles gigantes | sí |

## Probar el juego automáticamente

`herramientas_dev/prueba_juego.gd` recorre el bucle entero (comprar, arrancar, bolsa,
carretilla, dejar y coger una bolsa, cortacésped, contenedor, camión y basurero), escribe
`OK`/`FALLO` por cada paso y guarda capturas:

```bash
godot --path . -s herramientas_dev/prueba_juego.gd -- capturas_prueba
```

Usa la partida guardada del proyecto (`user://partida.json`): hazlo en una copia del proyecto
con otro `config/name` en `project.godot` si no quieres perder la tuya.

## Convenciones de los modelos

- Unidades en metros, **Y hacia arriba**, el frente mira a **+Z**.
- Origen en la base (en el suelo). Herramientas: origen en el agarre. UI: origen en el centro.
- Las piezas animables son **nodos hijos con el origen en su punto de giro**:
  - `camion_basura`: `rueda_*` (giran en X), `brazo` (elevador trasero).
  - `basurero`: `pierna_izq/der` (cadera), `brazo_izq/der` (hombro).
  - `cortacesped`: origen en el manillar; el suelo queda 0,9 m por debajo.
  - `contenedor`: `tapa_izq`, `tapa_der` (bisagra atrás), `rueda_*`.
  - `cubo_basura`: `tapa`, `rueda_izq`, `rueda_der`.
  - `puerta_jardin`: `hoja_izq`, `hoja_der` (bisagras en los postes).
  - `escarabajo`: `pata_izq_1..3`, `pata_der_1..3`. `avispa`: `ala_izq`, `ala_der`.
  - `guantes`: `guante_izq`, `guante_der`.
  - `barra_progreso`: `relleno` tiene el origen a la izquierda → `scale.x` de 0 a 1 = progreso.
- Los materiales (`madera`, `estuco`, `tejado`, `hojas_verde`...) usan las texturas de
  `assets/modelos/texturas` teñidas con una paleta común. Godot los importa como `StandardMaterial3D`.
- Las hojas y la hierba llevan las dos caras en la geometría (con las mismas normales), para
  que se iluminen igual por delante y por detrás.
- **UI en 3D**: para usarlas en el HUD 2D, ponlas en un `SubViewport` con su cámara y usa
  un `ViewportTexture` en un `TextureRect` (o rénderízalas una vez a PNG como iconos).

## Regenerar o modificar

Todo sale de código, así que se puede cambiar y regenerar en segundos:

```bash
pip install trimesh numpy scipy pillow
python3 herramientas_dev/generar_texturas.py              # texturas
python3 herramientas_dev/generar_sonidos.py               # sonidos
python3 herramientas_dev/economia.py                      # equilibrio → scripts/datos.gd
python3 herramientas_dev/generar_modelos.py               # todos los modelos
python3 herramientas_dev/generar_modelos.py casa zarza    # solo algunos
blender -b --factory-startup -P herramientas_dev/blender_pulir.py           # pulido (biseles)
blender -b --factory-startup -P herramientas_dev/blender_capturas.py        # capturas
python3 herramientas_dev/generar_escena.py                # escena principal
python3 herramientas_dev/generar_galeria.py               # galería
```

### Pulido y capturas con Blender

- `blender_pulir.py` se pasa **después** de `generar_modelos.py`. Funde las caras planas, bisela
  las aristas vivas de las piezas duras (madera, metal, plástico, interfaz) para que atrapen la
  luz y recalcula sus normales. Las hojas, briznas y pétalos no se tocan: llevan las dos caras en
  la geometría y Blender las descartaría al importar, así que el `.gltf` final se monta con las
  piezas biseladas de Blender y el resto del original. Un modelo ya pulido se salta (usa
  `--forzar` para repetirlo). Si regeneras un modelo, vuelve a pulirlo:
  `blender -b --factory-startup -P herramientas_dev/blender_pulir.py -- casa valla`.
- `blender_capturas.py` renderiza cada modelo (EEVEE, cielo físico) y una hoja de contactos por
  categoría en `docs/previews/blender/`. Con `-- <carpeta> modelo1 modelo2` saca solo esos.
- Sin Python instalado vale el de Blender:
  `"C:\Program Files\Blender Foundation\Blender 5.0\5.0\python\bin\python.exe" -m pip install --target <carpeta> trimesh scipy pillow`
  y luego `PYTHONPATH=<carpeta>` al ejecutar los generadores.

- Colores: `PALETA` al principio de `generar_modelos.py`. Materiales y texturas: `MATS`.
  Suavidad de las piezas redondas (lados de tubos, tornos y cilindros): `DETALLE`.
- Densidad y colocación del jardín: función `componer()` de `generar_escena.py`
  (cantidades de cada planta, árboles, zona despejada, semilla aleatoria).
- Si retocas `principal.tscn` a mano en Godot, no vuelvas a ejecutar `generar_escena.py`
  o perderás los cambios (o guarda tu versión con otro nombre).
