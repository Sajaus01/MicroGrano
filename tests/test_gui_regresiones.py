"""Regresiones de selección de versiones y coordenadas en la interfaz."""
import numpy as np
import pytest

pytest.importorskip('PySide6', reason='Estas pruebas requieren el extra [gui].')
from PySide6.QtWidgets import QApplication, QDialog

from micrograno.visualizacion import preparar_vista
from micrograno_lab import ventana as modulo_ventana
from micrograno_lab.ventana import VentanaPrincipal


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ventana(app):
    w = VentanaPrincipal()
    original = np.arange(40 * 60 * 3, dtype=np.uint8).reshape(40, 60, 3)
    gris = np.linspace(0, 1, 18 * 24).reshape(18, 24)
    ids = {
        'original': w.sesion.agregar(original, 'imagen', 'Imagen original'),
        'gris': w.sesion.agregar(gris, 'gris', 'Versión gris pequeña', {'roi_confirmada': True}),
        'mascara': w.sesion.agregar(gris > 0.5, 'mascara', 'Máscara'),
    }
    w._actualizar_datos(ids['original'])
    yield w, ids
    w._detener_vista_previa(restaurar=False)
    if w.trabajo and w.trabajo.isRunning():
        w.trabajo.wait(30000)
    hilo = w._previa['hilo']
    if hilo and hilo.isRunning():
        hilo.wait(30000)
    w.modificada = False
    w.close()
    app.processEvents()


@pytest.mark.parametrize('operacion, metodo, herramienta', [
    ('extraer_roi', 'dibujar_roi', 'roi'),
    ('perfil_intensidad', 'dibujar_perfil', 'linea'),
])
def test_dibujar_usa_la_version_elegida_en_el_formulario(ventana, operacion, metodo, herramienta):
    w, ids = ventana
    w.elegir_operacion(operacion)
    entrada = w.entradas['imagen']
    entrada.setCurrentIndex(entrada.findData(ids['gris']))
    entrada.elegido_por_usuario = True
    assert w.datos.currentData() == ids['original']

    getattr(w, metodo)()

    assert w.datos.currentData() == ids['gris']
    assert w.entradas['imagen'].currentData() == ids['gris']
    assert w.visor_entrada._forma == (18, 24)
    assert w.visor_entrada.herramienta() == herramienta
    if operacion == 'extraer_roi':
        w._roi_elegida(2, 12, 3, 20)
        _, salidas = w.sesion.ejecutar(operacion, {'imagen': w.entradas['imagen'].currentData()},
                                      w._leer_parametros())
        recorte = w.sesion.artefactos[next(iter(salidas.values()))]
        np.testing.assert_array_equal(recorte.datos, w.sesion.artefactos[ids['gris']].datos[2:12, 3:20])
        assert w.sesion.artefactos[ids['original']].datos.shape == (40, 60, 3)
    else:
        w._linea_elegida(2, 3, 12, 20)
        parametros = w._leer_parametros()
        assert [parametros[n] for n in ('r0', 'c0', 'r1', 'c1')] == [2, 3, 12, 20]


@pytest.mark.parametrize('metodo', ['dibujar_roi', 'dibujar_perfil', 'medir_referencia'])
def test_dibujo_incompatible_explica_que_version_necesita(ventana, metodo, monkeypatch):
    w, ids = ventana
    w._activar(ids['mascara'])
    operacion = w.op_actual
    avisos = []
    monkeypatch.setattr(w.toast, 'mostrar', lambda texto, *args, **kwargs: avisos.append(texto))

    getattr(w, metodo)()

    assert avisos and 'grises' in avisos[-1]
    assert w.op_actual == operacion
    assert w.datos.currentData() == ids['mascara']
    assert w.visor_entrada.herramienta() == 'mover'


@pytest.mark.parametrize('exportar_salida', [False, True])
def test_exportacion_selecciona_activo_o_salida_explicita(ventana, monkeypatch, tmp_path, exportar_salida):
    w, ids = ventana
    _, salidas = w.sesion.ejecutar('convertir_grises', {'imagen': ids['original']})
    id_salida = next(iter(salidas.values()))
    w._actualizar_datos(ids['original'])
    w._llenar_tira(salidas, w.sesion)
    nombres, imagenes = [], []

    class DialogoExportacion:
        def __init__(self, parent, nombre, *args):
            nombres.append(nombre)

        def exec(self):
            return QDialog.DialogCode.Accepted

        def valores(self):
            return dict(ruta=str(tmp_path / 'figura.png'), titulo='', descripcion='', fuente='')

        def deleteLater(self):
            pass

    def exportar(imagen, *args, **kwargs):
        imagenes.append(imagen.copy())
        return {'advertencia_tipografica': ''}

    monkeypatch.setattr(modulo_ventana, 'DialogoExportarFigura', DialogoExportacion)
    monkeypatch.setattr(modulo_ventana, 'exportar_figura', exportar)
    esperado = id_salida if exportar_salida else ids['original']
    if exportar_salida:
        w.exportar_vista(id_salida)
    else:
        w.exportar_vista()

    assert nombres == [w.sesion.artefactos[esperado].nombre]
    vista = preparar_vista(w.sesion.artefactos[esperado], w.sesion, w.superponer.isChecked(), False)
    np.testing.assert_array_equal(imagenes[0], vista['imagen'])


def test_no_exporta_vista_previa_como_si_fuera_version_guardada(ventana, monkeypatch):
    w, ids = ventana
    w._llenar_tira({'gris': ids['gris']}, w.sesion)
    w._tira_previa = True
    avisos = []
    monkeypatch.setattr(w.toast, 'mostrar', lambda texto, *args, **kwargs: avisos.append(texto))
    monkeypatch.setattr(modulo_ventana, 'DialogoExportarFigura',
                        lambda *args: pytest.fail('Una vista previa no debe abrir la exportación.'))

    w.exportar_vista(ids['gris'])

    assert avisos and 'vista previa' in avisos[-1]
