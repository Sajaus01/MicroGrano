import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
import pandas as pd
from PIL import Image
import pytest
import tifffile
from micrograno import Sesion, EscalaEspacial, nucleo as m
from micrograno.archivos import (cargar_imagen,cargar_mascara,cargar_etiquetas,
    cargar_valores,guardar_resultado,exportar_figura,metadatos_entorno)
from micrograno.sinteticos import demostrar_catalogo, poblar_sesion
from micrograno.visualizacion import preparar_vista


def test_sesion_calibracion_y_roi_obligatorias():
    s=Sesion();id_=s.agregar(np.eye(20),'gris','prueba')
    with pytest.raises(ValueError,match='Confirme'):
        s.ejecutar('histograma_percentiles',{'imagen':id_})
    s.confirmar_roi(id_,'Prueba sintética sin anotaciones')
    _,z=s.ejecutar('umbralizar',{'imagen':id_},{'bloque':3})
    _,z=s.ejecutar('etiquetar_componentes',{'mascara':z['manual']})
    with pytest.raises(ValueError,match='calibración'):
        s.ejecutar('propiedades_basicas',{'etiquetas':z['etiquetas']},{'s_um_px':1})
    s.establecer_escala(z['etiquetas'],EscalaEspacial(2))
    r,_=s.ejecutar('propiedades_basicas',{'etiquetas':z['etiquetas']})
    assert r.resumen['s_um_px']==2
    with pytest.raises(ValueError,match='no coincide'):
        s.ejecutar('propiedades_basicas',{'etiquetas':z['etiquetas']},{'s_um_px':3})
    nuevo=s.agregar(np.zeros((20,20),np.uint8),'imagen','otra imagen')
    assert s.artefactos[nuevo].metadatos['escala'] is None
    assert not s.artefactos[nuevo].metadatos['roi_confirmada']


def test_copia_fuente_y_recorte_no_destructivo():
    a=np.arange(100,dtype=np.uint8).reshape(10,10)
    s=Sesion();id_=s.agregar(a,'imagen','original')
    a[:]=0
    assert s.artefactos[id_].datos.max()==99
    s.establecer_escala(id_,EscalaEspacial(0.5))
    _,out=s.ejecutar('extraer_roi',{'imagen':id_},dict(r0=2,r1=8,c0=3,c1=9))
    roi=s.artefactos[out['roi']]
    assert roi.metadatos['origen_rc']==[2,3]
    assert roi.metadatos['escala']['um_por_px']==0.5
    assert not roi.metadatos['roi_confirmada']
    assert s.artefactos[id_].datos.shape==(10,10)


def test_muestreo_invalida_escala():
    s=Sesion();ids=poblar_sesion(s)
    _,out=s.ejecutar('reducir_y_ampliar',{'imagen':ids['gris']})
    assert all(s.artefactos[x].metadatos['escala'] is None for x in out.values())


def test_guardar_abrir_recalcular_catalogo_y_codigo(tmp_path):
    s,inf=demostrar_catalogo()
    carpeta=tmp_path/'sesion'
    s.guardar(carpeta)
    recuperada=Sesion.abrir(carpeta)
    resultado=recuperada.reproducir()
    assert resultado['coincide'],resultado['diferencias']
    assert resultado['pasos_recalculados']==39
    script=carpeta/'reproducir.py'
    ast.parse(script.read_text(encoding='utf-8'))
    salida=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,timeout=45)
    assert salida.returncode==0,salida.stderr
    assert (carpeta/'salidas_reproducidas'/'paso_039'/'resultado.json').is_file()
    with pytest.raises(FileExistsError):s.guardar(carpeta)


def test_dano_dato_se_detecta(tmp_path):
    s=Sesion();id_=s.agregar(np.eye(5),'gris','prueba')
    carpeta=tmp_path/'s';s.guardar(carpeta)
    np.save(carpeta/'datos'/f'{id_}.npy',np.zeros((5,5)))
    with pytest.raises(ValueError,match='Hash incorrecto'):Sesion.abrir(carpeta)


def test_sesion_rechaza_rutas_fuera_de_carpeta(tmp_path):
    s=Sesion();s.agregar(np.eye(5),'gris','prueba')
    carpeta=tmp_path/'s';s.guardar(carpeta)
    p=carpeta/'sesion.json';registro=json.loads(p.read_text())
    registro['artefactos'][0]['archivo']='../../otro.npy'
    p.write_text(json.dumps(registro))
    with pytest.raises(ValueError,match='Ruta'):Sesion.abrir(carpeta)


def test_asociacion_fuente_y_superposicion():
    s=Sesion();ids=poblar_sesion(s)
    s.asociar_fuente(ids['etiquetas'],ids['gris'],'Misma rejilla sintética')
    vista=preparar_vista(s.artefactos[ids['etiquetas']],s,True,True)
    assert vista['imagen'].shape==(128,160)
    assert vista['contornos'] is not None
    assert {x[2] for x in vista['rotulos']}=={'1','3','8','12'}


def test_imagen_uint16_y_etiquetas_tiff(tmp_path):
    a=np.array([[0,1000],[2000,65535]],np.uint16)
    p=tmp_path/'imagen.tif';tifffile.imwrite(p,a)
    np.testing.assert_array_equal(cargar_imagen(p),a)
    e=np.array([[0,17],[90,90]],np.int32)
    q=tmp_path/'etiquetas.tif';tifffile.imwrite(q,e)
    np.testing.assert_array_equal(cargar_etiquetas(q),e)


def test_importacion_mascaras_explicitas_y_pickle_bloqueado(tmp_path):
    p=tmp_path/'mascara.png';Image.fromarray(np.array([[0,255],[255,0]],np.uint8)).save(p)
    assert cargar_mascara(p).dtype==bool
    Image.fromarray(np.array([[0,75],[255,0]],np.uint8)).save(p)
    with pytest.raises(ValueError):cargar_mascara(p)
    q=tmp_path/'objeto.npy';np.save(q,np.array([{'mal':'dato'}],dtype=object))
    with pytest.raises(ValueError):cargar_imagen(q)


def test_csv_no_descarta_datos_faltantes(tmp_path):
    p=tmp_path/'campos.csv';pd.DataFrame({'fraccion':[0.1,0.2,0.3]}).to_csv(p,index=False)
    np.testing.assert_allclose(cargar_valores(p,'fraccion'),[0.1,0.2,0.3])
    with pytest.raises(ValueError):cargar_valores(p,'no_existe')
    pd.DataFrame({'fraccion':[0.1,np.nan,0.3]}).to_csv(p,index=False)
    with pytest.raises(ValueError):cargar_valores(p,'fraccion')


def test_exportacion_resultado_y_json_estricto(tmp_path):
    a=np.full((10,10),0.5)
    r=m.evaluar_referencia(a,a)
    p=guardar_resultado(r,tmp_path/'r')
    datos=json.loads((p/'resultado.json').read_text())
    assert datos['resumen']['psnr_db']=='+Infinity'
    assert datos['datos']['ssim_local']['tipo']=='mapa'
    with pytest.raises(FileExistsError):guardar_resultado(r,p)

@pytest.mark.parametrize('extension',['.jpg','.tif'])
def test_figura_editorial_gris_y_ficha(tmp_path,extension):
    a=np.linspace(0,1,600).reshape(20,30)
    p=tmp_path/('figura'+extension)
    ficha=exportar_figura(a,p,titulo='Prueba sintética',descripcion='Rampa artificial.',fuente='Generación sintética para prueba.')
    with Image.open(p) as im:
        assert im.mode=='L'
        assert im.info['dpi'][0]>=299
    assert ficha['texto_minimo_pt']>=11
    assert p.with_suffix(extension+'.json').exists()


def test_entorno_reporta_micrograno_instalado():
    datos=metadatos_entorno()
    assert datos['python']
    assert datos['paquetes']['scikit-image']


def test_anotaciones_y_documentacion_calibracion(tmp_path):
    s=Sesion();id_=s.agregar(np.eye(10),'gris','prueba')
    s.anotar(id_,{'campo_id':'C01','material_declarado':''})
    s.establecer_escala(id_,EscalaEspacial(0.5),{'extremos_rc':[1,1,1,9]})
    s.guardar(tmp_path/'s');n=Sesion.abrir(tmp_path/'s')
    assert n.artefactos[id_].metadatos['anotaciones']['campo_id']=='C01'
    assert n.artefactos[id_].metadatos['calibracion_documentacion']['extremos_rc']==[1,1,1,9]
    x=s.agregar(np.array([1.,2.]),'valores','campos')
    with pytest.raises(ValueError):s.establecer_escala(x,EscalaEspacial(1))


def test_reproduccion_fuentes_importadas_entre_pasos(tmp_path):
    s=Sesion();uno=s.agregar(np.eye(20),'gris','imagen_uno')
    s.confirmar_roi(uno,'Prueba sintética')
    s.ejecutar('cuantizar',{'imagen':uno})
    dos=s.agregar(np.fliplr(np.eye(20)),'gris','imagen_dos')
    s.confirmar_roi(dos,'Prueba sintética')
    _,out=s.ejecutar('cuantizar',{'imagen':dos})
    s.ejecutar('histograma_percentiles',{'imagen':out['cuantizada']})
    info=s.reproducir(tmp_path/'recalculada')
    assert info['coincide']
    nueva=Sesion.abrir(tmp_path/'recalculada')
    dato=nueva.artefactos[nueva.pasos[1]['salidas']['cuantizada']]
    raiz=nueva.artefactos[dato.metadatos['raiz']]
    assert raiz.nombre=='imagen_dos'
