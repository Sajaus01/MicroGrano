#!/bin/sh
# MicroGrano Lab para macOS: prepara el entorno de Python si hace falta y abre la interfaz.
# Doble clic en Finder. Si macOS no lo abre: clic derecho > Abrir, o en Terminal:
#   sh iniciar_mac.command
DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$DIR" || exit 1
ARRANQUE="$DIR/lanzador/arranque.py"

for PY in "$DIR/.venv/bin/python" python3.13 \
          /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 \
          /opt/homebrew/bin/python3.13 /usr/local/bin/python3.13 python3 python; do
  if [ -x "$PY" ] || command -v "$PY" >/dev/null 2>&1; then
    if "$PY" -c 'import sys,sysconfig; sys.exit(0 if sys.version_info[:2] == (3, 13) and sys.maxsize > 2**32 and not sysconfig.get_config_var("Py_GIL_DISABLED") and getattr(sys, "_is_gil_enabled", lambda: True)() else 1)' >/dev/null 2>&1; then
      "$PY" "$ARRANQUE" "$@"
      CODIGO=$?
      if [ "$CODIGO" -ne 0 ]; then
        printf '\nPulse Intro para cerrar...'
        read _
      fi
      exit "$CODIGO"
    fi
  fi
done

echo "MicroGrano Lab necesita Python 3.13 de 64 bits con GIL."
echo "Instálelo desde https://www.python.org/downloads/ o con Homebrew: brew install python@3.13 python-tk@3.13"
open "https://www.python.org/downloads/" 2>/dev/null
printf 'Pulse Intro para cerrar...'
read _
exit 1
