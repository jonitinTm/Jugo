extends RefCounted
## Datos de equilibrio del juego.
## ARCHIVO GENERADO por herramientas_dev/economia.py: cambia los números allí (tiene un
## simulador para ver cómo queda el ritmo) y vuelve a ejecutarlo.

const ALCANCE := 2.6               # metros a los que llegas con la herramienta

## Césped: se siembra con clic derecho sobre las calvas de tierra.
const SEMILLAS_INICIALES := 15
const PAQUETE_SEMILLAS := 30       # semillas por compra
const PRECIO_SEMILLAS := 10
const RADIO_SIEMBRA := 2.2         # siembras todas las calvas en este radio de una vez
const TIEMPO_CRECER := 12.0        # segundos hasta que el césped está hecho
const PREMIO_CESPED := 1           # monedas por cada calva convertida en césped
## Una calva sin sembrar acaba echando malas hierbas. REBROTE_MAX a 0 lo desactiva.
const REBROTE_MIN := 300.0
const REBROTE_MAX := 480.0

## Herramientas en orden de compra. usos: clase de planta → Vector2(daño por golpe, radio de
## área; 0 = solo la planta apuntada). cadencia: segundos entre golpes. La herramienta se
## elige sola: la mejor que tengas para la planta apuntada.
const HERRAMIENTAS := [
	{"nombre": "Manos", "modelo": "guantes", "precio": 0, "cadencia": 0.35, "usos": {"hierba": Vector2(1.0, 0.0), "hojas": Vector2(1.0, 0.0)}, "pos": Vector3(0.0, -0.32, -0.55), "rot": Vector3(-35, 0, 0), "escala": 1.6},
	{"nombre": "Rastrillo", "modelo": "rastrillo", "precio": 12, "cadencia": 0.35, "usos": {"hojas": Vector2(3.0, 1.8), "hierba": Vector2(1.0, 1.0)}, "pos": Vector3(0.32, -0.3, -0.25), "rot": Vector3(78, 0, 0), "escala": 1.0},
	{"nombre": "Hoz", "modelo": "hoz", "precio": 50, "cadencia": 0.35, "usos": {"hierba": Vector2(2.0, 1.4)}, "pos": Vector3(0.32, -0.3, -0.5), "rot": Vector3(-40, 20, 0), "escala": 1.3},
	{"nombre": "Tijeras de podar", "modelo": "tijeras_podar", "precio": 180, "cadencia": 0.3, "usos": {"lenoso": Vector2(4.0, 0.0)}, "pos": Vector3(0.3, -0.45, -0.45), "rot": Vector3(-50, 0, 0), "escala": 1.1},
	{"nombre": "Machete", "modelo": "machete", "precio": 550, "cadencia": 0.3, "usos": {"lenoso": Vector2(7.0, 1.0), "hierba": Vector2(4.0, 1.6)}, "pos": Vector3(0.32, -0.28, -0.5), "rot": Vector3(-45, 0, -10), "escala": 1.3},
	{"nombre": "Desbrozadora", "modelo": "desbrozadora", "precio": 1000, "cadencia": 0.15, "usos": {"hierba": Vector2(4.0, 2.4), "lenoso": Vector2(4.0, 1.6), "hojas": Vector2(2.0, 2.4)}, "pos": Vector3(0.3, -0.25, -0.35), "rot": Vector3(70, 0, 0), "escala": 1.0},
	{"nombre": "Motosierra", "modelo": "motosierra", "precio": 1300, "cadencia": 0.15, "usos": {"tronco": Vector2(8.0, 0.0), "lenoso": Vector2(8.0, 0.0)}, "pos": Vector3(0.3, -0.38, -0.45), "rot": Vector3(0, 180, 0), "escala": 1.2},
]

## Mejoras de la bolsa.
const BOLSAS := [
	{"capacidad": 15, "precio": 0},
	{"capacidad": 30, "precio": 35},
	{"capacidad": 60, "precio": 140},
	{"capacidad": 120, "precio": 480},
]

## Reciclaje: capacidad del contenedor y multiplicador de lo que paga el camión.
const RECICLAJE := [
	{"nombre": "Contenedor básico", "capacidad": 15, "multiplicador": 1.0, "precio": 0},
	{"nombre": "Recogida selectiva", "capacidad": 50, "multiplicador": 1.25, "precio": 90},
	{"nombre": "Compostaje", "capacidad": 90, "multiplicador": 1.6, "precio": 380},
	{"nombre": "Planta de biomasa", "capacidad": 120, "multiplicador": 2.0, "precio": 900},
]

## clase: qué herramientas le sirven · nivel: herramienta mínima · volumen: lo que ocupa en la
## bolsa · valor: monedas que paga el camión · radio/alto: tamaño · calva: tierra que deja
const PLANTAS := {
	"hierbajo": {"nombre": "Hierbajo", "clase": "hierba", "vida": 2.0, "nivel": 0, "volumen": 1, "valor": 1, "radio": 0.4, "alto": 0.8, "calva": 0.55},
	"monton_hojas": {"nombre": "Montón de hojas", "clase": "hojas", "vida": 4.0, "nivel": 0, "volumen": 3, "valor": 4, "radio": 1.2, "alto": 0.6, "calva": 0.0},
	"alfombra_hojas": {"nombre": "Hojarasca", "clase": "hojas", "vida": 9.0, "nivel": 1, "volumen": 5, "valor": 10, "radio": 2.6, "alto": 0.2, "calva": 0.0},
	"hierbajo_grande": {"nombre": "Hierbajo gigante", "clase": "hierba", "vida": 8.0, "nivel": 2, "volumen": 3, "valor": 6, "radio": 0.6, "alto": 2.0, "calva": 0.8},
	"girasol_gigante": {"nombre": "Girasol gigante", "clase": "hierba", "vida": 10.0, "nivel": 2, "volumen": 3, "valor": 12, "radio": 0.5, "alto": 2.4, "calva": 0.6},
	"amapola_gigante": {"nombre": "Amapola gigante", "clase": "hierba", "vida": 10.0, "nivel": 2, "volumen": 3, "valor": 12, "radio": 0.5, "alto": 2.2, "calva": 0.6},
	"matorral": {"nombre": "Matorral", "clase": "lenoso", "vida": 24.0, "nivel": 3, "volumen": 5, "valor": 28, "radio": 1.1, "alto": 1.4, "calva": 1.3},
	"seta_gigante": {"nombre": "Seta gigante", "clase": "lenoso", "vida": 20.0, "nivel": 3, "volumen": 4, "valor": 30, "radio": 1.0, "alto": 1.6, "calva": 1.1},
	"zarza": {"nombre": "Zarza", "clase": "lenoso", "vida": 42.0, "nivel": 4, "volumen": 6, "valor": 60, "radio": 1.3, "alto": 1.4, "calva": 1.5},
	"tocon": {"nombre": "Tocón", "clase": "tronco", "vida": 80.0, "nivel": 6, "volumen": 10, "valor": 80, "radio": 1.2, "alto": 0.8, "calva": 1.6},
	"arbol_gigante": {"nombre": "Árbol gigante", "clase": "tronco", "vida": 200.0, "nivel": 6, "volumen": 15, "valor": 200, "radio": 0.9, "alto": 2.4, "calva": 2.2},
	"arbol_otono": {"nombre": "Árbol de otoño", "clase": "tronco", "vida": 160.0, "nivel": 6, "volumen": 15, "valor": 180, "radio": 0.8, "alto": 2.4, "calva": 2.0},
}
