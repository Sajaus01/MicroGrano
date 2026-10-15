import json
import numpy as np
from PIL import Image
import pytest
import tifffile

from micrograno import Sesion, EscalaEspacial
from micrograno.archivos import sha256_archivo
from micrograno_lab import exportacion
from micrograno_lab.exportacion import exportar_versiones, linaje_versiones


def test_exporta_original_roi_grises_y_todas_las_ramas(tmp_path):
    sesion = Sesion("Ensayo de versiones")
    original = np.arange(1200, dtype=np.uint16).reshape(20, 20, 3) * 50
    fuente = sesion.agregar(original, "imagen", "Original / muestra")
    sesion.establecer_escala(fuente, EscalaEspacial(0.25))
    _, roi = sesion.ejecutar("extraer_roi", {"imagen": fuente},
                              {"r0": 2, "r1": 18, "c0": 3, "c1": 17})
    sesion.confirmar_roi(roi["roi"], "Región sintética sin anotaciones")
    _, gris = sesion.ejecutar("convertir_grises", {"imagen": roi["roi"]})
    _, canales = sesion.ejecutar("separar_canales", {"imagen": roi["roi"]})
    _, mascaras = sesion.ejecutar("umbralizar", {"imagen": gris["gris"]}, {"bloque": 3})
    sesion.ejecutar("histograma_percentiles", {"imagen": gris["gris"]})
    ruta = exportar_versiones(sesion, tmp_path / "versiones")
    registro = json.loads(ruta.read_text(encoding="utf-8"))
    versiones = {v["id"]: v for v in registro["versiones"]}
    assert versiones.keys() == sesion.artefactos.keys()
    assert versiones[fuente]["progenitores"] == []
    assert versiones[roi["roi"]]["progenitores"] == [fuente]
    assert versiones[gris["gris"]]["progenitores"] == [roi["roi"]]
    for id_ in canales.values():
        assert versiones[id_]["progenitores"] == [roi["roi"]]
    for id_ in mascaras.values():
        assert versiones[id_]["operacion"] == "umbralizar"
        assert versiones[id_]["progenitores"] == [gris["gris"]]
    assert versiones[roi["roi"]]["metadatos"]["origen_rc"] == [2, 3]
    assert versiones[roi["roi"]]["metadatos"]["escala"]["um_por_px"] == 0.25
    for id_, version in versiones.items():
        original = sesion.artefactos[id_].datos
        npy = ruta.parent / version["archivos"]["npy"]["ruta"]
        copia = np.load(npy, allow_pickle=False)
        assert copia.dtype == original.dtype
        np.testing.assert_array_equal(copia, original)
        for archivo in version["archivos"].values():
            assert sha256_archivo(ruta.parent / archivo["ruta"]) == archivo["sha256"]
        if "tiff" in version["archivos"]:
            tiff = tifffile.imread(ruta.parent / version["archivos"]["tiff"]["ruta"])
            assert tiff.dtype == original.dtype
            np.testing.assert_array_equal(tiff, original)
    assert len(registro["resultados"]) == len(sesion.resultados)
    assert (ruta.parent / registro["resultados"][-1]["archivos"]["csv"]["ruta"]).is_file()
    np.testing.assert_array_equal(sesion.artefactos[fuente].datos,
                                  np.arange(1200, dtype=np.uint16).reshape(20, 20, 3) * 50)


@pytest.mark.parametrize("datos,tipo", [
    (np.array([[0, 65535], [1024, 32000]], dtype=np.uint16), "imagen"),
    (np.array([[0, 17], [70000, 2147483647]], dtype=np.int32), "etiquetas"),
    (np.array([[0, 1 / 3], [np.nextafter(1., 0.), 1.]], dtype=np.float64), "gris"),
    (np.array([[True, False], [False, True]]), "mascara"),
    (np.array([[[True, False, True], [False, True, False]]]), "imagen"),
    (np.arange(16, dtype=np.uint16).reshape(2, 2, 4), "imagen"),
    (np.array([[1., 2.], [3., 4.]], dtype=np.float16), "mapa"),
    (np.array([1., 2., 3.]), "valores"),
])
def test_precision_y_vistas_explicitas(tmp_path, datos, tipo):
    sesion = Sesion()
    sesion.agregar(datos, tipo, "Dato")
    ruta = exportar_versiones(sesion, tmp_path / "salida")
    version = json.loads(ruta.read_text(encoding="utf-8"))["versiones"][0]
    archivos = version["archivos"]
    copia = np.load(ruta.parent / archivos["npy"]["ruta"], allow_pickle=False)
    assert copia.dtype == datos.dtype
    assert copia.tobytes() == datos.tobytes()
    if (datos.ndim >= 2 and datos.dtype != np.float16
            and not (datos.dtype == bool and datos.ndim == 3)):
        copia_tiff = tifffile.imread(ruta.parent / archivos["tiff"]["ruta"])
        assert copia_tiff.dtype == datos.dtype
        assert copia_tiff.tobytes() == datos.tobytes()
    else:
        assert "tiff" not in archivos
    if datos.ndim >= 2:
        png = archivos["png_vista"]
        assert "no usar para mediciones" in png["uso"]
        assert png["transformacion"]
        with Image.open(ruta.parent / png["ruta"]) as imagen:
            assert imagen.size == (datos.shape[1], datos.shape[0])
    else:
        assert "png_vista" not in archivos


def test_nombres_duplicados_y_rutas_no_salen_del_destino(tmp_path):
    sesion = Sesion()
    for nombre in ("Duplicado", "Duplicado", "../dato", "..\\dato", "CON", "á/?"):
        sesion.agregar(np.eye(4), "gris", nombre)
    ruta = exportar_versiones(sesion, tmp_path / "salida", incluir_vistas=False)
    versiones = json.loads(ruta.read_text(encoding="utf-8"))["versiones"]
    nombres = [v["archivos"]["npy"]["ruta"] for v in versiones]
    assert len(set(nombres)) == len(nombres)
    assert all((ruta.parent / nombre).resolve().is_relative_to(ruta.parent) for nombre in nombres)
    assert not (ruta.parent / "vistas").exists()
    assert not list(tmp_path.glob(".micrograno-export-*"))


def test_no_sobrescribe_carpeta_existente(tmp_path):
    sesion = Sesion()
    sesion.agregar(np.eye(4), "gris", "imagen")
    destino = tmp_path / "salida"
    destino.mkdir()
    prueba = destino / "conservar.txt"
    prueba.write_text("No modificar", encoding="utf-8")
    with pytest.raises(FileExistsError, match="carpeta ya existe"):
        exportar_versiones(sesion, destino)
    assert prueba.read_text(encoding="utf-8") == "No modificar"
    assert list(destino.iterdir()) == [prueba]


def test_fallo_de_escritura_no_entrega_exportacion_parcial(tmp_path, monkeypatch):
    sesion = Sesion()
    sesion.agregar(np.eye(4), "gris", "imagen")
    def fallo(*args, **kwargs):
        raise OSError("Error de disco simulado")
    monkeypatch.setattr(exportacion.tifffile, "imwrite", fallo)
    with pytest.raises(OSError, match="Error de disco"):
        exportar_versiones(sesion, tmp_path / "salida")
    assert list(tmp_path.iterdir()) == []


def test_no_exporta_sesion_vacia(tmp_path):
    with pytest.raises(ValueError, match="no contiene versiones"):
        exportar_versiones(Sesion(), tmp_path / "salida")
    assert list(tmp_path.iterdir()) == []


def test_linaje_con_multiples_entradas_sin_modificar_sesion():
    sesion = Sesion()
    fuente = sesion.agregar(np.eye(10), "gris", "Original")
    sesion.confirmar_roi(fuente, "Dato sintético")
    _, salida = sesion.ejecutar("evaluar_referencia", {"candidata": fuente, "referencia": fuente})
    linajes = linaje_versiones(sesion)
    for id_ in salida.values():
        assert linajes[id_]["progenitores"] == [fuente]
        assert linajes[id_]["entradas"] == {"candidata": fuente, "referencia": fuente}
        linajes[id_]["entradas"]["candidata"] = "cambio_externo"
    assert sesion.pasos[0]["entradas"]["candidata"] == fuente


def test_exporta_todos_los_resultados_del_catalogo(tmp_path):
    from micrograno.sinteticos import demostrar_catalogo

    sesion, _ = demostrar_catalogo()
    ruta = exportar_versiones(sesion, tmp_path / "catalogo")
    registro = json.loads(ruta.read_text(encoding="utf-8"))
    assert len(registro["resultados"]) == 39
    assert len(registro["versiones"]) == len(sesion.artefactos)
    for version in registro["versiones"]:
        dato = np.load(ruta.parent / version["archivos"]["npy"]["ruta"], allow_pickle=False)
        np.testing.assert_array_equal(dato, sesion.artefactos[version["id"]].datos)
