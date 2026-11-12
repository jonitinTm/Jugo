extends CanvasLayer
## Interfaz del juego hecha con los modelos 3D de assets/modelos.
##
## Los modelos viven en un SubViewport propio (mundo 3D aparte, fondo transparente, cámara
## ortográfica) que se pinta encima del juego con un TextureRect. Así la interfaz nunca se
## mete dentro de las paredes ni recibe la luz o la niebla del jardín.
##
## Unidades: la cámara ve ALTO unidades de arriba abajo; el ancho depende de la ventana.
## Todo mira hacia +Z; los textos van un poco por delante (Z mayor) de los tablones.

const ALTO := 10.0
const PIXEL := 0.005                      # tamaño de un píxel de texto en unidades
const COLOR_TEXTO := Color(1.0, 0.97, 0.88)
const COLOR_BORDE := Color(0.16, 0.09, 0.04)
const COLOR_CARO := Color(1.0, 0.5, 0.42)
const COLOR_ORO := Color(1.0, 0.86, 0.4)

var _vp: SubViewport
var _contadores: Node3D
var _filas: Dictionary = {}               # clave → {"texto": Label3D, "icono": Node3D}
var _moneda: Node3D
var _pista_tablon: Node3D
var _pista_texto: Label3D
var _barra: Node3D
var _barra_relleno: Node3D
var _mensaje: Label3D
var _tiempo_mensaje: float = 0.0
var _tienda: Node3D
var _tienda_filas: Array = []             # [{"icono": Node3D, "nombre": Label3D, "precio": Label3D}]
var _tienda_firma: String = ""


func _ready() -> void:
	_crear_visor()
	_crear_contadores()
	_crear_pista()
	_crear_tienda()
	_crear_mira()
	get_viewport().size_changed.connect(_recolocar)
	_recolocar()


# ---------------------------------------------------------------- construcción
func _crear_visor() -> void:
	_vp = SubViewport.new()
	_vp.own_world_3d = true
	_vp.transparent_bg = true
	_vp.msaa_3d = Viewport.MSAA_4X
	_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(_vp)

	var entorno := Environment.new()
	entorno.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	entorno.ambient_light_color = Color(1.0, 0.98, 0.94)
	entorno.ambient_light_energy = 0.8

	var camara := Camera3D.new()
	camara.projection = Camera3D.PROJECTION_ORTHOGONAL
	camara.size = ALTO
	camara.near = 0.1
	camara.far = 60.0
	camara.position = Vector3(0, 0, 20)
	camara.environment = entorno
	_vp.add_child(camara)
	camara.current = true

	var luz := DirectionalLight3D.new()
	luz.rotation_degrees = Vector3(-35, 25, 0)
	luz.light_energy = 1.1
	_vp.add_child(luz)

	var lienzo := TextureRect.new()
	lienzo.texture = _vp.get_texture()
	lienzo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	lienzo.stretch_mode = TextureRect.STRETCH_SCALE
	lienzo.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	lienzo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(lienzo)


func _crear_contadores() -> void:
	_contadores = Node3D.new()
	_vp.add_child(_contadores)
	var datos := [
		["monedas", "moneda", Vector3.ZERO, 56, COLOR_ORO],
		["bolsa", "bolsa_basura", Vector3(0, -20, 0), 44, COLOR_TEXTO],
		["contenedor", "contenedor", Vector3(12, -30, 0), 44, COLOR_TEXTO],
		["semillas", "saco_semillas", Vector3(8, -20, 0), 44, COLOR_TEXTO],
		["jardin", "icono_hoja", Vector3.ZERO, 30, COLOR_TEXTO],
	]
	for i in range(datos.size()):
		var d: Array = datos[i]
		var y: float = -0.84 * i
		var ancho: float = 2.05 if i == 4 else 1.55
		var tablon := _modelo("boton_madera")
		tablon.scale = Vector3(ancho, 1.25, 1.0)
		tablon.position = Vector3(0.8 * ancho, y, -0.6)
		_contadores.add_child(tablon)
		var icono := _icono(d[1], 0.56, d[2])
		icono.position = Vector3(0.38, y, 0.2)
		_contadores.add_child(icono)
		var texto := _texto(d[3], HORIZONTAL_ALIGNMENT_LEFT)
		texto.modulate = d[4]
		texto.position = Vector3(0.82, y, 0.6)
		_contadores.add_child(texto)
		_filas[d[0]] = {"texto": texto, "icono": icono}
	_moneda = _filas["monedas"]["icono"]


func _crear_pista() -> void:
	_pista_tablon = _modelo("boton_madera")
	_pista_tablon.scale = Vector3(3.6, 1.2, 1.0)
	_pista_tablon.position = Vector3(0, -4.2, -0.6)
	_pista_tablon.visible = false
	_vp.add_child(_pista_tablon)
	_pista_texto = _texto(40, HORIZONTAL_ALIGNMENT_CENTER)
	_pista_texto.position = Vector3(0, -4.2, 0.6)
	_vp.add_child(_pista_texto)

	_barra = _modelo("barra_progreso")
	_barra.scale = Vector3.ONE * 0.75
	_barra.position = Vector3(0, -3.45, 0)
	_barra.visible = false
	_vp.add_child(_barra)
	var relleno := _barra.find_child("relleno", true, false)
	if relleno is Node3D:
		_barra_relleno = relleno as Node3D

	_mensaje = _texto(60, HORIZONTAL_ALIGNMENT_CENTER)
	_mensaje.position = Vector3(0, 3.1, 0.6)
	_mensaje.visible = false
	_vp.add_child(_mensaje)


func _crear_tienda() -> void:
	_tienda = Node3D.new()
	_tienda.visible = false
	_vp.add_child(_tienda)
	var panel := _modelo("panel_madera")
	panel.scale = Vector3(2.1, 2.1, 1.0)
	panel.position = Vector3(0, 0, -0.6)
	_tienda.add_child(panel)
	var titulo := _texto(60, HORIZONTAL_ALIGNMENT_CENTER)
	titulo.text = "TIENDA"
	titulo.modulate = COLOR_ORO
	titulo.position = Vector3(0, 1.62, 0.6)
	_tienda.add_child(titulo)
	for i in range(4):
		var y: float = 0.78 - 0.8 * i
		var nombre := _texto(34, HORIZONTAL_ALIGNMENT_LEFT)
		nombre.position = Vector3(-2.05, y, 0.6)
		_tienda.add_child(nombre)
		var precio := _texto(40, HORIZONTAL_ALIGNMENT_RIGHT)
		precio.position = Vector3(2.35, y, 0.6)
		_tienda.add_child(precio)
		var moneda := _icono("moneda", 0.36, Vector3(0, 25, 0))
		moneda.position = Vector3(2.68, y, 0.3)
		_tienda.add_child(moneda)
		_tienda_filas.append({"icono": null, "nombre": nombre, "precio": precio, "moneda": moneda, "y": y})


func _crear_mira() -> void:
	var mira := ColorRect.new()
	mira.color = Color(1, 1, 1, 0.85)
	mira.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	mira.offset_left = -3
	mira.offset_top = -3
	mira.offset_right = 3
	mira.offset_bottom = 3
	mira.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(mira)


## Ajusta el visor a la ventana y pega los contadores a la izquierda y la tienda a la derecha.
func _recolocar() -> void:
	var ventana: Vector2 = get_viewport().get_visible_rect().size
	var ancho: int = maxi(int(ventana.x), 64)
	var alto: int = maxi(int(ventana.y), 64)
	_vp.size = Vector2i(ancho, alto)
	var medio_ancho: float = ALTO * 0.5 * float(ancho) / float(alto)
	_contadores.position = Vector3(-medio_ancho + 0.25, ALTO * 0.5 - 0.6, 0)
	_tienda.position = Vector3(medio_ancho - 3.5, 0.3, 0)


# ---------------------------------------------------------------- piezas
func _modelo(nombre: String) -> Node3D:
	var recurso = load("res://assets/modelos/%s.gltf" % nombre)
	if recurso is PackedScene:
		var nodo = (recurso as PackedScene).instantiate()
		if nodo is Node3D:
			return nodo
	return Node3D.new()


## Transformación de `nodo` respecto a `raiz` (sin contar la de `raiz`).
func _relativa(nodo: Node3D, raiz: Node3D) -> Transform3D:
	var t := Transform3D.IDENTITY
	var n: Node = nodo
	while n != null and n != raiz:
		if n is Node3D:
			t = (n as Node3D).transform * t
		n = n.get_parent()
	return t


## Modelo centrado y escalado para que quepa en un cubo de lado `tam`; `giro` en grados.
func _icono(nombre: String, tam: float, giro: Vector3 = Vector3.ZERO) -> Node3D:
	var soporte := Node3D.new()
	var nodo := _modelo(nombre)
	soporte.add_child(nodo)
	var caja := AABB()
	var primera := true
	for malla in nodo.find_children("*", "MeshInstance3D", true, false):
		var mi: MeshInstance3D = malla
		var a: AABB = _relativa(mi, nodo) * mi.get_aabb()
		if primera:
			caja = a
			primera = false
		else:
			caja = caja.merge(a)
	var lado: float = maxf(caja.size.x, maxf(caja.size.y, caja.size.z))
	if lado > 0.0001:
		var e: float = tam / lado
		nodo.scale = Vector3.ONE * e
		nodo.position = -caja.get_center() * e
	soporte.rotation_degrees = giro
	return soporte


func _texto(tamano: int, alineacion: HorizontalAlignment) -> Label3D:
	var t := Label3D.new()
	t.font_size = tamano
	t.pixel_size = PIXEL
	t.outline_size = 12
	t.modulate = COLOR_TEXTO
	t.outline_modulate = COLOR_BORDE
	t.horizontal_alignment = alineacion
	t.shaded = false
	return t


# ---------------------------------------------------------------- animación
func _process(delta: float) -> void:
	if _moneda != null:
		_moneda.rotate_y(delta * 2.2)
	for fila in _tienda_filas:
		var icono = fila["icono"]
		if icono is Node3D and _tienda.visible:
			(icono as Node3D).rotate_y(delta * 0.9)
	if _tiempo_mensaje > 0.0:
		_tiempo_mensaje -= delta
		if _tiempo_mensaje <= 0.0:
			_mensaje.visible = false


func _saltito(nodo: Node3D) -> void:
	var t := nodo.create_tween()
	t.tween_property(nodo, "scale", Vector3.ONE * 1.35, 0.08)
	t.tween_property(nodo, "scale", Vector3.ONE, 0.18)


# ---------------------------------------------------------------- lo que usa juego.gd
## textos: diccionario clave → texto (monedas, bolsa, contenedor, semillas, jardin)
func actualizar(textos: Dictionary) -> void:
	for clave in textos:
		if not _filas.has(clave):
			continue
		var etiqueta: Label3D = _filas[clave]["texto"]
		var nuevo: String = String(textos[clave])
		if etiqueta.text != nuevo:
			if etiqueta.text != "":
				_saltito(_filas[clave]["icono"])
			etiqueta.text = nuevo


## Texto bajo la mira. vida entre 0 y 1 muestra la barra; negativo la oculta.
func pista(texto: String, vida: float) -> void:
	_pista_texto.text = texto
	_pista_tablon.visible = texto != ""
	_barra.visible = vida >= 0.0
	if vida >= 0.0 and _barra_relleno != null:
		_barra_relleno.scale.x = clampf(vida, 0.001, 1.0)


func mensaje(texto: String, segundos: float = 2.5) -> void:
	_mensaje.text = texto
	_mensaje.visible = true
	_tiempo_mensaje = segundos


## Panel de la tienda. filas: [{tecla, nombre, precio (-1 = agotado), modelo, puede}]
func tienda(mostrar: bool, filas: Array) -> void:
	_tienda.visible = mostrar
	if not mostrar:
		return
	var firma := str(filas)
	if firma == _tienda_firma:
		return
	_tienda_firma = firma
	for i in range(_tienda_filas.size()):
		var hueco: Dictionary = _tienda_filas[i]
		var nombre: Label3D = hueco["nombre"]
		var precio: Label3D = hueco["precio"]
		var moneda: Node3D = hueco["moneda"]
		var viejo = hueco["icono"]
		if viejo is Node3D:
			(viejo as Node3D).queue_free()
			hueco["icono"] = null
		if i >= filas.size():
			nombre.text = ""
			precio.text = ""
			moneda.visible = false
			continue
		var f: Dictionary = filas[i]
		var agotado: bool = int(f["precio"]) < 0
		var color: Color = COLOR_TEXTO if (f["puede"] or agotado) else COLOR_CARO
		nombre.text = "[%s]  %s" % [f["tecla"], f["nombre"]]
		nombre.modulate = color
		precio.text = "" if agotado else str(int(f["precio"]))
		precio.modulate = COLOR_ORO if f["puede"] else COLOR_CARO
		moneda.visible = not agotado
		var icono := _icono(String(f["modelo"]), 0.62, Vector3(12, -30, 0))
		icono.position = Vector3(-2.55, float(hueco["y"]), 0.2)
		_tienda.add_child(icono)
		hueco["icono"] = icono
