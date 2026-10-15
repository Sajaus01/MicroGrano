"""Catálogo único para API, formularios, ayudas, documentación y pruebas de cobertura."""
from __future__ import annotations
from dataclasses import dataclass, field
from inspect import signature, getdoc, Parameter
from typing import Any, Callable
from . import nucleo
from .modelos import Resultado, EscalaEspacial

@dataclass(frozen=True)
class Entrada:
    nombre: str
    tipos: tuple[str,...]
    ayuda: str
    opcional: bool = False

@dataclass(frozen=True)
class Operacion:
    id: str
    titulo: str
    grupo: str
    libro: str
    entradas: tuple[Entrada,...]
    referencias: tuple[str,...] = ()
    opciones: dict[str,tuple] = field(default_factory=dict)

    @property
    def funcion(self) -> Callable:
        return getattr(nucleo,self.id)

    @property
    def ayuda(self) -> str:
        return getdoc(self.funcion) or ''

    @property
    def parametros(self) -> dict:
        roles = {e.nombre for e in self.entradas}
        return {n:p for n,p in signature(self.funcion).parameters.items() if n not in roles}

    def ejemplo(self) -> str:
        """Ejemplo ejecutable con datos sintéticos y parámetros completos."""
        from .sinteticos import crear_conjunto, casos_catalogo
        ids = {nombre: f"datos[{nombre!r}]" for nombre in crear_conjunto()}
        entradas, parametros = casos_catalogo(ids)[self.id]
        if 's_um_px' in self.parametros and 's_um_px' not in parametros:
            parametros['s_um_px'] = 0.5
        parametros = resolver_parametros(self.id, parametros)
        argumentos = [f'{nombre}={expresion}' for nombre,expresion in entradas.items()]
        argumentos += [f'{nombre}={valor!r}' for nombre,valor in parametros.items()]
        cierre = ('print(resultado.como_dict())' if self.id == 'calibrar_escala' else
                  'print(resultado.resumen)\nprint(list(resultado.datos))\nprint(resultado.tabla.head())')
        return ('from micrograno import nucleo as mg\n'
                'from micrograno.sinteticos import crear_conjunto\n\n'
                '# Prueba sintética: no son parámetros ni resultados de una micrografía real.\n'
                '# La escala 0.5 µm/px, cuando aparece, es solo una convención de prueba.\n'
                'datos = crear_conjunto()\n'
                f'resultado = mg.{self.id}(\n    ' + ',\n    '.join(argumentos) +
                '\n)\n' + cierre)


def E(nombre,*tipos,opcional=False,ayuda=''):
    return Entrada(nombre,tipos,ayuda or f'Entrada {nombre}: '+', '.join(tipos),opcional)

I = lambda nombre='imagen': E(nombre,'gris')
M = lambda nombre='mascara': E(nombre,'mascara','limites')
L = lambda nombre='etiquetas': E(nombre,'etiquetas')
R = lambda nombre='imagen': E(nombre,'imagen','gris')
G2='Imagen y calibración'
G3='Preprocesamiento'
GM='Máscaras y morfología'
G4='Segmentación'
G5='Conteo y características'
GE='Estadística'

_OPERACIONES = [
    Operacion('explorar_imagen','Inspeccionar imagen',G2,'2.1',(R(),),('HarrisEtAl2020',)),
    Operacion('convertir_grises','Convertir a escala de grises',G2,'2.5',(R(),),('VanDerWaltEtAl2014',)),
    Operacion('separar_canales','Comparar canales RGB',G2,'2.5',(R(),),('GonzalezWoods2018',)),
    Operacion('extraer_roi','Seleccionar región de interés',G2,'2.2',(R(),),('AaronChew2021',)),
    Operacion('reducir_y_ampliar','Demostrar cambio de muestreo',G2,'2.3',(I(),),('Shannon1949',)),
    Operacion('cuantizar','Reducir niveles de intensidad',G2,'2.4',(I(),),('GonzalezWoods2018',)),
    Operacion('histograma_percentiles','Histograma y percentiles',G2,'2.6',(I(),),('GonzalezWoods2018',)),
    Operacion('perfil_intensidad','Perfil de intensidad',G2,'3.3–3.5; apoyo',(I(),),('AaronChew2021',)),
    Operacion('calibrar_escala','Calibrar escala espacial',G2,'2.7',(),('ASTM_E1951_2019','JCGM1002008')),
    Operacion('convertir_medidas','Convertir longitud y área',G2,'2.7',(),('JCGM1002008',)),
    Operacion('reescalar_percentiles','Estirar por percentiles',G3,'3.2',(I(),),('GonzalezWoods2018',)),
    Operacion('variantes_contraste','Comparar contraste',G3,'3.2',(I(),),('PizerEtAl1987','Zuiderveld1994')),
    Operacion('variantes_ruido','Comparar filtros de ruido',G3,'3.3',(I(),),('TomasiManduchi1998',)),
    Operacion('agregar_ruido','Añadir ruido sintético',G3,'3.3; apoyo',(I(),),('WangEtAl2004',)),
    Operacion('evaluar_referencia','PSNR y SSIM con referencia',G3,'3.3',(I('referencia'),I('candidata')),('WangEtAl2004',)),
    Operacion('corregir_iluminacion','Corregir iluminación',G3,'3.4',(I(),),('Sternberg1983',)),
    Operacion('top_hat','Residuos morfológicos claro y oscuro',G3,'3.4',(I(),),('Soille2004',)),
    Operacion('realzar_sobel','Componentes y magnitud de Sobel',G3,'3.5',(I(),),('GonzalezWoods2018',)),
    Operacion('variantes_morfologicas','Comparar morfología',GM,'3.6',(M(),),('Serra1982','Soille2004')),
    Operacion('limpiar_mascara','Filtrar por área y rellenar huecos',GM,'4.4 y 5.5',(M(),),('ScikitImageDocs2026',)),
    Operacion('invertir_mascara','Invertir primer plano',GM,'4.1; apoyo',(M(),)),
    Operacion('esqueletizar','Adelgazar red de límites',GM,'5.3; apoyo',(M('limites'),),('Soille2004',)),
    Operacion('umbralizar','Comparar umbrales',G4,'4.2',(I(),),('Otsu1979',),{'polaridad':('clara','oscura')}),
    Operacion('detectar_canny','Detectar límites candidatos con Canny',G4,'4.3',(I(),),('Canny1986',)),
    Operacion('etiquetar_componentes','Etiquetar componentes conexas',G4,'5.2',(M(),),('ScikitImageDocs2026',)),
    Operacion('limites_a_regiones','Obtener regiones de una red',G4,'4.3–4.4; apoyo',(M('limites'),),('Soille2004',)),
    Operacion('separar_watershed','Separar por watershed',G4,'4.4',
        (M(),E('marcadores','marcadores','etiquetas',opcional=True)),('Meyer1994','ScikitImageDocs2026')),
    Operacion('segmentar_clases','Clases de intensidad por multi-Otsu',G4,'4.5',(I(),),('LiaoChenChung2001',)),
    Operacion('extraer_clase','Extraer una clase como máscara',G4,'4.5; apoyo',(E('clases','clases'),)),
    Operacion('obtener_limites','Contornos de objetos etiquetados',G4,'4.4 y 5.3',(L(),),
        ('ScikitImageDocs2026',),{'modo':('thick','inner','outer')}),
    Operacion('evaluar_mascara','Dice e IoU con referencia',G4,'4.7; apoyo',
        (M('referencia'),M('candidata')),('ScikitImageDocs2026',)),
    Operacion('propiedades_basicas','Medir propiedades básicas',G5,'5.2',(L(),),('ScikitImageDocs2026',)),
    Operacion('descriptores_forma','Medir tamaño y forma',G5,'5.6',(L(),),('RussNeal2016',)),
    Operacion('medir_objetos','Filtrar, contar y medir objetos',G5,'5.5',(L(),),('RussNeal2016',),{'regla_marco':('excluir','conservar')}),
    Operacion('densidad_jeffries','Ponderación planimétrica ilustrativa',G5,'5.3.2',(L(),),('ASTM_E112_2025','ASTM_E1382_2023')),
    Operacion('fracciones_area','Fracción de área por clase',G5,'5.4',
        (E('clases','clases'),E('roi','mascara',opcional=True)),('Underwood1970',)),
    Operacion('intercepto_medio','Intercepción lineal',G5,'5.3.1',(M('limites'),),
        ('ASTM_E112_2025','ASTM_E1382_2023'),
        {'orientaciones':('ambas','horizontal','vertical'),'extremos':('excluir','incluir')}),
    Operacion('intervalo_bootstrap_media','Intervalo bootstrap de la media',GE,'5.7',
        (E('valores','valores'),),('EfronTibshirani1993',),{'unidad_analisis':('campo','probeta','unidad_independiente')}),
    Operacion('reporte_fraccion_area','Resumen de fracciones por campo',GE,'5.7',
        (E('valores','valores'),),('EfronTibshirani1993','GundersenJensen1987'),
        {'unidad_analisis':('campo','probeta','unidad_independiente')}),
]
CATALOGO = {op.id:op for op in _OPERACIONES}

AYUDA_PARAMETROS = {
    's_um_px':'Factor isotrópico verificado en µm/px. No use el aumento nominal.',
    'radio_px':'Radio del disco en píxeles. El diámetro es 2*radio+1.',
    'radio':'Radio de la bola rodante en píxeles. El coste aumenta con radio e imagen.',
    'area_minima':'Se conservan áreas de este número de píxeles o mayores.',
    'hueco_maximo':'Se rellenan huecos cerrados de este tamaño o menores; 0 desactiva.',
    'conectividad':'1: cuatro vecinos; 2: ocho vecinos. Mantenga la misma regla en el análisis.',
    'min_distance':'Separación mínima entre picos candidatos en píxeles; no es diámetro de grano.',
    'tile':'Lado de la región local de CLAHE, en píxeles.',
    'clip_limit':'Límite normalizado del histograma en CLAHE.',
    'sigma':'Desviación estándar del suavizado en px; en ruido sintético, unidades de intensidad.',
    'sigma_color':'Tolerancia de intensidad del bilateral para entradas [0,1].',
    'sigma_spatial':'Escala espacial del bilateral en píxeles.',
    'manual':'Umbral global de intensidad normalizada.',
    'bloque':'Lado impar de la ventana de media local, en píxeles.',
    'desplazamiento':'Se resta de la media local: T = media - desplazamiento.',
    'bajo':'Umbral inferior de Canny en la representación normalizada.',
    'alto':'Umbral superior de Canny, mayor que el inferior.',
    'p_bajo':'Percentil inferior, entre 0 y 100.',
    'p_alto':'Percentil superior, mayor que el inferior.',
    'r0':'Fila inicial; incluida en la ROI.', 'r1':'Fila final; excluida de la ROI (en perfiles es un centro de píxel).',
    'c0':'Columna inicial; incluida en la ROI.', 'c1':'Columna final; excluida de la ROI (en perfiles es un centro de píxel).',
    'referencia_um':'Longitud física documentada de la referencia en µm.',
    'referencia_px':'Distancia en píxeles entre los extremos medidos.',
    'incertidumbre_um':'Incertidumbre estándar de la referencia física, no expandida; opcional.',
    'incertidumbre_px':'Incertidumbre estándar de la distancia en píxeles; opcional.',
    'incertidumbre_s':'Incertidumbre estándar de la escala en µm/px; opcional.',
    'referencia':'Identificador del patrón, configuración o procedencia de la escala.',
    'longitud_px':'Longitud en píxeles a convertir.', 'area_px2':'Área en píxeles cuadrados a convertir.',
    'bits_salida':'Número de bits simulados, entre 1 y 16.',
    'factor':'Factor entero de reducción, al menos 2; demostración, no mejora óptica.',
    'bins':'Número de intervalos del histograma en [0,1].',
    'clases':'Número de clases de intensidad, 2 a 4; ninguna se identifica automáticamente.',
    'clase':'Identificador de la clase que se convertirá en máscara; cero puede ser válido.',
    'numero_lineas':'Número de líneas por orientación, sin duplicados.',
    'repeticiones':'Número de remuestreos; al menos 100.',
    'semilla':'Semilla entera para repetir exactamente el muestreo.',
    'confianza':'Cobertura nominal del intervalo, por ejemplo 0.95; no es una garantía de exactitud.',
    'excluir_abiertas':'Descarta regiones conectadas al marco; puede excluir perfiles truncados válidos.',
    'orientaciones':'Direcciones de prueba; se conservan sus resultados separados.',
    'extremos':'Tratamiento de corridas que alcanzan el extremo de una línea.',
    'modo':'Grosor/localización del contorno: thick, inner u outer.',
    'regla_marco':'Conservar o excluir instancias que tocan el marco de la ROI.',
    'polaridad':'Clara: I>T; oscura: I<=T. Compruebe qué representa el primer plano.',
    'unidad_analisis':'Unidad que aporta cada valor; su independencia debe venir del diseño del estudio.',
}


def resolver_parametros(id_operacion: str, parametros: dict | None = None) -> dict:
    op = CATALOGO[id_operacion]
    p = dict(parametros or {})
    desconocidos = set(p)-set(op.parametros)
    if desconocidos:
        raise ValueError(f'Parámetros desconocidos: {sorted(desconocidos)}')
    for n,definicion in op.parametros.items():
        if n not in p:
            if definicion.default is Parameter.empty:
                raise ValueError(f'Falta el parámetro obligatorio {n}.')
            p[n] = definicion.default
    return p


def ejecutar(id_operacion: str, entradas: dict | None = None,
             parametros: dict | None = None) -> Resultado:
    """Invoca únicamente una función registrada; nunca evalúa código recibido."""
    if id_operacion not in CATALOGO:
        raise ValueError(f'Operación desconocida: {id_operacion}')
    op = CATALOGO[id_operacion]
    e = dict(entradas or {})
    if set(e)-{x.nombre for x in op.entradas}:
        raise ValueError('Se recibieron nombres de entrada no declarados.')
    for x in op.entradas:
        if e.get(x.nombre) is None and not x.opcional:
            raise ValueError(f'Falta la entrada {x.nombre}.')
    r = op.funcion(**e,**resolver_parametros(id_operacion,parametros))
    if isinstance(r,EscalaEspacial):
        r = Resultado(resumen=r.como_dict(),advertencias=[
            'Escala isotrópica. Aplique el factor solo a la imagen y configuración verificadas.'])
    if not isinstance(r,Resultado):
        raise TypeError('La operación no produjo un Resultado válido.')
    return r


def verificar_catalogo() -> None:
    """Comprueba que toda la API científica está accesible y documentada."""
    if set(CATALOGO) != set(nucleo.__all__):
        raise AssertionError('La API y el catálogo no cubren las mismas funciones.')
    for op in CATALOGO.values():
        firma = signature(op.funcion)
        if not op.ayuda or not op.libro:
            raise AssertionError(f'Falta ayuda o correspondencia: {op.id}')
        for entrada in op.entradas:
            if entrada.nombre not in firma.parameters:
                raise AssertionError(f'Entrada inexistente: {op.id}/{entrada.nombre}')
        for nombre in op.parametros:
            if nombre not in AYUDA_PARAMETROS:
                raise AssertionError(f'Falta ayuda de parámetro: {op.id}/{nombre}')
