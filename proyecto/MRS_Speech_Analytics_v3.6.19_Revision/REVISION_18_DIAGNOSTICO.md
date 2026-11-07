# Revisión 18 · saldo y acuerdo final confirmados

La herramienta VALIDAR_IMPORTES.bat incorpora dos confirmaciones financieras:
saldo informado corregido por una persona y acuerdo final de parcialidades.
Se conservan las reglas operativas y el guardado en carpetas independientes
de la revisión 17.

## Comportamiento

- El saldo se registra mediante una casilla y un campo vacío. El programa no
  lo completa con el saldo esperado del Excel ni modifica la transcripción.
- Cuando hay importes distintos para una parcialidad, una casilla permite
  confirmar expresamente el último plan explícito que quedó acordado. Las
  cantidades y propuestas anteriores permanecen en la auditoría.
- Los registros incluyen fecha, alcance, huella de llamada/texto/segmentos y
  evidencia de recuperación. También deben coincidir con el saldo y el plan
  extraídos de la evidencia actual. Una revisión desactualizada bloquea la
  aprobación hasta revisarla o revocarla.
- Solo se resuelve el dato confirmado. Se recalculan los controles de mínimo,
  saldo de Excel, fechas, corte, vencimiento, privacidad, tarjeta y calidad.
  No se modifican puntajes ni umbrales mínimos.
- No confirmar otra vez una llamada conserva su registro anterior. La opción
  Revocar vuelve a evaluar la lectura ASR y conserva el registro previo en un
  historial. La revocación también se conserva al reanalizar.
- El Excel conserva sus 82 columnas anteriores y agrega cinco para las
  confirmaciones financieras y el historial de propuestas. No se reescriben los
  originales ni los datos de cuentas.

## Evidencia

- 467 pruebas aprobadas y compilación correcta de app y tools.
- Regresión de 268 evaluaciones históricas: 262 REVISAR, 2 FALLA_GRAVE y
  4 APROBADO; sin fallos de seguridad ni eliminaciones injustificadas de
  penalizaciones. El lote anterior de 36 conserva 1 APROBADO y 35 REVISAR.
  Esos archivos históricos no incluyen las dos confirmaciones nuevas.
- Las confirmaciones del usuario resuelven las dos discrepancias pendientes
  del checkpoint de tres llamadas: saldo informado y segunda parcialidad final.
  Resultado: 3 APROBADO, conservando los puntajes 100, 80 y 90. La confirmación
  anterior de importe recuperado y la corrección del nombre se conservaron.
- Un segundo reanálisis conservó las tres dictaminaciones y los registros.
  Textos, segmentos, evidencia ASR y datos de cuentas originales permanecieron
  sin cambios. No se ejecutó Whisper.
- Se probó la interfaz real en Linux con datos sintéticos: casillas desmarcadas,
  campo vacío, registro de saldo y plan, reporte y revocación. Falta verificar los
  controles nuevos en Windows. El usuario ya verificó el guardado de r17.

El asistente no escuchó las llamadas. Los hechos humanos proceden de las
confirmaciones explícitas del usuario. Los archivos reales y sus revisiones se
conservan fuera de Git. Estas tres dictaminaciones no cierran los 13 problemas.

## Uso con el checkpoint recibido

1. Extraer esta entrega y abrir proyecto\MRS_Speech_Analytics_v3.6.19_Revision.
2. Ejecutar VALIDAR_IMPORTES.bat y seleccionar el checkpoint final de r17.
3. Registrar el saldo ya confirmado en el campo correspondiente y marcar el
   acuerdo final de parcialidades ya confirmado. Las confirmaciones anteriores
   se conservan aunque no se marquen otra vez.
4. Guardar en copia y usar los archivos de
   %USERPROFILE%\MRS_Resultados\Validacion_MRS_r18_...\resultados.

No hace falta retranscribir ni instalar otro Whisper.
