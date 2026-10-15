"""Registra una prueba sobre una ROI explícita. No valida una segmentación real."""
from __future__ import annotations
import argparse
from pathlib import Path
from micrograno import Sesion, EscalaEspacial
from micrograno.archivos import cargar_imagen, sha256_archivo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imagen', type=Path, required=True)
    parser.add_argument('--roi', type=int, nargs=4, required=True,
                        metavar=('R0', 'R1', 'C0', 'C1'))
    parser.add_argument('--nota-roi', required=True,
                        help='Criterio de exclusión de barra de escala y anotaciones.')
    parser.add_argument('--salida', type=Path, required=True)
    parser.add_argument('--polaridad', choices=('clara', 'oscura'), required=True)
    parser.add_argument('--um-por-px', type=float,
                        help='Solo una calibración verificada, nunca el aumento nominal.')
    parser.add_argument('--referencia-escala',
                        help='Patrón/configuración o procedencia de la calibración.')
    parser.add_argument('--min-distance', type=int, default=18)
    parser.add_argument('--area-minima', type=int, default=80)
    args = parser.parse_args()
    if bool(args.um_por_px is not None) != bool(args.referencia_escala):
        parser.error('Declare conjuntamente --um-por-px y --referencia-escala, o ninguna.')
    if args.salida.exists():
        parser.error('La carpeta de salida debe ser nueva.')
    s = Sesion('Prueba de procesamiento; interpretación pendiente de revisión')
    original = s.agregar(cargar_imagen(args.imagen), 'imagen', args.imagen.name, {
        'procedencia': str(args.imagen.resolve()),
        'sha256_original': sha256_archivo(args.imagen)})
    _, ids = s.ejecutar('extraer_roi', {'imagen': original},
                       dict(zip(('r0','r1','c0','c1'), args.roi)))
    recorte = ids['roi']
    s.confirmar_roi(recorte, args.nota_roi)
    if args.um_por_px is not None:
        s.establecer_escala(recorte, EscalaEspacial(
            args.um_por_px, referencia=args.referencia_escala))
    _, ids = s.ejecutar('convertir_grises', {'imagen': recorte})
    gris = ids['gris']
    s.ejecutar('histograma_percentiles', {'imagen': gris})
    s.ejecutar('detectar_canny', {'imagen': gris})
    _, ids = s.ejecutar('umbralizar', {'imagen': gris}, {'polaridad': args.polaridad})
    _, ids = s.ejecutar('separar_watershed', {'mascara': ids['otsu']}, {
        'min_distance': args.min_distance, 'area_minima': args.area_minima})
    # Esta rama calcula características, pero no declara que las instancias sean granos.
    if args.um_por_px is not None:
        s.ejecutar('descriptores_forma', {'etiquetas': ids['etiquetas']})
    s.guardar(args.salida)
    print('Sesión guardada:', args.salida)
    print('Revise máscara, marcadores y etiquetas. Los parámetros no están validados para su material.')
    if args.um_por_px is None:
        print('No se calcularon magnitudes físicas: no se declaró calibración.')


if __name__ == '__main__':
    main()
