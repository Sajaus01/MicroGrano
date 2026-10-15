"""Validación interna. No convierte etiquetas en intensidades ni adivina unidades."""
from __future__ import annotations
import numpy as np
from skimage import util

def entero(x, nombre, minimo=0, maximo=None):
    if isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, np.integer)):
        raise TypeError(f"{nombre} debe ser un entero.")
    x = int(x)
    if x < minimo or (maximo is not None and x > maximo):
        raise ValueError(f"{nombre} fuera del intervalo permitido: {minimo} a {maximo}.")
    return x

def real(x, nombre, minimo=None, maximo=None, positivo=False):
    if isinstance(x, (bool, np.bool_)):
        raise TypeError(f"{nombre} debe ser numérico.")
    x = float(x)
    if not np.isfinite(x) or (minimo is not None and x < minimo) or (maximo is not None and x > maximo) or (positivo and x <= 0):
        raise ValueError(f"{nombre} debe ser finito y estar en el intervalo permitido.")
    return x

def arreglo(a, ndim=None):
    a = np.asarray(a)
    if a.size == 0 or a.dtype.kind not in "buif":
        raise ValueError("Se requiere un arreglo numérico real no vacío.")
    if ndim is not None and a.ndim != ndim:
        raise ValueError(f"Se esperaban {ndim} dimensiones; recibidas {a.ndim}.")
    if not np.isfinite(a).all():
        raise ValueError("La entrada contiene NaN o valores infinitos.")
    return a

def imagen(a):
    a = arreglo(a)
    if a.ndim != 2 and not (a.ndim == 3 and a.shape[-1] in (3, 4)):
        raise ValueError("Se admite una imagen 2D o RGB/RGBA; no pilas ni volúmenes.")
    if a.dtype.kind == 'i':
        raise ValueError("Las intensidades enteras deben ser sin signo. Convierta explícitamente la representación.")
    return a

def unidad(a):
    a = imagen(a)
    if a.dtype.kind == 'f':
        if a.min() < 0 or a.max() > 1:
            raise ValueError("Las intensidades flotantes deben estar en [0,1]; no se reescalan silenciosamente.")
        return a.astype(np.float64, copy=True)
    return util.img_as_float64(a)

def gris(a):
    a = arreglo(a, 2)
    if a.dtype.kind == 'b':
        raise TypeError("Se recibió una máscara, no una imagen de intensidades.")
    return unidad(a)

def mascara(a):
    a = arreglo(a, 2)
    if a.dtype.kind != 'b':
        raise TypeError("La máscara debe ser booleana. Importe o umbralice explícitamente.")
    return a.copy()

def etiquetas(a, clases=False):
    a = arreglo(a, 2)
    if a.dtype.kind not in 'ui' or a.min() < 0:
        raise TypeError("Se requiere un mapa de enteros no negativos; no una máscara.")
    if a.max() > np.iinfo(np.int32).max:
        raise ValueError("Identificador fuera del rango int32.")
    return a.astype(np.int32, copy=True)

def vector(a, minimo=2):
    a = arreglo(a, 1).astype(float)
    if len(a) < minimo:
        raise ValueError(f"Se necesitan al menos {minimo} unidades de análisis.")
    return a

def opcion(x, opciones, nombre):
    if x not in opciones:
        raise ValueError(f"{nombre} debe ser uno de {opciones}.")
    return x

def misma_forma(a, b):
    if a.shape != b.shape:
        raise ValueError("Las entradas deben tener exactamente la misma forma y estar alineadas.")

def escala(s):
    return real(s, "s_um_px (µm/px)", positivo=True)
