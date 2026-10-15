"""Regresiones del asistente: la ruta explícita nunca depende del visor."""
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np
import pytest

from micrograno import Sesion
from micrograno_lab.recorrido import ETAPAS, Recorrido, exportar_recorrido


def iniciado(*, calibrar=True):
    sesion = Sesion()
    imagen = np.full((40, 48, 3), 25, dtype=np.uint8)
    imagen[9:18, 12:23] = 220
    imagen[23:33, 29:41] = 170
    original = sesion.agregar(imagen, 'imagen', 'Micrografía de prueba')
    recorrido = Recorrido(sesion)
    recorrido.usar_original(original)
    if calibrar:
        recorrido.ejecutar('escala', {'referencia_um': 50, 'referencia_px': 100})
    else:
        recorrido.ejecutar('escala', opcion='omitir')
    recorrido.ejecutar('grises')
    return recorrido


def recortado(**kwargs):
    recorrido = iniciado(**kwargs)
    recorrido.ejecutar('roi', dict(r0=5, r1=36, c0=7, c1=44))
    recorrido.confirmar_roi('Región revisada, sin texto ni barra de escala.')
    return recorrido


def terminado(**kwargs):
    recorrido = recortado(**kwargs)
    for etapa in ('preparar', 'segmentar', 'limpiar', 'etiquetar'):
        recorrido.ejecutar(etapa)
    recorrido.ejecutar('medir', opcion=None if kwargs.get('calibrar', True) else 'omitir')
    recorrido.visitar('exportar')
    return recorrido


def test_recorte_es_la_entrada_real_de_todos_los_pasos_y_no_el_gris_original():
    recorrido = terminado()
    sesion = recorrido.sesion
    original = sesion.artefactos[recorrido.original_id].datos.copy()
    assert sesion.artefactos[recorrido.salida('grises')].datos.shape == (40, 48)
    assert sesion.artefactos[recorrido.salida('roi')].datos.shape == (31, 37)
    for i in range(1, len(ETAPAS)):
        assert recorrido.entrada(i) == recorrido.salida(i - 1)
    for etapa in ('roi', 'preparar', 'segmentar', 'limpiar', 'etiquetar', 'medir'):
        artefacto = sesion.artefactos[recorrido.salida(etapa)]
        assert artefacto.datos.shape == (31, 37)
        assert artefacto.metadatos['origen_rc'] == [5, 7]
        assert artefacto.metadatos['escala']['um_por_px'] == 0.5
        assert artefacto.metadatos['roi_confirmada']
    assert recorrido.resultado('medir').resumen['numero_objetos_entrada'] == 2
    assert recorrido.resultado('medir').resumen['numero_objetos_aceptados'] == 2
    np.testing.assert_array_equal(sesion.artefactos[recorrido.original_id].datos, original)
    assert not sesion.artefactos[recorrido.original_id].datos.flags.writeable


def test_ver_original_o_grises_no_cambia_la_cadena_ni_pierde_mascaras():
    recorrido = terminado()
    estados = recorrido.estados
    numero = len(recorrido.sesion.artefactos)
    for etapa in ('imagen', 'grises', 'roi', 'segmentar', 'exportar'):
        recorrido.visitar(etapa)
        recorrido.estado()
        recorrido.entrada()
        recorrido.salida()
    assert recorrido.estados == estados
    assert len(recorrido.sesion.artefactos) == numero
    assert recorrido.entrada('limpiar') == estados['segmentar'].salida_id


def test_no_avanza_sin_generar_y_confirmar_el_recorte_visible():
    recorrido = iniciado()
    recorrido.visitar('roi')
    assert recorrido.salida() is None
    with pytest.raises(ValueError, match='Complete'):
        recorrido.avanzar()
    roi = recorrido.ejecutar('roi', dict(r0=5, r1=36, c0=7, c1=44))
    assert roi.salida_id in recorrido.sesion.artefactos
    assert not recorrido.completada('roi')
    assert not recorrido.puede_visitar('preparar')
    with pytest.raises(ValueError, match='Complete'):
        recorrido.ejecutar('preparar')
    with pytest.raises(ValueError, match='Confirme'):
        recorrido.confirmar_roi(' ')
    recorrido.confirmar_roi('Verifiqué la exclusión de anotaciones.')
    assert recorrido.avanzar() == 4
    assert recorrido.entrada() == roi.salida_id


def test_repetir_el_mismo_recorte_no_pierde_confirmacion_ni_resultados():
    recorrido = terminado()
    estados = recorrido.estados
    pasos = len(recorrido.sesion.pasos)
    roi = recorrido.ejecutar('roi', dict(r0=5, r1=36, c0=7, c1=44))
    assert roi.confirmada
    assert recorrido.estados == estados
    assert len(recorrido.sesion.pasos) == pasos


def test_cambiar_roi_invalida_posteriores_y_conserva_imagenes_y_tablas_previas():
    recorrido = terminado()
    previos = set(recorrido.sesion.artefactos)
    medida = recorrido.resultado('medir')
    roi_anterior = recorrido.salida('roi')
    nueva = recorrido.ejecutar('roi', dict(r0=8, r1=35, c0=10, c1=43))
    assert nueva.salida_id != roi_anterior
    assert not nueva.confirmada
    assert set(recorrido.estados) == {'imagen', 'escala', 'grises', 'roi'}
    assert previos < set(recorrido.sesion.artefactos)
    assert any(resultado is medida for resultado in recorrido.sesion.resultados)
    assert recorrido.actual == 3
    recorrido.confirmar_roi('Segundo recorte revisado.')
    assert recorrido.ejecutar('preparar').salida_id == nueva.salida_id
    mascara = recorrido.ejecutar('segmentar')
    assert recorrido.sesion.artefactos[mascara.salida_id].datos.shape == (27, 33)


def test_un_error_de_calculo_preserva_la_ruta_anterior():
    recorrido = terminado()
    estados = recorrido.estados
    ids = set(recorrido.sesion.artefactos)
    with pytest.raises(ValueError):
        recorrido.ejecutar('roi', dict(r0=8, r1=1000, c0=10, c1=43))
    assert recorrido.estados == estados
    assert set(recorrido.sesion.artefactos) == ids


def test_preparar_y_seleccion_de_mascara_son_locales_a_su_etapa():
    recorrido = recortado()
    preparado = recorrido.ejecutar('preparar', opcion='mediana')
    assert preparado.salida_id == preparado.salidas['mediana']
    mascara = recorrido.ejecutar('segmentar', opcion='manual', parametros={'manual': 0.8})
    assert mascara.entrada_id == preparado.salida_id
    assert mascara.salida_id == mascara.salidas['manual']
    limpieza = recorrido.ejecutar('limpiar')
    assert limpieza.entrada_id == mascara.salida_id
    np.testing.assert_array_equal(recorrido.sesion.artefactos[mascara.salida_id].datos,
                                  recorrido.sesion.artefactos[limpieza.salida_id].datos)
    assert limpieza.parametros['area_minima'] == 1
    assert limpieza.parametros['hueco_maximo'] == 0


def test_sin_escala_se_segmenta_pero_no_se_inventan_medidas_fisicas():
    recorrido = terminado(calibrar=False)
    assert recorrido.estado('medir').omitida
    assert recorrido.resultado('medir') is None
    assert recorrido.entrada('exportar') == recorrido.salida('etiquetar')
    with pytest.raises(ValueError, match='Falta la escala'):
        recorrido.ejecutar('medir')
    assert recorrido.sesion.artefactos[recorrido.salida('etiquetar')].metadatos['escala'] is None


def test_cambiar_calibracion_conserva_medidas_anteriores_sin_reescribirlas():
    recorrido = terminado()
    anterior = recorrido.salida('etiquetar')
    resultado = recorrido.resultado('medir')
    areas = resultado.tabla.area_um2.copy()
    recorrido.ejecutar('escala', {'referencia_um': 100, 'referencia_px': 100})
    assert set(recorrido.estados) == {'imagen', 'escala'}
    assert recorrido.sesion.artefactos[anterior].metadatos['escala']['um_por_px'] == 0.5
    np.testing.assert_array_equal(resultado.tabla.area_um2, areas)
    gris = recorrido.ejecutar('grises')
    assert recorrido.sesion.artefactos[gris.salida_id].metadatos['escala']['um_por_px'] == 1


def test_el_estado_consultado_no_permite_cambiar_la_entrada_de_la_cadena():
    recorrido = terminado()
    copia = recorrido.estados
    copia['segmentar'].salidas['otsu'] = recorrido.original_id
    copia.pop('roi')
    assert recorrido.estado('segmentar').salidas['otsu'] == recorrido.salida('segmentar')
    assert recorrido.completada('roi')


def test_nueva_instancia_no_infiere_ids_de_otra_sesion():
    primera = terminado()
    segunda = Sesion()
    id_ = segunda.agregar(np.eye(40), 'gris', 'Otra micrografía')
    assert id_ == primera.original_id
    vacio = Recorrido(segunda)
    assert vacio.original_id is None
    assert vacio.entrada('segmentar') is None
    with pytest.raises(ValueError, match='Complete'):
        vacio.visitar('segmentar')


def test_guardar_y_abrir_recupera_ruta_exacta_incluyendo_ramas_anteriores(tmp_path):
    recorrido = terminado()
    vieja = recorrido.salida('segmentar')
    recorrido.ejecutar('segmentar', {'polaridad': 'oscura'})
    recorrido.visitar('segmentar')
    ruta = recorrido.guardar(tmp_path / 'sesion')
    abierta = Recorrido.abrir(ruta)
    assert abierta.estados == recorrido.estados
    assert abierta.actual == recorrido.actual
    assert vieja in abierta.sesion.artefactos
    assert abierta.entrada('limpiar') == recorrido.salida('segmentar')
    assert not abierta.completada('limpiar')


def test_roi_pendiente_sigue_pendiente_al_reabrir(tmp_path):
    recorrido = iniciado()
    recorrido.ejecutar('roi', dict(r0=5, r1=36, c0=7, c1=44))
    recorrido.visitar('roi')
    recorrido.guardar(tmp_path / 'sesion')
    abierta = Recorrido.abrir(tmp_path / 'sesion')
    assert abierta.salida('roi') == recorrido.salida('roi')
    assert not abierta.completada('roi')
    with pytest.raises(ValueError, match='Complete'):
        abierta.avanzar()


def test_sidecar_ajeno_no_se_asocia_por_coincidencia_de_identificadores(tmp_path):
    a, b = terminado(), terminado()
    b.sesion.nombre = 'Otra sesión, mismos identificadores'
    a.guardar(tmp_path / 'a')
    b.guardar(tmp_path / 'b')
    (tmp_path / 'b' / 'recorrido.json').write_bytes((tmp_path / 'a' / 'recorrido.json').read_bytes())
    with pytest.raises(ValueError, match='no corresponde'):
        Recorrido.abrir(tmp_path / 'b')


@pytest.mark.parametrize('alteracion', ['entrada', 'salida', 'resultado', 'confirmacion', 'hueco'])
def test_rechaza_cadenas_que_no_corresponden_al_calculo_guardado(tmp_path, alteracion):
    recorrido = terminado()
    recorrido.guardar(tmp_path / 'sesion')
    sidecar = tmp_path / 'sesion' / 'recorrido.json'
    datos = json.loads(sidecar.read_text(encoding='utf-8'))
    if alteracion == 'entrada':
        datos['estados']['limpiar']['entrada_id'] = recorrido.salida('roi')
    elif alteracion == 'salida':
        datos['estados']['segmentar']['salida_id'] = recorrido.salida('grises')
    elif alteracion == 'resultado':
        datos['estados']['limpiar']['indice_resultado'] = 0
    elif alteracion == 'confirmacion':
        datos['estados']['roi']['confirmada'] = False
    else:
        datos['estados'].pop('roi')
    sidecar.write_text(json.dumps(datos), encoding='utf-8')
    with pytest.raises(ValueError, match='no es válido'):
        Recorrido.abrir(tmp_path / 'sesion')


def test_sesion_sin_sidecar_no_se_convierte_en_ruta_inferida(tmp_path):
    recorrido = terminado()
    recorrido.sesion.guardar(tmp_path / 'sesion')
    with pytest.raises(ValueError, match='no contiene un recorrido'):
        Recorrido.abrir(tmp_path / 'sesion')


def test_exportacion_completa_conserva_versiones_y_permita_reabrir(tmp_path):
    recorrido = terminado()
    destino = tmp_path / 'analisis'
    manifiesto = exportar_recorrido(recorrido, destino)
    versiones = json.loads(manifiesto.read_text(encoding='utf-8'))
    assert {v['id'] for v in versiones['versiones']} == set(recorrido.sesion.artefactos)
    activo = json.loads((destino / 'recorrido_activo.json').read_text(encoding='utf-8'))
    assert activo['etapas'] == {k: asdict(v) for k, v in recorrido.estados.items()}
    for version in versiones['versiones']:
        exacto = np.load(destino / version['archivos']['npy']['ruta'], allow_pickle=False)
        np.testing.assert_array_equal(exacto, recorrido.sesion.artefactos[version['id']].datos)
    reabierto = Recorrido.abrir(destino)
    assert reabierto.estados == recorrido.estados
    assert (destino / 'sesion_reabrible' / 'reproducir.py').is_file()
    assert list((destino / 'tablas').glob('*.csv'))


def test_fallo_al_guardar_sesion_no_publica_exportacion_incompleta(tmp_path, monkeypatch):
    recorrido = terminado()
    estados, actual = recorrido.estados, recorrido.actual
    def fallo(_carpeta):
        raise OSError('Disco lleno de prueba')
    monkeypatch.setattr(recorrido, 'guardar', fallo)
    with pytest.raises(OSError, match='Disco lleno'):
        exportar_recorrido(recorrido, tmp_path / 'analisis')
    assert not (tmp_path / 'analisis').exists()
    assert not list(tmp_path.iterdir())
    assert recorrido.estados == estados
    assert recorrido.actual == actual


def test_fallo_de_escritura_del_recorrido_no_deja_sesion_sin_ruta(tmp_path, monkeypatch):
    recorrido = terminado()
    estados, actual = recorrido.estados, recorrido.actual
    escribir = Path.write_text
    def fallo_sidecar(ruta, *args, **kwargs):
        if ruta.name == 'recorrido.json':
            raise OSError('No se pudo escribir la ruta')
        return escribir(ruta, *args, **kwargs)
    monkeypatch.setattr(Path, 'write_text', fallo_sidecar)
    with pytest.raises(OSError, match='escribir la ruta'):
        recorrido.guardar(tmp_path / 'sesion')
    assert not list(tmp_path.iterdir())
    assert recorrido.estados == estados
    assert recorrido.actual == actual


@pytest.mark.parametrize('etapa_pendiente', [etapa['id'] for etapa in ETAPAS[1:]])
def test_reanuda_exactamente_el_paso_pendiente_sin_ejecutarlo_al_abrir(tmp_path, etapa_pendiente):
    recorrido = Recorrido()
    recorrido.usar_original(recorrido.sesion.agregar(np.eye(10, dtype=np.uint8) * 255, 'imagen', 'Prueba'))
    for etapa in ETAPAS[1:]:
        id_ = etapa['id']
        if id_ == etapa_pendiente:
            break
        p = ({'referencia_um': 10, 'referencia_px': 20} if id_ == 'escala'
             else {'r0': 1, 'r1': 9, 'c0': 1, 'c1': 9} if id_ == 'roi' else {})
        recorrido.ejecutar(id_, p)
        if id_ == 'roi':
            recorrido.confirmar_roi('Ejemplo sintético sin anotaciones.')
    recorrido.visitar(etapa_pendiente)
    estado_previo = recorrido.estados
    ruta = recorrido.guardar(tmp_path / 'sesion')
    recuperado = Recorrido.abrir(ruta)
    assert recuperado.actual == recorrido.actual
    assert recuperado.estados == estado_previo
    assert recuperado.entrada() == recorrido.entrada()
    assert not recuperado.completada()
    assert len(recuperado.sesion.pasos) == len(recorrido.sesion.pasos)


def diminuto(forma):
    recorrido = Recorrido()
    imagen = (np.indices(forma).sum(axis=0) % 2 * 255).astype(np.uint8)
    recorrido.usar_original(recorrido.sesion.agregar(imagen, 'imagen', 'ROI pequeña'))
    recorrido.ejecutar('escala', opcion='omitir')
    recorrido.ejecutar('grises')
    recorrido.ejecutar('roi', dict(r0=0, r1=forma[0], c0=0, c1=forma[1]),
                       nota='Datos sintéticos sin anotaciones.')
    return recorrido


@pytest.mark.parametrize('forma', [(1, 2), (2, 1), (2, 2), (3, 3)])
def test_roi_pequena_conserva_mascara_al_separar_objetos(forma):
    recorrido = diminuto(forma)
    for etapa in ('preparar', 'segmentar', 'limpiar'):
        recorrido.ejecutar(etapa)
    mascara = recorrido.sesion.artefactos[recorrido.salida('limpiar')].datos
    estado = recorrido.ejecutar('etiquetar', opcion='watershed')
    etiquetas = recorrido.sesion.artefactos[estado.salida_id].datos
    assert estado.parametros['area_minima'] == 1
    np.testing.assert_array_equal(etiquetas > 0, mascara)
    assert etiquetas.shape == forma


def test_roi_constante_informa_error_sin_cambiar_recorrido():
    recorrido = diminuto((1, 1))
    recorrido.ejecutar('preparar')
    recorrido.visitar('segmentar')
    estados, ids, pasos = recorrido.estados, set(recorrido.sesion.artefactos), len(recorrido.sesion.pasos)
    with pytest.raises(ValueError, match='constante'):
        recorrido.ejecutar('segmentar')
    assert recorrido.actual == 5
    assert recorrido.estados == estados
    assert set(recorrido.sesion.artefactos) == ids
    assert len(recorrido.sesion.pasos) == pasos


def test_error_de_salida_auxiliar_no_deja_versiones_huerfanas(tmp_path, monkeypatch):
    recorrido = diminuto((1, 2))
    recorrido.ejecutar('preparar')
    recorrido.ejecutar('segmentar')
    recorrido.visitar('preparar')
    estados, ids = recorrido.estados, set(recorrido.sesion.artefactos)
    pasos, resultados = len(recorrido.sesion.pasos), len(recorrido.sesion.resultados)
    agregar = recorrido.sesion._agregar
    def falla_ultima_salida(datos, tipo, nombre, metadatos):
        if nombre.endswith('bilateral'):
            raise ValueError('Salida auxiliar no válida')
        return agregar(datos, tipo, nombre, metadatos)
    monkeypatch.setattr(recorrido.sesion, '_agregar', falla_ultima_salida)
    with pytest.raises(ValueError, match='continúe sin filtrar'):
        recorrido.ejecutar('preparar', opcion='mediana')
    assert recorrido.estados == estados
    assert recorrido.actual == 4
    assert set(recorrido.sesion.artefactos) == ids
    assert len(recorrido.sesion.pasos) == pasos
    assert len(recorrido.sesion.resultados) == resultados
    recuperado = Recorrido.abrir(recorrido.guardar(tmp_path / 'sesion'))
    assert recuperado.estados == estados


def test_referencia_dibujada_se_conserva_al_guardar_y_reabrir(tmp_path):
    recorrido = iniciado()
    documentacion = {'linea_rc': [1, 2, 4, 6]}
    escala = recorrido.ejecutar('escala', {'referencia_um': 10, 'referencia_px': 5},
                                documentacion=documentacion)
    documentacion['linea_rc'][0] = 1000
    recuperado = Recorrido.abrir(recorrido.guardar(tmp_path / 'sesion'))
    meta = recuperado.sesion.artefactos[recuperado.original_id].metadatos
    assert meta['calibracion_documentacion']['linea_rc'] == [1, 2, 4, 6]
    assert meta['calibracion_documentacion']['origen'] == 'recorrido_guiado'
    assert meta['calibracion_documentacion']['parametros'] == escala.parametros
    assert meta['escala']['um_por_px'] == 2
    assert recuperado.sesion.eventos[-1]['documentacion']['linea_rc'] == [1, 2, 4, 6]


def test_cambiar_linea_de_referencia_registra_calibracion_aunque_el_factor_no_cambie():
    recorrido = iniciado()
    parametros = {'referencia_um': 5, 'referencia_px': 10}
    primera = {'linea_rc': [0, 0, 0, 10]}
    recorrido.ejecutar('escala', parametros, documentacion=primera)
    gris = recorrido.ejecutar('grises')
    cantidad = len(recorrido.sesion.pasos)
    recorrido.ejecutar('escala', parametros, documentacion=primera)
    assert len(recorrido.sesion.pasos) == cantidad
    assert recorrido.salida('grises') == gris.salida_id
    segunda = {'linea_rc': [1, 0, 1, 10]}
    recorrido.ejecutar('escala', parametros, documentacion=segunda)
    assert len(recorrido.sesion.pasos) == cantidad + 1
    assert not recorrido.completada('grises')
    assert gris.salida_id in recorrido.sesion.artefactos
    meta = recorrido.sesion.artefactos[recorrido.original_id].metadatos
    assert meta['calibracion_documentacion']['linea_rc'] == segunda['linea_rc']


@pytest.mark.parametrize('linea', [
    [0, 0, 0], [0, 0, 0, float('nan')], [0, 0, 0, float('inf')],
    [-1, 0, -1, 10], [40, 0, 40, 10], [0, 40, 0, 50],
    [0, 0, 0, 0], [0, 0, 0, 5], [True, 0, 0, 10],
])
def test_referencia_invalida_no_muta_la_escala_ni_los_pasos(linea):
    recorrido = iniciado()
    estados = recorrido.estados
    eventos, pasos = len(recorrido.sesion.eventos), len(recorrido.sesion.pasos)
    with pytest.raises(ValueError):
        recorrido.ejecutar('escala', {'referencia_um': 5, 'referencia_px': 10},
                           documentacion={'linea_rc': linea})
    assert recorrido.estados == estados
    assert len(recorrido.sesion.eventos) == eventos
    assert len(recorrido.sesion.pasos) == pasos


def test_documentacion_de_escala_no_se_acepta_en_otras_etapas():
    recorrido = iniciado()
    with pytest.raises(ValueError, match='solo se admite al calcular la escala'):
        recorrido.ejecutar('grises', documentacion={'linea_rc': [0, 0, 0, 10]})
    with pytest.raises(ValueError, match='solo se admite al calcular la escala'):
        recorrido.ejecutar('escala', opcion='omitir', documentacion={'linea_rc': [0, 0, 0, 10]})
