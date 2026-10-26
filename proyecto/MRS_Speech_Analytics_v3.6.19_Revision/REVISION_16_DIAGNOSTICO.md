# Revisión 16 · confirmaciones humanas y nombres de salida

Conserva las reglas del manual y las aclaraciones del usuario incorporadas en
la revisión 15, incluida la segunda exhibición hasta siete días desde el primer
pago. Añade el registro de confirmación de importes recuperados y un control
independiente de datos de salida.

## Confirmación con alcance limitado

- VALIDAR_IMPORTES.bat abre el checkpoint final y muestra las lecturas recuperadas.
  Las casillas comienzan desmarcadas. Cada confirmación se refiere a una ventana
  de una llamada, no al resto del lote.
- Se guarda una revisión separada, con huella del nombre de llamada, texto,
  segmentos y evidencia de recuperación. Cambios en esos datos invalidan la
  confirmación. Una ventana fallida o sin coincidencia no queda validada por
  confirmar otro importe.
- La revisión del importe solo resuelve ese control de evidencia. No exonera
  divulgación, referencia discordante, trato, fechas, negociación ni puntaje mínimo.
  No certifica voces ni equivale a aprobación completa de la llamada.
- Un reanálisis posterior conserva la confirmación válida sin ejecutar Whisper.
  La transcripción original y el indicador de la lectura ASR permanecen intactos;
  la confirmación humana se registra en otro campo.
- En análisis individual, Validar importe guarda una revisión separada al JSON.
  Se puede revocar guardando las casillas desmarcadas. Se conserva el contexto
  operativo del análisis y se respeta el puntaje mínimo configurado.

## Referencia y datos de salida

La referencia dictada y la tarjeta mencionada en audio se comparan únicamente
con numero_de_tarjeta del Excel. El identificador incluido en nombre_final no
sustituye a ese dato de origen.

Si nombre_final contiene una tarjeta distinta, se muestra como inconsistencia
de datos de salida, sin PEN003 ni penalización de audio. Antes de renombrar como
aprobado requiere corregir el identificador o resolver esa inconsistencia.
Una casilla separada permite usar numero_de_tarjeta para corregir únicamente
el prefijo del nombre, conservando el resto del nombre y la tarjeta de origen.
No se modifican saldos ni mínimos.

El checkpoint conserva el nombre anterior y la corrección. Si el Excel original
está en la ruta registrada o se selecciona, se genera una copia con las filas
confirmadas corregidas. Si no se localiza, los cambios quedan en el checkpoint
y el reporte lo aclara; el original no se sobrescribe.

## Evidencia y límites

- 429 pruebas aprobadas y compilación correcta.
- Regresión de 268 evaluaciones: 262 REVISAR, 2 FALLA_GRAVE y 4 APROBADO;
  sin fallos de seguridad ni eliminaciones de penalización sin justificar.
- Con el lote de tres y las dos confirmaciones explícitas del usuario para la
  llamada 23 —importe oído y tarjeta de origen— el resultado es 1 APROBADO y
  2 REVISAR. Las llamadas 12 y 32 conservan revisión por saldo y parcialidades.
- En la copia del Excel de cuentas solo cambió nombre_final de la fila confirmada.
  La tarjeta, los importes y los demás registros se conservaron.
- La confirmación y el resultado se conservaron en un reanálisis adicional.
- Se abrieron las interfaces de importe y lote en Linux: controles inicialmente
  desmarcados, guardado, revocación y generación de reporte comprobados con datos
  sintéticos. Falta verificar estas interfaces nuevas en Windows.

El asistente no escuchó el audio: las confirmaciones humanas utilizadas proceden
del usuario. Audios, transcripciones, registros de revisión, Excel y reportes
reales permanecen privados. No se consideran cerrados los 13 problemas.

## Aplicar esta entrega en Windows

1. Extraer el paquete completo y ejecutar VALIDAR_IMPORTES.bat.
2. Seleccionar el checkpoint final de la revisión anterior.
3. Marcar el importe ya comprobado en audio. Para la cuenta cuyo nombre difiere,
   marcar por separado la corrección con numero_de_tarjeta, si se ha confirmado.
4. Guardar en copia y generar reporte. Usar el checkpoint y Excel nuevos que
   muestra la consola. La revisión del motor debe ser 3.6.19-r16.

No hace falta repetir la transcripción ni instalar otro Whisper. Las reglas
del mínimo por mora, mes de liquidación y vencimiento se conservan.
