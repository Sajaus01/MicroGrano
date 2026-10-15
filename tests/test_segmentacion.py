import numpy as np
import pytest
from micrograno import nucleo as m


def test_umbral_polaridades_complementarias():
    a=np.tile(np.linspace(0,1,31),(31,1))
    claro=m.umbralizar(a,bloque=5,polaridad='clara')
    oscuro=m.umbralizar(a,bloque=5,polaridad='oscura')
    for k in ('manual','otsu','adaptativa'):
        np.testing.assert_array_equal(claro.datos[k],~oscuro.datos[k])
    with pytest.raises(ValueError):m.umbralizar(a,bloque=4)
    with pytest.raises(ValueError):m.umbralizar(np.ones((10,10)))


def test_filtro_area_incluye_igualdad():
    a=np.zeros((8,25),bool)
    a[1,1:5]=True # 4
    a[3,1:6]=True # 5
    a[5,1:7]=True # 6
    r=m.limpiar_mascara(a,area_minima=5,conectividad=1)
    assert not r.datos['limpia'][1].any()
    assert r.datos['limpia'][3].sum()==5
    assert r.datos['limpia'][5].sum()==6
    assert r.resumen['pixeles_eliminados']==4


def test_huecos_cerrados_sin_rellenar_exterior():
    a=np.zeros((12,12),bool);a[2:10,2:10]=True
    a[5,5]=False;a[6,7]=False
    r=m.limpiar_mascara(a,1,hueco_maximo=2)
    assert r.datos['limpia'][5,5] and r.datos['limpia'][6,7]
    assert not r.datos['limpia'][0,0]


def test_conectividad_cambia_conteo():
    a=np.eye(3,dtype=bool)
    assert m.etiquetar_componentes(a,1).resumen['numero_objetos']==3
    assert m.etiquetar_componentes(a,2).resumen['numero_objetos']==1


def test_mascara_no_se_infiere_de_imagen():
    with pytest.raises(TypeError):m.etiquetar_componentes(np.ones((4,4)))
    with pytest.raises(TypeError):m.variantes_morfologicas(np.ones((4,4),np.uint8))


def test_watershed_no_pierde_componentes_en_marco():
    a=np.zeros((20,30),bool);a[:3,:3]=True;a[9:15,18:26]=True
    r=m.separar_watershed(a,100,1)
    assert r.resumen['numero_objetos']>=2
    assert np.all(r.datos['etiquetas'][a]>0)
    assert not r.datos['etiquetas'][~a].any()


def test_watershed_marcadores_y_vacia():
    a=np.zeros((15,20),bool);a[3:12,2:18]=True
    seeds=np.zeros(a.shape,np.int32);seeds[7,5]=7;seeds[7,15]=19
    r=m.separar_watershed(a,3,1,marcadores=seeds)
    assert set(np.unique(r.datos['etiquetas']))=={0,7,19}
    np.testing.assert_array_equal(r.datos['marcadores'],seeds)
    z=m.separar_watershed(np.zeros((10,10),bool),2,1)
    assert z.resumen['numero_objetos']==0
    assert not z.datos['etiquetas'].any()
    with pytest.raises(ValueError):m.separar_watershed(a,3,1,marcadores=np.zeros_like(seeds))
    seeds[0,0]=5
    with pytest.raises(ValueError):m.separar_watershed(a,3,1,marcadores=seeds)


def test_limites_a_regiones_red_abierta():
    b=np.zeros((20,20),bool);b[4,4:16]=True;b[15,4:16]=True
    b[4:16,4]=True;b[4:16,15]=True
    r=m.limites_a_regiones(b,1)
    assert r.resumen['numero_objetos']==1
    assert r.datos['etiquetas'][10,10]>0
    assert r.datos['etiquetas'][0,0]==0
    b[4,9]=False
    assert m.limites_a_regiones(b,1).resumen['numero_objetos']==0


def test_clases_conservan_cero_y_no_identifican_fases(conjunto):
    r=m.segmentar_clases(conjunto['gris'])
    assert r.tipos['clases']=='clases'
    assert set(np.unique(r.datos['clases']))=={0,1,2}
    e=m.extraer_clase(r.datos['clases'],0)
    np.testing.assert_array_equal(e.datos['mascara'],r.datos['clases']==0)
    with pytest.raises(ValueError):m.segmentar_clases(conjunto['gris'],5)
    with pytest.raises(ValueError):m.segmentar_clases(np.ones((10,10)),2)


def test_dice_iou_con_oraculo():
    a=np.array([[1,1],[0,0]],bool);b=np.array([[1,0],[1,0]],bool)
    r=m.evaluar_mascara(a,b)
    assert r.resumen['dice']==0.5
    assert r.resumen['iou']==pytest.approx(1/3)
    assert r.resumen['falsos_positivos']==1
    assert m.evaluar_mascara(a,a).resumen['dice']==1
    z=np.zeros((2,2),bool)
    assert m.evaluar_mascara(z,z).resumen['iou']==1


def test_constantes_y_ruido_reproducible():
    a=np.full((16,16),0.5)
    r=m.variantes_contraste(a)
    for b in r.datos.values():np.testing.assert_array_equal(b,a)
    r1=m.agregar_ruido(a,0.03,42);r2=m.agregar_ruido(a,0.03,42)
    np.testing.assert_array_equal(r1.datos['con_ruido'],r2.datos['con_ruido'])
    for b in m.variantes_ruido(a).datos.values():assert np.isfinite(b).all()
    p=m.evaluar_referencia(a,a)
    assert p.resumen['psnr_db']==np.inf and p.resumen['ssim']==1


def test_no_cuantiza_filtro_media_a_ocho_bits():
    a=np.full((7,7),0.501)
    assert m.variantes_ruido(a).datos['media'][3,3]==pytest.approx(0.501,abs=1e-12)


def test_esqueleto_admite_entrada_inmutable(conjunto):
    a=conjunto['limites'];a.setflags(write=False)
    r=m.esqueletizar(a)
    assert r.datos['esqueleto'].dtype==bool

@pytest.mark.parametrize('llamada',[
    lambda a:m.detectar_canny(a,bajo=0.9,alto=0.1),
    lambda a:m.reescalar_percentiles(a,80,20),
    lambda a:m.variantes_contraste(a,clip_limit=0),
    lambda a:m.variantes_ruido(a,radio_px=0),
    lambda a:m.corregir_iluminacion(a,radio=0),
])
def test_parametros_invalidos(llamada,conjunto):
    with pytest.raises((ValueError,TypeError)):llamada(conjunto['gris'])
