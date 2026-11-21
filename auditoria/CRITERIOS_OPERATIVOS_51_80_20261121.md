# Criterios operativos 51–80 — Monitoreo Speech Analytics

**Recogidos:** 21 de noviembre de 2026. Continuación de `CRITERIOS_OPERATIVOS_50_RESPUESTAS_20261121.md`.
**Importante:** registrar decisión operativa no significa que el motor la implemente o que exista validación acústica. Mantener estatus de gestión, calidad, carpeta de salida y alertas por separado.

| N.º | Regla operativa confirmada / salvedad de implementación |
|---:|---|
| 51 | Responder «sí» al nombre completo indicado por el gestor puede acreditar identidad del titular; validar que la afirmación sea respuesta del interlocutor a esa identificación. |
| 52 | Cuando un familiar plantea negociar, gestor debe confirmar nuevamente si el familiar se hará responsable del pago. No sustituye validación de facultad jurídica para tratar datos del titular. |
| 53 | Convenio aceptado por familiar: estatus CONVENIO conforme instrucción operativa, conservando los controles de identidad/autorización y seguridad. |
| 54 | Interlocutor conoce datos de cuenta pero rehúsa identificarse: decisión depende del diálogo, no clasificar automáticamente CONTACTO NO DETERMINADO sin evaluar contexto. |
| 55 | Tercero conoce al titular pero indica «ya no vive aquí»: MENSAJE CON TERCERO; anotar situación real de contacto sin inferir recepción de recado. |
| 56 | En trabajo, titular ya no labora allí: el estatus depende de si la persona acepta o rechaza el recado. |
| 57 | BUZÓN: dejar únicamente motivo de contacto no sensible y teléfono de retorno, sin revelar saldos ni mora. |
| 58 | Tercero acepta mensaje pero gestor omite teléfono de retorno y no queda acreditado como conocido: gestión incorrecta del gestor, evaluar omisión. |
| 59 | Tercero conoce número de MRS pero gestor no verifica su corrección: recado válido con descuento de 5 puntos. |
| 60 | Recado aceptado sigue válido si tercero pide no volver a llamar; solicitud no puede registrarse en el flujo actual, pero debe canalizarse por un mecanismo de privacidad/operaciones para evitar contacto indebido. |
| 61 | Decir «asunto personal» ante pregunta de tercero por motivo de llamada: respuesta correcta. |
| 62 | Si tras confirmar convenio solo cambia importe sin nueva confirmación de fecha, mantener estatus CONVENIO; verificar que fecha anterior siga asociada al nuevo acuerdo. |
| 63 | Dos pagos, primero confirmado pero fecha del segundo aún pendiente: estatus CONVENIO; conservar alerta de completitud de plan y reglas de mora. |
| 64 | Propuesta espontánea de monto y fecha por titular, aceptada y válida: CONVENIO potencialmente APROBADO aunque gestor no iniciara alternativas. |
| 65 | Fecha fuera del plazo autorizado de mora: estatus NEGATIVA según criterio de monitoreo; conservar evidencia del acuerdo propuesto y penalización/falla por fecha fuera de política. |
| 66 | Aceptación condicionada a recibir salario («si me depositan»): COMPROMISO CONDICIONADO, no convenio firme. |
| 67 | Gestor comunica importe erróneo, lo corrige y obtiene nueva aceptación antes de terminar: evaluar acuerdo final corregido; no penalizar error inicial subsanado según criterio. |
| 68 | Pago parcial explicado correctamente, pero sin ofrecer otras alternativas: puede aprobar con deducción de 5 puntos por omitir alternativas. |
| 69 | OXXO no es lugar autorizado/operativo de pago; no acreditar como pago válido. Si el gestor orienta correctamente, la llamada puede APROBAR; conservar carpeta/alerta de lugar no autorizado. |
| 70 | Gestor facilita referencia bancaria errónea y la corrige antes de cualquier pago: FALLA GRAVE conforme criterio del usuario. |
| 71 | Referencia incorrecta facilitada por gestor previo: NO evaluar únicamente la actuación del gestor actual; identificar responsabilidad del anterior, preservando evaluación diferenciada por persona. |
| 72 | Titular reporta pago y acuerda enviar comprobante, sin fijar día de envío: CONVENIO. |
| 73 | Banco rechazó el pago; gestor proporciona pasos correctos, sin nueva fecha aceptada: NO DEFINE. |
| 74 | Respuesta operativa del usuario: confirmar «sí» a tercero que pregunta si es deuda no se trata como divulgación indebida; requiere revisión de privacidad antes de desactivar controles pues sí puede confirmar información del titular. |
| 75 | La usuaria se refiere al proceso ARCO de tercero que desconoce al titular. NO bloquear derechos ARCO del propio titular o su representante conforme legislación vigente. |
| 76 | Queja de maltrato en llamada anterior: aun si gestor actual da solución, resultado NO APROBADA conforme criterio de monitoreo; conservar atribución del incidente al gestor anterior. |
| 77 | Gestor repite una grosería como cita, sin dirigirla: FALLA GRAVE según criterio de calidad, con evidencia de quién pronunció la palabra. |
| 78 | 95 puntos y posible grosería sin emisor confirmado tras segunda escucha: APROBADO CON ALERTA; alerta visible y no atribuir falta grave sin evidencia. |
| 79 | Audio menor a 1 minuto con gestión completa: APROBADO en carpeta APROBADAS_DURACION_MENOR. |
| 80 | Falla grave comprobada con 90 puntos: FALLA GRAVE; mostrar puntaje 90/100 sin permitir aprobación. |

## Controles que no pueden relajarse automáticamente

- **52–53:** La responsabilidad verbal de pago de un familiar no equivale a autorización legal para divulgar datos de cuenta, negociar o responsabilizarlo por un adeudo ajeno. Conservar protección de datos y validación documental/contractual.
- **60:** Aunque no exista campo de registro de solicitud de no contacto, no se debe ignorar la petición: crear alerta trazable y canalizar a cumplimiento u operaciones sin revelar saldos.
- **65:** Mantener separadas la aceptación expresada por el titular y la validez del convenio por reglas de mora, aun si el estatus solicitado es NEGATIVA; no borrar evidencia de aceptación ni imponer conducta no pronunciada.
- **69:** Una afirmación de pago en OXXO no confirma recepción bancaria. Mantener carpeta especial y no acreditar monto abonado sin conciliación.
- **71/76:** Preservar responsabilidad individual: la conducta del gestor anterior no debe atribuirse sin evidencia al gestor actual aunque el caso se siga monitoreando.
- **74:** Confirmar la existencia de una deuda a un tercero puede revelar datos personales; no suprimir alertas de divulgación sin visto bueno de Compliance.
- **75:** La Ley Federal de Protección de Datos Personales en Posesión de los Particulares reconoce el ejercicio de ARCO a la persona titular o a su representante legal. La regla especial «NO CONOCEN A DEUDOR» es independiente de ese derecho.
- **77/78:** No fabricar un hablante ni convertir posible grosería en confirmada; guardar posición y evidencia de audio.
- **79/80:** La carpeta especial por duración no exime incumplimientos críticos.

## Estado

- Pendiente revisión y pruebas de integración de los 30 escenarios; los cambios particulares solo constarán como implementados si se verifican en el código de esta rama.
- No modificar datos reales, checkpoints ni audios originales.
