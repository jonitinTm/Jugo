extends Node3D
## Lógica principal del juego.
##
## Bucle: quitar plantas (la herramienta se elige sola) → vuelan a la bolsa que llevas en la
## mano → cuando se llena va a la carretilla (si tienes) o la dejas en el suelo (Q) → la llevas
## al cubo o al contenedor (E) → cuando el contenedor se llena viene el camión, baja el basurero,
## lo vacía y te paga → tienda (teclas 1-9): herramientas y mejoras (bolsa, carretilla, botas,
## ritmo, alcance, afilado, reciclaje, semillas).
## Cada planta quitada deja una calva de tierra que se siembra con clic derecho. El mapa tiene
## varias zonas que se abren pagando en su puerta; cada zona tiene plantas más duras, más
## valiosas y bichos que atacan.
##
## Controles: clic izquierdo (mantener) = quitar / atacar / empujar el cortacésped
##            clic derecho (mantener) = sembrar · E = vaciar / coger bolsa / abrir zona
##            Q = dejar una bolsa en el suelo · 1-9 = comprar en la tienda
##            F5 = guardar · F9 = borrar la partida

const Datos = preload("res://scripts/datos.gd")
const ARCHIVO := "user://partida.json"
const VERSION_PARTIDA := 2
const INICIO := Vector3(1.6, 0.1, 9.5)     # donde aparece (y reaparece) el jugador
const SONIDOS := ["camion_motor", "claxon", "marcha_atras", "compactador", "caja", "arrancar", "corte",
	"motor_herramienta", "bolsa", "tirar", "soltar", "compra", "error", "paso"]

# --- estado que se guarda
var monedas: int = 0
var nivel: int = 0                 # mejor herramienta comprada
var nivel_bolsa: int = 0
var nivel_reciclaje: int = 0
var nivel_afilado: int = 0
var nivel_velocidad: int = 0
var nivel_ritmo: int = 0
var nivel_alcance: int = 0
var nivel_carretilla: int = 0
var semillas: int = Datos.SEMILLAS_INICIALES
var bolsa_volumen: int = 0         # la bolsa de la mano
var bolsa_valor: int = 0
var carro: Array = []              # bolsas llenas en la carretilla: [volumen, valor]
var contenedor_volumen: int = 0
var contenedor_valor: int = 0
var zonas_abiertas: Array = []     # bool por zona
var trofeo: bool = false
var _quitadas: Array = []          # nombres de las plantas originales ya quitadas
var _bichos_muertos: Array = []
var _cespedes: Array = []          # [x, z, radio] del césped sembrado

# --- estado de la partida en curso
var vida: float = Datos.VIDA_JUGADOR
var _plantas: Array = []           # {nodo, tipo, zona, vida, vida_max, centro, radio, escala}
var _bichos: Array = []            # {nodo, tipo, zona, vida, vida_max, casa, destino, ...}
var _calvas: Array = []            # {nodo, pos, radio, rebrote}  (tierra sin sembrar)
var _puertas: Array = []           # {zona, nodo, pos, colision, rotulo}
var _bolsas_suelo: Array = []      # {nodo, volumen, valor}
var _total_plantas: int = 0
var _total_calvas: int = 0
var _cesped_hecho: int = 0
var _objetivo = null               # planta o bicho al que se apunta (diccionario) o null
var _objetivo_es_bicho: bool = false
var _en_mano: int = -1
var _enfriamiento: float = 0.0
var _enfriamiento_siembra: float = 0.0
var _tiempo: float = 0.0
var _sin_dano: float = 99.0
var _proximo_rebrote: float = 5.0
var _proximo_guardado: float = 30.0
var _camion_ocupado: bool = false
var _camion_x_previa: float = 0.0
var _ruedas: Array = []
var _aviso_semillas: bool = false
var _aviso_lleno: bool = false
var _cargando: bool = false
var _escena_calva: PackedScene
var _escena_cesped: PackedScene
var _escena_hierbajo: PackedScene
var _escena_bolsa: PackedScene
var _nodo_calvas: Node3D
var _nodo_bolsas: Node3D
var _sonidos: Dictionary = {}      # nombre → AudioStream
var _altavoces: Array = []         # reproductores 2D (se reparten por turnos)
var _altavoz_turno: int = 0
var _motor_camion: AudioStreamPlayer3D
var _pitido: AudioStreamPlayer3D
var _basurero: Node3D
var _basurero_andando: bool = false
var _basurero_lugar: Transform3D

@onready var jugador = $Jugador   # jugador.gd
@onready var camara: Camera3D = $Jugador/Camara
@onready var hud = $HUD           # hud.gd
@onready var contenedor: Node3D = get_node_or_null("Jugabilidad/contenedor_1")
@onready var cubo: Node3D = get_node_or_null("Jugabilidad/cubo_basura_1")
@onready var camion: Node3D = get_node_or_null("Jugabilidad/camion_basura_1")
@onready var tienda: Node3D = get_node_or_null("Jugabilidad/cartel_tienda_1")


func _ready() -> void:
	_escena_calva = _cargar("calva_tierra")
	_escena_cesped = _cargar("cesped_nuevo")
	_escena_hierbajo = _cargar("hierbajo")
	_escena_bolsa = _cargar("bolsa_basura")
	_nodo_calvas = Node3D.new()
	_nodo_calvas.name = "Calvas"
	add_child(_nodo_calvas)
	_nodo_bolsas = Node3D.new()
	_nodo_bolsas.name = "BolsasSuelo"
	add_child(_nodo_bolsas)
	_preparar_sonidos()
	for i in range(Datos.ZONAS.size()):
		zonas_abiertas.append(i == 0)
	_registrar_plantas()
	_registrar_bichos()
	_registrar_puertas()
	_optimizar()
	_abrir_hojas(get_node_or_null("Entorno/puerta_jardin_1"), false)
	if camion != null:
		camion.visible = false
		_ruedas = camion.find_children("rueda_*", "", true, false)
		_preparar_camion()
	_cargar_partida()
	_equipar(0)
	_aplicar_mejoras()
	_refrescar_hud()
	if _quitadas.is_empty():
		hud.mensaje("Arranca los hierbajos: mantén el clic izquierdo sobre ellos", 6.0)


func _cargar(modelo: String) -> PackedScene:
	var recurso = load("res://assets/modelos/%s.gltf" % modelo)
	if recurso is PackedScene:
		return recurso
	return null


# ---------------------------------------------------------------- sonido
func _preparar_sonidos() -> void:
	for nombre in SONIDOS:
		var ruta := "res://assets/sonidos/%s.wav" % nombre
		if ResourceLoader.exists(ruta):
			_sonidos[nombre] = load(ruta)
	for i in range(8):
		var a := AudioStreamPlayer.new()
		add_child(a)
		_altavoces.append(a)


## Sonido sin posición (interfaz, herramienta en la mano). Si `una_vez`, no se solapa consigo mismo.
func _sonar(nombre: String, volumen_db: float = 0.0, una_vez: bool = false) -> void:
	if not _sonidos.has(nombre):
		return
	if una_vez:
		for a in _altavoces:
			var p: AudioStreamPlayer = a
			if p.playing and p.stream == _sonidos[nombre]:
				return
	var altavoz: AudioStreamPlayer = _altavoces[_altavoz_turno]
	_altavoz_turno = (_altavoz_turno + 1) % _altavoces.size()
	altavoz.stream = _sonidos[nombre]
	altavoz.volume_db = volumen_db
	altavoz.pitch_scale = randf_range(0.94, 1.06)
	altavoz.play()


## Sonido en un punto del mundo (se oye más o menos según la distancia).
func _sonar_en(nombre: String, posicion: Vector3, volumen_db: float = 0.0) -> void:
	if not _sonidos.has(nombre):
		return
	var a := AudioStreamPlayer3D.new()
	a.stream = _sonidos[nombre]
	a.volume_db = volumen_db
	a.unit_size = 8.0
	add_child(a)
	a.global_position = posicion
	a.finished.connect(a.queue_free)
	a.play()


func _altavoz_3d(nombre: String, padre: Node3D, volumen_db: float, bucle: bool) -> AudioStreamPlayer3D:
	var a := AudioStreamPlayer3D.new()
	a.stream = _sonidos.get(nombre)
	a.volume_db = volumen_db
	a.unit_size = 10.0
	a.max_distance = 90.0
	padre.add_child(a)
	if bucle:
		a.finished.connect(func() -> void:
			if a.get_meta("sonando", false):
				a.play())
	return a


func _bucle(a: AudioStreamPlayer3D, encender: bool) -> void:
	if a == null or a.stream == null:
		return
	a.set_meta("sonando", encender)
	if encender and not a.playing:
		a.play()
	elif not encender:
		a.stop()


# ---------------------------------------------------------------- preparación
func _tipo_de(nodo: Node) -> String:
	var n := String(nodo.name)
	var i := n.rfind("_")
	return n.substr(0, i) if i > 0 else n


func _zona_de(pos: Vector3) -> int:
	for i in range(Datos.ZONAS.size()):
		var z: Dictionary = Datos.ZONAS[i]
		if pos.x >= float(z["x0"]) and pos.x <= float(z["x1"]) and pos.z >= float(z["z0"]) and pos.z <= float(z["z1"]):
			return i
	return 0


func _registrar_plantas() -> void:
	for grupo in ["Hierba", "Vegetacion", "Hojas", "Arboles"]:
		var padre := get_node_or_null(grupo)
		if padre == null:
			continue
		for hijo in padre.get_children():
			var tipo := _tipo_de(hijo)
			if Datos.PLANTAS.has(tipo) and hijo is Node3D:
				_registrar(hijo as Node3D, tipo)
				if float(Datos.PLANTAS[tipo]["calva"]) > 0.0:
					_total_calvas += 1
	_total_plantas = _plantas.size()


func _registrar(nodo: Node3D, tipo: String, escala_final: Vector3 = Vector3.ZERO) -> void:
	var d: Dictionary = Datos.PLANTAS[tipo]
	var escala: Vector3 = nodo.scale if escala_final == Vector3.ZERO else escala_final
	var altura: float = minf(float(d["alto"]) * escala.y * 0.5, 1.2)
	var zona: int = _zona_de(nodo.global_position)
	var vida_max: float = float(d["vida"]) * float(Datos.ZONAS[zona]["vida"])
	_plantas.append({
		"nodo": nodo, "tipo": tipo, "zona": zona, "vida": vida_max, "vida_max": vida_max,
		"centro": nodo.global_position + Vector3.UP * altura,
		"radio": float(d["radio"]) * escala.y, "escala": escala,
	})


func _registrar_bichos() -> void:
	var padre := get_node_or_null("Bichos")
	if padre == null:
		return
	for hijo in padre.get_children():
		var tipo := _tipo_de(hijo)
		if not Datos.BICHOS.has(tipo) or not (hijo is Node3D):
			continue
		var nodo: Node3D = hijo as Node3D
		var d: Dictionary = Datos.BICHOS[tipo]
		var zona: int = _zona_de(nodo.global_position)
		var vida_max: float = float(d["vida"]) * float(Datos.ZONAS[zona]["vida"])
		_bichos.append({
			"nodo": nodo, "tipo": tipo, "zona": zona, "vida": vida_max, "vida_max": vida_max,
			"casa": nodo.global_position, "destino": nodo.global_position, "espera": randf() * 3.0,
			"mordisco": 0.0, "fase": randf() * TAU, "escala": nodo.scale,
			"alas": nodo.find_children("ala_*", "", true, false),
		})


func _registrar_puertas() -> void:
	for i in range(1, Datos.ZONAS.size()):
		var z: Dictionary = Datos.ZONAS[i]
		_puertas.append({
			"zona": i, "pos": z["puerta"],
			"nodo": get_node_or_null("Entorno/puerta_jardin_%d" % (i + 1)),
			"colision": get_node_or_null("Colisiones/Puerta_%s" % z["id"]),
			"rotulo": get_node_or_null("Rotulos/Rotulo_%s" % z["id"]),
		})


## Rendimiento: lo pequeño no proyecta sombra y deja de dibujarse a lo lejos.
func _optimizar() -> void:
	for ajuste in [["Hierba", 45.0, false], ["Hojas", 60.0, false], ["Bichos", 45.0, true],
			["Vegetacion", 75.0, true], ["Vallas", 110.0, true], ["Arboles", 160.0, true]]:
		var padre := get_node_or_null(ajuste[0])
		if padre != null:
			_ajustar_mallas(padre, ajuste[1], ajuste[2])


func _ajustar_mallas(raiz: Node, distancia: float, sombras: bool) -> void:
	for malla in raiz.find_children("*", "MeshInstance3D", true, false):
		var m: MeshInstance3D = malla
		m.visibility_range_end = distancia
		m.visibility_range_end_margin = 6.0
		m.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		if not sombras:
			m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _abrir_hojas(puerta: Node, animado: bool) -> void:
	if puerta == null:
		return
	for par in [["hoja_izq", 100.0], ["hoja_der", -100.0]]:
		var hoja := puerta.find_child(par[0], true, false)
		if hoja is Node3D:
			var hoja3d: Node3D = hoja as Node3D
			var giro: float = deg_to_rad(par[1])
			if animado:
				hoja3d.create_tween().tween_property(hoja3d, "rotation:y", giro, 1.2).set_trans(Tween.TRANS_SINE)
			else:
				hoja3d.rotation.y = giro


## El basurero viaja en el estribo trasero del camión, mirando hacia el jardín.
func _preparar_camion() -> void:
	_motor_camion = _altavoz_3d("camion_motor", camion, 2.0, true)
	_pitido = _altavoz_3d("marcha_atras", camion, -2.0, true)
	var escena := _cargar("basurero")
	if escena == null:
		return
	_basurero = escena.instantiate()
	camion.add_child(_basurero)
	_basurero.position = Vector3(0.75, 0.82, -4.3)
	_basurero.rotation_degrees = Vector3(0, 90, 0)
	_basurero_lugar = _basurero.transform
	var brazo := _basurero.find_child("brazo_der", true, false)
	if brazo is Node3D:
		(brazo as Node3D).rotation_degrees = Vector3(-150, 0, 0)  # agarrado al asidero


# ---------------------------------------------------------------- mejoras
func _alcance() -> float:
	return float(Datos.ALCANCE[nivel_alcance]["valor"])


func _ritmo() -> float:
	return float(Datos.RITMO[nivel_ritmo]["valor"])


func _hueco_carretilla() -> int:
	return int(Datos.CARRETILLA[nivel_carretilla]["valor"]) - carro.size()


func _aplicar_mejoras() -> void:
	var v: float = float(Datos.VELOCIDAD[nivel_velocidad]["valor"])
	jugador.velocidad = Datos.VELOCIDAD_ANDAR * v
	jugador.velocidad_correr = Datos.VELOCIDAD_CORRER * v
	_mostrar_bolsa()


func _mostrar_bolsa() -> void:
	if jugador.has_method("mostrar_bolsa"):
		jugador.mostrar_bolsa(float(bolsa_volumen) / float(_capacidad_bolsa()), carro.size())


# ---------------------------------------------------------------- bucle
func _physics_process(delta: float) -> void:
	_tiempo += delta
	_enfriamiento = maxf(0.0, _enfriamiento - delta)
	_enfriamiento_siembra = maxf(0.0, _enfriamiento_siembra - delta)
	_mover_bichos(delta)
	_regenerar(delta)
	_buscar_objetivo()
	if _objetivo != null:
		var clase: String = "bicho" if _objetivo_es_bicho else String(Datos.PLANTAS[_objetivo["tipo"]]["clase"])
		var mejor: int = _mejor_herramienta(clase)
		if mejor >= 0:
			_equipar(mejor)
	_actualizar_pista()
	if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		if Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT) and _enfriamiento <= 0.0:
			_golpear()
		elif Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT) and _enfriamiento_siembra <= 0.0:
			_enfriamiento_siembra = 0.15
			_sembrar()
	if _tiempo >= _proximo_rebrote:
		_proximo_rebrote = _tiempo + 2.0
		_rebrotar()
	if _tiempo >= _proximo_guardado:
		_proximo_guardado = _tiempo + 30.0
		_guardar_partida()


func _process(_delta: float) -> void:
	if _camion_ocupado and camion != null:
		var avance: float = camion.position.x - _camion_x_previa
		_camion_x_previa = camion.position.x
		for r in _ruedas:
			if r is Node3D:
				(r as Node3D).rotate_x(avance / 0.55)
	if _basurero != null:
		var balanceo: float = sin(_tiempo * 9.0) * 0.6 if _basurero_andando else 0.0
		for par in [["pierna_izq", 1.0], ["pierna_der", -1.0]]:
			var p := _basurero.find_child(par[0], true, false)
			if p is Node3D:
				(p as Node3D).rotation.x = balanceo * float(par[1])


func _unhandled_input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed or event.echo:
		return
	var en_tienda: bool = _cerca_de(tienda, 3.2)
	var tecla: int = event.physical_keycode
	if en_tienda and tecla >= KEY_1 and tecla <= KEY_9:
		_comprar_fila(tecla - KEY_1)
		return
	match tecla:
		KEY_E:
			if _junto_a_deposito():
				_vaciar_bolsa()
			elif _bolsa_cercana() != null:
				_coger_bolsa(_bolsa_cercana())
			elif en_tienda:
				_comprar_fila(0)
			else:
				var puerta: Variant = _puerta_cercana()
				if puerta != null:
					_comprar_zona(puerta)
		KEY_Q:
			_soltar_bolsa()
		KEY_F5:
			_guardar_partida()
			hud.mensaje("Partida guardada")
		KEY_F9:
			_borrar_partida()


func _plano(a: Vector3, b: Vector3) -> float:
	return Vector2(a.x - b.x, a.z - b.z).length()


func _cerca_de(nodo: Node3D, distancia: float) -> bool:
	return nodo != null and _plano(nodo.global_position, jugador.global_position) < distancia


func _junto_a_deposito() -> bool:
	return _cerca_de(contenedor, 3.2) or _cerca_de(cubo, 2.4)


func _capacidad_bolsa() -> int:
	return int(Datos.BOLSAS[nivel_bolsa]["capacidad"])


func _capacidad_contenedor() -> int:
	return int(Datos.RECICLAJE[nivel_reciclaje]["capacidad"])


func _afilado() -> float:
	return pow(Datos.AFILADO_DANO, nivel_afilado)


func _precio_afilado() -> int:
	return int(round(Datos.AFILADO_PRECIO * pow(Datos.AFILADO_FACTOR, nivel_afilado)))


# ---------------------------------------------------------------- apuntar y golpear
## Puntuación de un posible objetivo (negativa = no se le puede apuntar).
func _puntuar(centro: Vector3, radio: float, origen: Vector3, mira: Vector3) -> float:
	var hacia: Vector3 = centro - origen
	if Vector2(hacia.x, hacia.z).length() > _alcance() + radio:
		return -1.0
	var distancia: float = hacia.length()
	if distancia < 0.01:
		return -1.0
	var alineado: float = mira.dot(hacia / distancia)
	# cuanto más grande y cercano, más fácil apuntarle
	if alineado < clampf(0.92 - radio / maxf(distancia, 0.5) * 0.5, 0.45, 0.92):
		return -1.0
	return alineado - distancia * 0.04


func _centro_bicho(b: Dictionary) -> Vector3:
	var nodo: Node3D = b["nodo"]
	var escala: Vector3 = b["escala"]
	return nodo.global_position + Vector3.UP * float(Datos.BICHOS[b["tipo"]]["alto"]) * escala.y * 0.5


func _buscar_objetivo() -> void:
	var origen: Vector3 = camara.global_position
	var mira: Vector3 = -camara.global_transform.basis.z
	var mejor = null
	var mejor_puntos: float = -1.0
	var es_bicho: bool = false
	for b in _bichos:
		if not zonas_abiertas[b["zona"]]:
			continue
		# los bichos tienen prioridad sobre las plantas (+0.3)
		var pb: float = _puntuar(_centro_bicho(b), float(Datos.BICHOS[b["tipo"]]["radio"]) + 0.3, origen, mira)
		if pb >= 0.0 and pb + 0.3 > mejor_puntos:
			mejor_puntos = pb + 0.3
			mejor = b
			es_bicho = true
	for p in _plantas:
		if not zonas_abiertas[p["zona"]]:
			continue
		var pp: float = _puntuar(p["centro"], float(p["radio"]), origen, mira)
		if pp > mejor_puntos:
			mejor_puntos = pp
			mejor = p
			es_bicho = false
	_objetivo = mejor
	_objetivo_es_bicho = es_bicho


## Mejor herramienta comprada para una clase de planta o "bicho" (-1 si ninguna sirve).
func _mejor_herramienta(clase: String) -> int:
	var mejor: int = -1
	var mejor_potencia: float = 0.0
	for i in range(nivel + 1):
		var h: Dictionary = Datos.HERRAMIENTAS[i]
		var usos: Dictionary = h["usos"]
		if usos.has(clase):
			var u: Vector2 = usos[clase]
			var potencia: float = u.x * (1.0 + u.y) / float(h["cadencia"])
			if potencia >= mejor_potencia:
				mejor_potencia = potencia
				mejor = i
	return mejor


func _equipar(indice: int) -> void:
	if indice == _en_mano:
		return
	_en_mano = indice
	jugador.equipar(Datos.HERRAMIENTAS[indice])


func _bolsa_llena() -> bool:
	return bolsa_volumen >= _capacidad_bolsa()


func _golpear() -> void:
	_enfriamiento = 0.35
	var en_mano: Dictionary = Datos.HERRAMIENTAS[maxi(_en_mano, 0)]
	# el cortacésped no se apunta: siega lo que tiene delante mientras lo empujas
	if bool(en_mano.get("empuje", false)) and not (_objetivo != null and _objetivo_es_bicho):
		_segar(en_mano)
		return
	if _objetivo == null:
		jugador.golpe()
		return
	var o: Dictionary = _objetivo
	var es_bicho: bool = _objetivo_es_bicho
	var d: Dictionary = Datos.BICHOS[o["tipo"]] if es_bicho else Datos.PLANTAS[o["tipo"]]
	var clase: String = "bicho" if es_bicho else String(d["clase"])
	var indice: int = _mejor_herramienta(clase)
	if nivel < int(d["nivel"]) or indice < 0:
		hud.mensaje("Necesitas: %s" % Datos.HERRAMIENTAS[int(d["nivel"])]["nombre"])
		_sonar("error", -6.0, true)
		return
	if not es_bicho and _bolsa_llena():
		_avisar_bolsa_llena()
		return
	var herramienta: Dictionary = Datos.HERRAMIENTAS[indice]
	var usos: Dictionary = herramienta["usos"]
	var uso: Vector2 = usos[clase]
	var afilado: float = _afilado()
	_enfriamiento = float(herramienta["cadencia"]) * _ritmo()
	jugador.golpe()
	_sonar(String(herramienta.get("sonido", "corte")), -4.0, String(herramienta.get("sonido", "")) == "motor_herramienta")
	var centro: Vector3 = _centro_bicho(o) if es_bicho else o["centro"]
	if uso.y > 0.0:
		_golpe_en_area(usos, centro, uso.y, afilado)
	elif es_bicho:
		_danar_bicho(o, uso.x * afilado)
	else:
		_danar_planta(o, uso.x * afilado)
	_refrescar_hud()


## Golpe en área: todo lo que esta herramienta pueda dañar alrededor de `centro`.
func _golpe_en_area(usos: Dictionary, centro: Vector3, radio: float, afilado: float) -> void:
	for otra in _plantas.duplicate():
		if _bolsa_llena():
			break
		var datos_otra: Dictionary = Datos.PLANTAS[otra["tipo"]]
		if not zonas_abiertas[otra["zona"]] or nivel < int(datos_otra["nivel"]) or not usos.has(datos_otra["clase"]):
			continue
		if _plano(otra["centro"], centro) <= radio + float(otra["radio"]) * 0.5:
			var uso_otra: Vector2 = usos[datos_otra["clase"]]
			_danar_planta(otra, uso_otra.x * afilado)
	if usos.has("bicho"):
		var uso_bicho: Vector2 = usos["bicho"]
		for otro in _bichos.duplicate():
			if not zonas_abiertas[otro["zona"]] or nivel < int(Datos.BICHOS[otro["tipo"]]["nivel"]):
				continue
			if _plano(_centro_bicho(otro), centro) <= radio + 0.4:
				_danar_bicho(otro, uso_bicho.x * afilado)


## Cortacésped: siega una franja delante de los pies del jugador.
func _segar(herramienta: Dictionary) -> void:
	_enfriamiento = float(herramienta["cadencia"]) * _ritmo()
	jugador.golpe()
	_sonar("motor_herramienta", -6.0, true)
	if _bolsa_llena():
		_avisar_bolsa_llena()
		return
	var delante: Vector3 = -jugador.global_transform.basis.z
	delante.y = 0.0
	var centro: Vector3 = jugador.global_position + delante.normalized() * 0.9
	var usos: Dictionary = herramienta["usos"]
	var radio: float = 0.0
	for c in usos:
		radio = maxf(radio, (usos[c] as Vector2).y)
	_golpe_en_area(usos, centro, radio, _afilado())
	_refrescar_hud()


func _avisar_bolsa_llena() -> void:
	if _hueco_carretilla() > 0:
		_bolsa_a_carretilla()
		return
	hud.mensaje("Bolsa llena: llévala al cubo (E) o déjala en el suelo (Q)", 3.0)
	_sonar("error", -8.0, true)


func _bolsa_a_carretilla() -> void:
	carro.append([bolsa_volumen, bolsa_valor])
	bolsa_volumen = 0
	bolsa_valor = 0
	_sonar("soltar", -4.0)
	hud.mensaje("Bolsa llena a la %s (%d/%d)" % [String(Datos.CARRETILLA[nivel_carretilla]["nombre"]).to_lower(),
		carro.size(), int(Datos.CARRETILLA[nivel_carretilla]["valor"])], 2.0)
	_mostrar_bolsa()
	_refrescar_hud()


func _temblor(nodo: Node3D, base: Vector3) -> void:
	var t := nodo.create_tween()
	t.tween_property(nodo, "scale", base * Vector3(1.06, 0.9, 1.06), 0.06)
	t.tween_property(nodo, "scale", base, 0.12)


## La planta quitada sale volando, encogiéndose, hacia la bolsa del jugador.
func _a_la_bolsa(nodo: Node3D, base: Vector3) -> void:
	var destino: Vector3 = jugador.global_position + Vector3.UP * 0.9 + jugador.global_transform.basis.x * -0.35
	var subida: Vector3 = (nodo.global_position + destino) * 0.5 + Vector3.UP * 1.2
	var t := nodo.create_tween()
	t.set_parallel(true)
	t.tween_property(nodo, "scale", base * 0.04, 0.45).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	t.tween_property(nodo, "global_position", subida, 0.2).set_ease(Tween.EASE_OUT)
	t.chain().tween_property(nodo, "global_position", destino, 0.25).set_ease(Tween.EASE_IN)
	t.chain().tween_callback(func() -> void:
		_sonar("bolsa", -10.0, true)
		if jugador.has_method("meter_en_bolsa"):
			jugador.meter_en_bolsa()
		nodo.queue_free())


func _danar_planta(p: Dictionary, dano: float) -> void:
	var d: Dictionary = Datos.PLANTAS[p["tipo"]]
	var zona: Dictionary = Datos.ZONAS[p["zona"]]
	p["vida"] = float(p["vida"]) - dano
	var nodo: Node3D = p["nodo"]
	var base: Vector3 = p["escala"]
	if float(p["vida"]) > 0.0:
		_temblor(nodo, base)
		return
	_plantas.erase(p)
	_quitadas.append(String(nodo.name))
	bolsa_volumen += int(d["volumen"])
	bolsa_valor += int(round(float(d["valor"]) * float(zona["valor"])))
	_a_la_bolsa(nodo, base)
	if float(d["calva"]) > 0.0:
		_crear_calva(nodo.global_position, float(d["calva"]) * base.y)
	if String(p["tipo"]).begins_with("arbol"):
		_quitar_colision_tronco(nodo.global_position)
	if _bolsa_llena():
		if _hueco_carretilla() > 0:
			_bolsa_a_carretilla()
		elif not _aviso_lleno:
			_aviso_lleno = true
			hud.mensaje("¡Bolsa llena! Llévala al cubo (E) o déjala en el suelo (Q) y sigue", 5.0)
	_mostrar_bolsa()
	if _plantas.is_empty():
		hud.mensaje("¡Todo el mapa despejado!", 10.0)


func _danar_bicho(b: Dictionary, dano: float) -> void:
	b["vida"] = float(b["vida"]) - dano
	var nodo: Node3D = b["nodo"]
	var base: Vector3 = b["escala"]
	if float(b["vida"]) > 0.0:
		_temblor(nodo, base)
		return
	_bichos.erase(b)
	_bichos_muertos.append(String(nodo.name))
	var premio: int = int(round(float(Datos.BICHOS[b["tipo"]]["premio"]) * float(Datos.ZONAS[b["zona"]]["valor"])))
	monedas += premio
	hud.mensaje("+%d monedas" % premio, 1.5)
	_sonar("caja", -10.0)
	var t := nodo.create_tween()
	t.tween_property(nodo, "scale", base * 0.05, 0.25).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
	t.tween_callback(nodo.queue_free)


func _quitar_colision_tronco(posicion: Vector3) -> void:
	var colisiones := get_node_or_null("Colisiones")
	if colisiones == null:
		return
	for c in colisiones.get_children():
		if String(c.name).begins_with("Tronco") and c is Node3D:
			if _plano((c as Node3D).global_position, posicion) < 0.6:
				c.queue_free()


# ---------------------------------------------------------------- bolsas en el suelo
func _bolsa_cercana() -> Variant:
	var mejor: Variant = null
	var mejor_d: float = 2.4
	for b in _bolsas_suelo:
		var d: float = _plano((b["nodo"] as Node3D).global_position, jugador.global_position)
		if d < mejor_d:
			mejor_d = d
			mejor = b
	return mejor


func _soltar_bolsa() -> void:
	var volumen: int = 0
	var valor: int = 0
	if bolsa_volumen > 0:
		volumen = bolsa_volumen
		valor = bolsa_valor
		bolsa_volumen = 0
		bolsa_valor = 0
	elif not carro.is_empty():
		var c: Array = carro.pop_back()
		volumen = int(c[0])
		valor = int(c[1])
	else:
		hud.mensaje("No llevas ninguna bolsa con nada dentro")
		return
	var delante: Vector3 = -jugador.global_transform.basis.z
	delante.y = 0.0
	var pos: Vector3 = jugador.global_position + delante.normalized() * 1.1
	_poner_bolsa(Vector3(pos.x, 0.0, pos.z), volumen, valor, true)
	_sonar("soltar")
	hud.mensaje("Bolsa en el suelo: vuelve a por ella con E", 2.5)
	_mostrar_bolsa()
	_refrescar_hud()


func _poner_bolsa(pos: Vector3, volumen: int, valor: int, animada: bool) -> void:
	var nodo: Node3D = _escena_bolsa.instantiate() if _escena_bolsa != null else Node3D.new()
	_nodo_bolsas.add_child(nodo)
	var tam: float = clampf(0.55 + 0.45 * float(volumen) / float(_capacidad_bolsa()), 0.55, 1.0)
	nodo.position = pos
	nodo.rotation.y = randf() * TAU
	if animada:
		nodo.position.y = 1.0
		nodo.scale = Vector3.ONE * tam * 0.6
		var t := nodo.create_tween().set_parallel(true)
		t.tween_property(nodo, "position:y", 0.0, 0.35).set_trans(Tween.TRANS_BOUNCE).set_ease(Tween.EASE_OUT)
		t.tween_property(nodo, "scale", Vector3.ONE * tam, 0.2)
	else:
		nodo.scale = Vector3.ONE * tam
	_bolsas_suelo.append({"nodo": nodo, "volumen": volumen, "valor": valor})


func _coger_bolsa(b: Dictionary) -> void:
	var volumen: int = int(b["volumen"])
	var valor: int = int(b["valor"])
	if bolsa_volumen == 0:
		bolsa_volumen = volumen
		bolsa_valor = valor
	elif bolsa_volumen + volumen <= _capacidad_bolsa():
		bolsa_volumen += volumen
		bolsa_valor += valor
	elif _hueco_carretilla() > 0:
		carro.append([volumen, valor])
	else:
		hud.mensaje("No te caben más bolsas: vacía la tuya en el cubo o compra una carretilla")
		_sonar("error", -6.0)
		return
	_bolsas_suelo.erase(b)
	var nodo: Node3D = b["nodo"]
	var t := nodo.create_tween().set_parallel(true)
	t.tween_property(nodo, "global_position", jugador.global_position + Vector3.UP * 0.9, 0.25)
	t.tween_property(nodo, "scale", Vector3.ONE * 0.1, 0.25)
	t.chain().tween_callback(nodo.queue_free)
	_sonar("bolsa")
	_mostrar_bolsa()
	_refrescar_hud()


# ---------------------------------------------------------------- bichos y vida del jugador
func _dentro_de_casa(p: Vector3) -> bool:
	return absf(p.x) < 4.8 and p.z > -3.8 and p.z < 5.6


func _mover_bichos(delta: float) -> void:
	var pj: Vector3 = jugador.global_position
	for b in _bichos:
		if not zonas_abiertas[b["zona"]]:
			continue
		var nodo: Node3D = b["nodo"]
		var d: Dictionary = Datos.BICHOS[b["tipo"]]
		var pos: Vector3 = nodo.global_position
		var casa: Vector3 = b["casa"]
		var a_jugador: float = _plano(pos, pj)
		# solo los que están cerca del jugador se mueven (el resto no gasta nada)
		if a_jugador > 40.0:
			continue
		var persigue: bool = a_jugador < 8.0 and _plano(pj, casa) < 16.0
		var destino: Vector3 = pj
		var velocidad: float = float(d["velocidad"])
		if not persigue:
			# deambula cerca de su casa
			b["espera"] = float(b["espera"]) - delta
			if float(b["espera"]) <= 0.0:
				b["espera"] = randf_range(2.0, 5.0)
				var a: float = randf() * TAU
				b["destino"] = casa + Vector3(cos(a), 0.0, sin(a)) * randf_range(0.5, 3.0)
			destino = b["destino"]
			velocidad *= 0.4
		var hacia := Vector3(destino.x - pos.x, 0.0, destino.z - pos.z)
		var distancia: float = hacia.length()
		var parada: float = 1.1 if persigue else 0.2
		if distancia > parada:
			var paso: Vector3 = hacia / distancia * minf(velocidad * delta, distancia)
			var nueva := Vector3(pos.x + paso.x, pos.y, pos.z + paso.z)
			if not _dentro_de_casa(nueva):
				nodo.global_position = nueva
			nodo.rotation.y = lerp_angle(nodo.rotation.y, atan2(hacia.x, hacia.z), minf(1.0, delta * 8.0))
		# las avispas flotan y baten las alas
		if String(b["tipo"]) == "avispa":
			nodo.position.y = casa.y + sin(_tiempo * 3.0 + float(b["fase"])) * 0.15
			var k: int = 0
			for ala in b["alas"]:
				if ala is Node3D:
					(ala as Node3D).rotation.z = sin(_tiempo * 45.0) * 0.5 * (1.0 if k % 2 == 0 else -1.0)
				k += 1
		# mordisco
		b["mordisco"] = maxf(0.0, float(b["mordisco"]) - delta)
		if persigue and a_jugador < 1.5 and float(b["mordisco"]) <= 0.0:
			b["mordisco"] = 1.2
			_herir(float(d["dano"]) * float(Datos.ZONAS[b["zona"]]["dano"]), String(d["nombre"]))


func _herir(dano: float, quien: String) -> void:
	vida -= dano
	_sin_dano = 0.0
	hud.golpe_recibido()
	if vida <= 0.0:
		vida = Datos.VIDA_JUGADOR
		bolsa_volumen = 0
		bolsa_valor = 0
		jugador.global_position = INICIO
		jugador.velocity = Vector3.ZERO
		hud.mensaje("Un %s te ha tumbado: pierdes lo que llevabas en la bolsa" % quien.to_lower(), 5.0)
		_mostrar_bolsa()
	_refrescar_hud()


func _regenerar(delta: float) -> void:
	_sin_dano += delta
	if _sin_dano > Datos.ESPERA_REGENERACION and vida < Datos.VIDA_JUGADOR:
		var antes: int = int(vida)
		vida = minf(Datos.VIDA_JUGADOR, vida + Datos.REGENERACION * delta)
		if int(vida) != antes:
			_refrescar_hud()


# ---------------------------------------------------------------- tierra y césped
func _crear_calva(posicion: Vector3, radio: float) -> void:
	if _escena_calva == null:
		return
	var nodo: Node3D = _escena_calva.instantiate()
	_nodo_calvas.add_child(nodo)
	nodo.position = Vector3(posicion.x, 0.04 + randf() * 0.015, posicion.z)
	nodo.rotation.y = randf() * TAU
	_ajustar_mallas(nodo, 70.0, false)
	if _cargando:
		nodo.scale = Vector3(radio, 1.0, radio)
	else:
		nodo.scale = Vector3(0.05, 1.0, 0.05)
		nodo.create_tween().tween_property(nodo, "scale", Vector3(radio, 1.0, radio), 0.3)
	_calvas.append({
		"nodo": nodo, "pos": nodo.position, "radio": radio,
		"rebrote": _tiempo + randf_range(Datos.REBROTE_MIN, Datos.REBROTE_MAX),
	})
	if not _aviso_semillas and not _cargando:
		_aviso_semillas = true
		hud.mensaje("Queda tierra al descubierto: clic derecho para sembrar césped", 6.0)


## Punto del suelo al que mira el jugador (como mucho a 4,5 m).
func _punto_suelo() -> Vector3:
	var origen: Vector3 = camara.global_position
	var mira: Vector3 = -camara.global_transform.basis.z
	var distancia: float = 4.5
	if mira.y < -0.05:
		distancia = minf(distancia, -origen.y / mira.y)
	var punto: Vector3 = origen + mira * distancia
	punto.y = 0.0
	return punto


func _calvas_en(punto: Vector3, radio: float) -> Array:
	var cerca: Array = []
	for c in _calvas:
		if _plano(c["pos"], punto) <= radio + float(c["radio"]) * 0.5:
			cerca.append(c)
	return cerca


func _sembrar() -> void:
	var cerca := _calvas_en(_punto_suelo(), Datos.RADIO_SIEMBRA)
	if cerca.is_empty():
		return
	if semillas <= 0:
		hud.mensaje("Sin semillas: cómpralas en la tienda (9)")
		return
	for c in cerca:
		if semillas <= 0:
			break
		semillas -= 1
		_calvas.erase(c)
		var pos: Vector3 = c["pos"]
		_cespedes.append([pos.x, pos.z, float(c["radio"])])
		_plantar_cesped(pos, float(c["radio"]), c["nodo"], false)
	_sonar("bolsa", -12.0, true)
	_refrescar_hud()


func _plantar_cesped(pos: Vector3, radio: float, tierra, crecido: bool) -> void:
	if _escena_cesped == null:
		_cesped_listo(pos, tierra)
		return
	var final := Vector3(radio, clampf(radio, 0.7, 1.3), radio)
	var nodo: Node3D = _escena_cesped.instantiate()
	_nodo_calvas.add_child(nodo)
	nodo.position = Vector3(pos.x, 0.055, pos.z)
	nodo.rotation.y = randf() * TAU
	_ajustar_mallas(nodo, 70.0, false)
	if crecido:
		nodo.scale = final
		_cesped_hecho += 1
		return
	nodo.scale = Vector3(radio * 0.15, 0.05, radio * 0.15)
	var t := nodo.create_tween()
	t.tween_property(nodo, "scale", final, Datos.TIEMPO_CRECER).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	t.tween_callback(_cesped_listo.bind(pos, tierra))


func _cesped_listo(pos: Vector3, tierra) -> void:
	if tierra != null and is_instance_valid(tierra):
		tierra.queue_free()
	_cesped_hecho += 1
	monedas += int(round(Datos.PREMIO_CESPED * float(Datos.ZONAS[_zona_de(pos)]["valor"])))
	_refrescar_hud()
	if _total_calvas > 0 and _cesped_hecho == _total_calvas:
		hud.mensaje("¡Todo el mapa tiene césped nuevo!", 10.0)


## Las calvas sin sembrar acaban echando un hierbajo (nunca delante de las narices del jugador).
func _rebrotar() -> void:
	if Datos.REBROTE_MAX <= 0.0 or _escena_hierbajo == null:
		return
	var padre := get_node_or_null("Hierba")
	if padre == null:
		return
	var cambios: bool = false
	for c in _calvas.duplicate():
		if _tiempo < float(c["rebrote"]) or _plano(c["pos"], jugador.global_position) < 6.0:
			continue
		var pos: Vector3 = c["pos"]
		_calvas.erase(c)
		var tierra = c["nodo"]
		if is_instance_valid(tierra):
			tierra.queue_free()
		var nodo: Node3D = _escena_hierbajo.instantiate()
		nodo.name = "rebrote_1"
		padre.add_child(nodo, true)
		nodo.position = Vector3(pos.x, 0.0, pos.z)
		nodo.rotation.y = randf() * TAU
		var final := Vector3.ONE * randf_range(0.9, 1.4)
		nodo.scale = final * 0.1
		_ajustar_mallas(nodo, 45.0, false)
		nodo.create_tween().tween_property(nodo, "scale", final, 3.0)
		_registrar(nodo, "hierbajo", final)
		_total_plantas = maxi(_total_plantas, _plantas.size())
		cambios = true
	if cambios:
		_refrescar_hud()


# ---------------------------------------------------------------- zonas
## Puerta de una zona todavía cerrada junto a la que está el jugador (o null).
func _puerta_cercana() -> Variant:
	for p in _puertas:
		if not zonas_abiertas[p["zona"]] and _plano(p["pos"], jugador.global_position) < 3.6:
			return p
	return null


func _comprar_zona(p: Dictionary) -> void:
	var z: Dictionary = Datos.ZONAS[p["zona"]]
	if _pagar(int(z["precio"]), String(z["nombre"])):
		_abrir_zona(p, true)
		hud.mensaje("¡Zona nueva: %s!" % z["nombre"], 5.0)
		_sonar("compra")
		_refrescar_hud()
		_guardar_partida()


func _abrir_zona(p: Dictionary, animado: bool) -> void:
	zonas_abiertas[p["zona"]] = true
	_abrir_hojas(p["nodo"], animado)
	var colision = p["colision"]
	if colision != null and is_instance_valid(colision):
		colision.queue_free()
	var rotulo = p["rotulo"]
	if rotulo is Label3D:
		(rotulo as Label3D).text = String(Datos.ZONAS[p["zona"]]["nombre"]).to_upper()


# ---------------------------------------------------------------- contenedor, camión y tienda
func _vaciar_bolsa() -> void:
	if bolsa_volumen <= 0 and carro.is_empty():
		hud.mensaje("No llevas nada que tirar")
		return
	var n_bolsas: int = carro.size() + (1 if bolsa_volumen > 0 else 0)
	contenedor_volumen += bolsa_volumen
	contenedor_valor += bolsa_valor
	for c in carro:
		contenedor_volumen += int(c[0])
		contenedor_valor += int(c[1])
	carro.clear()
	bolsa_volumen = 0
	bolsa_valor = 0
	_aviso_lleno = false
	var deposito: Node3D = contenedor if _cerca_de(contenedor, 3.2) else cubo
	_tirar_animacion(deposito, n_bolsas)
	hud.mensaje("%d bolsa%s al %s" % [n_bolsas, "" if n_bolsas == 1 else "s", "contenedor" if deposito == contenedor else "cubo"])
	_mostrar_bolsa()
	_refrescar_hud()
	if contenedor_volumen >= _capacidad_contenedor() and not _camion_ocupado:
		_llamar_camion()


## Las bolsas salen de las manos y caen dentro del cubo, que abre y cierra la tapa.
func _tirar_animacion(deposito: Node3D, n: int) -> void:
	if deposito == null or _escena_bolsa == null:
		_sonar("tirar")
		return
	for tapa_nombre in ["tapa", "tapa_izq", "tapa_der"]:
		var tapa := deposito.find_child(tapa_nombre, true, false)
		if tapa is Node3D:
			var t3: Node3D = tapa as Node3D
			var tw := t3.create_tween()
			tw.tween_property(t3, "rotation:x", deg_to_rad(-70.0), 0.15)
			tw.tween_interval(0.25 + 0.15 * n)
			tw.tween_property(t3, "rotation:x", 0.0, 0.25).set_trans(Tween.TRANS_BOUNCE).set_ease(Tween.EASE_OUT)
	for i in range(mini(n, 6)):
		var b: Node3D = _escena_bolsa.instantiate()
		add_child(b)
		b.global_position = jugador.global_position + Vector3.UP * 1.0
		b.scale = Vector3.ONE * 0.5
		var arriba: Vector3 = deposito.global_position + Vector3.UP * 2.2
		var dentro: Vector3 = deposito.global_position + Vector3.UP * 0.6
		var t := b.create_tween()
		t.tween_interval(0.12 * i)
		t.tween_property(b, "global_position", arriba, 0.25).set_ease(Tween.EASE_OUT)
		t.tween_property(b, "global_position", dentro, 0.18).set_ease(Tween.EASE_IN)
		t.tween_callback(func() -> void:
			_sonar_en("tirar", deposito.global_position, 2.0)
			b.queue_free())


func _pagar(precio: int, que: String) -> bool:
	if monedas < precio:
		hud.mensaje("Te faltan %d monedas para: %s" % [precio - monedas, que])
		_sonar("error", -4.0)
		return false
	monedas -= precio
	_sonar("compra", -2.0)
	return true


## Filas de la tienda en el orden de las teclas 1-9.
## Cada fila: {tecla, nombre, precio (-1 = ya no hay más), modelo, accion}
func _filas_tienda() -> Array:
	var filas: Array = []
	if nivel + 1 < Datos.HERRAMIENTAS.size():
		var h: Dictionary = Datos.HERRAMIENTAS[nivel + 1]
		filas.append({"nombre": h["nombre"], "precio": int(h["precio"]), "modelo": h["modelo"], "accion": "herramienta"})
	elif not trofeo:
		filas.append({"nombre": Datos.TROFEO_NOMBRE, "precio": Datos.TROFEO_PRECIO, "modelo": "moneda", "accion": "trofeo"})
	else:
		filas.append({"nombre": "¡Juego completado!", "precio": -1, "modelo": "moneda", "accion": ""})
	if nivel_bolsa + 1 < Datos.BOLSAS.size():
		var b: Dictionary = Datos.BOLSAS[nivel_bolsa + 1]
		filas.append({"nombre": "Bolsa de %d" % int(b["capacidad"]), "precio": int(b["precio"]), "modelo": "bolsa_basura", "accion": "bolsa"})
	else:
		filas.append({"nombre": "Bolsa: máxima", "precio": -1, "modelo": "bolsa_basura", "accion": ""})
	for m in [["carretilla", Datos.CARRETILLA, nivel_carretilla, "Carretilla", "cubo_basura"],
			["velocidad", Datos.VELOCIDAD, nivel_velocidad, "Velocidad", "guantes"],
			["ritmo", Datos.RITMO, nivel_ritmo, "Ritmo", "tijeras_podar"],
			["alcance", Datos.ALCANCE, nivel_alcance, "Alcance", "rastrillo"]]:
		var tabla: Array = m[1]
		var n: int = m[2]
		if n + 1 < tabla.size():
			var sig: Dictionary = tabla[n + 1]
			filas.append({"nombre": String(sig["nombre"]), "precio": int(sig["precio"]), "modelo": m[4], "accion": m[0]})
		else:
			filas.append({"nombre": "%s: máximo" % m[3], "precio": -1, "modelo": m[4], "accion": ""})
	if nivel_afilado < Datos.AFILADO_MAX:
		filas.append({"nombre": "Afilar (nivel %d)" % (nivel_afilado + 1), "precio": _precio_afilado(), "modelo": "machete", "accion": "afilado"})
	else:
		filas.append({"nombre": "Afilado: máximo", "precio": -1, "modelo": "machete", "accion": ""})
	if nivel_reciclaje + 1 < Datos.RECICLAJE.size():
		var r: Dictionary = Datos.RECICLAJE[nivel_reciclaje + 1]
		filas.append({"nombre": "%s (x%s)" % [r["nombre"], str(r["multiplicador"])], "precio": int(r["precio"]), "modelo": "contenedor", "accion": "reciclaje"})
	else:
		filas.append({"nombre": "Reciclaje: máximo", "precio": -1, "modelo": "contenedor", "accion": ""})
	filas.append({"nombre": "%d semillas" % Datos.PAQUETE_SEMILLAS, "precio": Datos.PRECIO_SEMILLAS, "modelo": "saco_semillas", "accion": "semillas"})
	for i in range(filas.size()):
		var f: Dictionary = filas[i]
		f["tecla"] = str(i + 1)
		f["puede"] = int(f["precio"]) >= 0 and monedas >= int(f["precio"])
	return filas


func _comprar_fila(i: int) -> void:
	var filas := _filas_tienda()
	if i < 0 or i >= filas.size():
		return
	var f: Dictionary = filas[i]
	var accion: String = f["accion"]
	if accion == "" or int(f["precio"]) < 0:
		hud.mensaje("Ya lo tienes al máximo")
		return
	if not _pagar(int(f["precio"]), String(f["nombre"])):
		return
	match accion:
		"herramienta":
			nivel += 1
			_equipar(nivel)
			var h: Dictionary = Datos.HERRAMIENTAS[nivel]
			if bool(h.get("empuje", false)):
				hud.mensaje("¡%s! Mantén el clic y empújalo: siega todo lo que pisa" % h["nombre"], 6.0)
			else:
				hud.mensaje("¡Nueva herramienta: %s!" % h["nombre"], 4.0)
		"trofeo":
			trofeo = true
			hud.mensaje("¡%s! Has completado el juego" % Datos.TROFEO_NOMBRE, 12.0)
		"bolsa":
			nivel_bolsa += 1
			hud.mensaje("¡Bolsa más grande: caben %d!" % _capacidad_bolsa(), 4.0)
		"carretilla":
			nivel_carretilla += 1
			hud.mensaje("¡%s! Llevas %d bolsas llenas además de la de la mano" % [Datos.CARRETILLA[nivel_carretilla]["nombre"],
				int(Datos.CARRETILLA[nivel_carretilla]["valor"])], 5.0)
			if _bolsa_llena():
				_bolsa_a_carretilla()
		"velocidad":
			nivel_velocidad += 1
			hud.mensaje("¡%s! Andas un %d %% más rápido" % [Datos.VELOCIDAD[nivel_velocidad]["nombre"],
				int(round((float(Datos.VELOCIDAD[nivel_velocidad]["valor"]) - 1.0) * 100.0))], 4.0)
		"ritmo":
			nivel_ritmo += 1
			hud.mensaje("¡%s! Trabajas un %d %% más deprisa" % [Datos.RITMO[nivel_ritmo]["nombre"],
				int(round((1.0 / float(Datos.RITMO[nivel_ritmo]["valor"]) - 1.0) * 100.0))], 4.0)
		"alcance":
			nivel_alcance += 1
			hud.mensaje("¡%s! Llegas a %.1f m" % [Datos.ALCANCE[nivel_alcance]["nombre"], _alcance()], 4.0)
		"afilado":
			nivel_afilado += 1
			hud.mensaje("Herramientas afiladas: daño x%.2f" % _afilado(), 3.0)
		"reciclaje":
			nivel_reciclaje += 1
			var r: Dictionary = Datos.RECICLAJE[nivel_reciclaje]
			hud.mensaje("¡%s! El camión paga x%s" % [r["nombre"], str(r["multiplicador"])], 4.0)
			if contenedor_volumen >= _capacidad_contenedor() and not _camion_ocupado:
				_llamar_camion()
		"semillas":
			semillas += Datos.PAQUETE_SEMILLAS
			hud.mensaje("+%d semillas de césped" % Datos.PAQUETE_SEMILLAS)
	_aplicar_mejoras()
	_refrescar_hud()
	_guardar_partida()


func _andar_basurero(destino: Vector3, segundos: float) -> void:
	_basurero_andando = true
	var mira := Vector3(destino.x, _basurero.global_position.y, destino.z)
	if mira.distance_to(_basurero.global_position) > 0.05:
		_basurero.look_at(mira, Vector3.UP, true)
	var t := _basurero.create_tween()
	t.tween_property(_basurero, "global_position", destino, segundos)
	await t.finished
	_basurero_andando = false


## El camión llega con su motor, pita, el basurero baja, vacía el contenedor, sube y se van.
func _llamar_camion() -> void:
	if camion == null or contenedor == null:
		_cobrar()
		return
	_camion_ocupado = true
	hud.mensaje("¡Contenedor lleno! Ya viene el camión de la basura...", 4.0)
	var parada: float = contenedor.position.x + 4.2
	camion.position.x = -75.0
	_camion_x_previa = camion.position.x
	camion.visible = true
	_bucle(_motor_camion, true)
	var t := create_tween()
	t.tween_property(camion, "position:x", parada, 6.0).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	await t.finished
	_sonar_en("claxon", camion.global_position + Vector3.UP * 2.0, 4.0)
	await get_tree().create_timer(0.7).timeout
	# el basurero baja del estribo y se acerca al contenedor
	if _basurero != null:
		var brazo := _basurero.find_child("brazo_der", true, false)
		if brazo is Node3D:
			(brazo as Node3D).rotation_degrees = Vector3.ZERO
		_basurero.reparent(self, true)
		var junto: Vector3 = contenedor.global_position + Vector3(0.6, 0.0, 1.5)
		var suelo: Vector3 = Vector3(_basurero.global_position.x, 0.0, _basurero.global_position.z)
		var salto := _basurero.create_tween()
		salto.tween_property(_basurero, "global_position", suelo, 0.3).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		await salto.finished
		await _andar_basurero(junto, 1.4)
		var a_contenedor := Vector3(contenedor.global_position.x, _basurero.global_position.y, contenedor.global_position.z)
		_basurero.look_at(a_contenedor, Vector3.UP, true)
		_bracear(true)
	# el contenedor se levanta, vuelca y vuelve a su sitio
	_bucle(_pitido, true)
	_sonar_en("compactador", contenedor.global_position + Vector3.UP, 2.0)
	var y0: float = contenedor.position.y
	t = create_tween()
	t.tween_property(contenedor, "position:y", y0 + 0.7, 0.6)
	t.tween_property(contenedor, "rotation:x", deg_to_rad(40.0), 0.5)
	t.tween_interval(0.8)
	t.tween_property(contenedor, "rotation:x", 0.0, 0.5)
	t.tween_property(contenedor, "position:y", y0, 0.6)
	await t.finished
	_bucle(_pitido, false)
	_cobrar()
	# saluda, vuelve al camión y se van
	if _basurero != null:
		_bracear(false)
		var vuelta: Vector3 = camion.to_global(_basurero_lugar.origin)
		await _andar_basurero(Vector3(vuelta.x, 0.0, vuelta.z), 1.4)
		_basurero.reparent(camion, true)
		var subir := _basurero.create_tween()
		subir.tween_property(_basurero, "transform", _basurero_lugar, 0.3)
		await subir.finished
		var brazo2 := _basurero.find_child("brazo_der", true, false)
		if brazo2 is Node3D:
			(brazo2 as Node3D).rotation_degrees = Vector3(-150, 0, 0)
	_sonar_en("claxon", camion.global_position + Vector3.UP * 2.0, 0.0)
	t = create_tween()
	t.tween_property(camion, "position:x", 85.0, 6.0).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	await t.finished
	_bucle(_motor_camion, false)
	camion.visible = false
	_camion_ocupado = false
	if contenedor_volumen >= _capacidad_contenedor():
		_llamar_camion()


## Brazos del basurero: los sube como si empujara el contenedor, o saluda.
func _bracear(empujar: bool) -> void:
	if _basurero == null:
		return
	for nombre in ["brazo_izq", "brazo_der"]:
		var b := _basurero.find_child(nombre, true, false)
		if not (b is Node3D):
			continue
		var b3: Node3D = b as Node3D
		var t := b3.create_tween()
		if empujar:
			t.tween_property(b3, "rotation_degrees:x", -80.0, 0.3)
		elif nombre == "brazo_der":
			for i in range(3):
				t.tween_property(b3, "rotation_degrees", Vector3(-160, 0, -25), 0.18)
				t.tween_property(b3, "rotation_degrees", Vector3(-160, 0, 25), 0.18)
			t.tween_property(b3, "rotation_degrees", Vector3.ZERO, 0.2)
		else:
			t.tween_property(b3, "rotation_degrees:x", 0.0, 0.3)


func _cobrar() -> void:
	var pago: int = int(round(contenedor_valor * float(Datos.RECICLAJE[nivel_reciclaje]["multiplicador"])))
	monedas += pago
	contenedor_volumen = 0
	contenedor_valor = 0
	hud.mensaje("¡El basurero te paga %d monedas!" % pago, 4.0)
	_sonar("caja")
	_refrescar_hud()
	_guardar_partida()


# ---------------------------------------------------------------- guardar y cargar
func _guardar_partida() -> void:
	var calvas: Array = []
	for c in _calvas:
		var pos: Vector3 = c["pos"]
		calvas.append([pos.x, pos.z, float(c["radio"])])
	var bolsas: Array = []
	for b in _bolsas_suelo:
		var pb: Vector3 = (b["nodo"] as Node3D).global_position
		bolsas.append([pb.x, pb.z, int(b["volumen"]), int(b["valor"])])
	var datos := {
		"version": VERSION_PARTIDA,
		"monedas": monedas, "nivel": nivel, "nivel_bolsa": nivel_bolsa, "nivel_reciclaje": nivel_reciclaje,
		"nivel_afilado": nivel_afilado, "nivel_velocidad": nivel_velocidad, "nivel_ritmo": nivel_ritmo,
		"nivel_alcance": nivel_alcance, "nivel_carretilla": nivel_carretilla, "semillas": semillas,
		"bolsa_volumen": bolsa_volumen, "bolsa_valor": bolsa_valor, "carro": carro, "bolsas_suelo": bolsas,
		"contenedor_volumen": contenedor_volumen, "contenedor_valor": contenedor_valor, "zonas": zonas_abiertas,
		"trofeo": trofeo, "quitadas": _quitadas, "bichos_muertos": _bichos_muertos, "cespedes": _cespedes, "calvas": calvas,
	}
	var archivo := FileAccess.open(ARCHIVO, FileAccess.WRITE)
	if archivo != null:
		archivo.store_string(JSON.stringify(datos))
		archivo.close()


func _cargar_partida() -> void:
	if not FileAccess.file_exists(ARCHIVO):
		return
	var archivo := FileAccess.open(ARCHIVO, FileAccess.READ)
	if archivo == null:
		return
	var datos = JSON.parse_string(archivo.get_as_text())
	archivo.close()
	if not (datos is Dictionary):
		return
	_cargando = true
	var version: int = int(datos.get("version", 1))
	monedas = int(datos.get("monedas", 0))
	var nivel_guardado: int = int(datos.get("nivel", 0))
	if version < 2 and nivel_guardado >= 5:
		nivel_guardado += 1  # la v2 metió el cortacésped antes de la desbrozadora
	nivel = clampi(nivel_guardado, 0, Datos.HERRAMIENTAS.size() - 1)
	nivel_bolsa = clampi(int(datos.get("nivel_bolsa", 0)), 0, Datos.BOLSAS.size() - 1)
	nivel_reciclaje = clampi(int(datos.get("nivel_reciclaje", 0)), 0, Datos.RECICLAJE.size() - 1)
	nivel_afilado = clampi(int(datos.get("nivel_afilado", 0)), 0, Datos.AFILADO_MAX)
	nivel_velocidad = clampi(int(datos.get("nivel_velocidad", 0)), 0, Datos.VELOCIDAD.size() - 1)
	nivel_ritmo = clampi(int(datos.get("nivel_ritmo", 0)), 0, Datos.RITMO.size() - 1)
	nivel_alcance = clampi(int(datos.get("nivel_alcance", 0)), 0, Datos.ALCANCE.size() - 1)
	nivel_carretilla = clampi(int(datos.get("nivel_carretilla", 0)), 0, Datos.CARRETILLA.size() - 1)
	semillas = int(datos.get("semillas", Datos.SEMILLAS_INICIALES))
	bolsa_volumen = int(datos.get("bolsa_volumen", 0))
	bolsa_valor = int(datos.get("bolsa_valor", 0))
	carro.clear()
	for c in datos.get("carro", []):
		if c is Array and c.size() >= 2:
			carro.append([int(c[0]), int(c[1])])
	contenedor_volumen = int(datos.get("contenedor_volumen", 0))
	contenedor_valor = int(datos.get("contenedor_valor", 0))
	trofeo = bool(datos.get("trofeo", false))
	var zonas: Array = datos.get("zonas", [])
	for p in _puertas:
		var i: int = p["zona"]
		if i < zonas.size() and bool(zonas[i]):
			_abrir_zona(p, false)
	# plantas y bichos que ya no están
	var quitadas: Dictionary = {}
	for nombre in datos.get("quitadas", []):
		quitadas[String(nombre)] = true
	for p in _plantas.duplicate():
		var nodo: Node3D = p["nodo"]
		if quitadas.has(String(nodo.name)):
			_plantas.erase(p)
			_quitadas.append(String(nodo.name))
			if String(p["tipo"]).begins_with("arbol"):
				_quitar_colision_tronco(nodo.global_position)
			nodo.queue_free()
	var muertos: Dictionary = {}
	for nombre in datos.get("bichos_muertos", []):
		muertos[String(nombre)] = true
	for b in _bichos.duplicate():
		var nodo_b: Node3D = b["nodo"]
		if muertos.has(String(nodo_b.name)):
			_bichos.erase(b)
			_bichos_muertos.append(String(nodo_b.name))
			nodo_b.queue_free()
	for c in datos.get("calvas", []):
		if c is Array and c.size() >= 3:
			_crear_calva(Vector3(float(c[0]), 0.0, float(c[1])), float(c[2]))
	for c in datos.get("cespedes", []):
		if c is Array and c.size() >= 3:
			_cespedes.append([float(c[0]), float(c[1]), float(c[2])])
			_plantar_cesped(Vector3(float(c[0]), 0.0, float(c[1])), float(c[2]), null, true)
	for b in datos.get("bolsas_suelo", []):
		if b is Array and b.size() >= 4:
			_poner_bolsa(Vector3(float(b[0]), 0.0, float(b[1])), int(b[2]), int(b[3]), false)
	_aviso_semillas = not _quitadas.is_empty()
	_cargando = false
	if contenedor_volumen >= _capacidad_contenedor():
		_cobrar()


func _borrar_partida() -> void:
	if FileAccess.file_exists(ARCHIVO):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(ARCHIVO))
	get_tree().reload_current_scene()


# ---------------------------------------------------------------- HUD
func _porcentaje(parte: int, total: int) -> int:
	return 0 if total <= 0 else int(round(100.0 * parte / total))


func _refrescar_hud() -> void:
	var texto_bolsa := "%d / %d" % [bolsa_volumen, _capacidad_bolsa()]
	if nivel_carretilla > 0:
		texto_bolsa += "  +%d/%d" % [carro.size(), int(Datos.CARRETILLA[nivel_carretilla]["valor"])]
	hud.actualizar({
		"monedas": str(monedas),
		"vida": str(int(ceil(vida))),
		"bolsa": texto_bolsa,
		"contenedor": "%d / %d" % [contenedor_volumen, _capacidad_contenedor()],
		"semillas": str(semillas),
		"jardin": "%d %% limpio · %d %% césped" % [
			_porcentaje(_total_plantas - _plantas.size(), _total_plantas),
			_porcentaje(_cesped_hecho, _total_calvas)],
	})


func _actualizar_pista() -> void:
	var en_tienda: bool = _cerca_de(tienda, 3.2) and not _junto_a_deposito()
	hud.tienda(en_tienda, _filas_tienda() if en_tienda else [])
	if _junto_a_deposito():
		var n: int = carro.size() + (1 if bolsa_volumen > 0 else 0)
		hud.pista("E: tirar %d bolsa%s" % [n, "" if n == 1 else "s"] if n > 0 else "No llevas bolsas llenas", -1.0)
		return
	if en_tienda:
		hud.pista("1-9: comprar", -1.0)
		return
	if _bolsa_cercana() != null:
		hud.pista("E: coger la bolsa", -1.0)
		return
	var puerta: Variant = _puerta_cercana()
	if puerta != null:
		var z: Dictionary = Datos.ZONAS[int(puerta["zona"])]
		hud.pista("E: abrir %s (%d monedas)" % [z["nombre"], int(z["precio"])], -1.0)
	elif _bolsa_llena() and _hueco_carretilla() <= 0:
		hud.pista("Bolsa llena · E en el cubo · Q: dejarla en el suelo", -1.0)
	elif _objetivo != null:
		var o: Dictionary = _objetivo
		var d: Dictionary = Datos.BICHOS[o["tipo"]] if _objetivo_es_bicho else Datos.PLANTAS[o["tipo"]]
		if nivel < int(d["nivel"]):
			hud.pista("%s · necesitas: %s" % [d["nombre"], Datos.HERRAMIENTAS[int(d["nivel"])]["nombre"]], -1.0)
		else:
			var h: Dictionary = Datos.HERRAMIENTAS[maxi(_en_mano, 0)]
			hud.pista("%s  (%s)" % [d["nombre"], h["nombre"]], float(o["vida"]) / float(o["vida_max"]))
	elif not _calvas.is_empty() and not _calvas_en(_punto_suelo(), Datos.RADIO_SIEMBRA).is_empty():
		hud.pista("Clic derecho: sembrar césped", -1.0)
	else:
		hud.pista("", -1.0)
