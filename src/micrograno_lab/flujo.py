"""Orden de aprendizaje y orientación de la interfaz, sin dependencias de Qt.

La biblioteca sigue validando cada ejecución. Estas comprobaciones anticipan
requisitos de entradas y contexto que la interfaz puede explicar sin calcular.
"""
from __future__ import annotations

from micrograno.catalogo import CATALOGO


PASOS_APRENDIZAJE = (
    {
        'id': 'imagen', 'titulo': 'Imagen',
        'descripcion': 'Importe una micrografía o abra el ejemplo. Inspeccione la imagen original; todas sus versiones se conservarán.',
        'operaciones': ('explorar_imagen',),
    },
    {
        'id': 'escala', 'titulo': 'Escala',
        'descripcion': 'Mida una referencia conocida en la imagen original y aplique la escala antes de recortar su barra. Puede continuar sin escala si todavía no medirá longitudes o áreas físicas.',
        'operaciones': ('calibrar_escala', 'convertir_medidas'),
    },
    {
        'id': 'grises_roi', 'titulo': 'Grises y ROI',
        'descripcion': 'Convierta a grises, recorte la región de interés y confirme que no contiene texto ni barra de escala. El recorte conserva el tamaño de píxel.',
        'operaciones': ('convertir_grises', 'extraer_roi', 'separar_canales'),
    },
    {
        'id': 'preparar', 'titulo': 'Preparar (opcional)',
        'descripcion': 'Examine las intensidades y compare tratamientos de contraste, ruido o iluminación cuando la imagen lo necesite. Elija una variante para continuar.',
        'operaciones': (
            'histograma_percentiles', 'perfil_intensidad', 'reescalar_percentiles',
            'variantes_contraste', 'variantes_ruido', 'corregir_iluminacion',
            'top_hat', 'realzar_sobel', 'evaluar_referencia',
            'reducir_y_ampliar', 'cuantizar', 'agregar_ruido',
        ),
    },
    {
        'id': 'segmentar', 'titulo': 'Segmentar',
        'descripcion': 'Elija qué representar: una máscara por umbral, clases de intensidad o una red de límites. Revise la salida sobre su imagen antes de medir.',
        'operaciones': ('umbralizar', 'segmentar_clases', 'detectar_canny'),
    },
    {
        'id': 'refinar', 'titulo': 'Refinar y separar',
        'descripcion': 'Limpie la máscara elegida y asigne identificadores a sus objetos. Use watershed si necesita separar regiones que se tocan; compruebe las separaciones.',
        'operaciones': (
            'limpiar_mascara', 'variantes_morfologicas', 'invertir_mascara',
            'extraer_clase', 'etiquetar_componentes', 'separar_watershed',
            'esqueletizar', 'limites_a_regiones', 'obtener_limites', 'evaluar_mascara',
        ),
    },
    {
        'id': 'medir', 'titulo': 'Medir',
        'descripcion': 'Mida objetos etiquetados con escala, fracciones de clases o intercepciones de límites. La estadística utiliza valores de campos o probetas independientes.',
        'operaciones': (
            'medir_objetos', 'propiedades_basicas', 'descriptores_forma',
            'fracciones_area', 'intercepto_medio', 'densidad_jeffries',
            'intervalo_bootstrap_media', 'reporte_fraccion_area',
        ),
    },
    {
        'id': 'exportar', 'titulo': 'Exportar',
        'descripcion': 'Exporte todas las versiones y tablas. Guarde también la sesión reproducible para reabrir el análisis y conservar su código.',
        'operaciones': (),
    },
)

_TIPOS = {
    'imagen': 'imagen', 'gris': 'imagen en grises', 'mascara': 'máscara',
    'limites': 'límites', 'etiquetas': 'objetos etiquetados',
    'clases': 'clases de intensidad', 'marcadores': 'marcadores',
    'mapa': 'mapa numérico', 'valores': 'valores por campo o probeta',
    'distribucion': 'distribución de remuestreo',
}

_SALIDAS = {
    'original': 'Original', 'gris': 'Grises', 'roi': 'ROI',
    'rojo': 'Canal rojo', 'verde': 'Canal verde', 'azul': 'Canal azul',
    'estirada': 'Contraste por percentiles', 'ecualizacion_global': 'Ecualización global',
    'clahe': 'Contraste CLAHE', 'media': 'Filtro de media', 'gaussiano': 'Filtro gaussiano',
    'mediana': 'Filtro de mediana', 'bilateral': 'Filtro bilateral',
    'manual': 'Máscara manual', 'otsu': 'Máscara Otsu', 'adaptativa': 'Máscara adaptativa',
    'limpia': 'Máscara limpia', 'mascara': 'Máscara', 'etiquetas': 'Objetos etiquetados',
    'clases': 'Clases de intensidad', 'limites': 'Límites', 'marcadores': 'Marcadores',
    'distancia': 'Distancia al borde', 'esqueleto': 'Límites adelgazados',
    'reducida': 'Muestreo reducido', 'ampliada': 'Muestreo ampliado',
    'cuantizada': 'Intensidad cuantizada', 'con_ruido': 'Ruido sintético',
    'medias_remuestreadas': 'Medias bootstrap',
}


def etapa_de_operacion(operacion: str) -> int:
    """Índice de etapa, desde cero; una operación desconocida vuelve al inicio."""
    return next((i for i, paso in enumerate(PASOS_APRENDIZAJE)
                 if operacion in paso['operaciones']), 0)


def razon_bloqueo(sesion, operacion: str, entradas: dict | None = None) -> str:
    """Explica el primer requisito pendiente; no sustituye la validación científica.

    ``entradas`` contiene roles del catálogo e identificadores de artefactos.
    No exige una imagen para las operaciones que solo reciben parámetros.
    Las dimensiones iguales son necesarias, pero no acreditan alineación física.
    """
    if operacion not in CATALOGO:
        return 'Seleccione una función de la biblioteca.'
    op = CATALOGO[operacion]
    ids = {rol: id_ for rol, id_ in (entradas or {}).items() if id_ is not None}
    roles = {entrada.nombre for entrada in op.entradas}
    if set(ids) - roles:
        return 'Hay una entrada que no corresponde a esta función.'
    seleccionadas = []
    for entrada in op.entradas:
        id_ = ids.get(entrada.nombre)
        tipos = ' o '.join(_TIPOS[tipo] for tipo in entrada.tipos)
        if id_ is None:
            if entrada.opcional:
                continue
            return f'Seleccione {entrada.nombre}: se requiere {tipos}.'
        dato = sesion.artefactos.get(id_)
        if dato is None:
            return f'La versión seleccionada como {entrada.nombre} ya no está disponible.'
        if dato.tipo not in entrada.tipos:
            return (f'{entrada.nombre.capitalize()} requiere {tipos}; '
                    f'la versión seleccionada contiene {_TIPOS.get(dato.tipo, dato.tipo)}.')
        seleccionadas.append(dato)
    principal = seleccionadas[0] if seleccionadas else None
    excepciones_roi = {'explorar_imagen', 'convertir_grises', 'separar_canales', 'extraer_roi'}
    if (principal is not None and principal.tipo != 'valores'
            and operacion not in excepciones_roi
            and not principal.metadatos.get('roi_confirmada', False)):
        return 'Confirme la ROI de esta versión: revise que excluya la barra de escala y las anotaciones.'
    if (principal is not None and 's_um_px' in op.parametros
            and not principal.metadatos.get('escala')):
        return 'Asocie una escala a esta versión antes de medir en µm o µm².'
    if operacion == 'separar_canales' and principal.datos.ndim != 3:
        return 'Comparar canales necesita una imagen RGB o RGBA opaca; elija la versión original en color.'
    if operacion in {'evaluar_referencia', 'evaluar_mascara', 'separar_watershed', 'fracciones_area'}:
        if len(seleccionadas) > 1 and any(
                dato.datos.shape != principal.datos.shape for dato in seleccionadas[1:]):
            return 'Las entradas deben tener la misma forma y representar la misma región alineada.'
    return ''


def _numero_version(sesion, id_: str) -> str:
    # El ID identifica la versión incluso si se importaron fuentes entre pasos.
    if id_.startswith('a') and id_[1:].isdigit():
        return f'{int(id_[1:]):02d}'
    return f'{tuple(sesion.artefactos).index(id_) + 1:02d}'


def nombre_version(sesion, id_: str) -> str:
    """Etiqueta breve y estable; nunca cambia el nombre ni el contenido del dato."""
    dato = sesion.artefactos[id_]
    if id_ in sesion.fuentes:
        etiqueta = 'Original' if dato.tipo in ('imagen', 'gris') else _TIPOS[dato.tipo].capitalize()
    else:
        salida = dato.metadatos.get('salida', '')
        etiqueta = _SALIDAS.get(salida, salida.replace('_', ' ').capitalize())
        if salida == 'limpia' and dato.tipo == 'limites':
            etiqueta = 'Límites limpios'
        if not etiqueta:
            etiqueta = _TIPOS[dato.tipo].capitalize()
    return f'{_numero_version(sesion, id_)} · {etiqueta}'


def origen_version(sesion, id_: str) -> str:
    """Procedencia legible, operación y versiones de entrada para el detalle."""
    dato = sesion.artefactos[id_]
    if id_ in sesion.fuentes:
        procedencia = dato.metadatos.get('procedencia', '')
        texto = f'Fuente: {dato.nombre} · {_TIPOS[dato.tipo]}.'
        if procedencia and procedencia != 'No declarada':
            texto += f' {procedencia}'
        return texto
    paso = next((paso for paso in sesion.pasos if id_ in paso['salidas'].values()), None)
    if paso is None:
        return f'{dato.nombre} · {_TIPOS[dato.tipo]}.'
    padres = ', '.join(f'{rol}: {nombre_version(sesion, padre)}'
                       for rol, padre in paso['entradas'].items())
    titulo = CATALOGO[paso['operacion']].titulo
    return f'{titulo} · {_TIPOS[dato.tipo]}. Entrada: {padres or "parámetros"}.'


def explicacion_entradas(operacion: str) -> str:
    """Contrato de entrada del catálogo en lenguaje de la interfaz."""
    op = CATALOGO[operacion]
    if not op.entradas:
        return 'Esta función usa los valores introducidos en los parámetros; no recibe una imagen.'
    partes = []
    for entrada in op.entradas:
        tipos = ' o '.join(_TIPOS[tipo] for tipo in entrada.tipos)
        partes.append(f'{entrada.nombre}: {tipos}' + (' (opcional)' if entrada.opcional else ''))
    return 'Entrada · ' + '; '.join(partes) + '.'


def explicacion_salida(operacion: str) -> str:
    """Explica qué hacer con el resultado, incluidas funciones sin imagen de salida."""
    if operacion == 'calibrar_escala':
        return 'Salida · Escala en µm/px. Aplíquela a la imagen cuya referencia midió; las versiones ya calculadas conservan su escala anterior.'
    if operacion in {
        'histograma_percentiles', 'perfil_intensidad', 'convertir_medidas',
        'propiedades_basicas', 'descriptores_forma', 'densidad_jeffries', 'fracciones_area',
    }:
        return 'Salida · Medidas o resumen del cálculo. Consulte los resultados; la imagen de entrada se conserva.'
    if operacion in {'intervalo_bootstrap_media', 'reporte_fraccion_area'}:
        return 'Salida · Resumen estadístico y distribución de medias remuestreadas. Esta distribución no representa nuevos campos independientes.'
    if operacion == 'umbralizar':
        return 'Salida · Máscaras manual, Otsu y adaptativa. Compare las alternativas y elija una para limpiar o separar objetos.'
    if operacion == 'segmentar_clases':
        return 'Salida · Clases de intensidad. Puede medir su fracción de área o extraer una clase como máscara; no son identificaciones de fases.'
    if operacion == 'separar_watershed':
        return 'Salida · Máscara, distancia, marcadores, objetos etiquetados y límites. Elija los objetos etiquetados para medir tamaño y forma.'
    return 'Salida · Se guardan nuevas versiones y los resultados de la función. Seleccione la versión que desea usar en el paso siguiente.'
