# Revisión 19 · incorporar confirmaciones en el lote completo

La muestra de tres llamadas quedó verificada en los archivos devueltos de r18.
El lote anterior de 36 todavía no contenía sus registros. Esta revisión añade
INCORPORAR_VALIDACIONES.bat para trasladar esos hechos en una copia del lote.

## Comportamiento

Se selecciona primero el checkpoint completo y después el checkpoint final ya
validado. Todas las llamadas de la muestra deben existir por nombre exacto en
el lote, con el mismo texto, segmentos, duración y tarjeta de 16 dígitos. Los
datos de cuenta también deben coincidir, salvo el nombre de salida corregido
con un registro explícito basado en numero_de_tarjeta.

Se comprueban las huellas y evidencias de las confirmaciones de importe y saldo
o acuerdo final. Una confirmación incompatible, una revocación que contradiga un
registro del lote o una evidencia de recuperación distinta detienen la operación.
La comprobación de todas las llamadas se completa antes de crear la salida.

Se conservan el orden y todas las llamadas del lote, sus textos, segmentos,
rutas originales y datos de cuenta. Solo se incorpora la evidencia adicional
necesaria y las confirmaciones existentes, sin crear nuevas afirmaciones de
escucha. Se recalculan las clasificaciones con los umbrales del lote completo.
Las aprobaciones almacenadas en la muestra no se usan como dictamen del lote.

La salida incluye huellas de ambos checkpoints y un registro por llamada de los
campos incorporados. Los originales permanecen intactos. Si se localiza el Excel
de cuentas, se genera una copia con los nombres de salida ya confirmados; si no,
el checkpoint y el reporte conservan la corrección y la nota aclara ese límite.
No se ejecuta Whisper ni se copian audios. Se mantiene la salida independiente
de r17 para evitar rutas anidadas y el resto de las reglas de r18.

## Comprobación

- 492 pruebas aprobadas y compilación correcta de app y tools.
- Regresión histórica de 268 evaluaciones: 262 REVISAR, 2 FALLA_GRAVE y 4 APROBADO;
  sin fallos de seguridad ni eliminaciones injustificadas de penalizaciones.
- Lote real de 36: 1 APROBADO y 35 REVISAR antes de incorporar la muestra;
  4 APROBADO y 32 REVISAR después. Solo cambiaron las llamadas 12, 23 y 32.
  Las otras 33 conservaron su clasificación calculada con el mismo motor.
- Se conservaron las 36 transcripciones, segmentos, rutas y tarjetas. En la copia
  del Excel solo cambió nombre_final de la fila cuyo identificador ya se había
  confirmado. Un reanálisis posterior conservó el resultado y las revisiones.
- Se inició Tk y se probó el flujo completo en Linux con datos sintéticos y
  selecciones de archivos simuladas. Falta verificar la herramienta nueva en Windows.

En los 32 pendientes hay 12 diferencias de nombres de salida, 12 revisiones de
privacidad, 8 discordancias de estatus y 3 revisiones financieras. Los grupos se
superponen y no explican por sí solos todos los motivos. Esas revisiones requieren
evaluación individual; no equivalen a errores técnicos ni a fallas graves confirmadas.

No se consideran cerrados los 13 problemas. El asistente no escuchó los audios;
las confirmaciones incorporadas proceden del usuario. Los datos reales y las
auditorías se conservan fuera de Git.

## Uso en Windows

1. Extraer el paquete y abrir proyecto\MRS_Speech_Analytics_v3.6.19_Revision.
2. Ejecutar INCORPORAR_VALIDACIONES.bat.
3. Seleccionar el checkpoint del lote completo de 36 llamadas.
4. Seleccionar el checkpoint final de tres llamadas ya validado en r18.
5. Usar el checkpoint y reporte de
   %USERPROFILE%\MRS_Resultados\Integracion_MRS_r19_...\resultados.

No hace falta repetir las confirmaciones ni transcribir nuevamente los audios.
