# Contratos y límites de interpretación

## Alcance

MicroGrano analiza imágenes bidimensionales y datos numéricos de campos. No controla instrumentos, prepara probetas, evalúa enfoque ni estima rugosidad. No identifica materiales, fases, maclas o artefactos de preparación a partir de una intensidad. No hay modelos de aprendizaje entrenados incluidos. El programa no convierte las salidas al número ASTM G ni certifica cumplimiento normativo.

La demostración sintética comprueba las operaciones del software. La validez de límites de grano, conteos y características requiere imágenes documentadas, un mensurando definido y una referencia de evaluación independiente. No se transfiere un resultado de estas pruebas al libro sin aprobación del autor.

## Representaciones

Las imágenes de entrada pueden ser matrices de intensidad o RGB/RGBA de un solo plano. Un canal alfa no opaco se rechaza para evitar una composición no declarada. Los enteros sin signo se convierten según su intervalo de almacenamiento; no se deduce de un uint16 que la cámara haya usado efectivamente 12 bits. Los flotantes deben estar en [0,1]. No se aceptan NaN o infinitos como intensidades.

`mascara` y `limites` son booleanos. `etiquetas`, `marcadores` y `clases` contienen identificadores enteros no negativos. Las etiquetas de objetos son instancias, con cero como fondo; se verifica que un identificador no reúna regiones desconectadas. Los identificadores dispersos se compactan solo internamente cuando una operación lo requiere y se conservan en las tablas. Las clases no se tratan como objetos: una clase puede ocupar regiones desconectadas y la clase cero es válida.

Los mapas de respuesta firmados, distancias y distribuciones tienen tipos separados; no se convierten implícitamente en imágenes normalizadas o en nuevas observaciones estadísticas. Es necesario elegir una operación compatible. Las funciones internas de validación no corresponden a experimentos adicionales y no tienen botones independientes.

## Geometría y calibración

Las coordenadas son (fila, columna), con origen superior izquierdo y filas crecientes hacia abajo. Un recorte utiliza límites finales excluidos. La calibración implementada es isotrópica: un único factor s en µm/px. No se aceptan escalas anisotrópicas como si fueran isotrópicas. Una imagen con tamaños de píxel distintos por eje requiere otro modelo de medida, no introducir un promedio sin justificarlo.

La incertidumbre de calibración usa propagación de primer orden para referencias independientes. Las conversiones muestran únicamente el componente procedente de la escala; no incluyen incertidumbre de segmentación, calibración correlacionada, preparación ni muestreo. La ausencia de una incertidumbre declarada se conserva como desconocida, no como cero.

Toda ROI y su exclusión de anotaciones deben revisarse explícitamente en una sesión. Las funciones NumPy llamadas directamente no conocen la barra de escala de un archivo: el usuario debe entregarles un arreglo adecuado. Las escalas no pasan a nuevas imágenes por persistencia de una configuración de interfaz.

## Parámetros y operaciones

Los parámetros predeterminados son valores iniciales de software. No constituyen una recomendación científica para todas las micrografías. El umbral mínimo de objeto es inclusivo: se conserva área >= area_minima. En scikit-image 0.26 se usa `max_size=area_minima-1`. La conectividad se declara y se conserva en las decisiones de análisis. Los huecos solo se rellenan si son cerrados y cumplen el tamaño máximo; el exterior no se rellena como si fuera un hueco.

La corrección divisiva protege su denominador, pero no determina por sí misma si la imagen obedece un modelo aditivo o multiplicativo. Las correcciones de fondo incluyen reescalado declarado. La elección de polaridad y el significado de las zonas claras u oscuras requieren revisión.

Watershed utiliza la máscara entregada, sin esconder una umbralización adicional. Los picos reciben identificadores distintos; si una componente no tiene un pico, se añade una semilla en su máximo y se informa. Un marcador válido por componente evita objetos perdidos por ausencia de semillas, pero no demuestra separación correcta de granos. No se aplica una reparación manual ficticia de límites ausentes.

## Magnitudes

La fracción de área conserva como denominador el dominio explícito de la ROI. Las fracciones de píxeles segmentados no equivalen automáticamente a fracciones volumétricas. El diámetro equivalente es un resumen del área, no una afirmación de forma circular. Se declaran los perímetros de contorno y Crofton; la circularidad digital no se fuerza artificialmente al intervalo [0,1]. Las magnitudes indefinidas quedan como NaN y se explican.

`medir_objetos` conserva la tabla de candidatos, aceptación y causa de exclusión. Devuelve fracciones antes y después del filtro por separado. La densidad de objetos aceptados en el área observada es descriptiva y depende de la regla del marco. `densidad_jeffries` aplica una ponderación ilustrativa de 0.5 a cada objeto del marco, incluidas esquinas; no sustituye geometría, reglas especiales y demás condiciones del procedimiento normativo.

La intercepción cuenta corridas de píxeles de límites sobre líneas horizontales/verticales. La longitud de prueba se mide entre centros extremos: (N-1)*s. Se informan orientación, longitud y conteos, con decisión explícita sobre extremos. Las corridas son intersecciones candidatas: tangencias, uniones y límites gruesos requieren inspección. Si no hay intersecciones, la media es indefinida, no cero.

Los intervalos bootstrap son percentiles de medias remuestreadas con semilla declarada. Requieren al menos dos valores finitos y una unidad de análisis defendible. La dispersión entre campos no es un presupuesto completo de incertidumbre. La identidad de una muestra y la independencia experimental no se deducen del formato CSV.

## Archivos, reproducción y recursos

Las fuentes y salidas se conservan en NPY sin pickle. CSV representa tablas y JSON registra contexto. SHA-256 detecta cambios de los arreglos al abrir una sesión; no es una firma del autor ni acredita la autenticidad científica. Los valores no finitos del JSON se escriben como cadenas explícitas para mantener JSON estricto.

La sesión es local, autocontenida y se guarda en una carpeta nueva. Se limita a 2 GB para apertura y escritura; el número de ramas y copias de imágenes puede consumir memoria antes de alcanzar ese límite. Una imagen grande con un radio grande de bola rodante puede tardar. No se declara rendimiento en equipos no probados.

La reproducción compara arreglos, tablas y resúmenes en el entorno instalado. Los parámetros y versiones quedan registrados; un cambio de dependencias puede modificar resultados. El archivo constraints fija las versiones seleccionadas, mientras el informe de verificación identifica las realmente ejecutadas. La GUI en PySide6 y las plataformas de escritorio no se considerarán probadas por el solo hecho de compilar sintácticamente sus fuentes.
