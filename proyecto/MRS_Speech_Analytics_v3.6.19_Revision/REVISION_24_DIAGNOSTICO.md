# Revisión 24: incorporar las lecturas recibidas sin perder correcciones

Se recibieron los resultados de la herramienta r23 ejecutada en Windows: diez
lecturas completas, cero errores de ejecución, modelo small/CPU/int8 y lectura
separada del cierre sin VAD. El Excel coincide con el JSON. Son hipótesis ASR:
no acreditan escucha humana ni identificación del hablante.

Las lecturas corresponden a las llamadas 2, 3, 4, 5, 6, 7, 8, 9, 11 y 12 del
lote de 95. Se comprobaron nombres, hashes de los audios, duraciones y evidencia
original. La herramienta se ejecutó sobre un checkpoint anterior; sus textos,
segmentos, duración y datos de cuenta coinciden con el lote actual. Se incorpora
únicamente la evidencia nueva; no se importan sus etiquetas ni nombres antiguos.
Los datos reales permanecen fuera de Git.

## Correcciones

- La lectura adicional se guarda separada, vinculada a texto, segmentos,
  duración y cuenta. Un cambio incompatible exige revisión. Un hash del registro
  permite detectar cambios posteriores; no equivale a firma ni certificación.
  Se conservan las transcripciones, tarjetas, importes y acuerdos confirmados,
  y las correcciones anteriores de nombres de salida.
- Se detectan repeticiones y alineaciones degradadas usando duración de palabras,
  densidad, repetición y compresión. En los resultados recibidos afectan partes
  de las llamadas 4 y 12 y la lectura del cierre de la 11. No se interpretan
  como negativa real del cliente ni como infracción. La compresión alta por sí
  sola no basta para descartar una frase. El texto bruto permanece disponible.
- Las señales nuevas de privacidad, referencia discordante, amenazas, trato o
  acuerdo inválido requieren revisión sin atribuirlas al gestor. No se importan
  puntajes ni omisiones de una lectura parcial. Una advertencia técnica aislada
  no retira una aprobación sustentada por la evidencia original. Una lectura
  degradada del cierre tampoco borra una expresión de la lectura completa.
- El correo ARCO dictado se reconoce cuando constan privacidad, arroba y el
  dominio literal autorizado. Se reconoce el número uno cuando está dictado;
  no se reconstruye un dominio dudoso. La llamada 12 conserva privacidad
  pendiente aunque ya se reconozca el correo. Se detecta también «mensalidad»
  como variante ASR de mensualidad en evidencia financiera.
- Seleccionar el JSON de lecturas en REANALIZAR_CHECKPOINT produce una indicación
  clara antes de crear salidas; ya no se trata como un lote de llamadas fallidas.
- El reporte principal conserva las primeras 87 columnas y añade tres:
  Lectura adicional audio, Alertas lectura ASR y Riesgos lectura adicional.

## Resultado y pendientes

El lote completo conserva **12 APROBADO, 81 REVISAR y 2 FALLA_GRAVE**, sin errores
técnicos de reanálisis. En los diez recibidos hay 1 APROBADO y 9 REVISAR.
No se crean aprobaciones por coincidencia entre dos lecturas automáticas.

El usuario indicó que no ha escuchado los tres puntos consultados. Por ello
permanecen sin confirmar el hablante de «qué poca madre» en la llamada 6, la
expresión y su hablante al final de la 11 y la aceptación del recado en la 7.
En esta última, las lecturas discrepan en la negación: no se elige una por
conveniencia ni se infiere parentesco. Estos pendientes no explican por sí solos
todos los demás bloqueos del lote. No se registran confirmaciones humanas nuevas.

## Uso

El paquete privado ya incluye el checkpoint de 95 con las diez lecturas y el
reporte recalculado: **no hace falta repetir las diez transcripciones ni procesar
los 95 audios**. Conservar este checkpoint como base para cambios de reglas.
`revision_audios_bloque.json` sigue siendo evidencia y no sustituye ese archivo.

Para otros bloques, `INCORPORAR_LECTURAS_BLOQUE.bat` solicita el checkpoint actual
y el JSON de lecturas. Si un resultado r23 se generó sobre otro checkpoint, pide
también aquel archivo de origen para verificar su correspondencia. Los lectores
r24 añaden un vínculo por llamada que permite comprobar ese contexto. Se crea
una copia independiente en `%USERPROFILE%\MRS_Resultados`; no se ejecuta Whisper,
no se copian audios ni se modifican los archivos de entrada.

`REVISAR_BLOQUE_AUDIOS.bat` conserva el modelo original disponible localmente;
añade advertencias técnicas al JSON y a la comparación Excel. No requiere otro
Whisper ni una actualización de Python. Se conserva Python 3.10.

## Verificación

- 765 pruebas unitarias e integración aprobadas, sin errores ni omisiones;
  compilación de aplicación y herramientas.
- 268 evaluaciones históricas contra r23, 196 transcripciones únicas: ninguna
  clasificación cambia, cero violaciones de invariantes y cero retiros de
  penalizaciones sin documentar.
- Los 95 resultados conservan toda la evidencia original y las 22 correcciones
  de nombre. Las 12 aprobaciones anteriores permanecen. Se verifican las 8.550
  celdas de datos del reporte principal contra el checkpoint.
- Las 36 llamadas anteriores conservan sus 7 aprobaciones, 13 correcciones de
  nombre y los registros de importes, saldo y parcialidades confirmados.
- Las lecturas recibidas acreditan ejecución del lector r23 en el equipo del
  usuario. El importador r24 se prueba en Linux con esos archivos y con casos
  sintéticos; falta una ejecución nativa de r24 en Windows. No se realizó una
  nueva transcripción en esta nube ni escucha humana.

No se afirma cierre de los 13 problemas operativos ni de las 81 llamadas pendientes.
