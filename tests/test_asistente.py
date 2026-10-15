"""Recorrido mediante los controles de la ventana que abre el lanzador."""
import json
import time

import numpy as np
import pytest

pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import QPointF, Qt
from PySide6.QtTest import QTest
from micrograno_lab.asistente import VentanaAsistente
from micrograno_lab.recorrido import Recorrido
from micrograno_lab.consulta import DialogoVersiones


def esperar(w, app):
    limite = time.monotonic() + 30
    while w._trabajo is not None and time.monotonic() < limite:
        app.processEvents()
        time.sleep(.005)
    app.processEvents()
    assert w._trabajo is None
    assert not w.mensaje.text().startswith('No se pudo'), w.mensaje.text()


def continuar(w, app):
    assert w.continuar.isEnabled(), w.continuar.text()
    w.continuar.click()
    esperar(w, app)


@pytest.fixture
def ventana():
    app = QApplication.instance() or QApplication([])
    w = VentanaAsistente()
    yield w, app
    esperar(w, app)
    w._modificado = False
    w.close()
    app.processEvents()


def hasta_roi(w, app, escala=True):
    w.cargar_ejemplo()
    continuar(w, app)
    assert w.etapa == 'escala'
    if escala:
        w._escala_ejemplo()
    else:
        w._omitir_escala()
    esperar(w, app)
    assert w.etapa == 'grises'
    continuar(w, app)
    assert w.etapa == 'roi'
    w.visor.roi_elegida.emit(10, 100, 15, 135)
    continuar(w, app)
    assert not w.recorrido.completada()
    assert not w.continuar.isEnabled()
    w.confirmacion_roi.setChecked(True)
    continuar(w, app)
    assert w.etapa == 'preparar'


def test_boton_continuar_encadena_roi_mascaras_medidas_y_exporta(ventana, tmp_path):
    w, app = ventana
    hasta_roi(w, app)
    rec = w.recorrido
    original = w.sesion.artefactos[rec.original_id].datos.copy()
    roi = rec.salida('roi')
    gris = w.sesion.artefactos[rec.salida('grises')].datos
    np.testing.assert_array_equal(w.sesion.artefactos[roi].datos, gris[10:100, 15:135])
    assert rec.entrada('preparar') == roi
    assert w._id_mostrado == roi
    continuar(w, app)
    assert w.etapa == 'segmentar'
    assert rec.entrada() == roi
    mascara = rec.salida()
    assert w.sesion.artefactos[mascara].datos.dtype == bool
    assert w._id_mostrado == mascara
    assert w.visor._tipo == 'mascara'
    continuar(w, app)
    assert w.etapa == 'limpiar'
    assert rec.entrada() == mascara
    limpia = rec.salida()
    continuar(w, app)
    assert w.etapa == 'etiquetar'
    assert rec.entrada() == limpia
    etiquetas = rec.salida()
    continuar(w, app)
    assert w.etapa == 'medir'
    assert rec.entrada() == etiquetas
    tabla = rec.resultado().tabla
    assert len(tabla) > 0
    assert 'area_um2' in tabla
    w._ver_tabla()
    assert w.modelo_tabla.rowCount() == len(tabla)
    continuar(w, app)
    assert w.etapa == 'exportar'
    for etapa in ('roi', 'segmentar', 'limpiar', 'etiquetar', 'medir'):
        assert w.sesion.artefactos[rec.salida(etapa)].datos.shape == (90, 120)
    np.testing.assert_array_equal(w.sesion.artefactos[rec.original_id].datos, original)
    destino = tmp_path / 'analisis'
    w.exportar(destino)
    esperar(w, app)
    assert (destino / 'versiones.json').is_file()
    assert (destino / 'sesion_reabrible' / 'recorrido.json').is_file()
    reabierto = Recorrido.abrir(destino)
    assert reabierto.actual == 9
    assert reabierto.estados == rec.estados
    assert set(reabierto.sesion.artefactos) == set(w.sesion.artefactos)


def test_navegar_y_consultar_no_selecciona_otra_entrada(ventana):
    w, app = ventana
    hasta_roi(w, app)
    continuar(w, app)
    etapa, entrada, salida = w.etapa, w.recorrido.entrada(), w.recorrido.salida()
    total = len(w.sesion.artefactos)
    dialogo = DialogoVersiones(w, w.sesion)
    dialogo.lista.setCurrentRow(0)
    dialogo.lista.setCurrentRow(dialogo.lista.count() - 1)
    dialogo.close()
    assert (w.etapa, w.recorrido.entrada(), w.recorrido.salida()) == (etapa, entrada, salida)
    w.anterior.click()
    continuar(w, app)
    assert w.recorrido.salida() == salida
    assert len(w.sesion.artefactos) == total
    assert all(isinstance(indicador, QLabel) for indicador in w.indicadores)
    assert not hasattr(w, 'datos')  # No existe selector de imagen activa.


def test_comparar_roi_no_sustituye_mascara(ventana):
    w, app = ventana
    hasta_roi(w, app)
    continuar(w, app)
    mascara, entrada = w.recorrido.salida(), w.recorrido.entrada()
    w.comparar.setChecked(True)
    assert w._id_mostrado == mascara
    np.testing.assert_array_equal(w.referencia._datos, w.sesion.artefactos[w.recorrido.salida('roi')].datos)
    assert w.recorrido.entrada() == entrada
    continuar(w, app)
    assert w.recorrido.entrada() == mascara


def test_redibujar_roi_obliga_confirmar_y_recalcular_siguientes(ventana):
    w, app = ventana
    hasta_roi(w, app)
    continuar(w, app)
    mascara_previa = w.recorrido.salida()
    w.anterior.click()
    w.anterior.click()
    assert w.etapa == 'roi'
    w._redibujar_roi()
    assert w._id_mostrado == w.recorrido.salida('grises')
    w.visor.roi_elegida.emit(20, 70, 30, 110)
    continuar(w, app)
    assert not w.continuar.isEnabled()
    assert w.recorrido.salida('segmentar') is None
    assert mascara_previa in w.sesion.artefactos
    w.confirmacion_roi.setChecked(True)
    continuar(w, app)
    assert w.recorrido.entrada() == w.recorrido.salida('roi')
    continuar(w, app)
    assert w.visor._datos.shape == (50, 80)


def test_recalcular_anterior_descarta_solo_ruta_posterior(ventana):
    w, app = ventana
    hasta_roi(w, app)
    continuar(w, app)
    anterior = w.recorrido.salida()
    continuar(w, app)
    limpia_anterior = w.recorrido.salida()
    w.anterior.click()
    w.polaridad.setCurrentIndex(1)
    assert w._sucio
    assert 'Actualizar' in w.continuar.text()
    continuar(w, app)
    assert w.etapa == 'segmentar'
    assert w.recorrido.salida() != anterior
    assert w.recorrido.salida('limpiar') is None
    assert limpia_anterior in w.sesion.artefactos
    np.testing.assert_array_equal(w.sesion.artefactos[w.recorrido.salida()].datos,
                                  ~w.sesion.artefactos[anterior].datos)
    continuar(w, app)
    assert w.recorrido.entrada() == w.recorrido.salida('segmentar')


def test_sin_escala_no_inventa_medidas(ventana):
    w, app = ventana
    hasta_roi(w, app, escala=False)
    for _ in range(4):
        continuar(w, app)
    assert w.etapa == 'medir'
    assert w.recorrido.estado() is None
    assert 'sin medidas' in w.continuar.text()
    continuar(w, app)
    assert w.etapa == 'exportar'
    assert w.recorrido.estado('medir').omitida
    assert all(p['operacion'] != 'medir_objetos' for p in w.sesion.pasos)


def test_guardar_y_abrir_reanuda_roi_pendiente(ventana, tmp_path):
    w, app = ventana
    w.cargar_ejemplo()
    continuar(w, app)
    w._omitir_escala()
    esperar(w, app)
    continuar(w, app)
    w._roi_completa()
    esperar(w, app)
    assert w.guardar_sesion(tmp_path / 'sesion')
    w.abrir_sesion(tmp_path / 'sesion')
    assert w.etapa == 'roi'
    assert not w.recorrido.completada()
    assert not w.continuar.isEnabled()
    assert w._id_mostrado == w.recorrido.salida('roi')


def test_reabrir_conserva_linea_de_calibracion(ventana, tmp_path):
    w, app = ventana
    w.cargar_ejemplo()
    continuar(w, app)
    w.visor.linea_elegida.emit(10., 20., 10., 70.)
    w.longitud_um.setValue(25)
    assert w.visor._linea.isVisible()
    continuar(w, app)
    w.anterior.click()
    assert w.etapa == 'escala'
    assert w.guardar_sesion(tmp_path / 'calibracion')
    w.abrir_sesion(tmp_path / 'calibracion')
    assert w._linea_coordenadas == [10., 20., 10., 70.]
    assert w.visor._linea.isVisible()
    assert w._linea_px == 50


def test_arrastrar_ratón_dibuja_y_recorta_la_entrada_correcta(ventana):
    w, app = ventana
    w.show()
    w.cargar_ejemplo()
    continuar(w, app)
    w._omitir_escala()
    esperar(w, app)
    continuar(w, app)
    app.processEvents()
    w.visor.ajustar()
    inicio = w.visor.mapFromScene(QPointF(20, 15))
    fin = w.visor.mapFromScene(QPointF(120, 85))
    QTest.mousePress(w.visor.viewport(), Qt.MouseButton.LeftButton, pos=inicio)
    QTest.mouseMove(w.visor.viewport(), fin)
    QTest.mouseRelease(w.visor.viewport(), Qt.MouseButton.LeftButton, pos=fin)
    assert w._rectangulo == dict(r0=15, r1=85, c0=20, c1=120)
    continuar(w, app)
    assert w.visor._datos.shape == (70, 100)
