# Revisión 37: conservar y recuperar transcripciones ante errores de análisis

Base: r36, commit 4837ac2b2fbe0bc87b02a573416a8c2bd2e20d8a.

## Cambio

Un error posterior a Whisper borraba `result` del checkpoint. Ahora el lote guarda
el JSON completo de transcripción antes de analizarlo. Si falla el procesamiento,
conserva esa evidencia y registra ERROR, sin puntuación ni aprobación anterior.

El reanálisis recupera los JSON faltantes del directorio de transcripciones del
checkpoint. Exige nombre de archivo exacto, extensión y texto; si se conocen
ambas rutas de audio, también deben coincidir. Guarda ruta y SHA-256 de la
recuperación. No sustituye las transcripciones ya incorporadas, no ejecuta
Whisper y no modifica los archivos originales. Un JSON ausente, distinto o
inválido conserva el caso en ERROR.

El antiguo error `payment_date_confirmed` no aparece como variable suelta en
r36: el campo utiliza `confirms_payment_date`. No se añadió un valor artificial
ni se relajaron reglas de fechas para ocultar ese error histórico.

## Resultados comprobados con los archivos locales

- Lote grande: 1.007 llamadas. Se recuperaron las 55 transcripciones ausentes;
  las 55 quedan en REVISAR. Resultado: 25 APROBADO, 962 REVISAR, 20 FALLA_GRAVE,
  cero errores de ejecución.
- Comparación contra r36 sobre las 952 llamadas analizables: ninguna diferencia
  de clasificación, puntuación o penalizaciones. El volumen alto de revisiones
  ya existía en r36 y no queda resuelto por esta revisión.
- Lote de 103: se registró, por archivo y contexto, la aclaración ya realizada
  por el usuario para la llamada 67: número para negociar el restante.
  Resultado: 21 APROBADO, 73 REVISAR, 9 FALLA_GRAVE. Se conservan las demás
  confirmaciones; no trasladar estos hechos al lote grande.
- Excel y checkpoint coinciden en archivo, puntuación y clasificación para
  las 1.110 filas de resultados. Las 952 transcripciones preexistentes y las
  1.007 relaciones de cuentas del lote grande permanecen idénticas.

## Uso

Extraer el paquete completo en una carpeta nueva y usar el Python existente
del programa. Ejecutar `REANALIZAR_CHECKPOINT.bat` y seleccionar el checkpoint
original. Mantener disponible su directorio de transcripciones para recuperar
las llamadas antiguas sin `result`. No hace falta reinstalar Whisper.

Los resultados privados se entregan por separado del código. No están en el
ZIP de la aplicación ni deben publicarse en GitHub.

## Límites

Esta revisión corrige recuperación y conservación de evidencia, no cierra los
13 problemas operativos. Los 962 REVISAR no equivalen a 962 incumplimientos.
Predominan estatus e identidad sin confirmar; requieren contrastar evidencia.
No se escucharon ni retranscribieron audios durante esta revisión.

Consultar VALIDACION_R37.json del paquete para los resultados exactos de pruebas
y las limitaciones del entorno de validación.
