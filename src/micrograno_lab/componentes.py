"""Componentes visuales reutilizables de MicroGrano Lab (sin lógica científica)."""
from __future__ import annotations
import keyword
import math
import re
from PySide6.QtCore import (QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QRect, QRectF,
                            QSize, Qt, QTimer, QVariantAnimation, Signal)
from PySide6.QtGui import (QColor, QFont, QIcon, QPainter, QPen, QSyntaxHighlighter,
                           QTextCharFormat, QGuiApplication)
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox, QFrame,
                               QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QPushButton, QSizePolicy, QSlider,
                               QStyledItemDelegate, QToolButton, QVBoxLayout, QWidget)
from . import iconos
from .tema import qcolor, tema


def polir(widget: QWidget) -> None:
    """Vuelve a aplicar la hoja de estilo tras cambiar una propiedad dinámica."""
    estilo = widget.style()
    estilo.unpolish(widget)
    estilo.polish(widget)
    widget.update()


def etiqueta(texto: str = '', rol: str | None = None, envolver: bool = False,
             seleccionable: bool = False) -> QLabel:
    e = QLabel(texto)
    if rol:
        e.setProperty('rol', rol)
    e.setWordWrap(envolver)
    if seleccionable:
        e.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return e


class EtiquetaSeccion(QLabel):
    """Encabezado pequeño en versalitas, como en las listas agrupadas de Apple."""

    def __init__(self, texto: str, parent=None):
        super().__init__(texto.upper(), parent)
        self.setProperty('rol', 'seccion')
        f = self.font()
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.6)
        self.setFont(f)


class EtiquetaIcono(QLabel):
    """Etiqueta con un icono vectorial que se redibuja al cambiar el tema."""

    def __init__(self, nombre: str, lado: int = 16, rol: str = 'texto2',
                 insignia: str | None = None, parent=None):
        super().__init__(parent)
        self._nombre, self._lado, self._rol, self._insignia = nombre, lado, rol, insignia
        self.setFixedSize(lado, lado)
        self._pintar()
        tema().cambiado.connect(self._pintar)

    def establecer(self, nombre: str | None = None, rol: str | None = None,
                   insignia: str | None = None) -> None:
        if nombre:
            self._nombre = nombre
        if rol:
            self._rol = rol
        self._insignia = insignia if insignia is not None else self._insignia
        self._pintar()

    def _pintar(self):
        try:
            self.setPixmap(iconos.pixmap(self._nombre, self._lado, self._rol, self._insignia))
        except RuntimeError:
            pass


def linea_horizontal() -> QFrame:
    f = QFrame()
    f.setProperty('clase', 'separador')
    f.setFixedHeight(1)
    return f


def linea_vertical() -> QFrame:
    f = QFrame()
    f.setProperty('clase', 'separador_v')
    f.setFixedWidth(1)
    return f


class Interruptor(QCheckBox):
    """Interruptor animado (switch) compatible con la API de QCheckBox."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(42, 24)
        self._pos = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.valueChanged.connect(self._mover)
        self.toggled.connect(self._animar)

    def sizeHint(self):
        return QSize(42, 24)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def _mover(self, valor):
        self._pos = float(valor)
        self.update()

    def _animar(self, activo):
        if not self.isVisible():
            self._pos = 1.0 if activo else 0.0
            self.update()
            return
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if activo else 0.0)
        self._anim.start()

    def showEvent(self, evento):
        self._pos = 1.0 if self.isChecked() else 0.0
        super().showEvent(evento)

    def paintEvent(self, _):
        t = tema()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.45)
        pista = QRectF(1, 2, 40, 20)
        apagado, encendido = t.color('pista'), t.color('acento')
        k = self._pos
        color = QColor(
            round(apagado.red() + (encendido.red() - apagado.red()) * k),
            round(apagado.green() + (encendido.green() - apagado.green()) * k),
            round(apagado.blue() + (encendido.blue() - apagado.blue()) * k))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(pista, 10, 10)
        x = pista.left() + 2 + k * (pista.width() - 20)
        perilla = QRectF(x, pista.top() + 2, 16, 16)
        p.setBrush(QColor(0, 0, 0, 40))
        p.drawEllipse(perilla.translated(0, 0.8))
        p.setBrush(QColor('#FFFFFF'))
        p.drawEllipse(perilla)
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(t.color('foco'), 2))
            p.drawRoundedRect(pista.adjusted(-0.5, -0.5, 0.5, 0.5), 10.5, 10.5)


class ControlSegmentado(QFrame):
    """Control segmentado exclusivo, como NSSegmentedControl."""
    cambiado = Signal(int)

    def __init__(self, opciones, parent=None, solo_iconos: bool = False, expandir: bool = False):
        super().__init__(parent)
        self.setObjectName('Segmentado')
        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(2)
        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)
        self._botones: list[QPushButton] = []
        for i, opcion in enumerate(opciones):
            if isinstance(opcion, str):
                texto, nombre_icono, ayuda = opcion, None, ''
            else:
                texto, nombre_icono, *resto = opcion
                ayuda = resto[0] if resto else ''
            b = QPushButton('' if solo_iconos else texto)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            if nombre_icono:
                b.setIcon(iconos.icono(nombre_icono, 'texto', 'acento'))
                b.setIconSize(QSize(15, 15))
            b.setToolTip(ayuda or (texto if solo_iconos else ''))
            if expandir:
                b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._grupo.addButton(b, i)
            self._botones.append(b)
            lay.addWidget(b)
        if self._botones:
            self._botones[0].setChecked(True)
        self._grupo.idClicked.connect(self.cambiado.emit)

    def indice(self) -> int:
        return self._grupo.checkedId()

    def establecer(self, indice: int, emitir: bool = False) -> None:
        if 0 <= indice < len(self._botones):
            self._botones[indice].setChecked(True)
            if emitir:
                self.cambiado.emit(indice)

    def boton(self, indice: int) -> QPushButton:
        return self._botones[indice]

    def botones(self) -> list[QPushButton]:
        return list(self._botones)


class SegmentosParametro(ControlSegmentado):
    """Segmentos con valores crudos; expone setText/text para los formularios."""

    def __init__(self, opciones: list[tuple], parent=None):
        super().__init__([texto for _, texto in opciones], parent)
        self.valores = [valor for valor, _ in opciones]

    def valor(self):
        i = self.indice()
        return self.valores[i] if 0 <= i < len(self.valores) else None

    def establecer_valor(self, valor) -> bool:
        for i, v in enumerate(self.valores):
            if v == valor or str(v) == str(valor):
                self.establecer(i)
                return True
        return False

    def setText(self, texto: str) -> None:
        if not self.establecer_valor(texto):
            raise ValueError(f'Valor no admitido: {texto}')

    def text(self) -> str:
        return str(self.valor())


class Selector(QComboBox):
    """Menú desplegable con valores crudos y textos legibles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegate(QStyledItemDelegate(self))
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(8)
        self.elegido_por_usuario = False
        self.activated.connect(lambda *_: setattr(self, 'elegido_por_usuario', True))

    def agregar(self, texto: str, valor=None, icono=None, ayuda: str = '') -> None:
        if icono is not None:
            self.addItem(icono, texto, valor)
        else:
            self.addItem(texto, valor)
        if ayuda:
            self.setItemData(self.count() - 1, ayuda, Qt.ItemDataRole.ToolTipRole)

    def setCurrentText(self, texto) -> None:  # acepta el valor crudo o el texto visible
        i = self.findData(texto)
        if i < 0:
            for j in range(self.count()):
                if str(self.itemData(j)) == str(texto):
                    i = j
                    break
        if i >= 0:
            self.setCurrentIndex(i)
        else:
            super().setCurrentText(texto)

    def valor(self):
        dato = self.currentData()
        return self.currentText() if dato is None else dato


class CampoNumero(QLineEdit):
    """Campo de texto numérico con validación visual; la biblioteca valida de nuevo."""
    validez = Signal(str)

    def __init__(self, meta: dict, tipo: str = 'float', opcional: bool = False, parent=None):
        super().__init__(parent)
        self.meta = meta
        self.tipo = tipo
        self.opcional = opcional
        self.editado_por_usuario = False
        self.textEdited.connect(self._marcar_editado)
        self.textChanged.connect(self._validar)
        if tipo != 'texto':
            self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        marcador = meta.get('marcador')
        if marcador:
            self.setPlaceholderText(marcador)
        elif opcional:
            self.setPlaceholderText('Opcional')

    def _marcar_editado(self, *_):
        self.editado_por_usuario = True

    def numero(self):
        texto = self.text().strip().replace(',', '.')
        if not texto:
            return None
        return int(texto) if self.tipo == 'int' else float(texto)

    def problema(self) -> str:
        texto = self.text().strip()
        if not texto:
            return '' if self.opcional or self.tipo == 'texto' else 'Complete este valor.'
        if self.tipo == 'texto':
            return ''
        try:
            v = self.numero()
        except ValueError:
            return 'Debe ser un número entero.' if self.tipo == 'int' else 'Debe ser un número.'
        if v is None:
            return ''
        if not math.isfinite(v):
            return 'Debe ser un número finito.'
        m = self.meta
        minimo, maximo = m.get('minimo'), m.get('maximo')
        if m.get('positivo') and v <= 0:
            return 'Debe ser mayor que 0.'
        if minimo is not None and maximo is not None and not (minimo <= v <= maximo):
            return f'Debe estar entre {minimo:g} y {maximo:g}.'
        if minimo is not None and v < minimo:
            return f'Debe ser mayor o igual que {minimo:g}.'
        if maximo is not None and v > maximo:
            return f'Debe ser menor o igual que {maximo:g}.'
        if m.get('impar') and int(v) % 2 != 1:
            return 'Debe ser un número impar.'
        return ''

    def _validar(self, *_):
        texto = self.problema()
        error = bool(texto) and bool(self.text().strip())
        if bool(self.property('error')) != error:
            self.setProperty('error', error)
            polir(self)
        self.validez.emit(texto if error else '')


class FilaParametro(QWidget):
    """Fila de formulario: etiqueta, campo, unidad, deslizador y ayuda."""

    def __init__(self, etiqueta_texto: str, campo: QWidget, unidad: str = '', ayuda: str = '',
                 nombre_tecnico: str = '', deslizador: tuple | None = None, apilado: bool = False,
                 parent=None):
        super().__init__(parent)
        self.campo = campo
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        cabecera = QHBoxLayout()
        cabecera.setSpacing(8)
        self.etiqueta = etiqueta(etiqueta_texto)
        self.etiqueta.setWordWrap(True)
        tooltip = ayuda
        if nombre_tecnico:
            tooltip = f'{ayuda}\n\nParámetro: {nombre_tecnico}' if ayuda else f'Parámetro: {nombre_tecnico}'
        self.etiqueta.setToolTip(tooltip)
        campo.setToolTip(tooltip)
        cabecera.addWidget(self.etiqueta, 1)
        if apilado:
            lay.addLayout(cabecera)
            lay.addWidget(campo)
        else:
            if isinstance(campo, QLineEdit):
                campo.setFixedWidth(104)
            cabecera.addWidget(campo, 0, Qt.AlignmentFlag.AlignRight)
            if unidad:
                u = etiqueta(unidad, 'secundario')
                u.setMinimumWidth(30)
                cabecera.addWidget(u)
            lay.addLayout(cabecera)
        self.deslizador = None
        if deslizador is not None and isinstance(campo, CampoNumero):
            self._crear_deslizador(*deslizador)
            lay.addWidget(self.deslizador)
        if ayuda:
            pie = etiqueta(ayuda, 'pie', envolver=True)
            lay.addWidget(pie)
        self.error = etiqueta('', 'error', envolver=True)
        self.error.hide()
        lay.addWidget(self.error)
        if isinstance(campo, CampoNumero):
            campo.validez.connect(self._mostrar_error)

    def _crear_deslizador(self, minimo, maximo):
        campo: CampoNumero = self.campo
        self._entero = campo.tipo == 'int'
        self._lim = (float(minimo), float(maximo))
        s = QSlider(Qt.Orientation.Horizontal)
        s.setCursor(Qt.CursorShape.PointingHandCursor)
        if self._entero:
            s.setRange(int(minimo), int(maximo))
        else:
            s.setRange(0, 1000)
        self.deslizador = s
        self._sincronizar_desde_campo()
        s.valueChanged.connect(self._desde_deslizador)
        campo.textChanged.connect(self._sincronizar_desde_campo)

    def _desde_deslizador(self, pos):
        campo: CampoNumero = self.campo
        if getattr(self, '_bloqueo', False):
            return
        if self._entero:
            valor = int(pos)
            texto = str(valor)
        else:
            a, b = self._lim
            valor = a + (b - a) * pos / 1000
            decimales = campo.meta.get('decimales', 3)
            texto = f'{valor:.{decimales}f}'.rstrip('0').rstrip('.') if decimales else f'{valor:.0f}'
            if texto in ('', '-0'):
                texto = '0'
        self._bloqueo = True
        campo.setText(texto)
        campo.editado_por_usuario = True
        self._bloqueo = False

    def _sincronizar_desde_campo(self, *_):
        if getattr(self, '_bloqueo', False) or self.deslizador is None:
            return
        try:
            v = self.campo.numero()
        except ValueError:
            return
        if v is None:
            return
        self._bloqueo = True
        if self._entero:
            self.deslizador.setValue(int(round(v)))
        else:
            a, b = self._lim
            self.deslizador.setValue(int(round((min(max(v, a), b) - a) / (b - a) * 1000)) if b > a else 0)
        self._bloqueo = False

    def _mostrar_error(self, texto):
        self.error.setText(texto)
        self.error.setVisible(bool(texto))


class Tarjeta(QFrame):
    """Contenedor redondeado con fondo de tarjeta."""

    def __init__(self, parent=None, margenes=(14, 12, 14, 12), espaciado: int = 12):
        super().__init__(parent)
        self.setProperty('clase', 'tarjeta')
        self.capa = QVBoxLayout(self)
        self.capa.setContentsMargins(*margenes)
        self.capa.setSpacing(espaciado)

    def agregar(self, widget: QWidget, separador_antes: bool = False) -> QWidget:
        if separador_antes and self.capa.count():
            self.capa.addWidget(linea_horizontal())
        self.capa.addWidget(widget)
        return widget


def seccion(titulo: str, tarjeta: QWidget, accion: QWidget | None = None) -> QWidget:
    """Encabezado de sección sobre una tarjeta, al estilo de Ajustes."""
    contenedor = QWidget()
    lay = QVBoxLayout(contenedor)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(6)
    cab = QHBoxLayout()
    cab.setContentsMargins(4, 0, 2, 0)
    cab.addWidget(EtiquetaSeccion(titulo))
    cab.addStretch(1)
    if accion is not None:
        cab.addWidget(accion)
    lay.addLayout(cab)
    lay.addWidget(tarjeta)
    return contenedor


class Chip(QPushButton):
    """Insignia pulsable con icono: estado de escala, ROI, etc."""

    def __init__(self, texto: str = '', icono: str | None = None, tipo: str = 'neutro', parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setIconSize(QSize(13, 13))
        self.establecer(texto, icono, tipo)

    def establecer(self, texto: str, icono: str | None = None, tipo: str = 'neutro') -> None:
        self.setText(texto)
        rol = {'ok': 'exito_texto', 'aviso': 'aviso_texto', 'error': 'error_texto',
               'info': 'acento'}.get(tipo, 'texto2')
        if icono:
            self.setIcon(iconos.icono(icono, rol))
        self.setProperty('chip', tipo)
        polir(self)


class Aviso(QFrame):
    """Recuadro de aviso en línea: información, advertencia, error o éxito."""
    cerrado = Signal()

    def __init__(self, texto: str = '', tipo: str = 'info', titulo: str = '', cerrable: bool = False,
                 parent=None):
        super().__init__(parent)
        self.setProperty('aviso', tipo)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 9, 10, 9)
        lay.setSpacing(9)
        self.icono = EtiquetaIcono(self._icono(tipo), 16, self._rol(tipo))
        lay.addWidget(self.icono, 0, Qt.AlignmentFlag.AlignTop)
        columna = QVBoxLayout()
        columna.setSpacing(2)
        self.titulo = etiqueta(titulo)
        f = self.titulo.font()
        f.setWeight(QFont.Weight.DemiBold)
        self.titulo.setFont(f)
        self.titulo.setVisible(bool(titulo))
        self.texto = etiqueta(texto, envolver=True)
        self.texto.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        columna.addWidget(self.titulo)
        columna.addWidget(self.texto)
        self.acciones = QHBoxLayout()
        self.acciones.setSpacing(6)
        self.acciones.addStretch(1)
        columna.addLayout(self.acciones)
        lay.addLayout(columna, 1)
        if cerrable:
            x = QToolButton()
            x.setIcon(iconos.icono('cerrar', 'texto2'))
            x.setIconSize(QSize(12, 12))
            x.setCursor(Qt.CursorShape.PointingHandCursor)
            x.clicked.connect(self._cerrar)
            lay.addWidget(x, 0, Qt.AlignmentFlag.AlignTop)

    @staticmethod
    def _icono(tipo):
        return {'info': 'info', 'aviso': 'aviso', 'error': 'error', 'ok': 'ok'}.get(tipo, 'info')

    @staticmethod
    def _rol(tipo):
        return {'info': 'acento', 'aviso': 'aviso_texto', 'error': 'error_texto',
                'ok': 'exito_texto'}.get(tipo, 'acento')

    def establecer(self, texto: str, tipo: str | None = None, titulo: str | None = None) -> None:
        if tipo:
            self.setProperty('aviso', tipo)
            self.icono.establecer(self._icono(tipo), self._rol(tipo))
            polir(self)
        if titulo is not None:
            self.titulo.setText(titulo)
            self.titulo.setVisible(bool(titulo))
        self.texto.setText(texto)

    def agregar_accion(self, texto: str, funcion) -> QPushButton:
        b = QPushButton(texto)
        b.setProperty('tipo', 'plano')
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(funcion)
        self.acciones.insertWidget(self.acciones.count() - 1, b)
        return b

    def limpiar_acciones(self) -> None:
        while self.acciones.count() > 1:
            item = self.acciones.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _cerrar(self):
        self.hide()
        self.cerrado.emit()


def sombra(widget: QWidget, radio: int = 28, desplazamiento: int = 8) -> None:
    efecto = QGraphicsDropShadowEffect(widget)
    efecto.setBlurRadius(radio)
    efecto.setOffset(0, desplazamiento)
    efecto.setColor(tema().color('sombra'))
    widget.setGraphicsEffect(efecto)


class _Superpuesto(QFrame):
    """Base de paneles flotantes anclados a un widget anfitrión."""

    def __init__(self, anfitrion: QWidget, nombre: str):
        super().__init__(anfitrion)
        self.setObjectName(nombre)
        self.anfitrion = anfitrion
        anfitrion.installEventFilter(self)
        self.hide()
        sombra(self, 30, 8)

    def eventFilter(self, objeto, evento):
        if objeto is self.anfitrion and evento.type() == QEvent.Type.Resize and self.isVisible():
            self._colocar()
        return False

    def _colocar(self):
        raise NotImplementedError


class Toast(_Superpuesto):
    """Mensaje breve que aparece en la parte inferior y desaparece solo."""

    def __init__(self, anfitrion: QWidget):
        super().__init__(anfitrion, 'Toast')
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 9, 10, 9)
        lay.setSpacing(9)
        self.icono = EtiquetaIcono('ok', 16, 'exito')
        self.texto = etiqueta('', envolver=True)
        self.texto.setMaximumWidth(520)
        self.boton = QPushButton()
        self.boton.setProperty('tipo', 'plano')
        self.boton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boton.hide()
        lay.addWidget(self.icono, 0, Qt.AlignmentFlag.AlignTop)
        lay.addWidget(self.texto, 1)
        lay.addWidget(self.boton)
        self._temporizador = QTimer(self)
        self._temporizador.setSingleShot(True)
        self._temporizador.timeout.connect(self.ocultar)
        self._accion = None
        self.boton.clicked.connect(self._ejecutar_accion)
        self._anim = QPropertyAnimation(self, b'pos', self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def mostrar(self, texto: str, tipo: str = 'ok', duracion: int = 4200, accion=None) -> None:
        nombre, rol = {'ok': ('ok', 'exito'), 'info': ('info', 'acento'), 'aviso': ('aviso', 'aviso'),
                       'error': ('error', 'error')}.get(tipo, ('info', 'acento'))
        self.icono.establecer(nombre, rol)
        self.texto.setText(texto)
        self._accion = accion[1] if accion else None
        self.boton.setText(accion[0] if accion else '')
        self.boton.setVisible(bool(accion))
        self.adjustSize()
        self._colocar(animar=not self.isVisible())
        self.show()
        self.raise_()
        self._temporizador.start(duracion)

    def anclar(self, widget: QWidget) -> None:
        """Coloca los mensajes sobre el borde inferior de `widget` cuando está visible."""
        self._ancla = widget

    def _destino(self) -> QPoint:
        a = self.anfitrion
        ancla = getattr(self, '_ancla', None)
        if ancla is not None and ancla.isVisible() and ancla.width() > self.width():
            base = ancla.mapTo(a, QPoint(ancla.width() // 2, ancla.height()))
            return QPoint(base.x() - self.width() // 2, base.y() - self.height() - 16)
        return QPoint(max(8, (a.width() - self.width()) // 2), a.height() - self.height() - 18)

    def _colocar(self, animar: bool = False):
        self.adjustSize()
        destino = self._destino()
        if animar:
            self.move(destino + QPoint(0, 24))
            self._anim.stop()
            self._anim.setStartValue(destino + QPoint(0, 24))
            self._anim.setEndValue(destino)
            self._anim.start()
        else:
            self.move(destino)

    def _ejecutar_accion(self):
        accion = self._accion
        self.ocultar()
        if accion:
            accion()

    def ocultar(self):
        self._temporizador.stop()
        self.hide()


class Hoja(_Superpuesto):
    """Aviso persistente anclado arriba al centro (similar a una hoja de macOS)."""

    def __init__(self, anfitrion: QWidget):
        super().__init__(anfitrion, 'Hoja')
        self.setMaximumWidth(560)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 10, 12)
        lay.setSpacing(12)
        self.icono = EtiquetaIcono('aviso', 26, 'aviso')
        lay.addWidget(self.icono, 0, Qt.AlignmentFlag.AlignTop)
        columna = QVBoxLayout()
        columna.setSpacing(4)
        self.titulo = etiqueta('')
        f = self.titulo.font()
        f.setWeight(QFont.Weight.DemiBold)
        f.setPointSizeF(f.pointSizeF() + 0.5)
        self.titulo.setFont(f)
        self.texto = etiqueta('', 'secundario', envolver=True)
        self.texto.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.detalle = QPlainTextEdit()
        self.detalle.setObjectName('Codigo')
        self.detalle.setReadOnly(True)
        self.detalle.setFixedHeight(150)
        self.detalle.hide()
        self.botones = QHBoxLayout()
        self.botones.setSpacing(8)
        columna.addWidget(self.titulo)
        columna.addWidget(self.texto)
        columna.addWidget(self.detalle)
        columna.addLayout(self.botones)
        lay.addLayout(columna, 1)
        cerrar = QToolButton()
        cerrar.setIcon(iconos.icono('cerrar', 'texto2'))
        cerrar.setIconSize(QSize(12, 12))
        cerrar.setToolTip('Cerrar')
        cerrar.setCursor(Qt.CursorShape.PointingHandCursor)
        cerrar.clicked.connect(self.hide)
        lay.addWidget(cerrar, 0, Qt.AlignmentFlag.AlignTop)

    def mostrar(self, titulo: str, texto: str, tipo: str = 'error', acciones=(), detalle: str = '') -> None:
        nombre, rol = {'error': ('error', 'error'), 'aviso': ('aviso', 'aviso'),
                       'info': ('info', 'acento'), 'ok': ('ok', 'exito')}.get(tipo, ('aviso', 'aviso'))
        self.icono.establecer(nombre, rol)
        self.titulo.setText(titulo)
        self.texto.setText(texto)
        self.detalle.setPlainText(detalle)
        self.detalle.hide()
        while self.botones.count():
            item = self.botones.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, (etiqueta_boton, funcion) in enumerate(acciones):
            b = QPushButton(etiqueta_boton)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            if i == 0:
                b.setProperty('tipo', 'primario')
            b.clicked.connect(lambda _=False, f=funcion: (self.hide(), f()))
            self.botones.addWidget(b)
        if detalle:
            d = QPushButton('Detalles técnicos')
            d.setProperty('tipo', 'plano')
            d.setCursor(Qt.CursorShape.PointingHandCursor)
            d.clicked.connect(lambda: (self.detalle.setVisible(not self.detalle.isVisible()),
                                       self._colocar()))
            self.botones.addWidget(d)
        self.botones.addStretch(1)
        self._colocar()
        self.show()
        self.raise_()

    def _colocar(self):
        ancho = min(560, max(360, self.anfitrion.width() - 40))
        capa = self.layout()
        capa.activate()
        alto = capa.heightForWidth(ancho) if capa.hasHeightForWidth() else capa.sizeHint().height()
        alto = max(alto, capa.minimumSize().height())
        self.setFixedSize(ancho, alto)
        self.move((self.anfitrion.width() - self.width()) // 2, 14)


class Popover(QWidget):
    """Ventana emergente redondeada con sombra, cerrada al hacer clic fuera."""

    def __init__(self, parent: QWidget | None = None, ancho: int = 340):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        externo = QVBoxLayout(self)
        externo.setContentsMargins(16, 10, 16, 20)
        self.marco = QFrame()
        self.marco.setObjectName('Popover')
        self.marco.setFixedWidth(ancho)
        sombra(self.marco, 32, 10)
        externo.addWidget(self.marco)
        self.contenido = QVBoxLayout(self.marco)
        self.contenido.setContentsMargins(16, 14, 16, 14)
        self.contenido.setSpacing(10)

    def mostrar_bajo(self, ancla: QWidget) -> None:
        self.adjustSize()
        global_ = ancla.mapToGlobal(QPoint(ancla.width() // 2, ancla.height()))
        x = global_.x() - self.width() // 2
        y = global_.y() - 4
        pantalla = QGuiApplication.screenAt(global_) or QGuiApplication.primaryScreen()
        if pantalla is not None:
            area = pantalla.availableGeometry()
            x = max(area.left() + 4, min(x, area.right() - self.width() - 4))
            y = min(y, area.bottom() - self.height())
        self.move(x, y)
        self.show()


class BotonIcono(QToolButton):
    """Botón plano con icono y texto opcional."""

    def __init__(self, nombre_icono: str, ayuda: str = '', texto: str | None = None,
                 alternable: bool = False, lado: int = 18, parent=None):
        super().__init__(parent)
        self.setIcon(iconos.icono(nombre_icono, 'texto', 'acento'))
        self.setIconSize(QSize(lado, lado))
        self.setToolTip(ayuda)
        self.setCheckable(alternable)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAutoRaise(True)
        if texto:
            self.setText(texto)
            self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.setProperty('texto', 'true')


class BotonBusqueda(QPushButton):
    """Botón con aspecto de campo de búsqueda y tecla de atajo, como Spotlight."""

    def __init__(self, texto: str = 'Buscar', atajo: str = 'Ctrl K', parent=None):
        super().__init__(parent)
        self._texto = texto
        self._atajo = atajo
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(196, 30)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

    def paintEvent(self, _):
        t = tema()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(t.color('borde'), 1) if self.underMouse() else Qt.PenStyle.NoPen)
        p.setBrush(t.color('control_hover') if self.underMouse() else t.color('busqueda'))
        p.drawRoundedRect(r, 8, 8)
        h = self.height()
        iconos.dibujar(p, QRectF(10, (h - 15) / 2, 15, 15), 'buscar', t.color('texto2'))
        p.setPen(t.color('texto3'))
        p.setFont(self.font())
        p.drawText(QRectF(32, 0, self.width() - 100, h), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
                   self._texto)
        f = QFont(self.font())
        f.setPointSizeF(max(7.0, f.pointSizeF() - 1.5))
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        ancho = p.fontMetrics().horizontalAdvance(self._atajo) + 12
        tecla = QRectF(self.width() - ancho - 7, (h - 18) / 2, ancho, 18)
        p.setPen(QPen(t.color('borde'), 1))
        p.setBrush(t.color('control'))
        p.drawRoundedRect(tecla, 4, 4)
        p.setPen(t.color('texto2'))
        p.drawText(tecla, int(Qt.AlignmentFlag.AlignCenter), self._atajo)


class CampoBusqueda(QLineEdit):
    def __init__(self, marcador: str = 'Buscar', parent=None):
        super().__init__(parent)
        self.setObjectName('Busqueda')
        self.setPlaceholderText(marcador)
        self.setClearButtonEnabled(True)
        self.addAction(iconos.icono('buscar', 'texto2'), QLineEdit.ActionPosition.LeadingPosition)


class BotonPrimario(QPushButton):
    """Botón principal azul con indicador de actividad."""

    def __init__(self, texto: str, nombre_icono: str | None = None, parent=None):
        super().__init__(texto, parent)
        self.setProperty('tipo', 'primario')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(34)
        self._texto = texto
        self._icono = nombre_icono
        if nombre_icono:
            self.setIcon(iconos.icono(nombre_icono, '#FFFFFF'))
            self.setIconSize(QSize(14, 14))
        self._angulo = 0
        self._giro = QTimer(self)
        self._giro.setInterval(16)
        self._giro.timeout.connect(self._avanzar)

    def ocupado(self, activo: bool, texto: str = 'Ejecutando…') -> None:
        if activo:
            self.setText('   ' + texto)
            self.setIcon(QIcon())
            self._giro.start()
        else:
            self._giro.stop()
            self.setText(self._texto)
            if self._icono:
                self.setIcon(iconos.icono(self._icono, '#FFFFFF'))
        self.update()

    def _avanzar(self):
        self._angulo = (self._angulo + 8) % 360
        self.update()

    def paintEvent(self, evento):
        super().paintEvent(evento)
        if self._giro.isActive():
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            ancho_texto = self.fontMetrics().horizontalAdvance(self.text().strip())
            x = (self.width() - ancho_texto) / 2 - 18
            r = QRectF(x, self.height() / 2 - 7, 14, 14)
            p.setPen(QPen(QColor(255, 255, 255, 70), 2))
            p.drawEllipse(r)
            p.setPen(QPen(QColor('#FFFFFF'), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(r, -self._angulo * 16, 100 * 16)


class EstadoVacio(QWidget):
    """Mensaje centrado para paneles sin contenido."""

    def __init__(self, nombre_icono: str, titulo: str, texto: str = '', parent=None,
                 compacto: bool = False):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(*((12, 8, 12, 8) if compacto else (24, 24, 24, 24)))
        lay.setSpacing(4 if compacto else 8)
        lay.addStretch(1)
        self.icono = EtiquetaIcono(nombre_icono, 28 if compacto else 40, 'texto3')
        lay.addWidget(self.icono, 0, Qt.AlignmentFlag.AlignHCenter)
        self.titulo = etiqueta(titulo)
        f = self.titulo.font()
        f.setPointSizeF(f.pointSizeF() + (0.5 if compacto else 2))
        f.setWeight(QFont.Weight.DemiBold)
        self.titulo.setFont(f)
        self.titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.titulo)
        self.texto = etiqueta(texto, 'secundario', envolver=True)
        self.texto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.texto.setMaximumWidth(560 if compacto else 420)
        # Centrado mediante márgenes elásticos: así el cálculo de altura del texto
        # envuelto es correcto y no se recorta.
        fila_texto = QHBoxLayout()
        fila_texto.addStretch(1)
        fila_texto.addWidget(self.texto, 10)
        fila_texto.addStretch(1)
        lay.addLayout(fila_texto)
        self.botones = QHBoxLayout()
        self.botones.setSpacing(8)
        self.botones.addStretch(1)
        self.botones.addStretch(1)
        lay.addSpacing(6)
        lay.addLayout(self.botones)
        lay.addStretch(1)

    def establecer(self, titulo: str, texto: str = '', nombre_icono: str | None = None) -> None:
        self.titulo.setText(titulo)
        self.texto.setText(texto)
        self.texto.setVisible(bool(texto))
        if nombre_icono:
            self.icono.establecer(nombre_icono)

    def agregar_boton(self, texto: str, funcion, primario: bool = False,
                      nombre_icono: str | None = None) -> QPushButton:
        b = QPushButton(texto)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        if primario:
            b.setProperty('tipo', 'primario')
        if nombre_icono:
            b.setIcon(iconos.icono(nombre_icono, '#FFFFFF' if primario else 'texto'))
            b.setIconSize(QSize(14, 14))
        b.clicked.connect(funcion)
        self.botones.insertWidget(self.botones.count() - 1, b)
        return b


class ResaltadorPython(QSyntaxHighlighter):
    """Coloreado sencillo de Python inspirado en Xcode."""
    _PALABRAS = re.compile(r'\b(' + '|'.join(keyword.kwlist) + r')\b')
    _NUMEROS = re.compile(r'\b\d+(\.\d+)?([eE][-+]?\d+)?\b')
    _FUNCIONES = re.compile(r'\b(def|class)\s+(\w+)')
    _LLAMADAS = re.compile(r'\b([A-Za-z_]\w*)(?=\()')
    _CADENAS = re.compile(r'(\"\"\"|\'\'\'|"[^"\n]*"|\'[^\'\n]*\')')
    _COMENTARIOS = re.compile(r'#[^\n]*')

    def __init__(self, documento):
        super().__init__(documento)
        tema().cambiado.connect(self.rehighlight)

    def _formato(self, claro: str, oscuro: str, negrita: bool = False) -> QTextCharFormat:
        f = QTextCharFormat()
        f.setForeground(QColor(oscuro if tema().oscuro else claro))
        if negrita:
            f.setFontWeight(QFont.Weight.DemiBold)
        return f

    def highlightBlock(self, texto: str) -> None:
        palabra = self._formato('#AD3DA4', '#FF7AB2', True)
        numero = self._formato('#272AD8', '#D9C97C')
        definicion = self._formato('#0B4F79', '#5DD8FF', True)
        llamada = self._formato('#326D74', '#67B7A4')
        cadena = self._formato('#C41A16', '#FC6A5D')
        comentario = self._formato('#5D6C79', '#7F8C98')
        for m in self._LLAMADAS.finditer(texto):
            self.setFormat(m.start(1), len(m.group(1)), llamada)
        for m in self._PALABRAS.finditer(texto):
            self.setFormat(m.start(), m.end() - m.start(), palabra)
        for m in self._NUMEROS.finditer(texto):
            self.setFormat(m.start(), m.end() - m.start(), numero)
        for m in self._FUNCIONES.finditer(texto):
            self.setFormat(m.start(2), len(m.group(2)), definicion)
        # Docstrings de varias líneas.
        self.setCurrentBlockState(0)
        inicio = 0
        if self.previousBlockState() != 1:
            inicio = texto.find('"""')
            if inicio < 0:
                inicio = None
        if inicio is not None:
            busqueda = inicio + 3 if self.previousBlockState() != 1 else 0
            fin = texto.find('"""', busqueda)
            if fin < 0:
                self.setCurrentBlockState(1)
                self.setFormat(inicio, len(texto) - inicio, cadena)
            else:
                self.setFormat(inicio, fin + 3 - inicio, cadena)
        for m in self._CADENAS.finditer(texto):
            if m.group(0) in ('"""', "'''"):
                continue
            self.setFormat(m.start(), m.end() - m.start(), cadena)
        for m in self._COMENTARIOS.finditer(texto):
            antes = texto[:m.start()]
            if antes.count('"') % 2 == 0 and antes.count("'") % 2 == 0:
                self.setFormat(m.start(), len(texto) - m.start(), comentario)
                break
