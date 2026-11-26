# Verificación de la consolidación r65 · 26/nov/2026

Rama: `codex/consolidacion-r65-20261125`. Base integrada: `ef1b5c6` (incluye `dd8362f`, `81506c4`, `d0783fe` y las cuatro pruebas nuevas de `test_checkpoint39_decision_guard.py`). Se conserva la revisión de aplicación `3.6.19-r65-consolidacion-20261125-validacion`; no se crea otra versión, etiqueta de publicación, instalador ni EXE.

## Adjuntos identificados y alcance comprobable

La usuaria aclaró que se refiere a los checkpoints adjuntos en este chat. `batch_checkpoint.json` contiene **79 llamadas, de las cuales 39 estaban REVISAR**; no es un lote de 39 registros. `checkpoint_reanalizado.json` contiene las mismas 79 transcripciones, con 38 REVISAR guardados. No se identificó un subconjunto independiente de 23; se revisaron las 79 entradas y todas sus revisiones y aprobaciones, por lo que no se excluye ninguna por esa diferencia de conteo.

Se ejecutó `reanalyze_checkpoint(..., acoustic=True, review_model='medium')` directamente sobre **ambos adjuntos**, con el mismo código y salidas privadas nuevas. Se compararon todas las filas con el dictamen guardado y con la ejecución de la base `ef1b5c6`. Los dos reanálisis producen los mismos dictámenes finales. `RESULTADOS_ADJUNTOS.json` registra hashes y conteos por archivo. El comparativo privado contiene ambas tablas completas, una hoja de las 39 revisiones originales y los intervalos pendientes. No se incorpora al repositorio ningún checkpoint, audio, Excel de clientes, transcripción ni credencial.

Se conservaron íntegros ambos adjuntos, todas las transcripciones, los datos financieros y las confirmaciones. En la copia de trabajo del batch se normalizaron 23 nombres finales por la autoridad ya autorizada de `numero_de_tarjeta`, con registro `output_name_normalization`; no se modificó el Excel ni la tarjeta. El otro adjunto ya traía esos nombres normalizados. Esta operación preexistente no se cuenta como una corrección nueva del motor.

Se encontraron 19533 archivos de audio locales; ninguno coincide por nombre con las 79 entradas. Cada reanálisis registró 50 necesidades de escucha sin audio, cero lecturas ejecutadas y cero errores de relectura. No son 50 llamadas REVISAR: el intento de recuperar contexto también precede a otras categorías. Un plan o un registro SIN_AUDIO no cuenta como segunda escucha.

## Resultado antes/después de los adjuntos

«Guardado» es el dictamen que contenía cada archivo recibido; «base» ejecuta realmente `ef1b5c6`; «corregido» ejecuta el código de esta consolidación. Los dos adjuntos tienen entradas financieras y confirmaciones equivalentes después de la normalización de nombres autorizada, pero mantienen su historial propio.

| Categoría | Batch guardado | Reanalizado guardado | Base integrada | Corregido, ambos |
|---|---:|---:|---:|---:|
| APROBADO | 6 | 6 | 14 | 15 |
| APROBADO_ETIQUETA_CORREGIDA | 5 | 6 | 2 | 4 |
| REVISAR | 39 | 38 | 36 | 33 |
| FALLA_MINIMA | 6 | 6 | 5 | 5 |
| NO_APROBADO_MENOR_80 | 0 | 0 | 2 | 2 |
| NO_APROBADO | 4 | 4 | 1 | 1 |
| SIN_RELACION_EXCEL | 19 | 19 | 19 | 19 |

De las **39 revisiones originales del batch**, se resuelven 12: **9 aprobadas y 3 rechazadas** (dos bajo 80 y una NO_APROBADO). Quedan 27 de esas 39 pendientes. Otras 6 entradas pasan a REVISAR: dos aprobaciones antiguas con términos de convenio sin corroborar y cuatro rechazos históricos con quejas previas y otras alertas pendientes de contexto, referencia o acuerdo. La queja previa no acredita por sí sola una falta del gestor actual; las demás dudas tampoco autorizan aprobar. Por eso el total final es 33; la disminución neta no representa todas las revisiones resueltas. En el otro adjunto, se resuelven también 12 de sus 38 revisiones y otras 7 entradas pasan a REVISAR.

Frente a la **base integrada ejecutada** se resuelven 3 revisiones adicionales con evidencia textual: dos propuestas rechazadas o con importe unilateral posterior se reetiquetan como NO DEFINE; una respuesta directa de importe y fecha confirma CONVENIO. Se comprueban las 19 aprobaciones resultantes: >=80, sin hallazgos activos REVIEW/PENDING_ALERT/CRITICAL, conservando los controles financieros y de seguridad. Las 16 aprobaciones de la base integrada se mantienen. Esto no certifica acústicamente las llamadas ni demuestra que las aprobaciones históricas guardadas fueran correctas. Se identifican por separado las que pasan a revisión, con causa y ventana, en el comparativo privado.

## Cinco casos solicitados

La correspondencia entre alias e identificador está únicamente en el comparativo privado.

| Alias de referencia | Base → corregido | Evidencia y límite |
|---|---|---|
| CASO-005 | REVISAR → REVISAR, 100 | Presión sobre bienes/cargos y plan fuera de política. No reducir a falta mínima ni atribuir voz/tono sin corroboración. Ventanas de presión: 259.54–309.21 y 468.63–496.45 s. |
| CASO-018 | REVISAR → REVISAR, 80 | Se elimina el falso importe proveniente de fragmentos del teléfono. Sigue faltando un importe actual atribuible al pago. Ventanas de negociación: 25.10–67.89, 261.51–318.69 y 445.35–454.91 s. |
| CASO-052 | REVISAR → REVISAR, 100 | El importe referido/citado y la respuesta deformada no prueban aceptación propia de los términos. Revisar 108.56–143.28 y 637.30–647.92 s. |
| CASO-067 | REVISAR → APROBADO, 80 | Pregunta actual, reparación breve, importe propio y respuesta de fecha consecutivos. CONVENIO entra antes de puntuar; se conserva la penalización existente por lugares. Validación textual, no escucha humana. |
| CASO-071 | REVISAR → REVISAR, 100→80 | Se recupera el CONVENIO. Se aplica la misma penalización -20 por lugares acreditados insuficientes; el recordatorio de comprobante deformado conserva incertidumbre, sin penalizar como omisión confirmada. Fragmento del comprobante: 365.92–383.46 s. |

Los tiempos son marcas ASR con margen, no una atribución acústica del emisor. El Excel privado contiene todos los intervalos, hallazgos y datos de ejecución; no se reconstruyen palabras que no estén en la fuente.

## Cambios productivos comunes

- `payment_lifecycle._payment_terms_responses`: asocia respuestas propias de importe y fecha dentro del mismo objeto de pago; admite una reparación breve, no cruza preguntas de contacto/comprobante ni acepta condiciones, citas, respuestas del gestor o fechas de vencimiento.
- `current_payment_amounts.explicit_current_amounts` y `AnalyticsService`: consumen esos eventos antes de determinar estatus, obligaciones y puntuación. La fecha procede de la respuesta, no de las alternativas de la pregunta.
- `payment_lifecycle.resolve_payment_events`: una elección de medio de pago no revoca por sí sola una decisión financiera firme.
- `balance_context_evidence.callback_dictation_spans` y `AnalyticsService`: distinguen contacto dictado tras introducción larga y conservan el mismo sistema de posiciones normalizadas; «…» ya no desplaza el teléfono hacia las cantidades.
- `quality_decision.evaluate_quality`: la guarda de convenio contradictorio sigue activa ante incertidumbre. Diferencia una negativa explícita final y un importe unilateral anunciado después de la decisión; estos no prueban un convenio aceptado.
- `treatment_evidence.asset_pressure_evidence`: centraliza presión sobre bienes/cargos con posición, contexto, negación/cita, rol y reporte previo. No usa una coincidencia global para confirmar una falta grave.
- `operational_script_evidence.receipt_request_evidence`: un recordatorio del documento sin acción inteligible queda pendiente. No acredita cumplimiento ni omisión; una solicitud clara resuelve la duda.
- `context_audio_recovery` y `medium_review_plan`: los nuevos bloqueos de convenio y presión se incluyen en recuperación financiera/seguridad, con evidencia y ventanas; presión requiere atribuir emisor.

No se cambian umbral de aprobación, argumentos de las 33 llamadas a `add_penalty`, usuarios, autenticación, permisos, GUI ni modelo primario. R57 y r64 se verifican con hashes: ver `INTEGRIDAD.json`.

## Pruebas y reproducción

La ejecución completa sobre la base integrada produjo **16 fallos, 3447 aprobadas y 22 omitidas**. Los 16 fallos provienen de la guarda excesiva de convenio contradictorio sobre propuestas no aceptadas; se conserva toda expectativa de las pruebas existentes. Las cuatro pruebas integradas de `test_checkpoint39_decision_guard.py` permanecen intactas. El resultado final y las omisiones se registran en `PRUEBAS.json`.

Desde `proyecto/MRS_Speech_Analytics_v3.6.19_Revision` con las dependencias del proyecto:

```bash
python -m pytest -q tests/test_checkpoint39_common_causes.py tests/test_checkpoint39_decision_guard.py
python -m pytest -q --junitxml=resultado_suite.xml
python tools/reanalyze_checkpoint.py --checkpoint /ruta/privada/checkpoint.json --output-dir /ruta/privada/salida_nueva --audio-dir /ruta/privada/audios --review-model medium
```

La última orden necesita el checkpoint y los audios reales para las escuchas; no los descarga ni crea evidencias humanas. Usar una carpeta de salida nueva. El reanálisis no sustituye la transcripción original ni copia/reclasifica físicamente audios.

Prueba real adicional: `BatchService.process_all` sobre un recorte histórico de 8 segundos con Small y Medium locales genuinos, sin dobles de salida ASR. Se ejecutan tres decodificaciones Medium sin errores, se conserva Small como primario, se genera checkpoint, Excel de calidad y motivos de no pago, y la copia conserva SHA-256 del WAV original. Es integración del flujo real; no es una llamada completa ni uno de los cinco audios solicitados. Ver `MEDIUM_INTEGRACION.json`.

No se probó Windows físico, no se hizo escucha humana y las pruebas gráficas que necesitan pantalla pueden quedar omitidas. Los dos checkpoints adjuntos y sus 79 llamadas sí se reanalizaron completamente; la corroboración acústica de los pendientes requiere sus audios originales. No se declara liberación para producción ni se genera otra versión mientras siga abierta esa comprobación.
