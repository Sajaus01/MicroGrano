"""Entrada de consola independiente de Qt."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .archivos import _jsonable, escribir_json, metadatos_entorno
from .catalogo import CATALOGO, verificar_catalogo
from .sesion import Sesion


def main(argv=None) -> int:
    parser=argparse.ArgumentParser(prog='micrograno',description='MicroGrano 1.0.0')
    sub=parser.add_subparsers(dest='comando',required=True)
    sub.add_parser('catalogo',help='Listar todas las operaciones científicas.')
    sub.add_parser('entorno',help='Mostrar las versiones instaladas.')
    demo=sub.add_parser('demo',help='Ejecutar el catálogo completo con datos sintéticos.')
    demo.add_argument('--salida',type=Path,default=Path('prueba_micrograno'))
    rep=sub.add_parser('reproducir',help='Recalcular una sesión y comparar los resultados.')
    rep.add_argument('sesion',type=Path)
    rep.add_argument('--salida',type=Path)
    args=parser.parse_args(argv)
    try:
        verificar_catalogo()
        if args.comando=='catalogo':
            for op in CATALOGO.values():
                print(f'{op.id:28} | {op.grupo:24} | {op.libro}')
        elif args.comando=='entorno':
            print(json.dumps(metadatos_entorno(),ensure_ascii=False,indent=2))
        elif args.comando=='demo':
            from .sinteticos import demostrar_catalogo
            s,informe=demostrar_catalogo()
            s.guardar(args.salida)
            informe['reproduccion']=s.reproducir()
            escribir_json(args.salida/'informe_demo.json',informe)
            print(f'{informe["total"]} operaciones ejecutadas. Sesión: {args.salida.resolve()}')
            print('Son datos sintéticos; no sustentan conclusiones metalográficas.')
        elif args.comando=='reproducir':
            informe=Sesion.abrir(args.sesion).reproducir(args.salida)
            print(json.dumps(_jsonable(informe),ensure_ascii=False,indent=2))
            return 0 if informe['coincide'] else 2
        return 0
    except (ValueError,TypeError,OSError,KeyError) as exc:
        print(f'Error: {exc}',file=sys.stderr)
        return 1
