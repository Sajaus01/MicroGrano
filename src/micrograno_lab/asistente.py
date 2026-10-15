"""Interfaz guiada: una ruta explícita y una salida revisable por etapa."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import math

from PySide6.QtCore import Qt, QThread, Signal, QSettings
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSpinBox, QStackedWidget, QTableView, QVBoxLayout, QWidget,
)

from micrograno import Sesion
from micrograno.archivos import cargar_imagen, sha256_archivo
from micrograno.visualizacion import preparar_vista
from .componentes import BotonPrimario, etiqueta
from .consulta import DialogoBiblioteca, DialogoVersiones
from .dialogos import DialogoCarpetaNueva
from .recorrido import ETAPAS, Recorrido, exportar_recorrido
from .tema import asegurar_tema, tema
from .visores import ModeloTabla, VisorImagen


class Trabajo(QThread):
    """Una sola operación en curso; la interfaz bloquea toda mutación concurrente."""

    def __init__(self, funcion, parent=None):
        super().__init__(parent)
        self.funcion = funcion
        self.valor = None
        self.error = None

    def run(self):
        try:
            self.valor = self.funcion()
        except Exception as error:
            self.error = str(error) or type(error).__name__


class VentanaAsistente(QMainWindow):
    """La selección visual nunca gobierna las entradas del procesamiento."""

    trabajo_terminado = Signal()

    def __init__(self, persistir=False):
        super().__init__()
        asegurar_tema()
        self.persistir = persistir
        self.recorrido = Recorrido()
        self._trabajo = None
        self._modificado = False
        self._sucio = False
        self._recortar = False
        self._rectangulo = None
        self._linea_px = None
        self._linea_coordenadas = None
        self._ejemplo = False
        self._ruta_sesion = None
        self._id_mostrado = None
        self.setWindowTitle('MicroGrano Lab · Asistente guiado')
        self.resize(1250, 820)
        self.setMinimumSize(860, 620)
        self._construir()
        if persistir:
            geometria = QSettings().value('asistente/geometria')
            if geometria:
                self.restoreGeometry(geometria)
        self._presentar()

    @property
    def sesion(self):
        return self.recorrido.sesion

    @property
    def etapa(self):
        return ETAPAS[self.recorrido.actual]['id']

    def ventana_pequena(self):
        pantalla = self.screen()
        return bool(pantalla and pantalla.availableGeometry().height() < 850)

    def _construir(self):
        raiz = QWidget()
        self.setCentralWidget(raiz)
        vertical = QVBoxLayout(raiz)
        vertical.setContentsMargins(0, 0, 0, 0)
        vertical.setSpacing(0)
        cabecera = QWidget()
        cabecera.setObjectName('CabeceraAsistente')
        fila = QHBoxLayout(cabecera)
        fila.setContentsMargins(22, 12, 22, 12)
        fila.addWidget(etiqueta('MicroGrano', 'titulo'))
        fila.addWidget(etiqueta('Laboratorio guiado', 'secundario'))
        fila.addStretch()
        self.nuevo = QPushButton('Nuevo análisis')
        self.abrir = QPushButton('Abrir sesión')
        self.guardar = QPushButton('Guardar')
        self.versiones = QPushButton('Versiones')
        for boton in (self.nuevo, self.abrir, self.guardar, self.versiones):
            fila.addWidget(boton)
        self.nuevo.clicked.connect(lambda: self.importar())
        self.abrir.clicked.connect(lambda: self.abrir_sesion())
        self.guardar.clicked.connect(lambda: self.guardar_sesion())
        self.versiones.clicked.connect(self.consultar_versiones)
        vertical.addWidget(cabecera)

        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(0, 0, 0, 0)
        cuerpo.setSpacing(0)
        lateral = QFrame()
        lateral.setObjectName('BarraLateral')
        lateral.setFixedWidth(210)
        recorrido = QVBoxLayout(lateral)
        recorrido.setContentsMargins(16, 24, 16, 18)
        recorrido.setSpacing(8)
        recorrido.addWidget(etiqueta('TU RECORRIDO', 'seccion'))
        recorrido.addSpacing(8)
        self.indicadores = []
        for etapa in ETAPAS:
            paso = QLabel(etapa['titulo'])
            paso.setWordWrap(True)
            paso.setMinimumHeight(37)
            recorrido.addWidget(paso)
            self.indicadores.append(paso)
        recorrido.addStretch()
        recorrido.addWidget(etiqueta('Cada paso recibe el resultado\ndel paso anterior.', 'pie', envolver=True))
        cuerpo.addWidget(lateral)

        zona = QWidget()
        principal = QVBoxLayout(zona)
        principal.setContentsMargins(26, 20, 26, 16)
        principal.setSpacing(10)
        self.numero = etiqueta('', 'seccion')
        self.titulo = etiqueta('', 'titulo')
        self.descripcion = etiqueta('', 'secundario', envolver=True)
        principal.addWidget(self.numero)
        principal.addWidget(self.titulo)
        principal.addWidget(self.descripcion)

        contenido = QHBoxLayout()
        contenido.setSpacing(18)
        imagen = QVBoxLayout()
        imagen.setSpacing(8)
        self.fuente = etiqueta('', 'pie', envolver=True)
        self.nombre_vista = etiqueta('', 'seccion', envolver=True)
        imagen.addWidget(self.fuente)
        imagen.addWidget(self.nombre_vista)
        self.vistas = QStackedWidget()
        self.visor = VisorImagen()
        self.visor.setMinimumSize(280, 240)
        self.visor.roi_elegida.connect(self._elegir_roi)
        self.visor.linea_elegida.connect(self._elegir_linea)
        self.lienzos = QWidget()
        lienzos = QHBoxLayout(self.lienzos)
        lienzos.setContentsMargins(0, 0, 0, 0)
        lienzos.setSpacing(8)
        lienzos.addWidget(self.visor, 1)
        self.referencia = VisorImagen()
        self.referencia.setVisible(False)
        lienzos.addWidget(self.referencia, 1)
        self.vistas.addWidget(self.lienzos)
        self.tabla = QTableView()
        self.tabla.setAlternatingRowColors(True)
        self.vistas.addWidget(self.tabla)
        imagen.addWidget(self.vistas, 1)
        self.comparar = QCheckBox('Comparar el resultado con la ROI')
        self.comparar.toggled.connect(self._comparar_roi)
        imagen.addWidget(self.comparar)
        self.pie_vista = etiqueta('Rueda: ampliar · Doble clic: ajustar', 'pie')
        imagen.addWidget(self.pie_vista)
        contenido.addLayout(imagen, 1)

        self.panel = QScrollArea()
        self.panel.setWidgetResizable(True)
        self.panel.setFrameShape(QFrame.Shape.NoFrame)
        self.panel.setFixedWidth(280)
        contenido.addWidget(self.panel)
        principal.addLayout(contenido, 1)
        self.mensaje = etiqueta('', 'secundario', envolver=True, seleccionable=True)
        self.mensaje.setVisible(False)
        principal.addWidget(self.mensaje)
        navegacion = QHBoxLayout()
        self.anterior = QPushButton('Anterior')
        self.anterior.clicked.connect(self.retroceder)
        navegacion.addWidget(self.anterior)
        navegacion.addStretch()
        self.continuar = BotonPrimario('Continuar')
        self.continuar.clicked.connect(self._accion_principal)
        navegacion.addWidget(self.continuar)
        principal.addLayout(navegacion)
        cuerpo.addWidget(zona, 1)
        vertical.addLayout(cuerpo, 1)

    def _aviso(self, texto, error=False):
        self.mensaje.setText(texto)
        self.mensaje.setStyleSheet('color: #bd3e35;' if error else '')
        self.mensaje.setVisible(bool(texto))

    def _boton_principal(self, texto, habilitado=True):
        self.continuar._texto = texto
        self.continuar.setText(texto)
        self.continuar.setEnabled(habilitado and self._trabajo is None)

    def _texto(self, texto, rol='secundario'):
        self.controles.addWidget(etiqueta(texto, rol, envolver=True))

    def _boton(self, texto, accion):
        boton = QPushButton(texto)
        boton.clicked.connect(accion)
        self.controles.addWidget(boton)
        return boton

    def _presentar(self):
        etapa = ETAPAS[self.recorrido.actual]
        self.numero.setText(f'PASO {self.recorrido.actual + 1} DE {len(ETAPAS)}')
        self.titulo.setText(etapa['titulo'])
        self.descripcion.setText(etapa['descripcion'])
        self._aviso('')
        t = tema()
        for i, indicador in enumerate(self.indicadores):
            completo = self.recorrido.completada(i)
            indicador.setText(f'{"✓" if completo else str(i + 1).zfill(2)}   {ETAPAS[i]["titulo"]}')
            activo = i == self.recorrido.actual
            indicador.setStyleSheet(
                f'padding: 7px; border-radius: 7px; '
                f'font-weight: {600 if activo else 400}; '
                + (f'background: {t.color("acento").name()}; color: white;' if activo else ''))
        anterior = self.panel.takeWidget()
        if anterior:
            anterior.deleteLater()
        contenedor = QWidget()
        self.controles = QVBoxLayout(contenedor)
        self.controles.setContentsMargins(0, 2, 2, 2)
        self.controles.setSpacing(12)
        self.panel.setWidget(contenedor)
        self.anterior.setEnabled(self.recorrido.actual > 0)
        hay_imagen = bool(self.recorrido.original_id)
        self.guardar.setEnabled(hay_imagen)
        self.versiones.setEnabled(bool(self.sesion.artefactos))
        self.nuevo.setVisible(hay_imagen)
        self.comparar.blockSignals(True)
        self.comparar.setChecked(False)
        self.comparar.blockSignals(False)
        self.comparar.setVisible(self.etapa in ('segmentar', 'limpiar', 'etiquetar', 'medir'))
        self.referencia.hide()
        self._mostrar_imagen()
        getattr(self, f'_panel_{self.etapa}')()
        self.controles.addStretch()
        if etapa['operacion']:
            estado = self.recorrido.estado()
            operacion = estado.operacion if estado and estado.operacion else etapa['operacion']
            self._texto('FUNCIÓN UTILIZADA' if estado and estado.operacion else 'FUNCIÓN DE ESTE PASO', 'seccion')
            if estado and estado.omitida:
                self._texto('No se ejecutó esta función: se conservó la entrada del paso anterior.', 'pie')
            self._texto(f'micrograno.{operacion}(...)', 'pie')
            self._boton('Qué hace y cómo se usa', lambda: DialogoBiblioteca(self, operacion).exec())
        self._actualizar_accion()

    def _nombre_salida(self, indice):
        id_ = ETAPAS[indice]['id']
        estado = self.recorrido.estado(indice)
        if id_ == 'escala':
            return 'Original con escala' if estado and not estado.omitida else 'Imagen original'
        if id_ == 'preparar':
            return 'ROI conservada' if estado and estado.omitida else 'ROI filtrada'
        if id_ == 'segmentar':
            return 'Máscara binaria · Otsu'
        if id_ == 'limpiar':
            return 'Máscara revisada'
        if id_ == 'etiquetar':
            return 'Objetos identificados'
        if id_ in ('medir', 'exportar'):
            return 'Objetos del análisis'
        return ETAPAS[indice]['titulo']

    def _mostrar_imagen(self, entrada=False):
        estado = self.recorrido.estado()
        i = self.recorrido.actual
        entrada = entrada or self._recortar or self._sucio
        id_ = self.recorrido.entrada() if entrada or estado is None else estado.salida_id
        self._id_mostrado = id_
        self.vistas.setCurrentWidget(self.lienzos)
        self.pie_vista.setText('Rueda: ampliar · Doble clic: ajustar')
        if id_ is None:
            self.fuente.setText('Una imagen · Un recorrido · Todas las versiones conservadas')
            self.nombre_vista.setText('')
            self.visor.limpiar('De la micrografía a las medidas',
                               'Abra una imagen metalográfica o pruebe el ejemplo para aprender el recorrido.')
            return
        artefacto = self.sesion.artefactos[id_]
        nombre = self._nombre_salida(max(0, i - 1) if entrada or estado is None else i)
        alto, ancho = artefacto.datos.shape[:2]
        self.nombre_vista.setText(f'{nombre} · {ancho} × {alto} px')
        if i:
            self.fuente.setText(f'Entrada fijada por el paso {i}: {self._nombre_salida(i - 1)}')
        else:
            self.fuente.setText(f'Original conservado: {artefacto.nombre}')
        self.visor.mostrar(preparar_vista(artefacto, self.sesion, superponer=False, rotular=False),
                           nombre, artefacto.datos, artefacto.tipo)
        herramienta = 'roi' if self.etapa == 'roi' and (not estado or self._recortar) else 'mover'
        if self.etapa == 'escala':
            herramienta = 'linea'
        self.visor.establecer_herramienta(herramienta)
        if self.etapa == 'escala' and self._linea_coordenadas:
            self.visor.mostrar_linea(*self._linea_coordenadas)

    def _comparar_roi(self, mostrar):
        self.referencia.setVisible(mostrar)
        if mostrar:
            self._mostrar_imagen()
            roi = self.sesion.artefactos[self.recorrido.salida('roi')]
            self.referencia.mostrar(preparar_vista(roi, self.sesion), 'ROI · referencia', roi.datos, roi.tipo)
            self.referencia.establecer_herramienta('mover')
            self.vistas.setCurrentWidget(self.lienzos)
            self.pie_vista.setText('Izquierda: resultado · Derecha: ROI de referencia')
        else:
            self.pie_vista.setText('Rueda: ampliar · Doble clic: ajustar')

    def _panel_imagen(self):
        if self.recorrido.original_id:
            self._texto('El original está guardado. Cada transformación creará su propia versión.')
            self._texto('Continúe para definir la escala antes de recortar la imagen.')
        else:
            self._texto('APRENDE CON UNA IMAGEN', 'seccion')
            self._texto('El asistente conecta los pasos y conserva sus resultados. Solo tendrá que revisar la imagen en cada etapa.')
            self._boton('Probar con una imagen de ejemplo', self.cargar_ejemplo)
            self._texto('El ejemplo es sintético; sirve para conocer el proceso.', 'pie')

    def _panel_escala(self):
        self._texto('1. Dibuje una línea sobre una longitud conocida de la imagen.\n2. Indique cuánto representa en micrómetros.')
        estado = self.recorrido.estado()
        p = estado.parametros if estado else {}
        self._linea_px = p.get('referencia_px')
        if estado and not estado.omitida:
            meta = self.sesion.artefactos[self.recorrido.original_id].metadatos
            self._linea_coordenadas = meta.get('calibracion_documentacion', {}).get('linea_rc')
            if self._linea_coordenadas:
                self.visor.mostrar_linea(*self._linea_coordenadas)
        self.longitud_px = etiqueta('', 'pie', envolver=True)
        self.controles.addWidget(self.longitud_px)
        self._actualizar_longitud()
        self.longitud_um = QDoubleSpinBox()
        self.longitud_um.setRange(0, 1e9)
        self.longitud_um.setDecimals(4)
        self.longitud_um.setSuffix(' µm')
        self.longitud_um.setValue(p.get('referencia_um', 0))
        self.longitud_um.setAccessibleName('Longitud conocida en micrómetros')
        self.controles.addWidget(self.longitud_um)
        self.longitud_um.valueChanged.connect(self._cambio)
        self._boton('Continuar sin escala', self._omitir_escala)
        if self._ejemplo:
            self._boton('Usar escala del ejemplo', self._escala_ejemplo)
            self._texto('Convención del ejemplo: 100 px = 50 µm. No es una calibración experimental.', 'pie')
        self._texto('Sin una referencia conocida podrá segmentar y exportar, pero se omitirá el cálculo de medidas físicas.', 'pie')

    def _panel_grises(self):
        self._texto('QUÉ CAMBIA', 'seccion')
        self._texto('La función convierte el color en una intensidad entre 0 y 1. El tamaño de la imagen se mantiene.')
        self._texto('Esta versión será la entrada del recorte. El original permanece en Versiones.')

    def _panel_roi(self):
        estado = self.recorrido.estado()
        if not estado or self._recortar:
            self._texto('Dibuje un rectángulo sobre la microestructura que desea analizar. Deje fuera la barra de escala, textos y bordes ajenos a la muestra.')
            self._boton('Usar toda la imagen', self._roi_completa)
            self.roi_detalle = etiqueta('Arrastre sobre la imagen para seleccionar la región.', 'pie', envolver=True)
            self.controles.addWidget(self.roi_detalle)
        else:
            self._texto('REVISE EL RECORTE', 'seccion')
            self._texto('Esta es la región que se utilizará en todos los pasos siguientes. La escala espacial se conserva.')
            self.confirmacion_roi = QCheckBox('El recorte contiene solo la región de análisis, sin barra de escala ni anotaciones.')
            self.confirmacion_roi.setStyleSheet('QCheckBox { spacing: 8px; }')
            # QLabel permite envolver la explicación sin truncar el control.
            self.confirmacion_roi.setText('Confirmo la región de análisis')
            self.confirmacion_roi.setChecked(estado.confirmada)
            self.confirmacion_roi.toggled.connect(lambda: self._actualizar_accion())
            self.controles.addWidget(self.confirmacion_roi)
            self._texto('Al confirmar declara que la ROI excluye barra de escala y anotaciones.', 'pie')
            self._boton('Volver a dibujar el recorte', self._redibujar_roi)

    def _panel_preparar(self):
        estado = self.recorrido.estado()
        self.filtrar = QCheckBox('Reducir ruido con mediana')
        self.filtrar.setChecked(bool(estado and not estado.omitida))
        self.filtrar.toggled.connect(self._cambio)
        self.controles.addWidget(self.filtrar)
        self._texto('Por defecto se conserva la ROI. Si activa el filtro, se usará la mediana con radio de 1 píxel.')
        self._texto('Revise los detalles finos: el filtrado puede eliminarlos junto con el ruido.', 'pie')

    def _panel_segmentar(self):
        self._texto('¿QUÉ DEBE QUEDAR EN BLANCO?', 'seccion')
        self.polaridad = QComboBox()
        self.polaridad.addItem('Las regiones claras', 'clara')
        self.polaridad.addItem('Las regiones oscuras', 'oscura')
        estado = self.recorrido.estado()
        self.polaridad.setCurrentIndex(1 if estado and estado.parametros.get('polaridad') == 'oscura' else 0)
        self.polaridad.currentIndexChanged.connect(self._cambio)
        self.controles.addWidget(self.polaridad)
        self._texto('Otsu calcula un umbral a partir de las intensidades de la ROI. Blanco indica primer plano; negro, fondo.')
        resultado = self.recorrido.resultado()
        if resultado:
            self._texto(f'Umbral calculado: {resultado.resumen["umbral_otsu"]:.4f} (intensidad de 0 a 1).', 'pie')
        self._texto('Compruebe que el blanco representa lo que desea medir. Una máscara no identifica por sí sola los granos ni las fases.', 'pie')

    def _panel_limpiar(self):
        self._texto('La máscara se conserva inicialmente. Si necesita corregirla, despliegue los ajustes y revise el resultado.')
        self.ajustes = QCheckBox('Ajustar limpieza de la máscara')
        self.controles.addWidget(self.ajustes)
        grupo = QWidget()
        formulario = QFormLayout(grupo)
        formulario.setContentsMargins(0, 0, 0, 0)
        formulario.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        estado = self.recorrido.estado()
        p = estado.parametros if estado else {}
        self.area_minima = QSpinBox()
        self.area_minima.setRange(1, 100000000)
        self.area_minima.setValue(p.get('area_minima', 1))
        self.hueco_maximo = QSpinBox()
        self.hueco_maximo.setRange(0, 100000000)
        self.hueco_maximo.setValue(p.get('hueco_maximo', 0))
        formulario.addRow('Conservar objetos desde (px²)', self.area_minima)
        formulario.addRow('Rellenar huecos hasta (px²)', self.hueco_maximo)
        self.controles.addWidget(grupo)
        cambiado = self.area_minima.value() != 1 or self.hueco_maximo.value() != 0
        self.ajustes.setChecked(cambiado)
        grupo.setVisible(cambiado)
        self.ajustes.toggled.connect(grupo.setVisible)
        self.area_minima.valueChanged.connect(self._cambio)
        self.hueco_maximo.valueChanged.connect(self._cambio)
        self._texto('El siguiente paso recibe únicamente la máscara limpia. Las máscaras de objetos retirados y píxeles agregados se conservan para consulta.', 'pie')
        resultado = self.recorrido.resultado()
        if resultado:
            self._texto(f'{resultado.resumen["pixeles_eliminados"]} píxeles retirados · '
                        f'{resultado.resumen["pixeles_agregados"]} píxeles agregados.', 'pie')

    def _panel_etiquetar(self):
        estado = self.recorrido.estado()
        self.watershed = QCheckBox('Separar objetos que se tocan')
        self.watershed.setChecked(bool(estado and estado.operacion == 'separar_watershed'))
        self.watershed.toggled.connect(self._cambio)
        self.controles.addWidget(self.watershed)
        self._texto('Cada región conectada recibe un identificador y un color. Se usa conectividad de 8 vecinos.')
        self._texto('La separación opcional usa watershed y puede dividir un objeto en exceso. Revise los colores antes de medir.', 'pie')
        if estado and estado.operacion == 'separar_watershed':
            self._texto('Separación mínima de picos: 12 px. Se conservan los componentes desde 1 px².', 'pie')
        resultado = self.recorrido.resultado()
        if resultado and 'numero_objetos' in resultado.resumen:
            self._texto(f'{resultado.resumen["numero_objetos"]} objetos identificados.', 'pie')

    def _panel_medir(self):
        entrada = self.recorrido.entrada()
        escala = self.sesion.artefactos[entrada].metadatos.get('escala')
        estado = self.recorrido.estado()
        if not escala:
            self._texto('SIN ESCALA ESPACIAL', 'seccion')
            self._texto('No se calcularán medidas físicas. Se conservarán las imágenes, máscaras y etiquetas para exportarlas.')
            self._texto('Puede volver al paso Escala con Anterior. Al calibrar, los pasos posteriores se volverán a calcular.', 'pie')
        elif estado:
            resultado = self.recorrido.resultado()
            tabla = resultado.tabla if resultado is not None else None
            self._texto(f'Escala utilizada: {escala["um_por_px"]:g} µm/px.')
            self._texto('Se conservan todos los objetos de al menos un píxel, incluidos los que tocan el marco. La tabla indica cuáles tocan el borde.')
            if tabla is not None:
                self._texto(f'{len(tabla)} objetos en la tabla. Se exportan todas las columnas.', 'pie')
                self.mostrar_tabla = QCheckBox('Mostrar tabla de medidas')
                self.mostrar_tabla.toggled.connect(lambda activa: self._ver_tabla() if activa else self._mostrar_imagen())
                self.controles.addWidget(self.mostrar_tabla)

    def _panel_exportar(self):
        self._texto('ANÁLISIS CONSERVADO', 'seccion')
        self._texto(f'{len(self.sesion.artefactos)} versiones disponibles, incluidas las salidas auxiliares y los cálculos anteriores.')
        self._texto('La exportación reúne imágenes, máscaras, etiquetas, tablas y la sesión que permite reabrir este recorrido.')
        self._texto('Los archivos NPY conservan los valores exactos. Los PNG son vistas para consultar. El índice documenta de dónde viene cada versión y cuál sigue vigente.', 'pie')
        medida = self.recorrido.estado('medir')
        if medida and medida.omitida:
            self._texto('Este análisis no incluye medidas físicas porque se continuó sin escala.', 'pie')

    def _actualizar_accion(self):
        estado = self.recorrido.estado()
        if self.etapa == 'imagen' and not estado:
            self._boton_principal('Abrir imagen')
        elif self.etapa == 'escala' and (not estado or self._sucio):
            valido = bool(self._linea_px and self.longitud_um.value() > 0)
            self._boton_principal('Calibrar y continuar', valido)
        elif self.etapa == 'roi':
            if not estado or self._recortar:
                self._boton_principal('Crear y revisar ROI', self._rectangulo is not None)
            else:
                self._boton_principal('Confirmar ROI y continuar', self.confirmacion_roi.isChecked())
        elif self.etapa == 'medir' and not estado:
            escala = self.sesion.artefactos[self.recorrido.entrada()].metadatos.get('escala')
            self._boton_principal('Calcular medidas' if escala else 'Continuar sin medidas físicas')
        elif self.etapa == 'exportar':
            self._boton_principal('Exportar análisis completo')
        elif self._sucio or (not estado and self.etapa != 'imagen'):
            self._boton_principal('Actualizar resultado' if estado else 'Calcular este paso')
        else:
            siguiente = ETAPAS[min(self.recorrido.actual + 1, len(ETAPAS) - 1)]['titulo']
            self._boton_principal(f'Continuar · {siguiente}')

    def _cambio(self, *_):
        self._sucio = True
        self._mostrar_imagen(entrada=True)
        self._aviso('Aplique el cambio para revisar el nuevo resultado. Las versiones anteriores se conservarán.')
        self._actualizar_accion()

    def _actualizar_longitud(self):
        self.longitud_px.setText(f'Línea medida: {self._linea_px:.2f} px' if self._linea_px else 'Todavía no ha dibujado la referencia.')

    def _elegir_linea(self, r0, c0, r1, c1):
        if self.etapa != 'escala' or self._trabajo:
            return
        self._linea_px = math.hypot(r1 - r0, c1 - c0)
        self._linea_coordenadas = (r0, c0, r1, c1)
        self._sucio = True
        self._actualizar_longitud()
        self._actualizar_accion()

    def _elegir_roi(self, r0, r1, c0, c1):
        if self.etapa != 'roi' or self._trabajo or (self.recorrido.estado() and not self._recortar):
            return
        self._rectangulo = dict(r0=r0, r1=r1, c0=c0, c1=c1)
        self.roi_detalle.setText(f'Región seleccionada: {c1 - c0} × {r1 - r0} px. Cree el recorte para revisarlo.')
        self._actualizar_accion()

    def _roi_completa(self):
        alto, ancho = self.sesion.artefactos[self.recorrido.entrada()].datos.shape[:2]
        self._elegir_roi(0, alto, 0, ancho)
        self._calcular()

    def _redibujar_roi(self):
        self._recortar = True
        self._rectangulo = None
        self._presentar()

    def _omitir_escala(self):
        self._iniciar(lambda: self.recorrido.ejecutar('escala', opcion='omitir',
                    nota='Sin referencia espacial conocida.'), self._avanzar)

    def _escala_ejemplo(self):
        self._iniciar(lambda: self.recorrido.ejecutar('escala', dict(
            referencia_um=50.0, referencia_px=100.0, referencia='Convención sintética: 0.5 µm/px.')),
            self._avanzar)

    def _accion_principal(self):
        if self._trabajo:
            return
        if self.etapa == 'imagen' and not self.recorrido.original_id:
            self.importar()
        elif self.etapa == 'exportar':
            self.exportar()
        elif self.etapa == 'roi' and self.recorrido.estado() and not self._recortar:
            if self.confirmacion_roi.isChecked():
                self.recorrido.confirmar_roi('ROI revisada: excluye barra de escala y anotaciones.')
                self._modificado = True
                self._avanzar()
        elif self._sucio or not self.recorrido.completada() or self._recortar:
            self._calcular()
        else:
            self._avanzar()

    def _calcular(self):
        if self._trabajo:
            return
        etapa = self.etapa
        parametros, opcion = {}, None
        documentacion = None
        if etapa == 'escala':
            if not self._linea_px or self.longitud_um.value() <= 0:
                self._aviso('Dibuje una referencia e indique su longitud real.', True)
                return
            parametros = dict(referencia_um=self.longitud_um.value(), referencia_px=self._linea_px,
                              referencia='Referencia dibujada en la imagen original.')
            if self._linea_coordenadas:
                documentacion = {'linea_rc': list(self._linea_coordenadas)}
        elif etapa == 'roi':
            if self._rectangulo is None:
                return
            parametros = dict(self._rectangulo)
        elif etapa == 'preparar':
            opcion = 'mediana' if self.filtrar.isChecked() else 'conservar'
            if opcion == 'mediana':
                parametros = dict(radio_px=1)
        elif etapa == 'segmentar':
            opcion = 'otsu'
            parametros = dict(polaridad=self.polaridad.currentData())
        elif etapa == 'limpiar':
            parametros = dict(area_minima=self.area_minima.value(), hueco_maximo=self.hueco_maximo.value())
        elif etapa == 'etiquetar':
            opcion = 'watershed' if self.watershed.isChecked() else 'componentes'
        elif etapa == 'medir':
            if not self.sesion.artefactos[self.recorrido.entrada()].metadatos.get('escala'):
                opcion = 'omitir'
        despues = self._avanzar if etapa == 'escala' or (etapa == 'medir' and opcion == 'omitir') else self._presentar
        self._iniciar(lambda: self.recorrido.ejecutar(etapa, parametros, opcion=opcion,
                     nota='Sin escala espacial: no se calcularon medidas físicas.' if opcion == 'omitir' else '',
                     documentacion=documentacion), despues)

    def _iniciar(self, funcion, despues, *, modifica=True):
        if self._trabajo:
            return
        trabajo = Trabajo(funcion, self)
        self._trabajo = trabajo
        for widget in (self.nuevo, self.abrir, self.guardar, self.versiones, self.anterior, self.panel, self.visor):
            widget.setEnabled(False)
        self.continuar.ocupado(True, 'Procesando…')
        self.continuar.setEnabled(False)
        self.comparar.setEnabled(False)
        self._aviso('Procesando el resultado de este paso…')

        def terminado():
            self._trabajo = None
            for widget in (self.nuevo, self.abrir, self.guardar, self.versiones, self.anterior, self.panel, self.visor):
                widget.setEnabled(True)
            self.continuar.ocupado(False)
            self.comparar.setEnabled(True)
            if trabajo.error:
                self._actualizar_accion()
                self._aviso(f'No se pudo completar este paso. {trabajo.error}', True)
            else:
                self._sucio = False
                self._recortar = False
                self._modificado = self._modificado or modifica
                despues()
            trabajo.deleteLater()
            self.trabajo_terminado.emit()

        trabajo.finished.connect(terminado)
        trabajo.start()

    def _avanzar(self):
        self.recorrido.avanzar()
        self._modificado = True
        self._entrar()

    def retroceder(self):
        if self._trabajo:
            return
        self.recorrido.retroceder()
        self._modificado = True
        self._entrar()

    def _entrar(self):
        self._sucio = self._recortar = False
        self._rectangulo = None
        self._linea_coordenadas = None
        self._presentar()
        if self.recorrido.estado() is not None:
            return
        if self.etapa in ('grises', 'preparar', 'segmentar', 'limpiar', 'etiquetar'):
            self._calcular()
        elif self.etapa == 'medir':
            escala = self.sesion.artefactos[self.recorrido.entrada()].metadatos.get('escala')
            if escala:
                self._calcular()

    def _ver_tabla(self):
        resultado = self.recorrido.resultado('medir')
        if resultado is None or resultado.tabla is None:
            return
        self.modelo_tabla = ModeloTabla(resultado.tabla, self)
        self.comparar.setChecked(False)
        self.tabla.setModel(self.modelo_tabla)
        self.tabla.resizeColumnsToContents()
        self.vistas.setCurrentWidget(self.tabla)
        self.nombre_vista.setText('Medidas de los objetos · tabla completa')
        self.pie_vista.setText('Desplace la tabla horizontalmente para consultar todas las columnas.')

    def consultar_versiones(self):
        if self._trabajo:
            return
        principales = {}
        for i, etapa in enumerate(ETAPAS):
            salida = self.recorrido.salida(i)
            if salida:
                principales.setdefault(salida, etapa['titulo'])
        DialogoVersiones(self, self.sesion, principales).exec()

    def _permitir_reemplazo(self):
        if self._trabajo:
            return False
        if not self._modificado:
            return True
        respuesta = QMessageBox.question(self, 'Guardar el análisis',
            'Hay cambios sin guardar. ¿Desea guardar la sesión antes de continuar?',
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save)
        if respuesta == QMessageBox.StandardButton.Save:
            return self.guardar_sesion()
        return respuesta == QMessageBox.StandardButton.Discard

    def importar(self, tipo='imagen', ruta=None):
        if self._trabajo:
            return
        if tipo != 'imagen':
            self._aviso('El recorrido comienza con una imagen metalográfica. Las máscaras se generan dentro del análisis.', True)
            return
        if not ruta:
            ruta, _ = QFileDialog.getOpenFileName(self, 'Abrir micrografía', '',
                'Imágenes (*.tif *.tiff *.png *.jpg *.jpeg *.bmp);;Todos los archivos (*)')
        if not ruta or not self._permitir_reemplazo():
            return
        try:
            datos = cargar_imagen(ruta)
            nueva = Recorrido()
            id_ = nueva.sesion.agregar(datos, 'imagen', Path(ruta).name,
                                       {'ruta': str(Path(ruta).resolve()), 'sha256': sha256_archivo(ruta)})
            nueva.usar_original(id_)
        except Exception as error:
            self._aviso(f'No se pudo abrir la imagen. {error}', True)
            return
        self._reemplazar(nueva)

    def cargar_ejemplo(self):
        if not self._permitir_reemplazo():
            return
        from micrograno.sinteticos import crear_conjunto
        nueva = Recorrido()
        id_ = nueva.sesion.agregar(crear_conjunto()['rgb'], 'imagen', 'Microestructura sintética',
                                   {'ejemplo_guiado': True})
        nueva.usar_original(id_)
        self._reemplazar(nueva)

    def _reemplazar(self, recorrido, ruta=None):
        self.recorrido = recorrido
        self._ruta_sesion = ruta
        self._modificado = ruta is None
        self._ejemplo = bool(recorrido.original_id and self.sesion.artefactos[recorrido.original_id].metadatos.get('ejemplo_guiado'))
        self._entrar()

    def _elegir_carpeta(self, titulo, nombre, boton):
        dialogo = DialogoCarpetaNueva(self, titulo,
            'Se creará una carpeta nueva para conservar el análisis completo.',
            nombre, str(Path.home() / 'Documents'), boton=boton)
        return dialogo.ruta() if dialogo.exec() else None

    def guardar_sesion(self, ruta=None):
        if self._trabajo or not self.recorrido.original_id:
            return False
        if ruta is None:
            ruta = self._elegir_carpeta('Guardar sesión', 'MicroGrano_' + datetime.now().strftime('%Y%m%d_%H%M%S'), 'Guardar')
        if not ruta:
            return False
        try:
            self.recorrido.guardar(ruta)
        except Exception as error:
            self._aviso(f'No se pudo guardar la sesión. {error}', True)
            return False
        self._ruta_sesion = Path(ruta)
        self._modificado = False
        self._aviso(f'Sesión guardada en {ruta}')
        return True

    def abrir_sesion(self, ruta=None):
        if self._trabajo:
            return
        if not ruta:
            ruta, _ = QFileDialog.getOpenFileName(self, 'Abrir sesión', '', 'Sesión de MicroGrano (sesion.json)')
        if not ruta or not self._permitir_reemplazo():
            return
        try:
            nueva = Recorrido.abrir(ruta)
        except Exception as error:
            # Las sesiones anteriores no contienen una ruta inequívoca. Se consultan
            # sin adivinar qué versión debía alimentar al siguiente paso.
            carpeta = Path(ruta) if Path(ruta).is_dir() else Path(ruta).parent
            if not (carpeta / 'recorrido.json').exists() and (carpeta / 'sesion.json').exists():
                try:
                    anterior = Sesion.abrir(carpeta)
                    DialogoVersiones(self, anterior).exec()
                    self._aviso('Sesión anterior consultada. Para el asistente, inicie un análisis con su imagen original.')
                    return
                except Exception:
                    pass
            self._aviso(f'No se pudo abrir el recorrido. {error}', True)
            return
        self._reemplazar(nueva, Path(ruta))

    def exportar(self, ruta=None):
        if self._trabajo:
            return
        if ruta is None:
            ruta = self._elegir_carpeta('Exportar análisis completo', 'MicroGrano_resultados_' + datetime.now().strftime('%Y%m%d_%H%M%S'), 'Exportar')
        if not ruta:
            return

        def terminado():
            self._modificado = False
            self._presentar()
            self._aviso(f'Análisis exportado en {ruta}. La carpeta sesion_reabrible permite retomar este recorrido.')

        self._iniciar(lambda: exportar_recorrido(self.recorrido, ruta), terminado, modifica=False)

    def closeEvent(self, evento):
        if self._trabajo:
            self._aviso('Espere a que termine el procesamiento antes de cerrar.')
            evento.ignore()
            return
        if not self._permitir_reemplazo():
            evento.ignore()
            return
        if self.persistir:
            QSettings().setValue('asistente/geometria', self.saveGeometry())
        evento.accept()
