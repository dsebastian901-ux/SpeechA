# r42 — identificación contextual y validación del lote de 100

## Resultado

- Archivo recibido: 1 APROBADO, 96 REVISAR y 3 FALLA_GRAVE.
- Reglas nuevas, nombres originales: 84 REVISAR, 7 APROBADO, 6 NO_APROBADO_MENOR_80, 3 FALLA_GRAVE.
- Con corrección autorizada de nombres desde numero_de_tarjeta: 74 REVISAR, 12 APROBADO, 11 NO_APROBADO_MENOR_80, 3 FALLA_GRAVE.
- Se corrigieron 44 nombres de salida en copia. El ASR, las cuentas y los archivos originales se conservan.

La mejora es parcial: persisten muchas llamadas pendientes. REVISAR no equivale a una falta demostrada; no se cambian etiquetas para aparentar una menor necesidad de revisión ni se fija una cuota de aprobaciones.

## Criterio operativo confirmado por el usuario

La identificación del titular se evalúa por la pregunta nominal, la respuesta y la conversación sobre su propia tarjeta o pago, sin indicios de familiar o transferencia. También se conserva la autorreferencia inequívoca a la cuenta después de la pregunta nominal. No se exige una frase literal como «soy yo»; un sí o agradecimiento aislado no basta. La etiqueta del Excel no constituye evidencia de quién habla.

Se mantienen los filtros contra terceros, actuación por otra persona, ausencia del titular, citas, hipótesis y voz conocida del gestor. La nueva evidencia es textual y no se registra como escucha humana o diarización.

## Otras correcciones

- Por aclaración operativa del usuario, omitir dos lugares autorizados resta 20 puntos; puede aprobar con 80 si cumple los demás filtros. La omisión sigue visible y penalizada, sin bloqueo adicional de revisión.
- «El pagaré» no significa «yo pagaré». Las condiciones y los rechazos no se convierten en un convenio firme.
- Las preguntas de confirmación no requieren repetir dos veces «pago»; se distinguen preguntas futuras, depósitos anteriores y aceptación condicionada.
- Un convenio nuevo aceptado con fecha mantiene sus validaciones aunque también se mencione un pago histórico.
- Reconoce depósitos y pagos reportados mediante formas pasivas y demostrativos; una notificación futura de recibido no acredita un pago anterior.
- Reconoce «puede realizarle» como variante ASR del ofrecimiento de pago cuando enumera marcas autorizadas; excluye la negación y mantiene marcas únicas.
- Reconoce el reporte de capturas ya enviadas, incluidas expresiones como «ya les pasé las capturas».
- Interpreta «8 mil» como 8000, sin completarlo desde Excel; mantiene revisión de cifras fragmentadas y contradictorias.
- Distingue saldo histórico, descuento ofrecido, corrección explícita de saldo y días del mes.
- Una cortesía posterior a una despedida no convierte la cola de grabación en espera. La conversación pendiente conserva el límite de 65 segundos.
- El puntaje inferior a 80 por criterios ordinarios puede resolverse como NO_APROBADO_MENOR_80 cuando no hay dudas de seguridad, finanzas, trato, referencias o llamadas pendientes. Se conservan las observaciones de identidad y etiqueta; no se certifica que estén resueltas. Una incertidumbre de seguridad mantiene REVISAR.
- Las denuncias de insultos formuladas como pregunta se conservan como quejas, sin confundirlas con preguntas del gestor o negaciones.
- Las referencias a cobros percibidos como amenazas mantienen el bloqueo de trato; no se atribuyen como falta grave del gestor por esa frase aislada.
- Las quejas de hostigamiento y afectación del trabajo bloquean la aprobación, también en seguimientos de pago.
- Se conservan privacidad, ARCO, visitas en 1–2 PV, groserías, referencias y reglas de mora, montos y fechas.

## Alcance del contraste de audio

Se recibieron 100 grabaciones con coincidencia exacta de nombres y duraciones. El contraste adicional utilizó 27 ventanas de 12 llamadas, con Whisper medium local; 5 lecturas repetitivas se excluyeron como evidencia para resolver criterios.

La comparación fue orientativa: también cambian el motor y la decodificación respecto a small. No demuestra que sea obligatorio cambiar el modelo del usuario. Las lecturas nuevas no sustituyeron la transcripción ni alimentaron las aprobaciones de este reanálisis. Esta corrección funciona sobre el checkpoint actual, sin ejecutar Whisper.

## Pendientes del lote

Quedan 41 contactos no determinados, 75 estatus sin coincidencia confirmada, 42 puntajes por debajo de 80, 5 alertas de queja y 1 de espera. Son cifras superpuestas.

Se consultó un caso de cancelación por pago del saldo total sin descuento en 1–3 PV para distinguirlo de una liquidación no autorizada. Se conserva la regla anterior mientras esa definición no sea aclarada. No se afirma que todas las marcaciones graves hayan sido confirmadas por una persona.

## Regresión

- 1819 pruebas correctas, 7 gráficas omitidas, cero fallos.
- Lote anterior de 1,007: 939 REVISAR, 18 NO_APROBADO_MENOR_80, 39 APROBADO, 11 FALLA_GRAVE.
- Copia anterior de 1,007 con nombres corregidos: 889 REVISAR, 41 NO_APROBADO_MENOR_80, 66 APROBADO, 11 FALLA_GRAVE.
- Lote anterior de 103: 72 REVISAR, 21 APROBADO, 9 FALLA_GRAVE, 1 NO_APROBADO_MENOR_80.
- Verificadas todas las celdas de calidad y los totales de motivos en cinco salidas. Confirmaciones previas y transcripciones conservadas.

## Uso con este lote

1. Extraer el ZIP completo en una carpeta nueva.
2. Abrir REANALIZAR_CON_TARJETA_EXCEL.bat.
3. Seleccionar el batch_checkpoint.json de las 100 llamadas enviadas. Se usa numero_de_tarjeta guardado en cada cuenta para corregir el nombre en copia.
4. Esperar el mensaje final. Los Excel de calidad y motivos de no pago se generan en la carpeta 04_Reportes nueva; el checkpoint nuevo se llama Checkpoint_r42_Recuperado.json.

El reanálisis conserva los archivos originales y no mueve las copias físicas de audio anteriores. Para conservar los nombres anteriores usar REANALIZAR_CHECKPOINT.bat. Para audios nuevos usar el procesamiento habitual y el modelo local instalado.

Esta entrega es un piloto de reglas, no el instalador final con usuarios.
