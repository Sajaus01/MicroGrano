"""Datos artificiales para comprobar software; no son micrografías ni resultados."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
import tifffile
from .modelos import EscalaEspacial
from .sesion import Sesion
from .catalogo import CATALOGO
from .archivos import escribir_json


def crear_conjunto() -> dict[str,np.ndarray]:
    """Conjunto determinista: intensidades, máscaras, clases, instancias y valores."""
    r,c = np.mgrid[:128,:160]
    mascara = ((r-64)**2+(c-56)**2<25**2)|((r-64)**2+(c-91)**2<25**2)
    mascara[:9,126:143] = True
    mascara[7:11,9:13] = True
    imagen = np.clip(0.12+0.65*mascara+0.12*c/159+0.015*np.sin(r/4),0,1)
    rgb = np.stack([imagen,np.clip(imagen*0.95+0.02,0,1),
                    np.clip(imagen*0.9+0.025,0,1)],axis=-1)
    rgb = np.rint(rgb*255).astype(np.uint8)
    etiquetas = np.zeros((128,160),np.int32)
    etiquetas[10:31,15:39]=1
    etiquetas[43:83,26:63]=3
    etiquetas[56:102,91:141]=8
    etiquetas[:8,125:139]=12
    limites = np.zeros((128,160),bool)
    limites[[32,64,96],:]=True
    limites[:,[40,80,120]]=True
    clases = np.digitize(imagen,[0.20,0.55]).astype(np.int32)
    marcadores = np.zeros((128,160),np.int32)
    marcadores[64,56]=1;marcadores[64,91]=2;marcadores[4,134]=3;marcadores[8,10]=4
    return {'gris':imagen,'rgb':rgb,'mascara':mascara,'etiquetas':etiquetas,
        'limites':limites,'clases':clases,'marcadores':marcadores,
        'valores':np.array([0.21,0.25,0.24,0.19,0.22,0.27],float)}


def poblar_sesion(sesion: Sesion) -> dict[str,str]:
    """Añade entradas sintéticas identificadas como tales, con escala convencional."""
    conjunto = crear_conjunto()
    tipos = {'gris':'gris','rgb':'imagen','mascara':'mascara','etiquetas':'etiquetas',
             'limites':'limites','clases':'clases','marcadores':'marcadores','valores':'valores'}
    ids = {}
    for nombre,a in conjunto.items():
        id_ = sesion.agregar(a,tipos[nombre],f'Sintético / {nombre}',{
            'procedencia':'Generador determinista de MicroGrano; no es una micrografía.',
            'sintetico':True})
        sesion.confirmar_roi(id_,'Dato sintético: sin barra de escala ni anotaciones incrustadas.')
        if a.ndim>=2:
            sesion.establecer_escala(id_,EscalaEspacial(0.5,referencia='Convención sintética de prueba; no calibración instrumental.'))
        ids[nombre] = id_
    for nombre in ('mascara','clases','marcadores'):
        sesion.artefactos[ids[nombre]].metadatos['raiz'] = ids['gris']
    return ids


def casos_catalogo(ids: dict[str,str]) -> dict[str,tuple[dict,dict]]:
    """Entradas válidas de demostración para cada operación pública; no flujo único."""
    casos = {}
    for nombre,op in CATALOGO.items():
        entradas = {}
        for e in op.entradas:
            if e.opcional:
                continue
            rol = e.nombre
            if rol in ('imagen','referencia','candidata'):
                fuente = 'mascara' if nombre=='evaluar_mascara' else 'gris'
                if nombre in ('convertir_grises','separar_canales','explorar_imagen'):
                    fuente='rgb'
            else:
                fuente=rol
            entradas[rol]=ids[fuente]
        p = {}
        if nombre=='extraer_roi':p=dict(r0=8,r1=120,c0=8,c1=152)
        if nombre=='perfil_intensidad':p=dict(r0=25.0,c0=4.0,r1=88.0,c1=140.0)
        if nombre=='calibrar_escala':p=dict(referencia_um=50.0,referencia_px=100.0,referencia='Referencia sintética')
        if nombre=='convertir_medidas':p=dict(s_um_px=0.5,longitud_px=25.0,area_px2=100.0)
        if nombre=='corregir_iluminacion':p=dict(radio=6.0)
        if nombre=='top_hat':p=dict(radio_px=4)
        if nombre=='separar_watershed':p=dict(min_distance=10,area_minima=20)
        if nombre=='segmentar_clases':p=dict(clases=3)
        if nombre in ('intervalo_bootstrap_media','reporte_fraccion_area'):
            p=dict(repeticiones=1000,semilla=2026)
        casos[nombre]=(entradas,p)
    return casos


def demostrar_catalogo() -> tuple[Sesion,dict]:
    """Ejecuta las 39 operaciones sobre datos apropiados y conserva cada rama."""
    s = Sesion('Verificación sintética del catálogo completo')
    ids = poblar_sesion(s)
    informe = {'tipo':'Prueba de ejecución, no validación metalográfica','operaciones':[]}
    for nombre,(entradas,p) in casos_catalogo(ids).items():
        r,salidas = s.ejecutar(nombre,entradas,p)
        informe['operaciones'].append({'funcion':nombre,'ejecutada':True,
            'salidas':list(salidas),'filas_tabla':len(r.tabla)})
    informe['total'] = len(informe['operaciones'])
    return s,informe


def guardar_conjunto(carpeta: str | Path) -> None:
    """Escribe el conjunto artificial y su ficha, sin incorporar datos privados."""
    p=Path(carpeta)
    p.mkdir(parents=True,exist_ok=True)
    datos=crear_conjunto()
    for nombre,a in datos.items():
        if (p/(nombre+'.npy')).exists():
            raise FileExistsError('El conjunto ya existe; no se sobrescribe.')
        np.save(p/(nombre+'.npy'),a,allow_pickle=False)
    Image.fromarray(datos['rgb']).save(p/'imagen_sintetica_rgb.png')
    Image.fromarray(np.rint(datos['gris']*65535).astype(np.uint16)).save(p/'imagen_sintetica_16bits.tif')
    Image.fromarray(datos['mascara'].astype(np.uint8)*255).save(p/'mascara_sintetica.png')
    tifffile.imwrite(p/'etiquetas_sinteticas.tif',datos['etiquetas'])
    pd.DataFrame({'campo':[f'campo_{i+1}' for i in range(6)],'fraccion_area':datos['valores']}).to_csv(
        p/'campos_sinteticos.csv',index=False)
    escribir_json(p/'procedencia.json',{'origen':'Generados por micrograno.sinteticos.crear_conjunto',
        'sinteticos':True,'uso':'Comprobar el software; no investigación metalográfica.',
        'escala_convencional_um_px':0.5,'advertencia':'La escala es una convención numérica, no una calibración de microscopio.'})
