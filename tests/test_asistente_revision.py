"""Contratos Qt y entradas de los controles del asistente guiado."""
import threading
import time

import numpy as np
from PIL import Image
import pytest

pytest.importorskip('PySide6', reason='Estas pruebas requieren el extra [gui].')
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from micrograno_lab.asistente import VentanaAsistente
from micrograno_lab.dialogos import DialogoCarpetaNueva
from micrograno_lab.recorrido import Recorrido


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def esperar(app, ventana):
    limite = time.monotonic() + 20
    while ventana._trabajo is not None and time.monotonic() < limite:
        app.processEvents()
        time.sleep(0.005)
    assert ventana._trabajo is None
    assert not ventana.mensaje.text().startswith('No se pudo'), ventana.mensaje.text()


@pytest.fixture
def ventana(app):
    w = VentanaAsistente()
    yield w
    if w._trabajo is not None:
        w._trabajo.wait(20000)
        app.processEvents()
    w._modificado = False
    w.close()
    w.deleteLater()
    app.processEvents()


def preparar_etapa(ventana, etapa):
    r = Recorrido()
    imagen = np.full((70, 84, 3), 20, dtype=np.uint8)
    imagen[12:29, 15:33] = 210
    imagen[38:58, 50:72] = 170
    original = r.sesion.agregar(imagen, 'imagen', 'Micrografía de prueba')
    r.usar_original(original)
    if etapa != 'escala':
        r.ejecutar('escala', opcion='omitir')
        r.ejecutar('grises')
    if etapa == 'preparar':
        r.ejecutar('roi', dict(r0=5, r1=65, c0=7, c1=80))
        r.confirmar_roi('ROI sintética revisada')
        r.ejecutar('preparar', opcion='conservar')
    r.visitar(etapa)
    ventana._reemplazar(r)
    return r


def test_senal_roi_y_boton_pasan_coordenadas_reales_a_la_biblioteca(app, ventana):
    r = preparar_etapa(ventana, 'roi')
    gris = r.sesion.artefactos[r.entrada()].datos.copy()
    ventana.visor.roi_elegida.emit(5, 65, 7, 80)
    assert ventana.continuar.isEnabled()
    ventana.continuar.click()
    esperar(app, ventana)
    estado = r.estado('roi')
    assert estado is not None and not estado.confirmada
    assert estado.parametros == dict(r0=5, r1=65, c0=7, c1=80)
    np.testing.assert_array_equal(r.sesion.artefactos[estado.salida_id].datos, gris[5:65, 7:80])
    assert ventana._id_mostrado == estado.salida_id
    assert not ventana.continuar.isEnabled()


def test_checkbox_mediana_y_boton_usan_el_parametro_de_radio_real(app, ventana):
    r = preparar_etapa(ventana, 'preparar')
    roi = r.salida('roi')
    ventana.filtrar.click()
    ventana.continuar.click()
    esperar(app, ventana)
    estado = r.estado()
    assert estado.operacion == 'variantes_ruido'
    assert estado.parametros['radio_px'] == 1
    assert estado.entrada_id == roi
    assert estado.salida_id == estado.salidas['mediana']
    assert ventana._id_mostrado == estado.salida_id


def test_linea_y_longitud_calibran_el_original_y_continuan(app, ventana):
    r = preparar_etapa(ventana, 'escala')
    ventana.visor.linea_elegida.emit(0, 0, 0, 40)
    ventana.longitud_um.setValue(20)
    ventana.continuar.click()
    esperar(app, ventana)
    assert ventana.etapa == 'grises'
    assert r.estado('escala').parametros['referencia_px'] == 40
    assert r.sesion.artefactos[r.original_id].metadatos['escala']['um_por_px'] == 0.5
    assert r.sesion.artefactos[r.salida('grises')].metadatos['escala']['um_por_px'] == 0.5


def test_boton_abrir_imagen_usa_la_ruta_elegida(app, ventana, monkeypatch, tmp_path):
    datos = np.arange(48 * 60 * 3, dtype=np.uint8).reshape(48, 60, 3)
    ruta = tmp_path / 'muestra.png'
    Image.fromarray(datos).save(ruta)
    monkeypatch.setattr(QFileDialog, 'getOpenFileName', lambda *_a, **_k: (str(ruta), 'Imágenes'))
    ventana.continuar.click()
    assert ventana.recorrido.original_id
    original = ventana.sesion.artefactos[ventana.recorrido.original_id]
    np.testing.assert_array_equal(original.datos, datos)
    assert original.metadatos['ruta'] == str(ruta.resolve())
    assert ventana.etapa == 'imagen'
    assert ventana.continuar.text().startswith('Continuar')


def test_dialogo_carpeta_real_devuelve_destino_validado(ventana, monkeypatch, tmp_path):
    def aceptar(dialogo):
        dialogo.ubicacion.setText(str(tmp_path))
        assert dialogo.boton_aceptar.isEnabled()
        return QDialog.DialogCode.Accepted
    monkeypatch.setattr(DialogoCarpetaNueva, 'exec', aceptar)
    ruta = ventana._elegir_carpeta('Guardar sesión', 'prueba', 'Guardar')
    assert ruta == tmp_path / 'prueba'
    assert not ruta.exists()
    monkeypatch.setattr(DialogoCarpetaNueva, 'exec', lambda _self: QDialog.DialogCode.Rejected)
    assert ventana._elegir_carpeta('Guardar sesión', 'prueba', 'Guardar') is None


def test_cierre_y_reemplazo_bloqueados_durante_calculo(app, ventana, monkeypatch):
    preparar_etapa(ventana, 'escala')
    recorrido = ventana.recorrido
    liberar = threading.Event()
    monkeypatch.setattr(QMessageBox, 'question', lambda *_a, **_k: pytest.fail('No debe abrir confirmación mientras calcula'))
    ventana._iniciar(lambda: liberar.wait(5), lambda: None, modifica=False)
    try:
        evento = QCloseEvent()
        ventana.closeEvent(evento)
        assert not evento.isAccepted()
        ventana.importar(ruta='imagen_inexistente.png')
        ventana.cargar_ejemplo()
        ventana.retroceder()
        assert ventana.recorrido is recorrido
        assert ventana.etapa == 'escala'
        assert not ventana.panel.isEnabled()
        assert not ventana.visor.isEnabled()
    finally:
        liberar.set()
        esperar(app, ventana)
    assert ventana.panel.isEnabled()
    assert ventana.visor.isEnabled()
