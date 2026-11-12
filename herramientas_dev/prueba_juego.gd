extends SceneTree
## Prueba automática del bucle del juego:
##   godot --path . -s herramientas_dev/prueba_juego.gd -- [carpeta_capturas]
## OJO: guarda en user://partida.json como el juego. Para no pisar tu partida, ejecútala en una
## copia del proyecto con otro config/name en project.godot.
## Compra mejoras, arranca plantas, llena la bolsa y la carretilla, deja y recoge una bolsa,
## siega con el cortacésped, vacía en el contenedor y espera al camión y al basurero.
## Escribe "OK ..." / "FALLO ..." por cada comprobación y guarda capturas de momentos clave.

var _salida := ""
var _juego: Node
var _fallos := 0


func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	_salida = args[0] if args.size() > 0 else OS.get_user_data_dir()
	DirAccess.make_dir_recursive_absolute(_salida)
	root.size = Vector2i(1280, 720)
	_juego = load("res://escenas/principal.tscn").instantiate()
	root.add_child(_juego)
	_correr.call_deferred()
	# por si algo se cuelga: la prueba nunca dura más de 2 minutos
	create_timer(120.0).timeout.connect(func() -> void:
		print("RESULTADO: SE HA COLGADO")
		quit(2))


func _comprobar(cond: bool, que: String) -> void:
	if cond:
		print("OK     ", que)
	else:
		_fallos += 1
		print("FALLO  ", que)


func _esperar(seg: float) -> void:
	await create_timer(seg).timeout


func _captura(nombre: String) -> void:
	await process_frame
	await process_frame
	var img := root.get_texture().get_image()
	img.save_jpg(_salida.path_join(nombre + ".jpg"), 0.88)
	print("captura ", nombre)


func _mirar(desde: Vector3, hacia: Vector3) -> void:
	var j: CharacterBody3D = _juego.jugador
	j.global_position = desde
	var d := hacia - desde
	j.rotation.y = atan2(-d.x, -d.z)
	j.camara.rotation.x = atan2(d.y - 1.6, Vector2(d.x, d.z).length())


func _plantas_cerca(pos: Vector3, radio: float, tipo: String = "") -> Array:
	var res: Array = []
	for p in _juego._plantas:
		var n: Node3D = p["nodo"]
		if is_instance_valid(n) and (tipo == "" or p["tipo"] == tipo) and _juego.zonas_abiertas[p["zona"]] \
				and Vector2(n.global_position.x - pos.x, n.global_position.z - pos.z).length() < radio:
			res.append(p)
	return res


func _correr() -> void:
	await _esperar(1.5)
	var j: CharacterBody3D = _juego.jugador
	_comprobar(_juego.has_method("_comprar_fila"), "juego.gd compila y está en marcha")
	_comprobar(absf(j.velocidad - 3.2) < 0.01, "velocidad de partida 3,2 m/s (%.2f)" % j.velocidad)
	await _captura("01_inicio")

	# --- arrancar plantas con las manos: vuelan a la bolsa
	var cerca := _plantas_cerca(j.global_position, 12.0, "hierbajo")
	_comprobar(cerca.size() >= 5, "hay hierbajos cerca del inicio (%d)" % cerca.size())
	var p0: Dictionary = cerca[0]
	_mirar(p0["nodo"].global_position + Vector3(1.5, 0, 1.5), p0["centro"])
	await _esperar(0.3)
	for i in range(5):
		_juego._danar_planta(cerca[i], 999.0)
	await _esperar(0.15)
	await _captura("02_plantas_volando")
	await _esperar(0.6)
	_comprobar(_juego.bolsa_volumen == 5, "5 hierbajos en la bolsa (%d)" % _juego.bolsa_volumen)

	# --- tienda: dinero de prueba y compras con 1-9
	_juego.monedas = 20000
	var tienda: Node3D = _juego.tienda
	_mirar(tienda.global_position + Vector3(0.5, 0, 2.2), tienda.global_position + Vector3.UP * 1.5)
	await _esperar(0.4)
	await _captura("03_tienda")
	_juego._comprar_fila(2)   # carretilla
	_juego._comprar_fila(3)   # botas
	_juego._comprar_fila(4)   # ritmo
	_juego._comprar_fila(5)   # alcance
	_comprobar(_juego.nivel_carretilla == 1, "carretilla comprada")
	_comprobar(j.velocidad > 3.5, "las botas suben la velocidad (%.2f m/s)" % j.velocidad)
	_comprobar(_juego._ritmo() < 1.0, "el ritmo acorta la cadencia (x%.2f)" % _juego._ritmo())
	_comprobar(_juego._alcance() > 2.6, "el alcance sube (%.1f m)" % _juego._alcance())
	for i in range(5):
		_juego._comprar_fila(0)   # herramientas hasta el cortacésped
	_comprobar(String(_juego.Datos.HERRAMIENTAS[_juego.nivel]["nombre"]) == "Cortacésped", "herramientas compradas hasta el cortacésped")
	await _esperar(0.2)
	await _captura("04_tienda_comprada")

	# --- llenar la bolsa: la llena pasa sola a la carretilla
	var cap: int = _juego._capacidad_bolsa()
	_juego.bolsa_volumen = cap - 1
	var mas := _plantas_cerca(j.global_position, 30.0, "hierbajo")
	_juego._danar_planta(mas[0], 999.0)
	_comprobar(_juego.carro.size() == 1 and _juego.bolsa_volumen == 0, "bolsa llena → carretilla (%d en carro)" % _juego.carro.size())

	# --- dejar una bolsa en el suelo y recogerla
	_juego.bolsa_volumen = 7
	_juego.bolsa_valor = 7
	_juego._soltar_bolsa()
	_comprobar(_juego._bolsas_suelo.size() == 1 and _juego.bolsa_volumen == 0, "Q deja la bolsa en el suelo")
	await _esperar(0.5)
	var b: Dictionary = _juego._bolsas_suelo[0]
	var pb: Vector3 = (b["nodo"] as Node3D).global_position
	_mirar(pb + Vector3(1.2, 0, 1.2), pb)
	await _esperar(0.3)
	await _captura("05_bolsa_en_el_suelo")
	_comprobar(_juego._bolsa_cercana() != null, "E coge la bolsa cuando estás al lado")
	if _juego._bolsa_cercana() != null:
		_juego._coger_bolsa(_juego._bolsa_cercana())
	_comprobar(_juego._bolsas_suelo.is_empty() and _juego.bolsa_volumen == 7, "bolsa recogida (%d)" % _juego.bolsa_volumen)

	# --- cortacésped: siega lo que tiene delante sin apuntar
	var hierba := _plantas_cerca(Vector3(0, 0, 14), 9.0)
	var objetivo: Dictionary = {}
	for p in hierba:
		if String(_juego.Datos.PLANTAS[p["tipo"]]["clase"]) == "hierba":
			objetivo = p
			break
	_comprobar(not objetivo.is_empty(), "hay hierba para segar")
	if not objetivo.is_empty():
		var pos: Vector3 = (objetivo["nodo"] as Node3D).global_position
		_mirar(pos + Vector3(0, 0, 0.9), pos + Vector3(0, -0.4, -2.0))
		_juego._equipar(5)
		await _esperar(0.3)
		var mano: Node3D = j._mano
		_comprobar(mano.get_parent() == j and mano.get_child_count() > 0,
			"el cortacésped va en el cuerpo (%s, en mano: %d, %s)" % [mano.get_parent().name, _juego._en_mano, str(mano.global_position)])
		await _captura("06_cortacesped")
		var antes: int = _juego._plantas.size()
		_juego.bolsa_volumen = 0
		for i in range(8):
			_juego._segar(_juego.Datos.HERRAMIENTAS[5])
		await _esperar(0.6)
		_comprobar(_juego._plantas.size() < antes, "el cortacésped siega (%d plantas)" % (antes - _juego._plantas.size()))

	# --- contenedor lleno: viene el camión, baja el basurero, vacía y paga
	_juego.contenedor_volumen = _juego._capacidad_contenedor() - 2
	_juego.contenedor_valor = 300
	_juego.bolsa_volumen = 5
	_juego.bolsa_valor = 40
	var cont: Node3D = _juego.contenedor
	_mirar(cont.global_position + Vector3(-1.0, 0, -2.6), cont.global_position + Vector3(0, 0.8, 0))
	await _esperar(0.3)
	var dinero: int = _juego.monedas
	_juego._vaciar_bolsa()
	await _esperar(0.25)
	await _captura("07_bolsas_al_contenedor")
	# desde la acera, para ver llegar el camión y al basurero
	_mirar(Vector3(1.0, 0.05, 31.5), Vector3(8.5, 1.2, 25.5))
	_juego.vida = 9999.0
	_comprobar(_juego._camion_ocupado, "con el contenedor lleno se llama al camión")
	await _esperar(4.6)
	await _captura("08_llega_el_camion")
	await _esperar(2.4)
	await _captura("09_baja_el_basurero")
	await _esperar(1.3)
	await _captura("10_vacia_el_contenedor")
	await _esperar(4.5)
	_comprobar(_juego.monedas > dinero, "el basurero paga (%d → %d)" % [dinero, _juego.monedas])
	_comprobar(_juego.contenedor_volumen == 0, "contenedor vacío")
	await _captura("11_se_va")
	await _esperar(7.0)
	_comprobar(not _juego._camion_ocupado, "el camión se ha ido")
	print("RESULTADO: %s (%d fallos)" % ["TODO BIEN" if _fallos == 0 else "HAY FALLOS", _fallos])
	quit(1 if _fallos > 0 else 0)
