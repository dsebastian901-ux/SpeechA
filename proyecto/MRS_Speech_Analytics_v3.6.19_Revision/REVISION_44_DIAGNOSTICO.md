# r44 — corrección de interpretación y revisiones innecesarias

## Resultado comprobado en el lote recibido

r43: 15 APROBADO, 71 REVISAR, 11 NO_APROBADO_MENOR_80 y 3 FALLA_GRAVE.
r44: 17 APROBADO, 65 REVISAR, 15 NO_APROBADO_MENOR_80 y 3 FALLA_GRAVE.

Tres llamadas se liberan sin aumentar puntajes. Cuatro salen de revisión para rechazarse por incumplimientos ordinarios con puntaje insuficiente. Una aprobación se retira al reconocer una denuncia de atención previa deficiente. No se elimina esa queja para conservar un número de aprobaciones. La revisión sigue siendo alta y no se declara resuelto todo el problema.

El Excel individual privado documenta las 100 llamadas y las 65 pendientes, con archivo, fecha, últimos cuatro dígitos, dictamen, puntaje, motivo y hallazgo. No está incluido en este ZIP público.

## Correcciones

- Separa pago de servicio por convenio de transferencia a CLABE/cuenta. Valida códigos bancarios literales o dictados por grupos completos, sin truncar ni completar desde Excel. Esta validación no agrega opciones por mencionar un banco aisladamente.
- No trata pedir captura de una transferencia como dictar un destino bancario nuevo. Una cuenta, CLABE o instrucción de transferencia concreta conserva sus filtros.
- Reconoce solicitudes de compartiría/compartiríamos el comprobante.
- No confunde el teléfono de diez dígitos al reverso con una tarjeta de dieciséis. Conserva comparación de la tarjeta real contra numero_de_tarjeta del Excel.
- Reconoce conversación sobre transferencia propia, presupuesto pendiente o carta finiquito propia tras pregunta nominal, con exclusiones de terceros, gestor conocido, hipótesis y respuestas aisladas.
- Reconoce confirmaciones explícitas de monto/fecha y respuestas con objeto de pago; un ok genérico o recibir WhatsApp no bastan. Una falla de registro en una aplicación sola no define estatus de pago.
- Distingue realizó de realizo para no sustituir una promesa futura con una frase administrativa sobre actualización.
- Separa fechas informativas del siguiente ciclo de la promesa actual; no convierte día 7-8 en agosto del año siguiente.
- Lee 11 100 pesos como un solo importe; no usa únicamente los últimos tres dígitos. Vincula el importe preguntado para un porcentaje propuesto, sin calcularlo a partir de la cuenta de Excel.
- No trata cubrir/poner al corriente saldo vencido como afirmar el saldo total. Distingue cotizaciones históricas, preguntas y declaraciones actuales.
- Cuenta en cero es un estado reportado por el interlocutor, nunca una verificación bancaria. Si hay queja de llamadas/molestia o atención anterior, sigue bloqueada la aprobación.
- Reconoce me colgó, me dices que me calle y denuncias de mensajes de cobranza sin respuesta como quejas por revisar. No atribuye automáticamente la conducta al gestor actual.

Se conservan privacidad/PEN003, ARCO, groserías, recados, amenazas/visitas, espera de 65 segundos, reglas de mora y los campos de validación humana. La omisión de dos lugares resta 20; no crea un bloqueo adicional si conserva 80 y cumple los otros filtros.

## Aplicación en Windows

1. Extraiga TODO el ZIP en una carpeta nueva.
2. Abra proyecto/MRS_Speech_Analytics_v3.6.19_Revision.
3. Ejecute REANALIZAR_CHECKPOINT.bat.
4. Seleccione el último checkpoint_reanalizado.json generado con r43, el mismo que acaba de enviar.
5. Espere el mensaje final. Se guardan un checkpoint nuevo y los Excel de calidad y motivos de no pago en otra carpeta.

No necesita volver a transcribir los audios ni descargar otro Whisper. No cambie manualmente los dictámenes ni las transcripciones. El original se conserva.

## Validación y límites

1,945 pruebas correctas, 7 de interfaz omitidas, cero fallos. Linux/Python 3.10; sin certificación nativa de Windows. Se auditó la regresión de 2,217 evaluaciones en cuatro salidas correspondientes a 1,210 llamadas únicas: ASR, cuentas, confirmaciones, celdas de calidad y totales de motivos de no pago.

Se contrastaron seis ventanas con medium local para investigar dudas; una repetitiva y otra de cobertura insuficiente fueron descartadas. No constituye escucha humana ni comparación controlada entre modelos. No se aplicaron esas lecturas a las aprobaciones ni se reemplazó Whisper original.

Persisten casos con voz, importes, fechas, estatus o transcripción ambiguos. La política de cancelación por saldo total sin descuento en 1–3 PV continúa pendiente; se conserva la regla anterior. No aprobar para cumplir una cuota. El instalador final con usuarios sigue en desarrollo separado; este ZIP es el piloto de correcciones.
