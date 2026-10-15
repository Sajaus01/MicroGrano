"""Pruebas Qt: se omiten explícitamente cuando falta el extra [gui]."""
import time
import inspect
import pytest
pytest.importorskip('PySide6',reason='PySide6 no está instalado; la ejecución de la interfaz no se ha verificado aquí.')
from PySide6.QtWidgets import QApplication
from micrograno.catalogo import CATALOGO
from micrograno_lab.ventana import VentanaPrincipal

@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])

@pytest.fixture
def ventana(app):
    w=VentanaPrincipal();w.cargar_demo()
    yield w
    if w.trabajo and w.trabajo.isRunning():w.trabajo.wait(30000)
    w.modificada=False;w.close();app.processEvents()


def test_formulario_para_todas_las_funciones(ventana):
    for id_,op in CATALOGO.items():
        ventana.elegir_operacion(id_)
        assert set(ventana.campos)==set(op.parametros)
        assert set(ventana.entradas)=={e.nombre for e in op.entradas}
        assert ventana.codigo.toPlainText()
        assert ventana.ayuda.toPlainText()


def test_ejecucion_en_hilo_y_resultado_visible(ventana,app):
    ventana.elegir_operacion('histograma_percentiles')
    errores=[]
    ventana._error=lambda texto,detalle='':errores.append(texto)
    ventana.ejecutar_actual()
    fin=time.monotonic()+20
    while ventana.trabajo is not None and time.monotonic()<fin:
        app.processEvents();time.sleep(0.01)
    assert not errores
    assert ventana.trabajo is None
    assert ventana.sesion.pasos[-1]['operacion']=='histograma_percentiles'
    assert len(ventana.modelo.tabla)==256
    assert ventana.resumen.toPlainText()

@pytest.mark.parametrize('id_operacion',list(CATALOGO))
def test_catalogo_ejecutable_desde_formularios(ventana,app,id_operacion,monkeypatch):
    """Cada formulario debe producir los parámetros que usa realmente el hilo."""
    from micrograno.sinteticos import casos_catalogo
    from micrograno.catalogo import resolver_parametros
    from PySide6.QtWidgets import QCheckBox, QComboBox, QMessageBox
    ids={a.nombre.split(' / ')[-1]: id_ for id_,a in ventana.sesion.artefactos.items()}
    entradas,parametros=casos_catalogo(ids)[id_operacion]
    if 's_um_px' in CATALOGO[id_operacion].parametros and 's_um_px' not in parametros:
        parametros['s_um_px']=0.5
    parametros=resolver_parametros(id_operacion,parametros)
    ventana.elegir_operacion(id_operacion)
    for nombre,id_ in entradas.items():
        w=ventana.entradas[nombre];w.setCurrentIndex(w.findData(id_))
    for nombre,valor in parametros.items():
        w=ventana.campos[nombre]
        if isinstance(w,QCheckBox):w.setChecked(valor)
        elif isinstance(w,QComboBox):w.setCurrentText(str(valor))
        else:w.setText('' if valor is None else str(valor))
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**kw:QMessageBox.StandardButton.Yes)
    errores=[];ventana._error=lambda texto,detalle='':errores.append(texto)
    ventana.ejecutar_actual()
    fin=time.monotonic()+25
    while ventana.trabajo is not None and time.monotonic()<fin:
        app.processEvents();time.sleep(0.01)
    assert not errores
    assert ventana.trabajo is None
    assert ventana.sesion.pasos[-1]['operacion']==id_operacion
    assert ventana.resumen.toPlainText()
