"""MicroGrano Lab: formularios del catálogo y llamadas a la biblioteca, sin algoritmos duplicados."""
from __future__ import annotations
from pathlib import Path
import os
import sys


def configurar_aplicacion(app) -> None:
    """Nombre, icono, tipografía y apariencia; no afecta a ningún cálculo."""
    from .iconos import icono_app
    from .tema import asegurar_tema
    app.setApplicationName('MicroGrano Lab')
    app.setApplicationDisplayName('MicroGrano Lab')
    app.setOrganizationName('MicroGrano')
    app.setApplicationVersion('1.0.0')
    app.setWindowIcon(icono_app())
    asegurar_tema()


def _senalar_ventana_visible() -> None:
    """Avisa al lanzador (lanzador/arranque.py) de que la ventana ya está abierta."""
    ruta = os.environ.pop('MICROGRANO_SENAL_LISTO', None)
    if ruta:
        try:
            Path(ruta).write_text(str(os.getpid()), encoding='utf-8')
        except OSError:
            pass


def _identificar_en_windows() -> None:
    """Agrupa la ventana bajo su propio icono en la barra de tareas de Windows."""
    if sys.platform.startswith('win'):
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('MicroGrano.Lab.1.0.0')
        except Exception:
            pass


def main() -> int:
    """Inicia Qt solo cuando se solicita la aplicación; la biblioteca no lo necesita."""
    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print('Falta PySide6. Desde la carpeta del repositorio ejecute:\n'
              'python -m pip install -e ".[gui]"', file=sys.stderr)
        return 1
    _identificar_en_windows()
    app = QApplication.instance() or QApplication(sys.argv)
    configurar_aplicacion(app)
    from .asistente import VentanaAsistente
    ventana = VentanaAsistente(persistir=True)
    if ventana.ventana_pequena():
        ventana.showMaximized()
    else:
        ventana.show()
    QTimer.singleShot(0, _senalar_ventana_visible)
    for argumento in sys.argv[1:]:
        ruta = Path(argumento)
        if ruta.name == 'sesion.json' or (ruta.is_dir() and (
                (ruta / 'sesion.json').is_file() or (ruta / 'sesion_reabrible' / 'sesion.json').is_file())):
            ventana.abrir_sesion(str(ruta))
        elif ruta.is_file():
            ventana.importar('valores' if ruta.suffix.lower() == '.csv' else 'imagen', str(ruta))
    return app.exec()
