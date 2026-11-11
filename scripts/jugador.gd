extends CharacterBody3D
## Jugador en primera persona para recorrer el jardín.
## WASD / flechas: moverse · Ratón: mirar · Shift: correr · Espacio: saltar · Esc: soltar el ratón
## Clic izquierdo: usar la herramienta · E: interactuar (lo gestiona juego.gd)

@export var velocidad := 4.0
@export var velocidad_correr := 7.5
@export var fuerza_salto := 4.5
@export var sensibilidad := 0.0025

@onready var camara: Camera3D = $Camara

var gravedad: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _mano: Node3D
var _mano_reposo: Vector3 = Vector3.ZERO
var _tween_golpe: Tween


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _unhandled_input(event: InputEvent) -> void:
	var capturado := Input.mouse_mode == Input.MOUSE_MODE_CAPTURED
	if event is InputEventMouseMotion and capturado:
		rotate_y(-event.relative.x * sensibilidad)
		camara.rotation.x = clamp(camara.rotation.x - event.relative.y * sensibilidad, -1.4, 1.4)
	elif event is InputEventKey and event.pressed and event.keycode == KEY_ESCAPE:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE if capturado else Input.MOUSE_MODE_CAPTURED
	elif event is InputEventMouseButton and event.pressed and not capturado:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= gravedad * delta
	elif Input.is_physical_key_pressed(KEY_SPACE):
		velocity.y = fuerza_salto

	var entrada := Vector3.ZERO
	if Input.is_physical_key_pressed(KEY_W) or Input.is_physical_key_pressed(KEY_UP):
		entrada.z -= 1.0
	if Input.is_physical_key_pressed(KEY_S) or Input.is_physical_key_pressed(KEY_DOWN):
		entrada.z += 1.0
	if Input.is_physical_key_pressed(KEY_A) or Input.is_physical_key_pressed(KEY_LEFT):
		entrada.x -= 1.0
	if Input.is_physical_key_pressed(KEY_D) or Input.is_physical_key_pressed(KEY_RIGHT):
		entrada.x += 1.0

	var direccion := transform.basis * entrada
	direccion.y = 0.0
	direccion = direccion.normalized()
	var v := velocidad_correr if Input.is_physical_key_pressed(KEY_SHIFT) else velocidad
	velocity.x = direccion.x * v
	velocity.z = direccion.z * v
	move_and_slide()


## Muestra en la mano el modelo de una herramienta (entrada de Datos.HERRAMIENTAS).
func equipar(herramienta: Dictionary) -> void:
	if _mano == null:
		_mano = Node3D.new()
		_mano.name = "Mano"
		camara.add_child(_mano)
	for hijo in _mano.get_children():
		hijo.queue_free()
	var escena = load("res://assets/modelos/%s.gltf" % herramienta["modelo"])
	if escena is PackedScene:
		var modelo: Node = (escena as PackedScene).instantiate()
		_mano.add_child(modelo)
		for malla in modelo.find_children("*", "MeshInstance3D", true, false):
			(malla as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var rot: Vector3 = herramienta["rot"]
	_mano.position = herramienta["pos"]
	_mano_reposo = Vector3(deg_to_rad(rot.x), deg_to_rad(rot.y), deg_to_rad(rot.z))
	_mano.rotation = _mano_reposo
	_mano.scale = Vector3.ONE * float(herramienta["escala"])


## Animación de golpe de la herramienta.
func golpe() -> void:
	if _mano == null:
		return
	if _tween_golpe != null:
		_tween_golpe.kill()
	_mano.rotation = _mano_reposo
	_tween_golpe = create_tween()
	_tween_golpe.tween_property(_mano, "rotation:x", _mano_reposo.x - 0.7, 0.08)
	_tween_golpe.tween_property(_mano, "rotation:x", _mano_reposo.x, 0.2)
