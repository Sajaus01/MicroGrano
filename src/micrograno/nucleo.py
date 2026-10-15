"""Punto de acceso único a la API científica de MicroGrano 1.0.0.

Los listados del libro deben importar desde este módulo. Cada implementación
reside una sola vez en el módulo temático correspondiente.
"""
from .imagen import (explorar_imagen, convertir_grises, separar_canales, extraer_roi,
    reducir_y_ampliar, cuantizar, histograma_percentiles, perfil_intensidad,
    calibrar_escala, convertir_medidas)
from .preprocesamiento import (reescalar_percentiles, variantes_contraste,
    variantes_ruido, agregar_ruido, evaluar_referencia, corregir_iluminacion,
    top_hat, realzar_sobel, variantes_morfologicas, limpiar_mascara,
    invertir_mascara, esqueletizar)
from .segmentacion import (umbralizar, detectar_canny, etiquetar_componentes,
    limites_a_regiones, separar_watershed, segmentar_clases, extraer_clase,
    obtener_limites, evaluar_mascara)
from .medicion import (propiedades_basicas, descriptores_forma, medir_objetos,
    densidad_jeffries, fracciones_area, intercepto_medio)
from .estadistica import intervalo_bootstrap_media, reporte_fraccion_area

__all__ = [
    'explorar_imagen','convertir_grises','separar_canales','extraer_roi',
    'reducir_y_ampliar','cuantizar','histograma_percentiles','perfil_intensidad',
    'calibrar_escala','convertir_medidas','reescalar_percentiles',
    'variantes_contraste','variantes_ruido','agregar_ruido','evaluar_referencia',
    'corregir_iluminacion','top_hat','realzar_sobel','variantes_morfologicas',
    'limpiar_mascara','invertir_mascara','esqueletizar','umbralizar',
    'detectar_canny','etiquetar_componentes','limites_a_regiones',
    'separar_watershed','segmentar_clases','extraer_clase','obtener_limites',
    'evaluar_mascara','propiedades_basicas','descriptores_forma','medir_objetos',
    'densidad_jeffries','fracciones_area','intercepto_medio',
    'intervalo_bootstrap_media','reporte_fraccion_area'
]
