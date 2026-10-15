"""Recorrido lineal: cada etapa recibe exclusivamente la salida de la anterior.

La navegación es independiente de los datos. Revisar una etapa no selecciona
otra imagen ni elimina resultados; recalcularla invalida solo la ruta posterior.
Todos los cálculos y artefactos permanecen en una única :class:`Sesion`.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
import tempfile

from micrograno import EscalaEspacial, Sesion
from micrograno.catalogo import resolver_parametros


ETAPAS = (
    dict(id='imagen', titulo='Imagen original', operacion='',
         descripcion='Abra una micrografía. El original se conserva durante todo el recorrido.'),
    dict(id='escala', titulo='Escala', operacion='calibrar_escala',
         descripcion='Asocie una referencia conocida antes de recortar su barra de escala.'),
    dict(id='grises', titulo='Escala de grises', operacion='convertir_grises',
         descripcion='Convierta la imagen original a intensidades normalizadas entre cero y uno.'),
    dict(id='roi', titulo='Región de interés', operacion='extraer_roi',
         descripcion='Recorte y revise la región que continuará por todos los pasos restantes.'),
    dict(id='preparar', titulo='Preparar la ROI', operacion='variantes_ruido',
         descripcion='Conserve la ROI o aplique un filtro de mediana si necesita reducir ruido.'),
    dict(id='segmentar', titulo='Crear la máscara', operacion='umbralizar',
         descripcion='Separe los objetos del fondo y compruebe visualmente la máscara.'),
    dict(id='limpiar', titulo='Revisar la máscara', operacion='limpiar_mascara',
         descripcion='Conserve la máscara o retire componentes pequeños y rellene huecos.'),
    dict(id='etiquetar', titulo='Identificar objetos', operacion='etiquetar_componentes',
         descripcion='Asigne un identificador a cada objeto de la máscara revisada.'),
    dict(id='medir', titulo='Medir objetos', operacion='medir_objetos',
         descripcion='Calcule medidas con la escala del original o continúe sin medidas físicas.'),
    dict(id='exportar', titulo='Exportar resultados', operacion='',
         descripcion='Guarde todas las versiones, máscaras, tablas y el recorrido reproducible.'),
)
_IDS = tuple(etapa['id'] for etapa in ETAPAS)
_OPERACIONES = {
    'grises': ('convertir_grises', 'imagen', 'gris'),
    'roi': ('extraer_roi', 'imagen', 'roi'),
    'preparar': ('variantes_ruido', 'imagen', 'mediana'),
    'segmentar': ('umbralizar', 'imagen', 'otsu'),
    'limpiar': ('limpiar_mascara', 'mascara', 'limpia'),
    'etiquetar': ('etiquetar_componentes', 'mascara', 'etiquetas'),
    'medir': ('medir_objetos', 'etiquetas', 'aceptadas'),
}
_DEFECTOS = {
    'limpiar': dict(area_minima=1, hueco_maximo=0, conectividad=2),
    'medir': dict(area_minima=1, regla_marco='conservar'),
}


@dataclass(frozen=True)
class EstadoEtapa:
    entrada_id: str | None
    salida_id: str
    operacion: str = ''
    parametros: dict = field(default_factory=dict)
    salidas: dict = field(default_factory=dict)
    indice_resultado: int | None = None
    omitida: bool = False
    nota: str = ''
    confirmada: bool = True


class Recorrido:
    """Estado explícito del asistente, sin imagen activa ni búsquedas por tipo.

    ``ejecutar`` calcula y conserva la salida, pero no avanza. La ROI queda
    pendiente hasta ``confirmar_roi``. ``avanzar`` exige completar la etapa.
    Consultar ``estado`` o ``estados`` devuelve copias sin acceso de escritura.
    """

    def __init__(self, sesion: Sesion | None = None):
        self.sesion = sesion if sesion is not None else Sesion()
        self._estados: dict[str, EstadoEtapa] = {}
        self._actual = 0

    @property
    def actual(self) -> int:
        return self._actual

    @property
    def estados(self) -> dict[str, EstadoEtapa]:
        return deepcopy(self._estados)

    @property
    def original_id(self) -> str | None:
        return self.salida('imagen')

    @property
    def siguiente_pendiente(self) -> int:
        return next((i for i, id_ in enumerate(_IDS) if not self.completada(id_)), len(_IDS) - 1)

    def _indice(self, etapa: str | int | None) -> int:
        if etapa is None:
            return self._actual
        if isinstance(etapa, str) and etapa in _IDS:
            return _IDS.index(etapa)
        if type(etapa) is int and 0 <= etapa < len(_IDS):
            return etapa
        raise ValueError('Etapa del recorrido no válida.')

    def estado(self, etapa: str | int | None = None) -> EstadoEtapa | None:
        return deepcopy(self._estados.get(_IDS[self._indice(etapa)]))

    def entrada(self, etapa: str | int | None = None) -> str | None:
        indice = self._indice(etapa)
        return self.salida(indice - 1) if indice else self.original_id

    def salida(self, etapa: str | int | None = None) -> str | None:
        estado = self._estados.get(_IDS[self._indice(etapa)])
        return estado.salida_id if estado else None

    def completada(self, etapa: str | int | None = None) -> bool:
        estado = self._estados.get(_IDS[self._indice(etapa)])
        return estado is not None and estado.confirmada

    def resultado(self, etapa: str | int | None = None):
        estado = self._estados.get(_IDS[self._indice(etapa)])
        if estado is None or estado.indice_resultado is None:
            return None
        return self.sesion.resultados[estado.indice_resultado]

    def puede_visitar(self, etapa: str | int) -> bool:
        indice = self._indice(etapa)
        return all(self.completada(i) for i in range(indice))

    def visitar(self, etapa: str | int) -> int:
        indice = self._indice(etapa)
        if not self.puede_visitar(indice):
            raise ValueError('Complete y confirme los pasos anteriores antes de continuar.')
        self._actual = indice
        return indice

    def avanzar(self) -> int:
        if not self.completada():
            raise ValueError('Complete y confirme este paso antes de continuar.')
        return self.visitar(min(self._actual + 1, len(_IDS) - 1))

    def retroceder(self) -> int:
        return self.visitar(max(self._actual - 1, 0))

    def _registrar(self, id_: str, estado: EstadoEtapa) -> EstadoEtapa:
        indice = _IDS.index(id_)
        for posterior in _IDS[indice + 1:]:
            self._estados.pop(posterior, None)
        self._estados[id_] = deepcopy(estado)
        self._actual = min(self._actual, indice)
        return deepcopy(estado)

    def usar_original(self, id_fuente: str) -> EstadoEtapa:
        """Inicia explícitamente una ruta; nunca deduce un original de la sesión."""
        if id_fuente not in self.sesion.fuentes:
            raise ValueError('La imagen original debe ser una fuente importada de esta sesión.')
        if self.sesion.artefactos[id_fuente].tipo not in ('imagen', 'gris'):
            raise ValueError('El recorrido comienza con una imagen, no con una máscara.')
        if self.original_id == id_fuente:
            return self.estado('imagen')
        return self._registrar('imagen', EstadoEtapa(None, id_fuente, salidas={'original': id_fuente}))

    def ejecutar(self, etapa: str | int | None = None, parametros: dict | None = None,
                 *, opcion: str | None = None, nota: str = '',
                 documentacion: dict | None = None) -> EstadoEtapa:
        if not isinstance(nota, str):
            raise TypeError('La nota de revisión debe ser un texto.')
        indice = self._indice(etapa)
        id_ = _IDS[indice]
        if documentacion is not None and (id_ != 'escala' or opcion == 'omitir'):
            raise ValueError('La documentación de referencia solo se admite al calcular la escala.')
        if documentacion is not None and not isinstance(documentacion, dict):
            raise TypeError('La documentación de referencia debe ser un diccionario.')
        if id_ == 'imagen':
            raise ValueError('Importe una imagen y registre explícitamente su original.')
        if not self.puede_visitar(indice):
            raise ValueError('Complete y confirme los pasos anteriores antes de ejecutar este paso.')
        entrada = self.entrada(indice)
        parametros = deepcopy(parametros or {})
        previo = self._estados.get(id_)

        if ((id_ == 'preparar' and opcion in (None, 'conservar')) or
                (id_ in ('escala', 'medir') and opcion == 'omitir') or id_ == 'exportar'):
            if parametros:
                raise ValueError('Un paso conservado u omitido no admite parámetros de cálculo.')
            estado = EstadoEtapa(entrada, entrada, omitida=id_ != 'exportar', nota=nota)
            if previo == estado:
                return deepcopy(previo)
            if id_ == 'escala':
                artefacto = self.sesion.artefactos[entrada]
                artefacto.metadatos['escala'] = None
                artefacto.metadatos.pop('calibracion_documentacion', None)
                self.sesion.eventos.append(dict(evento='escala_omitida', artefacto=entrada, nota=nota))
            return self._registrar(id_, estado)

        if id_ == 'escala':
            if opcion is not None:
                raise ValueError('Opción de calibración no válida.')
            operacion, rol, salida = 'calibrar_escala', None, None
        else:
            operacion, rol, salida = _OPERACIONES[id_]
            permitidas = {'preparar': ('mediana',), 'segmentar': ('otsu', 'manual', 'adaptativa'),
                          'etiquetar': ('componentes', 'watershed')}
            if opcion is not None and opcion not in permitidas.get(id_, ()):
                raise ValueError('Opción no válida para este paso.')
            if id_ == 'segmentar':
                salida = opcion or 'otsu'
            if id_ == 'etiquetar' and opcion == 'watershed':
                operacion = 'separar_watershed'

        p = {**_DEFECTOS.get(id_, {}), **parametros}
        if operacion == 'separar_watershed':
            # La eliminación de objetos pertenece a la etapa de limpieza.
            # El default científico de watershed no debe volver a filtrarlos
            # de forma invisible al usuario del recorrido.
            p.setdefault('area_minima', 1)
        if id_ == 'medir':
            escala = self.sesion.artefactos[entrada].metadatos.get('escala')
            if not escala:
                raise ValueError('Falta la escala: vuelva al paso Escala o continúe sin medidas físicas.')
            p.setdefault('s_um_px', escala['um_por_px'])
        p = resolver_parametros(operacion, p)
        documento_escala = None
        if id_ == 'escala':
            documento_escala = deepcopy(documentacion or {})
            if 'linea_rc' in documento_escala:
                linea = documento_escala['linea_rc']
                if (not isinstance(linea, (list, tuple)) or len(linea) != 4
                        or any(isinstance(x, bool) or not isinstance(x, Real)
                               or not math.isfinite(x) for x in linea)):
                    raise ValueError('Los extremos de referencia deben ser cuatro coordenadas numéricas finitas.')
                r0, c0, r1, c1 = (float(x) for x in linea)
                alto, ancho = self.sesion.artefactos[entrada].datos.shape[:2]
                if not (0 <= r0 <= alto - 1 and 0 <= r1 <= alto - 1
                        and 0 <= c0 <= ancho - 1 and 0 <= c1 <= ancho - 1):
                    raise ValueError('Los extremos de referencia deben estar dentro de la imagen original.')
                longitud = math.hypot(r1 - r0, c1 - c0)
                if longitud == 0 or not math.isclose(longitud, float(p['referencia_px']), rel_tol=1e-9, abs_tol=1e-9):
                    raise ValueError('La longitud en píxeles debe coincidir con los extremos de referencia dibujados.')
                documento_escala['linea_rc'] = [r0, c0, r1, c1]
            documento_escala.update(origen='recorrido_guiado', parametros=deepcopy(p))
        if (previo and previo.entrada_id == entrada and previo.operacion == operacion
                and previo.parametros == p and (salida is None or previo.salidas.get(salida) == previo.salida_id)
                and (id_ != 'escala' or self.sesion.artefactos[entrada].metadatos.get(
                    'calibracion_documentacion') == documento_escala)):
            if id_ == 'roi' and nota.strip() and not previo.confirmada:
                return self.confirmar_roi(nota)
            return deepcopy(previo)

        # Una operación puede producir varias salidas. Si una salida auxiliar
        # falla al registrarse, tampoco quedan las primeras como artefactos
        # huérfanos de un cálculo que el asistente declaró fallido.
        ids_anteriores = set(self.sesion.artefactos)
        n_pasos, n_resultados = len(self.sesion.pasos), len(self.sesion.resultados)
        n_eventos = len(self.sesion.eventos)
        meta_anterior = deepcopy(self.sesion.artefactos[entrada].metadatos) if id_ == 'escala' else None
        try:
            resultado, salidas = self.sesion.ejecutar(operacion, {rol: entrada} if rol else {}, p)
            if id_ == 'escala':
                self.sesion.establecer_escala(entrada, EscalaEspacial(**resultado.resumen),
                                            documento_escala)
                seleccionada = entrada
            else:
                seleccionada = salidas[salida]
        except Exception as error:
            for nuevo in set(self.sesion.artefactos) - ids_anteriores:
                del self.sesion.artefactos[nuevo]
            del self.sesion.pasos[n_pasos:]
            del self.sesion.resultados[n_resultados:]
            del self.sesion.eventos[n_eventos:]
            if meta_anterior is not None:
                self.sesion.artefactos[entrada].metadatos = meta_anterior
            if operacion == 'variantes_ruido' and min(self.sesion.artefactos[entrada].datos.shape) == 1:
                raise ValueError('La comparación de filtros no pudo procesar una ROI de una sola fila '
                                 'o columna. Amplíe el recorte o continúe sin filtrar.') from error
            raise
        estado = EstadoEtapa(entrada, seleccionada, operacion, p, salidas,
                             len(self.sesion.resultados) - 1, confirmada=id_ != 'roi')
        self._registrar(id_, estado)
        if id_ == 'roi' and nota.strip():
            return self.confirmar_roi(nota)
        return deepcopy(estado)

    def confirmar_roi(self, nota: str) -> EstadoEtapa:
        estado = self._estados.get('roi')
        if estado is None:
            raise ValueError('Genere y revise primero el recorte de la ROI.')
        if not isinstance(nota, str) or not nota.strip():
            raise ValueError('Confirme que la ROI excluye barra de escala y anotaciones.')
        if estado.confirmada and estado.nota == nota.strip():
            return deepcopy(estado)
        self.sesion.confirmar_roi(estado.salida_id, nota.strip())
        return self._registrar('roi', replace(estado, nota=nota.strip(), confirmada=True))

    def guardar(self, carpeta: str | Path) -> Path:
        """Publica juntos los datos y su ruta, o no publica ninguna carpeta."""
        destino = Path(carpeta).expanduser().resolve()
        if destino.exists():
            raise FileExistsError('La carpeta ya existe. Elija una carpeta nueva para esta sesión.')
        self._validar_estado()
        destino.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.micrograno-guardar-', dir=destino.parent) as temporal:
            preparado = Path(temporal) / 'sesion'
            manifiesto = self.sesion.guardar(preparado)
            contenido = dict(esquema=1, sesion_sha256=self._sha256(manifiesto),
                             actual=self.actual,
                             estados={k: asdict(v) for k, v in self._estados.items()})
            (preparado / 'recorrido.json').write_text(
                json.dumps(contenido, ensure_ascii=False, indent=2), encoding='utf-8')
            if destino.exists():
                raise FileExistsError('El destino apareció durante el guardado. Elija otra carpeta.')
            preparado.rename(destino)
        return destino / 'sesion.json'

    @staticmethod
    def _sha256(ruta: Path) -> str:
        return hashlib.sha256(ruta.read_bytes()).hexdigest()

    @classmethod
    def abrir(cls, ruta: str | Path) -> 'Recorrido':
        ruta = Path(ruta).resolve()
        manifiesto = ruta / 'sesion.json' if ruta.is_dir() else ruta
        if ruta.is_dir() and not manifiesto.is_file():
            manifiesto = ruta / 'sesion_reabrible' / 'sesion.json'
        sidecar = manifiesto.parent / 'recorrido.json'
        if not sidecar.is_file():
            raise ValueError('Esta sesión no contiene un recorrido guiado; no se inferirá una imagen de trabajo.')
        if sidecar.stat().st_size > 1_000_000:
            raise ValueError('El archivo del recorrido supera el tamaño admitido.')
        contenido = json.loads(sidecar.read_text(encoding='utf-8'))
        if not isinstance(contenido, dict) or contenido.get('esquema') != 1:
            raise ValueError('Formato del recorrido no compatible.')
        if contenido.get('sesion_sha256') != cls._sha256(manifiesto):
            raise ValueError('El recorrido no corresponde a esta sesión o su manifiesto cambió.')
        recorrido = cls(Sesion.abrir(manifiesto))
        try:
            estados = contenido['estados']
            if not isinstance(estados, dict) or any(k not in _IDS for k in estados):
                raise ValueError('Etapas desconocidas.')
            recorrido._estados = {k: EstadoEtapa(**v) for k, v in estados.items()}
            recorrido._validar_estado()
            recorrido.visitar(contenido['actual'])
        except (KeyError, TypeError, IndexError, ValueError) as error:
            raise ValueError(f'El estado del recorrido no es válido: {error}') from error
        return recorrido

    def _validar_estado(self) -> None:
        """Verifica la cadena, las salidas y las llamadas reales del manifiesto."""
        ultimo_resultado = -1
        for indice, id_ in enumerate(_IDS):
            estado = self._estados.get(id_)
            if estado is None:
                if any(k in self._estados for k in _IDS[indice + 1:]):
                    raise ValueError('Hay una etapa sin su predecesora.')
                continue
            if not isinstance(estado.parametros, dict) or not isinstance(estado.salidas, dict):
                raise ValueError('Parámetros o salidas no válidos.')
            if type(estado.omitida) is not bool or type(estado.confirmada) is not bool or not isinstance(estado.nota, str):
                raise ValueError('Confirmación de etapa no válida.')
            if not estado.confirmada and id_ != 'roi':
                raise ValueError('Solo la ROI admite confirmación pendiente.')
            if estado.salida_id not in self.sesion.artefactos or not self.puede_visitar(indice):
                raise ValueError('La cadena apunta a una salida no disponible.')
            if id_ == 'imagen':
                if (estado.entrada_id is not None or estado.salida_id not in self.sesion.fuentes
                        or self.sesion.artefactos[estado.salida_id].tipo not in ('imagen', 'gris')
                        or estado.operacion or estado.omitida or estado.indice_resultado is not None
                        or estado.salidas != {'original': estado.salida_id}):
                    raise ValueError('El original no corresponde a una fuente de imagen.')
                continue
            if estado.entrada_id != self.salida(indice - 1):
                raise ValueError('Una etapa no recibe la salida de su predecesora.')
            if not estado.operacion:
                if (id_ not in ('escala', 'preparar', 'medir', 'exportar')
                        or estado.salida_id != estado.entrada_id or estado.indice_resultado is not None
                        or estado.parametros or estado.salidas or estado.omitida != (id_ != 'exportar')):
                    raise ValueError('Paso omitido o conservado no válido.')
                if id_ == 'escala' and self.sesion.artefactos[estado.salida_id].metadatos.get('escala'):
                    raise ValueError('La escala omitida conserva una calibración no declarada.')
                continue
            if estado.omitida:
                raise ValueError('Una operación calculada no puede estar omitida.')
            esperado = 'calibrar_escala' if id_ == 'escala' else _OPERACIONES.get(id_, ('',))[0]
            permitidas = (esperado, 'separar_watershed') if id_ == 'etiquetar' else (esperado,)
            if estado.operacion not in permitidas:
                raise ValueError('La operación no corresponde a su etapa.')
            n = estado.indice_resultado
            if type(n) is not int or not ultimo_resultado < n < len(self.sesion.pasos):
                raise ValueError('Orden de resultados no válido.')
            ultimo_resultado = n
            paso = self.sesion.pasos[n]
            entradas = {} if id_ == 'escala' else {_OPERACIONES[id_][1]: estado.entrada_id}
            if (paso['operacion'] != estado.operacion or paso['entradas'] != entradas
                    or paso['parametros'] != estado.parametros or paso['salidas'] != estado.salidas):
                raise ValueError('La etapa no coincide con el cálculo guardado.')
            if id_ == 'escala':
                if (estado.salida_id != estado.entrada_id or
                        self.sesion.artefactos[estado.salida_id].metadatos.get('escala') != self.sesion.resultados[n].resumen):
                    raise ValueError('La calibración no coincide con el original.')
            else:
                claves = ('otsu', 'manual', 'adaptativa') if id_ == 'segmentar' else (_OPERACIONES[id_][2],)
                if estado.salida_id not in [estado.salidas.get(k) for k in claves]:
                    raise ValueError('La salida elegida no pertenece a este paso.')
            if id_ == 'roi':
                meta = self.sesion.artefactos[estado.salida_id].metadatos
                if estado.confirmada != bool(meta.get('roi_confirmada')) or (estado.confirmada and not estado.nota.strip()):
                    raise ValueError('La confirmación de ROI no coincide con la imagen.')


def exportar_recorrido(recorrido: Recorrido, carpeta: str | Path) -> Path:
    """Entrega atómica: todas las versiones, la ruta activa y una sesión reabrible.

    Las ramas anteriores permanecen en el inventario; ``recorrido_activo.json``
    identifica exactamente qué resultado de cada etapa se utilizó para seguir.
    """
    from .exportacion import exportar_versiones

    destino = Path(carpeta).expanduser().resolve()
    if destino.exists():
        raise FileExistsError('La carpeta ya existe. Elija una carpeta nueva para el análisis.')
    if not recorrido.original_id:
        raise ValueError('Importe una imagen antes de exportar el recorrido.')
    recorrido._validar_estado()
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.micrograno-recorrido-', dir=destino.parent) as temporal:
        entrega = Path(temporal) / 'entrega'
        exportar_versiones(recorrido.sesion, entrega)
        recorrido.guardar(entrega / 'sesion_reabrible')
        activo = dict(esquema=1, actual=recorrido.actual,
                      sesion_reabrible='sesion_reabrible/sesion.json',
                      etapas={k: asdict(v) for k, v in recorrido.estados.items()})
        (entrega / 'recorrido_activo.json').write_text(
            json.dumps(activo, ensure_ascii=False, indent=2), encoding='utf-8')
        if destino.exists():
            raise FileExistsError('El destino apareció durante la exportación. Elija otra carpeta.')
        entrega.rename(destino)
    return destino / 'versiones.json'
