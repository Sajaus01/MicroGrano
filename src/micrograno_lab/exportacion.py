"""Exportación de todas las versiones, independiente de la selección del visor.

NPY es la copia exacta. TIFF conserva los valores cuando el formato admite el
tipo de arreglo. Los PNG son vistas de 8 bits y nunca sustituyen esos datos.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
import tempfile
import unicodedata

import numpy as np
from PIL import Image
import tifffile

from micrograno.archivos import escribir_json, metadatos_entorno, sha256_archivo
from micrograno.sesion import Artefacto, Sesion
from micrograno.visualizacion import preparar_vista


def linaje_versiones(sesion: Sesion) -> dict[str, dict]:
    """Relaciona cada versión con las entradas y parámetros que la produjeron."""
    linajes = {
        id_: {"progenitores": [], "operacion": None, "paso": None,
              "entradas": {}, "parametros": {}, "salida": None}
        for id_ in sesion.artefactos
    }
    for numero, paso in enumerate(sesion.pasos, 1):
        for salida, id_ in paso["salidas"].items():
            linajes[id_] = {
                "progenitores": list(dict.fromkeys(paso["entradas"].values())),
                "operacion": paso["operacion"], "paso": numero,
                "entradas": deepcopy(paso["entradas"]),
                "parametros": deepcopy(paso["parametros"]), "salida": salida,
            }
    return linajes


def _nombre_archivo(nombre: str) -> str:
    texto = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", texto).strip("_")[:64] or "dato"


def _admite_tiff(datos: np.ndarray) -> bool:
    imagen = datos.ndim == 2 or (datos.ndim == 3 and datos.shape[-1] in (3, 4))
    # Se omiten, por ejemplo, longdouble y float16: NPY mantiene su precisión.
    # TIFF binario RGB no mantiene sus muestras con todos los lectores.
    tipo = ((datos.dtype.kind == "b" and datos.ndim == 2)
            or (datos.dtype.kind in "ui" and datos.dtype.itemsize in (1, 2, 4, 8))
            or (datos.dtype.kind == "f" and datos.dtype.itemsize in (4, 8)))
    return imagen and tipo


def _vista_png(artefacto: Artefacto, sesion: Sesion) -> tuple[np.ndarray, str]:
    vista = preparar_vista(artefacto, sesion)
    datos = vista["imagen"]
    tipo = vista["tipo"]
    if tipo in ("etiquetas", "marcadores", "clases"):
        # Se colorean identificadores completos, sin truncarlos a 8 bits.
        etiquetas = datos.astype(np.uint64)
        colores = np.stack(((etiquetas * 67) % 193 + 63,
                            (etiquetas * 131) % 193 + 63,
                            (etiquetas * 47) % 193 + 63), axis=-1).astype(np.uint8)
        colores[datos == 0] = 0
        return colores, ("Colores categóricos; identificador 0 en negro (en clases también pertenece al dominio). El PNG no conserva "
                         "los identificadores y los colores pueden repetirse.")
    if datos.dtype.kind == "b":
        return datos.astype(np.uint8) * 255, "Máscara: falso = 0; verdadero = 255."
    a = datos.astype(np.float64)
    if tipo in ("imagen", "gris") and datos.dtype.kind == "u":
        a /= np.iinfo(datos.dtype).max
        transformacion = "Intensidad dividida por el máximo del tipo entero de origen."
    elif tipo in ("imagen", "gris") and a.min() >= 0 and a.max() <= 1:
        transformacion = "Intensidad en [0, 1] representada en 8 bits."
    else:
        minimo, maximo = datos.min().item(), datos.max().item()
        if minimo == maximo:
            a = np.zeros(datos.shape, dtype=np.float64)
        else:
            # Normalizar antes de restar evita desbordar con extremos grandes.
            magnitud = max(abs(float(minimo)), abs(float(maximo)))
            a /= magnitud
            a = (a - a.min()) / (a.max() - a.min())
        transformacion = f"Rango [{minimo}, {maximo}] reescalado a [0, 255] para visualización."
    return np.rint(np.clip(a, 0, 1) * 255).astype(np.uint8), transformacion


def _archivo(ruta: Path, base: Path, **descripcion) -> dict:
    return {"ruta": ruta.relative_to(base).as_posix(),
            "sha256": sha256_archivo(ruta), **descripcion}


def exportar_versiones(sesion: Sesion, carpeta: str | Path, *,
                       incluir_vistas: bool = True) -> Path:
    """Exporta fuentes, ROI y todas las ramas a una carpeta nueva.

    Devuelve la ruta de ``versiones.json``. Cada versión incluye NPY exacto,
    TIFF científico si es compatible y, opcionalmente, una vista PNG. También
    conserva el grafo, metadatos, resultados y tablas de cada paso. Un error
    durante la escritura descarta el temporal y no publica una entrega parcial.
    No depende de Qt ni modifica la sesión.
    """
    destino = Path(carpeta).expanduser().resolve()
    if destino.exists():
        raise FileExistsError("La carpeta ya existe. Elija una carpeta nueva para exportar las versiones.")
    if not sesion.artefactos:
        raise ValueError("La sesión no contiene versiones para exportar.")
    destino.parent.mkdir(parents=True, exist_ok=True)
    linajes = linaje_versiones(sesion)
    with tempfile.TemporaryDirectory(prefix=".micrograno-export-", dir=destino.parent) as temporal:
        base = Path(temporal)
        (base / "datos").mkdir()
        inventario = []
        for numero, (id_, artefacto) in enumerate(sesion.artefactos.items(), 1):
            nombre = f"version_{numero:04d}_{_nombre_archivo(id_)}_{_nombre_archivo(artefacto.nombre)}"
            datos = artefacto.datos
            npy = base / "datos" / f"{nombre}.npy"
            np.save(npy, datos, allow_pickle=False)
            archivos = {"npy": _archivo(npy, base, uso="Dato exacto, sin normalización.")}
            notas = []
            if _admite_tiff(datos):
                tiff = base / "datos" / f"{nombre}.tif"
                tifffile.imwrite(tiff, datos,
                                 photometric="rgb" if datos.ndim == 3 else "minisblack",
                                 metadata={"axes": "YXS" if datos.ndim == 3 else "YX"})
                archivos["tiff"] = _archivo(tiff, base, uso="Dato científico; conserva valores y precisión.")
            else:
                notas.append("TIFF omitido: dimensiones o tipo no compatibles. Los datos exactos están en NPY.")
            if incluir_vistas and datos.ndim >= 2:
                # Tipos de precisión extendida se conservan en NPY; convertirlos
                # a float64 para una vista podría desbordar o eliminar contraste.
                if datos.dtype.kind == "f" and datos.dtype.itemsize > 8:
                    notas.append("PNG omitido para conservar el dato de precisión extendida en NPY.")
                else:
                    (base / "vistas").mkdir(exist_ok=True)
                    png = base / "vistas" / f"{nombre}_vista.png"
                    imagen, transformacion = _vista_png(artefacto, sesion)
                    Image.fromarray(imagen).save(png)
                    archivos["png_vista"] = _archivo(
                        png, base, uso="Vista de 8 bits; no usar para mediciones.",
                        transformacion=transformacion)
            inventario.append({
                "id": id_, "nombre": artefacto.nombre, "tipo": artefacto.tipo,
                "fuente": id_ in sesion.fuentes, "forma": list(datos.shape),
                "dtype": str(datos.dtype), "metadatos": deepcopy(artefacto.metadatos),
                **linajes[id_], "archivos": archivos, "notas": notas,
            })
        resultados = []
        for numero, resultado in enumerate(sesion.resultados, 1):
            registro = {"paso": numero, "resumen": resultado.resumen,
                        "advertencias": resultado.advertencias,
                        "tipos": resultado.tipos,
                        "tabla": {"columnas": list(resultado.tabla.columns),
                                  "valores": resultado.tabla.values.tolist(),
                                  "dtypes": {str(c): str(d) for c, d in resultado.tabla.dtypes.items()}},
                        "archivos": {}}
            if len(resultado.tabla.columns):
                (base / "tablas").mkdir(exist_ok=True)
                csv = base / "tablas" / f"paso_{numero:03d}.csv"
                resultado.tabla.to_csv(csv, index=False, encoding="utf-8-sig")
                registro["archivos"]["csv"] = _archivo(csv, base)
            resultados.append(registro)
        escribir_json(base / "versiones.json", {
            "esquema": 1, "contenido": "exportacion_versiones_micrograno",
            "nombre": sesion.nombre, "entorno": metadatos_entorno(),
            "fuentes": list(sesion.fuentes), "versiones": inventario,
            "pasos": sesion.pasos, "resultados": resultados, "eventos": sesion.eventos,
            "formatos": {
                "npy": "Valores y dtype originales; cargar con numpy.load(..., allow_pickle=False).",
                "tiff": "Datos científicos sin conversión, cuando el tipo es compatible.",
                "png_vista": "Representación de 8 bits; su transformación se documenta por versión.",
            },
        })
        if destino.exists():
            raise FileExistsError("La carpeta de destino apareció durante la exportación. Elija otra carpeta.")
        base.rename(destino)
    return destino / "versiones.json"
