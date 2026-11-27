# Corrección de la ruta productiva de r67

Continuación de `codex/consolidacion-r67-20261127`, desde `1ea369e7ca0edd576ba765cbca3f458c2dfcd421`. No se crea r68, no se compila EXE y no se cambia el modelo principal. El trabajo previo de `auditoria/r67-20261127` describe ese commit de referencia; los resultados actuales se registran aquí.

## Defectos reproducidos y corrección

1. **Se mezclaban dos acuerdos.** Con tres pagos de 300 aceptados y un cierre posterior propio de 1,200 para el día 22, el extractor de hechos conservaba 900 para el día 23 y Analytics combinaba 900 con el día 22. `negotiation_resolution.resolve_negotiation` selecciona el objeto vigente para Analytics, extracción de hechos y selección focal. Los planes anteriores siguen en el texto e historial, pero no aportan importe/calendario a la obligación posterior. Se conserva la incertidumbre cuando una oferta de parcialidades incompleta puede referirse al pago confirmado; tampoco se pierde el formato coordinado «mil hoy y dos mil mañana». Se distinguen los términos propios, la recapitulación aceptada, la referencia a un plan completo y la confirmación de una parcialidad. Esta última actualiza únicamente el componente explícito si el calendario completo ya estaba aceptado; sin los otros términos no se inventa un acuerdo completo.
2. **Un plan sustituido seguía produciendo una supuesta falta de validación.** `unresolved_accepted_plan` y el extractor de parcialidades recibían toda la conversación, incluso después de identificar el nuevo acuerdo o una revocación. Ahora validan el ámbito financiero vigente. Una aceptación referencial conserva el contexto completo del plan y las confirmaciones humanas; no se recorta al último «sí». Los riesgos de privacidad, maltrato, fraude, amenazas y ofertas prohibidas siguen evaluando el texto completo.
3. **Problemas de comunicación se convertían en negativas financieras.** Dos clasificadores interpretaban el «no» de «no le escucho / no entiendo» como rechazo del pago. Eso creaba una contradicción artificial con los hechos recuperados por Medium. Ambos consultan `payment_reply_scope.communication_repair`. Una confirmación de audición no es reparación; un rechazo o compromiso financiero expreso conserva su prioridad.
4. **El lote añadía motivos de un dictamen intermedio al resultado final.** Aunque la decisión compartida ya se había resuelto, BatchService conservaba motivos de su antigua evaluación paralela. Se elimina esa segunda puerta: metadatos, motivo, checkpoint, carpeta y Excel se finalizan con la misma decisión compartida. Se conserva la medición y política de duración, incluido el tratamiento autorizado de llamadas cortas.

No se agregaron bloqueos para ocultar las discrepancias anteriores. No cambiaron los argumentos de las 33 penalizaciones. Las expectativas históricas de pruebas no se modificaron para obtener aprobaciones.

## Demostración de extremo a extremo

La interfaz inicia `BatchService.process_all` desde `app/ui/views/batch_view.py`; las pruebas ejecutan esa misma clase, cargando audios y Excel. No se usa un motor alterno de reanálisis para producir estos resultados.

`reproducir_flujo_completo.py` crea un proyecto y Excel sintéticos nuevos y ejecuta BatchService, relación de cuentas, recuperación, reglas, decisión, copia verificada del WAV, checkpoint y reportes de calidad/motivos de no pago. Sus salidas ASR están **explícitamente controladas** y los WAV contienen silencio: esta prueba verifica integración y no reconocimiento acústico. No sustituye Analytics, clasificadores, consenso, selección focal ni exportadores.

La comparación incluye 14 escenarios (11 REVISAR antes y 3 después, ocho resueltos sin alterar las ponderaciones): verifica pago válido, pago posterior al vencimiento, importe inferior al mínimo, revocación del plan, queja de atención, propuesta sin modificación, negativa inicial superada y concordancia/contradicción entre relecturas, además de promesa propia, recapitulación posterior y cambio de una parcialidad. Cada caso contrasta importe, fecha, clasificación, motivo, carpeta, checkpoint y Excel. Se conserva CONVENIO / FALLA_GRAVE / NEGOCIACION_INVALIDA cuando corresponde.

Además se ejecutaron dos grabaciones históricas **completas**, de 95.7 y 101 segundos, con Small real y Medium real instalado localmente. No se sustituyeron salidas ASR ni se alteró el plan de fragmentos. La relación de cuentas usa un Excel privado derivado de los campos históricos conservados del checkpoint; no se presenta como prueba con el Excel original adjunto. Se repitió además el reconocimiento completo con el código final congelado: cinco relecturas Medium, una de ellas tercera, sin errores de ejecución; su resultado insuficiente se registra como tal, no como pendiente. Las variaciones de ASR cambian fragmentos y tiempos, por lo que no se presentan como una medición comparativa de rendimiento. Posteriormente, las mismas transcripciones y lecturas genuinas se ejecutaron con el código final congelado mediante el procesamiento por lotes, conservando los originales presentes, sus huellas y las lecturas. Esto separa inferencia real de comparación lógica determinista. No constituye escucha humana ni validación bancaria del pago.

Los audios y cuentas de estos casos históricos no corresponden al lote de 23 del 27/nov. No se certifican aprobaciones recuperadas en ese lote ausente. Los datos reales permanecen fuera del repositorio y ZIP; los resúmenes públicos omiten sus importes y fechas financieras. La inferencia nueva puede variar sus transcripciones entre ejecuciones: por eso se compara el mismo ASR genuino con ambos motores, sin atribuir al código cambios causados por textos distintos.

## Reproducción

Desde el proyecto, con las dependencias existentes:

```bash
python -m pytest -q tests/test_product_pipeline_negotiation.py
PYTHONPATH=. python ../../auditoria/r67-flujo-real-20261127/reproducir_flujo_completo.py /tmp/mrs-proyecto-nuevo
```

La carpeta destino debe ser nueva. No modifica proyectos, cuentas ni audios anteriores. `PRUEBAS.json` registra los resultados ejecutados; `COMPARATIVO.json` y `FLUJO_REAL.json` separan entradas controladas, reconocimiento real y repetición de las transcripciones genuinas. No se probó Windows físico ni se realizó escucha humana.
