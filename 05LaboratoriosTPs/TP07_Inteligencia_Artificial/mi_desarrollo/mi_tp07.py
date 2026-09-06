# =====================================================================
#  TP07 - Inteligencia Artificial
#  Agente que interpreta comandos en lenguaje natural
# =====================================================================

import re
from robot import Robot
from ejecutor import Ejecutor
from evaluar import evaluar

ALUMNO = "Estudiante UADE"


# =====================================================================
#  ETAPA 1 - CLASIFICADOR DE INTENCION
# =====================================================================
class ClasificadorIntencion:
    """Decide QUE quiere el usuario, sin mirar los numeros todavia."""

    TIPOS = ("MOVER", "GIRAR", "DETENERSE", "SALUDO",
             "CONSULTAR_ESTADO", "DESCONOCIDO")

    def __init__(self):
        try:
            from entrenar import entrenar_desde_csv
            self.modelo = entrenar_desde_csv()
        except Exception:
            self.modelo = None

    def clasificar(self, texto):
        """Devuelve uno de los seis tipos de TIPOS."""
        t = texto.lower().strip()

        # Las palabras de verbos peligrosos / fuera de dominio se descartan previamente
        if re.search(r"\b(salta|saltá|salto|corre|corré|sprint|empuja|empujá|golpea|rompe|tira|cae|fuerza)\b", t):
            return "DESCONOCIDO"

        if self.modelo is not None:
            try:
                pred = self.modelo.predict([texto])[0]
                if pred in self.TIPOS:
                    return pred
            except Exception:
                pass

        # Respaldo por reglas (Regex)
        if re.search(r"\b(c[óo]mo\s+te\s+llam[aá]s|qu[eé]\s+onda|qui[eé]n\s+sos|cu[aá]ntos?\s+a[ñn]os)\b", t):
            return "DESCONOCIDO"

        if re.search(r"\bno\s+(?:avances?|te\s+muevas?|camines?|sigas?)\b", t) or \
           re.search(r"\b(detente|deténete|par[aá]|fren[aá]|stop|quieto)\b", t):
            return "DETENERSE"

        if re.search(r"\b(bater[íi]a|estado|status|info)\b", t) or \
           re.search(r"c[óo]mo\s+est[aá]s\s+(de\s+)?bater[íi]a", t) or \
           re.search(r"cu[aá]nta\s+bater[íi]a", t):
            return "CONSULTAR_ESTADO"

        if re.search(r"\b(salud[aoá]|hac[eé]\s+un\s+saludo)\b", t) or \
           (re.search(r"\b(hola|hi|wave)\b", t) and not re.search(r"\b(llam[aá]s|sos)\b", t)):
            return "SALUDO"

        if re.search(r"\b(gir[aá]|rot[aá]|turn|vuelta|media\s+vuelta)\b", t):
            return "GIRAR"

        if re.search(r"\b(avanz[aá]|camin[aá]|mu[eé]vete|movete|adelante|retroced[eé]|and[aá]|forward)\b", t):
            return "MOVER"

        return "DESCONOCIDO"


# =====================================================================
#  ETAPA 2 - EXTRACTOR DE PARAMETROS
# =====================================================================
class ExtractorParametros:
    """Saca los numeros del texto. Sigue en unidades humanas."""

    def extraer(self, texto, tipo):
        params = {}
        t = texto.lower().strip()

        # Distancia en metros (ej. "2 metros", "0.5 metros", "1 metro")
        m_dist = re.search(r"(\d+(?:\.\d+)?)\s*metro", t)
        if m_dist:
            params["distancia_m"] = float(m_dist.group(1))

        # Ángulo en grados (ej. "90 grados", "45°")
        m_ang = re.search(r"(\d+)\s*(?:grado|°)", t)
        if m_ang:
            params["angulo_deg"] = int(m_ang.group(1))
        elif "media vuelta" in t:
            params["angulo_deg"] = 180

        # Velocidad en m/s (ej. "a 0.2 m/s", "2 m/s")
        m_vel = re.search(r"(\d+(?:\.\d+)?)\s*m/s", t)
        if m_vel:
            params["velocidad_ms"] = float(m_vel.group(1))
        elif re.search(r"\b(despacio|lento)\b", t):
            params["velocidad_ms"] = 0.2
        elif re.search(r"\b(r[aá]pido|veloz)\b", t):
            params["velocidad_ms"] = 0.5

        # Dirección
        if re.search(r"\b(derecha|derecho)\b", t):
            params["direccion"] = "derecha"
        elif re.search(r"\b(izquierda)\b", t):
            params["direccion"] = "izquierda"
        elif re.search(r"\b(atr[aá]s|retroced[eé])\b", t):
            params["direccion"] = "atras"

        return params


# =====================================================================
#  ETAPA 3 - VALIDADOR DE SEGURIDAD
# =====================================================================
class ValidadorSeguridad:
    """La ultima barrera antes del robot."""

    PALABRAS_PELIGROSAS = ("salta", "saltá", "salto", "corre", "corré", "sprint",
                           "empuja", "empujá", "golpea", "rompe", "tira", "cae", "fuerza")

    DIST_MAX_M = 5.0
    VEL_MAX_MS = 0.5
    ANG_MAX_DEG = 180

    def __init__(self, perfil):
        self.perfil = perfil

    def validar(self, texto, tipo, parametros):
        t = texto.lower().strip()

        # 1. Palabras peligrosas en el texto original
        for p in self.PALABRAS_PELIGROSAS:
            if re.search(r"\b" + re.escape(p) + r"\b", t):
                return False, f"Acción '{p}' no permitida por razones de seguridad."

        # 2. Distancia máxima
        dist = parametros.get("distancia_m")
        if dist is not None and dist > self.DIST_MAX_M:
            return False, f"Distancia {dist}m excede límite de {self.DIST_MAX_M}m"

        # 3. Velocidad máxima
        vel = parametros.get("velocidad_ms")
        if vel is not None and vel > self.VEL_MAX_MS:
            return False, f"Velocidad {vel} m/s excede límite de {self.VEL_MAX_MS} m/s"

        # 4. Ángulo máximo (180°)
        ang = parametros.get("angulo_deg")
        if ang is not None and ang > self.ANG_MAX_DEG:
            return False, f"Ángulo {ang}° excede límite de {self.ANG_MAX_DEG}°"

        return True, ""


# =====================================================================
#  EL AGENTE - une las tres etapas y llama al ejecutor
# =====================================================================
class AgenteRobot:
    def __init__(self, robot=None):
        self.robot = robot
        self.clasificador = ClasificadorIntencion()
        self.extractor = ExtractorParametros()
        self.validador = ValidadorSeguridad(
            robot.perfil if robot else _perfil_por_defecto())
        self.ejecutor = Ejecutor(robot) if robot else None
        self.historial = []

    def procesar(self, texto):
        # 1. Clasificar intención
        tipo = self.clasificador.clasificar(texto)

        # 2. Extraer parámetros
        parametros = self.extractor.extraer(texto, tipo)

        # 3. Validar seguridad
        valido, motivo = self.validador.validar(texto, tipo, parametros)

        if not valido:
            return {
                "tipo": tipo,
                "parametros": parametros,
                "ejecutar": False,
                "bloqueado": True,
                "confianza": 0.0,
                "texto_original": texto,
                "mensaje": f"BLOQUEADO: {motivo}",
            }

        if tipo == "DESCONOCIDO":
            return {
                "tipo": "DESCONOCIDO",
                "parametros": {},
                "ejecutar": False,
                "bloqueado": False,
                "confianza": 0.0,
                "texto_original": texto,
                "mensaje": "Comando no reconocido",
            }

        # 4. Ejecutar si hay robot conectado
        if self.ejecutor is not None:
            self.ejecutor.ejecutar(tipo, parametros)

        return {
            "tipo": tipo,
            "parametros": parametros,
            "ejecutar": True,
            "bloqueado": False,
            "confianza": 0.9,
            "texto_original": texto,
            "mensaje": f"Ejecutado {tipo} con {parametros}",
        }


def _perfil_por_defecto():
    """Permite evaluar el agente sin abrir el simulador."""
    import sys
    from pathlib import Path
    entorno = Path(__file__).resolve().parent.parent / "entorno"
    if str(entorno) not in sys.path:
        sys.path.insert(0, str(entorno))
    from sim.safety import perfil
    return perfil("tp07")


def main():
    import sys

    sin_robot = "--sin-robot" in sys.argv

    robot = None
    if not sin_robot:
        robot = Robot()
        robot.conectar()

    try:
        agente = AgenteRobot(robot)
        evaluar(agente)

        if robot is not None:
            print("\n  Escribi ordenes para el robot. Enter vacio para salir.")
            while True:
                try:
                    texto = input("\n  > ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if not texto:
                    break
                r = agente.procesar(texto)
                print(f"    {r['tipo']}  {r.get('mensaje', '')}")
    finally:
        if robot is not None:
            robot.detenerse()
            robot.desconectar()


if __name__ == "__main__":
    main()
