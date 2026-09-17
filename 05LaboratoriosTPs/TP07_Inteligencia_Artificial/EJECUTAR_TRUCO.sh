#!/usr/bin/env bash
# Abre la mesa de Truco contra el G1. Si el simulador 3D esta abierto,
# el robot gesticula cuando canta; si no, se juega igual.
cd "$(dirname "$0")" || exit 1

CANDIDATOS="python3 python3.13 python3.12 python3.11 python3.10 python"
[ -x "$HOME/.venvs/unitree/bin/python" ] && CANDIDATOS="$HOME/.venvs/unitree/bin/python $CANDIDATOS"
PYTHON=""
for PY in $CANDIDATOS; do
  command -v "$PY" >/dev/null 2>&1 || [ -x "$PY" ] || continue
  PYTHON="$PY"; break
done

if [ -z "$PYTHON" ]; then
  echo "   No encuentro Python. Instalalo y volve a intentar."
  read -r -p "   Enter para cerrar..."; exit 1
fi

# La mesa usa pygame. Si falta, se instala una sola vez para este usuario.
if ! "$PYTHON" -c "import pygame" >/dev/null 2>&1; then
  echo "   Instalando pygame, una sola vez..."
  "$PYTHON" -m pip install --user pygame
fi

"$PYTHON" card_game_framework/main_cli.py "$@"
echo
read -r -p "Enter para cerrar..."
