"""Ventana principal de MicroGrano Lab: explorar, ejecutar y conservar cada resultado.

La ventana solo compone la interfaz. Toda operación científica se delega en
`micrograno.Sesion`, que invoca las funciones registradas en el catálogo.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import html
import inspect
import json
import math
import time
import traceback
import numpy as np
import pandas as pd
from PySide6.QtCore import QSettings, QSize, Qt, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import (QAction, QActionGroup, QCursor, QDesktopServices, QFont, QIcon,
                           QKeySequence)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox,
                               QComboBox, QDialog, QFileDialog, QGridLayout, QHBoxLayout,
                               QHeaderView, QInputDialog, QLabel, QListWidget, QListWidgetItem,
                               QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton,
                               QScrollArea, QSizePolicy, QSplitter, QStackedWidget, QTableView,
                               QTextBrowser, QToolBar, QToolButton, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget)
from micrograno import EscalaEspacial, Sesion
from micrograno.archivos import (_jsonable, cargar_etiquetas, cargar_imagen, cargar_mascara,
                                 cargar_valores, exportar_figura, guardar_resultado,
                                 metadatos_entorno, sha256_archivo)
from micrograno.catalogo import AYUDA_PARAMETROS, CATALOGO, verificar_catalogo
from micrograno.visualizacion import preparar_vista
from . import iconos
from .componentes import (Aviso, BotonBusqueda, BotonIcono, BotonPrimario, CampoBusqueda, CampoNumero, Chip,
                          ControlSegmentado, EstadoVacio, EtiquetaIcono, FilaParametro, Hoja,
                          Interruptor, ResaltadorPython, SegmentosParametro, Selector,
                          Tarjeta, Toast, etiqueta, linea_vertical, seccion)
from .dialogos import (DialogoAsociarFuente, DialogoAtajos, DialogoCarpetaNueva,
                       DialogoConfirmarROI, DialogoExportarFigura, DialogoMetadatos, DialogoTexto,
                       PaletaComandos, normalizar)
from .paneles import EtiquetaRecortada, FilaDato, FilaPaso, PaginaBienvenida, TiraSalidas
from .tema import SISTEMA, asegurar_tema, familia_codigo, fuente_codigo, tema
from .textos import (DESTACADAS, ENTRADAS, GRUPOS, OPERACIONES, PESTANA_PREFERIDA,
                     PREFERENCIA_SALIDA, SIN_ENTRADA, TIPOS, descripcion_dato, etiqueta_clave,
                     etiqueta_generica, etiqueta_opcion, formatear_valor, meta_parametro,
                     nombre_salida, nombre_tipo, sugerencia_error)
from .visores import (COLORES_CONTORNO, OPCIONES_VISTA, ModeloTabla, PanelGrafica, ProxyTabla,
                      VisorImagen, miniatura)
from .aprendizaje import InterfazAprendizaje
from .flujo import (PASOS_APRENDIZAJE, nombre_version, origen_version, razon_bloqueo,
                    explicacion_entradas, explicacion_salida)
from .exportacion import exportar_versiones

GUIA = ('MicroGrano Lab — guía de trabajo\n\n'
        + '\n'.join(f'{i}. {paso["titulo"]}. {paso["descripcion"]}'
                    for i, paso in enumerate(PASOS_APRENDIZAJE, 1))
        + '''

En cada lección, revise qué hace la función, qué entrada necesita y qué produce. Ajuste los parámetros y ejecute. La pestaña Python muestra un ejemplo de uso de la biblioteca; el catálogo reúne todas las funciones.

Cada ejecución conserva sus salidas. Seleccione una y pulse «Continuar con esta versión» para usarla en la siguiente lección. En «Versiones» puede volver a la imagen original, los grises, la ROI o cualquier variante anterior. Una vista previa se conserva solo después de ejecutar.

«Guardar sesión» permite reabrir el análisis y conserva datos exactos, parámetros, contexto y reproducir.py. «Exportar todas las versiones» crea archivos NPY y TIFF compatibles, vistas PNG, tablas y un índice de procedencia. Los PNG son representaciones para visualizar; las mediciones deben conservar los datos exactos. Exportar no sustituye guardar la sesión.

Watershed necesita una máscara; medir objetos, etiquetas de instancias; las fracciones, clases. Revise las máscaras y los contornos sobre la imagen fuente. Pulse una fila de la tabla para destacar el objeto. Los intervalos estadísticos utilizan valores de campos o probetas independientes, no partículas como réplicas automáticas.

Calibre antes de recortar la barra de escala. La escala no se infiere de 100X o 200X; cada entrada puede tener su propia calibración. Modificarla no cambia medidas anteriores. Las demostraciones de cambio de muestreo eliminan la escala asociada.

Los valores iniciales son demostrativos, no parámetros validados para un material. Canny produce límites candidatos, no granos; las clases no identifican fases. Intercepción y ponderación planimétrica no constituyen la aplicación completa de ASTM E112.

Guarde la sesión antes de cerrar. El programa procesa las imágenes localmente.
''')

MODOS_VISTA = ('activo', 'resultado', 'lado', 'cortina')
TIPOS_IMPORTACION = (('Imagen', 'imagen'), ('Máscara binaria', 'mascara'), ('Red de límites', 'limites'),
                     ('Etiquetas de objetos', 'etiquetas'), ('Clases de intensidad', 'clases'),
                     ('Marcadores', 'marcadores'), ('Valores por campo (CSV)', 'valores'))
EXTENSIONES = {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.npy', '.csv', '.json'}
TEXTO_EJECUTAR = {'extraer_roi': 'Recortar región', 'calibrar_escala': 'Calcular escala',
                  'perfil_intensidad': 'Obtener perfil'}
# Operaciones rápidas que admiten vista previa sin registrarse en la sesión.
VISTA_PREVIA = {'convertir_grises', 'separar_canales', 'reducir_y_ampliar', 'cuantizar',
                'reescalar_percentiles', 'variantes_contraste', 'variantes_ruido', 'agregar_ruido',
                'top_hat', 'realzar_sobel', 'variantes_morfologicas', 'limpiar_mascara',
                'invertir_mascara', 'esqueletizar', 'umbralizar', 'detectar_canny',
                'etiquetar_componentes', 'limites_a_regiones', 'separar_watershed',
                'segmentar_clases', 'extraer_clase', 'obtener_limites'}
LIMITE_PREVIA_PX = 6_000_000


class Trabajo(QThread):
    correcto = Signal(object)
    fallo = Signal(str, str)

    def __init__(self, sesion, operacion, entradas, parametros, parent=None):
        super().__init__(parent)
        self.sesion = sesion
        self.operacion = operacion
        self.entradas = entradas
        self.parametros = parametros
        self.duracion = 0.0

    def run(self):
        inicio = time.perf_counter()
        try:
            resultado = self.sesion.ejecutar(self.operacion, self.entradas, self.parametros)
            self.duracion = time.perf_counter() - inicio
            self.correcto.emit(resultado)
        except Exception as exc:
            self.duracion = time.perf_counter() - inicio
            self.fallo.emit(str(exc), traceback.format_exc())


class TrabajoExportacion(QThread):
    correcto = Signal(object)
    fallo = Signal(str, str)

    def __init__(self, sesion, carpeta, parent=None):
        super().__init__(parent)
        self.sesion = sesion
        self.carpeta = carpeta

    def run(self):
        try:
            self.correcto.emit(exportar_versiones(self.sesion, self.carpeta))
        except Exception as exc:
            self.fallo.emit(str(exc), traceback.format_exc())


class TrabajoVistaPrevia(QThread):
    """Ejecuta la operación en una sesión temporal: aplica las mismas validaciones
    de la biblioteca, pero el resultado no se registra en la sesión del usuario."""
    listo = Signal(int, object)
    fallo = Signal(int, str)

    def __init__(self, secuencia, entradas, operacion, parametros, parent=None):
        super().__init__(parent)
        self.secuencia = secuencia
        self.datos_entrada = entradas
        self.operacion = operacion
        self.parametros = parametros

    def run(self):
        try:
            temporal = Sesion('Vista previa')
            ids = {}
            for rol, datos, tipo, nombre, metadatos in self.datos_entrada:
                ids[rol] = temporal.agregar(datos, tipo, nombre, metadatos)
            r, salidas = temporal.ejecutar(self.operacion, ids, self.parametros)
            self.listo.emit(self.secuencia, (r, salidas, temporal))
        except Exception as exc:
            self.fallo.emit(self.secuencia, str(exc))


def _mezclar(fondo: str, color: str, alfa: float) -> str:
    """Color opaco equivalente a `color` con opacidad `alfa` sobre `fondo` (para HTML)."""
    f = [int(fondo[i:i + 2], 16) for i in (1, 3, 5)]
    c = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(a + (b - a) * alfa):02X}' for a, b in zip(f, c))


def _hex(valor) -> str:
    return valor[0] if isinstance(valor, tuple) else valor


class VentanaPrincipal(InterfazAprendizaje, QMainWindow):
    def __init__(self, persistir: bool = False):
        super().__init__()
        asegurar_tema()
        verificar_catalogo()
        self.persistir = persistir
        self.setWindowIcon(iconos.icono_app())
        self.setAcceptDrops(True)
        self.sesion = Sesion()
        self.trabajo = None
        self._modificada = False
        self.op_actual = 'explorar_imagen'
        self.paso_actual = None
        self.campos: dict = {}
        self.entradas: dict = {}
        self.filas_parametro: dict = {}
        self.ultima_escala = None
        self.linea_referencia = None
        self.ultima_calibracion: dict = {}
        self.modo_linea = 'calibracion'
        self.ruta_sesion = None
        self.opciones_vista = dict(OPCIONES_VISTA)
        self.modo_vista = 'activo'
        self.acc: dict[str, QAction] = {}
        self._miniaturas: dict = {}
        self._sincronizando = False
        self._form_op = None
        self._ocupada = False
        self._explorar = False
        self._tira_previa = False
        self._clave_preferida = None
        self._ultima_carpeta = str(Path.home())
        self._recientes_memoria: list[str] = []
        self._aviso_escala = None
        self._previa = {'secuencia': 0, 'hilo': None, 'pendiente': False, 'resultado': None,
                        'salidas': None, 'sesion': None}
        self._temporizador_previa = QTimer(self)
        self._temporizador_previa.setSingleShot(True)
        self._temporizador_previa.setInterval(260)
        self._temporizador_previa.timeout.connect(self._lanzar_vista_previa)
        self._crear_acciones()
        self._crear_menu()
        self._crear_barra_superior()
        self._crear_contenido()
        self._llenar_catalogo()
        self._formulario()
        self._actualizar_datos()
        self._limpiar_resultados()
        self.acc['panel'].setChecked(False)
        self.modificada = False
        self._ajustar_tamano_inicial()
        if persistir:
            self._restaurar_estado()
        else:
            self.bienvenida.establecer_recientes([])
        tema().cambiado.connect(self._tema_cambiado)

    # ------------------------------------------------------------------
    # Estado general
    # ------------------------------------------------------------------

    @property
    def modificada(self) -> bool:
        return self._modificada

    @modificada.setter
    def modificada(self, valor: bool) -> None:
        self._modificada = bool(valor)
        self.setWindowModified(self._modificada)
        self._actualizar_titulo()

    def _actualizar_titulo(self):
        if self.ruta_sesion:
            nombre = Path(self.ruta_sesion).parent.name
            self.setWindowTitle(f'{nombre}[*] — MicroGrano Lab 1.0.0')
        elif self.sesion.artefactos:
            self.setWindowTitle('Sesión sin guardar[*] — MicroGrano Lab 1.0.0')
        else:
            self.setWindowTitle('MicroGrano Lab 1.0.0[*]')

    def _ajustar_tamano_inicial(self):
        pantalla = QApplication.primaryScreen()
        if pantalla is None:
            self.resize(1440, 900)
            return
        area = pantalla.availableGeometry()
        ancho = min(1500, int(area.width() * 0.94))
        alto = min(960, int(area.height() * 0.92))
        self.resize(ancho, alto)
        self.move(area.left() + (area.width() - ancho) // 2, area.top() + (area.height() - alto) // 2)

    def ventana_pequena(self) -> bool:
        pantalla = QApplication.primaryScreen()
        if pantalla is None:
            return False
        area = pantalla.availableGeometry()
        return area.width() < 1600 or area.height() < 960

    # ------------------------------------------------------------------
    # Acciones, menús y barra superior
    # ------------------------------------------------------------------

    def _accion(self, clave, texto, funcion, atajo=None, icono=None, alternable=False, ayuda=''):
        a = QAction(texto, self)
        if icono:
            a.setIcon(iconos.icono(icono))
        if atajo:
            if isinstance(atajo, (list, tuple)):
                a.setShortcuts([QKeySequence(x) for x in atajo])
            else:
                a.setShortcut(QKeySequence(atajo))
        a.setCheckable(alternable)
        if ayuda:
            a.setToolTip(ayuda)
            a.setStatusTip(ayuda)
        if alternable:
            a.toggled.connect(lambda estado, f=funcion: f(estado))
        else:
            a.triggered.connect(lambda *_, f=funcion: f())
        self.addAction(a)
        self.acc[clave] = a
        return a

    def _crear_acciones(self):
        A = self._accion
        A('nueva', 'Nueva sesión', self.nueva_sesion, 'Ctrl+N', 'nuevo')
        A('abrir', 'Abrir sesión…', self.abrir_sesion, 'Ctrl+O', 'abrir')
        A('guardar', 'Guardar sesión…', self.guardar_sesion, 'Ctrl+S', 'guardar',
          ayuda='Guarda datos exactos, parámetros y reproducir.py en una carpeta nueva.')
        for texto, tipo in TIPOS_IMPORTACION:
            A(f'importar_{tipo}', f'{texto}…', lambda t=tipo: self.importar(t),
              'Ctrl+I' if tipo == 'imagen' else None, TIPOS[tipo]['icono'])
        A('ejemplo', 'Aprender con una imagen sintética', self.cargar_ejemplo, None, 'matraz')
        A('demo', 'Conjunto completo para explorar el catálogo', self.cargar_demo, None, 'matraz')
        A('exportar_resultado', 'Exportar resultado…', self.exportar_resultado, 'Ctrl+E', 'exportar',
          ayuda='NPY exactos, tabla CSV y resumen JSON del paso seleccionado.')
        A('exportar_versiones', 'Exportar todas las versiones…', self.exportar_todas_versiones,
          'Ctrl+Alt+E', 'exportar', ayuda='Originales, grises, ROI y todas las variantes, con datos exactos y vistas PNG.')
        A('exportar_figura', 'Exportar figura editorial…', self.exportar_vista, 'Ctrl+Shift+E', 'imagen')
        A('salir', 'Salir', self.close, 'Ctrl+Q')
        A('ejecutar', 'Ejecutar herramienta', self.ejecutar_actual, ['Ctrl+Return', 'Ctrl+Enter'], 'ejecutar')
        A('buscar', 'Buscar herramientas y acciones…', self.abrir_paleta, 'Ctrl+K', 'buscar')
        A('buscar_lateral', 'Buscar en la lista de herramientas', self._enfocar_busqueda, 'Ctrl+F')
        A('restablecer', 'Restablecer parámetros', self.restablecer_parametros, None, 'restablecer')
        A('usar', 'Usar salida como dato activo', self.usar_salida, 'Ctrl+U', 'usar')
        A('recortar', 'Dibujar región de interés', self.dibujar_roi, 'R', 'recortar')
        A('confirmar_roi', 'Confirmar región de análisis…', self.confirmar_roi, None, 'ok')
        A('calibrar', 'Calibrar escala…', self.medir_referencia, None, 'regla')
        A('aplicar_escala', 'Aplicar escala calculada al dato activo…', self.aplicar_escala)
        A('asociar', 'Asociar imagen fuente…', self.asociar_fuente, None, 'enlace')
        A('metadatos', 'Anotar metadatos…', self.anotar_dato, None, 'etiqueta')
        A('mover', 'Mover', lambda: self._usar_herramienta('mover'), 'H', 'mover')
        A('regla', 'Regla', lambda: self._usar_herramienta('regla'), 'L', 'regla')
        A('perfil', 'Perfil de intensidad', lambda: self._usar_herramienta('perfil'), 'P', 'perfil')
        A('cancelar', 'Cancelar herramienta', self.cancelar_herramienta, 'Esc')
        A('ajustar', 'Ajustar a la ventana', lambda: self._zoom('ajustar'), ['Ctrl+0', 'F'], 'ajustar')
        A('zoom_100', 'Tamaño real', lambda: self._zoom('100'), 'Ctrl+1', 'tamano_real')
        A('acercar', 'Acercar', lambda: self._zoom('mas'), ['Ctrl++', 'Ctrl+='], 'zoom_mas')
        A('alejar', 'Alejar', lambda: self._zoom('menos'), 'Ctrl+-', 'zoom_menos')
        A('barra_lateral', 'Barra lateral', self._alternar_lateral, 'Ctrl+B', 'barra_lateral', alternable=True)
        A('inspector', 'Inspector', self._alternar_inspector, 'Ctrl+Shift+I', 'inspector', alternable=True)
        A('panel', 'Panel de resultados', self._alternar_panel, 'Ctrl+J', 'panel_inferior', alternable=True)
        for clave in ('barra_lateral', 'inspector', 'panel'):
            self.acc[clave].blockSignals(True)
            self.acc[clave].setChecked(True)
            self.acc[clave].blockSignals(False)
        self.grupo_modos = QActionGroup(self)
        for modo, texto in zip(MODOS_VISTA, ('Solo el dato activo', 'Solo el resultado', 'Lado a lado',
                                             'Cortina de comparación')):
            a = A(f'modo_{modo}', texto, lambda m=modo: self._cambiar_modo_vista(m))
            a.setCheckable(True)
            self.grupo_modos.addAction(a)
        self.acc['modo_activo'].setChecked(True)
        self.grupo_apariencia = QActionGroup(self)
        for modo, texto, icono in (('auto', 'Automática (sistema)', 'automatico'), ('claro', 'Clara', 'sol'),
                                   ('oscuro', 'Oscura', 'luna')):
            a = A(f'apariencia_{modo}', texto, lambda m=modo: self.cambiar_apariencia(m), None, icono)
            a.setCheckable(True)
            self.grupo_apariencia.addAction(a)
        self.acc[f'apariencia_{tema().modo}'].setChecked(True)
        A('guia', 'Guía de trabajo', self.mostrar_guia, 'F1', 'ayuda')
        A('flujo', 'Flujo del dato activo', self.mostrar_flujo, None, 'guia')
        A('atajos', 'Atajos de teclado', self.mostrar_atajos, 'Ctrl+/', 'teclado')
        A('entorno', 'Entorno instalado', self.mostrar_entorno, None, 'codigo')
        A('acerca', 'Alcance y créditos', self.mostrar_acerca, None, 'info')
        # Capas de la vista.
        self.superponer = A('superponer', 'Superponer resultados sobre la imagen fuente', self._capas_cambiadas)
        self.superponer.setCheckable(True)
        self.superponer.setChecked(True)
        self.rotulos = A('rotulos', 'Mostrar identificadores de objetos', self._capas_cambiadas)
        self.rotulos.setCheckable(True)
        self.accion_colores = A('colores', 'Colorear objetos y clases', self._capas_cambiadas)
        self.accion_colores.setCheckable(True)
        self.accion_colores.setChecked(True)
        self.accion_estirar = A('estirar', 'Estirar el contraste de la vista (no altera datos)', self._capas_cambiadas)
        self.accion_estirar.setCheckable(True)
        self.accion_sincronizar = A('sincronizar', 'Sincronizar el zoom de las dos vistas', lambda: None)
        self.accion_sincronizar.setCheckable(True)
        self.accion_sincronizar.setChecked(True)
        self.grupo_contorno = QActionGroup(self)
        for nombre, color in COLORES_CONTORNO:
            a = A(f'contorno_{color}', nombre, self._capas_cambiadas)
            a.setCheckable(True)
            a.setData(color)
            self.grupo_contorno.addAction(a)
            if color == OPCIONES_VISTA['color_contorno']:
                a.setChecked(True)

    def _crear_menu(self):
        barra = self.menuBar()
        archivo = barra.addMenu('Archivo')
        for clave in ('nueva', 'abrir'):
            archivo.addAction(self.acc[clave])
        self.menu_recientes = archivo.addMenu('Abrir reciente')
        self.menu_recientes.aboutToShow.connect(self._llenar_menu_recientes)
        archivo.addSeparator()
        self.menu_importar = archivo.addMenu(iconos.icono('importar'), 'Importar')
        for _, tipo in TIPOS_IMPORTACION:
            self.menu_importar.addAction(self.acc[f'importar_{tipo}'])
        archivo.addAction(self.acc['ejemplo'])
        archivo.addAction(self.acc['demo'])
        archivo.addSeparator()
        archivo.addAction(self.acc['guardar'])
        self.menu_exportar = QMenu('Exportar', self)
        self.menu_exportar.addAction(self.acc['exportar_versiones'])
        self.menu_exportar.addSeparator()
        self.menu_exportar.addAction(self.acc['exportar_resultado'])
        self.menu_exportar.addAction(self.acc['exportar_figura'])
        archivo.addAction(self.acc['exportar_resultado'])
        archivo.addAction(self.acc['exportar_versiones'])
        archivo.addAction(self.acc['exportar_figura'])
        archivo.addSeparator()
        archivo.addAction(self.acc['salir'])
        self.menu_dato = barra.addMenu('Dato')
        for clave in ('usar', None, 'recortar', 'confirmar_roi', None, 'calibrar', 'aplicar_escala', None,
                      'asociar', 'metadatos'):
            if clave is None:
                self.menu_dato.addSeparator()
            else:
                self.menu_dato.addAction(self.acc[clave])
        herramientas = barra.addMenu('Herramientas')
        herramientas.addAction(self.acc['ejecutar'])
        herramientas.addAction(self.acc['buscar'])
        herramientas.addAction(self.acc['restablecer'])
        herramientas.addSeparator()
        for clave in ('mover', 'recortar', 'regla', 'perfil', 'cancelar'):
            herramientas.addAction(self.acc[clave])
        ver = barra.addMenu('Ver')
        for clave in ('barra_lateral', 'inspector', 'panel'):
            ver.addAction(self.acc[clave])
        ver.addSeparator()
        for modo in MODOS_VISTA:
            ver.addAction(self.acc[f'modo_{modo}'])
        ver.addSeparator()
        for clave in ('ajustar', 'zoom_100', 'acercar', 'alejar'):
            ver.addAction(self.acc[clave])
        ver.addSeparator()
        self.menu_capas = QMenu('Capas', self)
        for clave in ('superponer', 'rotulos', 'colores', 'estirar', 'sincronizar'):
            self.menu_capas.addAction(self.acc[clave])
        submenu = self.menu_capas.addMenu('Color de los contornos')
        for a in self.grupo_contorno.actions():
            submenu.addAction(a)
        ver.addMenu(self.menu_capas)
        apariencia = ver.addMenu(iconos.icono('apariencia'), 'Apariencia')
        for a in self.grupo_apariencia.actions():
            apariencia.addAction(a)
        ayuda = barra.addMenu('Ayuda')
        for clave in ('guia', 'flujo', 'atajos', None, 'entorno', 'acerca'):
            if clave is None:
                ayuda.addSeparator()
            else:
                ayuda.addAction(self.acc[clave])

    def _espaciador(self) -> QWidget:
        w = QWidget()
        w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return w

    def _crear_barra_superior(self):
        barra = QToolBar('Barra principal')
        barra.setObjectName('BarraSuperior')
        barra.setMovable(False)
        barra.setFloatable(False)
        barra.setIconSize(QSize(18, 18))
        barra.toggleViewAction().setVisible(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, barra)
        self.setUnifiedTitleAndToolBarOnMac(True)
        self.barra = barra
        importar = BotonIcono('importar', 'Abrir una imagen (Ctrl+I). Otros datos: Archivo > Importar.', texto='Abrir imagen')
        importar.clicked.connect(lambda: self.importar('imagen'))
        barra.addWidget(importar)
        barra.addWidget(self._espaciador())
        self._accion_etiqueta_datos = barra.addWidget(etiqueta('Versión de trabajo', 'secundario'))
        self.datos = Selector()
        self.datos.setProperty('pildora', 'true')
        self.datos.setMinimumContentsLength(15)
        self.datos.setMaximumWidth(330)
        self.datos.setIconSize(QSize(18, 18))
        self.datos.setToolTip('Dato activo: la entrada que usan las herramientas por defecto')
        self.datos.currentIndexChanged.connect(self._activo_cambiado)
        self._accion_datos = barra.addWidget(self.datos)
        self.chip_escala = Chip('Sin escala', 'regla', 'aviso')
        self.chip_escala.clicked.connect(self._chip_escala)
        self.chip_roi = Chip('ROI sin confirmar', 'recortar', 'aviso')
        self.chip_roi.clicked.connect(self._chip_roi)
        self.chip_sintetico = Chip('Sintético', 'matraz', 'info')
        self.chip_sintetico.setToolTip('Dato artificial generado para comprobar el software; no es una micrografía.')
        self.chip_sintetico.clicked.connect(lambda: self.toast.mostrar(
            'Dato sintético: comprueba el software, no sustenta conclusiones metalográficas. '
            'Su escala de 0.5 µm/px es una convención de prueba.', 'info'))
        # El estado se explica junto a la imagen; las acciones siguen en el menú Dato.
        self._acciones_chip = [barra.addWidget(w) for w in (self.chip_escala, self.chip_roi, self.chip_sintetico)]
        mas = BotonIcono('puntos', 'Acciones del dato activo')
        mas.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        mas.setMenu(self.menu_dato)
        self._accion_mas = barra.addWidget(mas)
        barra.addWidget(self._espaciador())
        self.btn_guia = BotonIcono('guia', 'Flujo de trabajo: qué falta para el dato activo', texto='Guía')
        self.btn_guia.clicked.connect(self.mostrar_flujo)
        self.btn_guia.setText('Pasos')
        barra.addWidget(self.btn_guia)
        buscar = BotonBusqueda('Buscar', 'Ctrl K')
        buscar.setToolTip('Buscar herramientas, datos y acciones (Ctrl+K)')
        buscar.clicked.connect(self.abrir_paleta)
        guardar = BotonIcono('guardar', 'Guardar la sesión reproducible (Ctrl+S)', texto='Guardar')
        guardar.clicked.connect(lambda: self.guardar_sesion())
        barra.addWidget(guardar)
        exportar = BotonIcono('exportar', 'Exportar todas las versiones. Exportaciones individuales: menú Archivo.', texto='Exportar todo')
        exportar.clicked.connect(self.exportar_todas_versiones)
        barra.addWidget(exportar)
        self._botones_barra = [importar, mas, guardar, exportar, self.btn_guia]
        self.btn_guardar = guardar
        self.btn_exportar = exportar

    # ------------------------------------------------------------------
    # Contenido: bienvenida, barra lateral, lienzo, panel e inspector
    # ------------------------------------------------------------------

    def _crear_contenido(self):
        self.paginas = QStackedWidget()
        self.paginas.setObjectName('Paginas')
        self.setCentralWidget(self.paginas)
        self.bienvenida = PaginaBienvenida()
        self.bienvenida.abrir_imagen.connect(lambda: self.importar('imagen'))
        self.bienvenida.probar_demo.connect(self.cargar_ejemplo)
        self.bienvenida.abrir_sesion.connect(lambda: self.abrir_sesion())
        self.bienvenida.abrir_reciente.connect(lambda ruta: self.abrir_sesion(ruta))
        self.bienvenida.explorar.connect(self._explorar_sin_datos)
        self.paginas.addWidget(self.bienvenida)
        trabajo = QWidget()
        trabajo.setObjectName('Raiz')
        lay = QHBoxLayout(trabajo)
        lay.setContentsMargins(0, 0, 0, 0)
        self.divisor = QSplitter(Qt.Orientation.Horizontal)
        self.divisor.setHandleWidth(1)
        lay.addWidget(self.divisor)
        self.lateral = self._crear_lateral()
        self.divisor.addWidget(self.lateral)
        self.divisor.addWidget(self._crear_centro())
        self.inspector = self._crear_inspector()
        self.divisor.addWidget(self.inspector)
        self.divisor.setStretchFactor(0, 0)
        self.divisor.setStretchFactor(1, 1)
        self.divisor.setStretchFactor(2, 0)
        self.divisor.setCollapsible(1, False)
        self.divisor.setSizes([270, 820, 360])
        self.paginas.addWidget(trabajo)
        self.hoja = Hoja(self.paginas)
        self.toast = Toast(self.paginas)
        self.toast.anclar(self.lienzo)

    def _crear_lateral(self) -> QWidget:
        w = QWidget()
        w.setObjectName('BarraLateral')
        w.setMinimumWidth(258)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 8)
        lay.setSpacing(8)
        self.selector_lateral = ControlSegmentado([('Pasos', None), ('Versiones', None), ('Catálogo', None)],
                                                  expandir=True)
        lay.addWidget(self.selector_lateral)
        self.pila_lateral = QStackedWidget()
        lay.addWidget(self.pila_lateral, 1)
        self.pila_lateral.addWidget(self._crear_pasos())
        herramientas = QWidget()
        hl = QVBoxLayout(herramientas)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)
        self.buscar = CampoBusqueda('Buscar herramienta')
        self.buscar.textChanged.connect(self._filtrar)
        hl.addWidget(self.buscar)
        fila = QHBoxLayout()
        fila.setContentsMargins(2, 0, 0, 0)
        texto = etiqueta('Solo para el dato activo', 'secundario')
        texto.setToolTip('Muestra únicamente las herramientas que aceptan el tipo del dato activo.')
        fila.addWidget(texto, 1)
        self.solo_compatibles = Interruptor()
        self.solo_compatibles.toggled.connect(self._filtrar)
        fila.addWidget(self.solo_compatibles)
        hl.addLayout(fila)
        self.arbol = QTreeWidget()
        self.arbol.setObjectName('Herramientas')
        self.arbol.setHeaderHidden(True)
        self.arbol.setIndentation(0)
        self.arbol.setRootIsDecorated(False)
        self.arbol.setIconSize(QSize(20, 20))
        self.arbol.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.arbol.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.arbol.currentItemChanged.connect(self._operacion_elegida)
        self.arbol.itemClicked.connect(self._clic_arbol)
        hl.addWidget(self.arbol, 1)
        datos = QWidget()
        dl = QVBoxLayout(datos)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(0)
        dl.addWidget(etiqueta('Versiones conservadas', 'titulo'))
        dl.addWidget(etiqueta('Seleccione una versión para verla y trabajar desde ella. Todas se incluyen al exportar.',
                              'secundario', envolver=True))
        dl.addSpacing(10)
        self.lista_datos = QListWidget()
        self.lista_datos.setObjectName('ListaDatos')
        self.lista_datos.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.lista_datos.currentRowChanged.connect(self._dato_elegido_lista)
        self.lista_datos.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.lista_datos.customContextMenuRequested.connect(self._menu_lista_datos)
        dl.addWidget(self.lista_datos, 1)
        self.vacio_datos = EstadoVacio('datos', 'Sin datos', 'Importe una imagen o cargue el conjunto sintético.')
        dl.addWidget(self.vacio_datos, 1)
        self.pila_lateral.addWidget(datos)
        exportar = QPushButton('Exportar todas las versiones…')
        exportar.clicked.connect(self.exportar_todas_versiones)
        dl.addWidget(exportar)
        self.pila_lateral.addWidget(herramientas)
        self.selector_lateral.cambiado.connect(self.pila_lateral.setCurrentIndex)
        return w

    def _crear_centro(self) -> QWidget:
        self.divisor_centro = QSplitter(Qt.Orientation.Vertical)
        self.divisor_centro.setHandleWidth(1)
        superior = QWidget()
        sl = QVBoxLayout(superior)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)
        self.contexto_version = etiqueta('', 'secundario', envolver=True)
        self.contexto_version.setContentsMargins(14, 8, 14, 2)
        sl.addWidget(self.contexto_version)
        cabecera = QWidget()
        cabecera.setObjectName('CabeceraLienzo')
        cl = QHBoxLayout(cabecera)
        cl.setContentsMargins(10, 6, 10, 6)
        cl.setSpacing(4)
        self.selector_vista = ControlSegmentado([
            ('Trabajo', None, 'Muestra la versión de trabajo'),
            ('Resultado', None, 'Muestra la salida seleccionada del paso actual'),
            ('Comparar', None, 'Compara la versión de trabajo y el resultado'),
            ('Cortina', None, 'Arrastre la línea para comparar ambas imágenes')])
        self.selector_vista.boton(3).hide()
        self.selector_vista.cambiado.connect(lambda i: self._cambiar_modo_vista(MODOS_VISTA[i]))
        cl.addWidget(self.selector_vista)
        cl.addStretch(1)
        self.btn_mover = BotonIcono('mover', 'Mover y acercar con la rueda (H)', alternable=True)
        self.btn_roi = BotonIcono('recortar', 'Dibujar la región de interés (R)', alternable=True)
        self.btn_regla = BotonIcono('regla', 'Regla: medir una distancia (L)', alternable=True)
        self.btn_perfil = BotonIcono('perfil', 'Perfil de intensidad a lo largo de una línea (P)', alternable=True)
        self.perfil = self.btn_perfil
        self.grupo_herramientas = QButtonGroup(self)
        self.grupo_herramientas.setExclusive(True)
        for b, nombre in ((self.btn_mover, 'mover'), (self.btn_roi, 'roi'), (self.btn_regla, 'regla'),
                          (self.btn_perfil, 'perfil')):
            self.grupo_herramientas.addButton(b)
            b.clicked.connect(lambda _=False, n=nombre: self._usar_herramienta(n))
            b.hide()
        self.btn_mover.setChecked(True)
        cl.addSpacing(4)
        cl.addWidget(linea_vertical())
        cl.addSpacing(4)
        capas = BotonIcono('capas', 'Capas de la vista: contornos, identificadores y colores')
        capas.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        capas.setMenu(self.menu_capas)
        cl.addWidget(capas)
        resultados = BotonIcono('tabla', 'Mostrar u ocultar resumen, tabla, gráfica e historial', texto='Resultados')
        resultados.clicked.connect(self.acc['panel'].toggle)
        cl.addWidget(resultados)
        cl.addSpacing(4)
        cl.addWidget(linea_vertical())
        cl.addSpacing(4)
        alejar = BotonIcono('zoom_menos', 'Alejar (Ctrl+-)')
        alejar.clicked.connect(self.acc['alejar'].trigger)
        self.etiqueta_zoom = QPushButton('—')
        self.etiqueta_zoom.setProperty('tipo', 'sutil')
        self.etiqueta_zoom.setFixedWidth(58)
        self.etiqueta_zoom.setToolTip('Pulse para ver a tamaño real (Ctrl+1)')
        self.etiqueta_zoom.clicked.connect(lambda: self._zoom('100'))
        cl.addWidget(self.etiqueta_zoom)
        acercar = BotonIcono('zoom_mas', 'Acercar (Ctrl++)')
        acercar.clicked.connect(self.acc['acercar'].trigger)
        ajustar = BotonIcono('ajustar', 'Ajustar a la ventana (F)')
        ajustar.clicked.connect(self.acc['ajustar'].trigger)
        cl.addWidget(ajustar)
        sl.addWidget(cabecera)
        lienzo = QWidget()
        lienzo.setObjectName('Lienzo')
        self.lienzo = lienzo
        ll = QHBoxLayout(lienzo)
        ll.setContentsMargins(0, 0, 0, 0)
        self.divisor_visores = QSplitter(Qt.Orientation.Horizontal)
        self.divisor_visores.setHandleWidth(2)
        self.visor_entrada = VisorImagen()
        self.visor_salida = VisorImagen()
        self.visor_salida.limpiar('Sin resultado', 'Ejecute una herramienta para ver aquí su salida.', 'destello')
        for v in (self.visor_entrada, self.visor_salida):
            v.zoom_cambiado.connect(self._zoom_visor)
            v.vista_cambiada.connect(lambda v=v: self._sincronizar_desde(v))
            self.divisor_visores.addWidget(v)
        self.visor_entrada.roi_elegida.connect(self._roi_elegida)
        self.visor_entrada.linea_elegida.connect(self._linea_elegida)
        self.visor_entrada.herramienta_cambiada.connect(self._herramienta_cambiada)
        vacio = self.visor_entrada.estado_vacio()
        vacio.agregar_boton('Importar imagen…', lambda: self.importar('imagen'), True, 'importar')
        vacio.agregar_boton('Datos sintéticos', self.cargar_demo, False, 'matraz')
        ll.addWidget(self.divisor_visores)
        sl.addWidget(lienzo, 1)
        self.caja_tira = QWidget()
        self.caja_tira.setObjectName('TiraContenedor')
        tl = QHBoxLayout(self.caja_tira)
        tl.setContentsMargins(14, 6, 12, 6)
        tl.setSpacing(12)
        info = QWidget()
        info.setFixedWidth(125)
        il = QVBoxLayout(info)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(2)
        self.titulo_tira = EtiquetaRecortada('')
        f = self.titulo_tira.font()
        f.setWeight(QFont.Weight.DemiBold)
        self.titulo_tira.setFont(f)
        self.sub_tira = etiqueta('', 'pie', envolver=True)
        il.addStretch(1)
        il.addWidget(self.titulo_tira)
        il.addWidget(self.sub_tira)
        il.addStretch(1)
        tl.addWidget(info)
        self.tira = TiraSalidas()
        self.salidas = self.tira
        self.tira.currentRowChanged.connect(self._salida_elegida)
        self.tira.itemDoubleClicked.connect(lambda *_: self.usar_salida())
        tl.addWidget(self.tira, 1)
        acciones = QVBoxLayout()
        acciones.setSpacing(6)
        self.usar = QPushButton('Continuar con esta versión')
        self.usar.setProperty('tipo', 'primario')
        self.usar.setIcon(iconos.icono('usar', '#FFFFFF'))
        self.usar.setIconSize(QSize(14, 14))
        self.usar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.usar.setToolTip('La salida pasa a ser la entrada de las siguientes herramientas (Ctrl+U). '
                             'El dato anterior sigue disponible.')
        self.usar.clicked.connect(self.continuar_salida)
        exportar_salida = QPushButton('Exportar figura…')
        exportar_salida.setProperty('tipo', 'sutil')
        exportar_salida.setIcon(iconos.icono('exportar', 'texto'))
        exportar_salida.clicked.connect(lambda: self.exportar_vista(self.tira.currentData()))
        self.exportar_salida_btn = exportar_salida
        acciones.addStretch(1)
        acciones.addWidget(self.usar)
        acciones.addWidget(exportar_salida)
        acciones.addStretch(1)
        tl.addLayout(acciones)
        sl.addWidget(self.caja_tira)
        self.divisor_centro.addWidget(superior)
        self.panel_inferior = self._crear_panel_inferior()
        self.divisor_centro.addWidget(self.panel_inferior)
        self.divisor_centro.setStretchFactor(0, 1)
        self.divisor_centro.setStretchFactor(1, 0)
        self.divisor_centro.setCollapsible(0, False)
        self.divisor_centro.setSizes([620, 240])
        self._cambiar_modo_vista('activo')
        return self.divisor_centro

    def _crear_panel_inferior(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName('PanelInferior')
        panel.setMinimumHeight(150)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(0)
        cabecera = QWidget()
        cabecera.setObjectName('CabeceraPanel')
        cl = QHBoxLayout(cabecera)
        cl.setContentsMargins(10, 6, 10, 6)
        cl.setSpacing(8)
        self.selector_resultados = ControlSegmentado([
            ('Resumen', 'resumen'), ('Tabla', 'tabla'), ('Gráfica', 'grafica'),
            ('Historial', 'historial'), ('Script', 'codigo')])
        cl.addWidget(self.selector_resultados)
        cl.addStretch(1)
        self.acciones_panel = QStackedWidget()
        self.acciones_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.acciones_panel.addWidget(QWidget())
        tabla_acc = QWidget()
        ta = QHBoxLayout(tabla_acc)
        ta.setContentsMargins(0, 0, 0, 0)
        ta.setSpacing(4)
        self.filtro_tabla = CampoBusqueda('Filtrar filas')
        self.filtro_tabla.setFixedWidth(200)
        ta.addWidget(self.filtro_tabla)
        copiar_tabla = BotonIcono('copiar', 'Copiar la tabla (pegable en una hoja de cálculo)')
        copiar_tabla.clicked.connect(self._copiar_tabla)
        exportar_csv = BotonIcono('exportar', 'Guardar la tabla como CSV')
        exportar_csv.clicked.connect(self._exportar_csv)
        ta.addWidget(copiar_tabla)
        ta.addWidget(exportar_csv)
        self.acciones_panel.addWidget(tabla_acc)
        self.acciones_panel.addWidget(QWidget())
        hist_acc = QWidget()
        ha = QHBoxLayout(hist_acc)
        ha.setContentsMargins(0, 0, 0, 0)
        reutilizar = QPushButton('Reutilizar parámetros')
        reutilizar.setProperty('tipo', 'sutil')
        reutilizar.setIcon(iconos.icono('restablecer', 'texto'))
        reutilizar.setToolTip('Abre la herramienta del paso elegido con sus entradas y parámetros')
        reutilizar.clicked.connect(lambda: self.reutilizar_paso())
        ha.addWidget(reutilizar)
        self.acciones_panel.addWidget(hist_acc)
        script_acc = QWidget()
        sa = QHBoxLayout(script_acc)
        sa.setContentsMargins(0, 0, 0, 0)
        copiar_script = QPushButton('Copiar')
        copiar_script.setProperty('tipo', 'sutil')
        copiar_script.setIcon(iconos.icono('copiar', 'texto'))
        copiar_script.clicked.connect(lambda: (QApplication.clipboard().setText(self.codigo_sesion.toPlainText()),
                                               self.toast.mostrar('Script copiado al portapapeles.', 'ok', 2200)))
        sa.addWidget(copiar_script)
        self.acciones_panel.addWidget(script_acc)
        cl.addWidget(self.acciones_panel)
        pl.addWidget(cabecera)
        self.pila_resultados = QStackedWidget()
        resumen = QWidget()
        rl = QVBoxLayout(resumen)
        rl.setContentsMargins(14, 8, 14, 6)
        rl.setSpacing(6)
        self.fila_sugerencias = QWidget()
        self._capa_sugerencias = QHBoxLayout(self.fila_sugerencias)
        self._capa_sugerencias.setContentsMargins(0, 0, 0, 0)
        self._capa_sugerencias.setSpacing(6)
        rl.addWidget(self.fila_sugerencias)
        self.pila_resumen = QStackedWidget()
        self.vacio_resumen = EstadoVacio('resumen', 'Sin resultados todavía',
                                         'Elija una herramienta en la barra lateral, revise sus entradas y '
                                         'parámetros en el inspector y pulse Ejecutar.', compacto=True)
        self.resumen = QTextBrowser()
        self.resumen.setOpenLinks(False)
        self.pila_resumen.addWidget(self.vacio_resumen)
        self.pila_resumen.addWidget(self.resumen)
        rl.addWidget(self.pila_resumen, 1)
        self.pila_resultados.addWidget(resumen)
        self.tabla = QTableView()
        self.modelo = ModeloTabla()
        self.proxy = ProxyTabla(self)
        self.proxy.setSourceModel(self.modelo)
        self.tabla.setModel(self.proxy)
        self.tabla.setSortingEnabled(True)
        self.tabla.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.proxy.sort(-1)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)
        self.tabla.setWordWrap(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.verticalHeader().setDefaultSectionSize(26)
        self.tabla.horizontalHeader().setHighlightSections(False)
        self.tabla.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.tabla.clicked.connect(self._fila_elegida)
        self.filtro_tabla.textChanged.connect(self.proxy.setFilterFixedString)
        self.pila_tabla = QStackedWidget()
        self.vacio_tabla = EstadoVacio('tabla', 'Sin tabla', 'Este resultado no tiene filas. Las herramientas de '
                                       'medición y los histogramas producen tablas.', compacto=True)
        self.pila_tabla.addWidget(self.vacio_tabla)
        self.pila_tabla.addWidget(self.tabla)
        self.pila_resultados.addWidget(self.pila_tabla)
        self.panel_grafica = PanelGrafica()
        self.pila_resultados.addWidget(self.panel_grafica)
        self.historial = QListWidget()
        self.historial.setObjectName('Historial')
        self.historial.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.historial.currentRowChanged.connect(self._historial_elegido)
        self.historial.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.historial.customContextMenuRequested.connect(self._menu_historial)
        self.pila_historial = QStackedWidget()
        self.vacio_historial = EstadoVacio('historial', 'Historial vacío',
                                           'Cada operación ejecutada queda registrada aquí con sus parámetros.', compacto=True)
        self.pila_historial.addWidget(self.vacio_historial)
        self.pila_historial.addWidget(self.historial)
        self.pila_resultados.addWidget(self.pila_historial)
        self.codigo_sesion = QPlainTextEdit()
        self.codigo_sesion.setObjectName('Codigo')
        self.codigo_sesion.setReadOnly(True)
        self.codigo_sesion.setFont(fuente_codigo(9))
        self.codigo_sesion.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._resaltador_sesion = ResaltadorPython(self.codigo_sesion.document())
        contenedor_codigo = QWidget()
        cc = QVBoxLayout(contenedor_codigo)
        cc.setContentsMargins(12, 8, 12, 10)
        cc.addWidget(self.codigo_sesion)
        self.pila_resultados.addWidget(contenedor_codigo)
        self.selector_resultados.cambiado.connect(self._cambiar_pestana_indice)
        pl.addWidget(self.pila_resultados, 1)
        return panel

    def _crear_inspector(self) -> QWidget:
        w = QWidget()
        w.setObjectName('Inspector')
        w.setMinimumWidth(300)
        w.setMaximumWidth(560)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        cabecera = QWidget()
        cl = QVBoxLayout(cabecera)
        cl.setContentsMargins(16, 14, 16, 8)
        cl.setSpacing(8)
        fila = QHBoxLayout()
        fila.setSpacing(12)
        self.icono_op = EtiquetaIcono('dato', 40, insignia=SISTEMA['azul'])
        fila.addWidget(self.icono_op, 0, Qt.AlignmentFlag.AlignTop)
        textos = QVBoxLayout()
        textos.setSpacing(1)
        self.titulo_op = etiqueta('', 'titulo', envolver=True)
        self.subtitulo_op = etiqueta('', 'pie', envolver=True)
        textos.addWidget(self.titulo_op)
        textos.addWidget(self.subtitulo_op)
        fila.addLayout(textos, 1)
        cl.addLayout(fila)
        self.descripcion_op = etiqueta('', 'secundario', envolver=True)
        cl.addWidget(self.descripcion_op)
        self.selector_inspector = ControlSegmentado([('Aplicar', None), ('Aprender', None),
                                                     ('Python', None)], expandir=True)
        cl.addWidget(self.selector_inspector)
        lay.addWidget(cabecera)
        self.pila_inspector = QStackedWidget()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.pila_inspector.addWidget(self.scroll)
        pagina_ayuda = QWidget()
        al = QVBoxLayout(pagina_ayuda)
        al.setContentsMargins(16, 4, 16, 12)
        self.ayuda = QTextBrowser()
        self.ayuda.setObjectName('Documento')
        self.ayuda.setOpenExternalLinks(True)
        al.addWidget(self.ayuda)
        self.pila_inspector.addWidget(pagina_ayuda)
        pagina_codigo = QWidget()
        pc = QVBoxLayout(pagina_codigo)
        pc.setContentsMargins(16, 4, 16, 12)
        pc.setSpacing(6)
        fila_codigo = QHBoxLayout()
        self.ver_implementacion = QCheckBox('Ver implementación')
        self.ver_implementacion.toggled.connect(self._render_codigo)
        fila_codigo.addWidget(self.ver_implementacion, 1)
        copiar = QPushButton('Copiar')
        copiar.setProperty('tipo', 'sutil')
        copiar.setIcon(iconos.icono('copiar', 'texto'))
        copiar.clicked.connect(lambda: (QApplication.clipboard().setText(self.codigo.toPlainText()),
                                        self.toast.mostrar('Código copiado al portapapeles.', 'ok', 2200)))
        fila_codigo.addWidget(copiar)
        pc.addLayout(fila_codigo)
        self.codigo = QPlainTextEdit()
        self.codigo.setObjectName('Codigo')
        self.codigo.setReadOnly(True)
        self.codigo.setFont(fuente_codigo(9))
        self.codigo.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._resaltador = ResaltadorPython(self.codigo.document())
        pc.addWidget(self.codigo, 1)
        self.pila_inspector.addWidget(pagina_codigo)
        self.selector_inspector.cambiado.connect(self.pila_inspector.setCurrentIndex)
        lay.addWidget(self.pila_inspector, 1)
        pie = QWidget()
        pie.setObjectName('PieInspector')
        pl = QVBoxLayout(pie)
        pl.setContentsMargins(16, 10, 16, 12)
        pl.setSpacing(8)
        self.requisitos = etiqueta('', 'secundario', envolver=True)
        pl.addWidget(self.requisitos)
        self.btn_resolver_roi = QPushButton('Revisar y confirmar ROI…')
        self.btn_resolver_roi.clicked.connect(self._confirmar_entrada_roi)
        pl.addWidget(self.btn_resolver_roi)
        self.btn_resolver_escala = QPushButton('Calibrar la entrada…')
        self.btn_resolver_escala.clicked.connect(self._calibrar_entrada_principal)
        pl.addWidget(self.btn_resolver_escala)
        self.fila_previa = QWidget()
        fp = QHBoxLayout(self.fila_previa)
        fp.setContentsMargins(0, 0, 0, 0)
        fp.setSpacing(8)
        fp.addWidget(EtiquetaIcono('ojo', 16, 'texto2'))
        columna = QVBoxLayout()
        columna.setSpacing(0)
        columna.addWidget(etiqueta('Vista previa en vivo'))
        self.estado_previa = etiqueta('Recalcula al cambiar parámetros, sin registrar.', 'pie', envolver=True)
        columna.addWidget(self.estado_previa)
        fp.addLayout(columna, 1)
        self.interruptor_previa = Interruptor()
        self.interruptor_previa.setToolTip('Muestra el resultado mientras ajusta los parámetros. '
                                           'No se registra en la sesión hasta pulsar Ejecutar.')
        self.interruptor_previa.toggled.connect(self._alternar_vista_previa)
        fp.addWidget(self.interruptor_previa)
        pl.addWidget(self.fila_previa)
        self.aplicar = QPushButton('Aplicar escala al dato activo…')
        self.aplicar.setIcon(iconos.icono('regla', 'texto'))
        self.aplicar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.aplicar.clicked.connect(self.aplicar_escala)
        self.aplicar.setEnabled(False)
        pl.addWidget(self.aplicar)
        self.ejecutar_btn = BotonPrimario('Ejecutar', 'ejecutar')
        self.ejecutar_btn.setToolTip('Ejecuta la herramienta y añade sus salidas a la sesión (Ctrl+Enter)')
        self.ejecutar_btn.clicked.connect(self.ejecutar_actual)
        pl.addWidget(self.ejecutar_btn)
        lay.addWidget(pie)
        return w

    # ------------------------------------------------------------------
    # Catálogo de herramientas
    # ------------------------------------------------------------------

    def _llenar_catalogo(self):
        self.arbol.blockSignals(True)
        self.arbol.clear()
        self.items: dict[str, QTreeWidgetItem] = {}
        self.grupos_items: dict[str, QTreeWidgetItem] = {}
        fuente_grupo = QFont(self.arbol.font())
        fuente_grupo.setPointSizeF(max(7.5, fuente_grupo.pointSizeF() - 1.5))
        fuente_grupo.setWeight(QFont.Weight.DemiBold)
        fuente_grupo.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.6)
        orden = [op for paso in PASOS_APRENDIZAJE for op in paso['operaciones']]
        for op in (CATALOGO[id_] for id_ in orden):
            if op.grupo not in self.grupos_items:
                g = QTreeWidgetItem([op.grupo.upper()])
                g.setFlags(Qt.ItemFlag.ItemIsEnabled)
                g.setFont(0, fuente_grupo)
                g.setSizeHint(0, QSize(0, 30))
                g.setToolTip(0, GRUPOS.get(op.grupo, {}).get('resumen', ''))
                self.arbol.addTopLevelItem(g)
                self.grupos_items[op.grupo] = g
            meta = OPERACIONES.get(op.id, {})
            color = GRUPOS.get(op.grupo, {}).get('color', SISTEMA['azul'])
            item = QTreeWidgetItem([op.titulo])
            item.setIcon(0, iconos.icono_insignia(meta.get('icono', 'dato'), color))
            item.setData(0, Qt.ItemDataRole.UserRole, op.id)
            item.setSizeHint(0, QSize(0, 30))
            self.grupos_items[op.grupo].addChild(item)
            self.items[op.id] = item
        self.arbol.collapseAll()
        self._colorear_arbol()
        self.arbol.blockSignals(False)
        self._seleccionar_item_arbol(self.op_actual)

    def _colorear_arbol(self):
        gris = tema().color('texto2')
        for g in self.grupos_items.values():
            g.setForeground(0, gris)
        self._actualizar_disponibilidad()

    def _actualizar_disponibilidad(self):
        if not hasattr(self, 'items'):
            return
        tipos = {a.tipo for a in self.sesion.artefactos.values()}
        normal, tenue = tema().color('texto'), tema().color('texto3')
        for id_, item in self.items.items():
            op = CATALOGO[id_]
            faltan = [e for e in op.entradas if not e.opcional and not (set(e.tipos) & tipos)]
            item.setForeground(0, tenue if faltan else normal)
            texto = f'{op.titulo}\n\n{OPERACIONES.get(id_, {}).get("resumen", "")}'
            if faltan:
                necesita = '; '.join(f'{ENTRADAS.get(e.nombre, e.nombre)} ({", ".join(nombre_tipo(t) for t in e.tipos)})'
                                     for e in faltan)
                texto += f'\n\nNecesita: {necesita}.'
            texto += f'\n\nmicrograno.nucleo.{id_} · Manuscrito {op.libro}'
            item.setToolTip(0, texto)

    def _clic_arbol(self, item, _columna=0):
        if item is not None and item.data(0, Qt.ItemDataRole.UserRole) is None:
            item.setExpanded(not item.isExpanded())

    def _filtrar(self, *_):
        if not hasattr(self, 'items'):
            return
        consulta = normalizar(self.buscar.text()).split()
        activo = self.sesion.artefactos.get(self.datos.currentData())
        solo = self.solo_compatibles.isChecked() and activo is not None
        for id_, item in self.items.items():
            op = CATALOGO[id_]
            heno = normalizar(f'{id_} {op.titulo} {op.grupo} {OPERACIONES.get(id_, {}).get("resumen", "")}')
            visible = all(q in heno for q in consulta)
            if solo:
                visible = visible and bool(op.entradas) and activo.tipo in op.entradas[0].tipos
            item.setHidden(not visible)
        for g in self.grupos_items.values():
            hijos = [g.child(i) for i in range(g.childCount())]
            g.setHidden(all(h.isHidden() for h in hijos))
            if consulta or solo:
                g.setExpanded(True)

    def _enfocar_busqueda(self):
        self.acc['barra_lateral'].setChecked(True)
        self.selector_lateral.establecer(2, emitir=True)
        self.buscar.setFocus()
        self.buscar.selectAll()

    def _seleccionar_item_arbol(self, id_):
        item = self.items.get(id_)
        if item is None:
            return
        if item.isHidden():
            self.buscar.blockSignals(True)
            self.buscar.clear()
            self.buscar.blockSignals(False)
            self.solo_compatibles.blockSignals(True)
            self.solo_compatibles.setChecked(False)
            self.solo_compatibles.blockSignals(False)
            self._filtrar()
        self.arbol.blockSignals(True)
        if item.parent() is not None:
            item.parent().setExpanded(True)
        self.arbol.setCurrentItem(item)
        self.arbol.scrollToItem(item)
        self.arbol.blockSignals(False)

    def elegir_operacion(self, id_):
        if id_ not in CATALOGO:
            raise ValueError(f'Operación desconocida: {id_}')
        if self.op_actual == id_:
            self._seleccionar_item_arbol(id_)
            self._formulario()
            return
        self.op_actual = id_
        self._seleccionar_item_arbol(id_)
        self._cambio_de_operacion()

    def _operacion_elegida(self, item, anterior=None):
        if item is None:
            return
        id_ = item.data(0, Qt.ItemDataRole.UserRole)
        if id_ and id_ != self.op_actual:
            self.op_actual = id_
            self._cambio_de_operacion()

    def _cambio_de_operacion(self):
        self._detener_vista_previa()
        self.hoja.hide()
        if self.visor_entrada.herramienta() != 'mover' and self.op_actual not in (
                'extraer_roi', 'calibrar_escala', 'perfil_intensidad'):
            self.visor_entrada.establecer_herramienta('mover')
        self._formulario()
        self._sincronizar_leccion()
        self.acc['inspector'].setChecked(True)
        if self.op_actual != 'extraer_roi':
            self.visor_entrada.ocultar_dibujos()
        self._programar_previa()

    # ------------------------------------------------------------------
    # Formulario del inspector
    # ------------------------------------------------------------------

    def _estado_formulario(self) -> dict:
        parametros = {}
        for n, w in self.campos.items():
            if isinstance(w, QCheckBox):
                parametros[n] = ('bool', w.isChecked(), True)
            elif isinstance(w, QComboBox):
                parametros[n] = ('opcion', w.currentData(), True)
            elif isinstance(w, SegmentosParametro):
                parametros[n] = ('segmento', w.valor(), True)
            else:
                parametros[n] = ('texto', w.text(), getattr(w, 'editado_por_usuario', False))
        entradas = {n: (w.currentData(), getattr(w, 'elegido_por_usuario', False)) for n, w in self.entradas.items()}
        return {'parametros': parametros, 'entradas': entradas}

    def _restaurar_formulario(self, estado: dict) -> None:
        for n, (id_, usuario) in estado.get('entradas', {}).items():
            combo = self.entradas.get(n)
            if combo is not None and usuario:
                i = combo.findData(id_)
                if i >= 0:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(i)
                    combo.blockSignals(False)
                    combo.elegido_por_usuario = True
        for n, (clase, valor, editado) in estado.get('parametros', {}).items():
            w = self.campos.get(n)
            if w is None:
                continue
            if clase == 'bool' and isinstance(w, QCheckBox):
                w.setChecked(bool(valor))
            elif clase == 'opcion' and isinstance(w, QComboBox):
                w.setCurrentText(valor)
            elif clase == 'segmento' and isinstance(w, SegmentosParametro):
                w.establecer_valor(valor)
            elif clase == 'texto' and isinstance(w, CampoNumero) and editado:
                w.setText(valor)
                w.editado_por_usuario = True

    def restablecer_parametros(self):
        self._formulario(conservar=False)
        self.toast.mostrar('Parámetros restablecidos a sus valores iniciales.', 'info', 2400)

    def _formulario(self, conservar: bool = True):
        op = CATALOGO[self.op_actual]
        estado = self._estado_formulario() if conservar and self._form_op == op.id else None
        self._form_op = op.id
        meta = OPERACIONES.get(op.id, {})
        color = GRUPOS.get(op.grupo, {}).get('color', SISTEMA['azul'])
        self.icono_op.establecer(meta.get('icono', 'dato'), insignia=color)
        self.titulo_op.setText(op.titulo)
        self.subtitulo_op.setText(f'micrograno.nucleo.{op.id}')
        self.descripcion_op.setText(meta.get('resumen', ''))
        cuerpo = QWidget()
        cuerpo.setObjectName('CuerpoInspector')
        lay = QVBoxLayout(cuerpo)
        lay.setContentsMargins(16, 6, 16, 16)
        lay.setSpacing(16)
        self.campos, self.entradas, self.filas_parametro = {}, {}, {}
        self._aviso_escala = None
        if op.entradas:
            tarjeta = Tarjeta()
            for i, e in enumerate(op.entradas):
                combo = Selector()
                combo.setIconSize(QSize(18, 18))
                combo.setMinimumContentsLength(12)
                self._poblar_entrada(combo, e)
                combo.currentIndexChanged.connect(lambda *_: self._entrada_cambiada())
                acepta = ', '.join(nombre_tipo(t) for t in e.tipos)
                fila = FilaParametro(ENTRADAS.get(e.nombre, etiqueta_generica(e.nombre)), combo,
                                     ayuda=f'Acepta: {acepta}.', nombre_tecnico=e.nombre, apilado=True)
                tarjeta.agregar(fila, separador_antes=i > 0)
                self.entradas[e.nombre] = combo
            lay.addWidget(seccion('Entradas', tarjeta))
        self._activo_entradas = self.datos.currentData()
        especiales: set[str] = set()
        if op.id == 'extraer_roi':
            especiales = {'r0', 'r1', 'c0', 'c1'}
            lay.addWidget(self._tarjeta_region(op))
        elif op.id == 'perfil_intensidad':
            especiales = {'r0', 'r1', 'c0', 'c1'}
            lay.addWidget(self._tarjeta_segmento(op))
        elif op.id == 'calibrar_escala':
            especiales = set(op.parametros)
            for w in self._tarjetas_calibracion(op):
                lay.addWidget(w)
        restantes = [n for n in op.parametros if n not in especiales]
        if restantes:
            tarjeta = Tarjeta()
            for i, n in enumerate(restantes):
                campo, fila = self._crear_campo(op, n, op.parametros[n])
                tarjeta.agregar(fila, separador_antes=i > 0)
                if n == 's_um_px' and op.entradas:
                    self._aviso_escala = Aviso('El dato de entrada no tiene escala asociada. Las medidas '
                                               'físicas requieren calibrarlo antes.', 'aviso')
                    self._aviso_escala.agregar_accion('Calibrar escala…', self._calibrar_entrada_principal)
                    self._aviso_escala.hide()
                    tarjeta.agregar(self._aviso_escala)
            restablecer = QPushButton('Restablecer')
            restablecer.setProperty('tipo', 'plano')
            restablecer.setCursor(Qt.CursorShape.PointingHandCursor)
            restablecer.clicked.connect(self.restablecer_parametros)
            lay.addWidget(seccion('Parámetros', tarjeta, restablecer))
        if op.parametros:
            lay.addWidget(Aviso('Valores iniciales demostrativos. Revise la ayuda y las unidades antes de ejecutar.',
                                'info'))
        if op.id in ('convertir_grises', 'extraer_roi', 'separar_canales', 'explorar_imagen'):
            lay.addWidget(etiqueta('Esta herramienta puede usarse antes de confirmar la región de análisis.',
                                   'pie', envolver=True))
        lay.addStretch(1)
        self.scroll.setWidget(cuerpo)
        if estado:
            self._restaurar_formulario(estado)
        self._entrada_cambiada(programar=False)
        self._actualizar_pie_inspector()
        self._render_ayuda()
        self._render_codigo()
        self._sincronizar_roi_visor()
        self._sincronizar_leccion()
        self._actualizar_requisitos()

    def _poblar_entrada(self, combo: Selector, e, previo=None, conservar: bool = False) -> None:
        """Propone la versión activa o una compatible de su misma imagen y región.

        Las versiones de otras imágenes requieren una elección explícita.
        """
        usuario = getattr(combo, 'elegido_por_usuario', False)
        combo.blockSignals(True)
        combo.clear()
        if e.opcional:
            combo.agregar(SIN_ENTRADA.get(e.nombre, 'No usar'), None)
        else:
            combo.agregar('Seleccione un dato…', None)
        compatibles = [(id_, a) for id_, a in self.sesion.artefactos.items() if a.tipo in e.tipos]
        for id_, a in compatibles:
            combo.agregar(a.nombre, id_, self._icono_dato(id_), f'{id_} · {descripcion_dato(a)}')
        ids = [id_ for id_, _ in compatibles]
        if conservar and (previo is None or previo in ids):
            elegido = previo
        elif not e.opcional and e.nombre != 'referencia':
            activo = self.datos.currentData() if hasattr(self, 'datos') else None
            a = self.sesion.artefactos.get(activo)
            relacionados = [id_ for id_, b in compatibles if a is not None
                and b.metadatos.get('raiz', id_) == a.metadatos.get('raiz', activo)
                and b.metadatos.get('origen_rc', [0, 0]) == a.metadatos.get('origen_rc', [0, 0])
                and b.datos.shape[:2] == a.datos.shape[:2]]
            elegido = activo if activo in ids else (relacionados[-1] if relacionados else None)
        else:
            elegido = None
        combo.setCurrentIndex(max(0, combo.findData(elegido)) if elegido is not None else 0)
        combo.elegido_por_usuario = usuario and elegido == previo and previo is not None
        combo.blockSignals(False)

    def _refrescar_entradas(self):
        """Actualiza las listas de entradas sin cambiar la elección vigente, salvo que el
        dato activo haya cambiado y la entrada no la hubiera elegido el usuario."""
        op = CATALOGO[self.op_actual]
        activo = self.datos.currentData()
        cambio_activo = activo != getattr(self, '_activo_entradas', None)
        self._activo_entradas = activo
        for numero, e in enumerate(op.entradas):
            combo = self.entradas.get(e.nombre)
            if combo is not None:
                conservar = not cambio_activo or (numero > 0 and combo.elegido_por_usuario)
                if cambio_activo and numero == 0:
                    combo.elegido_por_usuario = False
                self._poblar_entrada(combo, e, combo.currentData(), conservar)
        self._entrada_cambiada()

    def _id_entrada_principal(self):
        op = CATALOGO[self.op_actual]
        if op.entradas and op.entradas[0].nombre in self.entradas:
            return self.entradas[op.entradas[0].nombre].currentData()
        return self.datos.currentData()

    def _entrada_cambiada(self, programar: bool = True):
        op = CATALOGO[self.op_actual]
        principal = self.sesion.artefactos.get(self._id_entrada_principal())
        if 's_um_px' in self.campos and op.entradas:
            escala = principal.metadatos.get('escala') if principal is not None else None
            campo = self.campos['s_um_px']
            campo.setText(repr(float(escala['um_por_px'])) if escala else '')
            if self._aviso_escala is not None:
                self._aviso_escala.setVisible(principal is not None and not escala)
        if op.id in ('extraer_roi', 'perfil_intensidad'):
            dato = principal or self.sesion.artefactos.get(self.datos.currentData())
            if dato is not None and dato.datos.ndim >= 2:
                h, w = dato.datos.shape[:2]
                recorte = op.id == 'extraer_roi'
                for n, valor in (('r0', 0), ('c0', 0), ('r1', h if recorte else h - 1), ('c1', w if recorte else w - 1)):
                    campo = self.campos.get(n)
                    if campo is not None and not campo.editado_por_usuario:
                        campo.blockSignals(True)
                        campo.setText(str(valor))
                        campo.blockSignals(False)
                        campo._validar()
            self._sincronizar_roi_visor()
        if programar:
            self._programar_previa()
        self._actualizar_requisitos()

    def _crear_campo(self, op, nombre, p):
        meta = meta_parametro(op.id, nombre)
        default = p.default
        anotacion = str(p.annotation)
        ayuda = AYUDA_PARAMETROS.get(nombre, '')
        vacio = inspect.Parameter.empty
        if nombre in op.opciones:
            opciones = [(v, etiqueta_opcion(nombre, v)) for v in op.opciones[nombre]]
            if len(opciones) <= 3 and sum(len(t) for _, t in opciones) <= 30:
                campo = SegmentosParametro(opciones)
                if default is not vacio:
                    campo.establecer_valor(default)
                campo.cambiado.connect(lambda *_: self._programar_previa())
                fila = FilaParametro(meta['etiqueta'], campo, ayuda=ayuda, nombre_tecnico=nombre, apilado=True)
            else:
                campo = Selector()
                for valor, texto in opciones:
                    campo.agregar(texto, valor)
                if default is not vacio:
                    campo.setCurrentText(str(default))
                campo.currentIndexChanged.connect(lambda *_: self._programar_previa())
                fila = FilaParametro(meta['etiqueta'], campo, ayuda=ayuda, nombre_tecnico=nombre)
        elif default is True or default is False:
            campo = Interruptor()
            campo.setChecked(default)
            campo.toggled.connect(lambda *_: self._programar_previa())
            fila = FilaParametro(meta['etiqueta'], campo, ayuda=ayuda, nombre_tecnico=nombre)
        elif 'segmentos' in meta:
            campo = SegmentosParametro(list(meta['segmentos']))
            if default is not vacio:
                campo.establecer_valor(default)
            campo.cambiado.connect(lambda *_: self._programar_previa())
            fila = FilaParametro(meta['etiqueta'], campo, ayuda=ayuda, nombre_tecnico=nombre)
        else:
            if 'int' in anotacion and 'float' not in anotacion:
                tipo = 'int'
            elif 'float' in anotacion:
                tipo = 'float'
            else:
                tipo = 'texto'
            campo = CampoNumero(meta, tipo, default is None)
            if default is not vacio and default is not None:
                campo.setText(str(default))
            elif default is vacio:
                campo.setPlaceholderText('Obligatorio')
            if nombre == 's_um_px' and op.entradas:
                campo.setReadOnly(True)
                ayuda = 'Se toma de la calibración asociada al dato de entrada; la biblioteca comprueba que coincida.'
            campo.textChanged.connect(lambda *_: self._programar_previa())
            deslizador = meta.get('deslizador') if tipo != 'texto' and not campo.isReadOnly() else None
            fila = FilaParametro(meta['etiqueta'], campo, unidad=meta.get('unidad', ''), ayuda=ayuda,
                                 nombre_tecnico=nombre, deslizador=deslizador, apilado=tipo == 'texto')
        self.campos[nombre] = campo
        self.filas_parametro[nombre] = fila
        return campo, fila

    def _campo_coordenada(self, op, nombre, tipo):
        meta = meta_parametro(op.id, nombre)
        campo = CampoNumero(meta, tipo)
        campo.setToolTip(f'{AYUDA_PARAMETROS.get(nombre, "")}\n\nParámetro: {nombre}')
        campo.setMinimumWidth(64)
        campo.textChanged.connect(lambda *_: (self._sincronizar_roi_visor(), self._programar_previa()))
        self.campos[nombre] = campo
        return campo

    def _tarjeta_region(self, op) -> QWidget:
        tarjeta = Tarjeta()
        boton = QPushButton('Dibujar en la imagen')
        boton.setIcon(iconos.icono('recortar', 'texto'))
        boton.setCursor(Qt.CursorShape.PointingHandCursor)
        boton.setToolTip('Arrastre un rectángulo sobre el dato activo (R)')
        boton.clicked.connect(self.dibujar_roi)
        tarjeta.agregar(boton)
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(8)
        rejilla.setVerticalSpacing(8)
        for fila, (texto, a, b) in enumerate((('Filas', 'r0', 'r1'), ('Columnas', 'c0', 'c1'))):
            rejilla.addWidget(etiqueta(texto), fila, 0)
            rejilla.addWidget(self._campo_coordenada(op, a, 'int'), fila, 1)
            rejilla.addWidget(etiqueta('a', 'secundario'), fila, 2)
            rejilla.addWidget(self._campo_coordenada(op, b, 'int'), fila, 3)
            rejilla.addWidget(etiqueta('px', 'secundario'), fila, 4)
        rejilla.setColumnStretch(1, 1)
        rejilla.setColumnStretch(3, 1)
        tarjeta.capa.addLayout(rejilla)
        tarjeta.agregar(etiqueta('Coordenadas de la imagen de entrada. La fila y la columna finales no se '
                                 'incluyen en el recorte; el recorte conserva la escala.', 'pie', envolver=True))
        return seccion('Región', tarjeta)

    def _tarjeta_segmento(self, op) -> QWidget:
        tarjeta = Tarjeta()
        boton = QPushButton('Dibujar la línea en la imagen')
        boton.setIcon(iconos.icono('perfil', 'texto'))
        boton.setCursor(Qt.CursorShape.PointingHandCursor)
        boton.clicked.connect(self.dibujar_perfil)
        tarjeta.agregar(boton)
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(8)
        rejilla.setVerticalSpacing(8)
        rejilla.addWidget(etiqueta('Fila', 'secundario'), 0, 1)
        rejilla.addWidget(etiqueta('Columna', 'secundario'), 0, 2)
        for fila, (texto, a, b) in enumerate((('Inicio', 'r0', 'c0'), ('Fin', 'r1', 'c1')), 1):
            rejilla.addWidget(etiqueta(texto), fila, 0)
            rejilla.addWidget(self._campo_coordenada(op, a, 'float'), fila, 1)
            rejilla.addWidget(self._campo_coordenada(op, b, 'float'), fila, 2)
        rejilla.setColumnStretch(1, 1)
        rejilla.setColumnStretch(2, 1)
        tarjeta.capa.addLayout(rejilla)
        tarjeta.agregar(etiqueta('Los extremos son centros de píxel; la intensidad se interpola de forma bilineal.',
                                 'pie', envolver=True))
        return seccion('Segmento', tarjeta)

    def _tarjetas_calibracion(self, op) -> list[QWidget]:
        tarjeta = Tarjeta()
        boton = QPushButton('Medir la referencia en la imagen')
        boton.setIcon(iconos.icono('regla', 'texto'))
        boton.setCursor(Qt.CursorShape.PointingHandCursor)
        boton.setToolTip('Marque los extremos de la barra de escala o del patrón sobre el dato activo')
        boton.clicked.connect(self.medir_referencia)
        tarjeta.agregar(boton)
        for i, n in enumerate(('referencia_px', 'referencia_um', 'referencia')):
            _, fila = self._crear_campo(op, n, op.parametros[n])
            tarjeta.agregar(fila, separador_antes=True)
        tarjetas = [seccion('Referencia de longitud', tarjeta)]
        incertidumbre = Tarjeta()
        for i, n in enumerate(('incertidumbre_um', 'incertidumbre_px')):
            _, fila = self._crear_campo(op, n, op.parametros[n])
            incertidumbre.agregar(fila, separador_antes=i > 0)
        tarjetas.append(seccion('Incertidumbre estándar (opcional)', incertidumbre))
        if self.ultima_escala is not None:
            resultado = Tarjeta()
            cifra = etiqueta(f'1 px = {self.ultima_escala.um_por_px:.6g} µm', 'cifra')
            resultado.agregar(cifra)
            u = self.ultima_escala.incertidumbre_um_por_px
            detalle = f'Incertidumbre estándar: {u:.3g} µm/px' if u is not None else 'Incertidumbre no declarada (no equivale a cero).'
            if self.ultima_escala.referencia:
                detalle += f'\nReferencia: {self.ultima_escala.referencia}'
            resultado.agregar(etiqueta(detalle, 'secundario', envolver=True))
            resultado.agregar(etiqueta('Asóciela al dato que corresponda con «Aplicar escala al dato activo».',
                                       'pie', envolver=True))
            tarjetas.append(seccion('Escala calculada', resultado))
        return tarjetas

    def _actualizar_pie_inspector(self):
        op = self.op_actual
        self.fila_previa.setVisible(op in VISTA_PREVIA)
        self.aplicar.setVisible(op == 'calibrar_escala')
        self.aplicar.setEnabled(self.ultima_escala is not None and not self._ocupada)
        texto = TEXTO_EJECUTAR.get(op, 'Ejecutar')
        self.ejecutar_btn._texto = texto
        if not self._ocupada:
            self.ejecutar_btn.setText(texto)

    def _render_ayuda(self):
        op = CATALOGO[self.op_actual]
        c = tema().c
        texto2 = _hex(c['texto2'])
        meta = OPERACIONES.get(op.id, {})
        entradas = ''.join(
            f'<li><b>{html.escape(ENTRADAS.get(e.nombre, e.nombre))}</b>'
            f'{" (opcional)" if e.opcional else ""}: acepta {html.escape(", ".join(nombre_tipo(t) for t in e.tipos))}. '
            f'<span style="color:{texto2}">({html.escape(e.nombre)})</span></li>' for e in op.entradas)
        parametros = ''.join(
            f'<p><b>{html.escape(meta_parametro(op.id, n)["etiqueta"])}</b> '
            f'<code style="color:{texto2}">{html.escape(n)}</code><br>{html.escape(AYUDA_PARAMETROS[n])}</p>'
            for n in op.parametros)
        refs = ', '.join('[' + r + ']' for r in op.referencias) or 'Operación de soporte del repositorio.'
        self.ayuda.document().setDefaultStyleSheet(
            f'h3 {{ font-size: 10.5pt; margin-top: 14px; margin-bottom: 4px; }} '
            f'pre {{ font-family: "{familia_codigo()}"; font-size: 8.5pt; color: {texto2}; }} '
            f'p, li {{ margin-bottom: 6px; }}')
        self.ayuda.setHtml(
            f'<h2 style="margin-bottom:4px">{html.escape(op.titulo)}</h2>'
            f'<p>{html.escape(meta.get("resumen", ""))}</p>'
            f'<h3>Qué recibe</h3><p>{html.escape(explicacion_entradas(op.id))}</p>'
            f'<h3>Qué obtiene</h3><p>{html.escape(explicacion_salida(op.id))}</p>'
            f'<p style="color:{texto2}">Función: <code>{op.id}</code>. Correspondencia de trabajo con el manuscrito: '
            f'{html.escape(op.libro)}.</p>'
            + (f'<h3>Entradas</h3><ul>{entradas}</ul>' if entradas else '<h3>Entradas</h3><p>No requiere datos de la sesión.</p>')
            + (f'<h3>Parámetros</h3>{parametros}' if parametros else '')
            + f'<h3>Descripción técnica</h3><pre>{html.escape(op.ayuda)}</pre>'
            f'<h3>Ejemplo en Python</h3><pre>{html.escape(op.ejemplo())}</pre>'
            f'<h3>Referencias del libro</h3><p>{html.escape(refs)}</p>'
            '<p>[POR VERIFICAR: referencias bibliográficas y versiones de normas antes de redactar el libro].</p>'
            f'<p style="color:{texto2}">Las salidas se consultan en el lienzo, la Tabla y el Resumen. Una región '
            'calculada no recibe automáticamente identidad metalográfica.</p>')

    def _render_codigo(self):
        op = CATALOGO[self.op_actual]
        if self.ver_implementacion.isChecked():
            texto = f'# Archivo: {op.funcion.__module__.replace(".", "/")}.py\n\n' + inspect.getsource(op.funcion)
        else:
            texto = '# Ejemplo autónomo con datos sintéticos.\n# El script de su análisis está en Resultados > Script.\n\n' + op.ejemplo()
        self.codigo.setPlainText(texto)

    def _leer_parametros(self):
        op = CATALOGO[self.op_actual]
        salida = {}
        for n, p in op.parametros.items():
            w = self.campos[n]
            etiqueta_campo = meta_parametro(op.id, n)['etiqueta']
            if isinstance(w, QCheckBox):
                valor = w.isChecked()
            elif isinstance(w, QComboBox):
                valor = w.currentData() if w.currentData() is not None else w.currentText()
            elif isinstance(w, SegmentosParametro):
                valor = w.valor()
            else:
                texto = w.text().strip()
                anotacion = str(p.annotation)
                if not texto:
                    if p.default is None:
                        valor = None
                    elif p.default is inspect.Parameter.empty:
                        raise ValueError(f'Complete el parámetro «{etiqueta_campo}» ({n}).')
                    else:
                        valor = '' if 'str' in anotacion else p.default
                elif 'int' in anotacion and 'float' not in anotacion:
                    try:
                        valor = int(texto)
                    except ValueError:
                        raise ValueError(f'«{etiqueta_campo}» ({n}) debe ser un número entero.') from None
                elif 'float' in anotacion:
                    try:
                        valor = float(texto.replace(',', '.'))
                    except ValueError:
                        raise ValueError(f'«{etiqueta_campo}» ({n}) debe ser un número.') from None
                else:
                    valor = texto
            salida[n] = valor
        return salida

    # ------------------------------------------------------------------
    # Datos de la sesión y dato activo
    # ------------------------------------------------------------------

    def _miniatura_dato(self, id_, lado: int, sesion=None):
        """Miniatura en caché para la sesión del usuario; las de vista previa no se guardan."""
        sesion = sesion or self.sesion
        a = sesion.artefactos.get(id_)
        if a is None:
            return None
        clave = (id_, lado, tema().generacion if a.datos.ndim == 1 else 0)
        if sesion is self.sesion and clave in self._miniaturas:
            return self._miniaturas[clave]
        try:
            pm = miniatura(preparar_vista(a, sesion), lado, a.datos, a.tipo)
        except Exception:
            return None
        if sesion is self.sesion:
            self._miniaturas[clave] = pm
        return pm

    def _icono_dato(self, id_):
        pm = self._miniatura_dato(id_, 18)
        return QIcon(pm) if pm is not None else iconos.icono(TIPOS.get(self.sesion.artefactos[id_].tipo, {}).get('icono', 'dato'))

    def _actualizar_datos(self, seleccionar=None):
        anterior = seleccionar or self.datos.currentData()
        self.datos.blockSignals(True)
        self.datos.clear()
        for id_, a in self.sesion.artefactos.items():
            self.datos.agregar(nombre_version(self.sesion, id_), id_, self._icono_dato(id_),
                               f'{a.nombre}\n{origen_version(self.sesion, id_)}\n{descripcion_dato(a)}')
        indice = self.datos.findData(anterior)
        if indice >= 0:
            self.datos.setCurrentIndex(indice)
        self.datos.setEnabled(self.datos.count() > 0 and not self._ocupada)
        self.datos.blockSignals(False)
        self._llenar_lista_datos()
        self._actualizar_disponibilidad()
        self._actualizar_pagina()
        self._actualizar_titulo()
        self._activo_cambiado()

    def _llenar_lista_datos(self):
        self.lista_datos.blockSignals(True)
        self.lista_datos.clear()
        for id_, a in self.sesion.artefactos.items():
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, id_)
            item.setSizeHint(QSize(0, 52))
            imagen = a.datos.ndim >= 2
            item.setToolTip(f'{a.nombre}\n{origen_version(self.sesion, id_)}\n{descripcion_dato(a)}')
            fila = FilaDato(self._miniatura_dato(id_, 40), nombre_version(self.sesion, id_),
                            origen_version(self.sesion, id_),
                            bool(a.metadatos.get('escala')) if imagen else None,
                            bool(a.metadatos.get('roi_confirmada')) if imagen else None)
            self.lista_datos.addItem(item)
            self.lista_datos.setItemWidget(item, fila)
        hay = bool(self.sesion.artefactos)
        self.lista_datos.setVisible(hay)
        self.vacio_datos.setVisible(not hay)
        self.selector_lateral.boton(1).setText(f'Versiones ({len(self.sesion.artefactos)})' if hay else 'Versiones')
        self.lista_datos.blockSignals(False)

    def _sincronizar_lista_datos(self, id_):
        self.lista_datos.blockSignals(True)
        for i in range(self.lista_datos.count()):
            if self.lista_datos.item(i).data(Qt.ItemDataRole.UserRole) == id_:
                self.lista_datos.setCurrentRow(i)
                break
        self.lista_datos.blockSignals(False)

    def _dato_elegido_lista(self, fila):
        item = self.lista_datos.item(fila)
        if item is not None:
            self._activar(item.data(Qt.ItemDataRole.UserRole))
            self._cambiar_modo_vista('activo')

    def _activar(self, id_):
        i = self.datos.findData(id_)
        if i >= 0 and i != self.datos.currentIndex():
            self.datos.setCurrentIndex(i)

    def _menu_lista_datos(self, posicion):
        item = self.lista_datos.itemAt(posicion)
        if item is None:
            return
        self._activar(item.data(Qt.ItemDataRole.UserRole))
        menu = QMenu(self)
        for clave in ('confirmar_roi', 'calibrar', 'asociar', 'metadatos', None, 'exportar_figura'):
            if clave is None:
                menu.addSeparator()
            else:
                menu.addAction(self.acc[clave])
        menu.exec(self.lista_datos.viewport().mapToGlobal(posicion))

    def _actualizar_pagina(self):
        hay = bool(self.sesion.artefactos) or bool(self.sesion.pasos) or self._explorar
        self.paginas.setCurrentIndex(1 if hay else 0)
        con_datos = bool(self.sesion.artefactos)
        self._accion_datos.setVisible(con_datos)
        self._accion_etiqueta_datos.setVisible(con_datos)
        self._accion_mas.setVisible(con_datos)

    def _explorar_sin_datos(self):
        self._explorar = True
        self._actualizar_pagina()
        self.selector_lateral.establecer(2, emitir=True)

    def _activo_cambiado(self, *_):
        id_ = self.datos.currentData()
        self._sincronizar_lista_datos(id_)
        self._actualizar_chips()
        self._cambiar_modo_vista('activo')
        self._mostrar_activo()
        if self.entradas:
            self._refrescar_entradas()
        self._filtrar()
        self._actualizar_acciones()

    def _actualizar_chips(self):
        a = self.sesion.artefactos.get(self.datos.currentData())
        imagen = a is not None and a.datos.ndim >= 2
        for accion in self._acciones_chip:
            accion.setVisible(False)
        if not imagen:
            return
        escala = a.metadatos.get('escala')
        if escala:
            self.chip_escala.establecer(f'{escala["um_por_px"]:.4g} µm/px', 'regla', 'ok')
            texto = f'Escala asociada: {escala["um_por_px"]:.8g} µm/px'
            if escala.get('referencia'):
                texto += f'\nReferencia: {escala["referencia"]}'
            self.chip_escala.setToolTip(texto + '\n\nPulse para medir una nueva referencia.')
        elif a.metadatos.get('muestreo_modificado'):
            self.chip_escala.establecer('Escala invalidada', 'regla', 'aviso')
            self.chip_escala.setToolTip('El cambio de muestreo invalidó la escala de este dato.')
        else:
            self.chip_escala.establecer('Sin escala', 'regla', 'aviso')
            self.chip_escala.setToolTip('Este dato no tiene escala asociada. Pulse para calibrarlo.')
        if a.metadatos.get('roi_confirmada'):
            self.chip_roi.establecer('ROI confirmada', 'recortar', 'ok')
            self.chip_roi.setToolTip(f'Criterio registrado:\n{a.metadatos.get("nota_roi", "")}')
        else:
            self.chip_roi.establecer('ROI sin confirmar', 'recortar', 'aviso')
            self.chip_roi.setToolTip('Confirme que la región no contiene barra de escala ni anotaciones. '
                                     'Pulse para revisarla.')

    def _chip_escala(self):
        self.medir_referencia()

    def _chip_roi(self):
        a = self.sesion.artefactos.get(self.datos.currentData())
        if a is None:
            return
        if a.metadatos.get('roi_confirmada'):
            self.toast.mostrar(f'Región confirmada. Criterio: {a.metadatos.get("nota_roi", "")}', 'ok', 5000)
        else:
            self.confirmar_roi()

    def _actualizar_acciones(self):
        a = self.sesion.artefactos.get(self.datos.currentData())
        imagen = a is not None and a.datos.ndim >= 2
        habilitar = {
            'recortar': imagen, 'regla': imagen, 'perfil': imagen, 'calibrar': imagen,
            'confirmar_roi': imagen,
            'asociar': a is not None and a.tipo in ('mascara', 'limites', 'etiquetas', 'clases', 'marcadores'),
            'metadatos': a is not None, 'exportar_figura': imagen,
            'exportar_resultado': self.paso_actual is not None,
            'guardar': bool(self.sesion.artefactos),
            'exportar_versiones': bool(self.sesion.artefactos),
            'usar': self.tira.currentData() is not None and not self._tira_previa,
            'aplicar_escala': self.ultima_escala is not None,
        }
        for clave, valor in habilitar.items():
            self.acc[clave].setEnabled(bool(valor) and not self._ocupada)
        for clave in ('nueva', 'abrir', 'demo', 'ejemplo', 'buscar', 'restablecer',
                      *(f'importar_{tipo}' for _, tipo in TIPOS_IMPORTACION)):
            self.acc[clave].setEnabled(not self._ocupada)
        for b in (self.btn_roi, self.btn_regla, self.btn_perfil):
            b.setEnabled(imagen and not self._ocupada)
        self.usar.setEnabled(self.acc['usar'].isEnabled())
        self.btn_guardar.setEnabled(self.acc['guardar'].isEnabled())
        self.btn_exportar.setEnabled(self.acc['exportar_versiones'].isEnabled())
        salida = self._sesion_tira().artefactos.get(self.tira.currentData())
        self.exportar_salida_btn.setEnabled(salida is not None and salida.datos.ndim >= 2
                                            and not self._tira_previa and not self._ocupada)
        for i in (1, 2, 3):
            self.selector_vista.boton(i).setEnabled(salida is not None and salida.datos.ndim >= 2)
        self._actualizar_requisitos()

    def _mostrar_activo(self):
        a = self.sesion.artefactos.get(self.datos.currentData())
        if a is None:
            self.visor_entrada.limpiar('Sin dato activo', 'Importe una imagen o cargue el conjunto sintético para empezar.')
            return
        if a.datos.ndim == 1:
            self.visor_entrada.limpiar(a.nombre, f'Serie de {len(a.datos)} valores por unidad de análisis. '
                                       'Su distribución se muestra en la pestaña Gráfica.', 'tabla')
            if self.paso_actual is None:
                self.panel_grafica.establecer_serie(a.datos, a.nombre)
            return
        try:
            vista = preparar_vista(a, self.sesion, False, self.rotulos.isChecked())
            self.visor_entrada.mostrar(vista, f'Dato activo · {a.nombre}', a.datos, a.tipo,
                                       self.opciones_vista, conservar_vista=True)
            escala = a.metadatos.get('escala')
            self.visor_entrada.escala_um = escala['um_por_px'] if escala else None
        except Exception as exc:
            self.visor_entrada.limpiar('No se pudo mostrar el dato', str(exc), 'aviso')
            return
        if self.modo_vista == 'cortina':
            self._aplicar_cortina()
        self._sincronizar_roi_visor()

    # ------------------------------------------------------------------
    # Ejecución
    # ------------------------------------------------------------------

    def ejecutar_actual(self):
        if self.trabajo and self.trabajo.isRunning():
            return
        try:
            parametros = self._leer_parametros()
            entradas = {n: w.currentData() for n, w in self.entradas.items() if w.currentData() is not None}
            problema = razon_bloqueo(self.sesion, self.op_actual, entradas)
            if problema:
                self._actualizar_requisitos()
                self.toast.mostrar(problema, 'aviso', 5000)
                return
            if self.op_actual in ('evaluar_referencia', 'evaluar_mascara') and \
                    entradas.get('referencia') == entradas.get('candidata') and entradas.get('referencia'):
                respuesta = QMessageBox.question(self, 'Comparación del mismo dato',
                    'Está comparando el dato consigo mismo. Sirve como prueba de identidad, no como validación. ¿Continuar?')
                if respuesta != QMessageBox.StandardButton.Yes:
                    return
            self.hoja.hide()
            self._detener_vista_previa(restaurar=False)
            self._ocupado(True)
            self.trabajo = Trabajo(self.sesion, self.op_actual, entradas, parametros, self)
            self.trabajo.correcto.connect(self._resultado_recibido)
            self.trabajo.fallo.connect(self._error)
            self.trabajo.finished.connect(self._trabajo_terminado)
            self.trabajo.start()
        except Exception as exc:
            self._ocupado(False)
            self._error(str(exc), traceback.format_exc())

    @Slot(object)
    def _resultado_recibido(self, resultado):
        r, salidas = resultado
        self.modificada = True
        indice = len(self.sesion.pasos) - 1
        paso = self.sesion.pasos[indice]
        duracion = getattr(self.trabajo, 'duracion', 0.0) if self.trabajo is not None else 0.0
        if paso['operacion'] == 'calibrar_escala':
            self.ultima_escala = EscalaEspacial(**r.resumen)
            self.ultima_calibracion = {'parametros': paso['parametros'].copy()}
            if self.linea_referencia and np.isclose(self.linea_referencia['longitud_px'], paso['parametros']['referencia_px']):
                self.ultima_calibracion['medicion_grafica'] = self.linea_referencia.copy()
            self.aplicar.setEnabled(True)
        self._tira_previa = False
        self._actualizar_datos()
        self._agregar_historial(indice)
        self._ver_paso(indice, cambiar_pestana=True)
        op = CATALOGO[paso['operacion']]
        n = len(salidas)
        detalle = f'{n} salida{"s" if n != 1 else ""}' if n else 'sin salidas de imagen'
        texto = f'{op.titulo}: listo en {duracion:.2f} s · {detalle}. Revise el resultado antes de usarlo.'
        accion = None
        if paso['operacion'] == 'extraer_roi':
            accion = ('Usar y confirmar ROI…', self._usar_y_confirmar)
        elif paso['operacion'] == 'calibrar_escala':
            texto = f'Escala calculada: {self.ultima_escala.um_por_px:.6g} µm/px. Aplíquela al dato que corresponda.'
            accion = ('Aplicar al dato activo…', self.aplicar_escala)
        elif n:
            accion = ('Usar esta salida', self.usar_salida)
        self.toast.mostrar(texto, 'ok', 5200, accion)
        if paso['operacion'] == 'calibrar_escala':
            self._formulario()

    @Slot()
    def _trabajo_terminado(self):
        if self.trabajo:
            self.trabajo.deleteLater()
            self.trabajo = None
        self._ocupado(False)

    def _ocupado(self, ocupado: bool):
        self._ocupada = bool(ocupado)
        self.menuBar().setEnabled(not ocupado)
        for w in (self.datos, self.arbol, self.buscar, self.scroll, self.lista_datos, self.historial,
                  self.caja_tira, self.pila_lateral, self.btn_resolver_roi, self.btn_resolver_escala,
                  self.fila_previa, *self._botones_barra):
            w.setEnabled(not ocupado)
        self.ejecutar_btn.ocupado(ocupado)
        self.aplicar.setEnabled(not ocupado and self.ultima_escala is not None)
        self._actualizar_acciones()

    # ------------------------------------------------------------------
    # Resultados
    # ------------------------------------------------------------------

    def _limpiar_resultados(self):
        self.paso_actual = None
        self.historial.blockSignals(True)
        self.historial.clear()
        self.historial.blockSignals(False)
        self.pila_historial.setCurrentIndex(0)
        self.codigo_sesion.setPlainText(self.sesion.codigo() if self.sesion.pasos else '')
        self.tira.blockSignals(True)
        self.tira.clear()
        self.tira.blockSignals(False)
        self.caja_tira.hide()
        self.resumen.clear()
        self.pila_resumen.setCurrentIndex(0)
        self._limpiar_sugerencias()
        self.modelo = ModeloTabla()
        self.proxy.setSourceModel(self.modelo)
        self.pila_tabla.setCurrentIndex(0)
        self.panel_grafica.limpiar()
        self.visor_salida.limpiar('Sin resultado', 'Ejecute una herramienta para ver aquí su salida.', 'destello')

    def _agregar_historial(self, indice: int):
        paso = self.sesion.pasos[indice]
        op = CATALOGO[paso['operacion']]
        meta = OPERACIONES.get(op.id, {})
        color = GRUPOS.get(op.grupo, {}).get('color', SISTEMA['azul'])
        entradas = ', '.join(paso['entradas'].values()) or 'sin entradas'
        try:
            hora = datetime.fromisoformat(paso['fecha_utc']).astimezone().strftime('%H:%M:%S')
        except Exception:
            hora = ''
        n = len(paso['salidas'])
        subtitulo = f'{entradas} → {n} salida{"s" if n != 1 else ""}' + (f' · {hora}' if hora else '')
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, indice)
        item.setSizeHint(QSize(0, 46))
        self.historial.blockSignals(True)
        self.historial.addItem(item)
        self.historial.setItemWidget(item, FilaPaso(indice + 1, meta.get('icono', 'dato'), color, op.titulo, subtitulo))
        self.historial.setCurrentRow(self.historial.count() - 1)
        self.historial.blockSignals(False)
        self.pila_historial.setCurrentIndex(1)

    def _historial_elegido(self, fila):
        if 0 <= fila < len(self.sesion.pasos):
            self._detener_vista_previa(restaurar=False)
            self._ver_paso(fila, cambiar_pestana=False)

    def _menu_historial(self, posicion):
        item = self.historial.itemAt(posicion)
        if item is None:
            return
        indice = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.addAction(iconos.icono('restablecer'), 'Reutilizar parámetros', lambda: self.reutilizar_paso(indice))
        menu.addAction(iconos.icono('exportar'), 'Exportar resultado…', lambda: (self._ver_paso(indice, False),
                                                                               self.exportar_resultado()))
        menu.exec(self.historial.viewport().mapToGlobal(posicion))

    def reutilizar_paso(self, indice: int | None = None):
        if indice is None:
            indice = self.historial.currentRow() if self.historial.currentRow() >= 0 else self.paso_actual
        if indice is None or not 0 <= indice < len(self.sesion.pasos):
            self.toast.mostrar('Elija un paso del historial.', 'info')
            return
        paso = self.sesion.pasos[indice]
        self.elegir_operacion(paso['operacion'])
        for rol, id_ in paso['entradas'].items():
            combo = self.entradas.get(rol)
            if combo is not None and combo.findData(id_) >= 0:
                combo.setCurrentIndex(combo.findData(id_))
                combo.elegido_por_usuario = True
        for n, valor in paso['parametros'].items():
            w = self.campos.get(n)
            if w is None or (isinstance(w, CampoNumero) and w.isReadOnly()):
                continue
            if isinstance(w, QCheckBox):
                w.setChecked(bool(valor))
            elif isinstance(w, QComboBox):
                w.setCurrentText(valor)
            elif isinstance(w, SegmentosParametro):
                w.establecer_valor(valor)
            else:
                w.setText('' if valor is None else str(valor))
                w.editado_por_usuario = True
        self.toast.mostrar(f'Parámetros del paso {indice + 1} cargados. Ajústelos y pulse Ejecutar para crear un paso nuevo.',
                           'info')

    def _ver_paso(self, indice, cambiar_pestana: bool = True):
        self.paso_actual = indice
        self._tira_previa = False
        paso = self.sesion.pasos[indice]
        r = self.sesion.resultados[indice]
        op = CATALOGO[paso['operacion']]
        self.codigo_sesion.setPlainText(self.sesion.codigo())
        self._llenar_tira(paso['salidas'], self.sesion)
        self.titulo_tira.setText(f'Paso {indice + 1} · {op.titulo}')
        n = len(paso['salidas'])
        self.sub_tira.setText(f'{n} versión{"es" if n != 1 else ""} guardada{"s" if n != 1 else ""}. '
                             'Seleccione una y continúe.')
        self._mostrar_salida()
        nuevo = ModeloTabla(r.tabla)
        self.proxy.setSourceModel(nuevo)
        self.modelo = nuevo
        self.proxy.sort(-1)
        self.tabla.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.tabla.resizeColumnsToContents()
        for i in range(self.modelo.columnCount()):
            if self.tabla.columnWidth(i) > 220:
                self.tabla.setColumnWidth(i, 220)
        self.pila_tabla.setCurrentIndex(1 if len(r.tabla) else 0)
        self.resumen.setHtml(self._html_resumen(indice))
        self.pila_resumen.setCurrentIndex(1)
        self.panel_grafica.establecer_resultado(paso['operacion'], r)
        self._actualizar_sugerencias()
        imagenes = [x for x in paso['salidas'].values()
                    if x in self.sesion.artefactos and self.sesion.artefactos[x].datos.ndim >= 2]
        if cambiar_pestana:
            pestana = PESTANA_PREFERIDA.get(paso['operacion'], 'resumen')
            self._cambiar_pestana(pestana)
            self.acc['panel'].setChecked(not imagenes or pestana in ('tabla', 'grafica'))
            if imagenes and self.modo_vista == 'activo':
                self._cambiar_modo_vista('lado')
        self.historial.blockSignals(True)
        self.historial.setCurrentRow(indice)
        self.historial.blockSignals(False)
        self._actualizar_acciones()

    def _llenar_tira(self, salidas: dict, sesion) -> None:
        self.tira.blockSignals(True)
        self.tira.clear()
        preferida = None
        for clave, id_ in salidas.items():
            a = sesion.artefactos.get(id_)
            if a is None:
                continue
            item = QListWidgetItem(nombre_salida(clave))
            pm = self._miniatura_dato(id_, 58, sesion)
            if pm is not None:
                item.setIcon(QIcon(pm))
            item.setData(Qt.ItemDataRole.UserRole, id_)
            item.setData(Qt.ItemDataRole.UserRole + 1, clave)
            item.setToolTip(f'{nombre_salida(clave)} · {descripcion_dato(a)}\n{id_ if sesion is self.sesion else "vista previa"}')
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            self.tira.addItem(item)
        claves = list(salidas)
        if self._clave_preferida in claves:
            preferida = claves.index(self._clave_preferida)
        else:
            for p in PREFERENCIA_SALIDA:
                if p in claves:
                    preferida = claves.index(p)
                    break
        if self.tira.count():
            self.tira.setCurrentRow(preferida or 0)
        self.tira.blockSignals(False)
        self.caja_tira.setVisible(self.tira.count() > 0)

    def _salida_elegida(self, fila):
        item = self.tira.item(fila)
        if item is not None:
            self._clave_preferida = item.data(Qt.ItemDataRole.UserRole + 1)
        self._mostrar_salida()
        self._actualizar_sugerencias()
        self._actualizar_acciones()

    def _sesion_tira(self):
        return self._previa['sesion'] if self._tira_previa and self._previa['sesion'] is not None else self.sesion

    def _mostrar_salida(self, *_):
        id_ = self.tira.currentData()
        sesion = self._sesion_tira()
        if id_ not in sesion.artefactos:
            self.visor_salida.limpiar('Sin salida de imagen', 'Este paso no produjo imágenes. Revise el Resumen, '
                                      'la Tabla o la Gráfica.', 'resumen')
            return
        a = sesion.artefactos[id_]
        clave = self.tira.currentItem().data(Qt.ItemDataRole.UserRole + 1) if self.tira.currentItem() else ''
        if a.datos.ndim == 1:
            self.visor_salida.limpiar(nombre_salida(clave), f'Serie de {len(a.datos)} valores. Su distribución se '
                                      'muestra en la pestaña Gráfica.', 'histograma')
            return
        try:
            vista = preparar_vista(a, sesion, self.superponer.isChecked(), self.rotulos.isChecked())
            prefijo = 'Vista previa' if self._tira_previa else 'Resultado'
            self.visor_salida.mostrar(vista, f'{prefijo} · {nombre_salida(clave)}', a.datos, a.tipo,
                                      self.opciones_vista, conservar_vista=True)
            escala = a.metadatos.get('escala')
            self.visor_salida.escala_um = escala['um_por_px'] if escala else None
            if self.modo_vista == 'lado':
                self._sincronizar_desde(self.visor_entrada)
        except Exception as exc:
            self._error(str(exc), traceback.format_exc())
            return
        if self.modo_vista == 'cortina':
            self._aplicar_cortina()

    def usar_salida(self):
        if self._tira_previa:
            self.toast.mostrar('Esta es una vista previa. Pulse Ejecutar para registrarla antes de usarla.', 'info')
            return
        id_ = self.salidas.currentData()
        if id_:
            i = self.datos.findData(id_)
            if i >= 0:
                self.datos.setCurrentIndex(i)
                a = self.sesion.artefactos[id_]
                self.toast.mostrar(f'«{a.nombre}» es ahora el dato activo. El dato anterior sigue en la sesión.',
                                   'ok', 3200)

    def _usar_y_confirmar(self):
        self.usar_salida()
        self.confirmar_roi()

    def _limpiar_sugerencias(self):
        while self._capa_sugerencias.count():
            item = self._capa_sugerencias.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.fila_sugerencias.hide()

    def _actualizar_sugerencias(self):
        self._limpiar_sugerencias()
        if self.paso_actual is None or self._tira_previa:
            return
        paso = self.sesion.pasos[self.paso_actual]
        siguientes = OPERACIONES.get(paso['operacion'], {}).get('siguientes', ())
        if not siguientes:
            return
        salida = self.sesion.artefactos.get(self.tira.currentData())
        self._capa_sugerencias.addWidget(etiqueta('Siguiente paso:', 'secundario'))
        for sig in siguientes[:2]:
            op = CATALOGO[sig]
            compatible = salida is not None and bool(op.entradas) and salida.tipo in op.entradas[0].tipos
            chip = Chip(op.titulo, OPERACIONES.get(sig, {}).get('icono', 'dato'), 'info' if compatible else 'neutro')
            chip.setToolTip(f'Usa «{salida.nombre}» como dato activo y abre la herramienta.' if compatible
                            else 'Abre la herramienta.')
            chip.clicked.connect(lambda _=False, s=sig, i=(salida.id if compatible else None): self._continuar_con(s, i))
            self._capa_sugerencias.addWidget(chip)
        self._capa_sugerencias.addStretch(1)
        self.fila_sugerencias.show()

    def _continuar_con(self, id_operacion: str, id_dato=None):
        if id_dato is not None:
            self._activar(id_dato)
        self.elegir_operacion(id_operacion)
        a = self.sesion.artefactos.get(id_dato) if id_dato else None
        exentas = {'explorar_imagen', 'convertir_grises', 'separar_canales', 'extraer_roi'}
        if a is not None and a.tipo != 'valores' and not a.metadatos.get('roi_confirmada') and id_operacion not in exentas:
            self.toast.mostrar('Antes de analizar este dato, confirme su región de análisis.', 'info', 4000,
                               ('Confirmar ROI…', self.confirmar_roi))
        else:
            self.toast.mostrar(f'«{CATALOGO[id_operacion].titulo}» lista. Revise los parámetros y pulse Ejecutar.',
                               'info', 3000)

    def _html_resumen(self, indice: int) -> str:
        c = tema().c
        oscuro = tema().oscuro
        texto, texto2, panel = _hex(c['texto']), _hex(c['texto2']), _hex(c['panel'])
        fondo_cifra = '#2C2C2E' if oscuro else '#F2F2F7'
        fondo_aviso = _mezclar(panel, _hex(c['aviso']), 0.16 if oscuro else 0.12)
        paso = self.sesion.pasos[indice]
        r = self.sesion.resultados[indice]
        op = CATALOGO[paso['operacion']]
        try:
            hora = datetime.fromisoformat(paso['fecha_utc']).astimezone().strftime('%d/%m/%Y %H:%M:%S')
        except Exception:
            hora = paso.get('fecha_utc', '')
        partes = [f'<p style="color:{texto2}; font-size:8pt; margin:0">PASO {indice + 1} · {html.escape(hora)}</p>',
                  f'<p style="font-size:13pt; font-weight:600; margin:2px 0 6px 0">{html.escape(op.titulo)}</p>']
        destacadas = [k for k in DESTACADAS.get(op.id, ()) if k in r.resumen]
        if not destacadas:
            destacadas = [k for k, v in r.resumen.items()
                          if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool)][:3]
        if destacadas:
            ancho = 100 // len(destacadas)
            celdas = ''.join(
                f'<td width="{ancho}%" style="background-color:{fondo_cifra}; padding:9px 12px;">'
                f'<span style="color:{texto2}; font-size:8pt">{html.escape(etiqueta_clave(k))}</span><br>'
                f'<span style="font-size:15pt; font-weight:600">{html.escape(formatear_valor(r.resumen[k]))}</span></td>'
                for k in destacadas)
            partes.append(f'<table width="100%" cellspacing="6" cellpadding="0" style="margin-left:-6px"><tr>{celdas}</tr></table>')
        if paso['salidas']:
            nombres = ', '.join(nombre_salida(k) for k in paso['salidas'])
            partes.append(f'<p style="margin:6px 0">Salidas: {html.escape(nombres)}. La salida no reemplaza la entrada: '
                          'elíjala en la tira y pulse «Continuar con esta versión».</p>')
        for adv in r.advertencias:
            partes.append(f'<table width="100%" cellpadding="8" cellspacing="0" style="margin:4px 0">'
                          f'<tr><td style="background-color:{fondo_aviso}">⚠&nbsp; {html.escape(adv)}</td></tr></table>')
        if r.resumen:
            filas = ''.join(f'<tr><td style="color:{texto2}; padding:3px 14px 3px 0">{html.escape(etiqueta_clave(k))}</td>'
                            f'<td style="padding:3px 0">{html.escape(formatear_valor(v))}</td></tr>'
                            for k, v in r.resumen.items())
            partes.append(f'<h4>Valores calculados</h4><table cellspacing="0">{filas}</table>')
        if paso['entradas']:
            filas = ''.join(f'<tr><td style="color:{texto2}; padding:3px 14px 3px 0">{html.escape(ENTRADAS.get(rol, rol))}</td>'
                            f'<td>{html.escape(self.sesion.artefactos[x].nombre if x in self.sesion.artefactos else x)} '
                            f'<span style="color:{texto2}">({x})</span></td></tr>' for rol, x in paso['entradas'].items())
            partes.append(f'<h4>Entradas</h4><table cellspacing="0">{filas}</table>')
        if paso['parametros']:
            filas = ''.join(
                f'<tr><td style="color:{texto2}; padding:3px 14px 3px 0">{html.escape(meta_parametro(op.id, n)["etiqueta"])}</td>'
                f'<td>{html.escape(etiqueta_opcion(n, v) if isinstance(v, str) else formatear_valor(v))} '
                f'<span style="color:{texto2}">({n})</span></td></tr>' for n, v in paso['parametros'].items())
            partes.append(f'<h4>Parámetros efectivos</h4><table cellspacing="0">{filas}</table>')
        registro = json.dumps(_jsonable({'operacion': paso['operacion'], 'entradas': paso['entradas'],
                                         'parametros': paso['parametros'], 'resumen': r.resumen,
                                         'advertencias': r.advertencias,
                                         'contextos_entrada': paso['contextos_entrada']}),
                              ensure_ascii=False, indent=2)
        partes.append(f'<h4>Registro técnico</h4><pre style="font-family:\'{familia_codigo()}\'; font-size:8pt; '
                      f'color:{texto2}">{html.escape(registro)}</pre>')
        self.resumen.document().setDefaultStyleSheet('h4 { font-size: 9.5pt; margin-top: 14px; margin-bottom: 4px; }')
        return f'<html><body style="color:{texto}">{"".join(partes)}</body></html>'

    def graficar(self):
        self.panel_grafica.dibujar()

    def _cambiar_pestana(self, nombre: str):
        indice = {'resumen': 0, 'tabla': 1, 'grafica': 2, 'historial': 3, 'script': 4}.get(nombre, 0)
        self.selector_resultados.establecer(indice)
        self._cambiar_pestana_indice(indice)

    def _cambiar_pestana_indice(self, indice: int):
        self.pila_resultados.setCurrentIndex(indice)
        self.acciones_panel.setCurrentIndex(indice)

    def _fila_elegida(self, index):
        if not index.isValid() or self.paso_actual is None or self._tira_previa:
            return
        fila = self.proxy.mapToSource(index).row()
        t = self.modelo.tabla
        if 'etiqueta' not in t:
            return
        etiqueta_obj = int(t.iloc[fila]['etiqueta'])
        paso = self.sesion.pasos[self.paso_actual]
        candidatos = [self.tira.currentData()] + list(paso['salidas'].values())
        for id_ in candidatos:
            a = self.sesion.artefactos.get(id_)
            if a is not None and a.tipo == 'etiquetas' and np.any(a.datos == etiqueta_obj):
                if self.tira.currentData() != id_:
                    self.tira.setCurrentRow(self.tira.findData(id_))
                if self.modo_vista == 'activo':
                    self._cambiar_modo_vista('lado')
                self.visor_salida.resaltar(a.datos == etiqueta_obj)
                return

    def _copiar_tabla(self):
        t = self.modelo.tabla
        if not len(t.columns):
            return
        QApplication.clipboard().setText(t.to_csv(sep='\t', index=False))
        self.toast.mostrar('Tabla copiada. Puede pegarla en una hoja de cálculo.', 'ok', 2400)

    def _exportar_csv(self):
        t = self.modelo.tabla
        if not len(t.columns):
            self.toast.mostrar('El resultado seleccionado no tiene tabla.', 'info')
            return
        ruta, _ = QFileDialog.getSaveFileName(self, 'Guardar tabla', str(Path(self._carpeta_reciente()) / 'tabla.csv'),
                                              'CSV (*.csv)')
        if not ruta:
            return
        try:
            if Path(ruta).exists():
                raise FileExistsError('El archivo ya existe. Elija otro nombre para no sobrescribir resultados.')
            t.to_csv(ruta, index=False, encoding='utf-8-sig')
            self.toast.mostrar(f'Tabla guardada en {ruta}', 'ok')
        except Exception as exc:
            self._error(str(exc), traceback.format_exc())

    # ------------------------------------------------------------------
    # Vista: modos, capas, zoom y sincronización
    # ------------------------------------------------------------------

    def _cambiar_modo_vista(self, modo: str):
        if modo == 'cortina':
            if not self._aplicar_cortina():
                self.toast.mostrar('La cortina necesita un resultado de imagen con la misma forma que el dato activo.',
                                   'info', 3600)
                modo = 'lado'
        else:
            self.visor_entrada.quitar_cortina()
        anterior = self.modo_vista
        self.modo_vista = modo
        self.visor_entrada.setVisible(modo in ('activo', 'lado', 'cortina'))
        self.visor_salida.setVisible(modo in ('resultado', 'lado'))
        if modo == 'lado' and anterior != 'lado':
            self.divisor_visores.setSizes([10_000, 10_000])
        self.selector_vista.establecer(MODOS_VISTA.index(modo))
        self.acc[f'modo_{modo}'].setChecked(True)
        if modo == 'lado':
            QTimer.singleShot(0, lambda: self._sincronizar_desde(self.visor_entrada))
        self._zoom_visor()

    def _aplicar_cortina(self) -> bool:
        id_b = self.tira.currentData()
        sesion = self._sesion_tira()
        b = sesion.artefactos.get(id_b)
        if b is None or b.datos.ndim < 2 or self.visor_entrada.arreglo is None:
            return False
        try:
            vista = preparar_vista(b, sesion, self.superponer.isChecked(), self.rotulos.isChecked())
            clave = self.tira.currentItem().data(Qt.ItemDataRole.UserRole + 1) if self.tira.currentItem() else ''
            return self.visor_entrada.mostrar_cortina(vista, self.opciones_vista, b.datos, b.tipo,
                                                      f'Resultado · {nombre_salida(clave)}')
        except Exception:
            return False

    def _capas_cambiadas(self, *_):
        color = next((a.data() for a in self.grupo_contorno.actions() if a.isChecked()), OPCIONES_VISTA['color_contorno'])
        self.opciones_vista.update(colores=self.accion_colores.isChecked(), estirar=self.accion_estirar.isChecked(),
                                   color_contorno=color)
        self._mostrar_activo()
        if self.tira.count():
            self._mostrar_salida()

    def _visores_visibles(self) -> list[VisorImagen]:
        return [v for v in (self.visor_entrada, self.visor_salida) if v.isVisible()] or [self.visor_entrada]

    def _zoom(self, tipo: str):
        visores = self._visores_visibles()
        if self.modo_vista == 'lado' and self.accion_sincronizar.isChecked():
            visores = visores[:1]
        for v in visores:
            {'ajustar': v.ajustar, '100': v.zoom_100, 'mas': v.acercar, 'menos': v.alejar}[tipo]()

    def _zoom_visor(self, *_):
        v = self._visores_visibles()[0]
        self.etiqueta_zoom.setText(f'{v.escala() * 100:.0f} %' if v.arreglo is not None else '—')

    def _sincronizar_desde(self, origen: VisorImagen):
        if self._sincronizando or self.modo_vista != 'lado' or not self.accion_sincronizar.isChecked():
            return
        destino = self.visor_salida if origen is self.visor_entrada else self.visor_entrada
        if origen._forma is None or origen._forma != destino._forma:
            return
        self._sincronizando = True
        try:
            destino.aplicar_estado(origen.estado_vista())
        finally:
            self._sincronizando = False

    def _alternar_lateral(self, visible: bool):
        self.lateral.setVisible(visible)

    def _alternar_inspector(self, visible: bool):
        self.inspector.setVisible(visible)

    def _alternar_panel(self, visible: bool):
        self.panel_inferior.setVisible(visible)

    def cambiar_apariencia(self, modo: str):
        tema().aplicar(modo)
        self.acc[f'apariencia_{modo}'].setChecked(True)
        if self.persistir:
            self._ajustes().setValue('apariencia', modo)

    def _tema_cambiado(self):
        self._colorear_arbol()
        self._render_ayuda()
        if self.paso_actual is not None and self.paso_actual < len(self.sesion.pasos):
            self.resumen.setHtml(self._html_resumen(self.paso_actual))
        self._miniaturas = {k: v for k, v in self._miniaturas.items() if k[2] == 0}

    # ------------------------------------------------------------------
    # Herramientas de dibujo: ROI, regla, perfil y calibración
    # ------------------------------------------------------------------

    def _imagen_activa(self):
        a = self.sesion.artefactos.get(self.datos.currentData())
        if a is None or a.datos.ndim < 2:
            self.toast.mostrar('Active primero una imagen para usar esta herramienta.', 'info')
            self._herramienta_cambiada(self.visor_entrada.herramienta())
            return None
        return a

    def _preparar_lienzo_para_dibujo(self, id_=None):
        """Muestra el mismo dato cuyas coordenadas recibirá la operación."""
        id_ = id_ or self.datos.currentData()
        a = self.sesion.artefactos.get(id_)
        if a is None or a.datos.ndim < 2:
            self.toast.mostrar('Seleccione una imagen para dibujar sobre ella.', 'info')
            return False
        self._activar(id_)
        if self.modo_vista in ('resultado', 'cortina'):
            self._cambiar_modo_vista('activo')
        self._mostrar_activo()
        return True

    def _usar_herramienta(self, nombre: str):
        if nombre == 'mover':
            self.visor_entrada.establecer_herramienta('mover')
            return
        if nombre == 'roi':
            self.dibujar_roi()
        elif nombre == 'perfil':
            self.dibujar_perfil()
        elif nombre == 'regla':
            if self._imagen_activa() is None:
                return
            if not self._preparar_lienzo_para_dibujo():
                return
            self.modo_linea = 'regla'
            self.visor_entrada.establecer_herramienta('linea')
            self.toast.mostrar('Regla: arrastre entre dos puntos o haga dos clics. Esc cancela.', 'info', 3000)

    def _herramienta_cambiada(self, nombre: str):
        if nombre == 'roi':
            boton = self.btn_roi
        elif nombre == 'linea':
            boton = self.btn_perfil if self.modo_linea == 'perfil' else self.btn_regla
        else:
            boton = self.btn_mover
        boton.setChecked(True)

    def cancelar_herramienta(self):
        if self.hoja.isVisible():
            self.hoja.hide()
        self.visor_entrada.establecer_herramienta('mover')

    def dibujar_roi(self):
        id_ = self._id_entrada_principal() if self.op_actual == 'extraer_roi' else self.datos.currentData()
        a = self.sesion.artefactos.get(id_)
        if a is None or a.tipo not in CATALOGO['extraer_roi'].entradas[0].tipos:
            self.toast.mostrar('Para recortar, seleccione la imagen original o una versión en escala de grises.',
                               'info', 4200)
            self._herramienta_cambiada(self.visor_entrada.herramienta())
            return
        self._activar(id_)
        self.elegir_operacion('extraer_roi')
        if not self._preparar_lienzo_para_dibujo(id_):
            return
        self.visor_entrada.establecer_herramienta('roi')
        self.toast.mostrar('Arrastre un rectángulo sobre la imagen para elegir la región. Esc cancela.', 'info', 3600)

    def _roi_elegida(self, r0, r1, c0, c1):
        for n, x in zip(('r0', 'r1', 'c0', 'c1'), (r0, r1, c0, c1)):
            if n in self.campos:
                self.campos[n].setText(str(x))
                self.campos[n].editado_por_usuario = True
        self.visor_entrada.establecer_herramienta('mover')
        self.visor_entrada.mostrar_roi(r0, r1, c0, c1)
        self.toast.mostrar(f'Región de {c1 - c0} × {r1 - r0} px [{r0}:{r1}, {c0}:{c1}]. '
                           'Pulse «Recortar región» para crearla.', 'info', 4200)

    def _sincronizar_roi_visor(self, *_):
        if self.op_actual != 'extraer_roi' or not all(n in self.campos for n in ('r0', 'r1', 'c0', 'c1')):
            return
        principal = self._id_entrada_principal()
        if principal != self.datos.currentData():
            self.visor_entrada.ocultar_dibujos()
            return
        try:
            valores = [int(self.campos[n].text()) for n in ('r0', 'r1', 'c0', 'c1')]
        except ValueError:
            return
        r0, r1, c0, c1 = valores
        forma = self.visor_entrada._forma
        if forma is not None and (r0, r1, c0, c1) != (0, forma[0], 0, forma[1]):
            self.visor_entrada.mostrar_roi(r0, r1, c0, c1)
        else:
            self.visor_entrada.ocultar_dibujos()

    def confirmar_roi(self, id_=None):
        if self._ocupada:
            return
        id_ = id_ if isinstance(id_, str) else self.datos.currentData()
        if not id_ or id_ not in self.sesion.artefactos:
            return
        a = self.sesion.artefactos[id_]
        dialogo = DialogoConfirmarROI(self, a.nombre, self._miniatura_dato(id_, 150), a.metadatos.get('nota_roi', ''))
        aceptado = dialogo.exec() == QDialog.DialogCode.Accepted
        nota = dialogo.texto_nota()
        dialogo.deleteLater()
        if aceptado:
            try:
                self.sesion.confirmar_roi(id_, nota)
                self.modificada = True
                self._actualizar_datos()
                self.toast.mostrar('Región confirmada. Ya puede analizar este dato.', 'ok', 3000)
            except Exception as exc:
                self._error(str(exc))

    def medir_referencia(self):
        id_ = self.datos.currentData()
        a = self.sesion.artefactos.get(id_)
        if a is None or a.tipo not in ('imagen', 'gris'):
            self.toast.mostrar('Seleccione la imagen original o una versión en escala de grises que conserve '
                               'la referencia de longitud.', 'info', 4200)
            self._herramienta_cambiada(self.visor_entrada.herramienta())
            return
        self.modo_linea = 'calibracion'
        self.elegir_operacion('calibrar_escala')
        if not self._preparar_lienzo_para_dibujo(id_):
            return
        self.visor_entrada.establecer_herramienta('linea')
        self._herramienta_cambiada('linea')
        self.toast.mostrar('Marque los dos extremos de la barra de escala o del patrón: arrastre o haga dos clics.',
                           'info', 4200)

    def _calibrar_entrada_principal(self):
        principal = self._id_entrada_principal()
        if principal:
            self._activar(principal)
        self.medir_referencia()

    def dibujar_perfil(self):
        id_ = self._id_entrada_principal() if self.op_actual == 'perfil_intensidad' else self.datos.currentData()
        a = self.sesion.artefactos.get(id_)
        if a is None or a.tipo not in CATALOGO['perfil_intensidad'].entradas[0].tipos:
            self.toast.mostrar('El perfil necesita una imagen en escala de grises. Convierta la imagen '
                               'y seleccione esa versión antes de trazar la línea.', 'info', 4200)
            self._herramienta_cambiada(self.visor_entrada.herramienta())
            return
        self._activar(id_)
        self.modo_linea = 'perfil'
        self.elegir_operacion('perfil_intensidad')
        if not self._preparar_lienzo_para_dibujo(id_):
            return
        self.visor_entrada.establecer_herramienta('linea')
        self._herramienta_cambiada('linea')
        self.toast.mostrar('Dibuje la línea del perfil: arrastre o haga dos clics.', 'info', 3200)

    def _linea_elegida(self, r0, c0, r1, c1):
        largo = math.hypot(r1 - r0, c1 - c0)
        if self.modo_linea == 'calibracion' and 'referencia_px' in self.campos:
            self.linea_referencia = {'artefacto': self.datos.currentData(), 'extremos_rc': [r0, c0, r1, c1],
                                     'longitud_px': largo}
            self.campos['referencia_px'].setText(f'{largo:.12g}')
            self.campos['referencia_px'].editado_por_usuario = True
            self.toast.mostrar(f'Referencia medida: {largo:.6g} px. Introduzca su longitud real en µm y pulse '
                               '«Calcular escala».', 'info', 5000)
            if 'referencia_um' in self.campos:
                self.campos['referencia_um'].setFocus()
                self.campos['referencia_um'].selectAll()
        elif self.modo_linea == 'perfil' and self.op_actual == 'perfil_intensidad':
            for n, x in zip(('r0', 'c0', 'r1', 'c1'), (r0, c0, r1, c1)):
                if n in self.campos:
                    self.campos[n].setText(f'{x:.12g}')
                    self.campos[n].editado_por_usuario = True
            self.toast.mostrar(f'Segmento de {largo:.1f} px. Pulse «Obtener perfil».', 'info', 3000)
        else:
            escala = self.visor_entrada.escala_um
            texto = f'Distancia: {largo:.2f} px'
            if escala:
                texto += f' = {largo * escala:.4g} µm (con la escala del dato)'
            self.toast.mostrar(texto, 'info', 5000)
        self.visor_entrada.establecer_herramienta('mover')

    def aplicar_escala(self):
        if self._ocupada:
            return
        id_ = self.datos.currentData()
        if not id_ or self.ultima_escala is None:
            return
        respuesta = QMessageBox.question(self, 'Asociar calibración',
            f'¿Aplicar {self.ultima_escala.um_por_px:.8g} µm/px a {id_}?\n'
            'Confirme que la referencia corresponde a esta configuración y resolución. Las medidas previas no cambiarán.')
        if respuesta == QMessageBox.StandardButton.Yes:
            try:
                self.sesion.establecer_escala(id_, self.ultima_escala, self.ultima_calibracion)
                self.modificada = True
                self._actualizar_datos()
                self.toast.mostrar(f'Escala de {self.ultima_escala.um_por_px:.6g} µm/px asociada a '
                                   f'«{self.sesion.artefactos[id_].nombre}».', 'ok', 3600)
            except Exception as exc:
                self._error(str(exc))

    # ------------------------------------------------------------------
    # Acciones sobre datos
    # ------------------------------------------------------------------

    def anotar_dato(self):
        if self._ocupada:
            return
        id_ = self.datos.currentData()
        if id_ not in self.sesion.artefactos:
            return
        a = self.sesion.artefactos[id_]
        dialogo = DialogoMetadatos(self, a.nombre, a.metadatos.get('anotaciones', {}))
        aceptado = dialogo.exec() == QDialog.DialogCode.Accepted
        valores = dialogo.valores()
        dialogo.deleteLater()
        if aceptado:
            self.sesion.anotar(id_, valores)
            self.modificada = True
            self.toast.mostrar('Metadatos registrados en la sesión.', 'ok', 2400)

    def asociar_fuente(self):
        if self._ocupada:
            return
        id_ = self.datos.currentData()
        if id_ not in self.sesion.artefactos:
            return
        a = self.sesion.artefactos[id_]
        candidatos = [(x, f'{b.nombre}  ·  {x}', self._miniatura_dato(x, 44)) for x, b in self.sesion.artefactos.items()
                      if b.tipo in ('imagen', 'gris') and b.datos.shape[:2] == a.datos.shape]
        if not candidatos:
            self._error('Importe o recorte primero una imagen fuente de la misma forma.')
            return
        dialogo = DialogoAsociarFuente(self, a.nombre, candidatos)
        aceptado = dialogo.exec() == QDialog.DialogCode.Accepted
        imagen, nota = dialogo.eleccion() if aceptado else (None, '')
        dialogo.deleteLater()
        if aceptado:
            try:
                self.sesion.asociar_fuente(id_, imagen, nota)
                self.modificada = True
                self._actualizar_datos()
                self._mostrar_salida()
                self.toast.mostrar('Imagen fuente asociada: el mapa hereda su escala y su región.', 'ok', 3200)
            except Exception as exc:
                self._error(str(exc))

    def importar(self, tipo, ruta=None):
        if self._ocupada:
            return
        if not isinstance(ruta, str) or not ruta:
            filtro = ('CSV (*.csv)' if tipo == 'valores' else
                      'Imágenes y arreglos (*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.npy);;Todos los archivos (*)')
            ruta, _ = QFileDialog.getOpenFileName(self, f'Importar {nombre_tipo(tipo).lower()}', self._carpeta_reciente(),
                                                  filtro)
            if not ruta:
                return
        try:
            if tipo == 'imagen':
                datos = cargar_imagen(ruta)
            elif tipo in ('mascara', 'limites'):
                datos = cargar_mascara(ruta)
            elif tipo == 'valores':
                columnas = list(pd.read_csv(ruta, nrows=0).columns)
                columna, ok = QInputDialog.getItem(self, 'Columna de resultados',
                                                   'Elija la columna con un valor por campo o probeta:', columnas, 0, False)
                if not ok:
                    return
                datos = cargar_valores(ruta, columna)
            else:
                datos = cargar_etiquetas(ruta)
            meta = {'archivo': Path(ruta).name, 'sha256_archivo': sha256_archivo(ruta),
                    'procedencia': 'Archivo importado por el usuario; material y configuración no inferidos.'}
            if tipo == 'valores':
                meta['columna_csv'] = columna
            id_ = self.sesion.agregar(datos, tipo, Path(ruta).name, meta)
            self.modificada = True
            self._recordar_carpeta(Path(ruta).parent)
            self._actualizar_datos(id_)
            if tipo == 'imagen':
                self.elegir_operacion('explorar_imagen')
                self.selector_lateral.establecer(0, emitir=True)
                self._cambiar_modo_vista('activo')
                self.toast.mostrar(f'«{Path(ruta).name}» conservada como original. '
                                   'Calibre antes de recortar si la imagen contiene una barra de escala.', 'ok', 6000,
                                   ('Calibrar', self.medir_referencia))
            elif tipo == 'valores':
                self.toast.mostrar(f'{len(datos)} valores importados de la columna «{columna}».', 'ok', 5000,
                                   ('Intervalo bootstrap', lambda: self.elegir_operacion('intervalo_bootstrap_media')))
            else:
                self.toast.mostrar('Mapa importado. Para superponerlo y heredar la escala, asócielo a su imagen fuente.',
                                   'ok', 6000, ('Asociar imagen fuente…', self.asociar_fuente))
        except Exception as exc:
            self._error(str(exc), traceback.format_exc())

    def cargar_ejemplo(self):
        if self._ocupada:
            return
        from micrograno.sinteticos import crear_conjunto
        id_ = self.sesion.agregar(crear_conjunto()['rgb'], 'imagen', 'Ejemplo sintético RGB',
            {'sintetico': True, 'procedencia': 'Generado por micrograno.sinteticos; no es una micrografía.'})
        self.sesion.establecer_escala(id_, EscalaEspacial(0.5, referencia='Convención del ejemplo sintético'))
        self.modificada = True
        self._actualizar_datos(id_)
        self.elegir_operacion('explorar_imagen')
        self.selector_lateral.establecer(0, emitir=True)
        self._cambiar_modo_vista('activo')
        self.toast.mostrar('Ejemplo sintético: 0.5 µm/px es una convención. Convierta a grises y recorte una ROI para empezar.',
                           'info', 6500, ('Convertir a grises', lambda: self._abrir_leccion('convertir_grises')))

    def cargar_demo(self):
        if self._ocupada:
            return
        from micrograno.sinteticos import poblar_sesion
        ids = poblar_sesion(self.sesion)
        self.modificada = True
        self._actualizar_datos(ids['gris'])
        self.elegir_operacion('histograma_percentiles')
        self.toast.mostrar('Conjunto sintético cargado. La escala de 0.5 µm/px es una convención de prueba, '
                           'no la de un microscopio.', 'info', 5200)

    # ------------------------------------------------------------------
    # Sesiones y exportación
    # ------------------------------------------------------------------

    def _puede_reemplazar(self) -> bool:
        if not self.modificada:
            return True
        caja = QMessageBox(self)
        caja.setIcon(QMessageBox.Icon.Warning)
        caja.setWindowTitle('Cambios sin guardar')
        caja.setText('¿Desea guardar los cambios de la sesión actual?')
        caja.setInformativeText('Si no los guarda, se perderán las operaciones realizadas desde el último guardado.')
        guardar = caja.addButton('Guardar…', QMessageBox.ButtonRole.AcceptRole)
        descartar = caja.addButton('No guardar', QMessageBox.ButtonRole.DestructiveRole)
        caja.addButton('Cancelar', QMessageBox.ButtonRole.RejectRole)
        caja.setDefaultButton(guardar)
        caja.exec()
        if caja.clickedButton() is guardar:
            return bool(self.guardar_sesion())
        return caja.clickedButton() is descartar

    def _reiniciar_estado(self):
        self._detener_vista_previa(restaurar=False)
        self.paso_actual = None
        self.ultima_escala = None
        self.linea_referencia = None
        self.ultima_calibracion = {}
        self._miniaturas = {}
        self._clave_preferida = None
        self.aplicar.setEnabled(False)
        self._limpiar_resultados()

    def nueva_sesion(self):
        if self._ocupada:
            return
        if not self._puede_reemplazar():
            return
        self.sesion = Sesion()
        self.ruta_sesion = None
        self._explorar = False
        self._reiniciar_estado()
        self.modificada = False
        self._actualizar_datos()
        self._formulario(conservar=False)

    def _carpeta_nueva(self, titulo, subtitulo: str = '', nombre: str = '', icono: str = 'guardar',
                       boton: str = 'Guardar'):
        dialogo = DialogoCarpetaNueva(self, titulo, subtitulo or 'Elija dónde crear la carpeta. Debe ser nueva para '
                                      'no sobrescribir datos.', nombre, self._carpeta_reciente(), icono, boton)
        aceptado = dialogo.exec() == QDialog.DialogCode.Accepted
        ruta = dialogo.ruta()
        dialogo.deleteLater()
        if not aceptado:
            return None
        self._recordar_carpeta(ruta.parent)
        return ruta

    def guardar_sesion(self):
        try:
            carpeta = self._carpeta_nueva('Guardar sesión',
                                          'Se guardarán los arreglos exactos, los metadatos, los parámetros, los '
                                          'resultados y un programa reproducir.py.',
                                          datetime.now().strftime('sesion_%Y-%m-%d_%H%M'))
            if carpeta is None:
                return False
            ruta = self.sesion.guardar(carpeta)
            self.ruta_sesion = str(ruta)
            self.modificada = False
            self._agregar_reciente(str(ruta))
            self.toast.mostrar(f'Sesión y reproducir.py guardados en {ruta.parent}', 'ok', 6000,
                               ('Mostrar carpeta', lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta.parent)))))
            return True
        except Exception as exc:
            self._error(str(exc), traceback.format_exc())
            return False

    def abrir_sesion(self, ruta=None):
        if self._ocupada:
            return
        if not self._puede_reemplazar():
            return
        if not isinstance(ruta, str) or not ruta:
            ruta, _ = QFileDialog.getOpenFileName(self, 'Abrir sesión', self._carpeta_reciente(),
                                                  'Sesión de MicroGrano (sesion.json)')
            if not ruta:
                return
        try:
            nueva = Sesion.abrir(ruta)
            self.sesion = nueva
            self._reiniciar_estado()
            self.ruta_sesion = str(Path(ruta).resolve() if Path(ruta).is_file() else Path(ruta).resolve() / 'sesion.json')
            self.modificada = False
            self.codigo_sesion.setPlainText(nueva.codigo())
            for i in range(len(nueva.pasos)):
                self._agregar_historial(i)
            self._actualizar_datos()
            if nueva.pasos:
                self._ver_paso(len(nueva.pasos) - 1, cambiar_pestana=False)
            self._formulario()
            self._agregar_reciente(self.ruta_sesion)
            self._recordar_carpeta(Path(self.ruta_sesion).parent.parent)
            self.toast.mostrar('Sesión abierta y hashes de los datos verificados. Recalcule con el comando '
                               '«micrograno reproducir».', 'ok', 5200)
        except Exception as exc:
            self._error(str(exc), traceback.format_exc())

    def exportar_resultado(self):
        if self.paso_actual is None:
            self._error('Ejecute o seleccione un resultado del historial.')
            return
        try:
            carpeta = self._carpeta_nueva('Exportar resultado', 'Arreglos NPY exactos, tabla CSV y resumen JSON del paso '
                                          'seleccionado.', f'resultado_paso_{self.paso_actual + 1:03d}', 'exportar',
                                          'Exportar')
            if carpeta is None:
                return
            guardar_resultado(self.sesion.resultados[self.paso_actual], carpeta, self.sesion.pasos[self.paso_actual])
            self.toast.mostrar(f'Resultado exportado: {carpeta}', 'ok', 5200,
                               ('Mostrar carpeta', lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(carpeta)))))
        except Exception as exc:
            self._error(str(exc), traceback.format_exc())

    def exportar_todas_versiones(self):
        if not self.sesion.artefactos:
            self.toast.mostrar('Abra una imagen para crear la primera versión.', 'info')
            return
        if self._ocupada:
            return
        carpeta = self._carpeta_nueva('Exportar todas las versiones',
            f'Se exportarán las {len(self.sesion.artefactos)} versiones conservadas, incluidos originales y variantes. '
            'NPY y TIFF conservan datos; los PNG son vistas. Se incluyen las tablas y un índice de procedencia.',
            datetime.now().strftime('versiones_%Y-%m-%d_%H%M'), 'exportar', 'Exportar todo')
        if carpeta is None:
            return
        self._detener_vista_previa()
        self._ocupado(True)
        self.ejecutar_btn.setText('Exportando versiones…')
        self.trabajo = TrabajoExportacion(self.sesion, carpeta, self)
        self.trabajo.correcto.connect(self._versiones_exportadas)
        self.trabajo.fallo.connect(self._error)
        self.trabajo.finished.connect(self._trabajo_terminado)
        self.trabajo.start()

    @Slot(object)
    def _versiones_exportadas(self, ruta):
        self.toast.mostrar(f'Todas las versiones exportadas en {ruta.parent}', 'ok', 7000,
            ('Mostrar carpeta', lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(ruta.parent)))))

    def exportar_vista(self, id_=None):
        explicito = isinstance(id_, str)
        if not explicito:
            id_ = self.datos.currentData()
        elif self._tira_previa and id_ == self.tira.currentData():
            self.toast.mostrar('Ejecute la operación para conservar esta vista previa antes de exportarla.',
                               'info', 4200)
            return
        if id_ not in self.sesion.artefactos:
            self.toast.mostrar('Seleccione una versión de imagen para exportar.', 'info')
            return
        a = self.sesion.artefactos[id_]
        if a.datos.ndim == 1:
            self._error('Esta exportación corresponde a imágenes. Use «Guardar la gráfica» para una distribución.')
            return
        dialogo = DialogoExportarFigura(self, a.nombre, self._miniatura_dato(id_, 120), self._carpeta_reciente())
        aceptado = dialogo.exec() == QDialog.DialogCode.Accepted
        v = dialogo.valores()
        dialogo.deleteLater()
        if not aceptado:
            return
        try:
            vista = preparar_vista(a, self.sesion, self.superponer.isChecked(), False)
            ficha = exportar_figura(vista['imagen'], v['ruta'], titulo=v['titulo'], descripcion=v['descripcion'],
                                    fuente=v['fuente'], tipo=vista['tipo'], limites=vista['contornos'])
            self._recordar_carpeta(Path(v['ruta']).parent)
            if ficha['advertencia_tipografica']:
                self.toast.mostrar(f'Figura guardada: {v["ruta"]}. {ficha["advertencia_tipografica"]}', 'aviso', 8000)
            else:
                self.toast.mostrar(f'Figura guardada: {v["ruta"]}', 'ok', 4200)
        except Exception as exc:
            self._error(str(exc), traceback.format_exc())

    # ------------------------------------------------------------------
    # Vista previa en vivo
    # ------------------------------------------------------------------

    def _programar_previa(self):
        if (self.interruptor_previa.isChecked() and self.op_actual in VISTA_PREVIA and not self._ocupada):
            self._previa['secuencia'] += 1
            self._temporizador_previa.start()

    def _alternar_vista_previa(self, activo: bool):
        if activo:
            self.estado_previa.setText('Recalculando al cambiar parámetros…')
            self._programar_previa()
        else:
            self._detener_vista_previa()
            self.estado_previa.setText('Recalcula al cambiar parámetros, sin registrar.')

    def _detener_vista_previa(self, restaurar: bool = True):
        self._temporizador_previa.stop()
        self._previa['secuencia'] += 1
        self._previa['pendiente'] = False
        self._previa.update(resultado=None, salidas=None, sesion=None)
        if self._tira_previa:
            self._tira_previa = False
            if restaurar and self.paso_actual is not None:
                self._ver_paso(self.paso_actual, cambiar_pestana=False)
            elif restaurar:
                self.tira.clear()
                self.caja_tira.hide()
                self.visor_salida.limpiar('Sin resultado', 'Ejecute una herramienta para ver aquí su salida.', 'destello')

    def _lanzar_vista_previa(self):
        if not self.interruptor_previa.isChecked() or self.op_actual not in VISTA_PREVIA or self._ocupada:
            return
        hilo = self._previa['hilo']
        if hilo is not None and hilo.isRunning():
            self._previa['pendiente'] = True
            return
        try:
            parametros = self._leer_parametros()
        except Exception as exc:
            self.estado_previa.setText(f'En pausa: {exc}')
            return
        op = CATALOGO[self.op_actual]
        entradas = {n: w.currentData() for n, w in self.entradas.items() if w.currentData() is not None}
        if any(not e.opcional and e.nombre not in entradas for e in op.entradas):
            self.estado_previa.setText('Elija las entradas para ver la vista previa.')
            return
        artefactos = {rol: self.sesion.artefactos[x] for rol, x in entradas.items()}
        if any(a.datos.ndim >= 2 and a.datos.shape[0] * a.datos.shape[1] > LIMITE_PREVIA_PX for a in artefactos.values()):
            self.estado_previa.setText('Imagen demasiado grande para la vista previa en vivo; use Ejecutar.')
            return
        self._previa['secuencia'] += 1
        hilo = TrabajoVistaPrevia(self._previa['secuencia'],
                                  [(rol, a.datos, a.tipo, a.nombre, a.metadatos) for rol, a in artefactos.items()],
                                  self.op_actual, parametros, self)
        hilo.listo.connect(self._previa_lista)
        hilo.fallo.connect(self._previa_fallo)
        hilo.finished.connect(self._previa_terminada)
        self._previa['hilo'] = hilo
        self.estado_previa.setText('Calculando…')
        hilo.start()

    def _previa_terminada(self):
        hilo = self._previa['hilo']
        if hilo is not None:
            hilo.deleteLater()
        self._previa['hilo'] = None
        if self._previa['pendiente']:
            self._previa['pendiente'] = False
            self._lanzar_vista_previa()

    def _previa_lista(self, secuencia, datos):
        if secuencia != self._previa['secuencia'] or not self.interruptor_previa.isChecked() or self._ocupada:
            return
        r, salidas, temporal = datos
        self._previa.update(resultado=r, salidas=salidas, sesion=temporal)
        self._tira_previa = True
        self._llenar_tira(salidas, temporal)
        self.titulo_tira.setText(f'Vista previa · {CATALOGO[self.op_actual].titulo}')
        self.sub_tira.setText('No registrada. Pulse Ejecutar para guardarla en la sesión.')
        self._limpiar_sugerencias()
        if self.modo_vista == 'activo' and self.tira.count():
            self._cambiar_modo_vista('lado')
        self._mostrar_salida()
        self._actualizar_acciones()
        self.estado_previa.setText('Al día · no se registra en la sesión.')

    def _previa_fallo(self, secuencia, mensaje):
        if secuencia == self._previa['secuencia']:
            self.estado_previa.setText(f'En pausa: {mensaje}')

    # ------------------------------------------------------------------
    # Ayuda, guía y búsqueda global
    # ------------------------------------------------------------------

    def mostrar_flujo(self):
        self.acc['barra_lateral'].setChecked(True)
        self.selector_lateral.establecer(0, emitir=True)

    def _guia_html(self) -> str:
        c = tema().c
        texto2 = _hex(c['texto2'])
        pasos = ''.join(f'<tr><td style="padding:6px 12px 6px 0; font-weight:600; color:{_hex(c["acento"])}">{i}</td>'
                        f'<td style="padding:6px 0"><b>{html.escape(paso["titulo"])}</b><br>'
                        f'<span style="color:{texto2}">{html.escape(paso["descripcion"])}</span></td></tr>'
                        for i, paso in enumerate(PASOS_APRENDIZAJE, 1))
        consejos = [
            'En cada lección revise qué hace la función, sus entradas y sus salidas. Consulte la pestaña Python para ver un ejemplo de la biblioteca.',
            'Seleccione una salida y pulse «Continuar con esta versión». El panel «Versiones» conserva el original, los grises, la ROI y las variantes.',
            'Ejecute la operación para conservar una vista previa antes de continuar o exportarla.',
            'Calibre sobre la imagen original antes de recortar la barra. La escala no se infiere de «100X» ni del nombre del archivo.',
            'Watershed necesita una máscara; medir objetos, etiquetas de instancias; las fracciones, clases.',
            'Canny produce límites candidatos, no granos. Las clases no identifican fases.',
            'Pulse una fila de la tabla para resaltar el objeto en la imagen.',
            'Los intervalos estadísticos usan valores por campo o probeta, no partículas como réplicas.',
            'Intercepción y ponderación planimétrica no constituyen la aplicación completa de ASTM E112.',
        ]
        lista = ''.join(f'<li>{html.escape(x)}</li>' for x in consejos)
        return (f'<p>Siga las mismas ocho etapas del panel «Pasos». Cada ejecución conserva sus entradas y resultados.</p>'
                f'<table cellspacing="0">{pasos}</table><h3>Recuerde</h3><ul>{lista}</ul>'
                '<h3>Guardar y exportar</h3>'
                '<p><b>Guardar sesión</b> permite reabrir el análisis y conserva datos exactos, parámetros, '
                'contexto y <code>reproducir.py</code>.</p>'
                '<p><b>Exportar todas las versiones</b> crea archivos NPY y TIFF compatibles, vistas PNG, tablas '
                'y un índice de procedencia. Los PNG son representaciones para visualizar; los datos exactos '
                'se conservan en NPY y TIFF. Exportar no sustituye guardar la sesión antes de cerrar.</p>'
                f'<p style="color:{texto2}">Los valores iniciales son demostrativos, no parámetros validados para un '
                'material. El programa procesa las imágenes localmente.</p>')

    @staticmethod
    def _mostrar_dialogo(dialogo: QDialog) -> None:
        dialogo.exec()
        dialogo.deleteLater()

    def mostrar_guia(self):
        self._mostrar_dialogo(DialogoTexto(self, 'Guía de trabajo', self._guia_html(), 'ayuda', SISTEMA['azul']))

    def mostrar_atajos(self):
        self._mostrar_dialogo(DialogoAtajos(self))

    def mostrar_entorno(self):
        datos = json.dumps(metadatos_entorno(), ensure_ascii=False, indent=2)
        self._mostrar_dialogo(DialogoTexto(self, 'Entorno instalado',
                                           f'<pre style="font-family:\'{familia_codigo()}\'">{html.escape(datos)}</pre>',
                                           'codigo', SISTEMA['gris']))

    def mostrar_acerca(self):
        texto2 = _hex(tema().c['texto2'])
        self._mostrar_dialogo(DialogoTexto(
            self, 'MicroGrano 1.0.0',
            '<p><b>MicroGrano Lab</b> · biblioteca e interfaz del libro de Andrés Felipe Saavedra Sajaus.</p>'
            '<p>Se agradece el apoyo de la Universidad Tecnológica de Pereira, a través de la Vicerrectoría de '
            'Investigaciones, Innovación y Extensión.</p>'
            f'<p style="color:{texto2}">Los ejemplos son sintéticos. Las referencias del manuscrito aún requieren '
            'verificación bibliográfica. La biblioteca no identifica materiales, no controla equipos y no '
            'calcula rugosidad ni enfoque.</p>', 'info', SISTEMA['azul'], 520, 200))

    def _texto(self, titulo, texto):
        self._mostrar_dialogo(DialogoTexto(self, titulo, f'<p>{html.escape(texto).replace(chr(10), "<br>")}</p>',
                                           'info', SISTEMA['azul'], 520, 220))

    def abrir_paleta(self):
        if self._ocupada:
            return
        entradas = []
        for op in CATALOGO.values():
            color = GRUPOS.get(op.grupo, {}).get('color', SISTEMA['azul'])
            entradas.append({'titulo': op.titulo, 'subtitulo': f'Herramienta · {op.grupo}',
                             'claves': f'{op.id} {OPERACIONES.get(op.id, {}).get("resumen", "")}',
                             'icono': iconos.icono_insignia(OPERACIONES.get(op.id, {}).get('icono', 'dato'), color),
                             'accion': lambda i=op.id: (self.acc['inspector'].setChecked(True), self.elegir_operacion(i))})
        for id_, a in self.sesion.artefactos.items():
            entradas.append({'titulo': a.nombre, 'subtitulo': f'Dato · {id_} · {descripcion_dato(a)}',
                             'claves': a.tipo, 'icono': self._icono_dato(id_), 'accion': lambda i=id_: self._activar(i)})
        for clave in ('importar_imagen', 'ejemplo', 'demo', 'abrir', 'guardar', 'nueva', 'exportar_versiones', 'exportar_resultado', 'exportar_figura',
                      'usar', 'confirmar_roi', 'calibrar', 'asociar', 'metadatos', 'flujo', 'guia', 'atajos',
                      'apariencia_auto', 'apariencia_claro', 'apariencia_oscuro'):
            a = self.acc[clave]
            if not a.isEnabled():
                continue
            atajo = a.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
            texto = a.text().replace('&', '').rstrip('…')
            if clave.startswith('apariencia_'):
                texto = f'Apariencia: {texto}'
            if clave.startswith('importar_'):
                texto = f'Importar {texto.lower()}'
            entradas.append({'titulo': texto, 'subtitulo': 'Acción' + (f' · {atajo}' if atajo else ''),
                             'claves': clave, 'icono': a.icon(), 'accion': a.trigger})
        paleta = PaletaComandos(self, entradas)
        paleta.abrir_sobre(self)
        aceptado = paleta.exec() == QDialog.DialogCode.Accepted
        elegido = paleta.elegido()
        paleta.deleteLater()
        if aceptado and elegido:
            elegido['accion']()

    # ------------------------------------------------------------------
    # Errores y mensajes
    # ------------------------------------------------------------------

    @Slot(str, str)
    def _error(self, texto, detalle=''):
        texto = str(texto)
        sugerencia = sugerencia_error(texto)
        acciones = []
        if sugerencia:
            titulo, explicacion, sugeridas = sugerencia
            for etiqueta_accion, clave in sugeridas:
                acciones.append((etiqueta_accion, self._accion_sugerida(clave)))
            mensaje = f'{explicacion}\n\nDetalle: {texto}'
        else:
            titulo = 'No se pudo completar la acción'
            mensaje = texto
        self.hoja.mostrar(titulo, mensaje, 'error', acciones, detalle)
        self._resaltar_error(texto)

    def _accion_sugerida(self, clave: str):
        principal = self._id_entrada_principal()
        if clave == 'confirmar_roi':
            return lambda: self.confirmar_roi(principal)
        if clave == 'recortar':
            return lambda: (self._activar(principal) if principal else None, self.dibujar_roi())
        if clave == 'calibrar':
            return self._calibrar_entrada_principal
        if clave == 'escala_dato':
            return lambda: self._entrada_cambiada()
        return lambda: None

    def _resaltar_error(self, texto: str):
        opcionales = {e.nombre: e.opcional for e in CATALOGO[self.op_actual].entradas}
        for n, combo in self.entradas.items():
            error = combo.currentData() is None and not opcionales.get(n, True) and ('Falta' in texto or n in texto)
            if bool(combo.property('error')) != error:
                combo.setProperty('error', error)
                combo.style().unpolish(combo)
                combo.style().polish(combo)
        for n, w in self.campos.items():
            if isinstance(w, CampoNumero) and f'({n})' in texto:
                w.setProperty('error', True)
                w.style().unpolish(w)
                w.style().polish(w)
                self.selector_inspector.establecer(0, emitir=True)
                self.scroll.ensureWidgetVisible(w)

    # ------------------------------------------------------------------
    # Arrastrar y soltar, ajustes y cierre
    # ------------------------------------------------------------------

    def dragEnterEvent(self, evento):
        if self._ocupada:
            evento.ignore()
            return
        datos = evento.mimeData()
        if datos.hasUrls() and any(Path(u.toLocalFile()).suffix.lower() in EXTENSIONES for u in datos.urls()):
            evento.acceptProposedAction()

    def dropEvent(self, evento):
        if self._ocupada:
            evento.ignore()
            return
        rutas = [Path(u.toLocalFile()) for u in evento.mimeData().urls() if u.isLocalFile()]
        for ruta in rutas:
            sufijo = ruta.suffix.lower()
            if sufijo not in EXTENSIONES:
                continue
            if ruta.name == 'sesion.json':
                self.abrir_sesion(str(ruta))
                return
            if sufijo == '.csv':
                self.importar('valores', str(ruta))
                continue
            if sufijo == '.json':
                continue
            menu = QMenu(self)
            menu.addSection(f'Importar «{ruta.name}» como')
            for texto, tipo in TIPOS_IMPORTACION[:-1]:
                accion = menu.addAction(iconos.icono(TIPOS[tipo]['icono']), texto)
                accion.setData(tipo)
            elegida = menu.exec(QCursor.pos())
            if elegida is not None and elegida.data():
                self.importar(elegida.data(), str(ruta))
        evento.acceptProposedAction()

    def _ajustes(self) -> QSettings:
        return QSettings('MicroGrano', 'MicroGrano Lab')

    def _carpeta_reciente(self) -> str:
        if self.persistir:
            carpeta = self._ajustes().value('ultima_carpeta', self._ultima_carpeta)
            if carpeta and Path(str(carpeta)).is_dir():
                return str(carpeta)
        return self._ultima_carpeta if Path(self._ultima_carpeta).is_dir() else str(Path.home())

    def _recordar_carpeta(self, carpeta) -> None:
        self._ultima_carpeta = str(carpeta)
        if self.persistir:
            self._ajustes().setValue('ultima_carpeta', str(carpeta))

    def _recientes(self) -> list[str]:
        if self.persistir:
            valor = self._ajustes().value('recientes', [])
            lista = [valor] if isinstance(valor, str) else list(valor or [])
        else:
            lista = list(self._recientes_memoria)
        return [r for r in lista if Path(r).is_file()][:8]

    def _agregar_reciente(self, ruta: str) -> None:
        lista = [ruta] + [r for r in self._recientes() if r != ruta]
        lista = lista[:8]
        self._recientes_memoria = lista
        if self.persistir:
            self._ajustes().setValue('recientes', lista)
        self.bienvenida.establecer_recientes(lista)

    def _llenar_menu_recientes(self):
        self.menu_recientes.clear()
        recientes = self._recientes()
        if not recientes:
            a = self.menu_recientes.addAction('Sin sesiones recientes')
            a.setEnabled(False)
            return
        for ruta in recientes:
            p = Path(ruta)
            self.menu_recientes.addAction(iconos.icono('abrir'), f'{p.parent.name}  —  {p.parent.parent}',
                                          lambda r=ruta: self.abrir_sesion(r))

    def _restaurar_estado(self):
        s = self._ajustes()
        geometria = s.value('geometria')
        if geometria is not None:
            self.restoreGeometry(geometria)
        for nombre, divisor in (('divisor', self.divisor), ('divisor_centro', self.divisor_centro)):
            estado = s.value(nombre)
            if estado is not None:
                divisor.restoreState(estado)
        modo = s.value('apariencia', 'auto')
        if modo in ('auto', 'claro', 'oscuro') and modo != tema().modo:
            self.cambiar_apariencia(modo)
        self.bienvenida.establecer_recientes(self._recientes())

    def _guardar_estado(self):
        s = self._ajustes()
        s.setValue('geometria', self.saveGeometry())
        s.setValue('divisor', self.divisor.saveState())
        s.setValue('divisor_centro', self.divisor_centro.saveState())
        s.setValue('apariencia', tema().modo)

    def closeEvent(self, event):
        if self.trabajo and self.trabajo.isRunning():
            self.toast.mostrar('Espere a que termine la operación antes de cerrar.', 'aviso')
            event.ignore()
            return
        hilo = self._previa['hilo']
        if hilo is not None and hilo.isRunning():
            self._detener_vista_previa(restaurar=False)
            self.toast.mostrar('La vista previa está terminando. Cierre la ventana cuando finalice.', 'info')
            event.ignore()
            return
        if self.modificada and not self._puede_reemplazar():
            event.ignore()
            return
        self._detener_vista_previa(restaurar=False)
        if self.persistir:
            self._guardar_estado()
        event.accept()
