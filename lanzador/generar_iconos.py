"""Genera los iconos del lanzador a partir del icono de MicroGrano Lab.

Escribe en `lanzador/recursos/` un ICO de Windows con varios tamaños (para el ejecutable)
y PNG de 64, 128 y 256 px (para la ventana de progreso y otros sistemas).

Uso, con el entorno del repositorio:
    .venv\\Scripts\\python.exe lanzador\\generar_iconos.py
"""
from __future__ import annotations
import os
import struct
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'src'))

from PySide6.QtCore import QBuffer, QIODevice, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402
from micrograno_lab.iconos import _dibujar_app  # noqa: E402

TAMANOS_ICO = (16, 20, 24, 32, 40, 48, 64, 128, 256)
TAMANOS_PNG = (64, 128, 256)


def imagen(lado: int) -> QImage:
    img = QImage(lado, lado, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    pintor = QPainter(img)
    _dibujar_app(pintor, lado)
    pintor.end()
    return img


def como_png(img: QImage) -> bytes:
    bufer = QBuffer()
    bufer.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(bufer, 'PNG')
    return bytes(bufer.data())


def como_dib(img: QImage) -> bytes:
    """Entrada ICO clásica: cabecera BITMAPINFO, píxeles BGRA de abajo arriba y máscara AND."""
    lado = img.width()
    img = img.convertToFormat(QImage.Format.Format_ARGB32)
    datos = bytes(img.constBits())
    por_fila = img.bytesPerLine()
    filas = [datos[y * por_fila:y * por_fila + lado * 4] for y in range(lado - 1, -1, -1)]
    cabecera = struct.pack('<IiiHHIIiiII', 40, lado, lado * 2, 1, 32, 0, lado * lado * 4, 0, 0, 0, 0)
    mascara = b'\x00' * (((lado + 31) // 32) * 4 * lado)
    return cabecera + b''.join(filas) + mascara


def escribir_ico(ruta: Path) -> None:
    entradas = [(lado, como_png(imagen(lado)) if lado >= 128 else como_dib(imagen(lado))) for lado in TAMANOS_ICO]
    cabecera = struct.pack('<HHH', 0, 1, len(entradas))
    desplazamiento = 6 + 16 * len(entradas)
    directorio, cuerpo = b'', b''
    for lado, datos in entradas:
        directorio += struct.pack('<BBBBHHII', lado % 256, lado % 256, 0, 0, 1, 32, len(datos),
                                  desplazamiento + len(cuerpo))
        cuerpo += datos
    ruta.write_bytes(cabecera + directorio + cuerpo)


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    destino = Path(__file__).resolve().parent / 'recursos'
    destino.mkdir(exist_ok=True)
    escribir_ico(destino / 'micrograno.ico')
    for lado in TAMANOS_PNG:
        imagen(lado).save(str(destino / f'micrograno-{lado}.png'), 'PNG')
    print('Iconos escritos en', destino)
    del app
    return 0


if __name__ == '__main__':
    sys.exit(main())
