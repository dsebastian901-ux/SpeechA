# Revisión 12 · pagos reportados y recados

Conserva las correcciones de la revisión 11. Se contrastaron tres audios
originales adicionales con una nueva transcripción automatizada de Whisper
small, CPU int8, español, beam 5, VAD y tiempos por palabra. Los archivos
correspondían a las llamadas 17, 21 y 31 del checkpoint. Los audios pedidos
para las llamadas 12, 23 y 32 siguen pendientes; no se asume que un número
de fila de un Excel filtrado identifique el archivo.

## Correcciones verificadas

- Una petición de captura o comprobante de transferencia ya realizada no es
  una nueva instrucción bancaria. Se elimina esa revisión falsa cuando existe
  evidencia de pago reportado y no hay nueva instrucción, discusión futura ni
  datos de destino pendientes. Se mantienen las revisiones de una transferencia
  nueva y el bloqueo de cuentas no autorizadas, aunque haya un pago anterior.
- La autorización de una transferencia nueva se vincula a su instrucción; una
  cuenta mencionada en otro contexto no basta para autorizarla.
- La respuesta afirmativa a una pregunta de pago realizado reconoce un reporte
  de pago. Las variantes «puedo»/«pado» requieren además una pregunta posterior
  inequívoca sobre cuándo se hizo. Una negativa, respuesta incierta o propuesta
  futura no confirman pago realizado.
- Se extraen cantidades de declaraciones como «lo realicé» y respuestas de
  importe sin reutilizar como pago un saldo informado anteriormente. Un primer
  tramo sin importe no impide buscar la cantidad en la explicación posterior.
- Conocer al titular, ser familiar o contestar desde su trabajo no prueban que
  se dejó un mensaje. El estatus de recado exige evidencia de transmisión y
  recepción. Sin ella, se conserva el contacto con tercero y revisión.
- Una frase histórica/ambigua como «saldo pasado» no desplaza el saldo actual
  informado. Se añaden los términos «mentirosa/mentiroso» al control de trato:
  sin rol confirmado requieren revisión; atribuidos al gestor siguen el bloqueo
  de confrontación. No se inventa diarización a partir de SPEAKER_00/01.

## Resultados y límites

- 273 pruebas aprobadas y compilación correcta.
- Regresión de 268 evaluaciones: 259 REVISAR, 5 FALLA_GRAVE y 4 APROBADO;
  sin fallos de controles de seguridad ni eliminaciones de penalización sin
  justificar. Ocho casos adicionales se documentan con hash y condiciones
  explícitas de evidencia, sin aprobarlos automáticamente.
- Reanálisis del lote de 36 con sus textos guardados: 1 APROBADO y 35 REVISAR.
  Las correcciones cambian motivos y penalizaciones; no fuerzan aprobaciones.
- En la nueva transcripción de la llamada 17 se reconoce el reporte de pago
  y se elimina la falsa exigencia de datos para una transferencia nueva. Sigue
  pendiente la discrepancia entre el estatus Excel y el pago reportado.
- En la 21 se reconoce un pago reportado inferior al mínimo registrado. Se
  conserva la revisión de gestión del restante y de la diferencia del saldo.
- En la 31 se identifica un tercero, sin presumir recado aceptado ni negativa
  explícita a recibirlo. La posible divulgación conserva revisión de hablantes.

La retranscripción automatizada no certifica voces, tono ni todos los datos
del audio. Los archivos originales, las nuevas transcripciones y las auditorías
permanecen fuera de Git. Los 13 problemas no se consideran cerrados. La operación
completa en Windows sigue pendiente de validación; se conserva Python 3.10 y
la instalación existente de Whisper.

## Identificar y probar esta revisión

Ejecute REANALIZAR_CHECKPOINT.bat en la carpeta de esta versión y seleccione el
checkpoint original o el resultado de la revisión anterior. La consola muestra
«Revisión del motor: 3.6.19-r12». El JSON nuevo incluye reanalysis.engine_revision
y el Excel muestra la versión en NOTA_REANALISIS. La carpeta automática empieza
con Reanalisis_MRS_r12_. Se conservan los archivos de entrada y no se ejecuta
Whisper para este reanálisis de reglas.
