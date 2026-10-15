"""Ejecuta y guarda el catálogo completo con datos artificiales apropiados."""
from __future__ import annotations
import argparse
from pathlib import Path
from micrograno.sinteticos import demostrar_catalogo
from micrograno.sesion import Sesion
from micrograno.archivos import escribir_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida', type=Path, default=Path('sesion_sintetica'))
    args = parser.parse_args()
    sesion, informe = demostrar_catalogo()
    archivo = sesion.guardar(args.salida)
    cargada = Sesion.abrir(archivo)
    informe['reproduccion'] = cargada.reproducir()
    escribir_json(args.salida/'informe.json', informe)
    if not informe['reproduccion']['coincide']:
        raise RuntimeError('Los datos recalculados no coinciden con los guardados.')
    print('Operaciones ejecutadas:', informe['total'])
    print('Sesión y llamadas reproducibles:', archivo)
    print('Datos artificiales; no son resultados de la investigación.')


if __name__ == '__main__':
    main()
