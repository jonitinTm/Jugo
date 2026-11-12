extends Node3D
## Lógica principal del juego.
##
## Bucle: quitar plantas (la herramienta se elige sola según la planta) → la bolsa se llena →
## se vacía en el contenedor o en el cubo → el camión paga → tienda (herramientas, bolsa, semillas).
## Cada planta quitada deja una calva de tierra: con clic derecho se siembra césped en todas
## las calvas cercanas. Las calvas sin sembrar acaban echando malas hierbas otra vez.
##
## Controles: clic izquierdo (mantener) = quitar · clic derecho (mantener) = sembrar
##            E = vaciar bolsa / comprar herramienta · R = bolsa · F = reciclaje · T = semillas

const Datos = preload("res://scripts/datos.gd")

var monedas: int = 0
var nivel: int = 0                 # mejor herramienta comprada (índice en Datos.HERRAMIENTAS)
var nivel_bolsa: int = 0
var nivel_reciclaje: int = 0
var semillas: int = Datos.SEMILLAS_INICIALES
var bolsa_volumen: int = 0
var bolsa_valor: int = 0
var contenedor_volumen: int = 0
var contenedor_valor: int = 0

var _plantas: Array = []           # {nodo, tipo, vida, centro, radio, escala}
var _calvas: Array = []            # {nodo, pos, radio, rebrote}  (tierra sin sembrar)
var _total_plantas: int = 0
var _total_calvas: int = 0         # calvas que puede llegar a haber (plantas que dejan tierra)
var _cesped_hecho: int = 0
var _objetivo = null               # planta a la que se apunta (diccionario) o null
var _en_mano: int = -1             # herramienta que se ve en la mano
var _enfriamiento: float = 0.0
var _enfriamiento_siembra: float = 0.0
var _tiempo: float = 0.0
var _proximo_rebrote: float = 5.0
var _camion_ocupado: bool = false
var _camion_x_previa: float = 0.0
var _ruedas: Array = []
var _aviso_semillas: bool = false
var _escena_calva: PackedScene
var _escena_cesped: PackedScene
var _escena_hierbajo: PackedScene
var _nodo_calvas: Node3D

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
	_nodo_calvas = Node3D.new()
	_nodo_calvas.name = "Calvas"
	add_child(_nodo_calvas)
	_registrar_plantas()
	_optimizar()
	_abrir_puerta()
	if camion != null:
		camion.visible = false
		_ruedas = camion.find_children("rueda_*", "", true, false)
	_equipar(0)
	_refrescar_hud()
	hud.mensaje("Arranca los hierbajos: mantén el clic izquierdo sobre ellos", 6.0)


func _cargar(modelo: String) -> PackedScene:
	var recurso = load("res://assets/modelos/%s.gltf" % modelo)
	if recurso is PackedScene:
		return recurso
	return null


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
			if Datos.PLANTAS.has(tipo) and hijo is Node3D:
				_registrar(hijo as Node3D, tipo)
				if float(Datos.PLANTAS[tipo]["calva"]) > 0.0:
					_total_calvas += 1
	_total_plantas = _plantas.size()


func _registrar(nodo: Node3D, tipo: String, escala_final: Vector3 = Vector3.ZERO) -> void:
	var d: Dictionary = Datos.PLANTAS[tipo]
	var escala: Vector3 = nodo.scale if escala_final == Vector3.ZERO else escala_final
	var altura: float = minf(float(d["alto"]) * escala.y * 0.5, 1.2)
	_plantas.append({
		"nodo": nodo, "tipo": tipo, "vida": float(d["vida"]),
		"centro": nodo.global_position + Vector3.UP * altura,
		"radio": float(d["radio"]) * escala.y, "escala": escala,
	})


## Rendimiento: lo pequeño no proyecta sombra y deja de dibujarse a lo lejos.
func _optimizar() -> void:
	for ajuste in [["Hierba", 45.0, false], ["Hojas", 60.0, false], ["Bichos", 45.0, true], ["Vegetacion", 90.0, true]]:
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
	_tiempo += delta
	_enfriamiento = maxf(0.0, _enfriamiento - delta)
	_enfriamiento_siembra = maxf(0.0, _enfriamiento_siembra - delta)
	_objetivo = _buscar_objetivo()
	if _objetivo != null:
		var mejor: int = _mejor_herramienta(String(Datos.PLANTAS[_objetivo["tipo"]]["clase"]))
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


func _process(_delta: float) -> void:
	if _camion_ocupado and camion != null:
		var avance: float = camion.position.x - _camion_x_previa
		_camion_x_previa = camion.position.x
		for r in _ruedas:
			if r is Node3D:
				(r as Node3D).rotate_x(avance / 0.55)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.physical_keycode:
			KEY_E:
				if _junto_a_deposito():
					_vaciar_bolsa()
				elif _cerca_de(tienda, 3.2):
					_comprar_herramienta()
			KEY_R:
				if _cerca_de(tienda, 3.2):
					_comprar_bolsa()
			KEY_F:
				if _cerca_de(tienda, 3.2):
					_comprar_reciclaje()
			KEY_T:
				if _cerca_de(tienda, 3.2):
					_comprar_semillas()


func _cerca_de(nodo: Node3D, distancia: float) -> bool:
	if nodo == null:
		return false
	var d: Vector3 = nodo.global_position - jugador.global_position
	d.y = 0.0
	return d.length() < distancia


func _junto_a_deposito() -> bool:
	return _cerca_de(contenedor, 3.2) or _cerca_de(cubo, 2.4)


func _capacidad_bolsa() -> int:
	return int(Datos.BOLSAS[nivel_bolsa]["capacidad"])


func _capacidad_contenedor() -> int:
	return int(Datos.RECICLAJE[nivel_reciclaje]["capacidad"])


# ---------------------------------------------------------------- quitar plantas
func _buscar_objetivo():
	var origen: Vector3 = camara.global_position
	var mira: Vector3 = -camara.global_transform.basis.z
	var mejor = null
	var mejor_puntos: float = -1.0
	for p in _plantas:
		var hacia: Vector3 = p["centro"] - origen
		if Vector2(hacia.x, hacia.z).length() > Datos.ALCANCE + float(p["radio"]):
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


## Mejor herramienta comprada para una clase de planta (-1 si ninguna sirve).
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


func _golpear() -> void:
	_enfriamiento = 0.35
	if _objetivo == null:
		jugador.golpe()
		return
	var p: Dictionary = _objetivo
	var d: Dictionary = Datos.PLANTAS[p["tipo"]]
	var indice: int = _mejor_herramienta(String(d["clase"]))
	if nivel < int(d["nivel"]) or indice < 0:
		hud.mensaje("Necesitas: %s" % Datos.HERRAMIENTAS[int(d["nivel"])]["nombre"])
		return
	if bolsa_volumen >= _capacidad_bolsa():
		hud.mensaje("Bolsa llena: vacíala en el cubo o en el contenedor (E)")
		return
	var herramienta: Dictionary = Datos.HERRAMIENTAS[indice]
	var usos: Dictionary = herramienta["usos"]
	var uso: Vector2 = usos[d["clase"]]
	_enfriamiento = float(herramienta["cadencia"])
	jugador.golpe()
	if uso.y > 0.0:
		# golpe en área: todo lo que esta herramienta pueda cortar alrededor de la planta apuntada
		var centro: Vector3 = p["centro"]
		for otra in _plantas.duplicate():
			var datos_otra: Dictionary = Datos.PLANTAS[otra["tipo"]]
			if nivel < int(datos_otra["nivel"]) or not usos.has(datos_otra["clase"]):
				continue
			var hacia: Vector3 = otra["centro"] - centro
			hacia.y = 0.0
			if hacia.length() <= uso.y + float(otra["radio"]) * 0.5:
				var uso_otra: Vector2 = usos[datos_otra["clase"]]
				_danar(otra, uso_otra.x)
	else:
		_danar(p, uso.x)
	_refrescar_hud()


func _danar(p: Dictionary, dano: float) -> void:
	var d: Dictionary = Datos.PLANTAS[p["tipo"]]
	p["vida"] = float(p["vida"]) - dano
	var nodo: Node3D = p["nodo"]
	var base: Vector3 = p["escala"]
	if float(p["vida"]) > 0.0:
		# pequeño temblor al recibir el golpe
		var temblor := nodo.create_tween()
		temblor.tween_property(nodo, "scale", base * Vector3(1.06, 0.9, 1.06), 0.06)
		temblor.tween_property(nodo, "scale", base, 0.12)
		return
	_plantas.erase(p)
	bolsa_volumen += int(d["volumen"])
	bolsa_valor += int(d["valor"])
	var t := nodo.create_tween()
	t.tween_property(nodo, "scale", base * 0.05, 0.25).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
	t.tween_callback(nodo.queue_free)
	if float(d["calva"]) > 0.0:
		_crear_calva(nodo.global_position, float(d["calva"]) * base.y)
	if String(p["tipo"]).begins_with("arbol"):
		_quitar_colision_tronco(nodo.global_position)
	if _plantas.is_empty():
		hud.mensaje("¡Jardín despejado!", 10.0)


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


# ---------------------------------------------------------------- tierra y césped
func _crear_calva(posicion: Vector3, radio: float) -> void:
	if _escena_calva == null:
		return
	var nodo: Node3D = _escena_calva.instantiate()
	_nodo_calvas.add_child(nodo)
	nodo.position = Vector3(posicion.x, 0.04 + randf() * 0.015, posicion.z)
	nodo.rotation.y = randf() * TAU
	nodo.scale = Vector3(0.05, 1.0, 0.05)
	_ajustar_mallas(nodo, 70.0, false)
	nodo.create_tween().tween_property(nodo, "scale", Vector3(radio, 1.0, radio), 0.3)
	_calvas.append({
		"nodo": nodo, "pos": nodo.position, "radio": radio,
		"rebrote": _tiempo + randf_range(Datos.REBROTE_MIN, Datos.REBROTE_MAX),
	})
	if not _aviso_semillas:
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
		var d: Vector3 = c["pos"] - punto
		d.y = 0.0
		if d.length() <= radio + float(c["radio"]) * 0.5:
			cerca.append(c)
	return cerca


func _sembrar() -> void:
	var cerca := _calvas_en(_punto_suelo(), Datos.RADIO_SIEMBRA)
	if cerca.is_empty():
		return
	if semillas <= 0:
		hud.mensaje("Sin semillas: cómpralas en la tienda (T)")
		return
	for c in cerca:
		if semillas <= 0:
			break
		semillas -= 1
		_calvas.erase(c)
		_plantar_cesped(c)
	_refrescar_hud()


func _plantar_cesped(c: Dictionary) -> void:
	if _escena_cesped == null:
		_cesped_listo(c)
		return
	var radio: float = c["radio"]
	var alto: float = clampf(radio, 0.7, 1.3)
	var nodo: Node3D = _escena_cesped.instantiate()
	_nodo_calvas.add_child(nodo)
	var pos: Vector3 = c["pos"]
	nodo.position = pos + Vector3.UP * 0.012
	nodo.rotation.y = randf() * TAU
	nodo.scale = Vector3(radio * 0.15, 0.05, radio * 0.15)
	_ajustar_mallas(nodo, 70.0, false)
	var t := nodo.create_tween()
	t.tween_property(nodo, "scale", Vector3(radio, alto, radio), Datos.TIEMPO_CRECER).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	t.tween_callback(_cesped_listo.bind(c))


func _cesped_listo(c: Dictionary) -> void:
	var tierra = c["nodo"]
	if is_instance_valid(tierra):
		tierra.queue_free()
	_cesped_hecho += 1
	monedas += Datos.PREMIO_CESPED
	_refrescar_hud()
	if _total_calvas > 0 and _cesped_hecho >= _total_calvas:
		hud.mensaje("¡Todo el jardín tiene césped nuevo!", 10.0)


## Las calvas sin sembrar acaban echando un hierbajo (nunca delante de las narices del jugador).
func _rebrotar() -> void:
	if Datos.REBROTE_MAX <= 0.0 or _escena_hierbajo == null:
		return
	var padre := get_node_or_null("Hierba")
	if padre == null:
		return
	for c in _calvas.duplicate():
		if _tiempo < float(c["rebrote"]):
			continue
		var pos: Vector3 = c["pos"]
		var lejos: Vector3 = pos - jugador.global_position
		lejos.y = 0.0
		if lejos.length() < 6.0:
			continue
		_calvas.erase(c)
		var tierra = c["nodo"]
		if is_instance_valid(tierra):
			tierra.queue_free()
		var nodo: Node3D = _escena_hierbajo.instantiate()
		nodo.name = "hierbajo_rebrote"
		padre.add_child(nodo, true)
		nodo.position = Vector3(pos.x, 0.0, pos.z)
		nodo.rotation.y = randf() * TAU
		var final := Vector3.ONE * randf_range(0.9, 1.4)
		nodo.scale = final * 0.1
		_ajustar_mallas(nodo, 45.0, false)
		nodo.create_tween().tween_property(nodo, "scale", final, 3.0)
		_registrar(nodo, "hierbajo", final)
		_total_plantas = maxi(_total_plantas, _plantas.size())
	_refrescar_hud()


# ---------------------------------------------------------------- contenedor, camión y tienda
func _vaciar_bolsa() -> void:
	if bolsa_volumen <= 0:
		hud.mensaje("La bolsa está vacía")
		return
	contenedor_volumen += bolsa_volumen
	contenedor_valor += bolsa_valor
	bolsa_volumen = 0
	bolsa_valor = 0
	hud.mensaje("Bolsa vaciada")
	_refrescar_hud()
	if contenedor_volumen >= _capacidad_contenedor() and not _camion_ocupado:
		_llamar_camion()


func _pagar(precio: int, que: String) -> bool:
	if monedas < precio:
		hud.mensaje("Te faltan %d monedas para: %s" % [precio - monedas, que])
		return false
	monedas -= precio
	return true


func _comprar_herramienta() -> void:
	if nivel + 1 >= Datos.HERRAMIENTAS.size():
		hud.mensaje("Ya tienes todas las herramientas")
		return
	var siguiente: Dictionary = Datos.HERRAMIENTAS[nivel + 1]
	if _pagar(int(siguiente["precio"]), String(siguiente["nombre"])):
		nivel += 1
		_equipar(nivel)
		hud.mensaje("¡Nueva herramienta: %s!" % siguiente["nombre"], 4.0)
		_refrescar_hud()


func _comprar_bolsa() -> void:
	if nivel_bolsa + 1 >= Datos.BOLSAS.size():
		hud.mensaje("Ya tienes la bolsa más grande")
		return
	var siguiente: Dictionary = Datos.BOLSAS[nivel_bolsa + 1]
	if _pagar(int(siguiente["precio"]), "bolsa más grande"):
		nivel_bolsa += 1
		hud.mensaje("¡Bolsa más grande: caben %d!" % int(siguiente["capacidad"]), 4.0)
		_refrescar_hud()


func _comprar_reciclaje() -> void:
	if nivel_reciclaje + 1 >= Datos.RECICLAJE.size():
		hud.mensaje("El reciclaje ya está al máximo")
		return
	var siguiente: Dictionary = Datos.RECICLAJE[nivel_reciclaje + 1]
	if _pagar(int(siguiente["precio"]), String(siguiente["nombre"])):
		nivel_reciclaje += 1
		hud.mensaje("¡%s! El camión paga x%s" % [siguiente["nombre"], str(siguiente["multiplicador"])], 4.0)
		_refrescar_hud()
		if contenedor_volumen >= _capacidad_contenedor() and not _camion_ocupado:
			_llamar_camion()


func _comprar_semillas() -> void:
	if _pagar(Datos.PRECIO_SEMILLAS, "semillas"):
		semillas += Datos.PAQUETE_SEMILLAS
		hud.mensaje("+%d semillas de césped" % Datos.PAQUETE_SEMILLAS)
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
	if contenedor_volumen >= _capacidad_contenedor():
		_llamar_camion()


func _cobrar() -> void:
	var pago: int = int(round(contenedor_valor * float(Datos.RECICLAJE[nivel_reciclaje]["multiplicador"])))
	monedas += pago
	contenedor_volumen = 0
	contenedor_valor = 0
	hud.mensaje("+%d monedas" % pago, 4.0)
	_refrescar_hud()


# ---------------------------------------------------------------- HUD
func _porcentaje(parte: int, total: int) -> int:
	return 0 if total <= 0 else int(round(100.0 * parte / total))


func _refrescar_hud() -> void:
	hud.actualizar({
		"monedas": str(monedas),
		"bolsa": "%d / %d" % [bolsa_volumen, _capacidad_bolsa()],
		"contenedor": "%d / %d" % [contenedor_volumen, _capacidad_contenedor()],
		"semillas": str(semillas),
		"jardin": "%d %% limpio · %d %% césped" % [
			_porcentaje(_total_plantas - _plantas.size(), _total_plantas),
			_porcentaje(_cesped_hecho, _total_calvas)],
	})


## Filas del panel de la tienda: tecla, nombre, precio (-1 = ya no hay más), modelo del icono.
func _filas_tienda() -> Array:
	var filas: Array = []
	if nivel + 1 < Datos.HERRAMIENTAS.size():
		var h: Dictionary = Datos.HERRAMIENTAS[nivel + 1]
		filas.append({"tecla": "E", "nombre": h["nombre"], "precio": int(h["precio"]), "modelo": h["modelo"]})
	else:
		filas.append({"tecla": "E", "nombre": "Herramientas: todas", "precio": -1, "modelo": Datos.HERRAMIENTAS[nivel]["modelo"]})
	if nivel_bolsa + 1 < Datos.BOLSAS.size():
		var b: Dictionary = Datos.BOLSAS[nivel_bolsa + 1]
		filas.append({"tecla": "R", "nombre": "Bolsa de %d" % int(b["capacidad"]), "precio": int(b["precio"]), "modelo": "bolsa_basura"})
	else:
		filas.append({"tecla": "R", "nombre": "Bolsa: máxima", "precio": -1, "modelo": "bolsa_basura"})
	if nivel_reciclaje + 1 < Datos.RECICLAJE.size():
		var r: Dictionary = Datos.RECICLAJE[nivel_reciclaje + 1]
		filas.append({"tecla": "F", "nombre": "%s (paga x%s)" % [r["nombre"], str(r["multiplicador"])], "precio": int(r["precio"]), "modelo": "contenedor"})
	else:
		filas.append({"tecla": "F", "nombre": "Reciclaje: máximo", "precio": -1, "modelo": "contenedor"})
	filas.append({"tecla": "T", "nombre": "%d semillas" % Datos.PAQUETE_SEMILLAS, "precio": Datos.PRECIO_SEMILLAS, "modelo": "saco_semillas"})
	for f in filas:
		f["puede"] = int(f["precio"]) >= 0 and monedas >= int(f["precio"])
	return filas


func _actualizar_pista() -> void:
	var en_tienda: bool = _cerca_de(tienda, 3.2) and not _junto_a_deposito()
	hud.tienda(en_tienda, _filas_tienda() if en_tienda else [])
	if _junto_a_deposito():
		hud.pista("E: vaciar la bolsa", -1.0)
	elif _cerca_de(tienda, 3.2):
		hud.pista("", -1.0)
	elif _objetivo != null:
		var p: Dictionary = _objetivo
		var d: Dictionary = Datos.PLANTAS[p["tipo"]]
		if nivel < int(d["nivel"]):
			hud.pista("%s · necesitas: %s" % [d["nombre"], Datos.HERRAMIENTAS[int(d["nivel"])]["nombre"]], -1.0)
		else:
			var h: Dictionary = Datos.HERRAMIENTAS[maxi(_en_mano, 0)]
			hud.pista("%s  (%s)" % [d["nombre"], h["nombre"]], float(p["vida"]) / float(d["vida"]))
	elif not _calvas.is_empty() and not _calvas_en(_punto_suelo(), Datos.RADIO_SIEMBRA).is_empty():
		hud.pista("Clic derecho: sembrar césped", -1.0)
	else:
		hud.pista("", -1.0)
