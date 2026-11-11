extends CanvasLayer
## Interfaz mínima creada por código: contadores, mira, pista de interacción y mensajes.

var _etiquetas: Dictionary = {}
var _pista: Label
var _barra: ProgressBar
var _mensaje: Label
var _tiempo_mensaje: float = 0.0


func _ready() -> void:
	var raiz := Control.new()
	raiz.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	raiz.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(raiz)

	var contadores := VBoxContainer.new()
	contadores.position = Vector2(24, 20)
	contadores.mouse_filter = Control.MOUSE_FILTER_IGNORE
	raiz.add_child(contadores)
	for clave in ["monedas", "bolsa", "contenedor", "herramienta", "jardin"]:
		var e := _etiqueta(26 if clave == "monedas" else 20)
		if clave == "monedas":
			e.add_theme_color_override("font_color", Color(1.0, 0.85, 0.35))
		contadores.add_child(e)
		_etiquetas[clave] = e

	var mira := ColorRect.new()
	mira.color = Color(1, 1, 1, 0.85)
	mira.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	mira.offset_left = -3
	mira.offset_top = -3
	mira.offset_right = 3
	mira.offset_bottom = 3
	mira.mouse_filter = Control.MOUSE_FILTER_IGNORE
	raiz.add_child(mira)

	var abajo := VBoxContainer.new()
	abajo.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	abajo.offset_top = -150
	abajo.offset_bottom = -50
	abajo.alignment = BoxContainer.ALIGNMENT_END
	abajo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	raiz.add_child(abajo)
	_pista = _etiqueta(24)
	_pista.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	abajo.add_child(_pista)
	_barra = ProgressBar.new()
	_barra.custom_minimum_size = Vector2(320, 14)
	_barra.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	_barra.show_percentage = false
	_barra.max_value = 1.0
	_barra.step = 0.001
	_barra.visible = false
	_barra.mouse_filter = Control.MOUSE_FILTER_IGNORE
	abajo.add_child(_barra)

	_mensaje = _etiqueta(30)
	_mensaje.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	_mensaje.offset_top = 110
	_mensaje.offset_bottom = 160
	_mensaje.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_mensaje.visible = false
	raiz.add_child(_mensaje)


func _etiqueta(tamano: int) -> Label:
	var e := Label.new()
	e.add_theme_font_size_override("font_size", tamano)
	e.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.85))
	e.add_theme_constant_override("outline_size", 6)
	e.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return e


func _process(delta: float) -> void:
	if _tiempo_mensaje > 0.0:
		_tiempo_mensaje -= delta
		if _tiempo_mensaje <= 0.0:
			_mensaje.visible = false


## textos: diccionario clave → texto (monedas, bolsa, contenedor, herramienta, jardin)
func actualizar(textos: Dictionary) -> void:
	for clave in textos:
		if _etiquetas.has(clave):
			(_etiquetas[clave] as Label).text = String(textos[clave])


## Texto bajo la mira. vida entre 0 y 1 muestra la barra; negativo la oculta.
func pista(texto: String, vida: float) -> void:
	_pista.text = texto
	_barra.visible = vida >= 0.0
	if vida >= 0.0:
		_barra.value = vida


func mensaje(texto: String, segundos: float = 2.5) -> void:
	_mensaje.text = texto
	_mensaje.visible = true
	_tiempo_mensaje = segundos
