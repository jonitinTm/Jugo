extends Node3D
## Lógica principal: cortar plantas, llenar la bolsa, vaciarla en el contenedor,
## camión que paga y tienda de herramientas.
##
## Controles: clic izquierdo (mantener) = usar la herramienta · E = interactuar

const Datos = preload("res://scripts/datos.gd")

var monedas: int = 0
var nivel: int = 0                 # herramienta actual (índice en Datos.HERRAMIENTAS)
var bolsa_volumen: int = 0
var bolsa_valor: int = 0
var contenedor_volumen: int = 0
var contenedor_valor: int = 0

var _plantas: Array = []           # diccionarios {nodo, tipo, vida, centro, radio}
var _total_plantas: int = 0
var _objetivo = null               # planta a la que se apunta (diccionario) o null
var _enfriamiento: float = 0.0
var _camion_ocupado: bool = false
var _camion_x_previa: float = 0.0
var _ruedas: Array = []

@onready var jugador = $Jugador   # jugador.gd
@onready var camara: Camera3D = $Jugador/Camara
@onready var hud = $HUD           # hud.gd
@onready var contenedor: Node3D = get_node_or_null("Jugabilidad/contenedor_1")
@onready var camion: Node3D = get_node_or_null("Jugabilidad/camion_basura_1")
@onready var tienda: Node3D = get_node_or_null("Jugabilidad/cartel_tienda_1")


func _ready() -> void:
	_registrar_plantas()
	_optimizar()
	_abrir_puerta()
	if camion != null:
		camion.visible = false
		_ruedas = camion.find_children("rueda_*", "", true, false)
	jugador.equipar(Datos.HERRAMIENTAS[nivel])
	_refrescar_hud()
	hud.mensaje("Despeja el jardín: mantén el clic izquierdo sobre los hierbajos", 6.0)


# ---------------------------------------------------------------- preparación
func _tipo_de(nodo: Node) -> String:
	var n := String(nodo.name)
	var i := n.rfind("_")
	return n.substr(0, i) if i > 0 else n


func _registrar_plantas() -> void:
	for grupo in ["Hierba", "Vegetacion", "Hojas", "Arboles"]:
		var padre := get_node_or_null(grupo)
		if padre == null:
			continue
		for hijo in padre.get_children():
			var tipo := _tipo_de(hijo)
			if not Datos.PLANTAS.has(tipo) or not (hijo is Node3D):
				continue
			var d: Dictionary = Datos.PLANTAS[tipo]
			var nodo: Node3D = hijo
			var escala: float = nodo.scale.y
			var altura: float = minf(float(d["alto"]) * escala * 0.5, 1.2)
			_plantas.append({
				"nodo": nodo, "tipo": tipo, "vida": float(d["vida"]),
				"centro": nodo.global_position + Vector3.UP * altura,
				"radio": float(d["radio"]) * escala, "escala": nodo.scale,
			})
	_total_plantas = _plantas.size()


## Rendimiento: lo pequeño no proyecta sombra y deja de dibujarse a lo lejos.
func _optimizar() -> void:
	_ajustar_grupo("Hierba", 45.0, false)
	_ajustar_grupo("Hojas", 60.0, false)
	_ajustar_grupo("Bichos", 45.0, true)
	_ajustar_grupo("Vegetacion", 90.0, true)


func _ajustar_grupo(grupo: String, distancia: float, sombras: bool) -> void:
	var padre := get_node_or_null(grupo)
	if padre == null:
		return
	for malla in padre.find_children("*", "MeshInstance3D", true, false):
		var m: MeshInstance3D = malla
		m.visibility_range_end = distancia
		m.visibility_range_end_margin = 6.0
		m.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		if not sombras:
			m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _abrir_puerta() -> void:
	var puerta := get_node_or_null("Entorno/puerta_jardin_1")
	if puerta == null:
		return
	var izq := puerta.find_child("hoja_izq", true, false)
	var der := puerta.find_child("hoja_der", true, false)
	if izq is Node3D:
		(izq as Node3D).rotation.y = deg_to_rad(100.0)
	if der is Node3D:
		(der as Node3D).rotation.y = deg_to_rad(-100.0)


# ---------------------------------------------------------------- bucle
func _physics_process(delta: float) -> void:
	_enfriamiento = maxf(0.0, _enfriamiento - delta)
	_objetivo = _buscar_objetivo()
	_actualizar_pista()
	var capturado := Input.mouse_mode == Input.MOUSE_MODE_CAPTURED
	if capturado and Input.is_mouse_button_pressed(MOUSE_BUTTON_LEFT) and _enfriamiento <= 0.0:
		_enfriamiento = Datos.TIEMPO_GOLPE
		jugador.golpe()
		_golpear()


func _process(_delta: float) -> void:
	if _camion_ocupado and camion != null:
		var avance: float = camion.position.x - _camion_x_previa
		_camion_x_previa = camion.position.x
		for r in _ruedas:
			if r is Node3D:
				(r as Node3D).rotate_x(avance / 0.55)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.physical_keycode == KEY_E:
		_interactuar()


func _cerca_de(nodo: Node3D, distancia: float) -> bool:
	if nodo == null:
		return false
	var d: Vector3 = nodo.global_position - jugador.global_position
	d.y = 0.0
	return d.length() < distancia


# ---------------------------------------------------------------- cortar
func _buscar_objetivo():
	var origen: Vector3 = camara.global_position
	var mira: Vector3 = -camara.global_transform.basis.z
	var mejor = null
	var mejor_puntos: float = -1.0
	for p in _plantas:
		var hacia: Vector3 = p["centro"] - origen
		var plano := Vector2(hacia.x, hacia.z).length()
		if plano > Datos.ALCANCE + float(p["radio"]):
			continue
		var distancia: float = hacia.length()
		if distancia < 0.01:
			continue
		var alineado: float = mira.dot(hacia / distancia)
		# cuanto más grande y cercana, más fácil apuntarle
		var minimo: float = clampf(0.92 - float(p["radio"]) / maxf(distancia, 0.5) * 0.5, 0.45, 0.92)
		if alineado < minimo:
			continue
		var puntos: float = alineado - distancia * 0.04
		if puntos > mejor_puntos:
			mejor_puntos = puntos
			mejor = p
	return mejor


func _golpear() -> void:
	if _objetivo == null:
		return
	var p: Dictionary = _objetivo
	var d: Dictionary = Datos.PLANTAS[p["tipo"]]
	if nivel < int(d["nivel"]):
		hud.mensaje("Necesitas: %s" % Datos.HERRAMIENTAS[int(d["nivel"])]["nombre"])
		return
	if bolsa_volumen >= Datos.CAPACIDAD_BOLSA:
		hud.mensaje("Bolsa llena: vacíala en el contenedor de la calle (E)")
		return
	var herramienta: Dictionary = Datos.HERRAMIENTAS[nivel]
	var area: float = float(herramienta["area"])
	if area > 0.0:
		var centro: Vector3 = p["centro"]
		for otra in _plantas.duplicate():
			var hacia: Vector3 = otra["centro"] - centro
			hacia.y = 0.0
			if hacia.length() <= area and nivel >= int(Datos.PLANTAS[otra["tipo"]]["nivel"]):
				_danar(otra, float(herramienta["dano"]))
	else:
		_danar(p, float(herramienta["dano"]))
	_refrescar_hud()


func _danar(p: Dictionary, dano: float) -> void:
	var d: Dictionary = Datos.PLANTAS[p["tipo"]]
	if d.get("hojas", false) and Datos.HERRAMIENTAS[nivel]["modelo"] == "rastrillo":
		dano *= 3.0
	p["vida"] = float(p["vida"]) - dano
	var nodo: Node3D = p["nodo"]
	if float(p["vida"]) <= 0.0:
		_plantas.erase(p)
		bolsa_volumen += int(d["volumen"])
		bolsa_valor += int(d["valor"])
		var t := nodo.create_tween()
		t.tween_property(nodo, "scale", nodo.scale * 0.05, 0.25).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
		t.tween_callback(nodo.queue_free)
		if String(p["tipo"]).begins_with("arbol"):
			_quitar_colision_tronco(nodo.global_position)
		if _plantas.is_empty():
			hud.mensaje("¡Jardín despejado!", 10.0)
	else:
		# pequeño temblor al recibir el golpe
		var base: Vector3 = p["escala"]
		var t := nodo.create_tween()
		t.tween_property(nodo, "scale", base * Vector3(1.06, 0.9, 1.06), 0.06)
		t.tween_property(nodo, "scale", base, 0.12)


func _quitar_colision_tronco(posicion: Vector3) -> void:
	var colisiones := get_node_or_null("Colisiones")
	if colisiones == null:
		return
	for c in colisiones.get_children():
		if String(c.name).begins_with("Tronco") and c is Node3D:
			var d: Vector3 = (c as Node3D).global_position - posicion
			d.y = 0.0
			if d.length() < 0.6:
				c.queue_free()


# ---------------------------------------------------------------- contenedor, camión y tienda
func _interactuar() -> void:
	if _cerca_de(contenedor, 3.2):
		if bolsa_volumen <= 0:
			hud.mensaje("La bolsa está vacía")
			return
		contenedor_volumen += bolsa_volumen
		contenedor_valor += bolsa_valor
		bolsa_volumen = 0
		bolsa_valor = 0
		hud.mensaje("Bolsa vaciada en el contenedor")
		_refrescar_hud()
		if contenedor_volumen >= Datos.CAPACIDAD_CONTENEDOR and not _camion_ocupado:
			_llamar_camion()
	elif _cerca_de(tienda, 3.2):
		_comprar()


func _comprar() -> void:
	if nivel + 1 >= Datos.HERRAMIENTAS.size():
		hud.mensaje("Ya tienes la mejor herramienta")
		return
	var siguiente: Dictionary = Datos.HERRAMIENTAS[nivel + 1]
	var precio: int = int(siguiente["precio"])
	if monedas < precio:
		hud.mensaje("Te faltan %d monedas para: %s" % [precio - monedas, siguiente["nombre"]])
		return
	monedas -= precio
	nivel += 1
	jugador.equipar(siguiente)
	hud.mensaje("¡Nueva herramienta: %s!" % siguiente["nombre"], 4.0)
	_refrescar_hud()


func _llamar_camion() -> void:
	if camion == null or contenedor == null:
		_cobrar()
		return
	_camion_ocupado = true
	hud.mensaje("¡Contenedor lleno! Viene el camión de la basura...", 4.0)
	var parada: float = contenedor.position.x + 4.2
	camion.position.x = -75.0
	_camion_x_previa = camion.position.x
	camion.visible = true
	var t := create_tween()
	t.tween_property(camion, "position:x", parada, 5.0).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	await t.finished
	# el contenedor se levanta, vuelca y vuelve a su sitio
	var y0: float = contenedor.position.y
	t = create_tween()
	t.tween_property(contenedor, "position:y", y0 + 0.7, 0.5)
	t.tween_property(contenedor, "rotation:x", deg_to_rad(40.0), 0.4)
	t.tween_interval(0.5)
	t.tween_property(contenedor, "rotation:x", 0.0, 0.4)
	t.tween_property(contenedor, "position:y", y0, 0.5)
	await t.finished
	_cobrar()
	t = create_tween()
	t.tween_property(camion, "position:x", 85.0, 5.0).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	await t.finished
	camion.visible = false
	_camion_ocupado = false
	if contenedor_volumen >= Datos.CAPACIDAD_CONTENEDOR:
		_llamar_camion()


func _cobrar() -> void:
	var pago: int = contenedor_valor
	monedas += pago
	contenedor_volumen = 0
	contenedor_valor = 0
	hud.mensaje("+%d monedas" % pago, 4.0)
	_refrescar_hud()


# ---------------------------------------------------------------- HUD
func _refrescar_hud() -> void:
	var hechas: int = _total_plantas - _plantas.size()
	var porcentaje: int = 0 if _total_plantas == 0 else int(round(100.0 * hechas / _total_plantas))
	hud.actualizar({
		"monedas": "Monedas: %d" % monedas,
		"bolsa": "Bolsa: %d / %d" % [bolsa_volumen, Datos.CAPACIDAD_BOLSA],
		"contenedor": "Contenedor: %d / %d" % [contenedor_volumen, Datos.CAPACIDAD_CONTENEDOR],
		"herramienta": "Herramienta: %s" % Datos.HERRAMIENTAS[nivel]["nombre"],
		"jardin": "Jardín despejado: %d %%" % porcentaje,
	})


func _actualizar_pista() -> void:
	if _cerca_de(contenedor, 3.2):
		hud.pista("E: vaciar la bolsa en el contenedor", -1.0)
	elif _cerca_de(tienda, 3.2):
		if nivel + 1 >= Datos.HERRAMIENTAS.size():
			hud.pista("Tienda: ya tienes todas las herramientas", -1.0)
		else:
			var s: Dictionary = Datos.HERRAMIENTAS[nivel + 1]
			hud.pista("E: comprar %s (%d monedas)" % [s["nombre"], int(s["precio"])], -1.0)
	elif _objetivo != null:
		var p: Dictionary = _objetivo
		var d: Dictionary = Datos.PLANTAS[p["tipo"]]
		if nivel < int(d["nivel"]):
			hud.pista("%s · necesitas: %s" % [d["nombre"], Datos.HERRAMIENTAS[int(d["nivel"])]["nombre"]], -1.0)
		else:
			hud.pista(String(d["nombre"]), float(p["vida"]) / float(d["vida"]))
	else:
		hud.pista("", -1.0)
