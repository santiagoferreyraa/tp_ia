"""El robot dice sus cantos en voz alta. Solo en Windows (SAPI); en otro sistema calla."""

import os
import subprocess
import sys

# El texto viaja por variable de entorno, no pegado al comando: asi ninguna
# comilla ni simbolo de un verso puede romper (o inyectar) nada en PowerShell.
_SCRIPT = (
    "$v = New-Object -ComObject SAPI.SpVoice;"
    "foreach ($x in $v.GetVoices()) {"
    "  if ($x.GetAttribute('Language') -match '(^|;)(c0a|80a|40a|2c0a)') { $v.Voice = $x; break }"
    "};"
    "[void]$v.Speak($env:TRUCO_TEXTO)"
)


class Voz:
    def __init__(self):
        self.activa = sys.platform == "win32"
        self._proceso = None

    @property
    def disponible(self) -> bool:
        return sys.platform == "win32"

    def decir(self, contenido: str) -> None:
        if not (self.activa and self.disponible and contenido):
            return
        self.callar()
        entorno = dict(os.environ, TRUCO_TEXTO=contenido.replace("\n", ", "))
        try:
            self._proceso = subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", _SCRIPT],
                env=entorno, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:
            self._proceso = None

    def callar(self) -> None:
        if self._proceso and self._proceso.poll() is None:
            self._proceso.terminate()
        self._proceso = None

    def alternar(self) -> bool:
        self.activa = not self.activa
        if not self.activa:
            self.callar()
        return self.activa
