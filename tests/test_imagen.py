import numpy as np
import pytest
from micrograno import nucleo as m, EscalaEspacial


def test_roi_limites_excluidos_y_pixeles_intactos():
    a=np.arange(120,dtype=np.uint16).reshape(10,12)
    r=m.extraer_roi(a,2,6,3,8)
    np.testing.assert_array_equal(r.datos['roi'],a[2:6,3:8])
    assert r.datos['roi'].shape==(4,5)
    assert r.resumen['conserva_escala']

@pytest.mark.parametrize('roi',[(3,3,1,4),(6,2,1,4),(0,11,1,4),(-1,2,1,4),(0,2,0,0)])
def test_roi_invalida(roi):
    with pytest.raises((ValueError,TypeError)):
        m.extraer_roi(np.ones((10,10)),*roi)

@pytest.mark.parametrize('a',[
    np.array([[np.nan]]),np.array([[np.inf]]),np.array([[1.01]]),
    np.array([[-0.1]]),np.array([[-1]],dtype=np.int16),
])
def test_grises_no_normaliza_silenciosamente(a):
    with pytest.raises((ValueError,TypeError)):
        m.convertir_grises(a)


def test_uint16_se_preserva_rango_del_tipo():
    a=np.array([[0,4095,32768,65535]],np.uint16)
    b=m.convertir_grises(a).datos['gris']
    np.testing.assert_allclose(b,a/65535)
    assert b[0,1]<0.063


def test_transparencia_no_se_ignora():
    a=np.ones((4,4,4),float);a[0,0,3]=0.5
    with pytest.raises(ValueError,match='transparencia'):
        m.convertir_grises(a)
    a[...,3]=1
    assert m.convertir_grises(a).datos['gris'].shape==(4,4)


def test_rgb_y_canales(conjunto):
    r=m.separar_canales(conjunto['rgb'])
    assert set(r.datos)=={'rojo','verde','azul','gris'}
    np.testing.assert_allclose(r.datos['rojo'],conjunto['rgb'][...,0]/255)
    with pytest.raises(ValueError):m.separar_canales(conjunto['gris'])


def test_calibracion_y_propagacion():
    e=m.calibrar_escala(100,200,1,2,'patrón sintético')
    assert e.um_por_px==0.5
    assert e.incertidumbre_um_por_px==pytest.approx(0.5*np.sqrt(0.01**2+0.01**2))
    assert e.longitud_um(20)==10
    assert e.area_um2(100)==25
    r=m.convertir_medidas(0.5,20,100,0.01)
    assert r.resumen['u_longitud_solo_escala_um']==0.2
    assert r.resumen['u_area_solo_escala_um2']==1

@pytest.mark.parametrize('kw',[
    {'referencia_um':0,'referencia_px':100},
    {'referencia_um':10,'referencia_px':np.nan},
    {'referencia_um':10,'referencia_px':100,'incertidumbre_um':1},
    {'referencia_um':10,'referencia_px':100,'incertidumbre_um':-1,'incertidumbre_px':1},
])
def test_calibracion_invalida(kw):
    with pytest.raises(ValueError):m.calibrar_escala(**kw)

@pytest.mark.parametrize('s',[0,-1,np.nan,np.inf,True])
def test_escala_invalida(s):
    with pytest.raises((ValueError,TypeError)):EscalaEspacial(s)


def test_cuantizacion_niveles_y_no_cambio_geometrico():
    a=np.linspace(0,1,256).reshape(16,16)
    b=m.cuantizar(a,2).datos['cuantizada']
    np.testing.assert_allclose(np.unique(b),[0,1/3,2/3,1])
    assert b.shape==a.shape
    with pytest.raises((ValueError,TypeError)):m.cuantizar(a,2.5)


def test_histograma_conserva_numero_de_pixeles(conjunto):
    r=m.histograma_percentiles(conjunto['gris'],32)
    assert r.tabla.conteo.sum()==conjunto['gris'].size
    assert r.tabla.fraccion.sum()==pytest.approx(1)


def test_perfil_rampa():
    a=np.tile(np.linspace(0,1,11),(11,1))
    r=m.perfil_intensidad(a,5,0,5,10)
    assert r.resumen['longitud_px']==10
    np.testing.assert_allclose(r.tabla.intensidad,np.linspace(0,1,11))
    with pytest.raises(ValueError):m.perfil_intensidad(a,1,1,1,1)


def test_muestreo_no_crea_dimensiones_invalidas(conjunto):
    r=m.reducir_y_ampliar(conjunto['gris'],4)
    assert r.datos['reducida'].shape==(32,40)
    assert r.datos['ampliada'].shape==(128,160)
    for f in (0,1,200,2.5):
        with pytest.raises((ValueError,TypeError)):m.reducir_y_ampliar(conjunto['gris'],f)
