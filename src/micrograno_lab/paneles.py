"""Paneles de la ventana: bienvenida, filas de datos e historial y tira de salidas."""
from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont, QPainter, QPalette
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QListView, QListWidget,
                               QListWidgetItem, QSizePolicy, QVBoxLayout, QWidget)
from . import iconos
from .componentes import EtiquetaIcono, EtiquetaSeccion, etiqueta
from .tema import SISTEMA
from .textos import PASOS_GUIA


class EtiquetaRecortada(QLabel):
    """Etiqueta de una línea que abrevia el texto con «…» si no cabe."""

    def __init__(self, texto: str = '', rol: str | None = None, modo=Qt.TextElideMode.ElideRight,
                 parent=None):
        super().__init__(texto, parent)
        self._completo = texto
        self._modo = modo
        if rol:
            self.setProperty('rol', rol)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def setText(self, texto: str) -> None:
        self._completo = texto
        super().setText(texto)
        self.setToolTip(texto)

    def texto_completo(self) -> str:
        return self._completo

    def minimumSizeHint(self):
        return QSize(12, super().minimumSizeHint().height())

    def paintEvent(self, _):
        p = QPainter(self)
        p.setPen(self.palette().color(QPalette.ColorRole.WindowText))
        p.setFont(self.font())
        visible = self.fontMetrics().elidedText(self._completo, self._modo, self.width())
        p.drawText(self.rect(), int(self.alignment() | Qt.AlignmentFlag.AlignVCenter), visible)


class Baldosa(QFrame):
    """Tarjeta grande pulsable de la pantalla de bienvenida."""
    pulsada = Signal()

    def __init__(self, icono: str, color: str, titulo: str, texto: str, parent=None):
        super().__init__(parent)
        self.setProperty('clase', 'baldosa')
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(220)
        self.setMinimumHeight(168)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)
        lay.addWidget(EtiquetaIcono(icono, 36, insignia=color))
        t = etiqueta(titulo)
        f = t.font()
        f.setPointSizeF(f.pointSizeF() + 1.5)
        f.setWeight(QFont.Weight.DemiBold)
        t.setFont(f)
        lay.addWidget(t)
        lay.addWidget(etiqueta(texto, 'secundario', envolver=True))
        lay.addStretch(1)

    def mouseReleaseEvent(self, evento):
        if evento.button() == Qt.MouseButton.LeftButton and self.rect().contains(evento.position().toPoint()):
            self.pulsada.emit()
        super().mouseReleaseEvent(evento)


class PaginaBienvenida(QWidget):
    abrir_imagen = Signal()
    probar_demo = Signal()
    abrir_sesion = Signal()
    abrir_reciente = Signal(str)
    explorar = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('Bienvenida')
        externo = QVBoxLayout(self)
        externo.setContentsMargins(32, 24, 32, 24)
        externo.addStretch(2)
        columna = QWidget()
        columna.setMaximumWidth(920)
        lay = QVBoxLayout(columna)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        icono = QLabel()
        icono.setPixmap(iconos.pixmap_app(92))
        lay.addWidget(icono, 0, Qt.AlignmentFlag.AlignHCenter)
        titulo = etiqueta('MicroGrano Lab', 'titulo_grande')
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(titulo)
        sub = etiqueta('Aprenda a analizar imágenes con la biblioteca MicroGrano', 'subtitulo')
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(sub)
        lay.addSpacing(22)
        baldosas = QHBoxLayout()
        baldosas.setSpacing(14)
        for icono_b, color, texto_t, texto_d, senal in (
                ('importar', SISTEMA['azul'], 'Abrir una imagen',
                 'TIFF, PNG, JPG o NPY. La imagen original se conserva sin cambios.', self.abrir_imagen),
                ('matraz', SISTEMA['morado'], 'Aprender con un ejemplo',
                 'Empiece con una imagen sintética y construya sus versiones paso a paso.', self.probar_demo),
                ('abrir', SISTEMA['naranja'], 'Abrir una sesión',
                 'Continúe un análisis guardado. Los datos se verifican con SHA-256.', self.abrir_sesion)):
            b = Baldosa(icono_b, color, texto_t, texto_d)
            b.pulsada.connect(senal.emit)
            baldosas.addWidget(b, 1)
        lay.addLayout(baldosas)
        lay.addSpacing(26)
        lay.addWidget(EtiquetaSeccion('Cómo funciona'))
        lay.addSpacing(4)
        pasos = QHBoxLayout()
        pasos.setSpacing(10)
        for i, (_, texto_t, texto_d, icono_p) in enumerate(PASOS_GUIA, 1):
            pasos.addWidget(self._paso(i, icono_p, texto_t, texto_d), 1)
        lay.addLayout(pasos)
        lay.addSpacing(22)
        self._caja_recientes = QWidget()
        recientes = QVBoxLayout(self._caja_recientes)
        recientes.setContentsMargins(0, 0, 0, 0)
        recientes.setSpacing(6)
        recientes.addWidget(EtiquetaSeccion('Sesiones recientes'))
        self.lista_recientes = QListWidget()
        self.lista_recientes.setObjectName('ListaRecientes')
        self.lista_recientes.setIconSize(QSize(18, 18))
        self.lista_recientes.setMaximumHeight(130)
        self.lista_recientes.itemActivated.connect(lambda it: self.abrir_reciente.emit(it.data(Qt.ItemDataRole.UserRole)))
        self.lista_recientes.itemClicked.connect(lambda it: self.abrir_reciente.emit(it.data(Qt.ItemDataRole.UserRole)))
        recientes.addWidget(self.lista_recientes)
        lay.addWidget(self._caja_recientes)
        pie = QHBoxLayout()
        pie.addWidget(etiqueta('También puede arrastrar una imagen a esta ventana. Los archivos se procesan '
                               'localmente; no hay telemetría.', 'pie', envolver=True), 1)
        explorar = QLabel('<a href="#">Explorar las herramientas sin datos</a>')
        explorar.setProperty('rol', 'pie')
        explorar.linkActivated.connect(lambda *_: self.explorar.emit())
        pie.addWidget(explorar)
        lay.addLayout(pie)
        externo.addWidget(columna, 0, Qt.AlignmentFlag.AlignHCenter)
        externo.addStretch(3)
        self.establecer_recientes([])

    @staticmethod
    def _paso(numero: int, icono: str, titulo: str, texto: str) -> QWidget:
        caja = QFrame()
        caja.setProperty('clase', 'tarjeta')
        caja.setToolTip(texto)
        lay = QVBoxLayout(caja)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)
        fila = QHBoxLayout()
        fila.setSpacing(6)
        fila.addWidget(EtiquetaIcono(icono, 18, 'acento'))
        n = etiqueta(str(numero), 'terciario')
        fila.addStretch(1)
        fila.addWidget(n)
        lay.addLayout(fila)
        t = etiqueta(titulo, envolver=True)
        f = t.font()
        f.setPointSizeF(f.pointSizeF() - 0.5)
        f.setWeight(QFont.Weight.DemiBold)
        t.setFont(f)
        lay.addWidget(t)
        lay.addStretch(1)
        return caja

    def establecer_recientes(self, rutas: list[str]) -> None:
        self.lista_recientes.clear()
        for ruta in rutas:
            p = Path(ruta)
            item = QListWidgetItem(iconos.icono('abrir', 'texto2'), f'{p.parent.name}    —    {p.parent.parent}')
            item.setData(Qt.ItemDataRole.UserRole, ruta)
            item.setToolTip(ruta)
            self.lista_recientes.addItem(item)
        self._caja_recientes.setVisible(bool(rutas))


class FilaDato(QWidget):
    """Fila de la lista de datos: miniatura, nombre, descripción y estado."""

    def __init__(self, pixmap, titulo: str, subtitulo: str, escala: bool | None, roi: bool | None,
                 parent=None):
        super().__init__(parent)
        self.setObjectName('FilaDato')
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 5, 8, 5)
        lay.setSpacing(10)
        miniatura = QLabel()
        miniatura.setFixedSize(40, 40)
        if pixmap is not None:
            miniatura.setPixmap(pixmap)
        lay.addWidget(miniatura)
        textos = QVBoxLayout()
        textos.setSpacing(1)
        self.titulo = EtiquetaRecortada(titulo)
        self.subtitulo = EtiquetaRecortada(subtitulo, 'pie')
        textos.addWidget(self.titulo)
        textos.addWidget(self.subtitulo)
        lay.addLayout(textos, 1)
        estados = QVBoxLayout()
        estados.setSpacing(3)
        if escala is not None:
            e = EtiquetaIcono('regla', 13, 'exito' if escala else 'texto3')
            e.setToolTip('Escala asociada' if escala else 'Sin escala asociada')
            estados.addWidget(e)
        if roi is not None:
            r = EtiquetaIcono('recortar', 13, 'exito' if roi else 'texto3')
            r.setToolTip('Región de análisis confirmada' if roi else 'Región sin confirmar')
            estados.addWidget(r)
        lay.addLayout(estados)

    def sizeHint(self):
        return QSize(200, 52)


class FilaPaso(QWidget):
    """Fila del historial: número, herramienta y resumen de entradas y salidas."""

    def __init__(self, numero: int, icono: str, color: str, titulo: str, subtitulo: str, parent=None):
        super().__init__(parent)
        self.setObjectName('FilaPaso')
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 10, 6)
        lay.setSpacing(10)
        n = etiqueta(f'{numero}', 'terciario')
        n.setFixedWidth(22)
        n.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(n)
        lay.addWidget(EtiquetaIcono(icono, 24, insignia=color))
        textos = QVBoxLayout()
        textos.setSpacing(1)
        t = EtiquetaRecortada(titulo)
        f = t.font()
        f.setWeight(QFont.Weight.DemiBold)
        t.setFont(f)
        textos.addWidget(t)
        textos.addWidget(EtiquetaRecortada(subtitulo, 'pie'))
        lay.addLayout(textos, 1)

    def sizeHint(self):
        return QSize(260, 46)


class TiraSalidas(QListWidget):
    """Tira horizontal de miniaturas con las salidas de un paso."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('Tira')
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setWrapping(False)
        self.setMovement(QListView.Movement.Static)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setIconSize(QSize(58, 58))
        self.setGridSize(QSize(104, 100))
        self.setWordWrap(True)
        self.setUniformItemSizes(True)
        self.setHorizontalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(106)
        self.setSelectionMode(QListView.SelectionMode.SingleSelection)

    def currentData(self):
        item = self.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def findData(self, valor) -> int:
        for i in range(self.count()):
            if self.item(i).data(Qt.ItemDataRole.UserRole) == valor:
                return i
        return -1

    def setCurrentIndex(self, indice: int) -> None:
        self.setCurrentRow(indice)

    def wheelEvent(self, evento):
        barra = self.horizontalScrollBar()
        barra.setValue(barra.value() - evento.angleDelta().y() - evento.angleDelta().x())
