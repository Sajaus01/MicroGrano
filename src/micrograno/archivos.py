"""Entrada/salida explícita, sin pickle ni sustitución de imágenes originales."""
from __future__ import annotations
from pathlib import Path
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import platform
import sys
import numpy as np
import pandas as pd
from PIL import Image
import tifffile
from . import _validacion as v
from .modelos import Resultado


def metadatos_entorno() -> dict:
    """Versiones realmente instaladas, plataforma y fecha UTC de ejecución."""
    paquetes = {}
    for nombre in ('micrograno','numpy','scipy','scikit-image','pandas','Pillow',
                   'matplotlib','tifffile','PySide6','PySide6-Essentials','pytest'):
        try:
            paquetes[nombre] = importlib.metadata.version(nombre)
        except importlib.metadata.PackageNotFoundError:
            paquetes[nombre] = None
    return {'python':sys.version.split()[0],'plataforma':platform.platform(),
            'fecha_utc':datetime.now(timezone.utc).isoformat(),'paquetes':paquetes}


def _jsonable(obj):
    if is_dataclass(obj):
        return _jsonable(asdict(obj))
    if isinstance(obj,np.ndarray):
        return _jsonable(obj.tolist())
    if isinstance(obj,np.generic):
        return _jsonable(obj.item())
    if isinstance(obj,dict):
        return {str(k):_jsonable(v_) for k,v_ in obj.items()}
    if isinstance(obj,(list,tuple)):
        return [_jsonable(x) for x in obj]
    if isinstance(obj,float) and not np.isfinite(obj):
        return 'NaN' if np.isnan(obj) else ('+Infinity' if obj > 0 else '-Infinity')
    if isinstance(obj,Path):
        return str(obj)
    return obj


def escribir_json(ruta: str | Path, datos) -> None:
    """Escribe JSON UTF-8 estricto; no finitos se representan mediante cadenas."""
    Path(ruta).write_text(json.dumps(_jsonable(datos),ensure_ascii=False,indent=2,
                                    allow_nan=False),encoding='utf-8')


def sha256_archivo(ruta: str | Path) -> str:
    """Suma SHA-256 del archivo en bloques; no carga el archivo completo en memoria."""
    h = hashlib.sha256()
    with Path(ruta).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()


def _leer(ruta):
    p = Path(ruta).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f'No existe el archivo: {p}')
    if p.suffix.lower() == '.npy':
        a = np.load(p,allow_pickle=False)
    elif p.suffix.lower() in ('.tif','.tiff'):
        a = tifffile.imread(p)
    else:
        with Image.open(p) as im:
            if getattr(im,'n_frames',1) != 1:
                raise ValueError('Se requiere una imagen de un solo plano, no una secuencia.')
            if im.mode in ('P','CMYK','YCbCr'):
                im = im.convert('RGB')
            a = np.array(im)
    return a


def cargar_imagen(ruta: str | Path) -> np.ndarray:
    """Lee PNG, JPEG, TIFF u otros formatos de Pillow, o NPY; no normaliza."""
    return np.array(v.imagen(_leer(ruta)),copy=True)


def cargar_mascara(ruta: str | Path) -> np.ndarray:
    """Importa una máscara binaria; admite booleanos o valores 0 y 1/255/65535."""
    a = v.arreglo(_leer(ruta),2)
    if a.dtype.kind == 'b':
        return a.copy()
    unicos = np.unique(a)
    if not any(np.isin(unicos,[0,k]).all() for k in (1,255,65535)):
        raise ValueError('El archivo no es una máscara binaria. Umbralice explícitamente una imagen de intensidades.')
    return a != 0


def cargar_etiquetas(ruta: str | Path) -> np.ndarray:
    """Lee identificadores enteros 2D, no una visualización RGB de las etiquetas."""
    return v.etiquetas(_leer(ruta)).copy()


def cargar_valores(ruta: str | Path, columna: str) -> np.ndarray:
    """Lee una columna numérica CSV, separador coma y decimal punto; no descarta faltantes."""
    t = pd.read_csv(ruta)
    if columna not in t.columns:
        raise ValueError(f'Columna no encontrada. Disponibles: {list(t.columns)}')
    return v.vector(pd.to_numeric(t[columna],errors='raise').to_numpy())


def guardar_resultado(resultado: Resultado, carpeta: str | Path,
                       contexto: dict | None = None) -> Path:
    """Exporta NPY exactos, tabla CSV, resumen y contexto a una carpeta nueva."""
    p = Path(carpeta)
    if p.exists():
        raise FileExistsError('Elija una carpeta nueva para no sobrescribir resultados.')
    p.mkdir(parents=True)
    inventario = {}
    for nombre,a in resultado.datos.items():
        if not nombre.isidentifier():
            raise ValueError('Las claves de datos deben ser identificadores seguros.')
        f = p/(nombre+'.npy')
        np.save(f,a,allow_pickle=False)
        inventario[nombre] = {'archivo':f.name,'tipo':resultado.tipos[nombre],
            'forma':list(a.shape),'dtype':str(a.dtype),'sha256':sha256_archivo(f)}
    if len(resultado.tabla.columns):
        resultado.tabla.to_csv(p/'mediciones.csv',index=False,encoding='utf-8-sig')
    escribir_json(p/'resultado.json',{'micrograno':'1.0.0','datos':inventario,
        'resumen':resultado.resumen,'advertencias':resultado.advertencias,
        'contexto':contexto or {},'entorno':metadatos_entorno(),
        'no_finitos':'NaN, +Infinity y -Infinity se codifican como cadenas en JSON.'})
    return p


def exportar_figura(imagen: np.ndarray, ruta: str | Path, *,
                    titulo: str, descripcion: str, fuente: str,
                    tipo: str = 'gris', ppp: int = 300,
                    ancho_cm: float = 14.0,
                    limites: np.ndarray | None = None) -> dict:
    """Exporta JPG/TIF en gris con texto >=11 pt y ficha lateral de procedencia.

    Los ppp son de la figura de salida, no una medida de resolución óptica.
    La copia NPY del resultado es el dato cuantitativo; esta figura es su vista.
    """
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib import font_manager
    from .imagen import convertir_grises
    p = Path(ruta)
    if p.suffix.lower() not in ('.jpg','.jpeg','.tif','.tiff'):
        raise ValueError('Use extensión .jpg o .tif para la figura editorial.')
    if p.exists() or p.with_suffix(p.suffix+'.json').exists():
        raise FileExistsError('La figura o su ficha ya existen; utilice otro nombre.')
    if not all(str(s).strip() for s in (titulo,descripcion,fuente)):
        raise ValueError('La figura requiere título, descripción y fuente.')
    dpi = v.entero(ppp,'ppp',300,1200)
    ancho = v.real(ancho_cm,'ancho_cm',5,30)/2.54
    a = v.arreglo(imagen,2) if np.asarray(imagen).ndim == 2 else convertir_grises(imagen).datos['gris']
    disponible = any(f.name == 'Times New Roman' for f in font_manager.fontManager.ttflist)
    familia = 'Times New Roman' if disponible else 'DejaVu Serif'
    fig = Figure(figsize=(ancho,ancho*min(max(a.shape[0]/a.shape[1],0.5),1.8)+0.7),dpi=dpi)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    if tipo in ('mascara','limites'):
        ax.imshow(a,cmap='gray',vmin=0,vmax=1,interpolation='nearest')
    elif tipo in ('gris','imagen'):
        b = convertir_grises(a).datos['gris']
        ax.imshow(b,cmap='gray',vmin=0,vmax=1,interpolation='nearest')
    else:
        ax.imshow(a,cmap='gray',interpolation='nearest')
    if limites is not None:
        b = v.mascara(limites)
        v.misma_forma(a,b)
        ax.contour(b,levels=[0.5],colors='black',linewidths=1.5)
        ax.contour(b,levels=[0.5],colors='white',linewidths=0.55)
    ax.set_title(titulo,fontfamily=familia,fontsize=12)
    ax.set_xlabel('Columna (px)',fontfamily=familia,fontsize=11)
    ax.set_ylabel('Fila (px)',fontfamily=familia,fontsize=11)
    for label in ax.get_xticklabels()+ax.get_yticklabels():
        label.set_fontsize(11)
        label.set_fontfamily(familia)
    fig.tight_layout()
    # Rasterización final en un solo canal para garantizar escala de grises real.
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    out = Image.fromarray(rgba).convert('L')
    p.parent.mkdir(parents=True,exist_ok=True)
    out.save(p,dpi=(dpi,dpi),**({'quality':95} if p.suffix.lower() in ('.jpg','.jpeg') else {}))
    ficha = {'titulo':titulo,'descripcion':descripcion,'fuente':fuente,
        'ppp':dpi,'tamano_px':list(out.size),'fuente_tipografica':familia,
        'texto_minimo_pt':11,'tipo_dato_representado':tipo,
        'advertencia_tipografica':None if disponible else 'Times New Roman no está instalada; se usó DejaVu Serif. Revisar antes de entregar a la Editorial.',
        'advertencia':'Vista rasterizada, no dato de medición ni resolución óptica.'}
    escribir_json(p.with_suffix(p.suffix+'.json'),ficha)
    return ficha
