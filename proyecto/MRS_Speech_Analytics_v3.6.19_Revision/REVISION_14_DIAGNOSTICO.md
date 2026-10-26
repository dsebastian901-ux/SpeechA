# Revisión 14 · recuperación de importes omitidos

Se conserva la revisión 13 y se añade una lectura focalizada para solicitudes
de pago cuyo importe fue omitido por Whisper. El lote recibido desde Windows
confirmó tres ejecuciones nuevas del modelo, aunque las transcripciones repetían
los textos anteriores. Un reanálisis de reglas no recupera palabras ausentes.

## Comportamiento

- Cuando una solicitud explícita como «le están pidiendo» o «le ofrecemos» no
  contiene un importe y tiene marcas temporales utilizables, se releen dos
  ventanas cortas del audio original con el mismo modelo. No se dan al modelo
  cantidades esperadas, números de Excel ni instrucciones de completar cifras.
- Se conserva el texto base. Las lecturas adicionales se guardan en
  `result.recuperacion_importes`, con ventanas, textos y coincidencias. Un importe
  solo se incorpora al análisis si las dos lecturas contienen una única cantidad
  monetaria coincidente y la evidencia corresponde al texto y ventana originales.
- Una lectura que falla, difiere o contiene varios importes deja el caso pendiente.
  La ausencia del audio no se resuelve inventando cantidades. Las cifras ya
  presentes, aunque ambiguas, no se reemplazan automáticamente.
- La recuperación no identifica hablantes ni valida autorización del descuento.
  Todo caso con evidencia de recuperación conserva el bloqueo de aprobación.
  Las reglas de saldo, parcialidades, privacidad y trato se mantienen.
- El JSON y el Excel separan el texto base de la evidencia recuperada. Se añaden
  dos columnas al final: Recuperación importe audio y Evidencia recuperación importe;
  se conserva el orden de las columnas anteriores.
- La transcripción de audio nuevo también ejecuta este control cuando detecta
  una oferta incompleta. Se registran las versiones de las bibliotecas de ASR
  y el tiempo adicional. No se cambian dependencias ni modelo configurado.

## Prueba real y regresión

En la llamada 23 del lote de tres, se conservaron el texto omitido y el audio
original y se ejecutó la recuperación real. Las dos ventanas produjeron la misma
cantidad, coincidente con la confirmación posterior del usuario. El informe pasó
de importe del descuento no confirmado a importe identificado con descuento no
verificable. El dictamen sigue REVISAR. Las llamadas 12 y 32 no se retranscribieron
y conservaron sus motivos de revisión por saldo y parcialidades contradictorias.

- 330 pruebas aprobadas y compilación de app y herramientas correcta.
- Regresión: 268 evaluaciones, 196 textos y 5 checkpoints. Se conservan
  259 REVISAR, 5 FALLA_GRAVE y 4 APROBADO; sin fallos de seguridad ni
  eliminaciones de penalización sin justificar.
- Reanálisis de reglas del lote de 36: 35 REVISAR y 1 APROBADO.
- Recuperación real del lote de tres: una oferta incompleta, un importe
  recuperado y tres REVISAR. No se fuerza una aprobación.
- Se conservan los datos y reportes reales fuera de Git. No se afirma que
  todas las cantidades sean correctas ni que los 13 problemas estén cerrados.
  Falta verificar esta herramienta nueva en Windows; la prueba real se hizo en
  Linux con el audio original y el checkpoint devuelto desde Windows.

## Aplicar al lote existente en Windows

1. Extraer el paquete completo y abrir la carpeta de la aplicación.
2. Ejecutar RECUPERAR_IMPORTES.bat.
3. Seleccionar el batch_checkpoint.json del lote de tres y la carpeta que contiene
   esos audios originales, normalmente la carpeta 01_Audios del proyecto.
4. La consola debe mostrar 3.6.19-r14, las cantidades recuperadas, el reporte y
   el checkpoint nuevos. Usar esos archivos dentro de la carpeta resultados.

Se conserva el checkpoint de entrada y no se copian audios. No hace falta volver
a procesar el lote entero ni instalar otro Whisper. Si no se encuentra el audio
o no hay coincidencia, el reporte lo deja pendiente. La herramienta detecta
formas explícitas de oferta sin importe; no resuelve todas las omisiones o
confusiones posibles del reconocimiento de voz.
