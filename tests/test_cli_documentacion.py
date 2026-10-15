"""La documentación, consola y datos de demostración se verifican con la API."""
from pathlib import Path
import re
import json
import pytest
from micrograno.cli import main
from micrograno.catalogo import CATALOGO
from micrograno.sinteticos import guardar_conjunto

ROOT=Path(__file__).resolve().parents[1]

def test_consola_catalogo_y_entorno(capsys):
    assert main(['catalogo'])==0
    salida=capsys.readouterr().out
    assert all(k in salida for k in CATALOGO)
    assert main(['entorno'])==0
    entorno=json.loads(capsys.readouterr().out)
    assert entorno['paquetes']['micrograno']=='1.0.0'


def test_demo_consola_y_reproduccion(tmp_path):
    destino=tmp_path/'prueba'
    assert main(['demo','--salida',str(destino)])==0
    assert main(['reproducir',str(destino/'sesion.json')])==0
    assert main(['demo','--salida',str(destino)])==1


def test_consola_error_entrada_inexistente(tmp_path):
    assert main(['reproducir',str(tmp_path/'no_existe.json')])==1


def test_documentacion_de_todas_las_operaciones():
    api=(ROOT/'docs/api.md').read_text(encoding='utf-8')
    correspondencia=(ROOT/'docs/correspondencia_libro.md').read_text(encoding='utf-8')
    for nombre in CATALOGO:
        assert f'## `{nombre}`' in api
        assert f'| `{nombre}` |' in correspondencia
    assert api.count('### Ejemplo ejecutable')==len(CATALOGO)


def test_referencias_catalogo_provienen_del_inventario():
    bib=(ROOT/'docs/referencias_libro.bib').read_text(encoding='utf-8')
    claves=set(re.findall(r'@\w+\s*\{\s*([^,]+),',bib))
    assert {k for op in CATALOGO.values() for k in op.referencias}<=claves


def test_generador_no_sobrescribe(tmp_path):
    destino=tmp_path/'datos'
    guardar_conjunto(destino)
    assert (destino/'imagen_sintetica_16bits.tif').exists()
    assert json.loads((destino/'procedencia.json').read_text())['sinteticos'] is True
    with pytest.raises(FileExistsError):guardar_conjunto(destino)
