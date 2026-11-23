# Evidencia individual de los 34 fallos

Todos se reprodujeron individualmente contra `14cd432` y de nuevo contra el código entregado. Las pruebas existentes no se modificaron. `PASA` significa que se ejecutó completa esa prueba; `FALLA` sigue siendo un bloqueo. Los identificadores incluyen el parámetro original mediante hash, aunque no se publique su texto.

Son pruebas del programa con datos sintéticos, incluidas rutas normales de lotes, importación de revisiones y exportaciones; no son recálculos de los checkpoints reales de clientes ni una medición de tasa de aprobados.

## Recados

8 pasan / 2 fallan.

### fb39a573fb0b

- Prueba: `tests/test_context_audio_recovery.py::test_callback_consensus_resolves_only_missing_contact`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: El dictaminador duplicaba un detector estrecho de oferta de teléfono y trataba ASR incompleto como omisión acreditada de -15 puntos, llegando a aprobar. Antes aprobaba una oferta con seis dígitos. El consenso simulado posterior solo resuelve su entrega y conserva otros bloqueos. No se ejecutó una nueva escucha Whisper en esta prueba.
- Cambio productivo: Consumir unfinished_callback_offer como fuente compartida y reconocer ofertas directas y contacto truncado/repetido. Incertidumbre de entrega sigue REVISAR; omisión acreditada conserva -15 y umbral 80.
- Código: [analytics_service.py:1565](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L1565) · `calculate_basic_compliance`; [message_contact_evidence.py:214](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/message_contact_evidence.py#L214) · `unfinished_callback_offer`.
- Criterios: 58,146.
- Resultado: Prueba completa PASA; sin consenso suficiente no aprueba.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### 294977b1114a

- Prueba: `tests/test_dialogue_frames_r53.py::test_later_receipt_replaces_temporary_inability_but_not_final_refusal`.
- Antes → después: **FALLA → FALLA**. ABIERTO_CONFLICTO_CONTRATO_CRITERIO.
- Causa: La prueba exige NO_APROBADO por la sola negativa/incapacidad del tercero. La implementación vigente separa rechazo de recado y falta del gestor; el fixture deja una discrepancia de estatus sin código autorizado y, en algunas variantes, alertas independientes. La primera variante con recepción posterior acreditada pasa; la segunda ya detecta rechazo final, pero la prueba exige además rechazo automático de calidad.
- Cambio productivo: Sin cambio para forzar NO_APROBADO: conservar estatus SE NIEGAN A TOMAR RECADO, evaluación de etapas ejecutables y REVISAR cuando falta resolución sustentada. No convertir una conducta del tercero en incumplimiento del gestor ni inventar código de etiqueta.
- Código: [definitive_rejection.py:86](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/definitive_rejection.py#L86) · `definitive_rejection`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [status_output_label.py:24](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/status_output_label.py#L24) · `corrected_status_label`; [quality_decision.py:20](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/quality_decision.py#L20) · `evaluate_quality`.
- Criterios: 13,14,50,98.
- Resultado: Variante final: SE NIEGAN A TOMAR RECADO / REVISAR,100; pytest FALLA.
- Pendiente: Conciliar formalmente expectativa histórica con criterio vigente/catálogo y contrato de calidad, sin modificar esta prueba ni imponer un dictamen artificial.

### 017c652653b3

- Prueba: `tests/test_dialogue_frames_r53.py::test_received_message_with_incomplete_callback_has_its_actual_pending_reason`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: La decisión ya era REVISAR, pero el motivo no cumplía el contrato textual que distingue recepción probada de entrega incierta del teléfono. No era una aprobación indebida: la falla era el texto del motivo pendiente. Se informa recepción acreditada y teléfono incierto.
- Cambio productivo: Explicar expresamente la recepción acreditada y el contacto incompleto en ASR; no cambiar dictamen, puntuación ni inferir omisión.
- Código: [analytics_service.py:1594](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L1594) · `calculate_basic_compliance`.
- Criterios: 58,146.
- Resultado: Prueba completa PASA; conserva REVISAR.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### ef2311590209

- Prueba: `tests/test_fresh_batch_message_policy_r48.py::test_new_batch_applies_message_policy_and_safety_before_any_reanalysis`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: El dictaminador duplicaba un detector estrecho de oferta de teléfono y trataba ASR incompleto como omisión acreditada de -15 puntos, llegando a aprobar. Lote nuevo, variante conditionalphone: antes APROBADO85 al tratar contacto ofrecido incierto como omisión -15. Corrección aplicada en procesamiento normal, sin reanálisis ni lista de nombres.
- Cambio productivo: Consumir unfinished_callback_offer como fuente compartida y reconocer ofertas directas y contacto truncado/repetido. Incertidumbre de entrega sigue REVISAR; omisión acreditada conserva -15 y umbral 80.
- Código: [analytics_service.py:1565](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L1565) · `calculate_basic_compliance`; [message_contact_evidence.py:214](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/message_contact_evidence.py#L214) · `unfinished_callback_offer`.
- Criterios: 58,146.
- Resultado: Prueba completa PASA; lote nuevo aplica incertidumbre y seguridad.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### fccd255baf2b

- Prueba: `tests/test_message_dialogue_r49.py::test_declined_note_without_contact_is_definitive_but_later_delivery_is_not`.
- Antes → después: **FALLA → FALLA**. ABIERTO_CONFLICTO_CONTRATO_CRITERIO.
- Causa: La prueba exige NO_APROBADO por la sola negativa/incapacidad del tercero. La implementación vigente separa rechazo de recado y falta del gestor; el fixture deja una discrepancia de estatus sin código autorizado y, en algunas variantes, alertas independientes. Imposibilidad final de anotar está detectada; primer assert exige NO_APROBADO antes de comprobar las variantes con entrega o canal alternativo. No se certifican los asserts posteriores de una prueba fallida.
- Cambio productivo: Sin cambio para forzar NO_APROBADO: conservar estatus SE NIEGAN A TOMAR RECADO, evaluación de etapas ejecutables y REVISAR cuando falta resolución sustentada. No convertir una conducta del tercero en incumplimiento del gestor ni inventar código de etiqueta.
- Código: [definitive_rejection.py:86](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/definitive_rejection.py#L86) · `definitive_rejection`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [status_output_label.py:24](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/status_output_label.py#L24) · `corrected_status_label`; [quality_decision.py:20](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/quality_decision.py#L20) · `evaluate_quality`.
- Criterios: 7,14,50.
- Resultado: SE NIEGAN A TOMAR RECADO / REVISAR,100; pytest FALLA.
- Pendiente: Conciliar formalmente expectativa histórica con criterio vigente/catálogo y contrato de calidad, sin modificar esta prueba ni imponer un dictamen artificial.

### 443928271266

- Prueba: `tests/test_message_dialogue_r49.py::test_repeated_partial_number_at_cutoff_is_not_complete_contact`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: El dictaminador duplicaba un detector estrecho de oferta de teléfono y trataba ASR incompleto como omisión acreditada de -15 puntos, llegando a aprobar. Repeticiones 222/500 al corte no conforman un teléfono completo. Se usa detector compartido en lugar de certificar por eco.
- Cambio productivo: Consumir unfinished_callback_offer como fuente compartida y reconocer ofertas directas y contacto truncado/repetido. Incertidumbre de entrega sigue REVISAR; omisión acreditada conserva -15 y umbral 80.
- Código: [analytics_service.py:1565](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L1565) · `calculate_basic_compliance`; [message_contact_evidence.py:214](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/message_contact_evidence.py#L214) · `unfinished_callback_offer`.
- Criterios: 58,146.
- Resultado: Prueba completa PASA; no acredita teléfono ni aprueba.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### e226eaa54329

- Prueba: `tests/test_message_dialogue_r49.py::test_return_instruction_without_a_delivered_contact_never_approves`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: El dictaminador duplicaba un detector estrecho de oferta de teléfono y trataba ASR incompleto como omisión acreditada de -15 puntos, llegando a aprobar. La instrucción «al siguiente número» sin dígitos disponibles es entrega incierta, no omisión acreditada que permita aprobar85.
- Cambio productivo: Consumir unfinished_callback_offer como fuente compartida y reconocer ofertas directas y contacto truncado/repetido. Incertidumbre de entrega sigue REVISAR; omisión acreditada conserva -15 y umbral 80.
- Código: [analytics_service.py:1565](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L1565) · `calculate_basic_compliance`; [message_contact_evidence.py:214](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/message_contact_evidence.py#L214) · `unfinished_callback_offer`.
- Criterios: 58,146.
- Resultado: Prueba completa PASA; review_required=True y sin aprobación.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### 0bbd759fc50c

- Prueba: `tests/test_recado_context_r27.py::test_actual_message_refusals_still_block`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: Se omitía el rechazo elíptico de un recado ofrecido («no se lo puedo pasar», «no puedo recibir»), permitiendo una recepción falsa. «No puedo recibir,disculpe» respondía a oferta de recado; antes se omitía el rechazo y se aprobaba recepción inexistente.
- Cambio productivo: Resolver el objeto recado por contexto inmediato, sin cruzar otro objeto ni citas/preguntas/rol del gestor. El rechazo final impide acreditar recepción; no inventar penalización de calidad.
- Código: [definitive_rejection.py:10](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/definitive_rejection.py#L10) · `explicit_message_refusal`; [message_workflow.py:52](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/message_workflow.py#L52) · `workflow_validation`.
- Criterios: 14,98.
- Resultado: Prueba completa PASA; rechazo reconocido, no aprobación.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### 7b063e578671

- Prueba: `tests/test_recado_context_r27.py::test_actual_message_refusals_still_block`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: Se omitía el rechazo elíptico de un recado ofrecido («no se lo puedo pasar», «no puedo recibir»), permitiendo una recepción falsa. «No se lo puedo pasar» con objeto recado previo no se reconocía como rechazo; no se aplica a otros objetos ni preguntas.
- Cambio productivo: Resolver el objeto recado por contexto inmediato, sin cruzar otro objeto ni citas/preguntas/rol del gestor. El rechazo final impide acreditar recepción; no inventar penalización de calidad.
- Código: [definitive_rejection.py:10](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/definitive_rejection.py#L10) · `explicit_message_refusal`; [message_workflow.py:52](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/message_workflow.py#L52) · `workflow_validation`.
- Criterios: 14,98.
- Resultado: Prueba completa PASA; rechazo reconocido, no aprobación.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### eeaa0d19e854

- Prueba: `tests/test_recado_delivery_review.py::test_delivered_recado_does_not_waive_other_quality_rules`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: Una confirmación humana de entrega/contacto forzaba valid=True aunque una negativa final posterior revocara la recepción. Confirmación individual de recepción/contacto no puede dispensar revocación final. No se altera ni descarta el registro humano.
- Cambio productivo: La confirmación de entrega conserva su registro y alcance, pero no anula una revocación final. Registrar human_delivery_conflicts_with_final_refusal.
- Código: [message_workflow.py:52](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/message_workflow.py#L52) · `workflow_validation`.
- Criterios: 48,98.
- Resultado: Prueba completa PASA; historial conservado y sin aprobación forzada.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

## Pagos

7 pasan / 5 fallan.

### 6b4c9fad9dbe

- Prueba: `tests/test_audio_audit_rules.py::test_positive_answer_to_past_payment_question_is_a_report_not_a_future_agreement`.
- Antes → después: **FALLA → FALLA**. ABIERTO_CONFLICTO_CONTRATO_CRITERIO.
- Causa: La expectativa conserva ACLARACION o la procedencia de política 28/10, en conflicto con CONVENIO para pago reportado con comprobante del criterio 72. El pago reportado de 5000 no cubre mínimo 11000; la solicitud de ticket no crea una promesa futura ni cobertura. La aserción inicial pide ACLARACION y otra posterior exige penalizar falta de negociación.
- Cambio productivo: Registrar procedencia CRITERIO_72_USUARIO_20261121 y evento PAGO_REPORTADO_CON_COMPROBANTE sin afirmar verificación bancaria. No falsificar ACLARA ni matches para hacer pasar la prueba.
- Código: [analytics_service.py:4584](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4584) · `calculate_basic_compliance`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [status_output_label.py:24](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/status_output_label.py#L24) · `corrected_status_label`.
- Criterios: 33,72; decisiones 15/11: cobertura mínima.
- Resultado: CONVENIO como seguimiento; cobertura insuficiente conservada; pytest FALLA.
- Pendiente: Conciliar formalmente expectativa histórica con criterio vigente/catálogo y contrato de calidad, sin modificar esta prueba ni imponer un dictamen artificial.

### d789165fd016

- Prueba: `tests/test_financial_review.py::test_confirmed_fact_resolves_only_its_discrepancy_without_changing_source`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: El estatus se resolvía antes de validar importes, plan final y confirmaciones financieras. La decisión retenía un bloqueo ya resuelto por evidencia válida. Confirmación financiera del plan final válida y ligada a fuente no despejaba su discrepancia; no se elimina otra incertidumbre ni se reescribe transcripción.
- Cambio productivo: Resolver estatus una sola vez después de aplicar revisión financiera ligada a fuente y validar plan/ventana de mora; conservar los bloqueos independientes. Reconocer respuestas de cantidad con «lo que traigo son».
- Código: [analytics_service.py:3840](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L3840) · `calculate_basic_compliance`; [current_payment_amounts.py:7](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/current_payment_amounts.py#L7) · `explicit_current_amounts`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`.
- Criterios: 48,112,120.
- Resultado: Prueba completa PASA; confirmación solo resuelve su alcance.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### 193292767136

- Prueba: `tests/test_financial_review.py::test_final_plan_confirmation_keeps_other_blockers`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: El estatus se resolvía antes de validar importes, plan final y confirmaciones financieras. La decisión retenía un bloqueo ya resuelto por evidencia válida. Variante name: el plan confirmado no debe eliminar el bloqueo independiente del nombre de salida; una vez éste se confirma debe decidirse con los hechos ya validados.
- Cambio productivo: Resolver estatus una sola vez después de aplicar revisión financiera ligada a fuente y validar plan/ventana de mora; conservar los bloqueos independientes. Reconocer respuestas de cantidad con «lo que traigo son».
- Código: [analytics_service.py:3840](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L3840) · `calculate_basic_compliance`; [current_payment_amounts.py:7](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/current_payment_amounts.py#L7) · `explicit_current_amounts`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`.
- Criterios: 48,49,155.
- Resultado: Prueba completa PASA; nombre sigue siendo control independiente.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### 519e8e72d388

- Prueba: `tests/test_followup_calibration.py::test_regression_approval_exception_requires_the_new_user_policy_and_evidence`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: La herramienta de regresión exigía una promesa futura a un seguimiento de pago ya reportado y no reconocía el criterio 72 vigente. El detector de regresiones rechazaba la excepción válida porque su propia invariante seguía exigiendo compromiso futuro a un pago previo.
- Cambio productivo: Reconocer seguimiento CONVENIO con pago reportado, comprobante, cobertura del mínimo, evidencia válida y sin instrucción nueva no aceptada. No dispensar privacidad, tarjeta, trato ni otros controles.
- Código: [regression_checkpoints.py:123](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/tools/regression_checkpoints.py#L123) · `verified_followup_approval`; [regression_checkpoints.py:51](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/tools/regression_checkpoints.py#L51) · `_reported_followup_without_new_commitment`; [analytics_service.py:4584](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4584) · `calculate_basic_compliance`.
- Criterios: 72; cobertura mínima 15/11.
- Resultado: Prueba completa PASA; excepción no dispensa otros filtros.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### 82f2e725a0c3

- Prueba: `tests/test_followup_calibration.py::test_user_policy_retains_original_status_in_verified_payment_followup`.
- Antes → después: **FALLA → FALLA**. ABIERTO_CONFLICTO_CONTRATO_CRITERIO.
- Causa: La expectativa conserva ACLARACION o la procedencia de política 28/10, en conflicto con CONVENIO para pago reportado con comprobante del criterio 72. Con Excel CONVENIO y pago900>=mínimo700 la calidad es APROBADO100. La prueba falla por exigir fuente de octubre y ACLARACION, no por exceso de REVISAR.
- Cambio productivo: Registrar procedencia CRITERIO_72_USUARIO_20261121 y evento PAGO_REPORTADO_CON_COMPROBANTE sin afirmar verificación bancaria. No falsificar ACLARA ni matches para hacer pasar la prueba.
- Código: [analytics_service.py:4584](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4584) · `calculate_basic_compliance`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [status_output_label.py:24](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/status_output_label.py#L24) · `corrected_status_label`.
- Criterios: 72.
- Resultado: CONVENIO / APROBADO,100; pytest FALLA por expectativa histórica.
- Pendiente: Conciliar formalmente expectativa histórica con criterio vigente/catálogo y contrato de calidad, sin modificar esta prueba ni imponer un dictamen artificial.

### 7897731e2c1b

- Prueba: `tests/test_followup_calibration.py::test_user_policy_retains_original_status_in_verified_payment_followup`.
- Antes → después: **FALLA → FALLA**. ABIERTO_CONFLICTO_CONTRATO_CRITERIO.
- Causa: La expectativa conserva ACLARACION o la procedencia de política 28/10, en conflicto con CONVENIO para pago reportado con comprobante del criterio 72. Excel NO DEFINE difiere de CONVENIO de seguimiento. El nombre sintético no tiene bloque TH/PP autorizado para corregir; no se puede afirmar matches=True conservando estatus diferente.
- Cambio productivo: Registrar procedencia CRITERIO_72_USUARIO_20261121 y evento PAGO_REPORTADO_CON_COMPROBANTE sin afirmar verificación bancaria. No falsificar ACLARA ni matches para hacer pasar la prueba.
- Código: [analytics_service.py:4584](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4584) · `calculate_basic_compliance`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [status_output_label.py:24](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/status_output_label.py#L24) · `corrected_status_label`.
- Criterios: 45,50,72.
- Resultado: CONVENIO / REVISAR,100; corrección de etiqueta no sustentada por este nombre; pytest FALLA.
- Pendiente: Conciliar formalmente expectativa histórica con criterio vigente/catálogo y contrato de calidad, sin modificar esta prueba ni imponer un dictamen artificial.

### 2b434f84c6b9

- Prueba: `tests/test_mora_payment_policy.py::test_two_installment_exception_is_applied_to_the_complete_decision`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: La aceptación expresa del plan completo no se vinculaba a sus importes anteriores y la clasificación repetía un límite fijo sin aplicar la ventana multipago validada. Dos exhibiciones dentro de sus ventanas: se exige aceptación del plan completo y se respeta excepción validada de política. Los plazos inválidos continúan rechazándose en los demás parámetros.
- Cambio productivo: Vincular aceptación propia del plan completo solo a términos explícitos anteriores sin conflicto; usar window_end de la política después de validar sus plazos. No completar desde Excel.
- Código: [operational_outcome_resolution.py:47](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/operational_outcome_resolution.py#L47) · `final_plan_amounts_accepted`; [analytics_service.py:3840](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L3840) · `calculate_basic_compliance`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`.
- Criterios: 63,65,112,120.
- Resultado: Prueba completa PASA; excepción validada sin ampliar política.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### 9fdda7460edc

- Prueba: `tests/test_reported_batch_regression.py::test_accepted_payment_does_not_require_literal_confirmo_convenio`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: Se reconocía aceptación/intención de pago pero no el importe explícito de la misma oferta; los extractores de compromiso e importe discrepaban. «Podemos contemplar su pago600 el23» con aceptación contextual quedaba NO DEFINE porque el extractor del importe no reconocía la misma oferta aceptada.
- Cambio productivo: Unificar aceptación contextual y extracción del importe de oferta inmediata; admitir «podemos contemplar su pago», con controles de rol, negación, citas, historia y objeto.
- Código: [payment_intent_frames.py:56](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/payment_intent_frames.py#L56) · `payment_frames`; [current_payment_amounts.py:7](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/current_payment_amounts.py#L7) · `explicit_current_amounts`; [payment_lifecycle.py:34](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/payment_lifecycle.py#L34) · `financial_response_events`; [conversation_evidence.py:390](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/conversation_evidence.py#L390) · `payment_commitment`.
- Criterios: 22,24,112.
- Resultado: Prueba completa PASA; monto aceptado sin frase literal confirmo convenio.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### 9a345d8d9315

- Prueba: `tests/test_reported_batch_regression.py::test_reported_deposit_amount_can_cover_the_minimum_without_a_new_promise`.
- Antes → después: **FALLA → FALLA**. ABIERTO_CONFLICTO_CONTRATO_CRITERIO.
- Causa: La prueba exige el estatus compuesto PAGO REPORTADO / ACLARACION, ausente del catálogo; reportar un depósito sin aceptación de envío de comprobante ni aclaración bancaria no prueba ese estatus. Importe1000 y mínimo750 se reconocen sin inventar fecha. La falla es la etiqueta compuesta exigida; no falta extracción de cobertura.
- Cambio productivo: Sin crear etiqueta artificial: conservar importe reportado y cobertura del mínimo, evento previo y REVISAR por resultado no confirmado.
- Código: [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [status_output_label.py:24](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/status_output_label.py#L24) · `corrected_status_label`.
- Criterios: 33,50,72.
- Resultado: Resultado sigue REVISAR; pytest FALLA por estatus compuesto no autorizado.
- Pendiente: Conciliar formalmente expectativa histórica con criterio vigente/catálogo y contrato de calidad, sin modificar esta prueba ni imponer un dictamen artificial.

### 1bf104e55442

- Prueba: `tests/test_review_backlog.py::test_negated_partial_warning_does_not_generate_partial_penalty`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: Una explicación intermedia del efecto del pago cortaba el vínculo entre la única oferta monetaria y la aceptación propia posterior. «De preferencia completo para que no se tome como parcial» no acepta otro importe ni justifica penalización por oferta parcial; antes perdía el nexo y seguía REVISAR.
- Cambio productivo: Permitir una explicación del mismo pago, excluyendo nueva cifra/fecha/objeto, pregunta, cita o turno de cliente. Mantener negaciones y cambios de términos como barreras.
- Código: [payment_lifecycle.py:34](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/payment_lifecycle.py#L34) · `financial_response_events`; [current_payment_amounts.py:7](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/current_payment_amounts.py#L7) · `explicit_current_amounts`; [conversation_evidence.py:390](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/conversation_evidence.py#L390) · `payment_commitment`.
- Criterios: 67,112.
- Resultado: Prueba completa PASA; explicación no inventa pago parcial ni borra términos.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### 50ccc8100657

- Prueba: `tests/test_review_backlog.py::test_regression_guard_requires_real_current_agreement_not_cached_approval`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: Se cambió el identificador de método de evidencia, rompiendo lectores de reportes y validadores que dependen del contrato existente. El validador verified_current_agreement no reconocía la evidencia renombrada; se conserva contrato y ahora la aceptación enlaza cifra real. No se acepta aprobación cacheada.
- Cambio productivo: Restituir COMPROMISO_ACEPTADO_CON_FECHA y registrar amount_confirmed_from_dialogue por separado; conservar la exigencia de monto aceptado.
- Código: [analytics_service.py:4480](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4480) · `calculate_basic_compliance`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [regression_checkpoints.py:210](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/tools/regression_checkpoints.py#L210) · `verified_current_agreement`.
- Criterios: 22,24,112.
- Resultado: Prueba completa PASA; requiere convenio actual con evidencia.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### 0232b94de1e7

- Prueba: `tests/test_ten_audio_review.py::test_listing_of_banks_does_not_make_other_authorized_options_unsafe`.
- Antes → después: **FALLA → FALLA**. ABIERTO_EVIDENCIA_INSUFICIENTE.
- Causa: El titular promete depositar antes de que se enuncien los 1200 pesos; tras la cifra no existe respuesta que la acepte. Los lugares son válidos, pero eso no acredita aceptación del monto. Se cuentan dos lugares autorizados y se conserva transfer_option_listing_only. No hay respuesta propia tras la cifra1200; no inferirla del deseo previo de depositar.
- Cambio productivo: Sin aprobar por inferencia: conservar conteo de lugares y ausencia de transferencia insegura; importe hablado no equivale a importe aceptado. Requiere audio/contexto adicional que pruebe aceptación.
- Código: [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [current_payment_amounts.py:7](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/current_payment_amounts.py#L7) · `explicit_current_amounts`; [quality_decision.py:20](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/quality_decision.py#L20) · `evaluate_quality`.
- Criterios: 22,24,112.
- Resultado: NO DEFINE / REVISAR,100; pytest FALLA.
- Pendiente: Aportar audio/contexto que confirme aceptación del importe; sin esa evidencia no aprobar.

## Checkpoints

4 pasan / 0 fallan.

### c3ae0e056c8c

- Prueba: `tests/test_checkpoint_review_import.py::test_import_keeps_all_calls_original_transcripts_runtime_paths_and_validations`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: El estatus se resolvía antes de validar importes, plan final y confirmaciones financieras. La decisión retenía un bloqueo ya resuelto por evidencia válida. El importador ya emparejaba por archivo y conservaba fuentes; fallaba la evaluación posterior del plan, no la copia de originales. Se comprueban las cuatro llamadas, rutas, revisiones, idempotencia y Excel.
- Cambio productivo: Resolver estatus una sola vez después de aplicar revisión financiera ligada a fuente y validar plan/ventana de mora; conservar los bloqueos independientes. Reconocer respuestas de cantidad con «lo que traigo son».
- Código: [analytics_service.py:3840](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L3840) · `calculate_basic_compliance`; [current_payment_amounts.py:7](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/current_payment_amounts.py#L7) · `explicit_current_amounts`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`.
- Criterios: 48,49,112,120.
- Resultado: Prueba completa PASA; 4 APROBADO sintéticos esperados; originales intactos.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### acb4b2887845

- Prueba: `tests/test_checkpoint_review_import.py::test_reordered_reviewed_calls_are_matched_by_filename`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: El estatus se resolvía antes de validar importes, plan final y confirmaciones financieras. La decisión retenía un bloqueo ya resuelto por evidencia válida. Reordenar llamadas no perdía asociación; el conteo 3 APROBADO +1 REVISAR provenía del plan mal resuelto. No se modificó el algoritmo de emparejamiento.
- Cambio productivo: Resolver estatus una sola vez después de aplicar revisión financiera ligada a fuente y validar plan/ventana de mora; conservar los bloqueos independientes. Reconocer respuestas de cantidad con «lo que traigo son».
- Código: [analytics_service.py:3840](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L3840) · `calculate_basic_compliance`; [current_payment_amounts.py:7](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/current_payment_amounts.py#L7) · `explicit_current_amounts`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`.
- Criterios: 48,49,112,120.
- Resultado: Prueba completa PASA; asociación por nombre y 4 evaluaciones conservadas.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### 4a443799d235

- Prueba: `tests/test_financial_review.py::test_checkpoint_reviews_persist_report_original_values_and_can_be_revoked`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: El estatus se resolvía antes de validar importes, plan final y confirmaciones financieras. La decisión retenía un bloqueo ya resuelto por evidencia válida. Revisiones persistían pero una evaluación seguía REVISAR por resolver estatus antes del plan confirmado. La prueba cubre revocación y valores Excel originales.
- Cambio productivo: Resolver estatus una sola vez después de aplicar revisión financiera ligada a fuente y validar plan/ventana de mora; conservar los bloqueos independientes. Reconocer respuestas de cantidad con «lo que traigo son».
- Código: [analytics_service.py:3840](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L3840) · `calculate_basic_compliance`; [current_payment_amounts.py:7](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/current_payment_amounts.py#L7) · `explicit_current_amounts`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`.
- Criterios: 48,49,157.
- Resultado: Prueba completa PASA; persistencia y revocación comprobadas.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### 0b1b344c0368

- Prueba: `tests/test_recado_batch_review.py::test_batch_does_not_force_approval_or_waive_other_controls`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: Una confirmación humana de entrega/contacto forzaba valid=True aunque una negativa final posterior revocara la recepción. Una confirmación humana de entrega en lote no acredita que la aceptación permanezca después de «no le voy a pasar el recado».
- Cambio productivo: La confirmación de entrega conserva su registro y alcance, pero no anula una revocación final. Registrar human_delivery_conflicts_with_final_refusal.
- Código: [message_workflow.py:52](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/message_workflow.py#L52) · `workflow_validation`.
- Criterios: 48,98.
- Resultado: Prueba completa PASA; no fuerza aprobación ni borra controles.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

## Dictaminación

0 pasan / 5 fallan.

### ef2a5b872cb2

- Prueba: `tests/test_fresh_batch_r49.py::test_initial_batch_separates_approved_review_rejection_and_severe_failure`.
- Antes → después: **FALLA → FALLA**. ABIERTO_CONFLICTO_CONTRATO_CRITERIO.
- Causa: La prueba exige NO_APROBADO por la sola negativa/incapacidad del tercero. La implementación vigente separa rechazo de recado y falta del gestor; el fixture deja una discrepancia de estatus sin código autorizado y, en algunas variantes, alertas independientes. Lote inicial sintetiza aprobado, rechazo de tercero, privacidad incierta y PEN003 confirmado. Se detiene al esperar NO_APROBADO para rechazo de tercero; PEN003 confirmado sigue FALLA_GRAVE.
- Cambio productivo: Sin cambio para forzar NO_APROBADO: conservar estatus SE NIEGAN A TOMAR RECADO, evaluación de etapas ejecutables y REVISAR cuando falta resolución sustentada. No convertir una conducta del tercero en incumplimiento del gestor ni inventar código de etiqueta.
- Código: [definitive_rejection.py:86](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/definitive_rejection.py#L86) · `definitive_rejection`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [status_output_label.py:24](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/status_output_label.py#L24) · `corrected_status_label`; [quality_decision.py:20](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/quality_decision.py#L20) · `evaluate_quality`.
- Criterios: 14,45,46,50.
- Resultado: Rechazos del tercero: REVISAR100; grave: FALLA_GRAVE0; pytest FALLA.
- Pendiente: Conciliar formalmente expectativa histórica con criterio vigente/catálogo y contrato de calidad, sin modificar esta prueba ni imponer un dictamen artificial.

### 6271a64e43b7

- Prueba: `tests/test_message_dialogue_r49.py::test_bare_no_to_positive_message_offer_is_an_explicit_refusal`.
- Antes → después: **FALLA → FALLA**. ABIERTO_CONFLICTO_CONTRATO_CRITERIO.
- Causa: La prueba exige NO_APROBADO por la sola negativa/incapacidad del tercero. La implementación vigente separa rechazo de recado y falta del gestor; el fixture deja una discrepancia de estatus sin código autorizado y, en algunas variantes, alertas independientes. Se reconoce «No,gracias» a oferta positiva; la prueba exige que ese hecho del destinatario sea por sí mismo NO_APROBADO.
- Cambio productivo: Sin cambio para forzar NO_APROBADO: conservar estatus SE NIEGAN A TOMAR RECADO, evaluación de etapas ejecutables y REVISAR cuando falta resolución sustentada. No convertir una conducta del tercero en incumplimiento del gestor ni inventar código de etiqueta.
- Código: [definitive_rejection.py:86](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/definitive_rejection.py#L86) · `definitive_rejection`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [status_output_label.py:24](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/status_output_label.py#L24) · `corrected_status_label`; [quality_decision.py:20](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/quality_decision.py#L20) · `evaluate_quality`.
- Criterios: 14,50.
- Resultado: SE NIEGAN A TOMAR RECADO / REVISAR,100; pytest FALLA.
- Pendiente: Conciliar formalmente expectativa histórica con criterio vigente/catálogo y contrato de calidad, sin modificar esta prueba ni imponer un dictamen artificial.

### e33c4f619200

- Prueba: `tests/test_message_dialogue_r49.py::test_explicit_refusal_is_closed_without_approving_or_clearing_security`.
- Antes → después: **FALLA → FALLA**. ABIERTO_CONFLICTO_CONTRATO_CRITERIO.
- Causa: La prueba exige NO_APROBADO por la sola negativa/incapacidad del tercero. La implementación vigente separa rechazo de recado y falta del gestor; el fixture deja una discrepancia de estatus sin código autorizado y, en algunas variantes, alertas independientes. Rechazo expreso reconocido. La variante posterior con posible divulgación no llega a ejecutarse por fallo del primer assert; seguridad independiente cubierta por otras pruebas, sin atribución acústica inventada.
- Cambio productivo: Sin cambio para forzar NO_APROBADO: conservar estatus SE NIEGAN A TOMAR RECADO, evaluación de etapas ejecutables y REVISAR cuando falta resolución sustentada. No convertir una conducta del tercero en incumplimiento del gestor ni inventar código de etiqueta.
- Código: [definitive_rejection.py:86](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/definitive_rejection.py#L86) · `definitive_rejection`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [status_output_label.py:24](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/status_output_label.py#L24) · `corrected_status_label`; [quality_decision.py:20](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/quality_decision.py#L20) · `evaluate_quality`.
- Criterios: 14,46,50; PEN003.
- Resultado: SE NIEGAN A TOMAR RECADO / REVISAR,100; pytest FALLA.
- Pendiente: Conciliar formalmente expectativa histórica con criterio vigente/catálogo y contrato de calidad, sin modificar esta prueba ni imponer un dictamen artificial.

### 0c3512348454

- Prueba: `tests/test_user_decisions_20261121.py::test_last_confirmed_payment_agreement_overrides_prior_refusal`.
- Antes → después: **FALLA → FALLA**. ABIERTO_CONFLICTO_CONTRATO_CRITERIO.
- Causa: El fixture 1PV fija llamada 21/11 y pago 25/11: cuatro días frente al límite autorizado de tres. Espera CONVENIO sin contemplar el criterio 65. Se respeta aceptación final sobre negativa anterior; el bloqueo es la fecha fuera de mora, no una negativa previa retenida.
- Cambio productivo: Sin cambio de regla: mantener evidencia de aceptación, NEGATIVA por fecha fuera de política y rechazo de calidad comprobado; no ampliar plazo ni reducir penalización.
- Código: [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [analytics_service.py:3840](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L3840) · `calculate_basic_compliance`; [definitive_rejection.py:86](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/definitive_rejection.py#L86) · `definitive_rejection`.
- Criterios: 26,27,65.
- Resultado: NEGATIVA por política / NO_APROBADO,70; pytest FALLA.
- Pendiente: Conciliar formalmente expectativa histórica con criterio vigente/catálogo y contrato de calidad, sin modificar esta prueba ni imponer un dictamen artificial.

### 371e2097bb29

- Prueba: `tests/test_user_decisions_round2_20261121.py::test_agreement_requires_amount_and_date`.
- Antes → después: **FALLA → FALLA**. ABIERTO_CONFLICTO_CONTRATO_CRITERIO.
- Causa: El fixture 1PV fija llamada 21/11 y pago 25/11: cuatro días frente al límite autorizado de tres. Espera CONVENIO sin contemplar el criterio 65. El parámetro tiene monto y fecha explícitos aceptados pero plazo fuera de política. Los otros parámetros sin cifra/fecha se conservan en sus resultados existentes.
- Cambio productivo: Sin cambio de regla: mantener evidencia de aceptación, NEGATIVA por fecha fuera de política y rechazo de calidad comprobado; no ampliar plazo ni reducir penalización.
- Código: [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [analytics_service.py:3840](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L3840) · `calculate_basic_compliance`; [definitive_rejection.py:86](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/definitive_rejection.py#L86) · `definitive_rejection`.
- Criterios: 22,24,27,65.
- Resultado: NEGATIVA por política / NO_APROBADO,70; pytest FALLA.
- Pendiente: Conciliar formalmente expectativa histórica con criterio vigente/catálogo y contrato de calidad, sin modificar esta prueba ni imponer un dictamen artificial.

## Reportes

1 pasan / 2 fallan.

### e9724fcdf01e

- Prueba: `tests/test_dialogue_status.py::test_excel_does_not_put_contact_type_in_the_detected_status_column`.
- Antes → después: **FALLA → PASA**. CORREGIDO_COMPROBADO.
- Causa: Se cambió el identificador de método de evidencia, rompiendo lectores de reportes y validadores que dependen del contrato existente. El Excel separaba correctamente tipo de contacto y estatus, pero esperaba el identificador público anterior del método.
- Cambio productivo: Restituir COMPROMISO_ACEPTADO_CON_FECHA y registrar amount_confirmed_from_dialogue por separado; conservar la exigencia de monto aceptado.
- Código: [analytics_service.py:4480](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4480) · `calculate_basic_compliance`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [regression_checkpoints.py:210](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/tools/regression_checkpoints.py#L210) · `verified_current_agreement`.
- Criterios: 45,112.
- Resultado: Prueba completa PASA; columnas y contrato de evidencia conservados.
- Pendiente: Ninguna para esta regresión sintética; no equivale a validación acústica.

### fc6722c87a20

- Prueba: `tests/test_short_batch_outputs_r53.py::test_short_normal_and_corrected_label_are_copied_once_and_reported`.
- Antes → después: **FALLA → FALLA**. ABIERTO_CONFLICTO_CONTRATO_CRITERIO.
- Causa: La prueba exige NO_APROBADO por la sola negativa/incapacidad del tercero. La implementación vigente separa rechazo de recado y falta del gestor; el fixture deja una discrepancia de estatus sin código autorizado y, en algunas variantes, alertas independientes. Las dos copias aprobadas cortas y etiqueta corregida se generan correctamente. Tercera llamada se espera en NO_APROBADO por rechazo del tercero y alerta de privacidad; sin incumplimiento propio probado no se fuerza ese destino.
- Cambio productivo: Sin cambio para forzar NO_APROBADO: conservar estatus SE NIEGAN A TOMAR RECADO, evaluación de etapas ejecutables y REVISAR cuando falta resolución sustentada. No convertir una conducta del tercero en incumplimiento del gestor ni inventar código de etiqueta.
- Código: [definitive_rejection.py:86](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/definitive_rejection.py#L86) · `definitive_rejection`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [status_output_label.py:24](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/status_output_label.py#L24) · `corrected_status_label`; [quality_decision.py:20](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/quality_decision.py#L20) · `evaluate_quality`.
- Criterios: 14,45,46,50,150.
- Resultado: Dos APROBADO_DURACION_MENOR; tercero REVISAR; pytest FALLA.
- Pendiente: Conciliar formalmente expectativa histórica con criterio vigente/catálogo y contrato de calidad, sin modificar esta prueba ni imponer un dictamen artificial.

### 8879649ffd54

- Prueba: `tests/test_status_resolution_r51.py::test_reported_payment_status_carries_original_evidence_for_output_correction`.
- Antes → después: **FALLA → FALLA**. ABIERTO_CONFLICTO_CONTRATO_CRITERIO.
- Causa: La expectativa conserva ACLARACION o la procedencia de política 28/10, en conflicto con CONVENIO para pago reportado con comprobante del criterio 72. Se conserva evidencia para corregir etiqueta, pero el test pide ACLARA. El criterio72 lleva a CONVENIO/PP, no a ACLARACION; calidad y reetiquetado separados.
- Cambio productivo: Registrar procedencia CRITERIO_72_USUARIO_20261121 y evento PAGO_REPORTADO_CON_COMPROBANTE sin afirmar verificación bancaria. No falsificar ACLARA ni matches para hacer pasar la prueba.
- Código: [analytics_service.py:4584](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4584) · `calculate_basic_compliance`; [analytics_service.py:4443](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/analytics_service.py#L4443) · `calculate_basic_compliance`; [status_output_label.py:24](../../../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/app/services/status_output_label.py#L24) · `corrected_status_label`.
- Criterios: 45,50,72.
- Resultado: CONVENIO / APROBADO_ETIQUETA_CORREGIDA,100; pytest FALLA.
- Pendiente: Conciliar formalmente expectativa histórica con criterio vigente/catálogo y contrato de calidad, sin modificar esta prueba ni imponer un dictamen artificial.
