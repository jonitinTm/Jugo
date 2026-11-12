extends RefCounted
## Datos de equilibrio del juego.
## ARCHIVO GENERADO por herramientas_dev/economia.py: cambia los números allí (tiene un
## simulador para ver cómo queda el ritmo) y vuelve a ejecutarlo.

## Jugador: velocidad de partida (las botas de VELOCIDAD la multiplican)
const VELOCIDAD_ANDAR := 3.2
const VELOCIDAD_CORRER := 5.0

## Césped: se siembra con clic derecho sobre las calvas de tierra.
const SEMILLAS_INICIALES := 15
const PAQUETE_SEMILLAS := 30
const PRECIO_SEMILLAS := 10
const RADIO_SIEMBRA := 2.2
const TIEMPO_CRECER := 12.0
const PREMIO_CESPED := 1           # x valor de la zona
## Una calva sin sembrar acaba echando malas hierbas. REBROTE_MAX a 0 lo desactiva.
const REBROTE_MIN := 300.0
const REBROTE_MAX := 480.0

const VIDA_JUGADOR := 100.0
const REGENERACION := 6.0
const ESPERA_REGENERACION := 4.0

## Afilado: cada nivel multiplica el daño de todas las herramientas.
const AFILADO_DANO := 1.2
const AFILADO_PRECIO := 25.0
const AFILADO_FACTOR := 1.35
const AFILADO_MAX := 24

const TROFEO_NOMBRE := "Trofeo: Jardín del año"
const TROFEO_PRECIO := 620000

## Zonas del mapa en orden de desbloqueo. vida / valor / dano son multiplicadores.
const ZONAS := [
	{"id": "delantero", "nombre": "Jardín delantero", "x0": -15.0, "z0": 1.0, "x1": 15.0, "z1": 23.0, "precio": 0, "vida": 1.0, "valor": 1.0, "dano": 1.0, "puerta": Vector3(0.0, 0.0, 0.0)},
	{"id": "patio", "nombre": "Patio trasero", "x0": -15.0, "z0": -11.0, "x1": 15.0, "z1": 1.0, "precio": 250, "vida": 2.0, "valor": 2.5, "dano": 1.3, "puerta": Vector3(-9.5, 0.0, 1.0)},
	{"id": "huerto", "nombre": "Huerto abandonado", "x0": 15.0, "z0": -11.0, "x1": 45.0, "z1": 23.0, "precio": 1900, "vida": 4.0, "valor": 6.0, "dano": 1.6, "puerta": Vector3(15.0, 0.0, 12.0)},
	{"id": "arboleda", "nombre": "Arboleda", "x0": -15.0, "z0": -45.0, "x1": 45.0, "z1": -11.0, "precio": 8000, "vida": 8.0, "valor": 14.0, "dano": 2.0, "puerta": Vector3(0.0, 0.0, -11.0)},
	{"id": "zarzal", "nombre": "El Zarzal", "x0": -50.0, "z0": -45.0, "x1": -15.0, "z1": 23.0, "precio": 80000, "vida": 16.0, "valor": 32.0, "dano": 2.5, "puerta": Vector3(-15.0, 0.0, -28.0)},
]

## Herramientas en orden de compra. usos: clase → Vector2(daño por golpe, radio de área).
## La clase "bicho" es el daño contra bichos. La herramienta se elige sola.
const HERRAMIENTAS := [
	{"nombre": "Manos", "modelo": "guantes", "precio": 0, "cadencia": 0.35, "usos": {"hierba": Vector2(1.0, 0.0), "hojas": Vector2(1.0, 0.0)}, "empuje": false, "sonido": "arrancar", "pos": Vector3(0.0, -0.32, -0.55), "rot": Vector3(-35, 0, 0), "escala": 1.6},
	{"nombre": "Rastrillo", "modelo": "rastrillo", "precio": 12, "cadencia": 0.35, "usos": {"hojas": Vector2(3.0, 1.8), "hierba": Vector2(1.0, 1.0), "bicho": Vector2(1.0, 0.0)}, "empuje": false, "sonido": "arrancar", "pos": Vector3(0.32, -0.3, -0.25), "rot": Vector3(78, 0, 0), "escala": 1.0},
	{"nombre": "Hoz", "modelo": "hoz", "precio": 60, "cadencia": 0.35, "usos": {"hierba": Vector2(2.0, 1.4), "bicho": Vector2(2.0, 0.0)}, "empuje": false, "sonido": "corte", "pos": Vector3(0.32, -0.3, -0.5), "rot": Vector3(-40, 20, 0), "escala": 1.3},
	{"nombre": "Tijeras de podar", "modelo": "tijeras_podar", "precio": 200, "cadencia": 0.3, "usos": {"lenoso": Vector2(4.0, 0.0), "bicho": Vector2(3.0, 0.0)}, "empuje": false, "sonido": "corte", "pos": Vector3(0.3, -0.45, -0.45), "rot": Vector3(-50, 0, 0), "escala": 1.1},
	{"nombre": "Machete", "modelo": "machete", "precio": 1000, "cadencia": 0.3, "usos": {"lenoso": Vector2(7.0, 1.0), "hierba": Vector2(4.0, 1.6), "bicho": Vector2(6.0, 1.2)}, "empuje": false, "sonido": "corte", "pos": Vector3(0.32, -0.28, -0.5), "rot": Vector3(-45, 0, -10), "escala": 1.3},
	{"nombre": "Cortacésped", "modelo": "cortacesped", "precio": 3500, "cadencia": 0.15, "usos": {"hierba": Vector2(6.0, 1.3), "hojas": Vector2(6.0, 1.3)}, "empuje": true, "sonido": "motor_herramienta", "pos": Vector3(0.0, -0.72, -0.42), "rot": Vector3(0, 180, 0), "escala": 1.0},
	{"nombre": "Desbrozadora", "modelo": "desbrozadora", "precio": 9000, "cadencia": 0.15, "usos": {"hierba": Vector2(4.0, 2.4), "lenoso": Vector2(4.0, 1.6), "hojas": Vector2(2.0, 2.4), "bicho": Vector2(3.0, 2.0)}, "empuje": false, "sonido": "motor_herramienta", "pos": Vector3(0.3, -0.25, -0.35), "rot": Vector3(70, 0, 0), "escala": 1.0},
	{"nombre": "Motosierra", "modelo": "motosierra", "precio": 60000, "cadencia": 0.15, "usos": {"tronco": Vector2(8.0, 0.0), "lenoso": Vector2(8.0, 0.0), "bicho": Vector2(8.0, 0.0)}, "empuje": false, "sonido": "motor_herramienta", "pos": Vector3(0.3, -0.38, -0.45), "rot": Vector3(0, 180, 0), "escala": 1.2},
]

const BOLSAS := [
	{"capacidad": 15, "precio": 0},
	{"capacidad": 30, "precio": 35},
	{"capacidad": 60, "precio": 400},
	{"capacidad": 120, "precio": 3000},
	{"capacidad": 250, "precio": 15000},
	{"capacidad": 500, "precio": 90000},
]

## Reciclaje: capacidad del contenedor y multiplicador de lo que paga el camión.
const RECICLAJE := [
	{"nombre": "Contenedor básico", "capacidad": 15, "multiplicador": 1.0, "precio": 0},
	{"nombre": "Recogida selectiva", "capacidad": 50, "multiplicador": 1.25, "precio": 120},
	{"nombre": "Compostaje", "capacidad": 90, "multiplicador": 1.6, "precio": 800},
	{"nombre": "Planta de biomasa", "capacidad": 150, "multiplicador": 2.0, "precio": 5000},
	{"nombre": "Central de biogás", "capacidad": 300, "multiplicador": 2.5, "precio": 130000},
]

## Mejoras del jugador. Nivel 0 = lo de partida.
## VELOCIDAD: multiplica andar y correr · RITMO: multiplica la cadencia de las herramientas
## ALCANCE: metros a los que llegas · CARRETILLA: bolsas llenas que llevas además de la de la mano
const VELOCIDAD := [
	{"nombre": "Zapatillas viejas", "valor": 1.0, "precio": 0},
	{"nombre": "Botas de goma", "valor": 1.15, "precio": 25},
	{"nombre": "Botas de trabajo", "valor": 1.3, "precio": 180},
	{"nombre": "Botas de montaña", "valor": 1.45, "precio": 900},
	{"nombre": "Zapatillas de correr", "valor": 1.65, "precio": 6000},
	{"nombre": "Botas con muelles", "valor": 1.85, "precio": 40000},
]

const RITMO := [
	{"nombre": "Sin práctica", "valor": 1.0, "precio": 0},
	{"nombre": "Guantes de agarre", "valor": 0.88, "precio": 35},
	{"nombre": "Buena técnica", "valor": 0.77, "precio": 320},
	{"nombre": "Jardinero curtido", "valor": 0.66, "precio": 2200},
	{"nombre": "Manos de oro", "valor": 0.56, "precio": 14000},
	{"nombre": "Leyenda del jardín", "valor": 0.48, "precio": 90000},
]

const ALCANCE := [
	{"nombre": "Brazo normal", "valor": 2.6, "precio": 0},
	{"nombre": "Mango largo", "valor": 3.1, "precio": 90},
	{"nombre": "Mango telescópico", "valor": 3.7, "precio": 1500},
	{"nombre": "Brazo extensible", "valor": 4.4, "precio": 18000},
]

const CARRETILLA := [
	{"nombre": "Sin carretilla", "valor": 0, "precio": 0},
	{"nombre": "Carretilla", "valor": 1, "precio": 70},
	{"nombre": "Carretilla grande", "valor": 2, "precio": 700},
	{"nombre": "Remolque", "valor": 4, "precio": 5500},
	{"nombre": "Furgoneta", "valor": 8, "precio": 45000},
]

## clase: qué herramientas le sirven · nivel: herramienta mínima · calva: tierra que deja
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
	"tocon": {"nombre": "Tocón", "clase": "tronco", "vida": 80.0, "nivel": 7, "volumen": 10, "valor": 80, "radio": 1.2, "alto": 0.8, "calva": 1.6},
	"arbol_gigante": {"nombre": "Árbol gigante", "clase": "tronco", "vida": 200.0, "nivel": 7, "volumen": 15, "valor": 200, "radio": 0.9, "alto": 2.4, "calva": 2.2},
	"arbol_otono": {"nombre": "Árbol de otoño", "clase": "tronco", "vida": 160.0, "nivel": 7, "volumen": 15, "valor": 180, "radio": 0.8, "alto": 2.4, "calva": 2.0},
}

## nivel: herramienta mínima para hacerles daño · dano: vida que quitan por mordisco
const BICHOS := {
	"caracol": {"nombre": "Caracol", "vida": 5.0, "nivel": 1, "dano": 6.0, "velocidad": 0.9, "premio": 4, "radio": 0.4, "alto": 0.5},
	"escarabajo": {"nombre": "Escarabajo", "vida": 12.0, "nivel": 2, "dano": 9.0, "velocidad": 2.4, "premio": 10, "radio": 0.4, "alto": 0.4},
	"avispa": {"nombre": "Avispa", "vida": 10.0, "nivel": 4, "dano": 12.0, "velocidad": 3.6, "premio": 20, "radio": 0.45, "alto": 1.3},
}
