"""Imagen, muestreo, coordenadas y calibración; capítulos 2 y apéndices."""
from __future__ import annotations
from math import hypot
import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from skimage import color, transform
from . import _validacion as v
from .modelos import Resultado, EscalaEspacial

def explorar_imagen(imagen: np.ndarray) -> Resultado:
    """Inspecciona la representación original sin normalizar ni modificar píxeles."""
    a = v.imagen(imagen)
    return Resultado({'original': a}, {'original': 'imagen'}, resumen={
        'forma': list(a.shape), 'tipo_dato': str(a.dtype), 'minimo': float(a.min()),
        'maximo': float(a.max()), 'pixeles': int(a.shape[0]*a.shape[1]),
        'bytes_por_elemento': a.dtype.itemsize,
        'convencion': 'imagen[fila, columna]; fila crece hacia abajo'})

def convertir_grises(imagen: np.ndarray) -> Resultado:
    """Normaliza enteros por su tipo y convierte RGB a gris. RGBA exige alfa opaco."""
    a = v.unidad(imagen)
    if a.ndim == 3:
        if a.shape[2] == 4 and not np.all(a[..., 3] == 1):
            raise ValueError("RGBA con transparencia: componga el fondo de forma explícita antes del análisis.")
        a = color.rgb2gray(a[..., :3])
    return Resultado({'gris': a}, {'gris': 'gris'}, resumen={'intervalo': '[0,1]',
        'normalizacion': 'Enteros por rango del tipo; flotantes ya normalizados.'},
        advertencias=['No se infiere la profundidad efectiva de captura a partir del contenedor uint16.'])

def separar_canales(imagen: np.ndarray) -> Resultado:
    """Devuelve R, G, B y la conversión ponderada a gris con el mismo rango [0,1]."""
    a = v.unidad(imagen)
    if a.ndim != 3:
        raise ValueError("Esta operación necesita una imagen RGB o RGBA opaca.")
    gris = convertir_grises(imagen).datos['gris']
    d = {k: a[..., i] for i, k in enumerate(('rojo', 'verde', 'azul'))}
    d['gris'] = gris
    return Resultado(d, dict.fromkeys(d, 'gris'), advertencias=[
        'Diferencias entre canales no identifican fases ni materiales.'])

def extraer_roi(imagen: np.ndarray, r0: int, r1: int, c0: int, c1: int) -> Resultado:
    """Recorta [r0:r1, c0:c1], límites finales excluidos; no redimensiona."""
    a = v.imagen(imagen)
    r0, r1, c0, c1 = [v.entero(x, n) for x, n in zip((r0,r1,c0,c1), ('r0','r1','c0','c1'))]
    if not (r0 < r1 <= a.shape[0] and c0 < c1 <= a.shape[1]):
        raise ValueError("ROI vacía, invertida o fuera de la imagen.")
    return Resultado({'roi': a[r0:r1,c0:c1]}, {'roi': 'imagen'}, resumen={
        'roi_rc': [r0,r1,c0,c1], 'origen_local_en_imagen': [r0,c0],
        'conserva_escala': True}, advertencias=[
        'La exclusión de barra de escala y anotaciones debe comprobarse visualmente.'])

def reducir_y_ampliar(imagen: np.ndarray, factor: int = 4) -> Resultado:
    """Demostración de pérdida de muestreo, no una mejora de resolución óptica."""
    a = v.gris(imagen)
    factor = v.entero(factor, 'factor', 2, min(a.shape))
    b = transform.resize(a, (a.shape[0]//factor,a.shape[1]//factor),
                         anti_aliasing=True, preserve_range=True)
    c = transform.resize(b, a.shape, order=0, anti_aliasing=False, preserve_range=True)
    return Resultado({'reducida': b, 'ampliada': c}, {'reducida':'gris','ampliada':'gris'},
        resumen={'factor_solicitado':factor,'forma_original':list(a.shape),
                 'razon_filas': a.shape[0]/b.shape[0], 'razon_columnas': a.shape[1]/b.shape[1]},
        advertencias=['Demostración de muestreo. Las salidas requieren verificar de nuevo la calibración antes de medir.'])

def cuantizar(imagen: np.ndarray, bits_salida: int = 4) -> Resultado:
    """Cuantiza a 2**bits_salida niveles normalizados; conserva el tamaño espacial."""
    a = v.gris(imagen)
    bits = v.entero(bits_salida, 'bits_salida', 1, 16)
    niveles = 2**bits-1
    return Resultado({'cuantizada': np.rint(a*niveles)/niveles}, {'cuantizada':'gris'},
                     resumen={'bits_salida':bits,'niveles_posibles':niveles+1})

def histograma_percentiles(imagen: np.ndarray, bins: int = 256) -> Resultado:
    """Histograma en [0,1] y percentiles de la imagen de intensidades normalizada."""
    a = v.gris(imagen)
    bins = v.entero(bins,'bins',2,65536)
    h, b = np.histogram(a,bins=bins,range=(0,1))
    return Resultado(tabla=pd.DataFrame({'intensidad':(b[:-1]+b[1:])/2,
         'conteo':h, 'fraccion':h/a.size}), resumen={
         'p1':float(np.percentile(a,1)), 'p99':float(np.percentile(a,99)),
         'minimo':float(a.min()),'maximo':float(a.max()),'numero_pixeles':a.size,
         'bins': bins}, advertencias=['El histograma no localiza ni identifica fases.'])

def perfil_intensidad(imagen: np.ndarray, r0: float, c0: float, r1: float, c1: float) -> Resultado:
    """Muestrea un segmento entre centros de píxel con interpolación bilineal."""
    a = v.gris(imagen)
    r0,r1 = [v.real(x,'fila',0,a.shape[0]-1) for x in (r0,r1)]
    c0,c1 = [v.real(x,'columna',0,a.shape[1]-1) for x in (c0,c1)]
    largo = hypot(r1-r0,c1-c0)
    if largo == 0:
        raise ValueError("Los extremos del perfil deben ser distintos.")
    n = int(np.ceil(largo))+1
    rr, cc = np.linspace(r0,r1,n), np.linspace(c0,c1,n)
    valores = ndi.map_coordinates(a,[rr,cc],order=1,mode='nearest')
    return Resultado(tabla=pd.DataFrame({'distancia_px':np.linspace(0,largo,n),
        'fila_px':rr,'columna_px':cc,'intensidad':valores}),
        resumen={'longitud_px':largo, 'extremos_rc':[r0,c0,r1,c1]})

def calibrar_escala(referencia_um: float, referencia_px: float,
                    incertidumbre_um: float | None = None,
                    incertidumbre_px: float | None = None,
                    referencia: str = '') -> EscalaEspacial:
    """Calcula µm/px; propagación de primer orden con entradas independientes.

    Las dos incertidumbres estándar se proporcionan juntas o ambas se omiten.
    Omitir no equivale a incertidumbre cero. Se supone escala isotrópica.
    """
    l = v.real(referencia_um,'referencia_um',positivo=True)
    p = v.real(referencia_px,'referencia_px',positivo=True)
    if (incertidumbre_um is None) != (incertidumbre_px is None):
        raise ValueError("Proporcione ambas incertidumbres estándar o ninguna.")
    u = None
    if incertidumbre_um is not None:
        ul = v.real(incertidumbre_um,'incertidumbre_um',0)
        up = v.real(incertidumbre_px,'incertidumbre_px',0)
        u = l/p * hypot(ul/l,up/p)
    return EscalaEspacial(l/p,u,str(referencia))

def convertir_medidas(s_um_px: float, longitud_px: float = 1.0,
                       area_px2: float = 1.0, incertidumbre_s: float | None = None) -> Resultado:
    """Convierte longitud y área; la incertidumbre mostrada es solo la de escala."""
    e = EscalaEspacial(s_um_px,incertidumbre_s)
    datos = {'longitud_um':e.longitud_um(longitud_px),'area_um2':e.area_um2(area_px2)}
    if incertidumbre_s is not None:
        datos.update(u_longitud_solo_escala_um=longitud_px*incertidumbre_s,
                     u_area_solo_escala_um2=2*area_px2*s_um_px*incertidumbre_s)
    return Resultado(resumen=datos,advertencias=[
        'No incluye incertidumbre de delimitación, muestreo ni segmentación. Escala isotrópica.'])
