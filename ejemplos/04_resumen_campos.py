"""Resumen de una columna CSV de fracciones por unidad de análisis declarada."""
from __future__ import annotations
import argparse
from pathlib import Path
from micrograno import nucleo as mg
from micrograno.archivos import cargar_valores, guardar_resultado


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, required=True)
    parser.add_argument('--columna', default='fraccion_area')
    parser.add_argument('--unidad', choices=('campo','probeta','unidad_independiente'), required=True)
    parser.add_argument('--salida', type=Path, required=True)
    parser.add_argument('--semilla', type=int, default=2026)
    parser.add_argument('--repeticiones', type=int, default=10000)
    args = parser.parse_args()
    valores = cargar_valores(args.csv, args.columna)
    resultado = mg.reporte_fraccion_area(valores, semilla=args.semilla,
        repeticiones=args.repeticiones, unidad_analisis=args.unidad)
    guardar_resultado(resultado, args.salida)
    print(resultado.resumen)
    print('La independencia de los valores depende del diseño de muestreo, no del archivo CSV.')


if __name__ == '__main__':
    main()
