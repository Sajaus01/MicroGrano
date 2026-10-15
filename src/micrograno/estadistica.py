"""Resumen por unidades independientes, no por píxeles usados como réplicas."""
from __future__ import annotations
import numpy as np
from . import _validacion as v
from .modelos import Resultado


def intervalo_bootstrap_media(valores: np.ndarray, repeticiones: int = 10000,
                             semilla: int = 2026, confianza: float = 0.95,
                             unidad_analisis: str = 'campo') -> Resultado:
    """Intervalo percentil de la media; muestreo con reemplazo y memoria acotada.

    Se necesitan al menos dos valores finitos. La unidad experimental y la
    independencia son decisiones del estudio, no verificaciones del programa.
    """
    a = v.vector(valores)
    reps = v.entero(repeticiones,'repeticiones',100,1_000_000)
    seed = v.entero(semilla,'semilla',0)
    conf = v.real(confianza,'confianza',0.5,0.999)
    v.opcion(unidad_analisis,('campo','probeta','unidad_independiente'),'unidad_analisis')
    rng = np.random.default_rng(seed)
    medias = np.empty(reps,dtype=float)
    lote = max(1,min(512,1_000_000//len(a)))
    for i in range(0,reps,lote):
        n = min(lote,reps-i)
        medias[i:i+n] = a[rng.integers(0,len(a),size=(n,len(a)))].mean(axis=1)
    limites = np.quantile(medias,[(1-conf)/2,(1+conf)/2])
    return Resultado({'medias_remuestreadas':medias},{'medias_remuestreadas':'distribucion'},
        resumen={'numero_unidades':len(a),'unidad_analisis':unidad_analisis,
        'media':float(a.mean()),'desviacion_estandar_muestral':float(a.std(ddof=1)),
        'intervalo_percentil':[float(x) for x in limites],'confianza':conf,
        'repeticiones':reps,'semilla':seed},advertencias=[
        'El remuestreo supone unidades intercambiables bajo el diseño observado; no demuestra independencia.',
        'No incluye incertidumbre de escala, segmentación ni sesgo de muestreo.'])


def reporte_fraccion_area(valores: np.ndarray, repeticiones: int = 10000,
                          semilla: int = 2026, confianza: float = 0.95,
                          unidad_analisis: str = 'campo') -> Resultado:
    """Resume fracciones por campo/probeta en [0,1], no porcentajes de 0 a 100."""
    a = v.vector(valores)
    if a.min()<0 or a.max()>1:
        raise ValueError('Introduzca fracciones entre 0 y 1, no porcentajes.')
    r = intervalo_bootstrap_media(a,repeticiones,semilla,confianza,unidad_analisis)
    r.resumen.update(mensurando='fraccion_area',unidad='adimensional')
    return r
