"""Mediciones bidimensionales con escala, dominio y reglas de conteo explícitos."""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from skimage import measure
from . import _validacion as v
from .modelos import Resultado

_COLUMNAS = ['etiqueta','area_px2','area_um2','perimetro_um',
    'perimetro_crofton_um','centroide_fila_px','centroide_columna_px',
    'diametro_equivalente_um','eje_mayor_um','eje_menor_um','orientacion_rad',
    'circularidad','relacion_aspecto','feret_max_um','solidez','toca_marco']


def _tabla_regiones(etiquetas, s_um_px):
    a = v.etiquetas(etiquetas)
    s = v.escala(s_um_px)
    filas = []
    ids = np.unique(a[a > 0])
    compacta = np.where(a > 0, np.searchsorted(ids, a) + 1, 0).astype(np.int32)
    for r in measure.regionprops(compacta):
        id_original = int(ids[r.label - 1])
        if ndi.label(r.image,structure=np.ones((3,3),bool))[1] != 1:
            raise ValueError(f'La etiqueta {id_original} contiene partes desconectadas. Etiquete instancias, no clases.')
        p = float(r.perimeter*s)
        area = float(r.area*s*s)
        r0,c0,r1,c1 = r.bbox
        filas.append(dict(etiqueta=id_original,area_px2=int(r.area),area_um2=area,
            perimetro_um=p,perimetro_crofton_um=float(r.perimeter_crofton*s),
            centroide_fila_px=float(r.centroid[0]),centroide_columna_px=float(r.centroid[1]),
            diametro_equivalente_um=float(r.equivalent_diameter_area*s),
            eje_mayor_um=float(r.axis_major_length*s),eje_menor_um=float(r.axis_minor_length*s),
            orientacion_rad=float(r.orientation),
            circularidad=float(4*np.pi*area/p**2) if p>0 else np.nan,
            relacion_aspecto=float(r.axis_major_length/r.axis_minor_length) if r.axis_minor_length>0 else np.nan,
            feret_max_um=float(r.feret_diameter_max*s),solidez=float(r.solidity),
            toca_marco=bool(r0==0 or c0==0 or r1==a.shape[0] or c1==a.shape[1])))
    return a,pd.DataFrame(filas,columns=_COLUMNAS)


def propiedades_basicas(etiquetas: np.ndarray, s_um_px: float) -> Resultado:
    """Medidas por instancia conservando identificadores; cero representa fondo."""
    a,t = _tabla_regiones(etiquetas,s_um_px)
    cols = ['etiqueta','area_px2','area_um2','perimetro_um',
            'centroide_fila_px','centroide_columna_px','toca_marco']
    return Resultado({'etiquetas':a},{'etiquetas':'etiquetas'},tabla=t[cols],resumen={
        'numero_objetos':len(t),'s_um_px':s_um_px,'area_roi_um2':a.size*s_um_px**2},
        advertencias=['Son medidas de perfiles bidimensionales. Los objetos en el marco pueden estar truncados.'])


def descriptores_forma(etiquetas: np.ndarray, s_um_px: float) -> Resultado:
    """Área, perímetros, diámetro equivalente, ejes, orientación y Feret máximo.

    Circularidad usa el perímetro de contorno de regionprops, no Crofton.
    No se recorta a [0,1]: la discretización puede producir valores superiores a 1.
    Orientación: convención de regionprops, desde el eje de filas, en radianes.
    """
    a,t = _tabla_regiones(etiquetas,s_um_px)
    return Resultado({'etiquetas':a},{'etiquetas':'etiquetas'},tabla=t,resumen={
        's_um_px':s_um_px,'numero_objetos':len(t),
        'perimetro_circularidad':'regionprops.perimeter',
        'orientacion':'Ángulo del eje mayor respecto al eje de filas, según regionprops.'},
        advertencias=['La circularidad digital puede exceder uno; no se trunca.',
        'NaN significa descriptor indefinido, no cero. No se infiere orientación física de la probeta.'])


def medir_objetos(etiquetas: np.ndarray, s_um_px: float, area_minima: int = 20,
                  regla_marco: str = 'excluir') -> Resultado:
    """Filtra instancias ya separadas sin fusionarlas. Registra objetos descartados."""
    a,t = _tabla_regiones(etiquetas,s_um_px)
    area = v.entero(area_minima,'area_minima',1)
    v.opcion(regla_marco,('excluir','conservar'),'regla_marco')
    aceptado = (t.area_px2 >= area)
    if regla_marco == 'excluir':
        aceptado &= ~t.toca_marco.astype(bool)
    t['aceptado'] = aceptado.astype(bool)
    t['motivo'] = [
        '; '.join([reason for cond,reason in [(row.area_px2<area,'área menor que el mínimo'),
                 (regla_marco=='excluir' and row.toca_marco,'toca el marco')] if cond])
        or 'conservado' for row in t.itertuples()]
    ids = t.loc[t.aceptado,'etiqueta'].to_numpy(dtype=np.int32)
    b = np.where(np.isin(a,ids),a,0).astype(np.int32)
    roi_mm2 = a.size*s_um_px**2/1_000_000
    return Resultado({'aceptadas':b,'descartadas':np.where((a>0)&(b==0),a,0)},
        {'aceptadas':'etiquetas','descartadas':'etiquetas'},tabla=t,resumen={
        'numero_objetos_entrada':len(t),'numero_objetos_aceptados':len(ids),
        'numero_objetos_descartados':len(t)-len(ids),'area_roi_mm2':roi_mm2,
        'densidad_objetos_aceptados_mm2':len(ids)/roi_mm2,
        'fraccion_area_entrada':float(np.mean(a>0)),
        'fraccion_area_aceptada':float(np.mean(b>0)),
        'regla_marco':regla_marco,'area_minima_inclusiva_px':area},advertencias=[
        'La densidad se refiere a objetos aceptados por esta regla y al área completa de la ROI; no se declara insesgada.',
        'La fracción posterior al filtrado no sustituye la fracción original de una fase.'])


def densidad_jeffries(etiquetas: np.ndarray, s_um_px: float) -> Resultado:
    """Ponderación ilustrativa ni + 0.5*nb en una ROI rectangular; no número ASTM."""
    a,t = _tabla_regiones(etiquetas,s_um_px)
    nb = int(t.toca_marco.sum())
    ni = len(t)-nb
    area = a.size*s_um_px**2/1_000_000
    t['peso'] = np.where(t.toca_marco,0.5,1.0)
    return Resultado({'etiquetas':a},{'etiquetas':'etiquetas'},tabla=t[
        ['etiqueta','toca_marco','peso']],resumen={
        'interiores':ni,'en_marco':nb,'conteo_ponderado':ni+0.5*nb,
        'area_roi_mm2':area,'densidad_ponderada_mm2':(ni+0.5*nb)/area,
        'geometria':'ROI rectangular; cada perfil que toca el marco recibe peso 0.5.'},
        advertencias=['Esta ponderación reproduce el modelo ilustrativo del manuscrito, no el procedimiento ASTM E112 completo.',
        'No trata por separado esquinas, geometrías de prueba ni conversión al número G. No certifica conformidad normativa.'])


def fracciones_area(clases: np.ndarray, roi: np.ndarray | None = None) -> Resultado:
    """Proporciones por clase sobre un dominio explícito. Incluye la clase cero."""
    a = v.etiquetas(clases,clases=True)
    dominio = np.ones(a.shape,bool) if roi is None else v.mascara(roi)
    v.misma_forma(a,dominio)
    n = int(dominio.sum())
    if n == 0:
        raise ValueError('La ROI no contiene píxeles medibles.')
    ids,counts = np.unique(a[dominio],return_counts=True)
    t = pd.DataFrame({'clase':ids,'pixeles':counts,'fraccion_area':counts/n,
                      'porcentaje_area':100*counts/n})
    return Resultado({'dominio':dominio},{'dominio':'mascara'},tabla=t,resumen={
        'pixeles_roi':n,'pixeles_excluidos':int(a.size-n),
        'denominador':'Todos los píxeles verdaderos de la ROI; cero es una clase válida.'},
        advertencias=['La etiqueta numérica no identifica una fase. La fracción de área no se convierte automáticamente en fracción volumétrica.'])


def _corridas(perfil):
    cambios = np.diff(np.r_[False,perfil,False].astype(np.int8))
    return list(zip(np.flatnonzero(cambios == 1),np.flatnonzero(cambios == -1)-1))


def intercepto_medio(limites: np.ndarray, s_um_px: float, numero_lineas: int = 8,
                    orientaciones: str = 'ambas', extremos: str = 'excluir') -> Resultado:
    """Longitud de prueba entre centros extremos / corridas de límite por línea.

    Se cuentan corridas contiguas, no todos los píxeles del trazo. Horizontales y
    verticales se reportan por separado. No corrige tangencias, dobles trazos ni
    uniones triples; no calcula número G de ASTM.
    """
    a = v.mascara(limites)
    s = v.escala(s_um_px)
    n = v.entero(numero_lineas,'numero_lineas',1)
    v.opcion(orientaciones,('ambas','horizontal','vertical'),'orientaciones')
    v.opcion(extremos,('excluir','incluir'),'extremos')
    lineas = np.zeros(a.shape,bool)
    puntos = np.zeros(a.shape,bool)
    filas = []
    conjuntos = []
    if orientaciones in ('ambas','horizontal'):
        if n > a.shape[0]-2:
            raise ValueError('Demasiadas líneas horizontales para las filas interiores disponibles.')
        conjuntos.append(('horizontal',np.linspace(1,a.shape[0]-2,n,dtype=int)))
    if orientaciones in ('ambas','vertical'):
        if n > a.shape[1]-2:
            raise ValueError('Demasiadas líneas verticales para las columnas interiores disponibles.')
        conjuntos.append(('vertical',np.linspace(1,a.shape[1]-2,n,dtype=int)))
    for direccion,posiciones in conjuntos:
        for posicion in posiciones:
            perfil = a[posicion,:] if direccion == 'horizontal' else a[:,posicion]
            if len(perfil)<2:
                raise ValueError('Las líneas de prueba necesitan al menos dos píxeles.')
            corridas = _corridas(perfil)
            validas = [(inicio,fin) for inicio,fin in corridas
                if extremos == 'incluir' or (inicio>0 and fin<len(perfil)-1)]
            centros = [(inicio+fin)//2 for inicio,fin in validas]
            if direccion == 'horizontal':
                lineas[posicion,:]=True
                puntos[posicion,centros]=True
            else:
                lineas[:,posicion]=True
                puntos[centros,posicion]=True
            filas.append({'orientacion':direccion,'posicion_px':int(posicion),
                'longitud_px':len(perfil)-1,'longitud_um':(len(perfil)-1)*s,
                'intersecciones':len(validas),'corridas_extremas_excluidas':len(corridas)-len(validas)})
    t = pd.DataFrame(filas)
    ni = int(t.intersecciones.sum()); longitud = float(t.longitud_um.sum())
    por_dir = {}
    for direccion,grupo in t.groupby('orientacion'):
        cuenta = int(grupo.intersecciones.sum()); largo = float(grupo.longitud_um.sum())
        por_dir[direccion] = {'longitud_um':largo,'intersecciones':cuenta,
            'longitud_media_um':largo/cuenta if cuenta else None}
    return Resultado({'lineas_prueba':lineas,'intersecciones':puntos},
        {'lineas_prueba':'limites','intersecciones':'mascara'},tabla=t,resumen={
        'longitud_total_um':longitud,'intersecciones_totales':ni,
        'longitud_media_um':longitud/ni if ni else None,'por_orientacion':por_dir,
        'regla_extremos':extremos,'convencion_longitud':'Distancia entre centros: (N-1)*s.'},
        advertencias=[
        'Las corridas son candidatos a intersección: tangencias, dobles trazos y uniones requieren revisión.',
        'No constituye aplicación completa de ASTM E112 ni convierte a número G.'] +
        ([] if ni else ['No hay intersecciones válidas; no se calcula longitud media.']))
