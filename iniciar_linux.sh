#!/bin/sh
# MicroGrano Lab para Linux: prepara el entorno de Python si hace falta y abre la interfaz.
# Uso: sh iniciar_linux.sh   (o chmod +x iniciar_linux.sh && ./iniciar_linux.sh)
# Opciones: --reparar, --solo-instalar, --comprobar, --consola
DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$DIR" || exit 1
ARRANQUE="$DIR/lanzador/arranque.py"

for PY in "$DIR/.venv/bin/python" python3.13 python3 python; do
  if [ -x "$PY" ] || command -v "$PY" >/dev/null 2>&1; then
    if "$PY" -c 'import sys,sysconfig; sys.exit(0 if sys.version_info[:2] == (3, 13) and sys.maxsize > 2**32 and not sysconfig.get_config_var("Py_GIL_DISABLED") and getattr(sys, "_is_gil_enabled", lambda: True)() else 1)' >/dev/null 2>&1; then
      exec "$PY" "$ARRANQUE" "$@"
    fi
  fi
done

echo "MicroGrano Lab necesita Python 3.13 de 64 bits con GIL."
echo "Instale Python 3.13 con venv y Tk mediante el gestor de su distribución o desde https://www.python.org/downloads/."
exit 1
