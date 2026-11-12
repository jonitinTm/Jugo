#!/usr/bin/env python3
"""
Economía de "Jugo": tablas de equilibrio + simulador + generador de scripts/datos.gd.

    python3 herramientas_dev/economia.py            # simula una partida y escribe datos.gd
    python3 herramientas_dev/economia.py --solo-simular

Este archivo es la ÚNICA fuente de los números del juego: cambia aquí precios, daños,
vidas o capacidades, mira en la simulación cómo queda el ritmo y se regenera datos.gd.

Modelo de la economía
---------------------
Ingresos:
  - Cada planta tiene un VALOR. Al quitarla va a la bolsa; la bolsa se vacía en el
    contenedor y el camión paga  valor x multiplicador de reciclaje.
  - Cada calva de tierra sembrada da PREMIO_CESPED al terminar de crecer.
Gastos (todo en la tienda):
  - Herramientas (7 niveles): desbloquean plantas más duras y limpian más rápido.
  - Bolsa (4 niveles): menos viajes al cubo.
  - Reciclaje (4 niveles): contenedor más grande y el camión paga más (multiplicador).
  - Semillas: paquetes para sembrar césped.
Ritmo buscado: una mejora cada pocos minutos, la primera en menos de un minuto, y el
jardín completo en torno a 45-60 minutos.
"""
import math
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ------------------------------------------------------------------ tablas
ALCANCE = 2.6
SEMILLAS_INICIALES = 15
PAQUETE_SEMILLAS = 30
PRECIO_SEMILLAS = 10
RADIO_SIEMBRA = 2.2
TIEMPO_CRECER = 12.0
PREMIO_CESPED = 1                  # se multiplica por el "valor" de la zona
REBROTE_MIN = 300.0
REBROTE_MAX = 480.0

# Jugador
VIDA_JUGADOR = 100
REGENERACION = 6.0                 # vida por segundo...
ESPERA_REGENERACION = 4.0          # ...tras estos segundos sin recibir daño

# Afilado: mejora repetible, cada nivel multiplica el daño de todas las herramientas
AFILADO_DANO = 1.2
AFILADO_PRECIO = 25
AFILADO_FACTOR = 1.35              # cada nivel cuesta esto más que el anterior
AFILADO_MAX = 24

# Meta final: se compra en la tienda cuando ya tienes todas las herramientas
TROFEO_NOMBRE = "Trofeo: Jardín del año"
TROFEO_PRECIO = 620000

# Zonas del mapa, en orden de desbloqueo. rect = (x0, z0, x1, z1).
#   vida / valor / dano: multiplicadores de la vida de plantas y bichos, de lo que valen y
#   del daño que hacen los bichos.   puerta = (x, z, giro): puerta que da acceso.
#   contenido: cuántos de cada cosa coloca generar_escena.py.
ZONAS = [
    dict(id="delantero", nombre="Jardín delantero", rect=(-15, 1, 15, 23), precio=0, vida=1, valor=1, dano=1.0, puerta=None,
         contenido=dict(arbol_otono=1, roca=3, matorral=8, girasol_gigante=8, amapola_gigante=8, monton_hojas=3,
                        hierbajo_grande=30, hierbajo=200, caracol=4)),
    dict(id="patio", nombre="Patio trasero", rect=(-15, -11, 15, 1), precio=400, vida=2, valor=2.5, dano=1.3, puerta=(-9.5, 1, 0),
         contenido=dict(arbol_gigante=2, tocon=2, roca=3, seta_gigante=3, zarza=8, matorral=14, girasol_gigante=5,
                        amapola_gigante=5, hierbajo_grande=40, hierbajo=110, caracol=3, escarabajo=4)),
    dict(id="huerto", nombre="Huerto abandonado", rect=(15, -11, 45, 23), precio=1900, vida=4, valor=6, dano=1.6, puerta=(15, 12, 90),
         contenido=dict(arbol_otono=2, arbol_gigante=1, tocon=3, roca=6, seta_gigante=6, zarza=16, matorral=30,
                        girasol_gigante=25, amapola_gigante=20, monton_hojas=4, hierbajo_grande=90, hierbajo=260,
                        caracol=4, escarabajo=8, avispa=3)),
    dict(id="arboleda", nombre="Arboleda", rect=(-15, -45, 45, -11), precio=13000, vida=8, valor=14, dano=2.0, puerta=(0, -11, 0),
         contenido=dict(arbol_gigante=9, arbol_otono=5, tocon=10, roca=12, seta_gigante=24, zarza=30, matorral=50,
                        amapola_gigante=15, monton_hojas=8, hierbajo_grande=120, hierbajo=300, escarabajo=10, avispa=8)),
    dict(id="zarzal", nombre="El Zarzal", rect=(-50, -45, -15, 23), precio=80000, vida=16, valor=32, dano=2.5, puerta=(-15, -28, 90),
         contenido=dict(arbol_gigante=7, arbol_otono=3, tocon=8, roca=12, seta_gigante=15, zarza=90, matorral=60,
                        girasol_gigante=15, hierbajo_grande=140, hierbajo=280, caracol=6, escarabajo=12, avispa=14)),
]

# usos: clase -> (daño por golpe, radio de área). La clase "bicho" es el daño contra bichos.
HERRAMIENTAS = [
    dict(nombre="Manos", modelo="guantes", precio=0, cadencia=0.35,
         usos={"hierba": (1, 0), "hojas": (1, 0)},
         pos=(0.0, -0.32, -0.55), rot=(-35, 0, 0), escala=1.6),
    dict(nombre="Rastrillo", modelo="rastrillo", precio=12, cadencia=0.35,
         usos={"hojas": (3, 1.8), "hierba": (1, 1.0), "bicho": (1, 0)},
         pos=(0.32, -0.3, -0.25), rot=(78, 0, 0), escala=1.0),
    dict(nombre="Hoz", modelo="hoz", precio=60, cadencia=0.35,
         usos={"hierba": (2, 1.4), "bicho": (2, 0)},
         pos=(0.32, -0.3, -0.5), rot=(-40, 20, 0), escala=1.3),
    dict(nombre="Tijeras de podar", modelo="tijeras_podar", precio=200, cadencia=0.3,
         usos={"lenoso": (4, 0), "bicho": (3, 0)},
         pos=(0.3, -0.45, -0.45), rot=(-50, 0, 0), escala=1.1),
    dict(nombre="Machete", modelo="machete", precio=1000, cadencia=0.3,
         usos={"lenoso": (7, 1.0), "hierba": (4, 1.6), "bicho": (6, 1.2)},
         pos=(0.32, -0.28, -0.5), rot=(-45, 0, -10), escala=1.3),
    dict(nombre="Desbrozadora", modelo="desbrozadora", precio=9000, cadencia=0.15,
         usos={"hierba": (4, 2.4), "lenoso": (4, 1.6), "hojas": (2, 2.4), "bicho": (3, 2.0)},
         pos=(0.3, -0.25, -0.35), rot=(70, 0, 0), escala=1.0),
    dict(nombre="Motosierra", modelo="motosierra", precio=60000, cadencia=0.15,
         usos={"tronco": (8, 0), "lenoso": (8, 0), "bicho": (8, 0)},
         pos=(0.3, -0.38, -0.45), rot=(0, 180, 0), escala=1.2),
]

BOLSAS = [
    dict(capacidad=15, precio=0),
    dict(capacidad=30, precio=35),
    dict(capacidad=60, precio=400),
    dict(capacidad=120, precio=3000),
    dict(capacidad=250, precio=15000),
    dict(capacidad=500, precio=90000),
]

# Reciclaje: capacidad del contenedor y multiplicador de lo que paga el camión
RECICLAJE = [
    dict(nombre="Contenedor básico", capacidad=15, multiplicador=1.0, precio=0),
    dict(nombre="Recogida selectiva", capacidad=50, multiplicador=1.25, precio=120),
    dict(nombre="Compostaje", capacidad=90, multiplicador=1.6, precio=800),
    dict(nombre="Planta de biomasa", capacidad=150, multiplicador=2.0, precio=5000),
    dict(nombre="Central de biogás", capacidad=300, multiplicador=2.5, precio=130000),
]

# clase · vida · nivel (herramienta mínima) · volumen en la bolsa · valor · radio/alto · calva que deja
PLANTAS = {
    "hierbajo": dict(nombre="Hierbajo", clase="hierba", vida=2, nivel=0, volumen=1, valor=1, radio=0.4, alto=0.8, calva=0.55),
    "monton_hojas": dict(nombre="Montón de hojas", clase="hojas", vida=4, nivel=0, volumen=3, valor=4, radio=1.2, alto=0.6, calva=0.0),
    "alfombra_hojas": dict(nombre="Hojarasca", clase="hojas", vida=9, nivel=1, volumen=5, valor=10, radio=2.6, alto=0.2, calva=0.0),
    "hierbajo_grande": dict(nombre="Hierbajo gigante", clase="hierba", vida=8, nivel=2, volumen=3, valor=6, radio=0.6, alto=2.0, calva=0.8),
    "girasol_gigante": dict(nombre="Girasol gigante", clase="hierba", vida=10, nivel=2, volumen=3, valor=12, radio=0.5, alto=2.4, calva=0.6),
    "amapola_gigante": dict(nombre="Amapola gigante", clase="hierba", vida=10, nivel=2, volumen=3, valor=12, radio=0.5, alto=2.2, calva=0.6),
    "matorral": dict(nombre="Matorral", clase="lenoso", vida=24, nivel=3, volumen=5, valor=28, radio=1.1, alto=1.4, calva=1.3),
    "seta_gigante": dict(nombre="Seta gigante", clase="lenoso", vida=20, nivel=3, volumen=4, valor=30, radio=1.0, alto=1.6, calva=1.1),
    "zarza": dict(nombre="Zarza", clase="lenoso", vida=42, nivel=4, volumen=6, valor=60, radio=1.3, alto=1.4, calva=1.5),
    "tocon": dict(nombre="Tocón", clase="tronco", vida=80, nivel=6, volumen=10, valor=80, radio=1.2, alto=0.8, calva=1.6),
    "arbol_gigante": dict(nombre="Árbol gigante", clase="tronco", vida=200, nivel=6, volumen=15, valor=200, radio=0.9, alto=2.4, calva=2.2),
    "arbol_otono": dict(nombre="Árbol de otoño", clase="tronco", vida=160, nivel=6, volumen=15, valor=180, radio=0.8, alto=2.4, calva=2.0),
}

# Bichos: nivel = herramienta mínima para poder hacerles daño · dano = lo que quitan por
# mordisco · velocidad en m/s · premio = monedas al matarlo (x valor de la zona)
BICHOS = {
    "caracol": dict(nombre="Caracol", vida=5, nivel=1, dano=6, velocidad=0.9, premio=4, radio=0.4, alto=0.5),
    "escarabajo": dict(nombre="Escarabajo", vida=12, nivel=2, dano=9, velocidad=2.4, premio=10, radio=0.4, alto=0.4),
    "avispa": dict(nombre="Avispa", vida=10, nivel=4, dano=12, velocidad=3.6, premio=20, radio=0.45, alto=1.3),
}


# ------------------------------------------------------------------ simulador
def zona_de(x, z):
    for i, zo in enumerate(ZONAS):
        x0, z0, x1, z1 = zo["rect"]
        if x0 <= x <= x1 and z0 <= z <= z1:
            return i
    return 0


def inventario():
    """Cuántas plantas y bichos de cada tipo hay en cada zona de la escena principal."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import generar_escena as ge
    ge.reiniciar()
    ge.componer()
    cuenta = {}
    for it in ge.items:
        if it[0] in PLANTAS or it[0] in BICHOS:
            clave = (zona_de(it[2], it[4]), it[0])
            cuenta[clave] = cuenta.get(clave, 0) + 1
    return cuenta


def mejor_herramienta(nivel, clase):
    mejor, pot = None, 0.0
    for h in HERRAMIENTAS[:nivel + 1]:
        if clase in h["usos"]:
            d, a = h["usos"][clase]
            p = d * (1 + a) / h["cadencia"]
            if p >= pot:
                mejor, pot = h, p
    return mejor


def precio_afilado(n):
    return int(round(AFILADO_PRECIO * AFILADO_FACTOR ** n))


def simular(verboso=True, t_mover=2.0, t_viaje=20.0, t_siembra=0.3, t_bicho=4.0):
    """Jugador 'tipo': quita siempre lo más rentable que puede, vacía la bolsa cuando se llena
    y compra la mejora más barata en cuanto le llega el dinero."""
    quedan = inventario()
    t = monedas = bolsa = bolsa_valor = cont = cont_valor = ganado = 0.0
    nivel = nb = nr = na = 0
    nz = 0                               # última zona abierta
    semillas = SEMILLAS_INICIALES
    hitos, golpes_max = [], {}
    trofeo = [None]

    def comprar():
        nonlocal monedas, nivel, nb, nr, na, nz
        while True:
            ops = []
            if trofeo[0] is None and nivel + 1 >= len(HERRAMIENTAS) and nz + 1 >= len(ZONAS) and monedas >= TROFEO_PRECIO:
                monedas -= TROFEO_PRECIO
                trofeo[0] = t
                hitos.append((t, f"*** {TROFEO_NOMBRE} ({TROFEO_PRECIO}) ***"))
            if nivel + 1 < len(HERRAMIENTAS):
                ops.append((HERRAMIENTAS[nivel + 1]["precio"], "h"))
            if nb + 1 < len(BOLSAS):
                ops.append((BOLSAS[nb + 1]["precio"], "b"))
            if nr + 1 < len(RECICLAJE):
                ops.append((RECICLAJE[nr + 1]["precio"], "r"))
            if na < AFILADO_MAX:
                ops.append((precio_afilado(na), "a"))
            if nz + 1 < len(ZONAS):
                ops.append((ZONAS[nz + 1]["precio"], "z"))
            orden = {"z": 0, "h": 1, "b": 2, "r": 3, "a": 4}
            # ahorra para la siguiente zona: no compra bolsa/reciclaje caros antes de abrirla
            tope = ZONAS[nz + 1]["precio"] * 0.5 if nz + 1 < len(ZONAS) else float("inf")
            ops = [o for o in ops if o[0] <= monedas and (o[1] != "a" or o[0] <= monedas * 0.25)
                   and (o[1] not in "br" or o[0] <= tope)]
            if not ops:
                return
            precio, que = min(ops, key=lambda o: orden[o[1]])
            monedas -= precio
            if que == "h":
                nivel += 1
                hitos.append((t, f"Herramienta: {HERRAMIENTAS[nivel]['nombre']} ({precio})"))
            elif que == "b":
                nb += 1
                hitos.append((t, f"Bolsa de {BOLSAS[nb]['capacidad']} ({precio})"))
            elif que == "r":
                nr += 1
                hitos.append((t, f"Reciclaje: {RECICLAJE[nr]['nombre']} ({precio})"))
            elif que == "a":
                na += 1
            else:
                nz += 1
                hitos.append((t, f"=== ZONA: {ZONAS[nz]['nombre']} ({precio}) · afilado nivel {na} ==="))

    def vaciar(forzar=False):
        nonlocal t, bolsa, bolsa_valor, cont, cont_valor, monedas, ganado
        t += t_viaje
        cont, cont_valor, bolsa, bolsa_valor = cont + bolsa, cont_valor + bolsa_valor, 0, 0
        if cont >= RECICLAJE[nr]["capacidad"] or forzar:
            pago = round(cont_valor * RECICLAJE[nr]["multiplicador"])
            monedas, ganado, cont, cont_valor = monedas + pago, ganado + pago, 0, 0
            comprar()

    while True:
        mejor = None
        afilado = AFILADO_DANO ** na
        for (zi, tipo), n in quedan.items():
            if n <= 0 or zi > nz:
                continue
            zo = ZONAS[zi]
            es_bicho = tipo in BICHOS
            d = BICHOS[tipo] if es_bicho else PLANTAS[tipo]
            clase = "bicho" if es_bicho else d["clase"]
            if d["nivel"] > nivel:
                continue
            h = mejor_herramienta(nivel, clase)
            if h is None:
                continue
            dano, radio = h["usos"][clase]
            x0, z0, x1, z1 = zo["rect"]
            densidad = 0.0 if es_bicho else sum(
                m for (zj, k), m in quedan.items()
                if zj == zi and k in PLANTAS and PLANTAS[k]["clase"] == clase and PLANTAS[k]["nivel"] <= nivel) / ((x1 - x0) * (z1 - z0))
            k = min(n, max(1.0, 1 + math.pi * radio ** 2 * densidad * 0.6)) if radio > 0 else 1.0
            golpes = math.ceil(d["vida"] * zo["vida"] / (dano * afilado))
            tiempo = golpes * h["cadencia"] + (t_bicho if es_bicho else t_mover)
            valor = (d["premio"] if es_bicho else d["valor"]) * zo["valor"]
            rent = k * valor / tiempo
            if mejor is None or rent > mejor[0]:
                mejor = (rent, zi, tipo, k, tiempo, golpes)
        if mejor is None:
            if bolsa > 0 or cont > 0:
                vaciar(forzar=True)
                continue
            break
        _, zi, tipo, k, tiempo, golpes = mejor
        zo = ZONAS[zi]
        golpes_max[(zi, tipo)] = max(golpes_max.get((zi, tipo), 0), golpes)
        quedan[(zi, tipo)] -= k
        t += tiempo
        if tipo in BICHOS:
            premio = round(BICHOS[tipo]["premio"] * zo["valor"])
            monedas, ganado = monedas + premio, ganado + premio
            comprar()
            continue
        d = PLANTAS[tipo]
        bolsa += k * d["volumen"]
        bolsa_valor += k * d["valor"] * zo["valor"]
        if d["calva"] > 0:
            if semillas < k and monedas >= PRECIO_SEMILLAS:
                monedas -= PRECIO_SEMILLAS
                semillas += PAQUETE_SEMILLAS
            sembradas = min(k, semillas)
            semillas -= sembradas
            t += t_siembra * sembradas
            monedas += PREMIO_CESPED * zo["valor"] * sembradas
            ganado += PREMIO_CESPED * zo["valor"] * sembradas
        if bolsa >= BOLSAS[nb]["capacidad"]:
            vaciar()
    bloqueado = {k: round(n) for k, n in quedan.items() if n > 0.5}
    if verboso:
        print("  min   hito")
        anterior = 0.0
        for tt, txt in hitos:
            print(f" {tt / 60:5.1f}   {txt}   (+{(tt - anterior) / 60:.1f} min)")
            anterior = tt
        peor = max(golpes_max.items(), key=lambda kv: kv[1])
        print(f"\nFin de la partida simulada: {t / 60:.0f} min · ganado {ganado:,.0f} · sobran {monedas:,.0f} · afilado {na}")
        print("Trofeo:", "comprado en el minuto %.0f" % (trofeo[0] / 60) if trofeo[0] else "NO se llega a comprar")
        print(f"Planta que más golpes pidió: {peor[0][1]} en {ZONAS[peor[0][0]]['nombre']} ({peor[1]} golpes)")
        if bloqueado:
            print("ATENCIÓN, se queda sin poder quitar:", bloqueado)
    return hitos, t, bloqueado


# ------------------------------------------------------------------ datos.gd
def _v(valor):
    if isinstance(valor, str):
        return '"%s"' % valor
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, tuple):
        return "Vector%d(%s)" % (len(valor), ", ".join(str(x) for x in valor))
    if isinstance(valor, dict):
        return "{" + ", ".join('"%s": %s' % (k, _v(x)) for k, x in valor.items()) + "}"
    return repr(valor)


def _lista(nombre, filas):
    return "const %s := [\n%s\n]\n" % (nombre, "\n".join("\t%s," % _v(f) for f in filas))


def escribir_gd():
    plantas = {k: dict(d, vida=float(d["vida"])) for k, d in PLANTAS.items()}
    bichos = {k: dict(d, vida=float(d["vida"]), dano=float(d["dano"])) for k, d in BICHOS.items()}
    herr = [dict(h, usos={c: tuple(float(x) for x in u) for c, u in h["usos"].items()}) for h in HERRAMIENTAS]
    zonas = []
    for z in ZONAS:
        x0, z0, x1, z1 = z["rect"]
        p = z["puerta"]
        zonas.append(dict(id=z["id"], nombre=z["nombre"], x0=float(x0), z0=float(z0), x1=float(x1), z1=float(z1),
                          precio=z["precio"], vida=float(z["vida"]), valor=float(z["valor"]), dano=float(z["dano"]),
                          puerta=(float(p[0]), 0.0, float(p[1])) if p else (0.0, 0.0, 0.0)))
    dic = lambda d: "{\n%s\n}" % "\n".join('\t"%s": %s,' % (k, _v(x)) for k, x in d.items())
    txt = f"""extends RefCounted
## Datos de equilibrio del juego.
## ARCHIVO GENERADO por herramientas_dev/economia.py: cambia los números allí (tiene un
## simulador para ver cómo queda el ritmo) y vuelve a ejecutarlo.

const ALCANCE := {ALCANCE}               # metros a los que llegas con la herramienta

## Césped: se siembra con clic derecho sobre las calvas de tierra.
const SEMILLAS_INICIALES := {SEMILLAS_INICIALES}
const PAQUETE_SEMILLAS := {PAQUETE_SEMILLAS}
const PRECIO_SEMILLAS := {PRECIO_SEMILLAS}
const RADIO_SIEMBRA := {RADIO_SIEMBRA}
const TIEMPO_CRECER := {TIEMPO_CRECER}
const PREMIO_CESPED := {PREMIO_CESPED}           # x valor de la zona
## Una calva sin sembrar acaba echando malas hierbas. REBROTE_MAX a 0 lo desactiva.
const REBROTE_MIN := {REBROTE_MIN}
const REBROTE_MAX := {REBROTE_MAX}

const VIDA_JUGADOR := {float(VIDA_JUGADOR)}
const REGENERACION := {REGENERACION}
const ESPERA_REGENERACION := {ESPERA_REGENERACION}

## Afilado: cada nivel multiplica el daño de todas las herramientas.
const AFILADO_DANO := {AFILADO_DANO}
const AFILADO_PRECIO := {float(AFILADO_PRECIO)}
const AFILADO_FACTOR := {AFILADO_FACTOR}
const AFILADO_MAX := {AFILADO_MAX}

const TROFEO_NOMBRE := "{TROFEO_NOMBRE}"
const TROFEO_PRECIO := {TROFEO_PRECIO}

## Zonas del mapa en orden de desbloqueo. vida / valor / dano son multiplicadores.
{_lista("ZONAS", zonas)}
## Herramientas en orden de compra. usos: clase → Vector2(daño por golpe, radio de área).
## La clase "bicho" es el daño contra bichos. La herramienta se elige sola.
{_lista("HERRAMIENTAS", herr)}
{_lista("BOLSAS", BOLSAS)}
## Reciclaje: capacidad del contenedor y multiplicador de lo que paga el camión.
{_lista("RECICLAJE", RECICLAJE)}
## clase: qué herramientas le sirven · nivel: herramienta mínima · calva: tierra que deja
const PLANTAS := {dic(plantas)}

## nivel: herramienta mínima para hacerles daño · dano: vida que quitan por mordisco
const BICHOS := {dic(bichos)}
"""
    with open(os.path.join(RAIZ, "scripts", "datos.gd"), "w") as f:
        f.write(txt)
    print("\nscripts/datos.gd actualizado")


if __name__ == "__main__":
    simular()
    if "--solo-simular" not in sys.argv:
        escribir_gd()
