"""Toda operación pública se ejecuta, se documenta y conserva sus entradas."""
import inspect
import numpy as np
import pytest
from micrograno import nucleo, Sesion, Resultado
from micrograno.catalogo import CATALOGO, verificar_catalogo, ejecutar, resolver_parametros
from micrograno.sinteticos import poblar_sesion, casos_catalogo

@pytest.mark.parametrize('nombre',list(CATALOGO))
def test_cada_operacion_publica(nombre):
    s=Sesion();ids=poblar_sesion(s)
    entradas,p=casos_catalogo(ids)[nombre]
    antes={id_:s.artefactos[id_].datos.copy() for id_ in entradas.values()}
    r,salidas=s.ejecutar(nombre,entradas,p)
    assert isinstance(r,Resultado)
    assert r.datos.keys()==r.tipos.keys()==salidas.keys()
    for id_,a in antes.items():
        np.testing.assert_array_equal(s.artefactos[id_].datos,a)
        assert not s.artefactos[id_].datos.flags.writeable
    for a in r.datos.values():
        assert not a.flags.writeable
    assert s.pasos[-1]['operacion']==nombre


def test_catalogo_y_ayudas_sin_huerfanas():
    verificar_catalogo()
    assert set(CATALOGO)==set(nucleo.__all__)
    assert len(CATALOGO)==39
    for op in CATALOGO.values():
        compile(op.ejemplo(),'ejemplo','exec')
        assert op.funcion.__module__.startswith('micrograno.')
        assert inspect.getdoc(op.funcion)

@pytest.mark.parametrize('operacion,entradas,parametros',[
    ('no_existe',{},{}),('cuantizar',{},{}),
    ('cuantizar',{'otra':np.ones((3,3))},{}),
    ('cuantizar',{'imagen':np.ones((3,3))},{'inventado':1}),
    ('calibrar_escala',{},{}),
])
def test_catalogo_rechaza_llamadas_invalidas(operacion,entradas,parametros):
    with pytest.raises((ValueError,KeyError)):
        ejecutar(operacion,entradas,parametros)


def test_distribucion_bootstrap_no_es_vector_de_campos():
    s=Sesion();ids=poblar_sesion(s)
    _,sal=s.ejecutar('intervalo_bootstrap_media',{'valores':ids['valores']},{'repeticiones':100})
    with pytest.raises(ValueError,match='requiere tipos'):
        s.ejecutar('intervalo_bootstrap_media',{'valores':sal['medias_remuestreadas']})

@pytest.mark.parametrize('nombre',list(CATALOGO))
def test_ejemplo_de_ayuda_se_ejecuta(nombre):
    contexto={}
    exec(compile(CATALOGO[nombre].ejemplo(),nombre,'exec'),contexto)
    assert 'resultado' in contexto
