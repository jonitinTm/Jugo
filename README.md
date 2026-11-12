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
| Clic izquierdo (mantener) | quitar la planta a la que apuntas |
| Clic derecho (mantener) | sembrar césped en las calvas de tierra cercanas |
| E | vaciar la bolsa (cubo o contenedor) · comprar la siguiente herramienta (tienda) |
| R / F / T | en la tienda: bolsa más grande / reciclaje / semillas |
| Esc | soltar el ratón |

**El bucle:**

1. Empiezas con las **manos**, arrancando hierbajos de uno en uno. Lo que quitas va a la bolsa.
2. Vacías la bolsa en el **cubo** (junto a la puerta del jardín) o en el **contenedor** de la
   calle. Cuando se junta bastante viene el **camión**, lo vuelca y te paga.
3. En la **tienda** (cartel de madera junto al porche) compras herramientas, bolsas más
   grandes y semillas. Cada herramienta cambia *cómo* limpias: el rastrillo arrastra varios
   hierbajos y barre hojas, la hoz siega un arco, las tijeras y el machete abren matorrales y
   zarzas, la desbrozadora limpia mientras andas y la motosierra tala tocones y árboles.
   **La herramienta se elige sola** según la planta a la que apuntas.
4. Cada planta quitada deja una **calva de tierra**. Con clic derecho siembras césped en todas
   las calvas cercanas a la vez; crece solo y da una moneda. Una calva sin sembrar acaba
   echando otro hierbajo al cabo de unos minutos.

## Economía

Toda la economía está en `herramientas_dev/economia.py`, que además **simula una partida**
(un jugador que siempre quita lo más rentable y compra la mejora más barata que puede) y
genera `scripts/datos.gd`. Para ajustar el juego: cambia números allí y ejecútalo.

- **Ingresos:** el camión paga el valor de lo que haya en el contenedor multiplicado por el
  nivel de reciclaje; cada calva sembrada da 1 moneda.
- **Gastos (tienda):** herramientas (12 → 1300), bolsa (15 → 120 de capacidad), reciclaje
  (el camión paga x1 → x2 y el contenedor crece) y semillas (30 por 10 monedas).
- **Ritmo simulado** (jugador perfecto; una persona tardará bastante más): primera compra a
  los 40 s, una mejora cada 1-2 minutos, motosierra hacia el minuto 15 y jardín completo en
  unos 19 minutos.

## Interfaz 3D

`scripts/hud.gd` monta la interfaz con los propios modelos: moneda que gira, bolsa,
contenedor, saco de semillas y hoja sobre tablones de madera; pista y barra de vida abajo;
y el panel de la tienda con el modelo de cada compra. Viven en un visor 3D aparte (cámara
ortográfica, fondo transparente) que se pinta encima del juego.

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
  jugabilidad:   bolsa_basura, saco_semillas, cubo_basura, contenedor, camion_basura, moneda
  herramientas:  guantes, hoz, tijeras_podar, rastrillo, machete, desbrozadora, motosierra
  bichos:        escarabajo, caracol, avispa
  ui:            cartel_tienda, panel_madera, boton_madera, boton_verde,
                 flecha_mejora, icono_hoja, etiqueta_precio, barra_progreso
assets/modelos/texturas/   texturas compartidas por todos los modelos
escenas/principal.tscn     escena principal del juego
escenas/galeria.tscn       escena de prueba con todos los modelos
scripts/juego.gd           lógica: cortar, bolsa, contenedor, camión, tienda
scripts/datos.gd           tablas del juego (lo genera herramientas_dev/economia.py)
scripts/hud.gd             interfaz hecha con modelos 3D
scripts/jugador.gd         jugador en primera persona y herramienta en la mano
scripts/camara_orbital.gd  cámara de la galería
herramientas_dev/          scripts en Python que generan texturas, modelos y escenas
docs/previews/             capturas
```

## Progresión propuesta (herramientas → qué rompen)

| Nivel | Herramienta | Despeja | Contra bichos |
|---|---|---|---|
| 0 | Guantes | hierbajo pequeño, montón de hojas | — |
| 1 | Rastrillo | montones de hojas grandes y rápido | — |
| 2 | Hoz | hierbajo grande, flores gigantes | caracol |
| 3 | Tijeras de podar | matorral, setas | escarabajo |
| 4 | Machete | zarza | avispa |
| 5 | Desbrozadora | todo lo verde en área | todos (área) |
| 6 | Motosierra | tocones y árboles gigantes | — |

El bucle sería: despejar → la vegetación llena tu bolsa → bolsa al contenedor →
contenedor lleno = llega el `camion_basura`, levanta el contenedor con su `brazo` y
te paga en `moneda` → compras en el `cartel_tienda` → la barra de zona
(`barra_progreso`) marca cuánto llevas de cada parte del jardín.

## Convenciones de los modelos

- Unidades en metros, **Y hacia arriba**, el frente mira a **+Z**.
- Origen en la base (en el suelo). Herramientas: origen en el agarre. UI: origen en el centro.
- Las piezas animables son **nodos hijos con el origen en su punto de giro**:
  - `camion_basura`: `rueda_*` (giran en X), `brazo` (elevador trasero).
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
python3 herramientas_dev/generar_modelos.py               # todos los modelos
python3 herramientas_dev/generar_modelos.py casa zarza    # solo algunos
python3 herramientas_dev/generar_escena.py                # escena principal
python3 herramientas_dev/generar_galeria.py               # galería
```

- Colores: `PALETA` al principio de `generar_modelos.py`. Materiales y texturas: `MATS`.
- Densidad y colocación del jardín: función `componer()` de `generar_escena.py`
  (cantidades de cada planta, árboles, zona despejada, semilla aleatoria).
- Si retocas `principal.tscn` a mano en Godot, no vuelvas a ejecutar `generar_escena.py`
  o perderás los cambios (o guarda tu versión con otro nombre).
