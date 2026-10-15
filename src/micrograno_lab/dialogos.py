"""Diálogos de MicroGrano Lab: cada flujo se resuelve en una sola ventana clara."""
from __future__ import annotations
from pathlib import Path
import unicodedata
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPlainTextEdit, QPushButton, QTextBrowser,
                               QVBoxLayout, QWidget)
from . import iconos
from .componentes import (Aviso, ControlSegmentado, EtiquetaIcono, EtiquetaSeccion, Tarjeta,
                          etiqueta, sombra)
from .tema import SISTEMA, tema
from .textos import ATAJOS, METADATOS


def normalizar(texto: str) -> str:
    """Minúsculas sin tildes, para búsquedas tolerantes."""
    descompuesto = unicodedata.normalize('NFD', str(texto).casefold())
    return ''.join(c for c in descompuesto if unicodedata.category(c) != 'Mn')


class DialogoBase(QDialog):
    """Cabecera con icono, cuerpo y botones al estilo de las hojas de macOS."""

    def __init__(self, parent, titulo: str, subtitulo: str = '', icono: str = 'info',
                 color: str | None = None, ancho: int = 480):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setModal(True)
        self.setMinimumWidth(ancho)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 20, 22, 16)
        lay.setSpacing(14)
        cabecera = QHBoxLayout()
        cabecera.setSpacing(14)
        cabecera.addWidget(EtiquetaIcono(icono, 40, insignia=color or SISTEMA['azul']),
                           0, Qt.AlignmentFlag.AlignTop)
        textos = QVBoxLayout()
        textos.setSpacing(3)
        t = etiqueta(titulo, 'titulo')
        textos.addWidget(t)
        if subtitulo:
            textos.addWidget(etiqueta(subtitulo, 'secundario', envolver=True))
        cabecera.addLayout(textos, 1)
        lay.addLayout(cabecera)
        self.cuerpo = QVBoxLayout()
        self.cuerpo.setSpacing(10)
        lay.addLayout(self.cuerpo, 1)
        self.botones = QDialogButtonBox()
        lay.addWidget(self.botones)
        self.boton_aceptar = None

    def agregar_botones(self, aceptar: str = 'Aceptar', cancelar: str | None = 'Cancelar') -> QPushButton:
        self.boton_aceptar = self.botones.addButton(aceptar, QDialogButtonBox.ButtonRole.AcceptRole)
        self.boton_aceptar.setProperty('tipo', 'primario')
        self.boton_aceptar.setDefault(True)
        if cancelar:
            self.botones.addButton(cancelar, QDialogButtonBox.ButtonRole.RejectRole)
        self.botones.accepted.connect(self.accept)
        self.botones.rejected.connect(self.reject)
        return self.boton_aceptar


def _campo_multilinea(texto: str = '', marcador: str = '', alto: int = 64) -> QPlainTextEdit:
    campo = QPlainTextEdit(texto)
    campo.setProperty('editable', 'true')
    campo.setPlaceholderText(marcador)
    campo.setFixedHeight(alto)
    campo.setTabChangesFocus(True)
    return campo


class DialogoConfirmarROI(DialogoBase):
    """Registro explícito de la revisión del dominio de análisis."""

    def __init__(self, parent, nombre_dato: str, miniatura=None, nota_previa: str = ''):
        super().__init__(parent, 'Confirmar la región de análisis',
                         f'«{nombre_dato}». La confirmación es una revisión del responsable, '
                         'no una detección automática.', 'recortar', SISTEMA['azul'], 500)
        fila = QHBoxLayout()
        fila.setSpacing(14)
        if miniatura is not None:
            vista = QLabel()
            vista.setPixmap(miniatura)
            vista.setFixedSize(miniatura.size() / max(miniatura.devicePixelRatio(), 1))
            fila.addWidget(vista, 0, Qt.AlignmentFlag.AlignTop)
        columna = QVBoxLayout()
        columna.setSpacing(8)
        columna.addWidget(etiqueta('Antes de confirmar, compruebe en la imagen:', envolver=True))
        self.sin_barra = QCheckBox('La región no contiene la barra de escala.')
        self.sin_texto = QCheckBox('La región no contiene texto ni anotaciones incrustadas.')
        for c in (self.sin_barra, self.sin_texto):
            columna.addWidget(c)
            c.toggled.connect(self._validar)
        columna.addStretch(1)
        fila.addLayout(columna, 1)
        self.cuerpo.addLayout(fila)
        self.cuerpo.addWidget(EtiquetaSeccion('Criterio registrado'))
        self.nota = _campo_multilinea(nota_previa or 'Región revisada: no contiene barra de escala ni anotaciones incrustadas.')
        self.nota.textChanged.connect(self._validar)
        self.cuerpo.addWidget(self.nota)
        self.agregar_botones('Confirmar región')
        self._validar()

    def _validar(self):
        listo = self.sin_barra.isChecked() and self.sin_texto.isChecked() and bool(self.nota.toPlainText().strip())
        self.boton_aceptar.setEnabled(listo)

    def texto_nota(self) -> str:
        return self.nota.toPlainText().strip()


class DialogoMetadatos(DialogoBase):
    def __init__(self, parent, nombre_dato: str, existentes: dict):
        super().__init__(parent, 'Metadatos del dato',
                         f'«{nombre_dato}». Deje vacío lo que no esté documentado: no se infieren '
                         'material, fases ni configuración.', 'etiqueta', SISTEMA['indigo'], 520)
        tarjeta = Tarjeta(margenes=(14, 12, 14, 12), espaciado=8)
        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.campos = {}
        for clave, texto, marcador in METADATOS:
            if clave == 'notas':
                campo = _campo_multilinea(existentes.get(clave, ''), 'Observaciones', 58)
            else:
                campo = QLineEdit(existentes.get(clave, ''))
                campo.setPlaceholderText(marcador)
            campo.setToolTip(f'Clave registrada: {clave}')
            form.addRow(texto, campo)
            self.campos[clave] = campo
        tarjeta.capa.addLayout(form)
        self.cuerpo.addWidget(tarjeta)
        self.agregar_botones('Guardar metadatos')

    def valores(self) -> dict[str, str]:
        salida = {}
        for clave, campo in self.campos.items():
            texto = campo.toPlainText() if isinstance(campo, QPlainTextEdit) else campo.text()
            salida[clave] = texto.strip()
        return salida


class DialogoAsociarFuente(DialogoBase):
    def __init__(self, parent, nombre_dato: str, candidatos: list[tuple[str, str, object]]):
        super().__init__(parent, 'Asociar imagen fuente',
                         f'«{nombre_dato}» heredará la escala y la región de la imagen elegida. '
                         'Deben tener la misma forma y representar la misma región.', 'enlace',
                         SISTEMA['cian'], 520)
        self.lista = QListWidget()
        self.lista.setObjectName('ListaRecientes')
        self.lista.setIconSize(QSize(44, 44))
        for id_, texto, pm in candidatos:
            item = QListWidgetItem(texto)
            if pm is not None:
                from PySide6.QtGui import QIcon
                item.setIcon(QIcon(pm))
            item.setData(Qt.ItemDataRole.UserRole, id_)
            self.lista.addItem(item)
        self.lista.setFixedHeight(min(240, 60 * max(1, len(candidatos)) + 8))
        self.lista.setCurrentRow(0)
        self.cuerpo.addWidget(EtiquetaSeccion('Imagen correspondiente'))
        self.cuerpo.addWidget(self.lista)
        self.cuerpo.addWidget(EtiquetaSeccion('Verificación de la alineación'))
        self.nota = _campo_multilinea('', 'Describa cómo comprobó la correspondencia píxel a píxel.')
        self.nota.textChanged.connect(self._validar)
        self.cuerpo.addWidget(self.nota)
        self.agregar_botones('Asociar')
        self._validar()

    def _validar(self):
        self.boton_aceptar.setEnabled(bool(self.nota.toPlainText().strip()) and self.lista.currentItem() is not None)

    def eleccion(self) -> tuple[str, str]:
        return self.lista.currentItem().data(Qt.ItemDataRole.UserRole), self.nota.toPlainText().strip()


class DialogoCarpetaNueva(DialogoBase):
    """Elige ubicación y nombre de una carpeta que todavía no existe."""

    def __init__(self, parent, titulo: str, subtitulo: str, nombre: str = '', ubicacion: str = '',
                 icono: str = 'guardar', boton: str = 'Guardar'):
        super().__init__(parent, titulo, subtitulo, icono, SISTEMA['azul'], 520)
        tarjeta = Tarjeta(margenes=(14, 12, 14, 12), espaciado=10)
        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(10)
        self.nombre = QLineEdit(nombre)
        self.nombre.setPlaceholderText('Nombre de la carpeta nueva')
        fila = QHBoxLayout()
        self.ubicacion = QLineEdit(ubicacion or str(Path.home()))
        elegir = QPushButton('Elegir…')
        elegir.clicked.connect(self._elegir)
        fila.addWidget(self.ubicacion, 1)
        fila.addWidget(elegir)
        form.addRow('Nombre', self.nombre)
        form.addRow('Ubicación', fila)
        tarjeta.capa.addLayout(form)
        self.cuerpo.addWidget(tarjeta)
        self.destino = etiqueta('', 'pie', envolver=True)
        self.destino.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.cuerpo.addWidget(self.destino)
        self.agregar_botones(boton)
        self.nombre.textChanged.connect(self._validar)
        self.ubicacion.textChanged.connect(self._validar)
        self._validar()
        self.nombre.setFocus()
        self.nombre.selectAll()

    def _elegir(self):
        carpeta = QFileDialog.getExistingDirectory(self, 'Elegir ubicación', self.ubicacion.text())
        if carpeta:
            self.ubicacion.setText(carpeta)

    def ruta(self) -> Path:
        return Path(self.ubicacion.text().strip()) / self.nombre.text().strip()

    def _validar(self):
        nombre = self.nombre.text().strip()
        padre = Path(self.ubicacion.text().strip()) if self.ubicacion.text().strip() else None
        problema = ''
        if not nombre:
            problema = 'Escriba un nombre para la carpeta.'
        elif Path(nombre).name != nombre or nombre in ('.', '..') or any(c in nombre for c in '<>:"/\\|?*'):
            problema = 'Use un nombre simple, sin rutas ni caracteres especiales.'
        elif padre is None or not padre.is_dir():
            problema = 'La ubicación no existe.'
        elif (padre / nombre).exists():
            problema = 'Esa carpeta ya existe. MicroGrano no sobrescribe datos: elija otro nombre.'
        if problema:
            self.destino.setText(f'⚠ {problema}')
            self.destino.setProperty('rol', 'error')
        else:
            self.destino.setText(f'Se creará: {(padre / nombre)}')
            self.destino.setProperty('rol', 'pie')
        self.destino.style().unpolish(self.destino)
        self.destino.style().polish(self.destino)
        self.boton_aceptar.setEnabled(not problema)


class DialogoExportarFigura(DialogoBase):
    """Exportación editorial en gris: título, descripción y fuente en un solo paso."""

    def __init__(self, parent, nombre_dato: str, miniatura=None, ubicacion: str = ''):
        super().__init__(parent, 'Exportar figura editorial',
                         f'«{nombre_dato}». Se genera un JPG o TIF en escala de grises a 300 ppp, '
                         'con una ficha JSON de procedencia.', 'exportar', SISTEMA['morado'], 560)
        fila = QHBoxLayout()
        fila.setSpacing(14)
        if miniatura is not None:
            vista = QLabel()
            vista.setPixmap(miniatura)
            fila.addWidget(vista, 0, Qt.AlignmentFlag.AlignTop)
        tarjeta = Tarjeta(margenes=(14, 12, 14, 12), espaciado=8)
        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        self.titulo = QLineEdit()
        self.titulo.setPlaceholderText('Título de la figura')
        self.descripcion = _campo_multilinea('', 'Qué se representa y con qué criterio', 56)
        self.fuente = _campo_multilinea('', 'Procedencia y crédito autorizado', 46)
        self.formato = ControlSegmentado(['TIFF', 'JPEG'])
        form.addRow('Título', self.titulo)
        form.addRow('Descripción', self.descripcion)
        form.addRow('Fuente', self.fuente)
        form.addRow('Formato', self.formato)
        tarjeta.capa.addLayout(form)
        fila.addWidget(tarjeta, 1)
        self.cuerpo.addLayout(fila)
        destino = QHBoxLayout()
        self.ruta = QLineEdit(str(Path(ubicacion or Path.home()) / 'figura.tif'))
        elegir = QPushButton('Elegir…')
        elegir.clicked.connect(self._elegir)
        destino.addWidget(self.ruta, 1)
        destino.addWidget(elegir)
        self.cuerpo.addWidget(EtiquetaSeccion('Archivo de destino'))
        self.cuerpo.addLayout(destino)
        self.cuerpo.addWidget(Aviso('La figura es una vista rasterizada. Los arreglos NPY del resultado '
                                    'siguen siendo el dato de medición. Si Times New Roman no está '
                                    'instalada se usará una fuente sustituta y se indicará en la ficha.', 'info'))
        self.formato.cambiado.connect(self._cambiar_formato)
        self.agregar_botones('Exportar')
        for w in (self.titulo, self.ruta):
            w.textChanged.connect(self._validar)
        for w in (self.descripcion, self.fuente):
            w.textChanged.connect(self._validar)
        self._validar()

    def _cambiar_formato(self, indice):
        ruta = Path(self.ruta.text().strip() or 'figura.tif')
        self.ruta.setText(str(ruta.with_suffix('.tif' if indice == 0 else '.jpg')))

    def _elegir(self):
        filtro = 'TIFF (*.tif)' if self.formato.indice() == 0 else 'JPEG (*.jpg)'
        ruta, _ = QFileDialog.getSaveFileName(self, 'Archivo de la figura', self.ruta.text(), filtro)
        if ruta:
            self.ruta.setText(ruta)

    def _validar(self):
        completo = all(x.strip() for x in (self.titulo.text(), self.descripcion.toPlainText(),
                                           self.fuente.toPlainText(), self.ruta.text()))
        self.boton_aceptar.setEnabled(completo)

    def valores(self) -> dict:
        return {'ruta': self.ruta.text().strip(), 'titulo': self.titulo.text().strip(),
                'descripcion': self.descripcion.toPlainText().strip(),
                'fuente': self.fuente.toPlainText().strip()}


class DialogoTexto(DialogoBase):
    def __init__(self, parent, titulo: str, html: str, icono: str = 'info',
                 color: str | None = None, ancho: int = 620, alto: int = 440):
        super().__init__(parent, titulo, '', icono, color, ancho)
        self.navegador = QTextBrowser()
        self.navegador.setObjectName('Documento')
        self.navegador.setOpenExternalLinks(True)
        self.navegador.setHtml(html)
        self.navegador.setMinimumHeight(alto)
        self.cuerpo.addWidget(self.navegador)
        self.agregar_botones('Cerrar', None)


class DialogoAtajos(DialogoBase):
    def __init__(self, parent):
        super().__init__(parent, 'Atajos de teclado', 'Trabaje más rápido sin soltar el teclado.',
                         'teclado', SISTEMA['gris'], 520)
        tarjeta = Tarjeta(margenes=(14, 10, 14, 10), espaciado=0)
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(16)
        rejilla.setVerticalSpacing(7)
        for i, (teclas, texto) in enumerate(ATAJOS):
            tecla = QLabel(teclas)
            tecla.setStyleSheet('QLabel { font-weight: 600; }')
            rejilla.addWidget(tecla, i, 0, Qt.AlignmentFlag.AlignRight)
            rejilla.addWidget(etiqueta(texto, 'secundario'), i, 1)
        tarjeta.capa.addLayout(rejilla)
        self.cuerpo.addWidget(tarjeta)
        self.agregar_botones('Cerrar', None)


class PaletaComandos(QDialog):
    """Búsqueda global al estilo de Spotlight: herramientas, datos y acciones."""

    def __init__(self, parent, entradas: list[dict]):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup
                         | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.entradas = entradas
        externo = QVBoxLayout(self)
        externo.setContentsMargins(24, 16, 24, 32)
        marco = QFrame()
        marco.setObjectName('Paleta')
        marco.setFixedWidth(640)
        sombra(marco, 40, 14)
        externo.addWidget(marco)
        lay = QVBoxLayout(marco)
        lay.setContentsMargins(14, 10, 14, 12)
        lay.setSpacing(8)
        fila = QHBoxLayout()
        fila.setSpacing(10)
        fila.addWidget(EtiquetaIcono('buscar', 22, 'texto2'))
        self.campo = QLineEdit()
        self.campo.setObjectName('BusquedaPaleta')
        self.campo.setPlaceholderText('Buscar herramientas, datos y acciones…')
        fila.addWidget(self.campo, 1)
        lay.addLayout(fila)
        self.lista = QListWidget()
        self.lista.setObjectName('ListaPaleta')
        self.lista.setIconSize(QSize(22, 22))
        self.lista.setFixedHeight(360)
        self.lista.setUniformItemSizes(True)
        lay.addWidget(self.lista)
        self.vacio = etiqueta('Sin coincidencias', 'secundario')
        self.vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vacio.hide()
        lay.addWidget(self.vacio)
        self.campo.textChanged.connect(self._filtrar)
        self.campo.returnPressed.connect(self._ejecutar_actual)
        self.lista.itemActivated.connect(self._ejecutar_item)
        self.lista.itemClicked.connect(self._ejecutar_item)
        self.campo.installEventFilter(self)
        self._elegido = None
        self._filtrar('')

    def eventFilter(self, objeto, evento):
        from PySide6.QtCore import QEvent
        if objeto is self.campo and evento.type() == QEvent.Type.KeyPress:
            tecla = evento.key()
            if tecla in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                fila = self.lista.currentRow() + (1 if tecla == Qt.Key.Key_Down else -1)
                visibles = [i for i in range(self.lista.count())]
                if visibles:
                    self.lista.setCurrentRow(max(0, min(len(visibles) - 1, fila)))
                return True
            if tecla == Qt.Key.Key_Escape:
                self.reject()
                return True
        return super().eventFilter(objeto, evento)

    def _filtrar(self, texto: str):
        consulta = normalizar(texto).split()
        self.lista.clear()
        coincidencias = []
        for e in self.entradas:
            heno = normalizar(e['titulo'] + ' ' + e.get('subtitulo', '') + ' ' + e.get('claves', ''))
            if all(q in heno for q in consulta):
                prioridad = 0 if consulta and normalizar(e['titulo']).startswith(consulta[0]) else 1
                coincidencias.append((prioridad, e))
        coincidencias.sort(key=lambda x: x[0])
        for _, e in coincidencias[:60]:
            item = QListWidgetItem(e['titulo'] + (f'   —   {e["subtitulo"]}' if e.get('subtitulo') else ''))
            if e.get('icono') is not None:
                item.setIcon(e['icono'])
            item.setData(Qt.ItemDataRole.UserRole, e)
            item.setSizeHint(QSize(0, 34))
            self.lista.addItem(item)
        self.vacio.setVisible(not coincidencias)
        if self.lista.count():
            self.lista.setCurrentRow(0)

    def _ejecutar_actual(self):
        item = self.lista.currentItem()
        if item is not None:
            self._ejecutar_item(item)

    def _ejecutar_item(self, item):
        self._elegido = item.data(Qt.ItemDataRole.UserRole)
        self.accept()

    def elegido(self):
        return self._elegido

    def abrir_sobre(self, ventana: QWidget) -> None:
        self.adjustSize()
        geo = ventana.geometry()
        self.move(geo.center().x() - self.width() // 2, geo.top() + 70)
        self.campo.setFocus()
