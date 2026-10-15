"""Datos de visualización sin dependencia de Qt; no modifica datos de medición."""
from __future__ import annotations
import numpy as np
from skimage import measure, segmentation
from .imagen import convertir_grises


def preparar_vista(artefacto, sesion, superponer=False, rotular=False) -> dict:
    """Prepara base, contornos y rótulos; los identificadores no se renumeran."""
    a = artefacto.datos
    vista = {'imagen':a,'tipo':artefacto.tipo,'contornos':None,'rotulos':[],
             'nota':'Vista; los valores originales permanecen en el dato.'}
    if a.ndim == 1:
        return vista
    if rotular and artefacto.tipo in ('etiquetas','marcadores'):
        # Solo posición visual. Las medidas exportables provienen de medicion.py.
        ids = np.unique(a[a > 0])
        compacta = np.where(a > 0, np.searchsorted(ids,a) + 1, 0).astype(np.int32)
        for r in measure.regionprops(compacta):
            vista['rotulos'].append((r.centroid[1],r.centroid[0],str(ids[r.label-1])))
        if len(vista['rotulos'])>1000:
            vista['rotulos'] = []
            vista['nota'] += ' Más de 1000 rótulos: desactivados para conservar legibilidad.'
    if superponer and artefacto.tipo in ('etiquetas','mascara','limites','clases','marcadores'):
        raiz = sesion.artefactos.get(artefacto.metadatos.get('raiz'))
        if raiz and raiz.tipo in ('imagen','gris') and not artefacto.metadatos.get('muestreo_modificado'):
            rr,cc = artefacto.metadatos.get('origen_rc',[0,0])
            base = raiz.datos[rr:rr+a.shape[0],cc:cc+a.shape[1]]
            if base.shape[:2] == a.shape:
                vista['imagen'] = convertir_grises(base).datos['gris']
                vista['tipo'] = 'gris'
                vista['contornos'] = (a.astype(bool) if artefacto.tipo == 'limites' else
                    segmentation.find_boundaries(a.astype(np.int32),mode='thick'))
                vista['nota'] = 'Contornos de la salida sobre la imagen fuente; no es una nueva segmentación.'
        else:
            vista['nota'] = 'No hay imagen fuente compatible para la superposición; se muestra el dato.'
    return vista
