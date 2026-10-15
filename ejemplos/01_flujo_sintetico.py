"""Ejemplo directo de biblioteca. Todos los datos y la escala son sintéticos."""
from __future__ import annotations
import argparse
from pathlib import Path
from micrograno import nucleo as mg
from micrograno.archivos import guardar_resultado, escribir_json
from micrograno.sinteticos import crear_conjunto


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--salida', type=Path, default=Path('ejemplo_sintetico'))
    args = parser.parse_args()
    if args.salida.exists():
        parser.error('Elija una carpeta de salida nueva.')
    datos = crear_conjunto()
    # La máscara es una entrada conocida de la prueba, no una validación real.
    separacion = mg.separar_watershed(datos['mascara'], min_distance=10, area_minima=20)
    medidas = mg.descriptores_forma(separacion.datos['etiquetas'], s_um_px=0.5)
    args.salida.mkdir(parents=True)
    guardar_resultado(separacion, args.salida/'segmentacion')
    guardar_resultado(medidas, args.salida/'medidas')
    escribir_json(args.salida/'procedencia.json', {
        'sintetico': True, 'escala_convencional_um_px': 0.5,
        'uso': 'Comprobación del software. No es un resultado metalográfico.'})
    print(medidas.tabla.to_string(index=False))
    print('Resultados sintéticos guardados en', args.salida)


if __name__ == '__main__':
    main()
