"""Recorrido didáctico y controles de contexto, sin algoritmos de imagen."""
from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QListWidget, QListWidgetItem, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)
from micrograno.catalogo import CATALOGO
from .componentes import etiqueta
from .flujo import PASOS_APRENDIZAJE, etapa_de_operacion, razon_bloqueo
from .textos import nombre_tipo


class InterfazAprendizaje:
    """Composición del recorrido; la ventana conserva la ejecución y la sesión."""

    def _crear_pasos(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cuerpo = QWidget()
        lay = QVBoxLayout(cuerpo)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lay.addWidget(etiqueta('Aprender MicroGrano', 'titulo'))
        lay.addWidget(etiqueta('Siga el recorrido con una imagen. Puede volver a cualquier versión.',
                               'secundario', envolver=True))
        self.lista_pasos = QListWidget()
        self.lista_pasos.setObjectName('ListaPasos')
        self.lista_pasos.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for i, paso in enumerate(PASOS_APRENDIZAJE):
            item = QListWidgetItem(f'{i + 1:02d}   {paso["titulo"]}')
            item.setToolTip(paso['descripcion'])
            item.setSizeHint(QSize(0, 37))
            self.lista_pasos.addItem(item)
        self.lista_pasos.setFixedHeight(len(PASOS_APRENDIZAJE) * 37 + 6)
        lay.addWidget(self.lista_pasos)
        self.descripcion_paso = etiqueta('', 'secundario', envolver=True)
        lay.addWidget(self.descripcion_paso)
        self.acciones_paso = QVBoxLayout()
        self.acciones_paso.setSpacing(6)
        lay.addLayout(self.acciones_paso)
        lay.addStretch(1)
        self.lista_pasos.currentRowChanged.connect(self._mostrar_etapa)
        self.lista_pasos.itemClicked.connect(lambda *_: self._elegir_etapa(self.lista_pasos.currentRow()))
        self.lista_pasos.itemActivated.connect(lambda *_: self._elegir_etapa(self.lista_pasos.currentRow()))
        self.lista_pasos.setToolTip('Abra un paso con un clic o con la tecla Intro.')
        self.lista_pasos.setCurrentRow(0)
        scroll.setWidget(cuerpo)
        return scroll

    def _elegir_etapa(self, indice):
        operaciones = PASOS_APRENDIZAJE[indice]['operaciones']
        if not operaciones:
            self.acc['inspector'].setChecked(False)
            return
        a = self.sesion.artefactos.get(self.datos.currentData())
        if indice == 2:
            op = 'extraer_roi' if a is not None and a.tipo == 'gris' else 'convertir_grises'
        else:
            op = next((id_ for id_ in operaciones if a is not None and CATALOGO[id_].entradas
                       and a.tipo in CATALOGO[id_].entradas[0].tipos), operaciones[0])
        self._abrir_leccion(op)

    def _mostrar_etapa(self, indice):
        if indice < 0:
            return
        paso = PASOS_APRENDIZAJE[indice]
        self.descripcion_paso.setText(paso['descripcion'])
        while self.acciones_paso.count():
            item = self.acciones_paso.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        acciones = []
        if indice == 0:
            acciones.append(('Abrir imagen…', lambda: self.importar('imagen')))
        principales = {3: ('histograma_percentiles', 'variantes_contraste', 'variantes_ruido'),
                       5: ('limpiar_mascara', 'etiquetar_componentes', 'separar_watershed')}
        visibles = principales.get(indice, paso['operaciones'][:3])
        for op in visibles:
            acciones.append((CATALOGO[op].titulo, lambda _=False, op=op: self._abrir_leccion(op)))
        if len(paso['operaciones']) > len(visibles):
            acciones.append(('Más funciones de este paso…', lambda: self._catalogo_etapa(indice)))
        if indice == 2:
            acciones.append(('Confirmar la ROI activa…', self.confirmar_roi))
        if indice == len(PASOS_APRENDIZAJE) - 1:
            acciones.extend([('Exportar todas las versiones…', self.exportar_todas_versiones),
                             ('Guardar sesión reproducible…', self.guardar_sesion)])
        for texto, funcion in acciones:
            b = QPushButton(texto)
            b.setMinimumHeight(32)
            b.setToolTip(texto)
            b.clicked.connect(funcion)
            self.acciones_paso.addWidget(b)

    def _catalogo_etapa(self, indice):
        self.selector_lateral.establecer(2, emitir=True)
        self.buscar.clear()
        self.solo_compatibles.setChecked(False)
        permitidas = PASOS_APRENDIZAJE[indice]['operaciones']
        for op, item in self.items.items():
            item.setHidden(op not in permitidas)
        for grupo in self.grupos_items.values():
            grupo.setHidden(all(grupo.child(i).isHidden() for i in range(grupo.childCount())))
            grupo.setExpanded(True)

    def _abrir_leccion(self, operacion):
        self.acc['inspector'].setChecked(True)
        self.selector_inspector.establecer(0, emitir=True)
        self.elegir_operacion(operacion)
        if operacion == 'extraer_roi':
            self.dibujar_roi()
        elif operacion == 'calibrar_escala':
            self.medir_referencia()
        elif operacion == 'perfil_intensidad':
            self.dibujar_perfil()

    def _sincronizar_leccion(self):
        if hasattr(self, 'lista_pasos'):
            self.lista_pasos.setCurrentRow(etapa_de_operacion(self.op_actual))

    def _actualizar_requisitos(self):
        if not hasattr(self, 'requisitos'):
            return
        entradas = {n: w.currentData() for n, w in self.entradas.items() if w.currentData()}
        problema = razon_bloqueo(self.sesion, self.op_actual, entradas)
        self.requisitos.setText(problema or 'Listo para ejecutar. El cálculo queda registrado en la sesión.')
        self.requisitos.setProperty('rol', 'secundario')
        self.ejecutar_btn.setEnabled(not problema and not self._ocupada)
        self.acc['ejecutar'].setEnabled(not problema and not self._ocupada)
        op = CATALOGO[self.op_actual]
        self.btn_resolver_roi.setVisible(bool(problema and 'ROI' in problema))
        self.btn_resolver_escala.setVisible(bool(problema and 'ROI' not in problema and 'escala' in problema.lower()))
        if hasattr(self, 'contexto_version'):
            a = self.sesion.artefactos.get(self.datos.currentData())
            if a:
                escala = a.metadatos.get('escala')
                estado = f'{escala["um_por_px"]:.4g} µm/px' if escala else 'sin escala'
                roi = 'ROI confirmada' if a.metadatos.get('roi_confirmada') else 'ROI pendiente'
                sintetico = ' · Ejemplo sintético' if a.metadatos.get('sintetico') else ''
                self.contexto_version.setText(f'{nombre_tipo(a.tipo)} · {estado} · {roi}{sintetico}')
            else:
                self.contexto_version.setText('Abra una imagen para comenzar.')

    def _confirmar_entrada_roi(self):
        id_ = self._id_entrada_principal()
        if id_:
            self._activar(id_)
            self.confirmar_roi(id_)

    def continuar_salida(self):
        """Adopta la variante elegida explícitamente y abre la próxima lección."""
        if self._tira_previa:
            self.usar_salida()
            return
        id_ = self.tira.currentData()
        if id_ not in self.sesion.artefactos:
            return
        a = self.sesion.artefactos[id_]
        operacion = a.metadatos.get('operacion', '')
        salida = a.metadatos.get('salida', '')
        principal = {'limpiar_mascara': 'limpia', 'separar_watershed': 'etiquetas',
                     'medir_objetos': 'aceptadas'}.get(operacion)
        if principal and salida != principal:
            mensaje = {
                'limpiar_mascara': 'Esta vista muestra píxeles agregados o eliminados. Para segmentar objetos continúe con la máscara limpia.',
                'separar_watershed': 'Esta vista ayuda a revisar watershed. Para medir continúe con los objetos etiquetados.',
                'medir_objetos': 'Esta salida permite revisar las exclusiones. Para seguir analizando utilice los objetos aceptados.',
            }[operacion]
            self.toast.mostrar(mensaje, 'info', 7000,
                               ('Seleccionar salida principal', lambda: self._seleccionar_salida_clave(principal)))
            return
        if a.tipo in ('mapa', 'marcadores', 'distribucion'):
            self.toast.mostrar('Esta salida sirve para interpretar el cálculo. Elija una máscara, clases u objetos '
                               'para continuar. También se conservará al exportar todas las versiones.', 'info', 6500)
            return
        self.usar_salida()
        if operacion == 'extraer_roi' and not a.metadatos.get('roi_confirmada'):
            self.confirmar_roi(id_)
            if not a.metadatos.get('roi_confirmada'):
                return
        if a.tipo == 'gris':
            siguiente = 'extraer_roi' if not a.metadatos.get('roi_confirmada') else (
                'histograma_percentiles' if operacion in ('convertir_grises', 'extraer_roi') else 'umbralizar')
        elif a.tipo == 'imagen':
            siguiente = 'convertir_grises'
        elif a.tipo == 'mascara':
            siguiente = 'etiquetar_componentes' if operacion == 'limpiar_mascara' else 'limpiar_mascara'
        elif a.tipo == 'etiquetas':
            siguiente = 'medir_objetos'
        elif a.tipo == 'clases':
            siguiente = 'fracciones_area'
        elif a.tipo == 'limites':
            siguiente = 'limites_a_regiones'
        else:
            self.selector_lateral.establecer(1, emitir=True)
            return
        self._cambiar_modo_vista('activo')
        self._abrir_leccion(siguiente)
        op = CATALOGO[siguiente]
        if op.entradas and a.tipo in op.entradas[0].tipos:
            combo = self.entradas[op.entradas[0].nombre]
            combo.setCurrentIndex(combo.findData(id_))
            combo.elegido_por_usuario = False

    def _seleccionar_salida_clave(self, clave):
        for i in range(self.tira.count()):
            if self.tira.item(i).data(Qt.ItemDataRole.UserRole + 1) == clave:
                self.tira.setCurrentRow(i)
                return

