"""Contratos del flujo didáctico, sin cargar Qt ni crear ventanas."""
import numpy as np
import pytest

from micrograno import EscalaEspacial, Sesion
from micrograno.catalogo import CATALOGO
from micrograno.sinteticos import casos_catalogo, poblar_sesion
from micrograno_lab.flujo import (
    PASOS_APRENDIZAJE, etapa_de_operacion, razon_bloqueo,
    nombre_version, origen_version, explicacion_entradas, explicacion_salida,
)


def test_flujo_cubre_catalogo_una_vez_en_orden_de_dependencia():
    operaciones = [op for paso in PASOS_APRENDIZAJE for op in paso['operaciones']]
    assert len(PASOS_APRENDIZAJE) == 8
    assert len(operaciones) == len(set(operaciones))
    assert set(operaciones) == set(CATALOGO)
    assert etapa_de_operacion('calibrar_escala') < etapa_de_operacion('extraer_roi')
    assert etapa_de_operacion('umbralizar') < etapa_de_operacion('limpiar_mascara')
    assert etapa_de_operacion('etiquetar_componentes') < etapa_de_operacion('medir_objetos')
    assert etapa_de_operacion('desconocida') == 0


def test_requisitos_siguen_casos_validos_del_catalogo():
    sesion = Sesion()
    casos = casos_catalogo(poblar_sesion(sesion))
    for operacion, (entradas, _) in casos.items():
        assert razon_bloqueo(sesion, operacion, entradas) == '', operacion
        assert explicacion_entradas(operacion)
        assert explicacion_salida(operacion)


def test_calibracion_y_conversion_manual_no_necesitan_imagen():
    sesion = Sesion()
    assert razon_bloqueo(sesion, 'calibrar_escala', {}) == ''
    assert razon_bloqueo(sesion, 'convertir_medidas', {}) == ''


def test_precondiciones_anticipan_roi_escala_y_tipo_sin_modificar_fuente():
    sesion = Sesion()
    original = sesion.agregar(np.eye(8, dtype=np.uint8), 'imagen', 'Micrografía')
    assert razon_bloqueo(sesion, 'convertir_grises', {'imagen': original}) == ''
    assert razon_bloqueo(sesion, 'extraer_roi', {'imagen': original}) == ''
    assert 'grises' in razon_bloqueo(sesion, 'umbralizar', {'imagen': original})
    _, versiones = sesion.ejecutar('convertir_grises', {'imagen': original})
    gris = versiones['gris']
    assert 'Confirme la ROI' in razon_bloqueo(sesion, 'umbralizar', {'imagen': gris})
    sesion.confirmar_roi(gris, 'Región sintética sin anotaciones')
    assert razon_bloqueo(sesion, 'umbralizar', {'imagen': gris}) == ''
    objetos = sesion.agregar(np.eye(8, dtype=np.int32), 'etiquetas', 'Objetos')
    sesion.confirmar_roi(objetos, 'Región sintética sin anotaciones')
    assert 'escala' in razon_bloqueo(sesion, 'medir_objetos', {'etiquetas': objetos})
    sesion.establecer_escala(objetos, EscalaEspacial(0.5))
    assert razon_bloqueo(sesion, 'medir_objetos', {'etiquetas': objetos}) == ''
    assert sesion.artefactos[original].metadatos['escala'] is None


def test_referencia_debe_elegirse_y_tener_misma_forma():
    sesion = Sesion()
    a = sesion.agregar(np.eye(8), 'gris', 'Candidata', {'roi_confirmada': True})
    b = sesion.agregar(np.eye(9), 'gris', 'Referencia', {'roi_confirmada': True})
    assert 'referencia' in razon_bloqueo(sesion, 'evaluar_referencia', {'candidata': a})
    assert 'misma forma' in razon_bloqueo(sesion, 'evaluar_referencia', {'candidata': a, 'referencia': b})
    assert 'RGB' in razon_bloqueo(sesion, 'separar_canales', {'imagen': a})


def test_entradas_opcionales_y_versiones_inexistentes():
    sesion = Sesion()
    ids = poblar_sesion(sesion)
    assert razon_bloqueo(sesion, 'separar_watershed', {'mascara': ids['mascara'], 'marcadores': None}) == ''
    assert 'disponible' in razon_bloqueo(sesion, 'convertir_grises', {'imagen': 'a999999'})
    assert 'corresponde' in razon_bloqueo(sesion, 'convertir_grises', {'imagen': ids['rgb'], 'extra': ids['gris']})


def test_nombres_y_origen_conservan_identidad_y_ramas():
    sesion = Sesion()
    original = sesion.agregar(np.zeros((8, 8, 3), dtype=np.uint8), 'imagen', 'campo_01.png')
    _, versiones = sesion.ejecutar('convertir_grises', {'imagen': original})
    gris = versiones['gris']
    _, versiones = sesion.ejecutar('extraer_roi', {'imagen': gris}, {'r0': 1, 'r1': 7, 'c0': 1, 'c1': 7})
    roi = versiones['roi']
    assert nombre_version(sesion, original) == '01 · Original'
    assert nombre_version(sesion, gris) == '02 · Grises'
    assert nombre_version(sesion, roi) == '03 · ROI'
    assert 'campo_01.png' in origen_version(sesion, original)
    assert '02 · Grises' in origen_version(sesion, roi)
    assert 'región de interés' in origen_version(sesion, roi)
    assert sesion.artefactos[original].nombre == 'campo_01.png'
    assert sesion.artefactos[roi].datos.flags.writeable is False
