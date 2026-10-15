# Fuentes técnicas para mantener el software

Estas páginas se consultaron para comprobar interfaces, versiones y empaquetado. Son documentación técnica del repositorio; no se añaden silenciosamente a la bibliografía del manuscrito. Las referencias metodológicas del proyecto están en `referencias_libro.bib` y conservan su estado de verificación pendiente.

| Fuente primaria | Aspecto consultado |
|---|---|
| https://scikit-image.org/docs/0.26.x/api/skimage.morphology.html | Semántica inclusiva de `max_size`, conectividad, morfología |
| https://scikit-image.org/docs/0.26.x/api/skimage.segmentation.html | Watershed y contornos de etiquetas |
| https://scikit-image.org/docs/0.26.x/api/skimage.measure.html | Propiedades geométricas y convenciones de orientación/perímetro |
| https://doc.qt.io/qtforpython-6/ | PySide6 y componentes de interfaz |
| https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html | Hilos y señales de finalización |
| https://pypi.org/pypi/PySide6/6.10.2/json | Existencia y requisitos de la versión seleccionada; no prueba local |
| https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ | Metadatos de paquete, dependencias y extras |
| https://docs.python.org/3/library/venv.html | Entornos virtuales y uso directo de su intérprete |
| https://github.com/actions/checkout | Acción de obtención del código en CI |
| https://github.com/actions/setup-python | Configuración de intérprete para CI |

Consulta técnica realizada para esta entrega: 13 de octubre de 2026. La configuración de CI se entrega para su ejecución futura en el repositorio del autor; no hay un resultado de GitHub Actions asociado a este paquete.
