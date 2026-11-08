# Revisión 50 — causas de revisión automática

Las reglas se aplican a todos los audios, tanto al procesar un proyecto nuevo como al reanalizar. No hay excepciones por número de llamada, no se reescribe Whisper y no se cambian los datos originales para conseguir aprobaciones.

## Correcciones

1. Identificación: respuestas a solicitudes nominales, contexto de pago propio y autoidentificación de un familiar. Un sí inicial no prevalece sobre «habla su esposo» o «no, es su hermana». La ausencia declarada al solicitar una persona puede acreditar un intermediario aunque el receptor pregunte después quién llama. No se infiere parentesco por el Excel.
2. Recados: variantes locales de parentesco, amigo/conocido y trabajo; aceptación del mensaje y acuse del dictado; instrucciones de retorno expresadas de otras formas. Una cita, pregunta, agradecimiento del gestor o una oferta sin recepción no acreditan recado. Se conservan las respuestas reales de preparación del dictado y el traslado expresamente aceptado a Recursos Humanos en una línea laboral. La imposibilidad expresa de transmitirlo y un cierre claro pueden resolver NO_APROBADO.
3. Privacidad: la etiqueta de Excel no vuelve tercero a un titular identificado en la conversación. Se mantiene protección de importes, mora, deuda, tarjeta completa y estado financiero. Se conserva la autorización para «saldo pendiente» y «saldo vencido» sin cantidad. La autopresentación institucional dentro de la misma cláusula puede aportar atribución textual de esa declaración, con su método y límites explícitos; no asigna una voz acústica ni se propaga a otros turnos.
4. Referencias e importes: un dictado de contacto con ecos no se convierte automáticamente en referencia incompleta de tarjeta; las referencias explícitas y los 16 dígitos conservan validación. «Termina» y «terminó en» se tratan como identificadores. Una terminación de más de cuatro dígitos sigue pendiente y no se recorta para aprobar.
5. ARCO: se consideran intentos posteriores de dictar la dirección cuando un primer intento fue incompleto. Se conserva la exigencia de dominio completo y los demás pasos. Las instrucciones largas de documentos se evalúan dentro de la misma oración; no se completa un correo ni se inventa un documento.
6. Seguimientos: «¿mandó el comprobante? Sí» acredita reporte de envío previo, no recepción bancaria ni promesa nueva. Se conservan CONVENIO/TH en los seguimientos autorizados. La aclaración de pago se representa con el estatus válido ACLARACION cuando corresponde, sin certificar saldo al corriente. Los seguimientos documentales por fallecimiento conservan el estatus original por instrucción de la usuaria del 08/nov/2026; la conservación no exime seguridad ni trato.
7. Decisiones claras: quejas declaradas y documentadas pueden cerrar NO_APROBADO. Las preguntas, hipótesis o evidencias incompletas siguen REVISAR. La queja explícita de incompetencia del equipo o falta de personal capacitado para resolver también bloquea la aprobación. La falta de material para anotar, sin entrega ni alternativa posterior, no se convierte en recado recibido. Una falta crítica mantiene prioridad y cualquier duda independiente de seguridad conserva revisión.
8. Reportes: se corrige Revisar del resumen por gestor, se separan errores técnicos y se añaden columnas de no aprobados, fallas graves, errores y otros resultados. REVISION_PENDIENTE enumera las causas de las llamadas realmente pendientes con acciones y evidencia disponible. Los códigos de estatus derivados de otra duda no se cuentan como llamadas adicionales.

## Comprobación

VALIDACION_R50.json detalla las pruebas, el lote de 362, la auditoría de las 290 revisiones de r49, los conjuntos anteriores y las pruebas del lote normal. El comparativo privado identifica todas las llamadas y sus motivos antes/después; no contiene nuevas escuchas humanas.

## Límites

Se evalúan las transcripciones recibidas y sus segmentos. La prueba de proyecto nuevo usa ASR controlado; no equivale a volver a ejecutar Whisper en todo el lote. La atribución textual institucional no es una identificación acústica de voz. Los casos que conservan voz, referencia o términos financieros ambiguos permanecen REVISAR. No se declara prueba nativa de Windows ni entrega del futuro instalador autónomo con usuarios.
