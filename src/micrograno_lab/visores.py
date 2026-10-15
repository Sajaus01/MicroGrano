"""Visores, tabla y gráficas de la interfaz. Solo representan datos; no los analizan.

La conversión a colores de pantalla (`componer_vista`) nunca modifica los arreglos de
la sesión: produce una copia de 8 bits exclusivamente para mostrarla.
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd
from PySide6.QtCore import (QAbstractTableModel, QEvent, QModelIndex, QPointF, QRectF,
                            QSortFilterProxyModel, Qt, Signal)
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetricsF, QGuiApplication, QImage,
                           QPainter, QPainterPath, QPen, QPixmap, QTransform)
from PySide6.QtWidgets import (QFileDialog, QFrame, QGraphicsItem, QGraphicsLineItem,
                               QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsRectItem,
                               QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel,
                               QSizePolicy, QVBoxLayout, QWidget)
from . import iconos
from .componentes import BotonIcono, EstadoVacio, Selector, etiqueta
from .tema import rc_matplotlib, tema
from .textos import etiqueta_columna

OPCIONES_VISTA = {'colores': True, 'estirar': False, 'color_contorno': '#FFD60A'}
COLORES_CONTORNO = (('Amarillo', '#FFD60A'), ('Cian', '#64D2FF'), ('Magenta', '#FF2D96'),
                    ('Verde', '#30D158'), ('Blanco', '#FFFFFF'), ('Negro', '#000000'))


# ---------------------------------------------------------------------------
# Composición de la vista (NumPy puro, comprobable sin Qt)
# ---------------------------------------------------------------------------

def _lut(nombre: str, n: int = 256) -> np.ndarray:
    from matplotlib import colormaps
    return (colormaps[nombre](np.linspace(0, 1, n))[:, :3] * 255).round().astype(np.uint8)


def _hsv_a_rgb(h, s, v) -> np.ndarray:
    i = np.floor(h * 6).astype(int) % 6
    f = h * 6 - np.floor(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return (np.stack([r, g, b], axis=-1) * 255).round().astype(np.uint8)


def colores_identificadores(ids: np.ndarray) -> np.ndarray:
    """Color estable por identificador (ángulo áureo); el 0 (fondo) es negro."""
    ids = np.asarray(ids, dtype=np.int64)
    h = (ids * 0.6180339887498949 + 0.12) % 1.0
    s = 0.55 + 0.25 * ((ids * 0.37) % 1.0)
    v = 0.92 - 0.12 * ((ids * 0.53) % 1.0)
    colores = _hsv_a_rgb(h, s, v)
    colores[ids == 0] = (0, 0, 0)
    return colores


def _unidad_vista(a: np.ndarray) -> np.ndarray:
    """Intervalo [0, 1] para mostrar: enteros por su tipo y flotantes ya normalizados."""
    if a.dtype.kind == 'b':
        return a.astype(np.float32)
    if a.dtype.kind == 'u':
        return a.astype(np.float32) / np.iinfo(a.dtype).max
    if a.dtype.kind == 'f':
        return np.clip(np.nan_to_num(a.astype(np.float32)), 0, 1)
    lo, hi = float(a.min()), float(a.max())
    return ((a - lo) / (hi - lo)).astype(np.float32) if hi > lo else np.zeros(a.shape, np.float32)


def _estirar(u: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(u, [0.5, 99.5])
    return np.clip((u - lo) / (hi - lo), 0, 1) if hi > lo else u


def componer_vista(vista: dict, opciones: dict | None = None, original: np.ndarray | None = None,
                   tipo_original: str | None = None) -> dict:
    """Convierte la vista de `preparar_vista` en RGB de 8 bits y una capa de contornos."""
    o = {**OPCIONES_VISTA, **(opciones or {})}
    a = np.asarray(vista['imagen'])
    tipo = vista.get('tipo', 'gris')
    info = ''
    if a.ndim == 3:
        rgb = a[..., :3]
        if rgb.dtype == np.uint8:
            salida = rgb.copy()
        elif rgb.dtype.kind == 'b':
            salida = rgb.astype(np.uint8) * 255
        else:
            u = _unidad_vista(rgb)
            if o['estirar']:
                u = _estirar(u)
                info = 'Contraste de la vista estirado; los datos no cambian.'
            salida = (u * 255).round().astype(np.uint8)
        if o['estirar'] and rgb.dtype == np.uint8:
            salida = (_estirar(rgb.astype(np.float32) / 255) * 255).round().astype(np.uint8)
            info = 'Contraste de la vista estirado; los datos no cambian.'
    elif a.ndim == 2:
        if tipo in ('etiquetas', 'marcadores') and o['colores']:
            ids, inversa = np.unique(a, return_inverse=True)
            salida = colores_identificadores(ids)[inversa.reshape(a.shape)]
        elif tipo == 'clases' and o['colores']:
            k = max(int(a.max()) + 1, 2)
            paleta = _lut('viridis', 256)[np.linspace(10, 245, k).round().astype(int)]
            salida = paleta[np.clip(a, 0, k - 1)]
            info = 'Color por clase: del tono oscuro (clase 0) al claro.'
        elif tipo in ('mascara', 'limites') or a.dtype.kind == 'b':
            g = a.astype(bool).astype(np.uint8) * 255
            salida = np.repeat(g[..., None], 3, axis=2)
        elif tipo == 'mapa':
            v = a.astype(np.float64)
            finitos = v[np.isfinite(v)]
            lo, hi = (float(finitos.min()), float(finitos.max())) if finitos.size else (0.0, 0.0)
            if lo < 0 < hi:
                m = max(-lo, hi)
                u = np.clip((np.nan_to_num(v) / m + 1) / 2, 0, 1)
                salida = _lut('RdBu_r')[(u * 255).round().astype(int)]
                info = f'Mapa con signo: azul negativo, rojo positivo (±{m:.4g}).'
            else:
                u = (np.nan_to_num(v) - lo) / (hi - lo) if hi > lo else np.zeros_like(v)
                g = (np.clip(u, 0, 1) * 255).round().astype(np.uint8)
                salida = np.repeat(g[..., None], 3, axis=2)
                info = f'Vista escalada entre {lo:.4g} y {hi:.4g}.'
        elif tipo in ('etiquetas', 'marcadores', 'clases'):
            m = float(a.max())
            g = (a / m * 255).round().astype(np.uint8) if m > 0 else np.zeros(a.shape, np.uint8)
            salida = np.repeat(g[..., None], 3, axis=2)
        else:
            u = _unidad_vista(a)
            if o['estirar']:
                u = _estirar(u)
                info = 'Contraste de la vista estirado; los datos no cambian.'
            g = (u * 255).round().astype(np.uint8)
            salida = np.repeat(g[..., None], 3, axis=2)
    else:
        raise ValueError('Solo se muestran arreglos 2D o RGB.')
    capa = None
    b = vista.get('contornos')
    if b is not None:
        b = np.asarray(b, dtype=bool)
        if b.any() and not b.all():
            color = QColor(o['color_contorno'])
            capa = np.zeros(b.shape + (4,), np.uint8)
            capa[b] = (color.red(), color.green(), color.blue(), 255)
    puntos = []
    fuente = original if original is not None else a
    if (tipo_original or tipo) == 'marcadores' and fuente.ndim == 2:
        rr, cc = np.nonzero(fuente)
        if 0 < len(rr) <= 200_000:
            ids = fuente[rr, cc].astype(np.int64)
            unicos, inversa = np.unique(ids, return_inverse=True)
            if len(unicos) <= 5000:
                n = np.bincount(inversa)
                filas = np.bincount(inversa, rr) / n
                columnas = np.bincount(inversa, cc) / n
                puntos = [(float(c), float(r), int(i)) for r, c, i in zip(filas, columnas, unicos)]
    return {'rgb': np.ascontiguousarray(salida), 'capa': capa, 'info': info, 'puntos': puntos}


def a_qimage(arreglo: np.ndarray) -> QImage:
    a = np.ascontiguousarray(arreglo)
    h, w = a.shape[:2]
    if a.ndim == 2:
        img = QImage(a.data, w, h, w, QImage.Format.Format_Grayscale8)
    elif a.shape[2] == 3:
        img = QImage(a.data, w, h, 3 * w, QImage.Format.Format_RGB888)
    else:
        img = QImage(a.data, w, h, 4 * w, QImage.Format.Format_RGBA8888)
    return img.copy()


def miniatura(vista: dict, lado: int = 64, original=None, tipo_original=None) -> QPixmap:
    """Miniatura cuadrada con relleno, para listas y la tira de salidas."""
    a = np.asarray(vista['imagen'])
    app = QGuiApplication.instance()
    dpr = float(app.devicePixelRatio()) if app is not None else 1.0
    lado_px = max(8, round(lado * dpr))
    if a.ndim == 1:
        pm = QPixmap(lado_px, lado_px)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        iconos.dibujar(p, QRectF(0, 0, lado_px, lado_px), 'histograma', tema().color('texto2'))
        p.end()
        pm.setDevicePixelRatio(dpr)
        return pm
    paso = max(1, int(max(a.shape[0], a.shape[1]) // (lado_px * 2)))
    reducida = dict(vista)
    reducida['imagen'] = a[::paso, ::paso]
    if vista.get('contornos') is not None:
        reducida['contornos'] = np.asarray(vista['contornos'])[::paso, ::paso]
    orig = original[::paso, ::paso] if original is not None and original.ndim >= 2 else None
    compuesta = componer_vista(reducida, original=orig, tipo_original=tipo_original)
    img = a_qimage(compuesta['rgb'])
    if compuesta['capa'] is not None or compuesta['puntos']:
        p = QPainter(img)
        if compuesta['capa'] is not None:
            p.drawImage(0, 0, a_qimage(compuesta['capa']))
        if compuesta['puntos']:
            # Los marcadores de un píxel serían invisibles en miniatura: se dibujan como puntos.
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            radio = max(1.5, max(img.width(), img.height()) / 22)
            colores = colores_identificadores(np.array([i for _, _, i in compuesta['puntos']]))
            for (x, y, _), color in zip(compuesta['puntos'], colores):
                p.setPen(QPen(QColor('#FFFFFF'), max(1.0, radio / 3)))
                p.setBrush(QColor(*[int(v) for v in color]))
                p.drawEllipse(QPointF(x + 0.5, y + 0.5), radio, radio)
        p.end()
    img = img.scaled(lado_px, lado_px, Qt.AspectRatioMode.KeepAspectRatio,
                     Qt.TransformationMode.SmoothTransformation)
    pm = QPixmap(lado_px, lado_px)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    camino = QPainterPath()
    caja = QRectF((lado_px - img.width()) / 2, (lado_px - img.height()) / 2, img.width(), img.height())
    camino.addRoundedRect(caja, 4 * dpr, 4 * dpr)
    p.setClipPath(camino)
    p.drawImage(caja.topLeft(), img)
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


# ---------------------------------------------------------------------------
# Elementos gráficos auxiliares
# ---------------------------------------------------------------------------

class _Pildora(QGraphicsItem):
    """Texto sobre fondo translúcido que conserva su tamaño con cualquier zoom."""

    def __init__(self, texto: str = ''):
        super().__init__()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self._texto = texto
        self._fuente = QFont()
        self._fuente.setPointSizeF(8.5)
        self._fuente.setWeight(QFont.Weight.DemiBold)

    def establecer(self, texto: str) -> None:
        self.prepareGeometryChange()
        self._texto = texto
        self.update()

    def _caja(self) -> QRectF:
        m = QFontMetricsF(self._fuente)
        w = m.horizontalAdvance(self._texto) + 14
        h = m.height() + 6
        return QRectF(8, -h - 8, w, h)

    def boundingRect(self):
        return self._caja().adjusted(-1, -1, 1, 1)

    def paint(self, p, opcion, widget=None):
        if not self._texto:
            return
        caja = self._caja()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(28, 28, 30, 215))
        p.drawRoundedRect(caja, caja.height() / 2, caja.height() / 2)
        p.setPen(QColor('#FFFFFF'))
        p.setFont(self._fuente)
        p.drawText(caja, Qt.AlignmentFlag.AlignCenter, self._texto)


class _Rotulo(QGraphicsItem):
    """Identificador de objeto con contorno oscuro para leerse sobre cualquier fondo."""

    def __init__(self, texto: str):
        super().__init__()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        f = QFont()
        f.setPointSizeF(9)
        f.setWeight(QFont.Weight.Bold)
        self._camino = QPainterPath()
        self._camino.addText(0, 0, f, texto)
        r = self._camino.boundingRect()
        self._camino.translate(-r.center())

    def boundingRect(self):
        return self._camino.boundingRect().adjusted(-3, -3, 3, 3)

    def paint(self, p, opcion, widget=None):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(0, 0, 0, 200), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                      Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(self._camino)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#FFFFFF'))
        p.drawPath(self._camino)


class _Punto(QGraphicsItem):
    def __init__(self, color: QColor, radio: float = 4.5):
        super().__init__()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self._color, self._r = color, radio

    def boundingRect(self):
        r = self._r + 2
        return QRectF(-r, -r, 2 * r, 2 * r)

    def paint(self, p, opcion, widget=None):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor('#FFFFFF'), 1.6))
        p.setBrush(self._color)
        p.drawEllipse(QPointF(0, 0), self._r, self._r)


class _Perilla(QGraphicsItem):
    """Asa circular de la cortina de comparación."""

    def __init__(self):
        super().__init__()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)

    def boundingRect(self):
        return QRectF(-16, -16, 32, 32)

    def paint(self, p, opcion, widget=None):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 60))
        p.drawEllipse(QPointF(0, 1), 14, 14)
        p.setBrush(QColor('#FFFFFF'))
        p.drawEllipse(QPointF(0, 0), 13, 13)
        p.setPen(QPen(QColor('#1D1D1F'), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                      Qt.PenJoinStyle.RoundJoin))
        for s in (-1, 1):
            p.drawPolyline([QPointF(s * 2.5, -4), QPointF(s * 6.5, 0), QPointF(s * 2.5, 4)])


# ---------------------------------------------------------------------------
# Visor de imágenes
# ---------------------------------------------------------------------------

class VisorImagen(QGraphicsView):
    """Visor con zoom, paneo, ROI, regla, perfil y comparación de cortina."""
    roi_elegida = Signal(int, int, int, int)
    linea_elegida = Signal(float, float, float, float)
    pixel = Signal(str)
    zoom_cambiado = Signal(float)
    vista_cambiada = Signal()
    herramienta_cambiada = Signal(str)

    ZOOM_MAX = 64.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.escena = QGraphicsScene(self)
        self.setScene(self.escena)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setMinimumSize(160, 120)
        self._item = QGraphicsPixmapItem()
        self._item.setShapeMode(QGraphicsPixmapItem.ShapeMode.BoundingRectShape)
        self.escena.addItem(self._item)
        self._recorte_b = QGraphicsRectItem()
        self._recorte_b.setPen(Qt.PenStyle.NoPen)
        self._recorte_b.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape)
        self._recorte_b.setZValue(1)
        self._item_b = QGraphicsPixmapItem(self._recorte_b)
        self.escena.addItem(self._recorte_b)
        self._recorte_b.hide()
        self._capa = QGraphicsPixmapItem()
        self._capa.setZValue(2)
        self.escena.addItem(self._capa)
        self._capa_b = QGraphicsPixmapItem(self._recorte_b)
        self._capa_b.setZValue(1)
        self._resalte = QGraphicsPixmapItem()
        self._resalte.setZValue(3)
        self.escena.addItem(self._resalte)
        self._decoraciones: list[QGraphicsItem] = []
        self._velo = QGraphicsPathItem()
        self._velo.setPen(Qt.PenStyle.NoPen)
        self._velo.setBrush(QColor(0, 0, 0, 115))
        self._velo.setZValue(5)
        self.escena.addItem(self._velo)
        self._marco_roi = QGraphicsRectItem()
        self._marco_roi.setZValue(6)
        self.escena.addItem(self._marco_roi)
        self._etiqueta_roi = _Pildora()
        self._etiqueta_roi.setZValue(8)
        self.escena.addItem(self._etiqueta_roi)
        self._linea = QGraphicsLineItem()
        self._linea.setZValue(6)
        self.escena.addItem(self._linea)
        self._extremos = [_Punto(QColor('#0A84FF'), 4), _Punto(QColor('#0A84FF'), 4)]
        for e in self._extremos:
            e.setZValue(7)
            self.escena.addItem(e)
        self._etiqueta_linea = _Pildora()
        self._etiqueta_linea.setZValue(8)
        self.escena.addItem(self._etiqueta_linea)
        self._division = QGraphicsLineItem()
        self._division.setZValue(9)
        self.escena.addItem(self._division)
        self._perilla = _Perilla()
        self._perilla.setZValue(10)
        self.escena.addItem(self._perilla)
        self._ocultar_dibujos()
        self._division.hide()
        self._perilla.hide()
        self._datos = None
        self._tipo = None
        self._forma = None
        self._ajuste_auto = True
        self._herramienta = 'mover'
        self._roi_inicio = None
        self._linea_inicio = None
        self._linea_activa = False
        self._esperando_fin = False
        self._cortina = False
        self._division_x = 0.0
        self._arrastrando_division = False
        self._aplicando_estado = False
        self.escala_um = None
        self._crear_hud()
        self.horizontalScrollBar().valueChanged.connect(self._vista_movida)
        self.verticalScrollBar().valueChanged.connect(self._vista_movida)
        tema().cambiado.connect(self._tema_cambiado)
        self._tema_cambiado()
        self.limpiar('Sin imagen', 'Abra una imagen o cargue el conjunto sintético.')

    # -- interfaz pública --------------------------------------------------

    @property
    def arreglo(self):
        return self._datos

    @arreglo.setter
    def arreglo(self, valor):
        self._datos = valor

    def escala(self) -> float:
        return self.transform().m11()

    def mostrar(self, vista: dict, titulo: str = '', original=None, tipo_original=None,
                opciones: dict | None = None, conservar_vista: bool = False) -> dict:
        """Muestra una vista preparada; conserva zoom y centro si la forma coincide."""
        compuesta = componer_vista(vista, opciones, original, tipo_original)
        datos = original if original is not None else np.asarray(vista['imagen'])
        forma_nueva = compuesta['rgb'].shape[:2]
        mantener = conservar_vista and self._forma == forma_nueva and self._datos is not None
        estado = self.estado_vista() if mantener else None
        self._vacio.hide()
        self._datos = datos
        self._tipo = tipo_original or vista.get('tipo')
        self._forma = forma_nueva
        self._item.setPixmap(QPixmap.fromImage(a_qimage(compuesta['rgb'])))
        self._capa.setPixmap(QPixmap.fromImage(a_qimage(compuesta['capa'])) if compuesta['capa'] is not None else QPixmap())
        self._resalte.setPixmap(QPixmap())
        self._limpiar_decoraciones()
        for x, y, texto in vista.get('rotulos', []):
            r = _Rotulo(str(texto))
            r.setPos(x + 0.5, y + 0.5)
            r.setZValue(4)
            self.escena.addItem(r)
            self._decoraciones.append(r)
        if compuesta['puntos']:
            colores = colores_identificadores(np.array([i for _, _, i in compuesta['puntos']]))
            for (x, y, _), color in zip(compuesta['puntos'], colores):
                pt = _Punto(QColor(*[int(v) for v in color]))
                pt.setPos(x + 0.5, y + 0.5)
                pt.setZValue(4)
                self.escena.addItem(pt)
                self._decoraciones.append(pt)
        h, w = forma_nueva
        self.escena.setSceneRect(QRectF(-w * 0.5, -h * 0.5, w * 2, h * 2))
        self._recorte_b.setRect(QRectF(0, 0, w, h))
        self.quitar_cortina()
        self._ocultar_dibujos()
        self._textos_hud['titulo'] = titulo
        self._hud_titulo.setVisible(bool(titulo))
        nota = vista.get('nota', '')
        if nota.startswith('Vista;'):
            nota = ''  # Aviso genérico: no se repite en cada imagen.
        nota = ' '.join(x for x in (compuesta['info'], nota) if x)
        self._textos_hud['nota'] = nota
        self._hud_nota.setVisible(bool(nota))
        self._hud_nota.setToolTip(nota)
        if estado is not None:
            self.aplicar_estado(estado)
        else:
            self.ajustar()
        self._actualizar_suavizado()
        self._colocar_hud()
        return compuesta

    def limpiar(self, titulo: str = 'Sin imagen', texto: str = '', icono: str = 'dato') -> None:
        self._datos = None
        self._forma = None
        self._tipo = None
        self._item.setPixmap(QPixmap())
        self._capa.setPixmap(QPixmap())
        self._resalte.setPixmap(QPixmap())
        self._limpiar_decoraciones()
        self.quitar_cortina()
        self._ocultar_dibujos()
        self._hud_titulo.hide()
        self._hud_nota.hide()
        self._hud_info.hide()
        self._hud_zoom.hide()
        self._vacio.establecer(titulo, texto, icono)
        self._vacio.show()
        self._vacio.raise_()
        self._colocar_hud()

    def estado_vacio(self) -> EstadoVacio:
        return self._vacio

    def mostrar_cortina(self, vista_b: dict, opciones=None, original=None, tipo_original=None,
                        titulo_b: str = '') -> bool:
        if self._forma is None:
            return False
        compuesta = componer_vista(vista_b, opciones, original, tipo_original)
        if compuesta['rgb'].shape[:2] != self._forma:
            return False
        h, w = self._forma
        self._item_b.setPixmap(QPixmap.fromImage(a_qimage(compuesta['rgb'])))
        self._capa_b.setPixmap(QPixmap.fromImage(a_qimage(compuesta['capa'])) if compuesta['capa'] is not None else QPixmap())
        self._cortina = True
        self._recorte_b.show()
        self._division.show()
        self._perilla.show()
        self._textos_hud['derecha'] = titulo_b
        self._hud_derecha.setVisible(bool(titulo_b))
        self._mover_division(w / 2)
        self._colocar_hud()
        return True

    def quitar_cortina(self) -> None:
        self._cortina = False
        self._recorte_b.hide()
        self._division.hide()
        self._perilla.hide()
        if hasattr(self, '_hud_derecha'):
            self._hud_derecha.hide()

    def establecer_herramienta(self, nombre: str) -> None:
        if nombre not in ('mover', 'roi', 'linea'):
            raise ValueError('Herramienta desconocida.')
        self._herramienta = nombre
        self._roi_inicio = None
        self._linea_activa = False
        self._esperando_fin = False
        if nombre == 'mover':
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.viewport().unsetCursor()
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        self.herramienta_cambiada.emit(nombre)

    def herramienta(self) -> str:
        return self._herramienta

    # Compatibilidad con la API anterior de los visores.
    def seleccionar_roi(self):
        if self._datos is not None and np.ndim(self._datos) >= 2:
            self.establecer_herramienta('roi')

    def seleccionar_linea(self):
        if self._datos is not None and np.ndim(self._datos) >= 2:
            self.establecer_herramienta('linea')

    def mostrar_roi(self, r0, r1, c0, c1) -> None:
        if self._forma is None:
            return
        h, w = self._forma
        r0, r1 = sorted((max(0, min(h, r0)), max(0, min(h, r1))))
        c0, c1 = sorted((max(0, min(w, c0)), max(0, min(w, c1))))
        if r1 <= r0 or c1 <= c0:
            self._velo.hide()
            self._marco_roi.hide()
            self._etiqueta_roi.hide()
            return
        camino = QPainterPath()
        camino.setFillRule(Qt.FillRule.OddEvenFill)
        camino.addRect(QRectF(0, 0, w, h))
        camino.addRect(QRectF(c0, r0, c1 - c0, r1 - r0))
        self._velo.setPath(camino)
        self._velo.show()
        self._marco_roi.setRect(QRectF(c0, r0, c1 - c0, r1 - r0))
        self._marco_roi.show()
        self._etiqueta_roi.establecer(f'{c1 - c0} × {r1 - r0} px')
        self._etiqueta_roi.setPos(c0, r0)
        self._etiqueta_roi.show()

    def mostrar_linea(self, r0, c0, r1, c1) -> None:
        if self._forma is None:
            return
        a, b = QPointF(c0 + 0.5, r0 + 0.5), QPointF(c1 + 0.5, r1 + 0.5)
        self._linea.setLine(a.x(), a.y(), b.x(), b.y())
        self._linea.show()
        for e, pt in zip(self._extremos, (a, b)):
            e.setPos(pt)
            e.show()
        self._etiqueta_linea.establecer(self._texto_longitud(math.hypot(r1 - r0, c1 - c0)))
        self._etiqueta_linea.setPos(b)
        self._etiqueta_linea.show()

    def ocultar_dibujos(self) -> None:
        self._ocultar_dibujos()

    def resaltar(self, mascara: np.ndarray | None, centrar: bool = True) -> None:
        if mascara is None or self._forma is None or mascara.shape != self._forma:
            self._resalte.setPixmap(QPixmap())
            return
        m = np.asarray(mascara, dtype=bool)
        if not m.any():
            self._resalte.setPixmap(QPixmap())
            return
        interior = m.copy()
        interior[1:, :] &= m[:-1, :]
        interior[:-1, :] &= m[1:, :]
        interior[:, 1:] &= m[:, :-1]
        interior[:, :-1] &= m[:, 1:]
        borde = m & ~interior
        acento = tema().color('acento')
        capa = np.zeros(m.shape + (4,), np.uint8)
        capa[m] = (acento.red(), acento.green(), acento.blue(), 80)
        capa[borde] = (255, 255, 255, 255)
        self._resalte.setPixmap(QPixmap.fromImage(a_qimage(capa)))
        if centrar:
            filas, columnas = np.nonzero(m)
            caja = QRectF(columnas.min(), filas.min(), columnas.max() - columnas.min() + 1,
                          filas.max() - filas.min() + 1)
            visible = self.mapToScene(self.viewport().rect()).boundingRect()
            if not visible.contains(caja):
                self.centerOn(caja.center())
            self.vista_cambiada.emit()

    def ajustar(self) -> None:
        if self._forma is None:
            return
        h, w = self._forma
        area = self.viewport().rect()
        if area.width() < 4 or area.height() < 4:
            return
        s = min((area.width() - 24) / w, (area.height() - 24) / h)
        s = max(min(s, self.ZOOM_MAX), 1e-3)
        self.setTransform(QTransform.fromScale(s, s))
        self.centerOn(QPointF(w / 2, h / 2))
        self._ajuste_auto = True
        self._tras_zoom()

    def zoom_100(self) -> None:
        self._establecer_escala(1.0)

    def acercar(self) -> None:
        self._zoom_por(1.25, centro=True)

    def alejar(self) -> None:
        self._zoom_por(0.8, centro=True)

    def estado_vista(self):
        centro = self.mapToScene(self.viewport().rect().center())
        return {'escala': self.escala(), 'centro': centro, 'auto': self._ajuste_auto}

    def aplicar_estado(self, estado) -> None:
        if self._forma is None or estado is None:
            return
        self._aplicando_estado = True
        try:
            s = estado['escala']
            self.setTransform(QTransform.fromScale(s, s))
            self.centerOn(estado['centro'])
            self._ajuste_auto = estado.get('auto', False)
        finally:
            self._aplicando_estado = False
        self._actualizar_suavizado()
        self._actualizar_hud_zoom()

    # -- eventos -----------------------------------------------------------

    def wheelEvent(self, evento):
        if self._forma is None:
            return
        angulo = evento.angleDelta().y()
        es_panel_tactil = not evento.pixelDelta().isNull()
        ctrl = bool(evento.modifiers() & Qt.KeyboardModifier.ControlModifier)
        if angulo == 0 or (es_panel_tactil and not ctrl):
            # Desplazamiento con dos dedos: mover; la rueda del ratón: acercar.
            super().wheelEvent(evento)
            self._ajuste_auto = False
            return
        self._zoom_por(1.0015 ** angulo)

    def viewportEvent(self, evento):
        if evento.type() == QEvent.Type.NativeGesture and self._forma is not None:
            if evento.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
                self._zoom_por(1.0 + evento.value())
                return True
            if evento.gestureType() == Qt.NativeGestureType.SmartZoomNativeGesture:
                self.ajustar()
                return True
        return super().viewportEvent(evento)

    def mousePressEvent(self, evento):
        if self._forma is None or evento.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(evento)
            return
        p = self.mapToScene(evento.position().toPoint())
        if self._cortina and self._herramienta == 'mover':
            x_vista = self.mapFromScene(QPointF(self._division_x, 0)).x()
            if abs(evento.position().x() - x_vista) < 22:
                self._arrastrando_division = True
                self.viewport().setCursor(Qt.CursorShape.SplitHCursor)
                return
        if self._herramienta == 'roi':
            self._roi_inicio = self._ajustar_borde(p)
            self.mostrar_roi(self._roi_inicio.y(), self._roi_inicio.y(),
                             self._roi_inicio.x(), self._roi_inicio.x())
            return
        if self._herramienta == 'linea':
            q = self._ajustar_centro(p)
            if self._esperando_fin:
                self._terminar_linea(q)
            else:
                self._linea_inicio = q
                self._linea_activa = True
                self._dibujar_linea_temporal(q)
            return
        super().mousePressEvent(evento)

    def mouseMoveEvent(self, evento):
        p = self.mapToScene(evento.position().toPoint())
        self._informar_pixel(p)
        if self._arrastrando_division:
            self._mover_division(p.x())
            return
        if self._roi_inicio is not None:
            fin = self._ajustar_borde(p)
            self.mostrar_roi(self._roi_inicio.y(), fin.y(), self._roi_inicio.x(), fin.x())
            return
        if self._linea_activa or self._esperando_fin:
            self._dibujar_linea_temporal(self._ajustar_centro(p))
            return
        if self._cortina and self._herramienta == 'mover':
            x_vista = self.mapFromScene(QPointF(self._division_x, 0)).x()
            if abs(evento.position().x() - x_vista) < 22:
                self.viewport().setCursor(Qt.CursorShape.SplitHCursor)
            else:
                self.viewport().unsetCursor()
        super().mouseMoveEvent(evento)

    def mouseReleaseEvent(self, evento):
        if self._arrastrando_division:
            self._arrastrando_division = False
            self.viewport().unsetCursor()
            return
        if self._roi_inicio is not None and evento.button() == Qt.MouseButton.LeftButton:
            fin = self._ajustar_borde(self.mapToScene(evento.position().toPoint()))
            inicio = self._roi_inicio
            self._roi_inicio = None
            r0, r1 = sorted((int(round(inicio.y())), int(round(fin.y()))))
            c0, c1 = sorted((int(round(inicio.x())), int(round(fin.x()))))
            if r1 > r0 and c1 > c0:
                self.mostrar_roi(r0, r1, c0, c1)
                self.roi_elegida.emit(r0, r1, c0, c1)
            else:
                self._ocultar_roi()
            return
        if self._linea_activa and evento.button() == Qt.MouseButton.LeftButton:
            q = self._ajustar_centro(self.mapToScene(evento.position().toPoint()))
            if math.hypot(q.x() - self._linea_inicio.x(), q.y() - self._linea_inicio.y()) < 1.0:
                self._linea_activa = False
                self._esperando_fin = True
            else:
                self._terminar_linea(q)
            return
        super().mouseReleaseEvent(evento)

    def mouseDoubleClickEvent(self, evento):
        if self._herramienta == 'mover' and self._forma is not None:
            self.ajustar()
            return
        super().mouseDoubleClickEvent(evento)

    def leaveEvent(self, evento):
        self._hud_info.hide()
        super().leaveEvent(evento)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if self._ajuste_auto and self._forma is not None:
            self.ajustar()
        self._colocar_hud()

    def drawBackground(self, p, rect):
        p.fillRect(rect, tema().color('lienzo'))
        if self._forma is not None:
            h, w = self._forma
            p.save()
            p.setPen(Qt.PenStyle.NoPen)
            sombra = QColor(0, 0, 0, 70 if tema().oscuro else 38)
            s = 1 / max(self.escala(), 1e-6)
            for k, alfa in ((6, 0.25), (3, 0.5), (1.5, 1.0)):
                c = QColor(sombra)
                c.setAlphaF(sombra.alphaF() * alfa * 0.6)
                p.setBrush(c)
                p.drawRect(QRectF(-k * s, -k * s + 2 * s, w + 2 * k * s, h + 2 * k * s))
            p.restore()

    def drawForeground(self, p, rect):
        if self._forma is None or self.escala() < 14:
            return
        h, w = self._forma
        visible = rect.intersected(QRectF(0, 0, w, h))
        if visible.isEmpty():
            return
        p.save()
        pluma = QPen(QColor(128, 128, 128, 110), 0)
        pluma.setCosmetic(True)
        p.setPen(pluma)
        for x in range(int(math.floor(visible.left())), int(math.ceil(visible.right())) + 1):
            p.drawLine(QPointF(x, visible.top()), QPointF(x, visible.bottom()))
        for y in range(int(math.floor(visible.top())), int(math.ceil(visible.bottom())) + 1):
            p.drawLine(QPointF(visible.left(), y), QPointF(visible.right(), y))
        p.restore()

    # -- detalles internos -------------------------------------------------

    def _crear_hud(self):
        self._textos_hud = {'titulo': '', 'nota': '', 'derecha': ''}
        self._hud_titulo = QLabel(self)
        self._hud_titulo.setObjectName('HudTitulo')
        self._hud_derecha = QLabel(self)
        self._hud_derecha.setObjectName('HudTitulo')
        self._hud_nota = QLabel(self)
        self._hud_nota.setObjectName('Hud')
        self._hud_info = QLabel(self)
        self._hud_info.setObjectName('Hud')
        self._hud_zoom = QLabel(self)
        self._hud_zoom.setObjectName('Hud')
        for e in (self._hud_titulo, self._hud_derecha, self._hud_nota, self._hud_info, self._hud_zoom):
            e.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            e.hide()
        self._vacio = EstadoVacio('dato', 'Sin imagen', '', self)
        self._vacio.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

    @staticmethod
    def _texto_ajustado(etiqueta_hud: QLabel, texto: str, ancho: int) -> None:
        """Abrevia el texto de un indicador para que quepa en el ancho disponible."""
        relleno = 20
        visible = etiqueta_hud.fontMetrics().elidedText(texto, Qt.TextElideMode.ElideRight, max(40, ancho - relleno))
        etiqueta_hud.setText(visible)
        etiqueta_hud.adjustSize()

    def _colocar_hud(self):
        area = self.viewport().geometry()
        m = 10
        disponible = max(80, area.width() - 2 * m)
        if self._cortina and self._textos_hud['derecha']:
            mitad = disponible // 2 - 4
            self._texto_ajustado(self._hud_titulo, self._textos_hud['titulo'], mitad)
            self._texto_ajustado(self._hud_derecha, self._textos_hud['derecha'], mitad)
        else:
            self._texto_ajustado(self._hud_titulo, self._textos_hud['titulo'], disponible)
        self._texto_ajustado(self._hud_nota, self._textos_hud['nota'], disponible)
        self._hud_titulo.move(area.left() + m, area.top() + m)
        self._hud_derecha.move(area.right() - self._hud_derecha.width() - m, area.top() + m)
        self._hud_nota.move(area.left() + m, area.top() + m + (self._hud_titulo.height() + 6 if self._hud_titulo.isVisible() else 0))
        self._hud_info.adjustSize()
        self._hud_info.move(area.left() + m, area.bottom() - self._hud_info.height() - m)
        self._hud_zoom.adjustSize()
        self._hud_zoom.move(area.right() - self._hud_zoom.width() - m, area.bottom() - self._hud_zoom.height() - m)
        self._vacio.setGeometry(self.rect())

    def _tema_cambiado(self):
        acento = tema().color('acento')
        pluma = QPen(acento, 2)
        pluma.setCosmetic(True)
        self._marco_roi.setPen(pluma)
        pluma_linea = QPen(acento, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        pluma_linea.setCosmetic(True)
        self._linea.setPen(pluma_linea)
        pluma_div = QPen(QColor('#FFFFFF'), 2)
        pluma_div.setCosmetic(True)
        self._division.setPen(pluma_div)
        self.resetCachedContent()
        self.viewport().update()

    def _limpiar_decoraciones(self):
        for item in self._decoraciones:
            self.escena.removeItem(item)
        self._decoraciones = []

    def _ocultar_roi(self):
        self._velo.hide()
        self._marco_roi.hide()
        self._etiqueta_roi.hide()

    def _ocultar_dibujos(self):
        self._ocultar_roi()
        self._linea.hide()
        for e in self._extremos:
            e.hide()
        self._etiqueta_linea.hide()

    def _texto_longitud(self, largo_px: float) -> str:
        texto = f'{largo_px:.1f} px'
        if self.escala_um:
            texto += f'  ·  {largo_px * self.escala_um:.4g} µm'
        return texto

    def _ajustar_borde(self, p: QPointF) -> QPointF:
        h, w = self._forma
        return QPointF(max(0, min(w, round(p.x()))), max(0, min(h, round(p.y()))))

    def _ajustar_centro(self, p: QPointF) -> QPointF:
        """Coordenadas de centro de píxel (columna, fila), limitadas a la imagen."""
        h, w = self._forma
        return QPointF(max(0.0, min(w - 1.0, p.x() - 0.5)), max(0.0, min(h - 1.0, p.y() - 0.5)))

    def _dibujar_linea_temporal(self, q: QPointF):
        a = self._linea_inicio
        self._linea.setLine(a.x() + 0.5, a.y() + 0.5, q.x() + 0.5, q.y() + 0.5)
        self._linea.show()
        self._extremos[0].setPos(a + QPointF(0.5, 0.5))
        self._extremos[0].show()
        self._extremos[1].setPos(q + QPointF(0.5, 0.5))
        self._extremos[1].show()
        self._etiqueta_linea.establecer(self._texto_longitud(math.hypot(q.x() - a.x(), q.y() - a.y())))
        self._etiqueta_linea.setPos(q + QPointF(0.5, 0.5))
        self._etiqueta_linea.show()

    def _terminar_linea(self, q: QPointF):
        a = self._linea_inicio
        self._linea_activa = False
        self._esperando_fin = False
        self._dibujar_linea_temporal(q)
        if math.hypot(q.x() - a.x(), q.y() - a.y()) > 0:
            self.linea_elegida.emit(float(a.y()), float(a.x()), float(q.y()), float(q.x()))

    def _mover_division(self, x: float):
        if self._forma is None:
            return
        h, w = self._forma
        x = max(0.0, min(float(w), x))
        self._division_x = x
        self._recorte_b.setRect(QRectF(x, 0, w - x, h))
        self._division.setLine(x, 0, x, h)
        self._perilla.setPos(x, h / 2)

    def _informar_pixel(self, p: QPointF):
        datos = self._datos
        if datos is None or np.ndim(datos) < 2 or self._forma is None:
            return
        c, r = int(math.floor(p.x())), int(math.floor(p.y()))
        h, w = self._forma
        if not (0 <= r < h and 0 <= c < w):
            self._hud_info.hide()
            return
        try:
            v = datos[r, c]
        except IndexError:
            return
        tipo = self._tipo
        if np.ndim(v) > 0:
            valores = ' · '.join(f'{n} {x:.4g}' if isinstance(x, float) else f'{n} {x}'
                                 for n, x in zip('RGBA', np.asarray(v).tolist()))
        elif datos.dtype.kind == 'b':
            valores = 'primer plano' if v else 'fondo'
        elif tipo == 'etiquetas':
            valores = f'objeto {int(v)}' if v else 'fondo'
        elif tipo == 'clases':
            valores = f'clase {int(v)}'
        elif tipo == 'marcadores':
            valores = f'marcador {int(v)}' if v else 'sin marcador'
        elif datos.dtype.kind == 'f':
            valores = f'{float(v):.5g}'
        else:
            valores = str(v)
        texto = f'Fila {r}  ·  Columna {c}  ·  {valores}'
        self._hud_info.setText(texto)
        self._hud_info.show()
        self._hud_info.adjustSize()
        area = self.viewport().geometry()
        self._hud_info.move(area.left() + 10, area.bottom() - self._hud_info.height() - 10)
        self.pixel.emit(texto)

    def _zoom_por(self, factor: float, centro: bool = False):
        if self._forma is None:
            return
        nueva = max(0.02, min(self.ZOOM_MAX, self.escala() * factor))
        self._establecer_escala(nueva, centro)

    def _establecer_escala(self, nueva: float, centro: bool = True):
        if self._forma is None:
            return
        actual = self.escala()
        if actual <= 0:
            return
        anclaje = self.transformationAnchor()
        if centro:
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.scale(nueva / actual, nueva / actual)
        self.setTransformationAnchor(anclaje)
        self._ajuste_auto = False
        self._tras_zoom()

    def _tras_zoom(self):
        self._actualizar_suavizado()
        self._actualizar_hud_zoom()
        self.zoom_cambiado.emit(self.escala())
        if not self._aplicando_estado:
            self.vista_cambiada.emit()

    def _actualizar_hud_zoom(self):
        if self._forma is None:
            self._hud_zoom.hide()
            return
        self._hud_zoom.setText(f'{self.escala() * 100:.0f} %')
        self._hud_zoom.show()
        self._hud_zoom.adjustSize()
        area = self.viewport().geometry()
        self._hud_zoom.move(area.right() - self._hud_zoom.width() - 10, area.bottom() - self._hud_zoom.height() - 10)

    def _actualizar_suavizado(self):
        suave = self.escala() < 1
        modo = Qt.TransformationMode.SmoothTransformation if suave else Qt.TransformationMode.FastTransformation
        for item in (self._item, self._item_b):
            item.setTransformationMode(modo)
        for item in (self._capa, self._capa_b, self._resalte):
            item.setTransformationMode(Qt.TransformationMode.FastTransformation)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, suave)

    def _vista_movida(self, *_):
        if not self._aplicando_estado and self._forma is not None:
            self.vista_cambiada.emit()


# ---------------------------------------------------------------------------
# Tabla
# ---------------------------------------------------------------------------

class ModeloTabla(QAbstractTableModel):
    """Modelo de solo lectura; muestra valores formateados y ordena por el valor real."""

    def __init__(self, tabla=None, parent=None):
        super().__init__(parent)
        self.tabla = pd.DataFrame() if tabla is None else tabla.copy()
        self._numericas = {c for c in self.tabla.columns
                           if pd.api.types.is_numeric_dtype(self.tabla[c]) and not pd.api.types.is_bool_dtype(self.tabla[c])}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent is not None and parent.isValid() else len(self.tabla)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent is not None and parent.isValid() else len(self.tabla.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        valor = self.tabla.iat[index.row(), index.column()]
        columna = self.tabla.columns[index.column()]
        if role == Qt.ItemDataRole.DisplayRole:
            if isinstance(valor, (bool, np.bool_)):
                return 'Sí' if valor else 'No'
            if isinstance(valor, (float, np.floating)):
                return 'indefinido' if np.isnan(valor) else f'{valor:.6g}'
            return str(valor)
        if role == Qt.ItemDataRole.UserRole:
            if isinstance(valor, (bool, np.bool_)):
                return int(valor)
            if isinstance(valor, (int, float, np.integer, np.floating)):
                v = float(valor)
                return -math.inf if math.isnan(v) else v
            return str(valor)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if columna in self._numericas:
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        if role == Qt.ItemDataRole.ForegroundRole:
            if isinstance(valor, (float, np.floating)) and np.isnan(valor):
                return QBrush(tema().color('texto3'))
            if columna == 'aceptado' and isinstance(valor, (bool, np.bool_)):
                return QBrush(tema().color('exito_texto' if valor else 'texto2'))
            return None
        if role == Qt.ItemDataRole.ToolTipRole:
            if isinstance(valor, (float, np.floating)):
                return 'Indefinido (NaN): el descriptor no está definido, no es cero.' if np.isnan(valor) else repr(float(valor))
            return None
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            columna = self.tabla.columns[section]
            if role == Qt.ItemDataRole.DisplayRole:
                return etiqueta_columna(columna)
            if role == Qt.ItemDataRole.ToolTipRole:
                return f'Columna: {columna}'
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return str(section + 1)
        return None


class ProxyTabla(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSortRole(Qt.ItemDataRole.UserRole)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterKeyColumn(-1)


# ---------------------------------------------------------------------------
# Gráficas
# ---------------------------------------------------------------------------

_FAMILIAS_MPL = None


def _rc_seguro() -> dict:
    """Parámetros de Matplotlib limitados a fuentes que Matplotlib conoce."""
    global _FAMILIAS_MPL
    rc = rc_matplotlib()
    if _FAMILIAS_MPL is None:
        from matplotlib import font_manager
        _FAMILIAS_MPL = {f.name for f in font_manager.fontManager.ttflist}
    familias = [f for f in rc['font.family'] if f in _FAMILIAS_MPL] or ['DejaVu Sans']
    rc['font.family'] = familias
    return rc


class PanelGrafica(QWidget):
    """Gráfica del resultado activo con estilo de la interfaz."""
    TIPOS = ('Línea', 'Barras', 'Dispersión', 'Histograma')

    def __init__(self, parent=None):
        super().__init__(parent)
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(6)
        controles = QHBoxLayout()
        controles.setSpacing(8)
        self.tipo = Selector()
        for t in self.TIPOS:
            self.tipo.agregar(t, t)
        self.eje_x = Selector()
        self.eje_y = Selector()
        for w in (self.eje_x, self.eje_y):
            w.setMinimumContentsLength(14)
        controles.addWidget(etiqueta('Tipo', 'secundario'))
        controles.addWidget(self.tipo)
        self._etiqueta_x = etiqueta('X', 'secundario')
        controles.addWidget(self._etiqueta_x)
        controles.addWidget(self.eje_x, 1)
        self._etiqueta_y = etiqueta('Y', 'secundario')
        controles.addWidget(self._etiqueta_y)
        controles.addWidget(self.eje_y, 1)
        controles.addStretch(0)
        self.tipo.setMinimumContentsLength(11)
        self.tipo.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.guardar = BotonIcono('exportar', 'Guardar la gráfica como imagen (PNG, SVG o PDF)')
        self.guardar.clicked.connect(self._guardar)
        controles.addWidget(self.guardar)
        lay.addLayout(controles)
        self.figura = Figure(figsize=(6, 3))
        self.canvas = FigureCanvasQTAgg(self.figura)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.canvas.setMinimumHeight(80)
        lay.addWidget(self.canvas, 1)
        self.vacio = EstadoVacio('grafica', 'Sin gráfica', 'Ejecute una operación que produzca una tabla o una serie numérica.', compacto=True)
        lay.addWidget(self.vacio, 1)
        self.canvas.hide()
        self._resultado = None
        self._operacion = None
        self._serie = None
        self._titulo_serie = ''
        for w in (self.tipo, self.eje_x, self.eje_y):
            w.currentIndexChanged.connect(self.dibujar)
        tema().cambiado.connect(self.dibujar)

    @property
    def ax(self):
        return self.figura.axes[0] if self.figura.axes else self.figura.add_subplot(111)

    def limpiar(self):
        self._resultado = None
        self._serie = None
        self.dibujar()

    def establecer_resultado(self, id_operacion: str, resultado) -> None:
        self._resultado = resultado
        self._operacion = id_operacion
        self._serie = None
        tabla = resultado.tabla
        numericas = [str(c) for c in tabla.select_dtypes(include='number').columns
                     if not pd.api.types.is_bool_dtype(tabla[c])]
        for w in (self.tipo, self.eje_x, self.eje_y):
            w.blockSignals(True)
        self.eje_x.clear()
        self.eje_y.clear()
        for c in numericas:
            self.eje_x.agregar(etiqueta_columna(c), c)
            self.eje_y.agregar(etiqueta_columna(c), c)
        tipo, x, y = self._configuracion(id_operacion, numericas, resultado)
        self.tipo.setCurrentText(tipo)
        if x:
            self.eje_x.setCurrentText(x)
        if y:
            self.eje_y.setCurrentText(y)
        for w in (self.tipo, self.eje_x, self.eje_y):
            w.blockSignals(False)
        self.dibujar()

    def establecer_serie(self, valores: np.ndarray, titulo: str = '') -> None:
        self._resultado = None
        self._serie = np.asarray(valores, dtype=float)
        self._titulo_serie = titulo
        self.tipo.blockSignals(True)
        self.tipo.setCurrentText('Histograma')
        self.tipo.blockSignals(False)
        self.eje_x.clear()
        self.eje_y.clear()
        self.dibujar()

    def tiene_contenido(self) -> bool:
        return self.canvas.isVisible()

    @staticmethod
    def _configuracion(op, numericas, resultado):
        if op == 'histograma_percentiles':
            return 'Barras', 'intensidad', 'conteo'
        if op == 'perfil_intensidad':
            return 'Línea', 'distancia_px', 'intensidad'
        if op == 'fracciones_area':
            return 'Barras', 'clase', 'porcentaje_area'
        if op == 'intercepto_medio':
            return 'Barras', 'posicion_px', 'intersecciones'
        if op in ('intervalo_bootstrap_media', 'reporte_fraccion_area'):
            return 'Histograma', None, None
        if op == 'densidad_jeffries':
            return 'Barras', 'etiqueta', 'peso'
        for preferida in ('diametro_equivalente_um', 'area_um2', 'area_px2'):
            if preferida in numericas:
                return 'Histograma', 'etiqueta' if 'etiqueta' in numericas else None, preferida
        if len(numericas) >= 2:
            return 'Línea', numericas[0], numericas[1]
        return 'Histograma', None, numericas[0] if numericas else None

    def _vector_resultado(self):
        if self._resultado is None:
            return None
        for a in self._resultado.datos.values():
            if a.ndim == 1:
                return a
        return None

    def dibujar(self, *_):
        import matplotlib
        tipo = self.tipo.currentData() or 'Línea'
        hay_tabla = self._resultado is not None and len(self._resultado.tabla) > 0 and self.eje_y.count() > 0
        vector = self._serie if self._serie is not None else self._vector_resultado()
        con_ejes = hay_tabla and tipo != 'Histograma'
        self._etiqueta_x.setVisible(con_ejes)
        self.eje_x.setVisible(con_ejes)
        self._etiqueta_y.setVisible(hay_tabla)
        self.eje_y.setVisible(hay_tabla)
        if not hay_tabla and vector is None:
            self.canvas.hide()
            self.vacio.show()
            self.guardar.setEnabled(False)
            return
        self.vacio.hide()
        self.canvas.show()
        self.guardar.setEnabled(True)
        acento = tema().c['acento']
        naranja = tema().c['aviso']
        with matplotlib.rc_context(_rc_seguro()):
            self.figura.clear()
            self.figura.set_facecolor(_hex(tema().c['panel']))
            ax = self.figura.add_subplot(111)
            if hay_tabla and not (vector is not None and self._operacion in ('intervalo_bootstrap_media', 'reporte_fraccion_area')):
                t = self._resultado.tabla
                x, y = self.eje_x.currentData(), self.eje_y.currentData()
                if tipo == 'Histograma':
                    datos = pd.to_numeric(t[y], errors='coerce').dropna()
                    ax.hist(datos, bins='auto', color=acento, alpha=0.85, edgecolor=_hex(tema().c['panel']), linewidth=0.6)
                    ax.set_xlabel(etiqueta_columna(y))
                    ax.set_ylabel('Frecuencia')
                elif x in t and y in t:
                    if tipo == 'Barras':
                        xs = pd.to_numeric(t[x], errors='coerce')
                        ancho = float(np.median(np.diff(np.sort(xs.unique())))) * 0.85 if xs.nunique() > 1 else 0.8
                        colores = acento
                        if 'orientacion' in t:
                            colores = [acento if o == 'horizontal' else naranja for o in t['orientacion']]
                        ax.bar(xs, t[y], width=ancho, color=colores, alpha=0.9, linewidth=0)
                        if 'orientacion' in t:
                            from matplotlib.patches import Patch
                            ax.legend(handles=[Patch(color=acento, label='Horizontal'), Patch(color=naranja, label='Vertical')])
                    elif tipo == 'Dispersión':
                        ax.scatter(t[x], t[y], s=22, color=acento, alpha=0.85, edgecolors='none')
                    else:
                        ax.plot(t[x], t[y], color=acento, linewidth=1.8)
                        if len(t) < 300:
                            ax.fill_between(t[x], t[y], alpha=0.08, color=acento)
                    ax.set_xlabel(etiqueta_columna(x))
                    ax.set_ylabel(etiqueta_columna(y))
                    resumen = self._resultado.resumen
                    if self._operacion == 'histograma_percentiles':
                        for clave, nombre in (('p1', 'P1'), ('p99', 'P99')):
                            if clave in resumen:
                                ax.axvline(resumen[clave], color=naranja, linewidth=1.2, linestyle='--')
                                ax.text(resumen[clave], ax.get_ylim()[1] * 0.96, f' {nombre}', color=naranja,
                                        fontsize=8, va='top')
            else:
                v = np.asarray(vector, dtype=float)
                v = v[np.isfinite(v)]
                ax.hist(v, bins=min(40, max(5, len(v) // 5)) if len(v) > 10 else 'auto', color=acento,
                        alpha=0.85, edgecolor=_hex(tema().c['panel']), linewidth=0.6)
                ax.set_ylabel('Frecuencia')
                if self._serie is not None:
                    ax.set_xlabel(self._titulo_serie or 'Valor')
                else:
                    ax.set_xlabel('Media remuestreada')
                    resumen = self._resultado.resumen
                    if 'media' in resumen:
                        ax.axvline(resumen['media'], color=_hex(tema().c['texto']), linewidth=1.4, label='Media observada')
                    intervalo = resumen.get('intervalo_percentil')
                    if intervalo:
                        for lim in intervalo:
                            ax.axvline(lim, color=naranja, linewidth=1.3, linestyle='--')
                        ax.axvspan(intervalo[0], intervalo[1], color=naranja, alpha=0.08,
                                   label=f'Intervalo {resumen.get("confianza", 0.95):.0%}')
                    ax.legend(loc='upper right', fontsize=8)
            try:
                self.figura.tight_layout(pad=0.6)
            except Exception:
                pass
        self.canvas.draw_idle()

    def _guardar(self):
        ruta, _ = QFileDialog.getSaveFileName(self, 'Guardar gráfica', 'grafica.png',
                                              'PNG (*.png);;SVG (*.svg);;PDF (*.pdf)')
        if ruta:
            self.figura.savefig(ruta, dpi=200)


def _hex(valor) -> str:
    return valor[0] if isinstance(valor, tuple) else valor
