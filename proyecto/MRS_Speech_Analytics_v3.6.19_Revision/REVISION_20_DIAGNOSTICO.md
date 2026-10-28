# Revisión 20 · identidad y atribución de liquidaciones

El primer lote ampliado recibido contiene 95 llamadas completadas en r19:
91 REVISAR y 4 FALLA_GRAVE, sin errores técnicos. El reporte coincide con su
checkpoint. Whisper sí se ejecutó en ese procesamiento, con modelo small y CPU.
El tiempo registrado del lote fue de aproximadamente 1 hora 41 minutos.

## Correcciones

- Confirmación del titular: incorporar preguntas habituales con respuesta
  afirmativa, como Tengo el gusto con, Me comunico con y Con la señorita.
  Reconocer de favor y respuestas explícitas de identidad separadas por una
  presentación breve. Las preguntas sobre familiares, bancos, pagos o tarjetas
  no confirman titularidad. Una respuesta del gestor, un tercero conocido,
  ausencia, negación o petición de esperar no se convierte en titular.
- Liquidación: usar frases completas en lugar de ventanas acústicas como si
  fueran turnos. Diferenciar una pregunta o repetición sin atribución de una
  oferta. Cubrir el saldo vencido no equivale a liquidar toda la cuenta.
  Un verbo deber seguido de un monto describe deuda y no una orden de pago.
  Las intenciones en primera persona y los antecedentes no son ofertas del gestor.
- Conservar como críticas las ofertas totales explícitas en moras restringidas,
  incluidas explicaciones de pago total tras rechazar un descuento. Conservar
  como REVISAR las posibles liquidaciones sin oferta o atribución confirmada.
  Se guardan texto, rol disponible y tiempos de la evidencia usada.

No se cambia el puntaje mínimo, las penalizaciones del manual ni la transcripción.
No se infiere titularidad del estatus de Excel. No se instala otro modelo Whisper.

## Resultado del lote de 95

- Titulares reconocidos: de 6 a 26. Siguen sin identidad confirmada 67 llamadas.
- Dictaminaciones: 1 APROBADO, 92 REVISAR y 2 FALLA_GRAVE. Solo cambiaron de
  clasificación las llamadas 4, 22 y 63.
- Las llamadas 4 y 63 pasan de falla grave a revisión: saldo debido/intención
  personal y una repetición de liquidación no acreditaban la oferta penalizada.
- La llamada 22 obtiene APROBADO con 80 puntos. Es un resultado automático
  pendiente de cotejo acústico; no una verificación humana del asistente.
- Las llamadas 81 y 93 conservan falla grave por ARCO y oferta de liquidación,
  respectivamente, según la transcripción. Sus audios son prioritarios para cotejo.
- Persisten 22 nombres de salida discordantes. Ninguno de esos nombres constituye
  por sí solo el único bloqueo para aprobar con los demás controles actuales.
- No se consideran las 92 revisiones como incumplimientos ya demostrados. Muchos
  estatus no están confirmados. El motor conserva el límite informativo de 79
  cuando el estatus no se valida; ese puntaje no equivale a una medición humana
  de la calidad real del gestor.

Se conservaron las 95 transcripciones, segmentos, datos de cuenta y archivos
originales. El reanálisis no ejecutó Whisper ni movió o renombró audios. No se
puede determinar por qué el lote contiene 95 en vez de 100 sin la lista de entrada.

## Pruebas y límites

- 569 pruebas aprobadas; compilación de app y tools correcta con Python 3.10.
- Regresión de 268 evaluaciones históricas: 262 REVISAR, 2 FALLA_GRAVE y
  4 APROBADO, sin fallos de seguridad ni eliminaciones injustificadas de penalización.
- El lote anterior de 36 conserva 4 APROBADO y 32 REVISAR, sus 13 correcciones de
  nombres y las confirmaciones previas de importe, saldo y parcialidades.
- Se comprobaron las 87 columnas del reporte nuevo frente al checkpoint.

Las reglas nuevas se ejecutaron en Linux. Falta verificar el reanálisis de esta
entrega en Windows y cotejar audios de este lote. El asistente no escuchó los
audios ni verificó sus voces. Los datos reales permanecen fuera de Git.
Los 13 problemas no se consideran cerrados; se requiere calibración por casos.

## Aplicación en Windows

Extraer el paquete y ejecutar REANALIZAR_CHECKPOINT.bat desde
proyecto\MRS_Speech_Analytics_v3.6.19_Revision. Seleccionar el checkpoint del lote
de 95. Los archivos nuevos quedan en
%USERPROFILE%\MRS_Resultados\Reanalisis_MRS_r20_... . No es necesario repetir ASR.
