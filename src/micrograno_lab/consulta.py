"""Consulta de versiones y biblioteca sin cambiar el recorrido del análisis."""
from __future__ import annotations

import html
import inspect

import numpy as np
import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPlainTextEdit, QSplitter, QStackedWidget, QTableView,
    QTextBrowser, QVBoxLayout, QWidget,
)

from micrograno.catalogo import AYUDA_PARAMETROS, CATALOGO
from micrograno.visualizacion import preparar_vista
from .componentes import ResaltadorPython, etiqueta
from .dialogos import DialogoBase
from .flujo import explicacion_entradas, nombre_version, origen_version
from .tema import asegurar_tema, fuente_codigo
from .textos import OPERACIONES, meta_parametro, nombre_tipo
from .visores import ModeloTabla, VisorImagen


class DialogoVersiones(DialogoBase):
    """Galería de todos los artefactos; seleccionar solo cambia esta vista."""

    def __init__(self, parent, sesion, principales: dict[str, str] | None = None):
        asegurar_tema()
        super().__init__(parent, 'Versiones conservadas',
                         'Consulta; no cambia el análisis. Todas estas versiones se incluyen al exportar.',
                         icono='capas', ancho=760)
        self.resize(1050, 730)
        self.sesion = sesion
        self.principales = dict(principales or {})
        self.id_consultado = None

        division = QSplitter(Qt.Orientation.Horizontal)
        self.lista = QListWidget()
        self.lista.setMinimumWidth(240)
        self.lista.setWordWrap(True)
        self.lista.setAccessibleName('Versiones disponibles para consultar')
        division.addWidget(self.lista)

        detalle = QWidget()
        capa = QVBoxLayout(detalle)
        capa.setContentsMargins(12, 0, 0, 0)
        capa.setSpacing(8)
        self.titulo_version = etiqueta('', 'titulo', envolver=True)
        self.detalle_version = etiqueta('', 'secundario', envolver=True, seleccionable=True)
        self.origen = etiqueta('', 'pie', envolver=True, seleccionable=True)
        capa.addWidget(self.titulo_version)
        capa.addWidget(self.detalle_version)
        capa.addWidget(self.origen)
        self.contenido = QStackedWidget()
        self.visor = VisorImagen()
        self.visor.setAccessibleName('Vista de la versión consultada')
        self.tabla = QTableView()
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setAccessibleName('Valores de la versión consultada')
        self.contenido.addWidget(self.visor)
        self.contenido.addWidget(self.tabla)
        capa.addWidget(self.contenido, 1)
        capa.addWidget(etiqueta('Rueda: ampliar o reducir. Doble clic: ajustar la imagen.', 'pie'))
        division.addWidget(detalle)
        division.setStretchFactor(1, 1)
        division.setSizes([280, 700])
        self.cuerpo.addWidget(division, 1)
        self.agregar_botones('Cerrar', cancelar=None)

        for id_, artefacto in sesion.artefactos.items():
            texto = nombre_version(sesion, id_)
            if id_ in self.principales:
                texto += f'\nPaso: {self.principales[id_]}'
            item = QListWidgetItem(texto)
            item.setData(Qt.ItemDataRole.UserRole, id_)
            item.setToolTip(f'{artefacto.nombre}\n{origen_version(sesion, id_)}')
            self.lista.addItem(item)
        self.lista.currentRowChanged.connect(self._mostrar_version)
        if self.lista.count():
            self.lista.setCurrentRow(0)
        else:
            self.titulo_version.setText('Todavía no hay versiones')
            self.visor.limpiar('Sin imágenes', 'Abra una imagen para iniciar el recorrido.')

    def _mostrar_version(self, fila: int) -> None:
        item = self.lista.item(fila)
        if item is None:
            return
        id_ = item.data(Qt.ItemDataRole.UserRole)
        artefacto = self.sesion.artefactos[id_]
        self.id_consultado = id_
        titulo = nombre_version(self.sesion, id_)
        etapa = self.principales.get(id_)
        self.titulo_version.setText(titulo + (f' · {etapa}' if etapa else ''))
        datos = artefacto.datos
        if datos.ndim >= 2:
            dimensiones = f'{datos.shape[1]} × {datos.shape[0]} px'
            if datos.ndim == 3:
                dimensiones += f' · {datos.shape[2]} canales'
        else:
            dimensiones = f'{datos.size} valores'
        self.detalle_version.setText(
            f'{artefacto.nombre}\n{nombre_tipo(artefacto.tipo)} · {dimensiones} · {datos.dtype}')
        self.origen.setText(origen_version(self.sesion, id_))
        if datos.ndim >= 2:
            vista = preparar_vista(artefacto, self.sesion, superponer=False, rotular=False)
            self.visor.mostrar(vista, titulo, datos, artefacto.tipo)
            self.visor.establecer_herramienta('mover')
            self.contenido.setCurrentWidget(self.visor)
        else:
            self.modelo = ModeloTabla(pd.DataFrame({'valor': np.asarray(datos).reshape(-1)}), self)
            self.tabla.setModel(self.modelo)
            self.tabla.horizontalHeader().setStretchLastSection(True)
            self.contenido.setCurrentWidget(self.tabla)


class DialogoBiblioteca(DialogoBase):
    """Documentación y código de la API; no contiene acciones de procesamiento."""

    def __init__(self, parent, operacion: str | None = None):
        asegurar_tema()
        super().__init__(parent, 'Biblioteca MicroGrano',
                         'Consulta cómo recibe los datos cada función y qué calcula. El análisis permanece en su paso actual.',
                         icono='info', ancho=800)
        self.resize(1100, 780)
        self.operacion = None
        division = QSplitter(Qt.Orientation.Horizontal)
        self.lista = QListWidget()
        self.lista.setMinimumWidth(250)
        self.lista.setWordWrap(True)
        self.lista.setAccessibleName('Funciones de la biblioteca')
        division.addWidget(self.lista)

        detalle = QWidget()
        capa = QVBoxLayout(detalle)
        capa.setContentsMargins(12, 0, 0, 0)
        capa.setSpacing(8)
        self.ayuda = QTextBrowser()
        self.ayuda.setOpenExternalLinks(False)
        self.ayuda.setReadOnly(True)
        self.ayuda.setAccessibleName('Explicación de la función')
        capa.addWidget(self.ayuda, 2)
        fila_codigo = QHBoxLayout()
        self.titulo_codigo = QLabel('Ejemplo en Python')
        fila_codigo.addWidget(self.titulo_codigo)
        fila_codigo.addStretch(1)
        self.ver_implementacion = QCheckBox('Ver implementación')
        self.ver_implementacion.setToolTip('Muestra el código fuente de la función. No lo ejecuta.')
        fila_codigo.addWidget(self.ver_implementacion)
        capa.addLayout(fila_codigo)
        self.codigo = QPlainTextEdit()
        self.codigo.setObjectName('Codigo')
        self.codigo.setReadOnly(True)
        self.codigo.setFont(fuente_codigo())
        self.codigo.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.codigo.setAccessibleName('Código Python de consulta')
        self.resaltador = ResaltadorPython(self.codigo.document())
        capa.addWidget(self.codigo, 2)
        division.addWidget(detalle)
        division.setStretchFactor(1, 1)
        division.setSizes([300, 740])
        self.cuerpo.addWidget(division, 1)
        self.agregar_botones('Cerrar', cancelar=None)

        for op in CATALOGO.values():
            item = QListWidgetItem(op.titulo)
            item.setData(Qt.ItemDataRole.UserRole, op.id)
            item.setToolTip(f'{op.grupo} · {op.id}')
            self.lista.addItem(item)
        self.lista.currentRowChanged.connect(self._mostrar_operacion)
        self.ver_implementacion.toggled.connect(self._mostrar_codigo)
        ids = list(CATALOGO)
        self.lista.setCurrentRow(ids.index(operacion) if operacion in CATALOGO else 0)

    def _mostrar_operacion(self, fila: int) -> None:
        item = self.lista.item(fila)
        if item is None:
            return
        self.operacion = item.data(Qt.ItemDataRole.UserRole)
        op = CATALOGO[self.operacion]
        partes = [f'<h2>{html.escape(op.titulo)}</h2>',
                  f'<p>{html.escape(OPERACIONES.get(op.id, {}).get("resumen", op.ayuda))}</p>',
                  f'<p><b>Función:</b> <code>micrograno.nucleo.{html.escape(op.id)}</code></p>',
                  f'<p>{html.escape(explicacion_entradas(op.id))}</p>',
                  '<h3>Descripción y resultados</h3>',
                  f'<pre style="white-space:pre-wrap">{html.escape(op.ayuda)}</pre>']
        if op.parametros:
            partes.append('<h3>Parámetros de la función</h3>')
            for nombre, parametro in op.parametros.items():
                meta = meta_parametro(op.id, nombre)
                predeterminado = ('' if parametro.default is inspect.Parameter.empty else
                                  f' Valor predeterminado: {parametro.default!r}.')
                ayuda = AYUDA_PARAMETROS.get(nombre, '')
                partes.append(f'<p><b>{html.escape(meta["etiqueta"])}</b> '
                              f'(<code>{html.escape(nombre)}</code>). '
                              f'{html.escape(ayuda + predeterminado)}</p>')
        self.ayuda.setHtml(''.join(partes))
        self._mostrar_codigo()

    def _mostrar_codigo(self, *_):
        if self.operacion is None:
            return
        op = CATALOGO[self.operacion]
        if self.ver_implementacion.isChecked():
            self.titulo_codigo.setText('Implementación de la función · solo lectura')
            try:
                texto = inspect.getsource(op.funcion)
            except (OSError, TypeError):
                texto = '# El código fuente no está disponible en esta instalación.'
        else:
            self.titulo_codigo.setText('Ejemplo en Python · datos sintéticos')
            texto = op.ejemplo()
        self.codigo.setPlainText(texto)
