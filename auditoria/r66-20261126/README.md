# r66 · escuchas y dictaminación

Base exacta: `034869e6bcba1d420667c3c9051f3ad64284d178`, rama de origen `codex/consolidacion-r65-20261125`.
Rama de trabajo separada: `codex/consolidacion-r66-20261126`.
Revisión: `3.6.19-r66-escuchas-dictaminacion-20261126-validacion`.

## Criterio confirmado y cambios funcionales

La instrucción posterior de la usuaria establece: **CONVENIO como dictaminación, FALLA_GRAVE como clasificación y NEGOCIACION_INVALIDA como carpeta operativa para un acuerdo firme fuera del plazo autorizado, incluido vencimiento**. Esta instrucción prevalece sobre la falta mínima por plazo del 23/nov y sobre la gravedad aún pendiente en el documento del 26/nov. Se mantienen las excepciones de calendario expresamente autorizadas; ninguna supera el vencimiento.

1. **Destino compartido de calidad y copias.** `classification_policy.operational_folder_name`, `grave_date_policy.grave_date_folder`, `BatchService._copy_classified_audio` y el reporte usan el mismo destino. Se incluye la vía preexistente PEN005, que antes podía terminar en FALLA_GRAVE como carpeta en vez de NEGOCIACION_INVALIDA. La clasificación de calidad y el estatus CONVENIO no se renombraron para resolver el destino. Las alertas de referencia/lugares conservan separación dentro de la carpeta operativa. Se verificó íntegro el catálogo anterior de 16 destinos.
2. **Fecha sin aceptación del importe.** El motor distingue una cifra propuesta de un importe aceptado. Una respuesta de fecha sin aceptar ese importe no acredita PEN005 ni una falta grave de convenio: conserva revisión. Se mantiene la penalización original cuando se cumplen sus condiciones; no se cambia su valor.
3. **Segunda y tercera escucha.** `collect` ejecuta los dos contrastes locales y una tercera lectura con encuadre acotado y beam distinto cuando discrepan los hechos, los importes aún no confirmados o el ASR original. Guarda motivo, texto completo, segmentos, modelo real, tiempos, huella de texto y consenso inicial/final. Si falta ubicación suficiente, puede ejecutar una ventana exploratoria limitada; esta no habilita el consumo automático de un plan financiero.
4. **No omitir la tercera obligatoria.** `validate` y `confirmed_fact` impiden consumir evidencia favorable si la tercera requerida no se completó con calidad suficiente. Las contradicciones explícitas de importe, negativa o condición permanecen; una mayoría 2–1 no las borra. Las alertas independientes siguen solicitando escucha aunque ya exista una falta grave u otro rechazo comprobado; esa escucha no exime el incumplimiento.
5. **Resolver evidencia financiera suficiente en producción.** `reviewed_payment_plan` reutiliza los eventos actuales de pregunta/respuesta de importe y fecha. Dos lecturas utilizables deben corroborar el mismo plan, vinculado al audio/cuenta/texto y al modelo Medium real; la tercera debe estar completada si corresponde. El contacto debe estar identificado y no puede haber riesgos, contradicciones, una negativa/condición de origen ni una ventana financiera requerida sin calidad suficiente. El importe no se completa desde Excel; una propuesta seguida de un sí aislado no basta. El plan entra en `AnalyticsService.calculate_basic_compliance` antes de obligaciones, validación financiera, política de fechas, penalizaciones y estatus. No se cambia el dictamen después de puntuar. Se registra atribución conversacional, sin declarar diarización acústica ni escucha humana.
**Control adicional del contexto recuperado.** `supplemental_rule_checks.financial_context_risks` vuelve a pasar el texto completo de las lecturas que aportan un plan por el motor MRS existente. No cuenta como faltas las omisiones propias de un recorte (apertura, lugares o comprobante ya acreditados en el original); sí bloquea el consumo favorable ante cuenta personal, referencia no validada, queja, retiro explícito de comprobante, liquidación no corroborada u otro contexto financiero incompatible. Un plan coincidente no permite omitir esas alertas. Se conserva la incertidumbre del emisor: una lectura no se transforma por sí sola en falta grave confirmada. Se amplía además el reconocimiento del estado «queda liquidada/saldada» con los mismos filtros de atribución, negación y relato anterior.

6. **Umbral exacto de 80.** Se evalúa el número antes de redondearlo: 79.999 no se transforma en aprobación. Un umbral solicitado inferior a 80 no reduce el mínimo. Un plan recuperado sigue sujeto al mínimo de pago, vencimiento, calidad y controles de seguridad.
7. **Trazabilidad por fragmento.** El Excel antes podía reutilizar el primer consenso de un objetivo en otros fragmentos del mismo objetivo. Ahora cada grupo conserva su consenso y cada intento su texto y resultado. `EVIDENCIA_RELECTURAS` incluye ASR original del fragmento, motivo de tercera, consenso inicial, huella y tiempo por lectura; `RESULTADOS` añade Carpeta operativa conservando las columnas finales anteriores. Cuando se consume un plan corroborado se muestra PLAN_DE_PAGO_CORROBORADO, sin confundir la corroboración con aprobación de calidad.

No se alteran los argumentos de las 33 llamadas a `add_penalty`, los datos de cuentas, las credenciales, roles, GUI ni el formato de autenticación local. Se conserva el modelo primario; Medium se usa como revisor local separado y sin descargar modelos en ejecución. No se incorpora MRS Academy. Las huellas y comprobaciones están en `INTEGRIDAD.json` y `SHA256_CODIGO.json`.

## Pruebas y límites

**Resultado final: 3550 pruebas aprobadas, 0 fallos y 22 omisiones por Windows/pantalla. Incluye 50 regresiones r66 nuevas.**

La base exacta ejecutó 3522 casos: **3483 pasaron, 17 fallaron y 22 se omitieron**. Los 17 fallos corresponden a expectativas anteriores de la gravedad de acuerdos fuera de plazo; no se presentan como 17 reparaciones del motor. Se trazan los cambios de expectativas autorizados en `CAMBIOS_EXPECTATIVAS.json`. Se mantienen sus comprobaciones de puntos, aceptación, fechas, seguridad y conservación de estatus. Además se actualiza la aserción literal del sello de versión a r66, por la solicitud expresa de una revisión nueva; se conserva el esquema de recuperación 2.

Las regresiones r66 verifican el motor completo, la copia conservando bytes originales, vencimientos con Excel CONVENIO y NO DEFINE, límites inclusivos y calendarios, aceptación incompleta, rechazo del importe insuficiente, tercera ausente/fallida, contradicciones no votables, ventana posterior inutilizable, trazabilidad de varios fragmentos y bloqueo bajo 80. `PRUEBAS.json` registra la ejecución completa final y las pruebas focalizadas reales, sin sumar ejecuciones repetidas como casos nuevos.

Se ejecutó además `BatchService.process_all` con un recorte histórico real de 8 segundos: ASR Small y tres decodificaciones Medium genuinas, sin dobles de salida ASR; checkpoint, Excel de calidad, motivos de no pago y copia con SHA-256 idéntico al original. Las tres lecturas tienen texto y huellas; se ejecutó una tercera por discrepancia con el ASR original. La clasificación permanece REVISAR. Es una prueba real de integración e inferencia, no una llamada completa ni una validación humana de calidad. Ver `MEDIUM_REAL.json`.

La resolución automática de planes financieros se verifica mediante fronteras ASR controladas y llamadas sintéticas, separadas de la inferencia real anterior. Las pruebas no representan nuevas aprobaciones de clientes.

El mismo reproducer ejecutado sobre la base y r66 demuestra estos cambios (`CASOS_CONTROLADOS_ANTES_DESPUES.json`):

| Caso controlado | Base 034869e | r66 |
|---|---|---|
| 79.999 puntos | APROBADO por redondeo a 80 | NO_APROBADO_MENOR_80 |
| Fecha sin aceptar importe | FALLA_GRAVE, 0 puntos | REVISAR, 100; aceptación pendiente |
| Plan propio corroborado | REVISAR, sin estatus confirmado | CONVENIO y APROBADO, 100 |
| Tercera requerida falla | Hecho favorable consumible | Hecho bloqueado y tercera pendiente |
| Dos fragmentos con consenso distinto | Se repetía el primero | Cada fragmento conserva su resultado |

Estos cinco son experimentos controlados, no inferencia ni dictámenes nuevos de clientes. El programa de reproducción está en este directorio; se ejecuta con el proyecto correspondiente en PYTHONPATH. La prueba de Medium real anterior usa otra entrada y se registra por separado.

Se contrastó también el checkpoint adjunto de 79 llamadas con la base 034869e. El comparativo privado conserva las 79 filas, hallazgos, estatus, puntos y fragmentos de segunda escucha. Sus audios originales no están disponibles: no se atribuyen a ese lote las lecturas del recorte histórico. Los conteos y límites están en `CHECKPOINT_REFERENCIA.json`. El resultado de este contraste no sustituye los cambios del código ni las pruebas de nuevos lotes.

**No se probó Windows físico ni se realizó escucha humana.** Las omisiones por CMD/Windows y pantalla Tk se detallan en el resultado final. No se compila un EXE ni se declara validación física de producción.

## Reproducción

Desde `proyecto/MRS_Speech_Analytics_v3.6.19_Revision`, con el Python y dependencias existentes:

```bash
python -m pytest -q tests/test_r66_listening_and_deadlines.py
python -m pytest -q --junitxml=resultado_r66.xml
```

Para usar una carpeta de código separada y preservar la de r65 se puede extraer el ZIP de código r66 en otra carpeta, o crear un worktree desde la nueva rama. Los modelos y archivos privados no se distribuyen en ese ZIP; pueden importarse desde sus carpetas locales mediante las herramientas existentes. Las cuentas siguen usando la ubicación local anterior, independiente de la revisión de código.

La verificación de audio debe ejecutarse con sus archivos reales disponibles y Medium importado. Una ventana planificada, SIN_AUDIO, SIN_MODELO, una inferencia fallida o una lectura sin vinculación no acreditan una escucha exitosa ni una aprobación.
