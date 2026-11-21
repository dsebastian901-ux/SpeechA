# Criterios operativos 81–160 — Speech Analytics

**Origen:** respuestas de monitoreo del 21/11/2026. **Propósito:** definir la dictaminación antes de programar y validar. No implica implementación, pruebas superadas ni aprobación automática de los audios.

| N.º | Respuesta y regla operativa |
|---:|---|
| 81 | El «sí» a «¿se encuentra Juan Pérez?» no verifica identidad: el gestor debe aclarar quién es el interlocutor. |
| 82 | Si confirma el nombre pero luego dice ser homónimo/otra persona, invalidar identificación inicial. |
| 83 | Titular desconoce tarjeta: ACLARACIÓN solo si se informa que debe tramitar aclaración con el banco; registrar evidencia de orientación. |
| 84 | Si intervienen dos supuestos titulares, detener negociación hasta aclarar identidad. |
| 85 | Familiar acepta pago sin dar su nombre: se penaliza identificación incompleta (monto de descuento NO informado). |
| 86 | Titular autoriza verbalmente que un familiar continúe negociación: SÍ para dictaminación operativa; verificar alcance del consentimiento, privacidad y restricciones legales antes de habilitar información sensible. |
| 87 | Persona dice tener poder legal pero no acredita representación: RECADO CON TERCERO. |
| 88 | Titular negocia y familiar confirma monto/fecha al final: CONVENIO; conservar evidencia de intervención y autorización. |
| 89 | Solo timbrado, sin voz: DEBE DICTAMINARSE; no se proporcionó literal de estatus/carpeta. No evaluar ausencia de habla como falta de gestor. |
| 90 | Buzón contesta, gestor no deja mensaje: permanece BUZÓN, con incumplimiento de calidad. |
| 91 | Dejar saldo/mora en buzón: FALLA GRAVE. |
| 92 | Grabación de número inexistente/fuera de servicio: carpeta especial separada; esas llamadas no deberían ingresar al lote de gestión. |
| 93 | Persona contesta, guarda silencio y termina: SE NIEGA A TOMAR RECADO conforme criterio de monitoreo; no inventar identidad. |
| 94 | Inbound exige mismos pasos de identidad y cierre que llamada saliente. |
| 95 | Transferencia entre gestores: evaluar A CADA UNO de manera separada, solo por su participación. |
| 96 | Falla técnica después de negociación íntegra: conservar evaluación de lo realizado. |
| 97 | Primer tercero rechaza; segundo familiar acepta: prevalece resultado del segundo y se conservan hechos anteriores. |
| 98 | Tercero recibe recado, al final revoca aceptación («mejor no le diré»): SE NIEGAN A TOMAR RECADO. |
| 99 | Dejar recados con MENORES DE EDAD: FALLA GRAVE confirmada. |
| 100 | Tercero sin nombre ni parentesco acepta recado: MENSAJE CON TERCERO. |
| 101 | Tercero reporta hospitalización del titular y acepta recado: evaluar como recado normal. |
| 102 | Buzón del trabajo: BUZÓN. |
| 103 | Tercero acepta transmitir por WhatsApp solamente: NO es recado válido sin contacto de retorno hablado o conforme a matriz. |
| 104 | Recado aceptado válido y tercero pide no volver a contactarlo: solo calificar recado correcto; no existe registro operativo de petición en el flujo. Por cumplimiento, canalizar solicitud de no contacto por vía independiente. |
| 105 | «Pago en 24 horas»: fecha firme solo si no incumple la política de vencimiento/mora. |
| 106 | «Pago en la quincena» sin día: NO DEFINE. |
| 107 | «El próximo martes»: NO cuenta como fecha suficiente para CONVENIO. |
| 108 | «El primer día hábil del mes»: NO es fecha firme suficiente. |
| 109 | «Mil y tantos pesos»: monto no confirmado. |
| 110 | «Entre 500 y 1,000 pesos»: NO DEFINE. |
| 111 | Cantidad en dólares con cuenta MXN: REVISAR moneda. |
| 112 | Monto y fecha propuestos por gestor, titular responde «sí, está bien»: SÍ confirma convenio (distinguir de «ajá» aislado). |
| 113 | Plan de tres pagos: si solo primera fecha confirmada, CONVENIO con penalización por fechas faltantes. |
| 114 | Reestructura: para fecha se evalúa SOLO el primer pago; no penalizar fechas posteriores fuera de plazo por esa regla. |
| 115 | Reestructura 2PV: CONVENIO; política aplicable es PAGO INICIAL del 15% sobre saldo total, no mínimo general. |
| 116 | Bonificación del 35% sobre saldo total autorizada en 3PV, dentro de vencimiento; ofrecer en otra mora => FALLA GRAVE confirmada. |
| 117 | Fecha fuera de política clasificada NEGATIVA debe contabilizarse en la estadística de «se niegan a pagar»; guardar causa operativa para trazabilidad. |
| 118 | CONVENIO INCUMPLIDO anterior seguido de nuevo acuerdo válido: resultado final CONVENIO; conservar antecedente. |
| 119 | Monto y fecha exactos con condición «si recibo mi sueldo»: CONVENIO según criterio más reciente. Conservar condición verbal y no falsear certeza. |
| 120 | Pago inicial inferior al mínimo más resto acordado en otra fecha y total suficiente: CONVENIO COMPLETO; verificar política específica de mora. |
| 121 | Dos sucursales de una misma cadena autorizada: UN SOLO LUGAR. |
| 122 | Banco autorizado mencionado sin referencia bancaria: «sí» a contar como lugar válido, según respuesta; no implica que datos de pago incompletos sean instrucciones seguras. |
| 123 | Santander en ventanilla y transferencia autorizada a Santander: SÍ cuentan como dos opciones diferentes. |
| 124 | Cliente sin WhatsApp que enviará comprobante por email autorizado: cierre correcto. |
| 125 | Solicitud de comprobante a WhatsApp personal del gestor: FALLA GRAVE. |
| 126 | Gestor repite referencia incorrecta aportada por el cliente incluso sin recomendarla: FALLA GRAVE, según criterio del usuario; exigir evidencia de expresión y atribución. |
| 127 | Depósito aceptado por banco sin aplicación en sistema: CONVENIO con alerta de pago pendiente. |
| 128 | Titular denuncia pago en efectivo a personal del despacho: alerta especial de POSIBLE FRAUDE, independiente del score del gestor actual. |
| 129 | Familiar reporta fallecimiento sin documentación: MENSAJE CON FAMILIAR, con gestión de validación de defunción pendiente. |
| 130 | Titular desconoce tarjeta: ACLARACIÓN solo si confirma que realizará trámite bancario. |
| 131 | Número antes asociado al titular ahora pertenece a tercero: RECADO según estatus operativo; no autoriza compartir saldo ni suprimir corrección de datos. |
| 132 | Respuesta literal «sin» en mensaje («132 sin133no») no permite confirmar si era SÍ, SIN o NO; pendiente de respuesta. |
| 133 | Tercero menciona saldo y gestor lo repite confirmándolo: el usuario responde NO a considerar divulgación indebida; NO desactivar evaluación de privacidad hasta validación de Compliance. |
| 134 | Titular pide ARCO durante negociación sin convenio: NO DEFINE para estatus de cobranza, tramitar derechos por separado. |
| 135 | Titular solicita no llamar al trabajo, sí al móvil: gestión puede APROBAR; conservar/canalizar restricción de contacto. |
| 136 | Titular denuncia divulgación de otro gestor: sí generar reporte independiente de posible incidente de privacidad. |
| 137 | Visitas de cobranza no amenazantes PERMITIDAS en 3PV y mora superior; conservar contexto y regulación aplicable. |
| 138 | Uso de «jurídico» o «última oportunidad» sin amenaza expresa: NO penalizar según criterio más reciente; manténgase supervisión normativa/política externa. |
| 139 | Interrupciones reiteradas del gestor sin insultos o amenazas: DESCUENTO de 5 puntos. |
| 140 | Gestor levanta la voz de forma agresiva sin insultar: ALERTA PENDIENTE, confirmar audio. |
| 141 | SIN RESPUESTA en mensaje: titular acusa a gestor actual de maltrato, audio no lo confirma. No asignar resultado por inferencia. |
| 142 | Interlocutor insulta/amenaza y gestor termina profesionalmente: APROBADO CON EXCEPCIÓN (verificación acústica y condiciones de excepción). |
| 143 | Amenaza con contactar al empleador para presionar pago: FALLA GRAVE. |
| 144 | Maltrato denunciado de un empleado bancario externo (no MRS): llamada actual NO APROBADA según criterio de monitoreo; conservar atribución a empleado externo. |
| 145 | Dos faltas independientes de 5 puntos: acumular descuentos y restar 10. |
| 146 | Recado aceptado sin teléfono de retorno: descuento de 15 puntos. |
| 147 | Titular cuelga antes de identificación total: descuento de 25 puntos. |
| 148 | Queja confirmada de maltrato en llamada anterior: carpeta especial QUEJAS, sin confundir responsabilidad entre gestores. |
| 149 | Primera escucha posible grosería, segunda no corrobora voz/expresión: APROBADO CON ALERTA; documentar discrepancia. |
| 150 | Llamada de 45 s con alerta no bloqueante: carpeta APROBADAS_DURACION_MENOR tiene prioridad. |
| 151 | Etiqueta corregida, score >80 y privacidad todavía no resuelta: respuesta NO a mantener REVISAR; no suprimir advertencia de divulgación sin evidencia/validación legal. |
| 152 | Misma conducta genera penalización por falta de gestión y falta de alternativa: aplicar AMBAS según criterio indicado; marcar independencia de hechos en evidencia. |
| 153 | Dos tarjetas diferentes en una llamada: dictamen independiente por CUENTA. |
| 154 | Dos grabaciones idénticas atribuidas a distintos gestores: SÍ abrir revisión de identidad/autenticidad. |
| 155 | Tarjeta Excel coincide, nombre tiene error ortográfico pequeño: relacionar AUTOMÁTICAMENTE si identidad de cuenta por datos fuertes está confirmada. |
| 156 | Dos llamadas diferentes del mismo gestor/cuenta/día: conservar y evaluar AMBAS; no marcarlas duplicadas. |
| 157 | Reclasificar FALLA GRAVE a APROBADO manualmente: exige AUTORIZACIÓN adicional, mantener evidencia, versiones y responsable. |
| 158 | Nueva versión Whisper deja de detectar falla grave antes corroborada: conservar dictamen anterior hasta validación humana. |
| 159 | Audio contiene conversación ajena al final: generar INCIDENCIA de audio; no atribuirla al gestor principal. |
| 160 | Audio inicia cortado sin identificación inicial verificable: EVALUAR PARCIALMENTE, no ERROR DE AUDIO automático. Respuesta del usuario figura como «169 evaluarse parcialmente», interpretada como 160. |

## Respuestas faltantes o ambiguas

- **132:** la cadena `132 sin133no` no determina con seguridad la respuesta de 132; la de 133 sí se registra como NO.
- **141:** no se recibió respuesta explícita.
- **160:** la última respuesta escrita `169 evaluarse parcialmente` se interpreta provisionalmente como 160 por la secuencia 81–160.
- **85:** consta que se penaliza al familiar sin nombre, pero no la cuantía del descuento.
- **89:** se requiere dictaminar las llamadas sin voz; falta código literal de estatus/carpeta.
- **122:** respuesta «sí» a contar banco sin referencia; no autoriza publicar datos bancarios insuficientes o inseguros.

## Resguardos de cumplimiento

- **99/91/125/143:** confirmaciones de conductas de alto riesgo: proteger menores, privacidad en buzón, canales personales de entrega y amenazas.
- **116:** la bonificación 35% en 3PV debe cotejarse con autorización comercial vigente y fecha para cada lote; no basta el texto transcrito.
- **117:** el código estadístico NEGATIVA usado por política debe diferenciar su causa de una negativa expresa en evidencias aunque reporte agrupado.
- **133:** la respuesta operativa no suprime obligaciones de confidencialidad ni resuelve por sí misma si confirmar deuda a tercero es divulgación.
- **145/152:** se acumulan descuentos independientes, respetando tope de score 0 y justificación verificable.
- **153–159:** no alterar fuentes originales, bitácora de versiones, cuentas ni responsabilidad individual.

## Estado de implementación

Estas son reglas DOCUMENTADAS para análisis y pruebas de regresión. No declarar ninguna de las 80 implementada hasta verificar el comportamiento del motor y compararlo con audios reales; PR #5 permanece en borrador.