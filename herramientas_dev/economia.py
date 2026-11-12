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
PREMIO_CESPED = 1
REBROTE_MIN = 300.0
REBROTE_MAX = 480.0

# usos: clase de planta -> (daño por golpe, radio de área)
HERRAMIENTAS = [
    dict(nombre="Manos", modelo="guantes", precio=0, cadencia=0.35,
         usos={"hierba": (1, 0), "hojas": (1, 0)},
         pos=(0.0, -0.32, -0.55), rot=(-35, 0, 0), escala=1.6),
    dict(nombre="Rastrillo", modelo="rastrillo", precio=12, cadencia=0.35,
         usos={"hojas": (3, 1.8), "hierba": (1, 1.0)},
         pos=(0.32, -0.3, -0.25), rot=(78, 0, 0), escala=1.0),
    dict(nombre="Hoz", modelo="hoz", precio=50, cadencia=0.35,
         usos={"hierba": (2, 1.4)},
         pos=(0.32, -0.3, -0.5), rot=(-40, 20, 0), escala=1.3),
    dict(nombre="Tijeras de podar", modelo="tijeras_podar", precio=180, cadencia=0.3,
         usos={"lenoso": (4, 0)},
         pos=(0.3, -0.45, -0.45), rot=(-50, 0, 0), escala=1.1),
    dict(nombre="Machete", modelo="machete", precio=550, cadencia=0.3,
         usos={"lenoso": (7, 1.0), "hierba": (4, 1.6)},
         pos=(0.32, -0.28, -0.5), rot=(-45, 0, -10), escala=1.3),
    dict(nombre="Desbrozadora", modelo="desbrozadora", precio=1000, cadencia=0.15,
         usos={"hierba": (4, 2.4), "lenoso": (4, 1.6), "hojas": (2, 2.4)},
         pos=(0.3, -0.25, -0.35), rot=(70, 0, 0), escala=1.0),
    dict(nombre="Motosierra", modelo="motosierra", precio=1300, cadencia=0.15,
         usos={"tronco": (8, 0), "lenoso": (8, 0)},
         pos=(0.3, -0.38, -0.45), rot=(0, 180, 0), escala=1.2),
]

BOLSAS = [
    dict(capacidad=15, precio=0),
    dict(capacidad=30, precio=35),
    dict(capacidad=60, precio=140),
    dict(capacidad=120, precio=480),
]

# Reciclaje: capacidad del contenedor y multiplicador de lo que paga el camión
RECICLAJE = [
    dict(nombre="Contenedor básico", capacidad=15, multiplicador=1.0, precio=0),
    dict(nombre="Recogida selectiva", capacidad=50, multiplicador=1.25, precio=90),
    dict(nombre="Compostaje", capacidad=90, multiplicador=1.6, precio=380),
    dict(nombre="Planta de biomasa", capacidad=120, multiplicador=2.0, precio=900),
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


# ------------------------------------------------------------------ simulador
def inventario():
    """Cuántas plantas de cada tipo hay en la escena principal."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import generar_escena as ge
    ge.items.clear(), ge.ocupado.clear()
    ge.rng = ge.np.random.default_rng(ge.SEMILLA)
    ge.componer()
    cuenta = {}
    for it in ge.items:
        if it[0] in PLANTAS:
            cuenta[it[0]] = cuenta.get(it[0], 0) + 1
    return cuenta, (ge.X1 - ge.X0) * (ge.Z1 - ge.Z0) - 110.0


def mejor_herramienta(nivel, clase):
    mejor, pot = None, 0.0
    for h in HERRAMIENTAS[:nivel + 1]:
        if clase in h["usos"]:
            d, a = h["usos"][clase]
            p = d * (1 + a) / h["cadencia"]
            if p >= pot:
                mejor, pot = h, p
    return mejor


def simular(verboso=True, t_mover=2.0, t_viaje=20.0, t_siembra=0.3):
    """Jugador 'tipo': quita siempre lo más rentable que puede, vacía la bolsa cuando se llena
    y compra la mejora más barata en cuanto le llega el dinero."""
    quedan, area = inventario()
    total_valor = sum(PLANTAS[k]["valor"] * n for k, n in quedan.items())
    t = monedas = bolsa = bolsa_valor = cont = cont_valor = ganado = 0.0
    nivel = nb = nr = 0
    semillas = SEMILLAS_INICIALES
    hitos = []

    def comprar():
        nonlocal monedas, nivel, nb, nr
        while True:
            ops = []
            if nivel + 1 < len(HERRAMIENTAS):
                ops.append((HERRAMIENTAS[nivel + 1]["precio"], "h"))
            if nb + 1 < len(BOLSAS):
                ops.append((BOLSAS[nb + 1]["precio"], "b"))
            if nr + 1 < len(RECICLAJE):
                ops.append((RECICLAJE[nr + 1]["precio"], "r"))
            ops = [o for o in ops if o[0] <= monedas]
            if not ops:
                return
            precio, que = min(ops)
            monedas -= precio
            if que == "h":
                nivel += 1
                hitos.append((t, f"Herramienta: {HERRAMIENTAS[nivel]['nombre']} ({precio})"))
            elif que == "b":
                nb += 1
                hitos.append((t, f"Bolsa de {BOLSAS[nb]['capacidad']} ({precio})"))
            else:
                nr += 1
                hitos.append((t, f"Reciclaje: {RECICLAJE[nr]['nombre']} x{RECICLAJE[nr]['multiplicador']} ({precio})"))

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
        for tipo, n in quedan.items():
            d = PLANTAS[tipo]
            if n <= 0 or d["nivel"] > nivel:
                continue
            h = mejor_herramienta(nivel, d["clase"])
            if h is None:
                continue
            dano, radio = h["usos"][d["clase"]]
            densidad = sum(m for k, m in quedan.items() if PLANTAS[k]["clase"] == d["clase"] and PLANTAS[k]["nivel"] <= nivel) / area
            k = min(n, max(1.0, 1 + math.pi * radio ** 2 * densidad * 0.6)) if radio > 0 else 1.0
            tiempo = math.ceil(d["vida"] / dano) * h["cadencia"] + t_mover
            rent = k * d["valor"] / tiempo
            if mejor is None or rent > mejor[0]:
                mejor = (rent, tipo, k, tiempo)
        if mejor is None:
            # nada que pueda quitar: vende lo que lleve; si aun así no puede comprar, fin
            if bolsa > 0 or cont > 0:
                vaciar(forzar=True)
                continue
            break
        _, tipo, k, tiempo = mejor
        d = PLANTAS[tipo]
        quedan[tipo] -= k
        t += tiempo
        bolsa += k * d["volumen"]
        bolsa_valor += k * d["valor"]
        if d["calva"] > 0:
            if semillas < k and monedas >= PRECIO_SEMILLAS:
                monedas -= PRECIO_SEMILLAS
                semillas += PAQUETE_SEMILLAS
            sembradas = min(k, semillas)
            semillas -= sembradas
            t += t_siembra * sembradas
            monedas += PREMIO_CESPED * sembradas
            ganado += PREMIO_CESPED * sembradas
        if bolsa >= BOLSAS[nb]["capacidad"]:
            vaciar()
    bloqueado = {k: round(n) for k, n in quedan.items() if n > 0.5}
    if verboso:
        print(f"Valor total de las plantas del jardín: {total_valor} monedas (sin multiplicadores)")
        print(f"Coste de todas las mejoras: {sum(h['precio'] for h in HERRAMIENTAS) + sum(b['precio'] for b in BOLSAS) + sum(r['precio'] for r in RECICLAJE)}")
        print("\n  min   mejora")
        anterior = 0.0
        for tt, txt in hitos:
            print(f" {tt / 60:5.1f}   {txt}   (+{(tt - anterior) / 60:.1f} min)")
            anterior = tt
        print(f"\nFin de la partida simulada: {t / 60:.1f} min · ganado {ganado:.0f} · sobran {monedas:.0f} monedas")
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
    herr = [dict(h, usos={c: tuple(float(x) for x in u) for c, u in h["usos"].items()}) for h in HERRAMIENTAS]
    txt = f'''extends RefCounted
## Datos de equilibrio del juego.
## ARCHIVO GENERADO por herramientas_dev/economia.py: cambia los números allí (tiene un
## simulador para ver cómo queda el ritmo) y vuelve a ejecutarlo.

const ALCANCE := {ALCANCE}               # metros a los que llegas con la herramienta

## Césped: se siembra con clic derecho sobre las calvas de tierra.
const SEMILLAS_INICIALES := {SEMILLAS_INICIALES}
const PAQUETE_SEMILLAS := {PAQUETE_SEMILLAS}       # semillas por compra
const PRECIO_SEMILLAS := {PRECIO_SEMILLAS}
const RADIO_SIEMBRA := {RADIO_SIEMBRA}         # siembras todas las calvas en este radio de una vez
const TIEMPO_CRECER := {TIEMPO_CRECER}        # segundos hasta que el césped está hecho
const PREMIO_CESPED := {PREMIO_CESPED}           # monedas por cada calva convertida en césped
## Una calva sin sembrar acaba echando malas hierbas. REBROTE_MAX a 0 lo desactiva.
const REBROTE_MIN := {REBROTE_MIN}
const REBROTE_MAX := {REBROTE_MAX}

## Herramientas en orden de compra. usos: clase de planta → Vector2(daño por golpe, radio de
## área; 0 = solo la planta apuntada). cadencia: segundos entre golpes. La herramienta se
## elige sola: la mejor que tengas para la planta apuntada.
{_lista("HERRAMIENTAS", herr)}
## Mejoras de la bolsa.
{_lista("BOLSAS", BOLSAS)}
## Reciclaje: capacidad del contenedor y multiplicador de lo que paga el camión.
{_lista("RECICLAJE", RECICLAJE)}
## clase: qué herramientas le sirven · nivel: herramienta mínima · volumen: lo que ocupa en la
## bolsa · valor: monedas que paga el camión · radio/alto: tamaño · calva: tierra que deja
const PLANTAS := {{
{chr(10).join(chr(9) + '"%s": %s,' % (k, _v(d)) for k, d in plantas.items())}
}}
'''
    with open(os.path.join(RAIZ, "scripts", "datos.gd"), "w") as f:
        f.write(txt)
    print("\nscripts/datos.gd actualizado")


if __name__ == "__main__":
    simular()
    if "--solo-simular" not in sys.argv:
        escribir_gd()
