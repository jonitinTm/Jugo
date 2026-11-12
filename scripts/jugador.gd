extends CharacterBody3D
## Jugador en primera persona para recorrer el jardín.
## WASD / flechas: moverse · Ratón: mirar · Shift: correr · Espacio: saltar · Esc: soltar el ratón
## Clic izquierdo: usar la herramienta · E / Q: interactuar (lo gestiona juego.gd)
## La velocidad la fija juego.gd según las botas compradas en la tienda.

@export var velocidad := 3.2
@export var velocidad_correr := 5.0
@export var fuerza_salto := 4.5
@export var sensibilidad := 0.0025

@onready var camara: Camera3D = $Camara

var gravedad: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _mano: Node3D
var _mano_reposo: Vector3 = Vector3.ZERO
var _mano_pos: Vector3 = Vector3.ZERO
var _empuje: bool = false
var _tween_golpe: Tween
var _bolsa: Node3D                  # la bolsa que se ve en la mano izquierda
var _bolsa_modelo: Node3D
var _bolsa_tam: float = 0.0
var _carro: Array = []              # bolsitas apiladas (las de la carretilla)
var _pasos: AudioStreamPlayer
var _distancia_paso: float = 0.0
var _vaiven: float = 0.0


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	_pasos = AudioStreamPlayer.new()
	if ResourceLoader.exists("res://assets/sonidos/paso.wav"):
		_pasos.stream = load("res://assets/sonidos/paso.wav")
	_pasos.volume_db = -14.0
	add_child(_pasos)
	_crear_bolsa()


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

	# pisadas y un poco de vaivén de la mano al andar
	var horizontal := Vector2(velocity.x, velocity.z).length()
	if is_on_floor() and horizontal > 0.5:
		_distancia_paso += horizontal * delta
		_vaiven += horizontal * delta * 2.2
		if _distancia_paso > 1.6:
			_distancia_paso = 0.0
			if _pasos.stream != null:
				_pasos.pitch_scale = randf_range(0.85, 1.15)
				_pasos.play()
	else:
		_vaiven = lerpf(_vaiven, 0.0, delta * 4.0)
	if _mano != null and (_tween_golpe == null or not _tween_golpe.is_running()):
		var amp: float = 0.006 if _empuje else 0.012
		_mano.position = _mano_pos + Vector3(sin(_vaiven) * amp, absf(cos(_vaiven)) * amp, 0.0)
	if _bolsa != null:
		_bolsa.position.y = -0.36 + absf(sin(_vaiven)) * 0.015


## Muestra en la mano el modelo de una herramienta (entrada de Datos.HERRAMIENTAS).
## Las que se empujan (cortacésped) van al cuerpo, no a la cámara: no se inclinan al mirar.
func equipar(herramienta: Dictionary) -> void:
	_empuje = bool(herramienta.get("empuje", false))
	if _mano == null:
		_mano = Node3D.new()
		_mano.name = "Mano"
	var padre: Node3D = self if _empuje else camara
	if _mano.get_parent() != padre:
		if _mano.get_parent() != null:
			_mano.get_parent().remove_child(_mano)
		padre.add_child(_mano)
	for hijo in _mano.get_children():
		hijo.queue_free()
	var escena = load("res://assets/modelos/%s.gltf" % herramienta["modelo"])
	if escena is PackedScene:
		var modelo: Node = (escena as PackedScene).instantiate()
		_mano.add_child(modelo)
		for malla in modelo.find_children("*", "MeshInstance3D", true, false):
			(malla as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var rot: Vector3 = herramienta["rot"]
	_mano_pos = herramienta["pos"]
	if _empuje:
		# la cámara está a 1,6 m: el manillar queda a la altura de las manos
		_mano_pos = Vector3(_mano_pos.x, camara.position.y + _mano_pos.y, _mano_pos.z)
	_mano.position = _mano_pos
	_mano_reposo = Vector3(deg_to_rad(rot.x), deg_to_rad(rot.y), deg_to_rad(rot.z))
	_mano.rotation = _mano_reposo
	_mano.scale = Vector3.ONE * float(herramienta["escala"])
	if _bolsa != null:
		_bolsa.visible = not _empuje


## Animación de golpe de la herramienta (el cortacésped solo tiembla un poco).
func golpe() -> void:
	if _mano == null:
		return
	if _tween_golpe != null:
		_tween_golpe.kill()
	_mano.rotation = _mano_reposo
	_tween_golpe = create_tween()
	if _empuje:
		_tween_golpe.tween_property(_mano, "position", _mano_pos + Vector3(0, 0.01, -0.02), 0.05)
		_tween_golpe.tween_property(_mano, "position", _mano_pos, 0.08)
		return
	_tween_golpe.tween_property(_mano, "rotation:x", _mano_reposo.x - 0.7, 0.08)
	_tween_golpe.tween_property(_mano, "rotation:x", _mano_reposo.x, 0.2)


# ---------------------------------------------------------------- bolsa en la mano
func _crear_bolsa() -> void:
	_bolsa = Node3D.new()
	_bolsa.name = "Bolsa"
	camara.add_child(_bolsa)
	_bolsa.position = Vector3(-0.36, -0.36, -0.55)
	_bolsa.rotation_degrees = Vector3(-8, 25, 6)
	var escena = load("res://assets/modelos/bolsa_basura.gltf")
	if escena is PackedScene:
		_bolsa_modelo = (escena as PackedScene).instantiate()
		_bolsa.add_child(_bolsa_modelo)
		for malla in _bolsa_modelo.find_children("*", "MeshInstance3D", true, false):
			(malla as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mostrar_bolsa(0.0, 0)


## fraccion: lo llena que va la bolsa (0-1) · en_carro: bolsas llenas en la carretilla.
func mostrar_bolsa(fraccion: float, en_carro: int) -> void:
	if _bolsa_modelo == null:
		return
	_bolsa_tam = clampf(fraccion, 0.0, 1.0)
	# vacía es un saco arrugado y plano; llena, una bolsa redonda
	var e: float = 0.16 + 0.14 * _bolsa_tam
	_bolsa_modelo.scale = Vector3(e, 0.18 + 0.12 * _bolsa_tam, e)
	_bolsa_modelo.position = Vector3(0, -0.04 * _bolsa_tam, 0)
	# las bolsas de la carretilla asoman, pequeñitas, detrás
	while _carro.size() < en_carro:
		var escena = load("res://assets/modelos/bolsa_basura.gltf")
		if not (escena is PackedScene):
			break
		var b: Node3D = (escena as PackedScene).instantiate()
		_bolsa.add_child(b)
		var i: int = _carro.size()
		b.position = Vector3(-0.08 - 0.06 * (i % 4), -0.2 + 0.08 * int(i / 4), 0.1 + 0.03 * i)
		b.scale = Vector3.ONE * 0.13
		for malla in b.find_children("*", "MeshInstance3D", true, false):
			(malla as MeshInstance3D).cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_carro.append(b)
	while _carro.size() > en_carro:
		var ultimo: Node3D = _carro.pop_back()
		ultimo.queue_free()


## Saltito de la bolsa cuando le entra algo.
func meter_en_bolsa() -> void:
	if _bolsa_modelo == null:
		return
	var base: Vector3 = _bolsa_modelo.scale
	var t := _bolsa_modelo.create_tween()
	t.tween_property(_bolsa_modelo, "scale", base * Vector3(1.15, 0.9, 1.15), 0.06)
	t.tween_property(_bolsa_modelo, "scale", base, 0.12)
