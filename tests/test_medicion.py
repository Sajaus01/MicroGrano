import numpy as np
import pytest
from micrograno import nucleo as m


def test_area_escala_e_identificadores():
    a=np.zeros((20,20),np.int32);a[3:6,4:8]=42
    r=m.propiedades_basicas(a,0.5)
    f=r.tabla.iloc[0]
    assert f.etiqueta==42 and f.area_px2==12 and f.area_um2==3
    assert f.centroide_fila_px==4 and f.centroide_columna_px==5.5
    assert not f.toca_marco
    np.testing.assert_array_equal(r.datos['etiquetas'],a)


def test_etiquetas_escasas_no_se_renumeran():
    a=np.zeros((20,20),np.int32);a[2:7,2:7]=1_000_000
    t=m.descriptores_forma(a,2).tabla
    assert t.etiqueta.iloc[0]==1_000_000
    assert t.area_um2.iloc[0]==100
    assert t.diametro_equivalente_um.iloc[0]==pytest.approx(2*np.sqrt(100/np.pi))
    assert t.relacion_aspecto.iloc[0]==1


def test_etiqueta_desconectada_no_es_instancia():
    a=np.zeros((20,20),np.int32);a[2:4,2:4]=1;a[12:15,12:15]=1
    with pytest.raises(ValueError,match='desconectadas'):m.propiedades_basicas(a,1)


def test_filtrado_no_fusiona_etiquetas_adyacentes():
    a=np.zeros((15,20),np.int32);a[3:10,3:8]=3;a[3:10,8:13]=8
    r=m.medir_objetos(a,1,area_minima=35,regla_marco='conservar')
    assert r.resumen['numero_objetos_aceptados']==2
    assert set(np.unique(r.datos['aceptadas']))=={0,3,8}
    assert r.resumen['numero_objetos_descartados']==0


def test_filtro_marco_y_fracciones_separadas():
    a=np.zeros((20,20),np.int32);a[:3,2:5]=1;a[8:11,8:11]=2
    r=m.medir_objetos(a,1,1,'excluir')
    assert r.resumen['numero_objetos_aceptados']==1
    assert r.resumen['fraccion_area_entrada']==18/400
    assert r.resumen['fraccion_area_aceptada']==9/400
    assert r.tabla.loc[r.tabla.etiqueta==1,'motivo'].iloc[0]=='toca el marco'


def test_ponderacion_planimetrica_formula_declarada():
    a=np.zeros((20,20),np.int32);a[:2,2:4]=2;a[8:11,8:11]=3
    r=m.densidad_jeffries(a,0.5)
    assert r.resumen['interiores']==1 and r.resumen['en_marco']==1
    assert r.resumen['conteo_ponderado']==1.5
    assert r.resumen['area_roi_mm2']==pytest.approx(1e-4)
    assert r.resumen['densidad_ponderada_mm2']==pytest.approx(15000)
    assert 'ASTM' in ' '.join(r.advertencias)


def test_fracciones_cero_y_roi():
    a=np.array([[0,0,1],[1,2,2]],np.int32)
    r=m.fracciones_area(a)
    np.testing.assert_allclose(r.tabla.fraccion_area,[1/3]*3)
    roi=np.array([[1,1,1],[1,0,0]],bool)
    r=m.fracciones_area(a,roi)
    assert list(r.tabla.clase)==[0,1]
    np.testing.assert_allclose(r.tabla.fraccion_area,[0.5,0.5])
    assert r.resumen['pixeles_roi']==4
    with pytest.raises(ValueError):m.fracciones_area(a,np.zeros_like(a,bool))


def test_intercepcion_corridas_y_longitud_entre_centros():
    a=np.zeros((20,20),bool);a[:,4:6]=True;a[:,12]=True
    r=m.intercepto_medio(a,0.5,2,'horizontal','excluir')
    assert r.resumen['intersecciones_totales']==4
    assert r.resumen['longitud_total_um']==19
    assert r.resumen['longitud_media_um']==4.75
    assert r.tabla.intersecciones.tolist()==[2,2]
    a[:,0]=True
    excl=m.intercepto_medio(a,0.5,2,'horizontal','excluir')
    inc=m.intercepto_medio(a,0.5,2,'horizontal','incluir')
    assert excl.resumen['intersecciones_totales']==4
    assert inc.resumen['intersecciones_totales']==6
    assert excl.tabla.corridas_extremas_excluidas.sum()==2


def test_intercepcion_vacia_y_lineas_sin_duplicados():
    r=m.intercepto_medio(np.zeros((10,10),bool),1,3)
    assert r.resumen['longitud_media_um'] is None
    for _,g in r.tabla.groupby('orientacion'):
        assert len(g.posicion_px.unique())==3
    with pytest.raises(ValueError):m.intercepto_medio(np.zeros((3,3),bool),1,8)

@pytest.mark.parametrize('funcion',[m.propiedades_basicas,m.descriptores_forma,m.densidad_jeffries,m.medir_objetos])
def test_mediciones_vacias_y_escala_invalida(funcion):
    a=np.zeros((8,8),np.int32)
    r=funcion(a,1)
    assert r.tabla.empty
    with pytest.raises(ValueError):funcion(a,0)


def test_descriptor_indefinido_no_es_cero():
    a=np.zeros((5,5),np.int32);a[2,2]=1
    r=m.descriptores_forma(a,1)
    assert np.isnan(r.tabla.circularidad.iloc[0])
    assert np.isnan(r.tabla.relacion_aspecto.iloc[0])


def test_bootstrap_determinista_y_constante():
    a=np.array([1.,2.,3.,4.])
    r=m.intervalo_bootstrap_media(a,1000,99)
    b=m.intervalo_bootstrap_media(a,1000,99)
    np.testing.assert_array_equal(r.datos['medias_remuestreadas'],b.datos['medias_remuestreadas'])
    assert r.resumen['media']==2.5
    assert r.resumen['desviacion_estandar_muestral']==pytest.approx(np.std(a,ddof=1))
    k=m.intervalo_bootstrap_media(np.ones(5),100)
    assert k.resumen['intervalo_percentil']==[1.,1.]

@pytest.mark.parametrize('a',[[1.],[],[1.,np.nan],[1.,np.inf]])
def test_bootstrap_rechaza_vector_invalido(a):
    with pytest.raises(ValueError):m.intervalo_bootstrap_media(np.array(a))


def test_fracciones_no_acepta_porcentajes():
    with pytest.raises(ValueError):m.reporte_fraccion_area(np.array([10.,20.]))
    r=m.reporte_fraccion_area(np.array([0.1,0.2,0.3]),100)
    assert r.resumen['media']==pytest.approx(0.2)
