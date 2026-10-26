# Revisión 17 · guardado de resultados en rutas independientes

La captura de Windows muestra que las dos casillas sí estaban marcadas. El error
ocurría al guardar Reporte_Reanalisis_Reglas_nuevo.xlsx dentro de recuperaciones,
reanálisis y validaciones sucesivos. La revisión 16 añadía cada carpeta al origen,
haciendo crecer la ruta hasta superar el límite habitual de Windows.

## Cambio

VALIDAR_IMPORTES.bat, RECUPERAR_IMPORTES.bat y REANALIZAR_CHECKPOINT.bat crean cada
salida en una carpeta nueva bajo %USERPROFILE%\MRS_Resultados. La ubicación del
checkpoint de entrada ya no determina dónde se añade la siguiente salida.
La interfaz de validación muestra la carpeta base antes de guardar.

Se comprueban las rutas previstas antes de crear archivos en Windows, incluida
la copia temporal del reporte. Se usa un margen de 240 unidades UTF-16 sin
depender de activar rutas largas en el sistema. Una salida explícita demasiado
larga se rechaza con una indicación para elegir otra carpeta con --output-dir.
Las carpetas con archivos existentes se rechazan para conservar resultados.

Se mantienen los registros de confirmación y sus huellas, las reglas por mora,
la excepción de dos exhibiciones y el cotejo contra numero_de_tarjeta del Excel.
Los documentos de revisiones anteriores se conservan como historial.

## Comprobación

- 436 pruebas aprobadas y compilación de app y tools correcta. Se ejercitaron
  dos ejecuciones sucesivas de cada herramienta con un checkpoint en una ruta
  de más de 260 caracteres, simulando la comprobación del límite de Windows.
- Regresión histórica de 268 evaluaciones: 262 REVISAR, 2 FALLA_GRAVE y 4 APROBADO;
  sin fallos de seguridad ni eliminaciones injustificadas de penalizaciones.
  Los análisis coinciden con r16 salvo el identificador de revisión. El lote
  anterior de 36 conserva 1 APROBADO y 35 REVISAR, sin cambiar sus transcripciones.
- Con los tres registros recibidos y las confirmaciones expresas del usuario
  ya dadas en la conversación, se generaron checkpoint y reporte desde una ruta
  de entrada de 310 caracteres. El reporte resultante quedó en una ruta de 146.
  Resultado: 1 APROBADO y 2 REVISAR. La confirmación sobrevivió al reanálisis.
- En la copia del Excel de cuentas solo cambió nombre_final de la fila confirmada.
  Se conservaron originales, textos, tarjeta de origen, saldos y mínimos.

No se ejecutó Whisper para registrar las confirmaciones. El asistente no escuchó
el audio: los hechos confirmados proceden del usuario. Estas comprobaciones se
ejecutaron en Linux; falta verificar el guardado de esta revisión en Windows.
La corrección del guardado no cierra los 13 problemas de clasificación.

## Uso en Windows

1. Extraer el paquete completo en una carpeta nueva y abrir la aplicación dentro
   de proyecto\MRS_Speech_Analytics_v3.6.19_Revision.
2. Ejecutar VALIDAR_IMPORTES.bat y seleccionar el checkpoint final recuperado.
3. Marcar las dos confirmaciones ya comprobadas y guardar en copia.
4. Buscar la salida en %USERPROFILE%\MRS_Resultados\Validacion_MRS_r17_...\resultados.
   El reporte está dentro de 04_Reportes; el checkpoint está en resultados.

No hace falta repetir RECUPERAR_IMPORTES ni instalar otro Whisper para este paso.
