# Revisión 34: contenido del recado de retorno

## Fallo reproducido

El usuario confirmó que en la llamada 57 la hermana acepta el recado y toma
el número. R33 conserva correctamente esa aceptación, pero sigue en revisión
porque no reconoce como mensaje la instrucción «a ese número que se comunique
con nosotros». El contenido existe en el texto original y la lectura adicional;
no se agrega o corrige ASR para obtenerlo.

## Corrección limitada

La instrucción de retorno acredita contenido del mensaje solo cuando hay una
aceptación humana válida, separada y vinculada a esta llamada. Se exige dictado
numérico cercano y se excluyen intervenciones conocidas del titular, tercero
o interlocutor. También se excluyen preguntas, citas, negaciones e hipótesis.
La instrucción por sí sola no acredita aceptación ni parentesco.

Se conservan el texto, los segmentos, las repeticiones y los registros humanos.
El dictado no se transforma en una referencia de tarjeta ni se reconstruyen
dígitos faltantes. Detectar los fragmentos numéricos cercanos no certifica cuál
es el teléfono correcto. El rechazo del recado y los demás controles de calidad
y seguridad continúan bloqueando aprobación cuando corresponde.

## Resultado

La copia de trabajo ya incluye las aceptaciones de 4 y 96, y las aclaraciones
de que 29 y 39 no dejaron recado. Con la confirmación de la 57:

- **20 APROBADO, 74 REVISAR y 9 FALLA_GRAVE**, de 103 llamadas.
- Solo la 57 pasa de REVISAR a APROBADO; conserva 100 puntos.
- Los 103 puntajes, penalizaciones, datos originales, quince lecturas y todas
  las confirmaciones anteriores se conservan.
- Las llamadas 29 y 39 mantienen REVISAR por dictamen/recado, no aprobación.

## Validación y límites

La suite incorpora pruebas de contenido y recepción por separado, ausencia de
dictado, roles del dictado y del mensaje, negaciones, citas e hipótesis; también
verifica que no se eximan privacidad, amenazas, groserías, maltrato, tarjeta
incorrecta, rechazo o parentesco faltante. Resultado: **1.313 pruebas aprobadas**,
31 nuevas, y **268 evaluaciones históricas** contra r33 sin cambios de categoría,
retiros de penalizaciones ni fallos de seguridad. Se verificaron las 9.785 celdas
del Excel de resultados, sin diferencias respecto al checkpoint corregido.

La confirmación de aceptación procede del usuario; no se afirma escucha del
audio por el asistente ni diarización completa. La prueba nativa de r34 en
Windows sigue pendiente. Los 13 problemas operativos continúan sujetos a
validación por casos y no se declaran cerrados.

## Continuación local

Use el checkpoint final más reciente, con todas las confirmaciones anteriores.
Para guardar una recepción ya comprobada, `CONFIRMAR_ACEPTACION_RECADO.bat`.
Si la recepción ya está guardada, `REANALIZAR_CHECKPOINT.bat` de esta revisión.
No se ejecuta Whisper ni se necesita otro modelo; se generan otro checkpoint
y Excel sin sobrescribir los originales. Las cifras locales dependen de las
confirmaciones presentes en la base seleccionada.
