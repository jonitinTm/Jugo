extends SceneTree
## Capturas del juego tal y como lo pinta Godot (luz, cielo y sombras reales del juego).
##   godot --path . -s herramientas_dev/captura_godot.gd -- [carpeta_salida]
## Abre la escena principal, coloca una cámara en varios puntos y guarda un JPG de cada uno.

const VISTAS := [
	# nombre, posición, punto al que mira
	["juego_entrada", Vector3(1.6, 1.65, 9.5), Vector3(1.0, 1.0, 0.0)],
	["juego_jardin", Vector3(-6.0, 2.2, 8.0), Vector3(2.0, 0.6, -2.0)],
	["juego_cerca", Vector3(4.5, 1.2, 6.0), Vector3(6.5, 0.4, 2.0)],
	["juego_aerea", Vector3(18.0, 22.0, 26.0), Vector3(-2.0, 0.0, -6.0)],
	["juego_calle", Vector3(-4.0, 2.0, 18.0), Vector3(6.0, 1.0, 14.0)],
]

var _salida := "res://docs/previews/godot"
var _escena: Node
var _cam: Camera3D
var _i := -1
var _espera := 0


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		_salida = args[0]
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(_salida) if _salida.begins_with("res://") else _salida)
	root.size = Vector2i(1600, 900)
	_escena = load("res://escenas/principal.tscn").instantiate()
	root.add_child(_escena)
	_cam = Camera3D.new()
	_cam.fov = 70.0
	root.add_child(_cam)
	_espera = 90


func _process(_delta: float) -> bool:
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	if _espera > 0:
		_espera -= 1
		return false
	if _i >= 0:
		var img := root.get_texture().get_image()
		var ruta: String = _salida.path_join(VISTAS[_i][0] + ".jpg")
		img.save_jpg(ruta if not ruta.begins_with("res://") else ProjectSettings.globalize_path(ruta), 0.9)
		print("captura ", ruta)
	_i += 1
	if _i >= VISTAS.size():
		return true
	_cam.global_position = VISTAS[_i][1]
	_cam.look_at(VISTAS[_i][2], Vector3.UP)
	_cam.make_current()
	_espera = 20
	return false
