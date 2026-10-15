"""Recorrido completo desde una imagen hasta sus versiones exportadas."""
import json
import time
import numpy as np
import pytest

pytest.importorskip('PySide6')
from PySide6.QtWidgets import QApplication
from micrograno import Sesion
from micrograno_lab.ventana import VentanaPrincipal
from micrograno_lab.flujo import nombre_version


@pytest.fixture
def ventana():
    app = QApplication.instance() or QApplication([])
    w = VentanaPrincipal()
    errores = []
    w._error = lambda texto, detalle='': errores.append(texto)
    w._errores_prueba = errores
    yield w, app
    if w.trabajo:
        w.trabajo.wait(30000)
        app.processEvents()
    w.modificada = False
    w.close()
    app.processEvents()


def ejecutar(w, app):
    antes = len(w.sesion.pasos)
    w.ejecutar_actual()
    fin = time.monotonic() + 20
    while w.trabajo is not None and time.monotonic() < fin:
        app.processEvents()
        time.sleep(.005)
    assert w.trabajo is None
    assert not w._errores_prueba
    assert len(w.sesion.pasos) == antes + 1


def test_recorrido_completo_conserva_y_exporta_cada_version(ventana, tmp_path, monkeypatch):
    w, app = ventana
    w.cargar_ejemplo()
    original = w.datos.currentData()
    copia = w.sesion.artefactos[original].datos.copy()
    assert len(w.sesion.artefactos) == 1
    assert w.pila_lateral.currentIndex() == 0
    w._abrir_leccion('convertir_grises')
    ejecutar(w, app)
    gris = w.tira.currentData()
    assert 'Grises' in nombre_version(w.sesion, gris)
    w.continuar_salida()
    assert w.op_actual == 'extraer_roi'
    assert w.entradas['imagen'].currentData() == gris
    w._roi_elegida(10, 100, 10, 140)
    ejecutar(w, app)
    roi = w.tira.currentData()
    monkeypatch.setattr(w, 'confirmar_roi', lambda id_=None: w.sesion.confirmar_roi(
        id_ or w.datos.currentData(), 'ROI sintética revisada para esta prueba'))
    w.continuar_salida()
    assert w.datos.currentData() == roi
    assert w.sesion.artefactos[roi].datos.shape == (90, 130)
    assert w.sesion.artefactos[roi].metadatos['escala']['um_por_px'] == .5
    w._abrir_leccion('umbralizar')
    ejecutar(w, app)
    mascara = w.tira.currentData()
    assert w.sesion.artefactos[mascara].tipo == 'mascara'
    w.continuar_salida()
    assert w.op_actual == 'limpiar_mascara'
    ejecutar(w, app)
    w.continuar_salida()
    assert w.op_actual == 'etiquetar_componentes'
    ejecutar(w, app)
    etiquetas = w.tira.currentData()
    w.continuar_salida()
    assert w.op_actual == 'medir_objetos'
    assert w.entradas['etiquetas'].currentData() == etiquetas
    ejecutar(w, app)
    assert w.modelo.rowCount() > 0
    np.testing.assert_array_equal(w.sesion.artefactos[original].datos, copia)
    destino = tmp_path / 'versiones'
    monkeypatch.setattr(w, '_carpeta_nueva', lambda *a, **kw: destino)
    w.exportar_todas_versiones()
    if w.trabajo:
        fin = time.monotonic() + 30
        while w.trabajo is not None and time.monotonic() < fin:
            app.processEvents()
            time.sleep(.005)
    assert not w._errores_prueba
    registro = json.loads((destino / 'versiones.json').read_text(encoding='utf-8'))
    assert len(registro['versiones']) == len(w.sesion.artefactos)
    ruta = w.sesion.guardar(tmp_path / 'sesion')
    reabierta = Sesion.abrir(ruta)
    assert set(reabierta.artefactos) == set(w.sesion.artefactos)
    for id_, a in w.sesion.artefactos.items():
        np.testing.assert_array_equal(a.datos, reabierta.artefactos[id_].datos)


def test_requisitos_explican_roi_y_controles_sin_resultado(ventana):
    w, app = ventana
    w.cargar_ejemplo()
    w.elegir_operacion('convertir_grises')
    ejecutar(w, app)
    w.usar_salida()
    w.elegir_operacion('umbralizar')
    assert not w.ejecutar_btn.isEnabled()
    assert 'ROI' in w.requisitos.text()
    assert not w.btn_resolver_roi.isHidden()
    assert w.btn_resolver_escala.isHidden()
    assert not w.sesion.artefactos[w.datos.currentData()].metadatos.get('roi_confirmada')


def test_continuar_reemplaza_entrada_anterior_explicita(ventana):
    w, app = ventana
    w.cargar_demo()
    w.elegir_operacion('limpiar_mascara')
    ejecutar(w, app)
    viejo = w._id_entrada_principal()
    nueva = w.tira.currentData()
    w.elegir_operacion('etiquetar_componentes')
    combo = w.entradas['mascara']
    combo.setCurrentIndex(combo.findData(viejo))
    combo.elegido_por_usuario = True
    w.continuar_salida()
    assert w.entradas['mascara'].currentData() == nueva


def test_seleccionar_version_la_muestra_y_pasos_abren_funcion(ventana):
    w, app = ventana
    w.cargar_demo()
    w.elegir_operacion('umbralizar')
    ejecutar(w, app)
    w.lista_datos.setCurrentRow(1)
    assert w.modo_vista == 'activo'
    assert w.datos.currentData() == w.lista_datos.item(1).data(256)
    w._elegir_etapa(2)
    assert w.op_actual == 'convertir_grises'
    w._elegir_etapa(7)
    assert w.inspector.isHidden()
    w._elegir_etapa(0)
    assert w.op_actual == 'explorar_imagen'
    assert not w.inspector.isHidden()


def test_no_propone_version_de_otra_micrografia(ventana):
    w, app = ventana
    w.cargar_ejemplo()
    w.elegir_operacion('convertir_grises')
    ejecutar(w, app)
    gris_anterior = w.tira.currentData()
    w.cargar_ejemplo()
    w.elegir_operacion('umbralizar')
    assert w.entradas['imagen'].currentData() is None
    assert not w.ejecutar_btn.isEnabled()
    # La versión anterior sigue disponible para una elección explícita.
    assert w.entradas['imagen'].findData(gris_anterior) > 0


def test_exportacion_fallida_rehabilita_la_interfaz(ventana, tmp_path, monkeypatch):
    import micrograno_lab.ventana as modulo
    w, app = ventana
    w.cargar_ejemplo()
    monkeypatch.setattr(w, '_carpeta_nueva', lambda *a, **kw: tmp_path / 'salida')
    def fallo(*a, **kw):
        raise OSError('Disco de prueba no disponible')
    monkeypatch.setattr(modulo, 'exportar_versiones', fallo)
    w.exportar_todas_versiones()
    assert w._ocupada
    fin = time.monotonic() + 10
    while w.trabajo is not None and time.monotonic() < fin:
        app.processEvents()
        time.sleep(.005)
    assert w.trabajo is None
    assert not w._ocupada
    assert w.btn_exportar.isEnabled()
    assert w._errores_prueba == ['Disco de prueba no disponible']


@pytest.mark.parametrize('operacion,diagnostico,principal', [
    ('limpiar_mascara', 'eliminados', 'limpia'),
    ('separar_watershed', 'marcadores', 'etiquetas'),
])
def test_continuar_diagnostico_orienta_sin_cambiar_entrada(ventana, operacion, diagnostico, principal):
    w, app = ventana
    w.cargar_demo()
    w.elegir_operacion(operacion)
    ejecutar(w, app)
    activo = w.datos.currentData()
    w._seleccionar_salida_clave(diagnostico)
    salida = w.tira.currentData()
    w.continuar_salida()
    assert w.datos.currentData() == activo
    assert w.datos.currentData() != salida
    w._seleccionar_salida_clave(principal)
    w.continuar_salida()
    assert w.datos.currentData() == w.tira.currentData()


def test_sesion_no_cambia_durante_calculo_o_exportacion(ventana, monkeypatch):
    w, app = ventana
    w.cargar_ejemplo()
    original = w.sesion
    cantidad = len(original.artefactos)
    # Evita diálogos si una entrada omite por error la protección.
    monkeypatch.setattr(w, '_puede_reemplazar', lambda: True)
    w._ocupado(True)
    for clave in ('nueva', 'abrir', 'demo', 'ejemplo', 'importar_imagen'):
        assert not w.acc[clave].isEnabled()
        w.acc[clave].trigger()
    w.nueva_sesion()
    w.cargar_ejemplo()
    w.cargar_demo()
    w.abrir_sesion('no_debe_abrirse.json')
    w.importar('imagen', 'no_debe_abrirse.png')
    assert w.sesion is original
    assert len(w.sesion.artefactos) == cantidad
    assert not w._errores_prueba
    w._ocupado(False)
    assert w.acc['importar_imagen'].isEnabled()


def test_intro_abre_leccion_y_cierre_espera_previa(ventana):
    from PySide6.QtGui import QCloseEvent
    w, app = ventana
    w.cargar_ejemplo()
    w.lista_pasos.setCurrentRow(2)
    w.lista_pasos.itemActivated.emit(w.lista_pasos.item(2))
    assert w.op_actual == 'convertir_grises'
    class PreviaActiva:
        def isRunning(self):
            return True
    w._previa['hilo'] = PreviaActiva()
    evento = QCloseEvent()
    w.closeEvent(evento)
    assert not evento.isAccepted()
    w._previa['hilo'] = None
