"""Máscaras, clases e instancias son salidas distintas y no intercambiables."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from skimage import filters, feature, measure, segmentation
from . import _validacion as v
from .modelos import Resultado
from .preprocesamiento import limpiar_mascara


def umbralizar(imagen: np.ndarray, manual: float = 0.5, bloque: int = 51,
               desplazamiento: float = 0.02, polaridad: str = 'clara') -> Resultado:
    """Compara umbral manual, Otsu y media local. Clara: I>T; oscura: I<=T."""
    a = v.gris(imagen)
    manual = v.real(manual,'manual',0,1)
    bloque = v.entero(bloque,'bloque',3,2001)
    if bloque % 2 != 1:
        raise ValueError('La ventana local debe tener un número impar de píxeles.')
    desplazamiento = v.real(desplazamiento,'desplazamiento',-1,1)
    v.opcion(polaridad,('clara','oscura'),'polaridad')
    if np.ptp(a) == 0:
        raise ValueError('La imagen es constante; no se puede interpretar una separación de intensidades.')
    t = float(filters.threshold_otsu(a))
    local = filters.threshold_local(a,block_size=bloque,method='mean',offset=desplazamiento)
    d = {n:(a>u if polaridad == 'clara' else a<=u)
         for n,u in [('manual',manual),('otsu',t),('adaptativa',local)]}
    tipos = dict.fromkeys(d,'mascara')
    d['umbral_local'] = local
    tipos['umbral_local'] = 'mapa'
    return Resultado(d,tipos,resumen={'umbral_otsu':t,'umbral_manual':manual,
        'polaridad':polaridad,'regla_igualdad':'La igualdad pertenece a la clase oscura.'})


def detectar_canny(imagen: np.ndarray, sigma: float = 1.0,
                  bajo: float = 0.08, alto: float = 0.18) -> Resultado:
    """Detecta transiciones; devuelve límites candidatos, no objetos etiquetados."""
    a = v.gris(imagen)
    sigma = v.real(sigma,'sigma',0)
    bajo,alto = v.real(bajo,'bajo',0,1),v.real(alto,'alto',0,1)
    if bajo >= alto:
        raise ValueError('El umbral bajo debe ser menor que el alto.')
    b = feature.canny(a,sigma=sigma,low_threshold=bajo,high_threshold=alto)
    return Resultado({'canny':b},{'canny':'limites'},advertencias=[
        'Canny puede detectar ambos lados de un surco. No convierta el número de trazos en número de granos.'])


def etiquetar_componentes(mascara: np.ndarray, conectividad: int = 2) -> Resultado:
    """Etiqueta componentes conexas: 1 indica cuatro vecinos; 2, ocho vecinos."""
    a = v.mascara(mascara)
    c = v.entero(conectividad,'conectividad',1,2)
    e = measure.label(a,connectivity=c).astype(np.int32)
    return Resultado({'etiquetas':e},{'etiquetas':'etiquetas'},resumen={
        'numero_objetos':int(e.max()),'conectividad':c},advertencias=[
        'Un componente conexo solo es un grano cuando su delimitación se ha verificado.'])


def limites_a_regiones(limites: np.ndarray, area_minima: int = 20,
                       excluir_abiertas: bool = True,
                       conectividad: int = 1) -> Resultado:
    """Etiqueta el complemento de una red; puede excluir regiones que llegan al marco.

    No rellena huecos de la red ni inventa uniones. Una abertura real puede comunicar
    varios interiores y producir una sola región; se muestra para revisión.
    """
    a = v.mascara(limites)
    if not a.any():
        raise ValueError('No hay límites; no se puede inferir una red de granos.')
    c = v.entero(conectividad,'conectividad',1,2)
    b = limpiar_mascara(~a,area_minima=area_minima,conectividad=c).datos['limpia']
    e = measure.label(b,connectivity=c).astype(np.int32)
    abiertas = np.unique(np.concatenate([e[0],e[-1],e[:,0],e[:,-1]]))
    removidas = np.isin(e,abiertas[abiertas>0])
    if excluir_abiertas:
        e = np.where(removidas,0,e)
    return Resultado({'etiquetas':e,'regiones_en_marco':removidas},
        {'etiquetas':'etiquetas','regiones_en_marco':'mascara'},resumen={
        'numero_objetos':len(np.unique(e[e>0])), 'excluir_abiertas':bool(excluir_abiertas),
        'conectividad':c},advertencias=[
        'Excluir regiones en el marco puede eliminar granos válidos truncados. No es un estimador insesgado de densidad.',
        'Una red abierta o un rayón puede fusionar o dividir regiones. Revise la superposición.'])


def separar_watershed(mascara: np.ndarray, min_distance: int = 12,
                      area_minima: int = 20, conectividad: int = 2,
                      marcadores: np.ndarray | None = None) -> Resultado:
    """Separa una máscara explícita por distancia y marcadores; no umbraliza a escondidas.

    Marcadores opcionales: enteros no negativos, cero sin semilla. Cada componente
    debe contener una semilla. Sin marcadores se generan picos y se añade un máximo
    a cualquier componente sin pico, incluidos los que tocan el marco.
    """
    a = v.mascara(mascara)
    c = v.entero(conectividad,'conectividad',1,2)
    dist_min = v.entero(min_distance,'min_distance',1,10000)
    limpia = limpiar_mascara(a,area_minima=area_minima,conectividad=c).datos['limpia']
    estructura = ndi.generate_binary_structure(2,c)
    componentes,n = ndi.label(limpia,structure=estructura)
    # El exterior de la ROI se trata como fondo para definir la distancia en el marco.
    distancia = ndi.distance_transform_edt(np.pad(limpia,1))[1:-1,1:-1]
    agregadas = 0
    if marcadores is None:
        m = np.zeros(a.shape,dtype=np.int32)
        if n:
            picos = feature.peak_local_max(distancia,labels=componentes,
                min_distance=dist_min,exclude_border=False)
            for k,(r,col) in enumerate(picos,1):
                m[r,col] = k
            presentes = set(np.unique(componentes[m>0]))
            siguiente_id = len(picos) + 1
            for k,sl in enumerate(ndi.find_objects(componentes),1):
                if k in presentes:
                    continue
                local = np.where(componentes[sl] == k,distancia[sl],-1)
                rr,cc = np.unravel_index(np.argmax(local),local.shape)
                m[rr+sl[0].start,cc+sl[1].start] = siguiente_id
                siguiente_id += 1
                agregadas += 1
    else:
        m = v.etiquetas(marcadores)
        v.misma_forma(limpia,m)
        if np.any((m>0)&~limpia):
            raise ValueError('Los marcadores deben estar dentro de la máscara que supera el filtro de área.')
        presentes = np.unique(componentes[m>0])
        if set(presentes) != set(range(1,n+1)):
            raise ValueError('Cada componente de la máscara necesita al menos un marcador.')
        for k in np.unique(m[m>0]):
            if ndi.label(m == k,structure=estructura)[1] != 1:
                raise ValueError('Cada identificador de marcador debe formar una región conexa.')
    e = (segmentation.watershed(-distancia,m,mask=limpia,connectivity=estructura)
         if n else np.zeros(a.shape,dtype=np.int32))
    limites = segmentation.find_boundaries(e,connectivity=c,mode='thick')
    return Resultado({'mascara':limpia,'distancia':distancia,'marcadores':m,
        'etiquetas':e.astype(np.int32),'limites':limites},
        {'mascara':'mascara','distancia':'mapa','marcadores':'marcadores',
         'etiquetas':'etiquetas','limites':'limites'},resumen={
        'numero_objetos':len(np.unique(e[e>0])), 'numero_marcadores':len(np.unique(m[m>0])),
        'marcadores_automaticos_rescate':agregadas,'min_distance_px':dist_min,
        'conectividad':c,'marcadores_proporcionados':marcadores is not None},
        advertencias=['La geometría de distancia puede no coincidir con granos reales; revise las semillas y las separaciones.'])


def segmentar_clases(imagen: np.ndarray, clases: int = 3) -> Resultado:
    """Multi-Otsu: clases de intensidad 0..K-1, sin identidad metalúrgica asignada."""
    a = v.gris(imagen)
    k = v.entero(clases,'clases',2,4)
    if len(np.unique(a)) < k:
        raise ValueError('Hay menos intensidades distintas que clases solicitadas.')
    u = filters.threshold_multiotsu(a,classes=k,nbins=256)
    e = np.digitize(a,u).astype(np.int32)
    return Resultado({'clases':e},{'clases':'clases'},resumen={
        'umbrales':u.tolist(),'numero_clases':k},advertencias=[
        'Las clases son intervalos de intensidad, no fases identificadas. La clase cero es medible.'])


def extraer_clase(clases: np.ndarray, clase: int = 0) -> Resultado:
    """Extrae una clase como máscara sin unirla semánticamente a las otras clases."""
    a = v.etiquetas(clases,clases=True)
    k = v.entero(clase,'clase',0)
    if k not in a:
        raise ValueError('La clase solicitada no está presente.')
    return Resultado({'mascara':a == k},{'mascara':'mascara'},resumen={'clase':k})


def obtener_limites(etiquetas: np.ndarray, conectividad: int = 2,
                    modo: str = 'thick') -> Resultado:
    """Obtiene la representación de contornos de instancias ya etiquetadas."""
    a = v.etiquetas(etiquetas)
    c = v.entero(conectividad,'conectividad',1,2)
    v.opcion(modo,('thick','inner','outer'),'modo')
    b = segmentation.find_boundaries(a,connectivity=c,mode=modo)
    return Resultado({'limites':b},{'limites':'limites'},resumen={'modo':modo},
        advertencias=['Incluye interfaces con fondo. El grosor y los contactos afectan los conteos de intersecciones.'])


def evaluar_mascara(referencia: np.ndarray, candidata: np.ndarray) -> Resultado:
    """Compara máscaras binarias alineadas mediante conteos, Dice e IoU."""
    a,b = v.mascara(referencia),v.mascara(candidata)
    v.misma_forma(a,b)
    tp = int(np.sum(a&b)); fp = int(np.sum(~a&b)); fn = int(np.sum(a&~b))
    tn = int(np.sum(~a&~b)); union = tp+fp+fn
    return Resultado({'falsos_positivos':~a&b,'falsos_negativos':a&~b},
        {'falsos_positivos':'mascara','falsos_negativos':'mascara'},resumen={
        'verdaderos_positivos':tp,'falsos_positivos':fp,'falsos_negativos':fn,
        'verdaderos_negativos':tn,'iou':tp/union if union else 1.0,
        'dice':2*tp/(2*tp+fp+fn) if union else 1.0,
        'convencion_vacias':'Dos máscaras vacías reciben Dice=IoU=1.'},advertencias=[
        'Una referencia no independiente no prueba exactitud. Dice e IoU de píxeles no evalúan por sí solos el conteo de instancias.'])
