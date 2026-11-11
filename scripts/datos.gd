extends RefCounted
## Datos de equilibrio del juego: herramientas y plantas. Toca aquí para ajustar precios,
## daño, vida o lo que da cada planta.

const CAPACIDAD_BOLSA := 15        # volumen que cabe en la bolsa
const CAPACIDAD_CONTENEDOR := 40   # volumen con el que viene el camión
const ALCANCE := 2.6               # metros a los que llegas con la herramienta
const TIEMPO_GOLPE := 0.35         # segundos entre golpes (manteniendo el clic)

## Herramientas en orden de mejora. "nivel" = posición en la lista.
## pos / rot (grados) / escala: cómo se sujeta el modelo delante de la cámara.
const HERRAMIENTAS := [
	{"nombre": "Guantes", "modelo": "guantes", "precio": 0, "dano": 1.0, "area": 0.0,
		"pos": Vector3(0.0, -0.32, -0.55), "rot": Vector3(-35, 0, 0), "escala": 1.6},
	{"nombre": "Rastrillo", "modelo": "rastrillo", "precio": 15, "dano": 1.0, "area": 0.0,
		"pos": Vector3(0.32, -0.3, -0.25), "rot": Vector3(78, 0, 0), "escala": 1.0},
	{"nombre": "Hoz", "modelo": "hoz", "precio": 45, "dano": 2.0, "area": 0.0,
		"pos": Vector3(0.32, -0.3, -0.5), "rot": Vector3(-40, 20, 0), "escala": 1.3},
	{"nombre": "Tijeras de podar", "modelo": "tijeras_podar", "precio": 120, "dano": 3.0, "area": 0.0,
		"pos": Vector3(0.3, -0.45, -0.45), "rot": Vector3(-50, 0, 0), "escala": 1.1},
	{"nombre": "Machete", "modelo": "machete", "precio": 280, "dano": 5.0, "area": 0.0,
		"pos": Vector3(0.32, -0.28, -0.5), "rot": Vector3(-45, 0, -10), "escala": 1.3},
	{"nombre": "Desbrozadora", "modelo": "desbrozadora", "precio": 600, "dano": 8.0, "area": 2.2,
		"pos": Vector3(0.3, -0.25, -0.35), "rot": Vector3(70, 0, 0), "escala": 1.0},
	{"nombre": "Motosierra", "modelo": "motosierra", "precio": 1000, "dano": 20.0, "area": 0.0,
		"pos": Vector3(0.3, -0.38, -0.45), "rot": Vector3(0, 180, 0), "escala": 1.2},
]

## nivel: herramienta mínima · volumen: lo que ocupa en la bolsa · valor: monedas que paga el camión
## radio / alto: tamaño aproximado (para apuntar) · hojas: el rastrillo hace triple daño
const PLANTAS := {
	"hierbajo": {"nombre": "Hierbajo", "vida": 2.0, "nivel": 0, "volumen": 1, "valor": 1, "radio": 0.4, "alto": 0.8},
	"monton_hojas": {"nombre": "Montón de hojas", "vida": 4.0, "nivel": 0, "volumen": 3, "valor": 3, "radio": 1.2, "alto": 0.6, "hojas": true},
	"alfombra_hojas": {"nombre": "Hojarasca", "vida": 9.0, "nivel": 1, "volumen": 5, "valor": 6, "radio": 2.6, "alto": 0.2, "hojas": true},
	"hierbajo_grande": {"nombre": "Hierbajo gigante", "vida": 6.0, "nivel": 2, "volumen": 3, "valor": 4, "radio": 0.6, "alto": 2.0},
	"girasol_gigante": {"nombre": "Girasol gigante", "vida": 8.0, "nivel": 2, "volumen": 3, "valor": 6, "radio": 0.5, "alto": 2.4},
	"amapola_gigante": {"nombre": "Amapola gigante", "vida": 8.0, "nivel": 2, "volumen": 3, "valor": 6, "radio": 0.5, "alto": 2.2},
	"matorral": {"nombre": "Matorral", "vida": 15.0, "nivel": 3, "volumen": 5, "valor": 12, "radio": 1.1, "alto": 1.4},
	"seta_gigante": {"nombre": "Seta gigante", "vida": 12.0, "nivel": 3, "volumen": 4, "valor": 10, "radio": 1.0, "alto": 1.6},
	"zarza": {"nombre": "Zarza", "vida": 25.0, "nivel": 4, "volumen": 6, "valor": 20, "radio": 1.3, "alto": 1.4},
	"tocon": {"nombre": "Tocón", "vida": 80.0, "nivel": 6, "volumen": 10, "valor": 60, "radio": 1.2, "alto": 0.8},
	"arbol_gigante": {"nombre": "Árbol gigante", "vida": 200.0, "nivel": 6, "volumen": 15, "valor": 150, "radio": 0.9, "alto": 2.4},
	"arbol_otono": {"nombre": "Árbol de otoño", "vida": 160.0, "nivel": 6, "volumen": 15, "valor": 150, "radio": 0.8, "alto": 2.4},
}
