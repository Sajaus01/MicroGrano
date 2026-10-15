"""Transformaciones de intensidad y máscaras, sin selección automática de la mejor."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from skimage import exposure, filters, morphology, restoration, metrics
from . import _validacion as v
from .modelos import Resultado


def _estirar(a, p_bajo, p_alto):
    p_bajo = v.real(p_bajo,'p_bajo',0,100)
    p_alto = v.real(p_alto,'p_alto',0,100)
    if p_bajo >= p_alto:
        raise ValueError('El percentil inferior debe ser menor que el superior.')
    bajo, alto = np.percentile(a,[p_bajo,p_alto])
    if alto <= bajo:
        return a.copy(), float(bajo), float(alto)
    return np.clip((a-bajo)/(alto-bajo),0,1), float(bajo), float(alto)


def reescalar_percentiles(imagen: np.ndarray, p_bajo: float = 2.0,
                          p_alto: float = 98.0) -> Resultado:
    """Estira el contraste; si los percentiles coinciden, conserva la entrada."""
    a = v.gris(imagen)
    b, inferior, superior = _estirar(a,p_bajo,p_alto)
    return Resultado({'estirada':b},{'estirada':'gris'},resumen={
        'intensidad_inferior':inferior,'intensidad_superior':superior,
        'p_bajo':p_bajo,'p_alto':p_alto},advertencias=(
            ['Percentiles coincidentes: se conservó la entrada sin estiramiento.']
            if inferior == superior else ['Se saturan las intensidades fuera de los percentiles elegidos.']))


def variantes_contraste(imagen: np.ndarray, p_bajo: float = 2.0,
                       p_alto: float = 98.0, tile: int = 64,
                       clip_limit: float = 0.02) -> Resultado:
    """Compara percentiles, ecualización global y CLAHE sobre la misma entrada."""
    a = v.gris(imagen)
    tile = v.entero(tile,'tile',2,4096)
    clip_limit = v.real(clip_limit,'clip_limit',0,1,positivo=True)
    est = reescalar_percentiles(a,p_bajo,p_alto)
    if a.min() == a.max():
        global_, local = a.copy(), a.copy()
    else:
        global_ = exposure.equalize_hist(a)
        local = exposure.equalize_adapthist(a,kernel_size=tile,clip_limit=clip_limit)
    d = {'estirada':est.datos['estirada'],'ecualizacion_global':global_,'clahe':local}
    return Resultado(d,dict.fromkeys(d,'gris'),resumen=est.resumen,
        advertencias=['CLAHE puede amplificar textura y ruido. Los parámetros iniciales no están validados para su material.'])


def variantes_ruido(imagen: np.ndarray, radio_px: int = 1,
                   sigma: float = 1.0, sigma_color: float = 0.08,
                   sigma_spatial: float = 3.0) -> Resultado:
    """Media en disco, gaussiano, mediana y bilateral sin cuantización a 8 bits."""
    a = v.gris(imagen)
    r = v.entero(radio_px,'radio_px',1,100)
    sigma = v.real(sigma,'sigma',positivo=True)
    sc = v.real(sigma_color,'sigma_color',positivo=True)
    ss = v.real(sigma_spatial,'sigma_spatial',positivo=True)
    f = morphology.disk(r).astype(float)
    media = ndi.convolve(a, f/f.sum(), mode='reflect')
    d = {'media':media, 'gaussiano':filters.gaussian(a,sigma=sigma,preserve_range=True),
         'mediana':ndi.median_filter(a,footprint=f.astype(bool),mode='reflect'),
         'bilateral':restoration.denoise_bilateral(a,sigma_color=sc,
                        sigma_spatial=ss,channel_axis=None)}
    return Resultado(d,dict.fromkeys(d,'gris'),resumen={'radio_media_mediana_px':r},
        advertencias=['Los filtros no distinguen ruido de rasgos metalográficos pequeños.'])


def agregar_ruido(imagen: np.ndarray, sigma: float = 0.03,
                 semilla: int = 2026) -> Resultado:
    """Añade ruido gaussiano sintético con semilla y recorta a [0,1]."""
    a = v.gris(imagen)
    sigma = v.real(sigma,'sigma',0,1)
    semilla = v.entero(semilla,'semilla',0)
    b = a + np.random.default_rng(semilla).normal(0,sigma,a.shape)
    recortados = int(np.count_nonzero((b < 0)|(b > 1)))
    return Resultado({'con_ruido':np.clip(b,0,1)},{'con_ruido':'gris'},
        resumen={'sigma':sigma,'semilla':semilla,'pixeles_recortados':recortados},
        advertencias=['Prueba sintética; este ruido no representa un modelo verificado de la cámara.'])


def evaluar_referencia(referencia: np.ndarray, candidata: np.ndarray) -> Resultado:
    """PSNR y SSIM sobre imágenes alineadas con referencia conocida en [0,1]."""
    a,b = v.gris(referencia),v.gris(candidata)
    v.misma_forma(a,b)
    if min(a.shape) < 3:
        raise ValueError('SSIM requiere al menos 3 píxeles en cada dimensión.')
    ventana = min(7,min(a.shape))
    if ventana % 2 == 0:
        ventana -= 1
    mse = float(np.mean((a-b)**2))
    psnr = float('inf') if mse == 0 else float(10*np.log10(1/mse))
    ssim, mapa = metrics.structural_similarity(a,b,data_range=1.0,
                        win_size=ventana,full=True)
    return Resultado({'ssim_local':mapa},{'ssim_local':'mapa'},resumen={
        'psnr_db':psnr,'ssim':float(ssim),'error_cuadratico_medio':mse,
        'ventana_ssim':ventana,'data_range':1.0},advertencias=[
        'Estas métricas no validan límites de grano ni son medidas de enfoque. Se necesita una referencia independiente y alineada.'])


def corregir_iluminacion(imagen: np.ndarray, radio: float = 15.0) -> Resultado:
    """Bola rodante: fondo inferior y correcciones aditiva/divisiva normalizadas."""
    a = v.gris(imagen)
    radio = v.real(radio,'radio',1,200)
    fondo = restoration.rolling_ball(a,radius=radio)
    ad = np.maximum(a-fondo,0)
    seguro = np.maximum(fondo,np.finfo(float).eps)
    di = a/seguro * np.median(seguro)
    # Las correcciones se normalizan explícitamente; no se presentan como intensidades originales.
    ad_norm,lo,hi = _estirar(ad,2,98)
    di_norm,dlo,dhi = _estirar(di,2,98)
    d = {'fondo':fondo,'aditiva':np.clip(ad_norm,0,1),'divisiva':np.clip(di_norm,0,1)}
    return Resultado(d,dict.fromkeys(d,'gris'),resumen={
        'radio_px':radio,'percentiles_salida':[2,98],
        'limites_aditiva':[lo,hi],'limites_divisiva':[dlo,dhi],
        'pixeles_denominador_protegido':int(np.count_nonzero(fondo <= np.finfo(float).eps))},
        advertencias=['La bola rodante estima un fondo inferior para rasgos claros. Verifique la polaridad y la escala de los rasgos.',
        'La división cerca de cero puede amplificar artefactos. Un fondo oscuro o constante exige revisión.'])


def top_hat(imagen: np.ndarray, radio_px: int = 10) -> Resultado:
    """Residuos morfológicos claro (blanco) y oscuro (negro), sin asignarles fase."""
    a = v.gris(imagen)
    r = v.entero(radio_px,'radio_px',1,200)
    f = morphology.disk(r)
    d = {'claro':morphology.white_tophat(a,footprint=f),
         'oscuro':morphology.black_tophat(a,footprint=f)}
    return Resultado(d,dict.fromkeys(d,'gris'),advertencias=[
        'El radio decide qué estructuras se eliminan; el residuo no identifica el material.'])


def realzar_sobel(imagen: np.ndarray, sigma: float = 1.0) -> Resultado:
    """Derivadas en fila y columna y magnitud; respuestas firmadas no son intensidades."""
    a = v.gris(imagen)
    sigma = v.real(sigma,'sigma',0)
    suave = filters.gaussian(a,sigma=sigma,preserve_range=True)
    dr,dc = filters.sobel_h(suave),filters.sobel_v(suave)
    d = {'suavizada':suave,'derivada_fila':dr,'derivada_columna':dc,
         'magnitud':np.hypot(dr,dc)}
    return Resultado(d,{'suavizada':'gris','derivada_fila':'mapa',
        'derivada_columna':'mapa','magnitud':'mapa'},advertencias=[
        'Una transición de intensidad no demuestra la presencia de un límite de grano.'])


def variantes_morfologicas(mascara: np.ndarray, radio_px: int = 1) -> Resultado:
    """Compara cuatro operaciones sobre una máscara booleana con el mismo disco."""
    a = v.mascara(mascara)
    f = morphology.disk(v.entero(radio_px,'radio_px',1,200))
    d = {n:func(a,footprint=f) for n,func in [('erosion',morphology.erosion),
         ('dilatacion',morphology.dilation),('apertura',morphology.opening),
         ('cierre',morphology.closing)]}
    return Resultado(d,dict.fromkeys(d,'mascara'),resumen={'radio_px':radio_px},
        advertencias=['La morfología puede fusionar objetos o crear cierres que no existían en la imagen.'])


def limpiar_mascara(mascara: np.ndarray, area_minima: int = 20,
                   hueco_maximo: int = 0, conectividad: int = 2) -> Resultado:
    """Conserva componentes con área >= area_minima y rellena huecos <= hueco_maximo."""
    a = v.mascara(mascara)
    area = v.entero(area_minima,'area_minima',1)
    hueco = v.entero(hueco_maximo,'hueco_maximo',0)
    c = v.entero(conectividad,'conectividad',1,2)
    b = morphology.remove_small_objects(a,max_size=area-1,connectivity=c)
    if hueco:
        # Solo huecos cerrados: no convertir fondo exterior pequeño en objeto.
        fondos = ndi.label(~b,structure=ndi.generate_binary_structure(2,c))[0]
        ids_exteriores = np.unique(np.concatenate([fondos[0],fondos[-1],fondos[:,0],fondos[:,-1]]))
        areas = np.bincount(fondos.ravel())
        rellenar = np.flatnonzero((areas <= hueco)&(areas > 0))
        rellenar = np.setdiff1d(rellenar,np.r_[0,ids_exteriores])
        b = b | np.isin(fondos,rellenar)
    return Resultado({'limpia':b,'eliminados':a & ~b,'agregados':b & ~a},
        {'limpia':'mascara','eliminados':'mascara','agregados':'mascara'},resumen={
        'area_minima_inclusiva_px':area,'hueco_maximo_inclusivo_px':hueco,
        'conectividad':c,'pixeles_eliminados':int(np.sum(a & ~b)),
        'pixeles_agregados':int(np.sum(b & ~a))})


def invertir_mascara(mascara: np.ndarray) -> Resultado:
    """Intercambia verdadero y falso; la elección de primer plano es explícita."""
    a = v.mascara(mascara)
    return Resultado({'invertida':~a},{'invertida':'mascara'})


def esqueletizar(limites: np.ndarray) -> Resultado:
    """Adelgaza una red binaria; no cierra discontinuidades ni valida su identidad."""
    a = v.mascara(limites)
    return Resultado({'esqueleto':morphology.skeletonize(a)},{'esqueleto':'limites'},
        advertencias=['El adelgazamiento conserva una representación digital, no recupera límites ausentes.'])
