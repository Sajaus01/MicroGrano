"""Textos de presentación de MicroGrano Lab: nombres claros, unidades y ayudas breves.

Este módulo solo traduce identificadores técnicos a etiquetas legibles. Los nombres de
parámetros, opciones y salidas que recibe la biblioteca no cambian.
"""
from __future__ import annotations
import math
import numbers
from .tema import SISTEMA
from .flujo import PASOS_APRENDIZAJE

GRUPOS = {
    'Imagen y calibración': {'icono': 'dato', 'color': SISTEMA['azul'],
        'resumen': 'Ver, convertir, recortar y calibrar la imagen.'},
    'Preprocesamiento': {'icono': 'varita', 'color': SISTEMA['morado'],
        'resumen': 'Contraste, ruido, iluminación y realce.'},
    'Máscaras y morfología': {'icono': 'mascara', 'color': SISTEMA['cian'],
        'resumen': 'Limpiar, invertir y transformar máscaras.'},
    'Segmentación': {'icono': 'segmentar', 'color': SISTEMA['naranja'],
        'resumen': 'Separar regiones, bordes, objetos y clases.'},
    'Conteo y características': {'icono': 'regla', 'color': SISTEMA['verde'],
        'resumen': 'Contar y medir objetos, fracciones e intersecciones.'},
    'Estadística': {'icono': 'estadistica', 'color': SISTEMA['rosa'],
        'resumen': 'Resumir valores por campo o probeta.'},
}

OPERACIONES = {
    'explorar_imagen': {'icono': 'ojo',
        'resumen': 'Muestra la imagen tal como está guardada y resume su tamaño, tipo de dato e intervalo de valores. No modifica ningún píxel.',
        'siguientes': ('convertir_grises', 'separar_canales', 'extraer_roi')},
    'convertir_grises': {'icono': 'grises',
        'resumen': 'Convierte la imagen a intensidades entre 0 y 1 según el rango de su tipo de dato, sin estirar el contraste. Suele ser el primer paso del análisis.',
        'siguientes': ('extraer_roi', 'histograma_percentiles', 'calibrar_escala')},
    'separar_canales': {'icono': 'canales',
        'resumen': 'Separa los canales rojo, verde y azul y la conversión a gris para compararlos. Las diferencias entre canales no identifican fases.',
        'siguientes': ('extraer_roi', 'histograma_percentiles')},
    'extraer_roi': {'icono': 'recortar',
        'resumen': 'Recorta un rectángulo para dejar fuera la barra de escala y las anotaciones. Dibújelo sobre la imagen; el recorte conserva la escala y registra su origen.',
        'siguientes': ('histograma_percentiles', 'variantes_contraste', 'umbralizar')},
    'reducir_y_ampliar': {'icono': 'cuadricula',
        'resumen': 'Demuestra qué se pierde al reducir el muestreo: reduce la imagen y la vuelve a ampliar. Las salidas pierden la calibración.',
        'siguientes': ('histograma_percentiles',)},
    'cuantizar': {'icono': 'capas',
        'resumen': 'Simula la misma imagen con menos niveles de intensidad para ver el efecto de la profundidad de bits.',
        'siguientes': ('histograma_percentiles',)},
    'histograma_percentiles': {'icono': 'histograma',
        'resumen': 'Calcula el histograma de intensidades y los percentiles 1 y 99. Ayuda a revisar contraste y saturación antes de umbralizar.',
        'siguientes': ('reescalar_percentiles', 'umbralizar', 'segmentar_clases')},
    'perfil_intensidad': {'icono': 'perfil',
        'resumen': 'Mide la intensidad a lo largo de un segmento. Dibuje la línea sobre la imagen para obtener la curva.',
        'siguientes': ('umbralizar',)},
    'calibrar_escala': {'icono': 'regla',
        'resumen': 'Calcula la escala en µm/px a partir de una referencia de longitud documentada (barra de escala o micrómetro). Después aplíquela al dato correspondiente.',
        'siguientes': ()},
    'convertir_medidas': {'icono': 'usar',
        'resumen': 'Convierte una longitud en píxeles y un área en píxeles² a µm y µm² con una escala conocida.',
        'siguientes': ()},
    'reescalar_percentiles': {'icono': 'contraste',
        'resumen': 'Estira el contraste entre dos percentiles. Los valores que quedan fuera se saturan.',
        'siguientes': ('umbralizar', 'variantes_ruido')},
    'variantes_contraste': {'icono': 'apariencia',
        'resumen': 'Compara tres mejoras de contraste sobre la misma imagen: estiramiento por percentiles, ecualización global y CLAHE.',
        'siguientes': ('umbralizar', 'variantes_ruido')},
    'variantes_ruido': {'icono': 'ruido',
        'resumen': 'Compara cuatro filtros de ruido sobre la misma imagen: media, gaussiano, mediana y bilateral.',
        'siguientes': ('umbralizar', 'detectar_canny')},
    'agregar_ruido': {'icono': 'matraz',
        'resumen': 'Añade ruido gaussiano sintético con semilla para comprobar cómo responden los demás pasos.',
        'siguientes': ('variantes_ruido', 'evaluar_referencia')},
    'evaluar_referencia': {'icono': 'copiar',
        'resumen': 'Compara una imagen candidata con una referencia alineada mediante PSNR y SSIM.',
        'siguientes': ()},
    'corregir_iluminacion': {'icono': 'iluminacion',
        'resumen': 'Estima el fondo con una bola rodante y lo corrige de forma aditiva y divisiva. Puede tardar en imágenes grandes.',
        'siguientes': ('umbralizar', 'segmentar_clases')},
    'top_hat': {'icono': 'destello',
        'resumen': 'Extrae los detalles claros y oscuros más pequeños que el disco elegido (residuos top-hat).',
        'siguientes': ('umbralizar',)},
    'realzar_sobel': {'icono': 'grafica',
        'resumen': 'Calcula las derivadas de intensidad de Sobel y su magnitud para resaltar transiciones.',
        'siguientes': ('detectar_canny',)},
    'variantes_morfologicas': {'icono': 'morfologia',
        'resumen': 'Compara erosión, dilatación, apertura y cierre de una máscara con el mismo disco.',
        'siguientes': ('limpiar_mascara', 'etiquetar_componentes', 'separar_watershed')},
    'limpiar_mascara': {'icono': 'varita',
        'resumen': 'Elimina componentes pequeñas y rellena huecos cerrados pequeños. Muestra qué píxeles se quitaron y cuáles se agregaron.',
        'siguientes': ('separar_watershed', 'etiquetar_componentes')},
    'invertir_mascara': {'icono': 'invertir',
        'resumen': 'Intercambia el primer plano y el fondo de la máscara.',
        'siguientes': ('limpiar_mascara', 'etiquetar_componentes')},
    'esqueletizar': {'icono': 'esqueleto',
        'resumen': 'Adelgaza una red de límites hasta un píxel de grosor. No cierra discontinuidades.',
        'siguientes': ('limites_a_regiones', 'intercepto_medio')},
    'umbralizar': {'icono': 'umbral',
        'resumen': 'Convierte la imagen en máscaras con tres criterios a la vez: umbral manual, Otsu y adaptativo local. Elija si el primer plano es claro u oscuro.',
        'siguientes': ('limpiar_mascara', 'separar_watershed', 'etiquetar_componentes', 'variantes_morfologicas')},
    'detectar_canny': {'icono': 'bordes',
        'resumen': 'Detecta bordes candidatos con Canny. Produce límites, no granos ni objetos.',
        'siguientes': ('esqueletizar', 'limites_a_regiones', 'intercepto_medio')},
    'etiquetar_componentes': {'icono': 'numero',
        'resumen': 'Asigna un número distinto a cada región conexa de la máscara.',
        'siguientes': ('medir_objetos', 'descriptores_forma', 'obtener_limites')},
    'limites_a_regiones': {'icono': 'segmentar',
        'resumen': 'Convierte una red de límites en regiones etiquetadas (el complemento de la red). Puede excluir las regiones abiertas al marco.',
        'siguientes': ('medir_objetos', 'descriptores_forma')},
    'separar_watershed': {'icono': 'gota',
        'resumen': 'Separa objetos que se tocan usando la distancia al borde y semillas (watershed). Revise las semillas y las separaciones.',
        'siguientes': ('medir_objetos', 'descriptores_forma', 'obtener_limites')},
    'segmentar_clases': {'icono': 'paleta',
        'resumen': 'Divide las intensidades en 2 a 4 clases con multi-Otsu. Las clases son intervalos de intensidad, no fases identificadas.',
        'siguientes': ('fracciones_area', 'extraer_clase')},
    'extraer_clase': {'icono': 'mascara',
        'resumen': 'Convierte una clase de intensidad en una máscara. La clase cero también es válida.',
        'siguientes': ('limpiar_mascara', 'etiquetar_componentes', 'separar_watershed')},
    'obtener_limites': {'icono': 'contornos',
        'resumen': 'Obtiene los contornos de los objetos etiquetados, incluidas las interfaces con el fondo.',
        'siguientes': ('intercepto_medio',)},
    'evaluar_mascara': {'icono': 'venn',
        'resumen': 'Compara una máscara candidata con una referencia alineada (Dice e IoU) y muestra falsos positivos y negativos.',
        'siguientes': ()},
    'propiedades_basicas': {'icono': 'tabla',
        'resumen': 'Mide el área, el perímetro y el centroide de cada objeto etiquetado. Requiere una escala asociada.',
        'siguientes': ('descriptores_forma', 'medir_objetos')},
    'descriptores_forma': {'icono': 'forma',
        'resumen': 'Mide tamaño y forma de cada objeto: diámetro equivalente, ejes, Feret, circularidad y solidez.',
        'siguientes': ('medir_objetos',)},
    'medir_objetos': {'icono': 'objetos',
        'resumen': 'Filtra los objetos por área y por contacto con el marco, los cuenta y los mide. Registra por qué se descarta cada uno.',
        'siguientes': ('densidad_jeffries', 'descriptores_forma')},
    'densidad_jeffries': {'icono': 'densidad',
        'resumen': 'Cuenta objetos ponderando con 0.5 los que tocan el marco. Es un modelo ilustrativo, no el procedimiento ASTM E112 completo.',
        'siguientes': ()},
    'fracciones_area': {'icono': 'fraccion',
        'resumen': 'Calcula la fracción de área de cada clase dentro de la región elegida. La clase cero se incluye.',
        'siguientes': ()},
    'intercepto_medio': {'icono': 'intercepto',
        'resumen': 'Cuenta las intersecciones de líneas horizontales y verticales con la red de límites y calcula la longitud media.',
        'siguientes': ()},
    'intervalo_bootstrap_media': {'icono': 'estadistica',
        'resumen': 'Estima un intervalo bootstrap de la media a partir de valores por campo o por probeta.',
        'siguientes': ()},
    'reporte_fraccion_area': {'icono': 'resumen',
        'resumen': 'Resume fracciones de área por campo (entre 0 y 1) con su intervalo bootstrap.',
        'siguientes': ()},
}

TIPOS = {
    'imagen': {'nombre': 'Imagen', 'icono': 'dato', 'color': SISTEMA['azul']},
    'gris': {'nombre': 'Imagen en grises', 'icono': 'grises', 'color': SISTEMA['indigo']},
    'mascara': {'nombre': 'Máscara', 'icono': 'mascara', 'color': SISTEMA['cian']},
    'limites': {'nombre': 'Red de límites', 'icono': 'contornos', 'color': SISTEMA['naranja']},
    'etiquetas': {'nombre': 'Objetos etiquetados', 'icono': 'numero', 'color': SISTEMA['verde']},
    'clases': {'nombre': 'Clases de intensidad', 'icono': 'paleta', 'color': SISTEMA['morado']},
    'marcadores': {'nombre': 'Marcadores', 'icono': 'gota', 'color': SISTEMA['rosa']},
    'mapa': {'nombre': 'Mapa numérico', 'icono': 'grafica', 'color': SISTEMA['amarillo']},
    'valores': {'nombre': 'Valores por campo', 'icono': 'tabla', 'color': SISTEMA['menta']},
    'distribucion': {'nombre': 'Distribución remuestreada', 'icono': 'estadistica', 'color': SISTEMA['marron']},
}

ENTRADAS = {
    'imagen': 'Imagen', 'mascara': 'Máscara', 'limites': 'Red de límites',
    'etiquetas': 'Objetos etiquetados', 'marcadores': 'Marcadores', 'clases': 'Clases',
    'valores': 'Valores', 'referencia': 'Referencia', 'candidata': 'Candidata',
    'roi': 'Región (ROI)',
}

SIN_ENTRADA = {'marcadores': 'Automáticos (picos de distancia)', 'roi': 'Toda la imagen'}

# Metadatos de cada parámetro: etiqueta, unidad, intervalo admitido y deslizador sugerido.
PARAMETROS = {
    's_um_px': {'etiqueta': 'Escala', 'unidad': 'µm/px', 'minimo': 0, 'positivo': True},
    'radio_px': {'etiqueta': 'Radio del disco', 'unidad': 'px', 'minimo': 1, 'maximo': 200, 'deslizador': (1, 30)},
    'radio': {'etiqueta': 'Radio de la bola rodante', 'unidad': 'px', 'minimo': 1, 'maximo': 200, 'deslizador': (1, 100), 'decimales': 1},
    'area_minima': {'etiqueta': 'Área mínima', 'unidad': 'px', 'minimo': 1},
    'hueco_maximo': {'etiqueta': 'Hueco máximo a rellenar', 'unidad': 'px', 'minimo': 0},
    'conectividad': {'etiqueta': 'Vecindad', 'segmentos': ((1, '4 vecinos'), (2, '8 vecinos'))},
    'min_distance': {'etiqueta': 'Separación mínima entre semillas', 'unidad': 'px', 'minimo': 1, 'maximo': 10000},
    'tile': {'etiqueta': 'Tamaño de la región CLAHE', 'unidad': 'px', 'minimo': 2, 'maximo': 4096},
    'clip_limit': {'etiqueta': 'Límite de recorte CLAHE', 'minimo': 0, 'maximo': 1, 'positivo': True, 'deslizador': (0.001, 0.1), 'decimales': 3},
    'sigma': {'etiqueta': 'Sigma (σ)', 'unidad': 'px', 'minimo': 0, 'deslizador': (0, 10), 'decimales': 2},
    'sigma_color': {'etiqueta': 'Tolerancia de intensidad', 'minimo': 0, 'positivo': True, 'deslizador': (0.005, 0.5), 'decimales': 3},
    'sigma_spatial': {'etiqueta': 'Escala espacial', 'unidad': 'px', 'minimo': 0, 'positivo': True, 'deslizador': (0.5, 15), 'decimales': 1},
    'manual': {'etiqueta': 'Umbral manual', 'unidad': '0–1', 'minimo': 0, 'maximo': 1, 'deslizador': (0, 1), 'decimales': 3},
    'bloque': {'etiqueta': 'Ventana local', 'unidad': 'px', 'minimo': 3, 'maximo': 2001, 'impar': True},
    'desplazamiento': {'etiqueta': 'Desplazamiento', 'minimo': -1, 'maximo': 1, 'deslizador': (-0.2, 0.2), 'decimales': 3},
    'bajo': {'etiqueta': 'Umbral bajo', 'unidad': '0–1', 'minimo': 0, 'maximo': 1, 'deslizador': (0, 1), 'decimales': 3},
    'alto': {'etiqueta': 'Umbral alto', 'unidad': '0–1', 'minimo': 0, 'maximo': 1, 'deslizador': (0, 1), 'decimales': 3},
    'p_bajo': {'etiqueta': 'Percentil inferior', 'unidad': '%', 'minimo': 0, 'maximo': 100, 'deslizador': (0, 100), 'decimales': 1},
    'p_alto': {'etiqueta': 'Percentil superior', 'unidad': '%', 'minimo': 0, 'maximo': 100, 'deslizador': (0, 100), 'decimales': 1},
    'r0': {'etiqueta': 'Fila inicial', 'unidad': 'px', 'minimo': 0},
    'r1': {'etiqueta': 'Fila final', 'unidad': 'px', 'minimo': 0},
    'c0': {'etiqueta': 'Columna inicial', 'unidad': 'px', 'minimo': 0},
    'c1': {'etiqueta': 'Columna final', 'unidad': 'px', 'minimo': 0},
    'referencia_um': {'etiqueta': 'Longitud real de la referencia', 'unidad': 'µm', 'minimo': 0, 'positivo': True},
    'referencia_px': {'etiqueta': 'Longitud medida en la imagen', 'unidad': 'px', 'minimo': 0, 'positivo': True},
    'incertidumbre_um': {'etiqueta': 'Incertidumbre de la longitud real', 'unidad': 'µm', 'minimo': 0},
    'incertidumbre_px': {'etiqueta': 'Incertidumbre de la medida', 'unidad': 'px', 'minimo': 0},
    'incertidumbre_s': {'etiqueta': 'Incertidumbre de la escala', 'unidad': 'µm/px', 'minimo': 0},
    'referencia': {'etiqueta': 'Identificación de la referencia', 'marcador': 'Ej.: micrómetro objetivo, 10 µm/div'},
    'longitud_px': {'etiqueta': 'Longitud', 'unidad': 'px', 'minimo': 0},
    'area_px2': {'etiqueta': 'Área', 'unidad': 'px²', 'minimo': 0},
    'bits_salida': {'etiqueta': 'Bits de salida', 'unidad': 'bits', 'minimo': 1, 'maximo': 16, 'deslizador': (1, 16)},
    'factor': {'etiqueta': 'Factor de reducción', 'unidad': '×', 'minimo': 2, 'deslizador': (2, 16)},
    'bins': {'etiqueta': 'Intervalos del histograma', 'minimo': 2, 'maximo': 65536},
    'clases': {'etiqueta': 'Número de clases', 'segmentos': ((2, '2'), (3, '3'), (4, '4'))},
    'clase': {'etiqueta': 'Clase a extraer', 'minimo': 0},
    'numero_lineas': {'etiqueta': 'Líneas por orientación', 'minimo': 1, 'deslizador': (1, 40)},
    'repeticiones': {'etiqueta': 'Remuestreos', 'minimo': 100, 'maximo': 1_000_000},
    'semilla': {'etiqueta': 'Semilla aleatoria', 'minimo': 0},
    'confianza': {'etiqueta': 'Nivel de confianza', 'minimo': 0.5, 'maximo': 0.999, 'deslizador': (0.5, 0.999), 'decimales': 3},
    'excluir_abiertas': {'etiqueta': 'Excluir regiones abiertas al marco'},
    'orientaciones': {'etiqueta': 'Orientaciones'},
    'extremos': {'etiqueta': 'Corridas en los extremos'},
    'modo': {'etiqueta': 'Tipo de contorno'},
    'regla_marco': {'etiqueta': 'Objetos que tocan el marco'},
    'polaridad': {'etiqueta': 'Primer plano'},
    'unidad_analisis': {'etiqueta': 'Unidad de análisis'},
}

AJUSTES_OPERACION = {
    ('agregar_ruido', 'sigma'): {'etiqueta': 'Sigma del ruido (σ)', 'unidad': '0–1', 'maximo': 1, 'deslizador': (0, 0.2), 'decimales': 3},
    ('variantes_ruido', 'sigma'): {'etiqueta': 'Sigma gaussiana (σ)', 'positivo': True, 'deslizador': (0.1, 10)},
    ('variantes_ruido', 'radio_px'): {'etiqueta': 'Radio de media y mediana', 'maximo': 100, 'deslizador': (1, 15)},
    ('realzar_sobel', 'sigma'): {'etiqueta': 'Suavizado previo (σ)'},
    ('detectar_canny', 'sigma'): {'etiqueta': 'Suavizado (σ)'},
    ('top_hat', 'radio_px'): {'deslizador': (1, 50)},
    ('variantes_morfologicas', 'radio_px'): {'deslizador': (1, 20)},
    ('limites_a_regiones', 'area_minima'): {'etiqueta': 'Área mínima de región'},
    ('medir_objetos', 'area_minima'): {'etiqueta': 'Área mínima de objeto'},
    ('separar_watershed', 'area_minima'): {'etiqueta': 'Área mínima de componente'},
    ('perfil_intensidad', 'r0'): {'etiqueta': 'Fila de inicio'},
    ('perfil_intensidad', 'c0'): {'etiqueta': 'Columna de inicio'},
    ('perfil_intensidad', 'r1'): {'etiqueta': 'Fila de fin'},
    ('perfil_intensidad', 'c1'): {'etiqueta': 'Columna de fin'},
}

OPCIONES = {
    'polaridad': {'clara': 'Claro', 'oscura': 'Oscuro'},
    'modo': {'thick': 'Grueso', 'inner': 'Interior', 'outer': 'Exterior'},
    'regla_marco': {'excluir': 'Excluir', 'conservar': 'Conservar'},
    'orientaciones': {'ambas': 'Ambas', 'horizontal': 'Horizontal', 'vertical': 'Vertical'},
    'extremos': {'excluir': 'Excluir', 'incluir': 'Incluir'},
    'unidad_analisis': {'campo': 'Campo', 'probeta': 'Probeta', 'unidad_independiente': 'Unidad independiente'},
}

SALIDAS = {
    'original': 'Original', 'gris': 'Escala de grises', 'rojo': 'Canal rojo', 'verde': 'Canal verde',
    'azul': 'Canal azul', 'roi': 'Recorte', 'reducida': 'Reducida', 'ampliada': 'Reampliada',
    'cuantizada': 'Cuantizada', 'estirada': 'Estirada', 'ecualizacion_global': 'Ecualización global',
    'clahe': 'CLAHE', 'media': 'Media', 'gaussiano': 'Gaussiano', 'mediana': 'Mediana',
    'bilateral': 'Bilateral', 'con_ruido': 'Con ruido', 'ssim_local': 'SSIM local',
    'fondo': 'Fondo estimado', 'aditiva': 'Corrección aditiva', 'divisiva': 'Corrección divisiva',
    'claro': 'Residuo claro', 'oscuro': 'Residuo oscuro', 'suavizada': 'Suavizada',
    'derivada_fila': 'Derivada en filas', 'derivada_columna': 'Derivada en columnas',
    'magnitud': 'Magnitud', 'erosion': 'Erosión', 'dilatacion': 'Dilatación', 'apertura': 'Apertura',
    'cierre': 'Cierre', 'limpia': 'Máscara limpia', 'eliminados': 'Píxeles eliminados',
    'agregados': 'Píxeles agregados', 'invertida': 'Invertida', 'esqueleto': 'Esqueleto',
    'manual': 'Umbral manual', 'otsu': 'Otsu', 'adaptativa': 'Adaptativa',
    'umbral_local': 'Mapa de umbral local', 'canny': 'Bordes de Canny', 'etiquetas': 'Objetos',
    'regiones_en_marco': 'Regiones en el marco', 'mascara': 'Máscara', 'distancia': 'Distancia',
    'marcadores': 'Marcadores', 'limites': 'Límites', 'clases': 'Clases',
    'falsos_positivos': 'Falsos positivos', 'falsos_negativos': 'Falsos negativos',
    'aceptadas': 'Objetos aceptados', 'descartadas': 'Objetos descartados', 'dominio': 'Dominio',
    'lineas_prueba': 'Líneas de prueba', 'intersecciones': 'Intersecciones',
    'medias_remuestreadas': 'Medias remuestreadas',
}

# Salida que se muestra primero al terminar una operación; nunca se adopta sola.
PREFERENCIA_SALIDA = ('etiquetas', 'aceptadas', 'gris', 'clases', 'limpia', 'mascara', 'otsu',
                      'canny', 'estirada', 'roi', 'cuantizada', 'limites')

COLUMNAS = {
    'etiqueta': 'Objeto', 'area_px2': 'Área (px²)', 'area_um2': 'Área (µm²)',
    'perimetro_um': 'Perímetro (µm)', 'perimetro_crofton_um': 'Perímetro Crofton (µm)',
    'centroide_fila_px': 'Centroide, fila (px)', 'centroide_columna_px': 'Centroide, columna (px)',
    'diametro_equivalente_um': 'Diámetro equivalente (µm)', 'eje_mayor_um': 'Eje mayor (µm)',
    'eje_menor_um': 'Eje menor (µm)', 'orientacion_rad': 'Orientación (rad)',
    'circularidad': 'Circularidad', 'relacion_aspecto': 'Relación de aspecto',
    'feret_max_um': 'Feret máximo (µm)', 'solidez': 'Solidez', 'toca_marco': 'Toca el marco',
    'aceptado': 'Aceptado', 'motivo': 'Motivo', 'peso': 'Peso', 'clase': 'Clase',
    'pixeles': 'Píxeles', 'fraccion_area': 'Fracción de área', 'porcentaje_area': 'Área (%)',
    'intensidad': 'Intensidad', 'conteo': 'Conteo', 'fraccion': 'Fracción',
    'distancia_px': 'Distancia (px)', 'fila_px': 'Fila (px)', 'columna_px': 'Columna (px)',
    'orientacion': 'Orientación', 'posicion_px': 'Posición (px)', 'longitud_px': 'Longitud (px)',
    'longitud_um': 'Longitud (µm)', 'intersecciones': 'Intersecciones',
    'corridas_extremas_excluidas': 'Corridas extremas excluidas',
}

CLAVES = {
    'forma': 'Forma del arreglo', 'tipo_dato': 'Tipo de dato', 'minimo': 'Mínimo', 'maximo': 'Máximo',
    'pixeles': 'Píxeles', 'bytes_por_elemento': 'Bytes por elemento', 'convencion': 'Convención',
    'intervalo': 'Intervalo', 'normalizacion': 'Normalización', 'roi_rc': 'ROI [r0, r1, c0, c1]',
    'origen_local_en_imagen': 'Origen en la imagen (fila, columna)', 'conserva_escala': 'Conserva la escala',
    'factor_solicitado': 'Factor solicitado', 'forma_original': 'Forma original',
    'razon_filas': 'Razón en filas', 'razon_columnas': 'Razón en columnas', 'bits_salida': 'Bits de salida',
    'niveles_posibles': 'Niveles posibles', 'p1': 'Percentil 1', 'p99': 'Percentil 99',
    'numero_pixeles': 'Número de píxeles', 'bins': 'Intervalos', 'longitud_px': 'Longitud (px)',
    'extremos_rc': 'Extremos (r0, c0, r1, c1)', 'um_por_px': 'Escala (µm/px)',
    'incertidumbre_um_por_px': 'Incertidumbre de la escala (µm/px)', 'referencia': 'Referencia',
    'longitud_um': 'Longitud (µm)', 'area_um2': 'Área (µm²)',
    'u_longitud_solo_escala_um': 'Incertidumbre de longitud por escala (µm)',
    'u_area_solo_escala_um2': 'Incertidumbre de área por escala (µm²)',
    'intensidad_inferior': 'Intensidad inferior', 'intensidad_superior': 'Intensidad superior',
    'p_bajo': 'Percentil inferior', 'p_alto': 'Percentil superior',
    'radio_media_mediana_px': 'Radio de media y mediana (px)', 'sigma': 'Sigma', 'semilla': 'Semilla',
    'pixeles_recortados': 'Píxeles recortados a [0, 1]', 'psnr_db': 'PSNR (dB)', 'ssim': 'SSIM',
    'error_cuadratico_medio': 'Error cuadrático medio', 'ventana_ssim': 'Ventana SSIM (px)',
    'data_range': 'Rango de datos', 'radio_px': 'Radio (px)', 'percentiles_salida': 'Percentiles de salida',
    'limites_aditiva': 'Límites de la corrección aditiva', 'limites_divisiva': 'Límites de la corrección divisiva',
    'pixeles_denominador_protegido': 'Píxeles con denominador protegido',
    'area_minima_inclusiva_px': 'Área mínima inclusiva (px)', 'hueco_maximo_inclusivo_px': 'Hueco máximo inclusivo (px)',
    'conectividad': 'Conectividad', 'pixeles_eliminados': 'Píxeles eliminados',
    'pixeles_agregados': 'Píxeles agregados', 'umbral_otsu': 'Umbral de Otsu',
    'umbral_manual': 'Umbral manual', 'polaridad': 'Polaridad', 'regla_igualdad': 'Regla de igualdad',
    'numero_objetos': 'Objetos', 'excluir_abiertas': 'Excluye regiones abiertas',
    'numero_marcadores': 'Marcadores', 'marcadores_automaticos_rescate': 'Semillas de rescate añadidas',
    'min_distance_px': 'Separación mínima (px)', 'marcadores_proporcionados': 'Marcadores proporcionados',
    'umbrales': 'Umbrales', 'numero_clases': 'Número de clases', 'clase': 'Clase', 'modo': 'Modo',
    'verdaderos_positivos': 'Verdaderos positivos', 'falsos_positivos': 'Falsos positivos',
    'falsos_negativos': 'Falsos negativos', 'verdaderos_negativos': 'Verdaderos negativos',
    'iou': 'IoU', 'dice': 'Dice', 'convencion_vacias': 'Convención para máscaras vacías',
    's_um_px': 'Escala (µm/px)', 'area_roi_um2': 'Área de la ROI (µm²)',
    'perimetro_circularidad': 'Perímetro usado en la circularidad', 'orientacion': 'Orientación',
    'numero_objetos_entrada': 'Objetos de entrada', 'numero_objetos_aceptados': 'Objetos aceptados',
    'numero_objetos_descartados': 'Objetos descartados', 'area_roi_mm2': 'Área de la ROI (mm²)',
    'densidad_objetos_aceptados_mm2': 'Densidad de aceptados (objetos/mm²)',
    'fraccion_area_entrada': 'Fracción de área de entrada', 'fraccion_area_aceptada': 'Fracción de área aceptada',
    'regla_marco': 'Regla del marco', 'interiores': 'Objetos interiores', 'en_marco': 'Objetos en el marco',
    'conteo_ponderado': 'Conteo ponderado', 'densidad_ponderada_mm2': 'Densidad ponderada (objetos/mm²)',
    'geometria': 'Geometría', 'pixeles_roi': 'Píxeles de la ROI', 'pixeles_excluidos': 'Píxeles excluidos',
    'denominador': 'Denominador', 'longitud_total_um': 'Longitud total (µm)',
    'intersecciones_totales': 'Intersecciones', 'longitud_media_um': 'Longitud media (µm)',
    'por_orientacion': 'Por orientación', 'regla_extremos': 'Regla de extremos',
    'convencion_longitud': 'Convención de longitud', 'numero_unidades': 'Unidades de análisis',
    'unidad_analisis': 'Unidad de análisis', 'media': 'Media',
    'desviacion_estandar_muestral': 'Desviación estándar muestral', 'intervalo_percentil': 'Intervalo percentil',
    'confianza': 'Confianza', 'repeticiones': 'Remuestreos', 'mensurando': 'Mensurando', 'unidad': 'Unidad',
    'intersecciones': 'Intersecciones', 'longitud_media': 'Longitud media',
}

DESTACADAS = {
    'explorar_imagen': ('forma', 'tipo_dato', 'minimo', 'maximo'),
    'histograma_percentiles': ('p1', 'p99', 'minimo', 'maximo'),
    'perfil_intensidad': ('longitud_px',),
    'calibrar_escala': ('um_por_px', 'incertidumbre_um_por_px'),
    'convertir_medidas': ('longitud_um', 'area_um2'),
    'reescalar_percentiles': ('intensidad_inferior', 'intensidad_superior'),
    'variantes_contraste': ('intensidad_inferior', 'intensidad_superior'),
    'agregar_ruido': ('pixeles_recortados',),
    'evaluar_referencia': ('psnr_db', 'ssim'),
    'limpiar_mascara': ('pixeles_eliminados', 'pixeles_agregados'),
    'umbralizar': ('umbral_otsu', 'umbral_manual'),
    'etiquetar_componentes': ('numero_objetos',),
    'limites_a_regiones': ('numero_objetos',),
    'separar_watershed': ('numero_objetos', 'numero_marcadores', 'marcadores_automaticos_rescate'),
    'segmentar_clases': ('numero_clases', 'umbrales'),
    'evaluar_mascara': ('dice', 'iou'),
    'propiedades_basicas': ('numero_objetos', 'area_roi_um2'),
    'descriptores_forma': ('numero_objetos',),
    'medir_objetos': ('numero_objetos_aceptados', 'numero_objetos_descartados', 'densidad_objetos_aceptados_mm2'),
    'densidad_jeffries': ('conteo_ponderado', 'densidad_ponderada_mm2'),
    'fracciones_area': ('pixeles_roi', 'pixeles_excluidos'),
    'intercepto_medio': ('intersecciones_totales', 'longitud_media_um'),
    'intervalo_bootstrap_media': ('media', 'intervalo_percentil', 'numero_unidades'),
    'reporte_fraccion_area': ('media', 'intervalo_percentil', 'numero_unidades'),
}

PESTANA_PREFERIDA = {
    'histograma_percentiles': 'grafica', 'perfil_intensidad': 'grafica',
    'intervalo_bootstrap_media': 'grafica', 'reporte_fraccion_area': 'grafica',
    'propiedades_basicas': 'tabla', 'descriptores_forma': 'tabla', 'medir_objetos': 'tabla',
    'densidad_jeffries': 'tabla', 'fracciones_area': 'tabla', 'intercepto_medio': 'tabla',
}

METADATOS = (
    ('muestra_id', 'Identificador de la muestra', 'Ej.: P-07'),
    ('campo_id', 'Campo', 'Ej.: campo 3, zona central'),
    ('material_declarado', 'Material declarado', 'Solo si está documentado'),
    ('condicion_declarada', 'Condición o tratamiento', 'Solo si está documentado'),
    ('microscopio', 'Microscopio', 'Modelo y configuración'),
    ('objetivo', 'Objetivo', 'Ej.: 20×/0.45'),
    ('orientacion_declarada', 'Orientación declarada', 'Ej.: sección transversal'),
    ('responsable', 'Responsable', 'Nombre de quien revisa'),
    ('notas', 'Notas', ''),
)

PASOS_GUIA = tuple(
    (paso['id'], {'preparar': 'Preparar', 'refinar': 'Refinar'}.get(paso['id'], paso['titulo']),
     paso['descripcion'], icono)
    for paso, icono in zip(PASOS_APRENDIZAJE,
                           ('importar', 'regla', 'recortar', 'varita', 'segmentar', 'mascara', 'objetos', 'exportar'))
)

ATAJOS = (
    ('Ctrl+K', 'Buscar herramientas, datos y acciones'),
    ('Ctrl+Enter', 'Ejecutar la herramienta actual'),
    ('Ctrl+I', 'Importar una imagen'),
    ('Ctrl+O', 'Abrir una sesión'),
    ('Ctrl+S', 'Guardar la sesión'),
    ('Ctrl+N', 'Nueva sesión'),
    ('Ctrl+U', 'Usar la salida seleccionada como dato activo'),
    ('Ctrl+F', 'Buscar en la lista de herramientas'),
    ('Ctrl+B', 'Mostrar u ocultar la barra lateral'),
    ('Ctrl+Shift+I', 'Mostrar u ocultar el inspector'),
    ('Ctrl+J', 'Mostrar u ocultar el panel de resultados'),
    ('H', 'Herramienta Mover'),
    ('R', 'Dibujar una región (ROI)'),
    ('L', 'Regla: medir una distancia'),
    ('P', 'Dibujar un perfil de intensidad'),
    ('F o Ctrl+0', 'Ajustar la imagen a la ventana'),
    ('Ctrl+1', 'Tamaño real (100 %)'),
    ('Ctrl++ / Ctrl+-', 'Acercar o alejar'),
    ('Esc', 'Cancelar la herramienta de dibujo'),
    ('F1', 'Guía de trabajo'),
)

# Errores frecuentes de la biblioteca con una sugerencia y una acción de la interfaz.
SUGERENCIAS_ERROR = (
    ('Confirme primero que la región de análisis', 'Falta confirmar la región de análisis',
     'Revise que la entrada no contenga la barra de escala ni anotaciones y confirme la ROI. Si la imagen las incluye, recórtela primero.',
     (('Confirmar ROI…', 'confirmar_roi'), ('Recortar ROI', 'recortar'))),
    ('Asocie una calibración a este dato', 'El dato no tiene escala',
     'Las medidas físicas requieren una escala asociada al dato de entrada.',
     (('Calibrar escala…', 'calibrar'),)),
    ('El parámetro de escala no coincide', 'La escala no coincide',
     'El parámetro de escala debe ser igual a la calibración asociada al dato de entrada.',
     (('Usar la escala del dato', 'escala_dato'),)),
    ('Falta seleccionar', 'Falta una entrada', 'Elija el dato de entrada en el inspector.', ()),
    ('Falta la entrada', 'Falta una entrada', 'Elija el dato de entrada en el inspector.', ()),
    ('requiere tipos', 'Tipo de dato incompatible',
     'La entrada elegida no tiene el tipo que espera esta herramienta.', ()),
    ('Complete el parámetro', 'Falta un parámetro', 'Complete el campo resaltado.', ()),
    ('Proporcione ambas incertidumbres', 'Incertidumbres incompletas',
     'Indique las dos incertidumbres estándar o deje ambas vacías.', ()),
    ('Los marcadores deben estar dentro', 'Marcadores fuera de la máscara',
     'Cada marcador debe caer dentro de la máscara que supera el filtro de área.', ()),
    ('Cada componente de la máscara necesita', 'Faltan marcadores',
     'Cada componente de la máscara necesita al menos un marcador. Pruebe con marcadores automáticos.', ()),
)


def sugerencia_error(mensaje: str):
    for patron, titulo, texto, acciones in SUGERENCIAS_ERROR:
        if patron in mensaje:
            return titulo, texto, acciones
    return None


def meta_parametro(id_operacion: str, nombre: str) -> dict:
    meta = dict(PARAMETROS.get(nombre, {'etiqueta': etiqueta_generica(nombre)}))
    meta.update(AJUSTES_OPERACION.get((id_operacion, nombre), {}))
    return meta


def etiqueta_generica(nombre: str) -> str:
    texto = nombre.replace('_', ' ').strip()
    return texto[:1].upper() + texto[1:]


def nombre_salida(clave: str) -> str:
    return SALIDAS.get(clave, etiqueta_generica(clave))


def nombre_tipo(tipo: str) -> str:
    return TIPOS.get(tipo, {}).get('nombre', etiqueta_generica(tipo))


def etiqueta_columna(nombre) -> str:
    return COLUMNAS.get(str(nombre), etiqueta_generica(str(nombre)))


def etiqueta_clave(nombre: str) -> str:
    return CLAVES.get(nombre, etiqueta_generica(nombre))


def etiqueta_opcion(parametro: str, valor) -> str:
    return OPCIONES.get(parametro, {}).get(valor, str(valor))


def formatear_numero(valor, cifras: int = 6) -> str:
    if isinstance(valor, bool):
        return 'Sí' if valor else 'No'
    if isinstance(valor, numbers.Integral):
        texto = f'{int(valor):,}'.replace(',', ' ')
        return texto
    if isinstance(valor, numbers.Real):
        v = float(valor)
        if math.isnan(v):
            return 'indefinido'
        if math.isinf(v):
            return '∞' if v > 0 else '−∞'
        if v != 0 and (abs(v) >= 1e6 or abs(v) < 1e-4):
            return f'{v:.{cifras - 1}e}'.replace('e-0', 'e-').replace('e+0', 'e+')
        texto = f'{v:.{cifras}g}'
        return texto
    return str(valor)


def formatear_valor(valor) -> str:
    """Texto legible para un valor del resumen; no altera el dato guardado."""
    if valor is None:
        return '—'
    if isinstance(valor, str):
        if valor in ('NaN',):
            return 'indefinido'
        return valor
    if isinstance(valor, dict):
        return '; '.join(f'{etiqueta_clave(str(k))}: {formatear_valor(v)}' for k, v in valor.items())
    if isinstance(valor, (list, tuple)):
        if len(valor) == 2 and all(isinstance(x, numbers.Real) and not isinstance(x, bool) for x in valor):
            return f'{formatear_numero(valor[0])} – {formatear_numero(valor[1])}'
        return '[' + ', '.join(formatear_valor(x) for x in valor) + ']'
    if hasattr(valor, 'item') and not isinstance(valor, (list, tuple, dict)):
        try:
            return formatear_numero(valor.item())
        except Exception:
            return str(valor)
    return formatear_numero(valor)


def descripcion_dato(artefacto) -> str:
    forma = artefacto.datos.shape
    if len(forma) >= 2:
        tam = f'{forma[1]}×{forma[0]} px'
        if len(forma) == 3:
            tam += f' · {forma[2]} canales'
    else:
        tam = f'{forma[0]} valores'
    return f'{nombre_tipo(artefacto.tipo)} · {tam}'
