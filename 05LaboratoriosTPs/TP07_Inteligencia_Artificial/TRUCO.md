# Truco contra el Unitree G1 — extensión del TP07

El G1 juega al truco argentino mano a mano: sin flor, con envido y truco
completos, a 15 o a 30 puntos. Hay dos formas de jugar:

| | Qué es | Cómo se abre |
|---|---|---|
| **Mesa virtual** | Todo en pantalla: vos contra el G1 | `EJECUTAR_TRUCO.bat` / `.sh` |
| **Cartas reales** | Cartas de verdad; un operador le cuenta al G1 lo que pasa en la mesa | `EJECUTAR_TRUCO_CARTAS_REALES.bat`, o *Cartas reales* en el menú |

Si el simulador del TP07 está abierto (`INICIAR_SIMULADOR`), el G1 del
simulador saluda cuando canta. Sin simulador se juega igual.

Requisitos: Python 3.10+ y `pygame`. Los lanzadores lo instalan si falta.

---

## Mesa virtual

- **Controles:** click en tu carta para tirarla; los cantos están a la izquierda y Quiero / No quiero a la derecha.
- **Teclas:** **D** muestra las cartas del robot (para presentar), **M** prende o apaga la voz, **Esc** abre el menú.
- **El robot miente:** canta o acepta sin tener cartas alrededor de la mitad de las veces (`FAROL` en `escena_partida.py`).
- **Versos:** a veces canta con un verso de `truco/frases/frases.md` (`PROB_VERSO` en `frases_robot.py`).

## Cartas reales: pantalla del operador

El robot **no ve la mesa**: no hay visión todavía. Juegan tres personas:

- **el rival**, que juega contra el G1;
- **el ayudante**, que tiene las cartas del G1 y las tira;
- **el operador**, en la notebook.

Cada mano se juega así:

1. **Reparto:** el operador toca en la grilla las 3 cartas que le tocaron al G1.
2. **Turno del rival:** el operador toca la carta que tiró o el canto que hizo. También puede **escribir** lo que dijo el rival ("quiero retruco", "tiro el ancho de espada", "tengo 27"): lo traduce el intérprete y se confirma con Enter.
3. **Turno del G1:** el G1 decide y **dice** su jugada ("¡Truco!", "Tiro el 7 de oro"). En la pantalla aparece en grande qué carta tirar; el ayudante la tira y el operador confirma con Enter.
4. **Envido querido:** el rival dice sus tantos y el operador los carga, como en una mesa real. Si el rival muestra sus 3 cartas y no suman lo que dijo, la pantalla avisa.

Cada jugada y cada orden al robot quedan **registradas con fecha y hora** en
`registros/`, como pide la consigna para el robot físico.

### Con el G1 físico (SIN PROBAR)
```
python card_game_framework/main_cli.py --operador --robot-real eth0 --voz-g1
```
Usa la misma API que `mi_desarrollo/robot.py` (DDS, solo Linux, con el SDK de
Unitree). Antes de usarlo con el robot hay que verificar:
- que `AudioClient.TtsMaker` del G1 hable castellano. Si no, la voz sale por la notebook sin cambiar nada;
- que el saludo (`WaveHand`) funcione con el robot quieto frente a la mesa.

Con el robot real no se envía ningún movimiento de desplazamiento: solo el saludo.

---

## Cómo está armado

```
card_game_framework/card_framework/
├── games/truco/truco_game.py      reglas (motor). Soporta manos "ocultas" para cartas reales
├── agents/heuristic_truco_agent.py la IA del G1 (heurísticas + farol + lectura del tanteador)
├── interfaces/
│   ├── partida_real.py            partida con cartas reales, sin pygame
│   ├── interprete_truco.py        texto -> Clasificador -> Extractor -> Validador (pipeline del TP07)
│   ├── frases_robot.py            lo que dice el G1
│   └── mesa/                      pantallas en pygame (menú, mesa, operador) y conexión al robot
└── rutas.py                       rutas relativas a truco/ y mi_desarrollo/
```

**El cerebro es el mismo en las dos formas de jugar:** `TrucoGame` y
`HeuristicTrucoAgent`. Lo único que cambia es de dónde salen los datos (la
pantalla o un operador) y adónde va la jugada (la animación o la voz y los
gestos del robot).

**Relación con el TP07:** el intérprete repite la arquitectura de la
consigna. El clasificador de intención trabaja por reglas, el extractor saca la
carta y los tantos, y el **validador es independiente**: aunque el
clasificador entienda "quiero", si no hay nada que querer, lo rechaza y dice
por qué.

## Tests

```
cd card_game_framework
python tests/test_truco.py          # reglas e IA
python tests/test_partida_real.py   # cartas reales (incluye 300 partidas simuladas)
python tests/test_interprete.py     # intérprete estilo TP07
```

## Lo que falta

- **Visión:** reconocer las cartas con una cámara. Primero una cámara USB cenital, con un dataset de fotos de las 40 cartas; después la del G1.
- **Micrófono:** reconocimiento de voz que alimente al intérprete. El resto del pipeline no cambia.
- **Probar en el G1 físico:** la voz por su parlante y los gestos.
