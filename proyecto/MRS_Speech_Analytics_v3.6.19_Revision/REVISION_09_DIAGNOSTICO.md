# Revisión 09 · diagnóstico y correcciones, validación pendiente

La revisión 08 fue demasiado restrictiva para conversaciones naturales. Se
reprodujeron exactamente las puntuaciones, penalizaciones y clasificaciones de
las 36 evaluaciones del checkpoint informado por el usuario. El lote original
terminó sin excepciones técnicas: 32 REVISAR y 4 FALLA_GRAVE.

## Fallos reproducidos y corregidos

- Identificación: respuestas a preguntas dirigidas al titular, como «ella habla»,
  «sí, dígame» o «así es», no se reconocían. Ahora se registra esa evidencia sin
  copiar la identidad del Excel ni asignar una voz a SPEAKER_00/01. Una respuesta
  conocida del gestor o una contradicción posterior no confirma titular.
- Silencio: las llamadas 15 y 29 se invalidaban como abandono del gestor solo
  por un silencio final. Ese dato requiere revisión del audio y no prueba quién
  dejó de responder. Se conserva el bloqueo de revisión.
- Datos bancarios: en la llamada 26, números globales de tarjeta/referencia se
  vinculaban a bancos mencionados en otro contexto. El dato incorrecto debe
  estar ligado localmente a una instrucción de pago a una cuenta o CLABE.
- Liquidación: «no puede liquidar» activaba una oferta prohibida en la llamada 33.
  Una negación no constituye oferta de liquidación.
- Conversaciones: una propuesta de pago no es aceptación; una pregunta sobre un
  pago anterior no demuestra que se realizó. Se distingue pago reportado,
  compromiso aceptado, rechazo y respuesta condicional.
- Lugares: los fragmentos acústicos de Whisper no son límites de oraciones. Se
  reúnen las frases para reconocer ofertas que cruzan fragmentos. Se reconocen
  «pagarlo» y la escritura 7-11. SMR requiere contexto de presentación del despacho.
- Reporte: se eliminan repeticiones exactas de motivos, conservando cada bloqueo.

## Resultado y límites

- 181 pruebas unitarias y de integración aprobadas.
- Regresión histórica de 268 evaluaciones: 258 REVISAR, 6 FALLA_GRAVE, 4 APROBADO;
  sin aprobaciones adicionales. Los cambios de penalización esperados incluyen
  condiciones de evidencia y hash del checkpoint en la regresión reproducible.
- Nuevo lote de 36: 36 REVISAR, 0 FALLA_GRAVE, 0 aprobaciones. Se identifican
  19 titulares, 1 tercero y 16 contactos sin confirmar en las transcripciones.
- Esto NO cierra los 13 problemas ni valida los 36 dictámenes. Persisten casos
  sin identidad o estatus confirmados, desacuerdos entre Excel y pagos ya
  reportados, y propuestas/condicionales que requieren revisión humana.
- No se incluyeron los audios originales: faltan atribución de voces y contraste
  acústico. Tampoco se ha validado esta revisión en Windows.

## Reanalizar el checkpoint sin ejecutar Whisper

1. En la carpeta de la aplicación, ejecute REANALIZAR_CHECKPOINT.bat.
2. Seleccione una copia de batch_checkpoint.json.
3. Se crea una carpeta Reanalisis_MRS_ junto al archivo seleccionado, con
   checkpoint_reanalizado.json y 04_Reportes/Reporte_Reanalisis_Reglas.xlsx.

Se usa el Python existente; no hay cambio de versión ni un nuevo Whisper.
Se conservan los archivos originales y no se copian ni mueven audios. La hoja
NOTA_REANALISIS aclara que «Clasificación física» representa el cálculo nuevo,
no una copia o movimiento efectuado sobre los archivos.

También puede ejecutarse desde consola:

    python tools/reanalyze_checkpoint.py --checkpoint "ruta/batch_checkpoint.json"

Los checkpoints y reportes reales permanecen fuera del repositorio.
