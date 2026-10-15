"""Consultar una versión o una función nunca cambia el procesamiento."""
from copy import deepcopy

import numpy as np
import pytest

pytest.importorskip('PySide6', reason='Estas pruebas requieren el extra [gui].')
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton

from micrograno import Sesion
from micrograno.catalogo import CATALOGO
from micrograno_lab.consulta import DialogoBiblioteca, DialogoVersiones


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sesion():
    s = Sesion('Consulta')
    original = s.agregar(np.arange(24 * 30 * 3, dtype=np.uint8).reshape(24, 30, 3),
                         'imagen', 'Imagen original')
    _, roi = s.ejecutar('extraer_roi', {'imagen': original},
                        {'r0': 2, 'r1': 22, 'c0': 3, 'c1': 27})
    s.confirmar_roi(roi['roi'], 'Región sintética de prueba')
    _, grises = s.ejecutar('convertir_grises', {'imagen': roi['roi']})
    s.ejecutar('umbralizar', {'imagen': grises['gris']}, {'bloque': 3})
    s.agregar(np.array([1.0, 2.5, 3.0]), 'valores', 'Valores por campo')
    return s


def test_consulta_todas_versiones_sin_mutar_la_sesion(app, sesion, monkeypatch):
    pasos, fuentes = deepcopy(sesion.pasos), deepcopy(sesion.fuentes)
    datos = {id_: a.datos.copy() for id_, a in sesion.artefactos.items()}
    metadatos = {id_: deepcopy(a.metadatos) for id_, a in sesion.artefactos.items()}
    resultados = list(sesion.resultados)
    principal = next(iter(sesion.artefactos))
    etapas = {principal: 'Imagen'}
    monkeypatch.setattr(sesion, 'ejecutar', lambda *_a, **_k: pytest.fail('La consulta no ejecuta funciones'))
    dialogo = DialogoVersiones(None, sesion, etapas)
    try:
        assert dialogo.lista.count() == len(sesion.artefactos)
        assert 'Paso: Imagen' in dialogo.lista.item(0).text()
        assert 'Consulta; no cambia el análisis' in ' '.join(
            e.text() for e in dialogo.findChildren(QLabel))
        for fila, (id_, artefacto) in enumerate(sesion.artefactos.items()):
            dialogo.lista.setCurrentRow(fila)
            assert dialogo.id_consultado == id_
            assert artefacto.nombre in dialogo.detalle_version.text()
            if artefacto.datos.ndim >= 2:
                assert dialogo.contenido.currentWidget() is dialogo.visor
                np.testing.assert_array_equal(dialogo.visor.arreglo, artefacto.datos)
                assert dialogo.visor.herramienta() == 'mover'
                if artefacto.tipo == 'mascara':
                    assert dialogo.visor._tipo == 'mascara'
                    assert dialogo.visor._capa.pixmap().isNull()
            else:
                assert dialogo.contenido.currentWidget() is dialogo.tabla
                np.testing.assert_array_equal(dialogo.modelo.tabla['valor'].to_numpy(), artefacto.datos)
        assert sesion.pasos == pasos
        assert sesion.fuentes == fuentes
        assert all(a is b for a, b in zip(sesion.resultados, resultados))
        assert len(sesion.resultados) == len(resultados)
        assert set(sesion.artefactos) == set(datos)
        for id_, artefacto in sesion.artefactos.items():
            np.testing.assert_array_equal(artefacto.datos, datos[id_])
            assert artefacto.metadatos == metadatos[id_]
        assert etapas == {principal: 'Imagen'}
        assert [b.text() for b in dialogo.findChildren(QPushButton)] == ['Cerrar']
    finally:
        dialogo.close()
        dialogo.deleteLater()
        app.processEvents()


def test_galeria_vacia_y_principales_independientes(app):
    dialogo = DialogoVersiones(None, Sesion())
    try:
        assert dialogo.lista.count() == 0
        assert dialogo.id_consultado is None
        assert dialogo.visor.arreglo is None
    finally:
        dialogo.close()
        dialogo.deleteLater()
        app.processEvents()


def test_biblioteca_cubre_catalogo_sin_controles_de_ejecucion(app):
    dialogo = DialogoBiblioteca(None, 'extraer_roi')
    try:
        assert dialogo.operacion == 'extraer_roi'
        assert dialogo.lista.count() == len(CATALOGO) == 39
        assert dialogo.ayuda.isReadOnly()
        assert dialogo.codigo.isReadOnly()
        for fila, id_ in enumerate(CATALOGO):
            dialogo.lista.setCurrentRow(fila)
            assert dialogo.lista.currentItem().data(Qt.ItemDataRole.UserRole) == id_
            assert f'micrograno.nucleo.{id_}' in dialogo.ayuda.toPlainText()
            assert f'mg.{id_}(' in dialogo.codigo.toPlainText()
        assert [b.text() for b in dialogo.findChildren(QPushButton)] == ['Cerrar']
    finally:
        dialogo.close()
        dialogo.deleteLater()
        app.processEvents()


def test_implementacion_es_solo_consulta_y_recupera_ejemplo(app):
    dialogo = DialogoBiblioteca(None, 'umbralizar')
    try:
        ejemplo = dialogo.codigo.toPlainText()
        dialogo.ver_implementacion.setChecked(True)
        assert 'def umbralizar(' in dialogo.codigo.toPlainText()
        assert dialogo.codigo.isReadOnly()
        assert dialogo.operacion == 'umbralizar'
        dialogo.ver_implementacion.setChecked(False)
        assert dialogo.codigo.toPlainText() == ejemplo
    finally:
        dialogo.close()
        dialogo.deleteLater()
        app.processEvents()
