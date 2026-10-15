"""Sesiones trazables: grafo de operaciones, entradas inmutables y reproducción."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import json
import tempfile
import shutil
import numpy as np
import pandas as pd
from . import _validacion as v
from .modelos import Resultado, EscalaEspacial, TIPOS
from .catalogo import CATALOGO, ejecutar, resolver_parametros
from .archivos import escribir_json, sha256_archivo, metadatos_entorno, _jsonable

@dataclass
class Artefacto:
    """Un arreglo tipado y sus coordenadas/procedencia; no reemplaza su fuente."""
    id: str
    nombre: str
    tipo: str
    datos: np.ndarray
    metadatos: dict = field(default_factory=dict)

    def __post_init__(self):
        a = np.array(self.datos,copy=True)
        if self.tipo not in TIPOS:
            raise ValueError('Tipo de artefacto no admitido.')
        if self.tipo == 'imagen':
            v.imagen(a)
        elif self.tipo == 'gris':
            v.gris(a)
        elif self.tipo in ('mascara','limites'):
            v.mascara(a)
        elif self.tipo in ('etiquetas','marcadores','clases'):
            v.etiquetas(a)
        elif self.tipo in ('valores','distribucion'):
            v.arreglo(a,1)
        else:
            v.arreglo(a,2)
        a.setflags(write=False)
        self.datos = a
        self.metadatos = deepcopy(self.metadatos)


class Sesion:
    """Gestiona una sesión sin dependencias de Qt.

    Toda imagen analizada debe tener confirmación explícita de ROI sin anotaciones.
    La escala se asocia a un artefacto; no pasa automáticamente a otra imagen.
    Cambiar escala o ROI no recalcula ni reescribe resultados previos.
    """
    def __init__(self, nombre: str = 'Análisis de micrografías'):
        self.nombre = nombre
        self.artefactos: dict[str,Artefacto] = {}
        self.pasos: list[dict] = []
        self.resultados: list[Resultado] = []
        self.fuentes: list[str] = []
        self.eventos: list[dict] = []
        self.entorno_creacion = metadatos_entorno()

    def _agregar(self,datos,tipo,nombre,metadatos):
        id_ = f'a{len(self.artefactos)+1:06d}'
        self.artefactos[id_] = Artefacto(id_,nombre,tipo,datos,metadatos)
        return id_

    def agregar(self, datos: np.ndarray, tipo: str, nombre: str,
                metadatos: dict | None = None) -> str:
        """Importa una fuente; la escala y confirmación de otra fuente no se heredan."""
        meta = {'escala':None,'roi_confirmada':False,'origen_rc':[0,0],
                'procedencia':'No declarada'}
        meta.update(deepcopy(metadatos or {}))
        id_ = self._agregar(datos,tipo,nombre,meta)
        self.artefactos[id_].metadatos['raiz'] = id_
        self.fuentes.append(id_)
        return id_

    def confirmar_roi(self, id_: str, nota: str) -> None:
        """Registra la revisión del dominio; exige una anotación del responsable."""
        if not nota.strip():
            raise ValueError('Anote el criterio de exclusión de barra y anotaciones.')
        a = self.artefactos[id_]
        a.metadatos.update(roi_confirmada=True,nota_roi=nota)
        self.eventos.append({'evento':'confirmacion_roi','artefacto':id_,
            'nota':nota,'fecha_utc':datetime.now(timezone.utc).isoformat()})

    def establecer_escala(self, id_: str, escala: EscalaEspacial,
                           documentacion: dict | None = None) -> None:
        """Asocia una escala a este dato; las medidas ya calculadas no cambian."""
        if not isinstance(escala,EscalaEspacial):
            raise TypeError('Se requiere una EscalaEspacial validada.')
        if self.artefactos[id_].datos.ndim < 2:
            raise ValueError('La calibración espacial solo se asocia a datos de imagen.')
        self.artefactos[id_].metadatos['escala'] = escala.como_dict()
        self.artefactos[id_].metadatos['calibracion_documentacion'] = deepcopy(documentacion or {})
        self.eventos.append({'evento':'calibracion','artefacto':id_,
            'escala':escala.como_dict(),'documentacion':deepcopy(documentacion or {}),'fecha_utc':datetime.now(timezone.utc).isoformat()})

    def anotar(self, id_: str, anotaciones: dict[str,str]) -> None:
        """Registra metadatos declarados, sin inferir material ni sobrescribir geometría."""
        if not all(isinstance(k,str) and isinstance(x,str) for k,x in anotaciones.items()):
            raise TypeError('Las anotaciones deben ser pares de texto.')
        self.artefactos[id_].metadatos.setdefault('anotaciones',{}).update(deepcopy(anotaciones))
        self.eventos.append({'evento':'anotacion','artefacto':id_,
            'anotaciones':deepcopy(anotaciones),'fecha_utc':datetime.now(timezone.utc).isoformat()})

    def asociar_fuente(self, id_: str, imagen_id: str, nota: str) -> None:
        """Asocia un mapa importado a una imagen alineada por decisión explícita."""
        dato, imagen = self.artefactos[id_], self.artefactos[imagen_id]
        if dato.tipo not in ('mascara','limites','etiquetas','clases','marcadores'):
            raise ValueError('Solo se asocian mapas importados a su imagen fuente.')
        if imagen.tipo not in ('imagen','gris') or dato.datos.shape != imagen.datos.shape[:2]:
            raise ValueError('La imagen fuente debe tener la misma forma y estar alineada.')
        if not nota.strip():
            raise ValueError('Anote cómo se verificó la alineación de los datos.')
        for clave in ('raiz','origen_rc','escala','roi_confirmada','nota_roi'):
            if clave in imagen.metadatos:
                dato.metadatos[clave] = deepcopy(imagen.metadatos[clave])
        dato.metadatos['asociacion_imagen'] = imagen_id
        dato.metadatos['nota_alineacion'] = nota
        self.eventos.append({'evento':'asociar_fuente','artefacto':id_,
            'imagen':imagen_id,'nota':nota,'fecha_utc':datetime.now(timezone.utc).isoformat()})

    def ejecutar(self, operacion: str, entradas: dict[str,str] | None = None,
                 parametros: dict | None = None) -> tuple[Resultado,dict[str,str]]:
        """Ejecuta una operación registrada y añade salidas sin cambiar sus entradas."""
        if operacion not in CATALOGO:
            raise ValueError('Operación no registrada.')
        op = CATALOGO[operacion]
        ids = {k:x for k,x in (entradas or {}).items() if x is not None}
        nombres = {e.nombre for e in op.entradas}
        if set(ids)-nombres:
            raise ValueError('Nombres de entrada no declarados en el catálogo.')
        for e in op.entradas:
            if e.nombre not in ids:
                if not e.opcional:
                    raise ValueError(f'Falta seleccionar {e.nombre}.')
            elif ids[e.nombre] not in self.artefactos or self.artefactos[ids[e.nombre]].tipo not in e.tipos:
                raise ValueError(f'{e.nombre} requiere tipos {e.tipos}.')
        principales = [ids[e.nombre] for e in op.entradas if e.nombre in ids]
        principal = self.artefactos[principales[0]] if principales else None
        excepciones = {'explorar_imagen','convertir_grises','separar_canales','extraer_roi'}
        if principal and principal.tipo != 'valores' and operacion not in excepciones:
            if not principal.metadatos.get('roi_confirmada',False):
                raise ValueError('Confirme primero que la región de análisis excluye barra de escala y anotaciones.')
        p = dict(parametros or {})
        if 's_um_px' in op.parametros and principal:
            escala = principal.metadatos.get('escala')
            if not escala:
                raise ValueError('Asocie una calibración a este dato antes de medir en unidades físicas.')
            if 's_um_px' not in p:
                p['s_um_px'] = escala['um_por_px']
            if not np.isclose(float(p['s_um_px']),float(escala['um_por_px']),rtol=1e-12,atol=0):
                raise ValueError('El parámetro de escala no coincide con la calibración asociada al dato.')
        p = resolver_parametros(operacion,p)
        contextos = {n:deepcopy(self.artefactos[x].metadatos) for n,x in ids.items()}
        datos = {n:self.artefactos[x].datos for n,x in ids.items()}
        r = ejecutar(operacion,datos,p)
        salidas = {}
        for clave,a in r.datos.items():
            meta = deepcopy(principal.metadatos) if principal else {}
            tipo = r.tipos[clave]
            if operacion == 'extraer_roi' and principal:
                tipo = principal.tipo
                or_,oc = meta.get('origen_rc',[0,0])
                meta['origen_rc'] = [or_+p['r0'],oc+p['c0']]
                meta['roi_local_rc'] = [p['r0'],p['r1'],p['c0'],p['c1']]
                meta['roi_confirmada'] = False
            if principal and principal.tipo == 'limites' and operacion in {
                'variantes_morfologicas','limpiar_mascara','invertir_mascara'}:
                tipo = 'limites'
            if operacion == 'reducir_y_ampliar':
                meta.update(escala=None,muestreo_modificado=True)
            if operacion == 'agregar_ruido':
                meta['ruido_sintetico'] = True
            meta.update(paso=len(self.pasos)+1,operacion=operacion,salida=clave)
            salidas[clave] = self._agregar(a,tipo,f'{op.titulo} / {clave}',meta)
        self.pasos.append({'operacion':operacion,'entradas':ids,'parametros':deepcopy(p),
            'contextos_entrada':contextos,'salidas':salidas,
            'fecha_utc':datetime.now(timezone.utc).isoformat()})
        self.resultados.append(r)
        return r,salidas

    def codigo(self) -> str:
        """Genera llamadas Python explícitas, sin depender del estado de la interfaz."""
        lineas = ['"""Reproduce las operaciones. Ejecútelo junto a sesion.json y datos/."""',
            'from pathlib import Path','import numpy as np',
            'from micrograno import nucleo as mg',
            'from micrograno.archivos import guardar_resultado, escribir_json',
            'from micrograno.modelos import EscalaEspacial','',
            'base = Path(__file__).resolve().parent',
            'destino = base / "salidas_reproducidas"',
            'if destino.exists():',
            '    raise FileExistsError("Use una carpeta nueva; salidas_reproducidas ya existe.")',
            'destino.mkdir()','']
        for id_ in self.fuentes:
            lineas.append(f'{id_} = np.load(base / "datos/{id_}.npy", allow_pickle=False)')
        for i,paso in enumerate(self.pasos,1):
            args = [f'{n}={x}' for n,x in paso['entradas'].items()]
            args += [f'{n}={valor!r}' for n,valor in paso['parametros'].items()]
            lineas.extend(['',f'# Paso {i}: {CATALOGO[paso["operacion"]].titulo}',
                f'r{i} = mg.{paso["operacion"]}('+', '.join(args)+')',
                f'if isinstance(r{i}, EscalaEspacial):',
                f'    escribir_json(destino / "paso_{i:03d}_escala.json", r{i}.como_dict())',
                'else:',f'    guardar_resultado(r{i}, destino / "paso_{i:03d}")'])
            for clave,id_ in paso['salidas'].items():
                lineas.append(f'{id_} = r{i}.datos[{clave!r}]')
        lineas += ['', 'print("Reproducción terminada:", destino)', '']
        return '\n'.join(lineas)

    def guardar(self, carpeta: str | Path) -> Path:
        """Escribe una sesión autocontenida a una carpeta nueva mediante renombrado."""
        p = Path(carpeta).resolve()
        if p.exists():
            raise FileExistsError('La carpeta ya existe. Elija una carpeta nueva para esta sesión.')
        if sum(a.datos.nbytes + 4096 for a in self.artefactos.values()) > 2_000_000_000:
            raise ValueError('La sesión supera 2 GB. Guarde un campo o una ROI por sesión.')
        p.parent.mkdir(parents=True,exist_ok=True)
        temporal = Path(tempfile.mkdtemp(prefix='.micrograno-',dir=p.parent))
        try:
            (temporal/'datos').mkdir()
            inventario = []
            for id_,a in self.artefactos.items():
                f = temporal/'datos'/f'{id_}.npy'
                np.save(f,a.datos,allow_pickle=False)
                inventario.append({'id':id_,'nombre':a.nombre,'tipo':a.tipo,
                    'archivo':f'datos/{id_}.npy','sha256':sha256_archivo(f),
                    'metadatos':a.metadatos})
            resultados = []
            for r in self.resultados:
                resultados.append({'resumen':r.resumen,'advertencias':r.advertencias,
                    'tipos':r.tipos,'columnas':list(r.tabla.columns),
                    'tabla':r.tabla.values.tolist(),'dtypes':{str(c):str(d) for c,d in r.tabla.dtypes.items()}})
            escribir_json(temporal/'sesion.json',{'esquema':1,'micrograno':'1.0.0',
                'nombre':self.nombre,'entorno_creacion':self.entorno_creacion,
                'entorno_guardado':metadatos_entorno(),'fuentes':self.fuentes,
                'artefactos':inventario,'pasos':self.pasos,'resultados':resultados,
                'eventos':self.eventos})
            (temporal/'reproducir.py').write_text(self.codigo(),encoding='utf-8')
            temporal.rename(p)
        except Exception:
            shutil.rmtree(temporal,ignore_errors=True)
            raise
        return p/'sesion.json'

    @classmethod
    def abrir(cls, ruta: str | Path) -> 'Sesion':
        """Abre y verifica hashes; no ejecuta scripts ni usa pickle."""
        p = Path(ruta).resolve()
        if p.is_dir():
            p = p/'sesion.json'
        if p.stat().st_size > 50_000_000:
            raise ValueError('El manifiesto supera el tamaño de seguridad admitido.')
        registro = json.loads(p.read_text(encoding='utf-8'))
        if registro.get('esquema') != 1 or registro.get('micrograno') != '1.0.0':
            raise ValueError('Esquema o versión de sesión no compatibles.')
        s = cls(registro['nombre'])
        s.entorno_creacion = registro['entorno_creacion']
        acumulado = 0
        for entrada in registro['artefactos']:
            id_ = entrada['id']
            if not (len(id_)==7 and id_.startswith('a') and id_[1:].isdigit()) or id_ in s.artefactos:
                raise ValueError('Identificador de artefacto inválido o repetido.')
            esperado = f'datos/{id_}.npy'
            if entrada['archivo'] != esperado:
                raise ValueError('Ruta de datos no permitida.')
            f = (p.parent/esperado).resolve()
            if not f.is_relative_to(p.parent):
                raise ValueError('Un dato intenta salir de la carpeta de sesión.')
            acumulado += f.stat().st_size
            if acumulado > 2_000_000_000:
                raise ValueError('La sesión supera 2 GB; divida el análisis por campos.')
            if sha256_archivo(f) != entrada['sha256']:
                raise ValueError(f'Hash incorrecto: {f.name}. El archivo cambió o está dañado.')
            a = np.load(f,allow_pickle=False)
            s.artefactos[id_] = Artefacto(id_,entrada['nombre'],entrada['tipo'],a,entrada['metadatos'])
        s.fuentes = registro['fuentes']
        if any(x not in s.artefactos for x in s.fuentes):
            raise ValueError('Falta un artefacto fuente.')
        s.pasos = registro['pasos']; s.eventos = registro.get('eventos',[])
        if len(s.pasos) != len(registro['resultados']):
            raise ValueError('El número de pasos y resultados no coincide.')
        disponibles = set(s.fuentes)
        for paso,rr in zip(s.pasos,registro['resultados']):
            if paso['operacion'] not in CATALOGO:
                raise ValueError('La sesión contiene una operación no registrada.')
            if any(x not in disponibles for x in paso['entradas'].values()):
                raise ValueError('El grafo contiene una dependencia no disponible o un ciclo.')
            if any(x not in s.artefactos or x in disponibles for x in paso['salidas'].values()):
                raise ValueError('Salida no disponible o reutilizada en el grafo.')
            disponibles.update(paso['salidas'].values())
            datos = {k:s.artefactos[x].datos for k,x in paso['salidas'].items()}
            t = pd.DataFrame(rr['tabla'],columns=rr['columnas'])
            for c,dt in rr.get('dtypes',{}).items():
                if dt.startswith(('float','int','uint')):
                    t[c] = pd.to_numeric(t[c].replace({'NaN':np.nan,'+Infinity':np.inf,'-Infinity':-np.inf}),errors='raise').astype(dt)
                elif dt == 'bool':
                    t[c] = t[c].astype(bool)
            s.resultados.append(Resultado(datos,rr['tipos'],t,rr['resumen'],rr['advertencias']))
        return s

    def reproducir(self, destino: str | Path | None = None) -> dict:
        """Recalcula desde las fuentes y compara arreglos, tablas y resúmenes guardados."""
        nueva = Sesion(self.nombre+' / reproducción')
        ids = {}
        for id_ in self.fuentes:
            a = self.artefactos[id_]
            ids[id_] = nueva.agregar(a.datos,a.tipo,a.nombre,a.metadatos)
        def remapear(meta):
            copia = deepcopy(meta)
            for clave in ('raiz','asociacion_imagen'):
                if copia.get(clave) in ids:
                    copia[clave] = ids[copia[clave]]
            return copia
        for original,nuevo in ids.items():
            nueva.artefactos[nuevo].metadatos = remapear(self.artefactos[original].metadatos)
        errores = []
        for i,(paso,esperado) in enumerate(zip(self.pasos,self.resultados),1):
            for rol,original in paso['entradas'].items():
                nueva.artefactos[ids[original]].metadatos = remapear(paso['contextos_entrada'][rol])
            r,salidas = nueva.ejecutar(paso['operacion'],
                {rol:ids[x] for rol,x in paso['entradas'].items()},paso['parametros'])
            if r.datos.keys() != esperado.datos.keys():
                errores.append(f'Paso {i}: claves de salida distintas.')
            else:
                for clave,a in r.datos.items():
                    b = esperado.datos[clave]
                    igual = a.shape == b.shape and (np.allclose(a,b,rtol=1e-10,atol=1e-12,equal_nan=True)
                        if a.dtype.kind == 'f' else np.array_equal(a,b))
                    if not igual:
                        errores.append(f'Paso {i}: arreglo {clave} distinto.')
            try:
                pd.testing.assert_frame_equal(r.tabla,esperado.tabla,check_dtype=False,check_index_type=False,check_column_type=False,
                                               rtol=1e-10,atol=1e-12)
            except AssertionError:
                errores.append(f'Paso {i}: tabla distinta.')
            if _jsonable(r.resumen) != _jsonable(esperado.resumen):
                errores.append(f'Paso {i}: resumen distinto.')
            for clave,id_ in paso['salidas'].items():
                ids[id_] = salidas[clave]
        informe = {'pasos_recalculados':len(self.pasos),'coincide':not errores,
            'diferencias':errores,'entorno':metadatos_entorno(),
            'tolerancia_arreglos_flotantes':{'rtol':1e-10,'atol':1e-12},
            'advertencia':'Coincidencia computacional no equivale a validación metalográfica.'}
        if destino is not None:
            nueva.guardar(destino)
            escribir_json(Path(destino)/'verificacion_reproduccion.json',informe)
        return informe
