"""Iconos vectoriales de la interfaz, dibujados con QPainter al estilo de SF Symbols.

Cada icono se pinta en una cuadrícula de 24×24 unidades y toma su color del tema
activo en el momento de dibujarse; por eso cambia solo al pasar a modo oscuro.
"""
from __future__ import annotations
import math
from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt
from PySide6.QtGui import (QColor, QFont, QGuiApplication, QIcon, QIconEngine, QLinearGradient,
                           QPainter, QPainterPath, QPen, QPixmap, QPolygonF, QRadialGradient)
from .tema import tema

_DIBUJOS: dict = {}


def _registro(*nombres):
    def decorador(funcion):
        for nombre in nombres:
            _DIBUJOS[nombre] = funcion
        return funcion
    return decorador


def _linea(p: QPainter, *puntos) -> None:
    p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in puntos]))


def _rect(p: QPainter, x, y, w, h, r) -> None:
    p.drawRoundedRect(QRectF(x, y, w, h), r, r)


def _punto(p: QPainter, x, y, r, color) -> None:
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawEllipse(QPointF(x, y), r, r)
    p.restore()


def _destello(p: QPainter, cx, cy, s, color) -> None:
    camino = QPainterPath()
    camino.moveTo(cx, cy - s)
    camino.quadTo(cx, cy, cx + s, cy)
    camino.quadTo(cx, cy, cx, cy + s)
    camino.quadTo(cx, cy, cx - s, cy)
    camino.quadTo(cx, cy, cx, cy - s)
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawPath(camino)
    p.restore()


def _caja_abierta(p: QPainter) -> None:
    camino = QPainterPath()
    camino.moveTo(8.5, 9.5)
    camino.lineTo(6.5, 9.5)
    camino.quadTo(4.5, 9.5, 4.5, 11.5)
    camino.lineTo(4.5, 18.5)
    camino.quadTo(4.5, 20.5, 6.5, 20.5)
    camino.lineTo(17.5, 20.5)
    camino.quadTo(19.5, 20.5, 19.5, 18.5)
    camino.lineTo(19.5, 11.5)
    camino.quadTo(19.5, 9.5, 17.5, 9.5)
    camino.lineTo(15.5, 9.5)
    p.drawPath(camino)


@_registro('barra_lateral')
def _(p, c):
    _rect(p, 3, 5, 18, 14, 3)
    _linea(p, (9.5, 5.5), (9.5, 18.5))


@_registro('inspector')
def _(p, c):
    _rect(p, 3, 5, 18, 14, 3)
    _linea(p, (14.5, 5.5), (14.5, 18.5))


@_registro('panel_inferior')
def _(p, c):
    _rect(p, 3, 5, 18, 14, 3)
    _linea(p, (3.5, 13.5), (20.5, 13.5))


@_registro('importar')
def _(p, c):
    camino = QPainterPath()
    camino.moveTo(4, 13.5)
    camino.lineTo(4, 17.5)
    camino.quadTo(4, 20, 6.5, 20)
    camino.lineTo(17.5, 20)
    camino.quadTo(20, 20, 20, 17.5)
    camino.lineTo(20, 13.5)
    p.drawPath(camino)
    _linea(p, (12, 3.5), (12, 14.5))
    _linea(p, (8, 10.5), (12, 14.5), (16, 10.5))


@_registro('exportar')
def _(p, c):
    _caja_abierta(p)
    _linea(p, (12, 14.5), (12, 3))
    _linea(p, (8.5, 6.5), (12, 3), (15.5, 6.5))


@_registro('guardar')
def _(p, c):
    _caja_abierta(p)
    _linea(p, (12, 3), (12, 14))
    _linea(p, (8.5, 10.5), (12, 14), (15.5, 10.5))


@_registro('abrir')
def _(p, c):
    camino = QPainterPath()
    camino.moveTo(3.5, 7.5)
    camino.quadTo(3.5, 5.5, 5.5, 5.5)
    camino.lineTo(9.5, 5.5)
    camino.lineTo(11.5, 7.5)
    camino.lineTo(18.5, 7.5)
    camino.quadTo(20.5, 7.5, 20.5, 9.5)
    camino.lineTo(20.5, 17.5)
    camino.quadTo(20.5, 19.5, 18.5, 19.5)
    camino.lineTo(5.5, 19.5)
    camino.quadTo(3.5, 19.5, 3.5, 17.5)
    camino.closeSubpath()
    p.drawPath(camino)
    _linea(p, (3.5, 10.5), (20.5, 10.5))


@_registro('nuevo')
def _(p, c):
    _rect(p, 5, 3.5, 14, 17, 3)
    _linea(p, (12, 9), (12, 15))
    _linea(p, (9, 12), (15, 12))


@_registro('ejecutar')
def _(p, c):
    camino = QPainterPath()
    camino.moveTo(8, 5.5)
    camino.lineTo(18.5, 12)
    camino.lineTo(8, 18.5)
    camino.closeSubpath()
    p.setBrush(c)
    p.drawPath(camino)


@_registro('buscar')
def _(p, c):
    p.drawEllipse(QPointF(10.5, 10.5), 6, 6)
    _linea(p, (15, 15), (20, 20))


@_registro('zoom_mas')
def _(p, c):
    p.drawEllipse(QPointF(10.5, 10.5), 6.5, 6.5)
    _linea(p, (15.3, 15.3), (20, 20))
    _linea(p, (7.8, 10.5), (13.2, 10.5))
    _linea(p, (10.5, 7.8), (10.5, 13.2))


@_registro('zoom_menos')
def _(p, c):
    p.drawEllipse(QPointF(10.5, 10.5), 6.5, 6.5)
    _linea(p, (15.3, 15.3), (20, 20))
    _linea(p, (7.8, 10.5), (13.2, 10.5))


@_registro('ajustar')
def _(p, c):
    for puntos in (((4, 9), (4, 4), (9, 4)), ((15, 4), (20, 4), (20, 9)),
                   ((20, 15), (20, 20), (15, 20)), ((9, 20), (4, 20), (4, 15))):
        _linea(p, *puntos)


@_registro('tamano_real')
def _(p, c):
    f = QFont()
    f.setPixelSize(10)
    f.setBold(True)
    p.setFont(f)
    p.drawText(QRectF(0, 0, 24, 24), Qt.AlignmentFlag.AlignCenter, '1:1')


@_registro('mover')
def _(p, c):
    _linea(p, (12, 3.5), (12, 20.5))
    _linea(p, (3.5, 12), (20.5, 12))
    _linea(p, (9.5, 6), (12, 3.5), (14.5, 6))
    _linea(p, (9.5, 18), (12, 20.5), (14.5, 18))
    _linea(p, (6, 9.5), (3.5, 12), (6, 14.5))
    _linea(p, (18, 9.5), (20.5, 12), (18, 14.5))


@_registro('recortar')
def _(p, c):
    _linea(p, (7, 3), (7, 17), (21, 17))
    _linea(p, (3, 7), (17, 7), (17, 21))


@_registro('regla')
def _(p, c):
    p.save()
    p.translate(12, 12)
    p.rotate(-45)
    _rect(p, -10, -3.6, 20, 7.2, 1.6)
    for i, x in enumerate((-6, -3, 0, 3, 6)):
        _linea(p, (x, -3.6), (x, -3.6 + (3.0 if i % 2 == 0 else 1.8)))
    p.restore()


@_registro('perfil')
def _(p, c):
    _linea(p, (3, 15), (7, 15), (9.5, 7), (12.5, 18), (15, 9), (17, 13), (21, 13))


@_registro('capas')
def _(p, c):
    camino = QPainterPath()
    camino.moveTo(12, 3.5)
    camino.lineTo(20.5, 8)
    camino.lineTo(12, 12.5)
    camino.lineTo(3.5, 8)
    camino.closeSubpath()
    p.drawPath(camino)
    _linea(p, (3.5, 12), (12, 16.5), (20.5, 12))
    _linea(p, (3.5, 16), (12, 20.5), (20.5, 16))


@_registro('contornos')
def _(p, c):
    pluma = p.pen()
    pluma.setDashPattern([1.6, 1.6])
    p.setPen(pluma)
    camino = QPainterPath()
    camino.moveTo(6, 8)
    camino.cubicTo(9, 3, 17, 4, 19, 8)
    camino.cubicTo(21, 12, 18, 19, 12, 19)
    camino.cubicTo(6, 19, 3, 13, 6, 8)
    p.drawPath(camino)


@_registro('numero')
def _(p, c):
    _linea(p, (10, 4), (8, 20))
    _linea(p, (16, 4), (14, 20))
    _linea(p, (5, 9), (20, 9))
    _linea(p, (4, 15), (19, 15))


@_registro('lado_a_lado')
def _(p, c):
    _rect(p, 3, 5, 18, 14, 3)
    _linea(p, (12, 5.5), (12, 18.5))


@_registro('cortina')
def _(p, c):
    _rect(p, 3, 5, 18, 14, 3)
    _linea(p, (12, 2.5), (12, 21.5))
    _punto(p, 12, 12, 2.7, c)


@_registro('dato', 'imagen')
def _(p, c):
    _rect(p, 3, 5, 18, 14, 3)
    _linea(p, (6, 16.5), (10, 12), (13, 15), (15, 13), (18, 16.5))
    p.drawEllipse(QPointF(15.5, 9.3), 1.5, 1.5)


@_registro('grises', 'automatico')
def _(p, c):
    p.drawEllipse(QPointF(12, 12), 8, 8)
    camino = QPainterPath()
    camino.moveTo(12, 4)
    camino.arcTo(QRectF(4, 4, 16, 16), 90, 180)
    camino.closeSubpath()
    p.fillPath(camino, c)


@_registro('contraste', 'invertir')
def _(p, c):
    p.drawEllipse(QPointF(12, 12), 8, 8)
    camino = QPainterPath()
    camino.moveTo(12, 4)
    camino.arcTo(QRectF(4, 4, 16, 16), 90, -180)
    camino.closeSubpath()
    p.fillPath(camino, c)


@_registro('umbral')
def _(p, c):
    _rect(p, 3.5, 3.5, 17, 17, 4)
    camino = QPainterPath()
    camino.addRoundedRect(QRectF(3.5, 3.5, 17, 17), 4, 4)
    mitad = QPainterPath()
    mitad.addRect(QRectF(3.5, 3.5, 8.5, 17))
    p.fillPath(camino.intersected(mitad), c)


@_registro('canales')
def _(p, c):
    for x, y in ((12, 8.8), (8.8, 14.4), (15.2, 14.4)):
        p.drawEllipse(QPointF(x, y), 5, 5)


@_registro('histograma')
def _(p, c):
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(c)
    for x, y in ((3.5, 12), (8.5, 6), (13.5, 9), (18.5, 14.5)):
        p.drawRoundedRect(QRectF(x, y, 3.2, 20.5 - y), 1.1, 1.1)
    p.restore()


@_registro('iluminacion', 'sol')
def _(p, c):
    p.drawEllipse(QPointF(12, 12), 3.8, 3.8)
    for k in range(8):
        a = math.radians(k * 45)
        _linea(p, (12 + 6.7 * math.cos(a), 12 + 6.7 * math.sin(a)),
               (12 + 9.0 * math.cos(a), 12 + 9.0 * math.sin(a)))


@_registro('luna')
def _(p, c):
    disco = QPainterPath()
    disco.addEllipse(QPointF(12, 12), 8, 8)
    mordida = QPainterPath()
    mordida.addEllipse(QPointF(16.5, 8.5), 7, 7)
    p.drawPath(disco.subtracted(mordida))


@_registro('ruido')
def _(p, c):
    for x, y, r in ((5, 6, 1.3), (10, 5, 1.0), (15, 6.5, 1.5), (19.5, 5, 1.0), (6.5, 11, 1.0),
                    (12, 11.5, 1.6), (17.5, 11.5, 1.1), (4.5, 16.5, 1.4), (9.5, 17, 1.0),
                    (14.5, 17.5, 1.3), (19.5, 17, 1.5)):
        _punto(p, x, y, r, c)


@_registro('varita')
def _(p, c):
    _linea(p, (4, 20), (14.5, 9.5))
    _destello(p, 17.5, 6, 3.4, c)
    _destello(p, 8, 5, 1.9, c)
    _destello(p, 19.5, 13.5, 1.7, c)


@_registro('mascara')
def _(p, c):
    _rect(p, 3.5, 3.5, 17, 17, 4)
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(c)
    p.drawEllipse(QPointF(12, 12), 5, 4.2)
    p.restore()


@_registro('morfologia')
def _(p, c):
    p.drawEllipse(QPointF(12, 12), 8, 8)
    pluma = p.pen()
    pluma.setDashPattern([1.4, 1.6])
    p.setPen(pluma)
    p.drawEllipse(QPointF(12, 12), 4.3, 4.3)


@_registro('esqueleto')
def _(p, c):
    _linea(p, (4, 18.5), (9, 10.5), (15, 14), (20, 5))
    _linea(p, (9, 10.5), (7.5, 4))
    for x, y in ((4, 18.5), (9, 10.5), (15, 14), (20, 5), (7.5, 4)):
        _punto(p, x, y, 1.7, c)


@_registro('segmentar')
def _(p, c):
    _rect(p, 3, 3, 18, 18, 4)
    _linea(p, (9.5, 3.5), (9.5, 9.5), (3.5, 11))
    _linea(p, (9.5, 9.5), (15, 13.5), (20.5, 10.5))
    _linea(p, (15, 13.5), (13.5, 20.5))


@_registro('bordes')
def _(p, c):
    camino = QPainterPath()
    camino.moveTo(3.5, 15)
    camino.cubicTo(6, 6, 9, 6, 10.5, 12)
    camino.cubicTo(12, 18, 15, 18, 16.5, 11)
    camino.cubicTo(17.5, 7, 19.5, 7, 20.5, 9)
    p.drawPath(camino)


@_registro('gota')
def _(p, c):
    camino = QPainterPath()
    camino.moveTo(12, 3.5)
    camino.cubicTo(12, 3.5, 5.5, 10.5, 5.5, 14.5)
    camino.cubicTo(5.5, 18.4, 8.4, 21, 12, 21)
    camino.cubicTo(15.6, 21, 18.5, 18.4, 18.5, 14.5)
    camino.cubicTo(18.5, 10.5, 12, 3.5, 12, 3.5)
    camino.closeSubpath()
    p.drawPath(camino)


@_registro('paleta')
def _(p, c):
    camino = QPainterPath()
    camino.moveTo(12, 3.5)
    camino.cubicTo(6.5, 3.5, 3.5, 7.5, 3.5, 12)
    camino.cubicTo(3.5, 16.5, 7, 20.5, 11.5, 20.5)
    camino.cubicTo(13, 20.5, 13.5, 19.5, 13, 18.3)
    camino.cubicTo(12.4, 17, 13, 15.5, 14.6, 15.5)
    camino.lineTo(17, 15.5)
    camino.cubicTo(19, 15.5, 20.5, 14, 20.5, 12)
    camino.cubicTo(20.5, 7.3, 16.7, 3.5, 12, 3.5)
    camino.closeSubpath()
    p.drawPath(camino)
    for x, y in ((8, 10.5), (11.5, 7.5), (15.5, 8.5), (7.8, 14.6)):
        _punto(p, x, y, 1.4, c)


@_registro('venn')
def _(p, c):
    p.drawEllipse(QPointF(9, 12), 6, 6)
    p.drawEllipse(QPointF(15, 12), 6, 6)


@_registro('objetos')
def _(p, c):
    for x in (6, 12, 18):
        for y in (6, 12, 18):
            p.drawEllipse(QPointF(x, y), 2.2, 2.2)


@_registro('forma')
def _(p, c):
    camino = QPainterPath()
    camino.moveTo(4, 19.5)
    camino.lineTo(9.5, 10)
    camino.lineTo(15, 19.5)
    camino.closeSubpath()
    p.drawPath(camino)
    p.drawEllipse(QPointF(15.5, 8), 4, 4)


@_registro('densidad')
def _(p, c):
    _rect(p, 3.5, 3.5, 17, 17, 3)
    _linea(p, (9.2, 3.5), (9.2, 20.5))
    _linea(p, (14.8, 3.5), (14.8, 20.5))
    _linea(p, (3.5, 9.2), (20.5, 9.2))
    _linea(p, (3.5, 14.8), (20.5, 14.8))
    p.fillRect(QRectF(9.2, 9.2, 5.6, 5.6), c)


@_registro('fraccion')
def _(p, c):
    p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
    cuna = QPainterPath()
    cuna.moveTo(12, 12)
    cuna.arcTo(QRectF(3.5, 3.5, 17, 17), 90, -115)
    cuna.closeSubpath()
    p.fillPath(cuna, c)


@_registro('intercepto')
def _(p, c):
    _linea(p, (3, 8), (21, 8))
    _linea(p, (3, 16), (21, 16))
    pluma = p.pen()
    pluma.setWidthF(pluma.widthF() * 0.85)
    p.setPen(pluma)
    camino = QPainterPath()
    camino.moveTo(9, 3)
    camino.cubicTo(12, 8, 6, 14, 10, 21)
    camino.moveTo(16, 3)
    camino.cubicTo(19, 9, 13, 15, 16, 21)
    p.drawPath(camino)


@_registro('estadistica')
def _(p, c):
    _linea(p, (3.5, 20), (20.5, 20))
    camino = QPainterPath()
    camino.moveTo(3.5, 18)
    camino.cubicTo(7.2, 18, 8.6, 6, 12, 6)
    camino.cubicTo(15.4, 6, 16.8, 18, 20.5, 18)
    p.drawPath(camino)


@_registro('tabla')
def _(p, c):
    _rect(p, 3.5, 4.5, 17, 15, 2.5)
    _linea(p, (3.5, 9.5), (20.5, 9.5))
    _linea(p, (3.5, 14.5), (20.5, 14.5))
    _linea(p, (9.5, 4.5), (9.5, 19.5))


@_registro('grafica')
def _(p, c):
    _linea(p, (4, 4), (4, 20), (20, 20))
    _linea(p, (7, 15.5), (11, 11), (14, 13), (19.5, 6.5))


@_registro('resumen')
def _(p, c):
    _rect(p, 5, 3, 14, 18, 2.5)
    _linea(p, (8.5, 8), (15.5, 8))
    _linea(p, (8.5, 11.5), (15.5, 11.5))
    _linea(p, (8.5, 15), (13, 15))


@_registro('historial', 'reloj')
def _(p, c):
    p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
    _linea(p, (12, 7.5), (12, 12), (15, 14))


@_registro('codigo')
def _(p, c):
    _linea(p, (8, 7), (3.5, 12), (8, 17))
    _linea(p, (16, 7), (20.5, 12), (16, 17))
    _linea(p, (13.5, 5), (10.5, 19))


@_registro('ayuda')
def _(p, c):
    p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
    camino = QPainterPath()
    camino.moveTo(9.5, 9.7)
    camino.cubicTo(9.5, 7.8, 10.7, 7, 12, 7)
    camino.cubicTo(13.4, 7, 14.6, 8, 14.6, 9.5)
    camino.cubicTo(14.6, 11.4, 12, 11.4, 12, 13.6)
    p.drawPath(camino)
    _punto(p, 12, 16.7, 1.1, c)


@_registro('info')
def _(p, c):
    p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
    _linea(p, (12, 11), (12, 16.5))
    _punto(p, 12, 7.9, 1.1, c)


@_registro('aviso')
def _(p, c):
    camino = QPainterPath()
    camino.moveTo(12, 4)
    camino.lineTo(20.8, 19.3)
    camino.lineTo(3.2, 19.3)
    camino.closeSubpath()
    p.drawPath(camino)
    _linea(p, (12, 9.5), (12, 14))
    _punto(p, 12, 16.6, 1.05, c)


@_registro('error')
def _(p, c):
    p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
    _linea(p, (9, 9), (15, 15))
    _linea(p, (15, 9), (9, 15))


@_registro('ok')
def _(p, c):
    p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
    _linea(p, (8, 12.3), (11, 15.2), (16.2, 9.2))


@_registro('check')
def _(p, c):
    _linea(p, (5, 12.5), (10, 17), (19, 7))


@_registro('cerrar')
def _(p, c):
    _linea(p, (6.5, 6.5), (17.5, 17.5))
    _linea(p, (17.5, 6.5), (6.5, 17.5))


@_registro('mas')
def _(p, c):
    _linea(p, (12, 5), (12, 19))
    _linea(p, (5, 12), (19, 12))


@_registro('menos')
def _(p, c):
    _linea(p, (5, 12), (19, 12))


@_registro('chevron_abajo')
def _(p, c):
    _linea(p, (6, 9.5), (12, 15.5), (18, 9.5))


@_registro('chevron_arriba')
def _(p, c):
    _linea(p, (6, 14.5), (12, 8.5), (18, 14.5))


@_registro('chevron_derecha')
def _(p, c):
    _linea(p, (9.5, 6), (15.5, 12), (9.5, 18))


@_registro('chevron_izquierda')
def _(p, c):
    _linea(p, (14.5, 6), (8.5, 12), (14.5, 18))


@_registro('restablecer')
def _(p, c):
    _linea(p, (9, 5), (4.5, 9.5), (9, 14))
    camino = QPainterPath()
    camino.moveTo(4.5, 9.5)
    camino.lineTo(14.5, 9.5)
    camino.cubicTo(18, 9.5, 20, 12, 20, 14.75)
    camino.cubicTo(20, 17.5, 18, 20, 14.5, 20)
    camino.lineTo(9.5, 20)
    p.drawPath(camino)


@_registro('copiar')
def _(p, c):
    _rect(p, 8.5, 8.5, 12, 12, 2.5)
    camino = QPainterPath()
    camino.moveTo(15.5, 8.5)
    camino.lineTo(15.5, 5.5)
    camino.quadTo(15.5, 3.5, 13.5, 3.5)
    camino.lineTo(5.5, 3.5)
    camino.quadTo(3.5, 3.5, 3.5, 5.5)
    camino.lineTo(3.5, 13.5)
    camino.quadTo(3.5, 15.5, 5.5, 15.5)
    camino.lineTo(8.5, 15.5)
    p.drawPath(camino)


@_registro('enlace')
def _(p, c):
    p.save()
    p.translate(12, 12)
    p.rotate(-45)
    _rect(p, -9.5, -3.4, 11, 6.8, 3.4)
    _rect(p, -1.5, -3.4, 11, 6.8, 3.4)
    p.restore()


@_registro('etiqueta')
def _(p, c):
    camino = QPainterPath()
    camino.moveTo(3.5, 5.5)
    camino.quadTo(3.5, 3.5, 5.5, 3.5)
    camino.lineTo(11, 3.5)
    camino.lineTo(20.5, 13)
    camino.lineTo(13, 20.5)
    camino.lineTo(3.5, 11)
    camino.closeSubpath()
    p.drawPath(camino)
    p.drawEllipse(QPointF(8, 8), 1.5, 1.5)


@_registro('guia')
def _(p, c):
    _linea(p, (3.5, 6.8), (5.2, 8.5), (8, 5.3))
    _linea(p, (11, 7), (20.5, 7))
    _linea(p, (3.5, 12.3), (5.2, 14), (8, 10.8))
    _linea(p, (11, 12.5), (20.5, 12.5))
    p.drawEllipse(QPointF(5.7, 18), 1.9, 1.9)
    _linea(p, (11, 18), (20.5, 18))


@_registro('datos')
def _(p, c):
    frente = QRectF(4, 9, 12, 11)
    detras = QRectF(8, 4, 12, 11)
    recorte = QPainterPath()
    recorte.addRect(QRectF(0, 0, 24, 24))
    hueco = QPainterPath()
    hueco.addRoundedRect(frente.adjusted(-1.6, -1.6, 1.6, 1.6), 3.5, 3.5)
    p.save()
    p.setClipPath(recorte.subtracted(hueco))
    p.drawRoundedRect(detras, 2.6, 2.6)
    p.restore()
    p.drawRoundedRect(frente, 2.6, 2.6)


@_registro('herramientas')
def _(p, c):
    for y, x in ((6.5, 15.5), (12, 8.5), (17.5, 13)):
        _linea(p, (3.5, y), (20.5, y))
        _punto(p, x, y, 2.4, c)


@_registro('usar')
def _(p, c):
    p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
    _linea(p, (7.8, 12), (16, 12))
    _linea(p, (12.6, 8.6), (16, 12), (12.6, 15.4))


@_registro('matraz')
def _(p, c):
    camino = QPainterPath()
    camino.moveTo(9.5, 3.5)
    camino.lineTo(9.5, 9.5)
    camino.lineTo(4.7, 17.8)
    camino.quadTo(3.6, 20.5, 6.5, 20.5)
    camino.lineTo(17.5, 20.5)
    camino.quadTo(20.4, 20.5, 19.3, 17.8)
    camino.lineTo(14.5, 9.5)
    camino.lineTo(14.5, 3.5)
    p.drawPath(camino)
    _linea(p, (8, 3.5), (16, 3.5))
    _linea(p, (7, 15), (17, 15))


@_registro('ojo')
def _(p, c):
    camino = QPainterPath()
    camino.moveTo(2.5, 12)
    camino.cubicTo(5, 7, 8.5, 5.5, 12, 5.5)
    camino.cubicTo(15.5, 5.5, 19, 7, 21.5, 12)
    camino.cubicTo(19, 17, 15.5, 18.5, 12, 18.5)
    camino.cubicTo(8.5, 18.5, 5, 17, 2.5, 12)
    camino.closeSubpath()
    p.drawPath(camino)
    p.drawEllipse(QPointF(12, 12), 3.2, 3.2)
    _punto(p, 12, 12, 1.2, c)


@_registro('puntos')
def _(p, c):
    for x in (6, 12, 18):
        _punto(p, x, 12, 1.7, c)


@_registro('filtro')
def _(p, c):
    _linea(p, (4, 7), (20, 7))
    _linea(p, (7, 12), (17, 12))
    _linea(p, (10, 17), (14, 17))


@_registro('teclado')
def _(p, c):
    _rect(p, 2.5, 6, 19, 12, 2.5)
    for x in (6, 9.3, 12.6, 15.9):
        _punto(p, x, 10, 0.9, c)
    _punto(p, 18.5, 10, 0.9, c)
    _linea(p, (8, 14.3), (16, 14.3))


@_registro('destello')
def _(p, c):
    _destello(p, 10, 12, 6.5, c)
    _destello(p, 18, 6, 3, c)
    _destello(p, 18.5, 17.5, 2.3, c)


@_registro('cuadricula')
def _(p, c):
    _rect(p, 3.5, 3.5, 17, 17, 3)
    for v in (9.2, 14.8):
        _linea(p, (v, 3.5), (v, 20.5))
        _linea(p, (3.5, v), (20.5, v))


@_registro('apariencia')
def _(p, c):
    p.drawEllipse(QPointF(12, 12), 8.5, 8.5)
    camino = QPainterPath()
    camino.moveTo(12, 3.5)
    camino.arcTo(QRectF(3.5, 3.5, 17, 17), 90, -180)
    camino.closeSubpath()
    p.fillPath(camino, c)


def _dibujar_desconocido(p, c):
    p.drawEllipse(QPointF(12, 12), 7, 7)


def nombres() -> list[str]:
    return sorted(_DIBUJOS)


def dibujar(p: QPainter, rect: QRectF, nombre: str, color: QColor,
            insignia: str | None = None, grosor: float | None = None) -> None:
    """Pinta el icono `nombre` centrado en `rect` con el color indicado."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    lado = min(rect.width(), rect.height())
    centro = rect.center()
    if insignia is not None:
        caja = QRectF(centro.x() - lado / 2, centro.y() - lado / 2, lado, lado)
        base = QColor(insignia)
        gradiente = QLinearGradient(caja.topLeft(), caja.bottomLeft())
        gradiente.setColorAt(0, base.lighter(115))
        gradiente.setColorAt(1, base.darker(103))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(gradiente)
        p.drawRoundedRect(caja, lado * 0.25, lado * 0.25)
        lado *= 0.68
        color = QColor('#FFFFFF')
        grosor = grosor or 2.1
    escala = lado / 24.0
    p.translate(centro.x() - 12 * escala, centro.y() - 12 * escala)
    p.scale(escala, escala)
    if grosor is None:
        grosor = 1.65 if lado >= 22 else (1.8 if lado >= 16 else 2.0)
    pluma = QPen(color, grosor, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                 Qt.PenJoinStyle.RoundJoin)
    p.setPen(pluma)
    p.setBrush(Qt.BrushStyle.NoBrush)
    _DIBUJOS.get(nombre, _dibujar_desconocido)(p, color)
    p.restore()


def _escala_pantalla() -> float:
    app = QGuiApplication.instance()
    try:
        return float(app.devicePixelRatio()) if app else 1.0
    except Exception:
        return 1.0


class MotorIcono(QIconEngine):
    """Motor que redibuja el icono con el color del tema vigente."""

    def __init__(self, nombre: str, rol: str = 'texto', insignia: str | None = None,
                 rol_activo: str | None = None):
        super().__init__()
        self.nombre = nombre
        self.rol = rol
        self.insignia = insignia
        self.rol_activo = rol_activo
        self._cache: dict = {}
        self._generacion = -1

    def clone(self):
        return MotorIcono(self.nombre, self.rol, self.insignia, self.rol_activo)

    def iconName(self):
        return self.nombre

    def _color(self, modo, estado) -> QColor:
        t = tema()
        if modo == QIcon.Mode.Disabled and self.insignia is None:
            return t.color('texto3')
        if estado == QIcon.State.On and self.rol_activo:
            return t.color(self.rol_activo)
        return t.color(self.rol)

    def paint(self, painter, rect, modo, estado):
        color = self._color(modo, estado)
        painter.save()
        if modo == QIcon.Mode.Disabled and self.insignia is not None:
            painter.setOpacity(0.38)
        dibujar(painter, QRectF(rect), self.nombre, color, self.insignia)
        painter.restore()

    def pixmap(self, size, modo, estado):
        return self.scaledPixmap(size, modo, estado, _escala_pantalla())

    def scaledPixmap(self, size, modo, estado, escala):
        t = tema()
        if self._generacion != t.generacion:
            self._cache.clear()
            self._generacion = t.generacion
        escala = float(escala or 1.0)
        clave = (size.width(), size.height(), modo, estado, round(escala, 3))
        pm = self._cache.get(clave)
        if pm is None:
            w = max(1, math.ceil(size.width() * escala))
            h = max(1, math.ceil(size.height() * escala))
            pm = QPixmap(w, h)
            pm.fill(Qt.GlobalColor.transparent)
            pintor = QPainter(pm)
            self.paint(pintor, QRect(0, 0, w, h), modo, estado)
            pintor.end()
            pm.setDevicePixelRatio(escala)
            self._cache[clave] = pm
        return pm


_CACHE_ICONOS: dict = {}


def icono(nombre: str, rol: str = 'texto', rol_activo: str | None = None) -> QIcon:
    clave = (nombre, rol, rol_activo, None)
    if clave not in _CACHE_ICONOS:
        _CACHE_ICONOS[clave] = QIcon(MotorIcono(nombre, rol, None, rol_activo))
    return _CACHE_ICONOS[clave]


def icono_insignia(nombre: str, color: str) -> QIcon:
    clave = (nombre, None, None, color)
    if clave not in _CACHE_ICONOS:
        _CACHE_ICONOS[clave] = QIcon(MotorIcono(nombre, 'texto', color))
    return _CACHE_ICONOS[clave]


def pixmap(nombre: str, lado: int, rol: str = 'texto', insignia: str | None = None) -> QPixmap:
    ic = icono_insignia(nombre, insignia) if insignia else icono(nombre, rol)
    return ic.pixmap(QSize(lado, lado))


def _dibujar_app(p: QPainter, lado: float) -> None:
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    margen = lado * 0.06
    caja = QRectF(margen, margen, lado - 2 * margen, lado - 2 * margen)
    radio = caja.width() * 0.225
    gradiente = QLinearGradient(caja.topLeft(), caja.bottomRight())
    gradiente.setColorAt(0.0, QColor('#40A9FF'))
    gradiente.setColorAt(0.55, QColor('#2F6BFF'))
    gradiente.setColorAt(1.0, QColor('#5E3CE6'))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(gradiente)
    p.drawRoundedRect(caja, radio, radio)
    brillo = QRadialGradient(caja.left() + caja.width() * 0.3, caja.top() + caja.height() * 0.2,
                             caja.width() * 0.8)
    brillo.setColorAt(0, QColor(255, 255, 255, 70))
    brillo.setColorAt(1, QColor(255, 255, 255, 0))
    p.setBrush(brillo)
    p.drawRoundedRect(caja, radio, radio)
    u = caja.width() / 24.0
    p.save()
    p.translate(caja.left(), caja.top())
    p.scale(u, u)
    blanco = QColor('#FFFFFF')
    centro, radio_lente = QPointF(10.6, 10.4), 6.6
    # Lupa sobre una red de límites de grano: «micro» y «grano».
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 255, 255, 46))
    p.drawEllipse(centro, radio_lente, radio_lente)
    lente = QPainterPath()
    lente.addEllipse(centro, radio_lente - 0.4, radio_lente - 0.4)
    p.save()
    p.setClipPath(lente)
    p.setPen(QPen(QColor(255, 255, 255, 215), 1.05, Qt.PenStyle.SolidLine,
                  Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    j1, j2, j3 = (9.3, 8.4), (13.2, 11.2), (8.8, 13.2)
    for a, b in ((j1, (9.6, 2.0)), (j1, (2.5, 9.0)), (j1, j2), (j2, (19.0, 8.0)),
                 (j1, j3), (j3, (2.5, 16.0)), (j3, (11.0, 19.0)), (j2, (14.5, 19.0))):
        _linea(p, a, b)
    p.restore()
    p.setPen(QPen(blanco, 1.75, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                  Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(centro, radio_lente, radio_lente)
    p.setPen(QPen(blanco, 2.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    _linea(p, (15.5, 15.3), (20.2, 20.0))
    p.restore()


def pixmap_app(lado: int) -> QPixmap:
    escala = _escala_pantalla()
    pm = QPixmap(max(1, round(lado * escala)), max(1, round(lado * escala)))
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    _dibujar_app(p, pm.width())
    p.end()
    pm.setDevicePixelRatio(escala)
    return pm


def icono_app() -> QIcon:
    ic = QIcon()
    for lado in (16, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(lado, lado)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        _dibujar_app(p, lado)
        p.end()
        ic.addPixmap(pm)
    return ic
