# Continuación de auditoría r58

Base: `b630ae9`. Rama: `codex/auditoria-integral-r58-20261120`. Fecha de entrega: 21/nov/2026.

Los 16 criterios parciales cierran su contrato de código con regresiones específicas. Esto no certifica la exactitud acústica de cada llamada. De los cinco no verificables, S.12 se resuelve mediante comprobación arquitectónica; cuatro conservan el límite de audio/validación humana o Windows físico.

Pruebas finales: **3104 aprobadas, 0 fallidas, 0 omitidas**, sin cambiar el código durante esa ejecución. Las **94 regresiones nuevas** pasan: en la base fallaban 64 y pasaban 30.

El comparativo de **2327 evaluaciones históricas** arroja **0 cambios de dictamen y 0 cambios de puntaje**. Por tanto, esta entrega no demuestra una reducción de REVISAR en ese corpus ni una mejora de precisión acústica. Sí reproduce y corrige los fallos de código descritos abajo, en el programa normal.

No se cambiaron umbral de aprobación, penalizaciones, prioridad de fallas graves ni la distinción entre incumplimiento confirmado e incertidumbre.

## Resultados por criterio

### 01.05 — CORREGIDO en el alcance del código

Prueba adicional con cinco estatus Excel y diálogo insuficiente: ninguno acredita identidad ni aprobación. No se cambió este criterio ni se usó Excel como evidencia de voz.

Código: `app/services/analytics_service.py:AnalyticsService.calculate_basic_compliance`. Prueba: `tests/test_partial_criteria_r58.py::test_excel_label_never_substitutes_for_missing_dialogue`.

### 02.03 — CORREGIDO en el alcance del código

Cierre por prueba adicional: confirmación explícita vinculada a archivo/contexto; cambio del texto invalida la confirmación. El parentesco no asigna hablante ni exime seguridad.

Código: `app/services/family_contact_review.py:validate_family_confirmation`. Prueba: `tests/test_partial_criteria_r58.py::test_family_confirmation_is_invalidated_by_context_and_never_assigns_a_voice`.

### 03.04 — CORREGIDO en el alcance del código

Negación e hipótesis se limitan a la cláusula financiera. Conflicto entre roles explícitos conserva REVISAR. La divulgación previa a un tercero no desaparece al incorporarse después el titular.

Código: `app/services/conversation_evidence.py:assess_privacy`. Prueba: `tests/test_partial_criteria_r58.py::test_unrelated_negation_does_not_hide_a_confirmed_disclosure`.

### 04.03 — CORREGIDO en el alcance del código

Conserva turnos explícitos incluso sin punto ASR y límites entre segmentos con roles semánticos distintos. Contradicciones entre etiqueta y segmento quedan NO DETERMINADO. SPEAKER_00/01 no se convierten en personas.

Código: `app/services/conversation_evidence.py:_sentence_evidence`. Prueba: `tests/test_partial_criteria_r58.py::test_semantic_segments_preserve_two_roles_inside_one_asr_sentence`.

### 04.07 — CORREGIDO en el alcance del código

Dos dictados literales completos e iguales de diez dígitos pueden extraerse. Ecos parciales, concatenaciones de fragmentos y dictados completos contradictorios no completan un teléfono.

Código: `app/services/payment_reference_validation.py:callback_numbers`. Prueba: `tests/test_partial_criteria_r58.py::test_complete_phone_repeated_as_two_full_numbers_is_not_partial_echo`.

### 06.03 — CORREGIDO en el alcance del código

Una petición anterior de INE no acredita un comprobante de línea expresamente excluido por una instrucción posterior. Se conservan derechos ARCO expresos, procedimiento, correo oficial y ambos documentos.

Código: `app/services/arco_validation.py:document_requests`. Prueba: `tests/test_partial_criteria_r58.py::test_arco_negated_line_proof_is_not_credited_to_an_earlier_ine_request`.

### 07.01 — CORREGIDO en el alcance del código

Separación de oferta vigente y relato previo. Una opción negada no cancela otras autorizadas afirmadas después. No se cuentan marcas del relato, duplicadas ni negadas; se conserva la penalización de 20 puntos.

Código: `app/services/conversation_evidence.py:payment_places`. Prueba: `tests/test_partial_criteria_r58.py::test_current_payment_venues_are_not_hidden_by_an_old_report`.

### 08.02 — CORREGIDO en el alcance del código

Se excluyen hipótesis y negaciones de la misma amenaza, relatos y venta de bienes por el cliente. Se detecta una amenaza directa nueva después de un relato anterior. No se relajan las restricciones 1–2 PV.

Código: `app/services/context_rules.py:prohibited_threat`. Prueba: `tests/test_partial_criteria_r58.py::test_negated_hypothetical_or_reported_asset_threat_is_not_direct_threat`.

### 09.02 — CORREGIDO en el alcance del código

Catálogo único para ASR primaria y lecturas adicionales, con variantes acotadas del cierre. Las relecturas sin hablante generan alerta; no se convierten en escucha humana ni infracción confirmada por sí solas.

Código: `app/services/treatment_evidence.py:offensive_language_phrases`. Prueba: `tests/test_partial_criteria_r58.py::test_additional_asr_uses_same_offensive_tail_variants_without_inventing_speaker`.

### 10.01 — CORREGIDO en el alcance del código

Se detecta «se interpreta como (un) chisme» y se bloquea aprobación. Negación, cita, pregunta y expresión del interlocutor no se convierten en trato despectivo directo del gestor.

Código: `app/services/treatment_evidence.py:dismissive_message_evidence`. Prueba: `tests/test_partial_criteria_r58.py::test_dismissive_interpretation_of_the_message_is_detected`.

### 11.04 — CORREGIDO en el alcance del código

Un segmento repetido con otra marca temporal ya no reutiliza la misma aparición del texto para fabricar un intervalo. Conserva separación entre indicio ASR y silencio acústico; inicio/cierre y límite 65 s sin cambios.

Código: `app/services/call_wait_evidence.py:_timed_units`. Prueba: `tests/test_partial_criteria_r58.py::test_wait_segments_must_align_to_distinct_source_occurrences`.

### 12.01 — CORREGIDO en el alcance del código

El relato de otra persona, una idea histórica o hipótesis no generan una aceptación nueva. Una decisión personal posterior explícita mantiene su propio ámbito y orden.

Código: `app/services/payment_lifecycle.py:payment_decision_events`. Prueba: `tests/test_partial_criteria_r58.py::test_reported_or_hypothetical_payment_is_not_a_new_acceptance`.

### 12.05 — CORREGIDO en el alcance del código

Comprobante de titularidad/propiedad de línea no acredita comprobante de pago. Conserva ticket/ticker/expectativa, canal y envío reportado por separado. La retirada expresa posterior cancela la petición anterior y deja evidencia auditable.

Código: `app/services/operational_script_evidence.py:receipt_request_evidence`. Prueba: `tests/test_partial_criteria_r58.py::test_final_explicit_receipt_waiver_cancels_prior_request`.

### 12.10 — CORREGIDO en el alcance del código

Lectura fallida o lista de importes incoherente invalida la recuperación aunque el texto contenga un número. Coincidencia de dos relecturas sigue siendo evidencia ASR, sin consultar Excel para fabricar el importe.

Código: `app/services/asr_amount_recovery.py:validated_entries`. Prueba: `tests/test_partial_criteria_r58.py::test_failed_recovered_amount_attempt_cannot_be_used_even_if_it_contains_a_number`.

### 13.11 — CORREGIDO en el alcance del código

Tres proyectos nuevos con salida ASR controlada comprueban las correcciones en BatchService, copias y ambos reportes. Además se ejecutan Whisper local real y lote normal con ASR guardado; no es un parche por fila de checkpoint.

Código: `app/services/batch_service.py:BatchService.process_all`. Prueba: `tests/test_normal_pipeline_partial_r58.py::test_new_normal_batch_uses_shared_corrected_extractors`.

### S.10 — CORREGIDO en el alcance del código

Alta y permisos individuales accesibles para la administradora. Pruebas GUI de crear/editar, ocho subconjuntos de funciones y tres escalas Tk. Operadores no obtienen administración, ajustes ni revisiones alternas.

Código: `app/ui/access_dialogs.py:users_window`. Prueba: `tests/test_individual_permissions_gui.py::test_admin_controls_remain_inside_resizable_window_at_different_tk_scaling`.

## Permisos individuales

La administradora conserva acceso total. Cada operador puede tener cualquier subconjunto de lotes, dashboard y reportes, incluso ninguno; puede autenticarse sin permiso de lotes. Las cuentas antiguas conservan identificadores, credenciales y funciones al migrar. El catálogo firmado versión 2 impide escalación y vuelta a un esquema que restaure permisos. Se comprueba autorización al ejecutar acciones, no solo al mostrar botones.

En el primer inicio r58 copia y valida el perfil local antiguo en `MRS_Speech_Analytics/acceso_r58`; no sobrescribe el perfil `acceso` de R57. Las modificaciones de permisos son transaccionales; fallos de escritura no publican un catálogo parcial. Catálogo alterado o actualizado revoca sesiones. Exportación USB no lleva clave privada. En equipos separados, los cambios se aplican al importar la actualización por USB.

Administración: **Usuarios y permisos → Nuevo operador / Permisos individuales → Guardar**. Después, **Exportar USB** e importar el catálogo en los demás equipos. Dashboard/reportes sin lotes tienen **Consultar proyecto**, sin permiso para crear o modificar proyectos.

## Pendiente fuera del contrato de código

- **05.03: NO VERIFICABLE.** Extracción y discordancia de referencia de 16 dígitos cubiertas por regresión sintética; no equivalen al caso histórico concreto. Requisito pendiente: Vincular inequívocamente el audio original a esa referencia histórica y validar los 16 dígitos mediante escucha humana.
- **09.04: NO VERIFICABLE.** Catálogo común y variantes de cierre probados en ASR primaria/adicional. Se ejecutó Whisper real en dos audios; no son gold de todos los insultos históricos. Requisito pendiente: Audio original completo, incluido el cierre, y validación humana del contenido y emisor en los casos históricos.
- **10.04: NO VERIFICABLE.** Vinculación por hash a audio disponible para nuevas revisiones y compatibilidad con revisiones antiguas; rechazo al reemplazar audio. Requisito pendiente: Escucha humana del tono y profesionalismo. No hay clasificador acústico validado que lo sustituya.
- **S.05: NO VERIFICABLE.** Runtime Windows y GUI bajo Wine; no certifican Windows físico. Requisito pendiente: Instalación y arranque en Windows físico, usuario local real de prueba, controladores/DPI y traslado USB físico.
- **S.12: CORREGIDO.** Identidad de clases e importaciones, servicio canónico offline, inventario de módulos vacíos y eliminación de implementación de respaldo alternativa en favor de compatibilidad. Requisito pendiente: Ninguna escucha para este cierre arquitectónico. Los módulos vacíos permanecen identificados como no implementados.

R57: 780 archivos protegidos sin cambios. No se publican audios, checkpoints, Excel de clientes, contraseñas, catálogos reales ni claves. El ZIP es código fuente con pruebas; no es un EXE ni un instalador nuevo.

Para reproducir: `python auditoria/ejecutar_pruebas.py --output <directorio-nuevo>`. Con Linux sin pantalla, agregar `--xvfb <ruta-a-Xvfb>`. `PRUEBAS_ANTES_DESPUES.csv` permite comprobar cada una de las 94 regresiones. `MATRIZ_BASE_B630AE9.json` conserva la matriz de partida.

## Procesamiento real y alcance de plataforma

- 175 audios en lote normal con ASR guardado: dictámenes y puntajes coinciden con la evaluación directa; copias SHA-256 y reportes de calidad/motivos de no pago verificados. No es transcripción nueva.
- Dos audios distintos con Whisper local real desde proyectos nuevos en Linux, conexiones de red bloqueadas: ambos REVISAR, 100 puntos; copias y ambos reportes verificados. No se atribuye por ello precisión acústica ni reducción de revisión.
- Uno de esos audios ejecutado además con binarios Windows bajo Wine: Whisper local, reportes y copia verificados; REVISAR, 100 puntos. Se usó OMP_NUM_THREADS=1. No es una tercera grabación distinta ni prueba de rendimiento por defecto.
- GUI Windows bajo Wine: alta inicial, acceso, edición de permisos individuales, importación USB con cuenta restringida, dashboard, reportes y rutas administrativas verificadas. Las cuentas usadas son sintéticas.
- El arnés de Wine emitió avisos Tcl de callbacks pendientes al destruir varias raíces Tk; completó sus verificaciones y terminó con código 0. Sigue pendiente verificar el ciclo de uso en Windows físico.

`CRITERIOS_CONTINUACION.csv/json` contiene el antes/después de las pruebas primarias de cada uno de los 16 criterios. Los dos criterios que ya pasaban esas pruebas se cierran por evidencia adicional de su contrato existente; no se presenta eso como una modificación nueva del algoritmo.
