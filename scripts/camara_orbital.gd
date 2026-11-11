extends Camera3D
## Cámara orbital sencilla para la galería de modelos.
## Clic derecho + arrastrar: girar · Rueda: zoom · WASD/QE: mover el objetivo · Shift: más rápido

@export var objetivo := Vector3.ZERO
@export var distancia := 15.0
@export var yaw := -30.0
@export var pitch := -25.0
@export var velocidad := 12.0

func _ready() -> void:
	_actualizar()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		yaw -= event.relative.x * 0.3
		pitch = clamp(pitch - event.relative.y * 0.3, -85.0, 10.0)
	elif event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			distancia = max(1.0, distancia * 0.9)
		elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distancia = min(200.0, distancia * 1.1)

func _process(delta: float) -> void:
	var dir := Vector3.ZERO
	if Input.is_physical_key_pressed(KEY_W): dir.z -= 1
	if Input.is_physical_key_pressed(KEY_S): dir.z += 1
	if Input.is_physical_key_pressed(KEY_A): dir.x -= 1
	if Input.is_physical_key_pressed(KEY_D): dir.x += 1
	if Input.is_physical_key_pressed(KEY_E): dir.y += 1
	if Input.is_physical_key_pressed(KEY_Q): dir.y -= 1
	var v := velocidad * (3.0 if Input.is_physical_key_pressed(KEY_SHIFT) else 1.0)
	objetivo += Basis(Vector3.UP, deg_to_rad(yaw)) * dir * v * delta
	_actualizar()

func _actualizar() -> void:
	var b := Basis.from_euler(Vector3(deg_to_rad(pitch), deg_to_rad(yaw), 0.0))
	global_position = objetivo + b * Vector3(0, 0, distancia)
	look_at(objetivo)
