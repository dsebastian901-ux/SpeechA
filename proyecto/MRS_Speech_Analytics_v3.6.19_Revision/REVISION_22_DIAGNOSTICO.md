# Revisión 22: bloqueos detectados en el lote pendiente

Se revisaron las reglas y la evidencia guardada de las 85 llamadas que r21 dejó
en REVISAR dentro de un lote de 95. No se realizó escucha humana ni nueva
transcripción: el checkpoint conserva el texto original, sus segmentos y tiempos.
No se considera una aprobación histórica como prueba de calidad.

## Correcciones

- Las secuencias telefónicas y números de convenio no sustituyen fechas de pago.
  Se reconocen confirmaciones como «el día 24», con contexto financiero.
- Una fecha de vencimiento o una hora no se convierte en saldo ni pago. Mencionar
  una tarjeta antes de introducir un importe no impide detectar el importe.
- Se reconocen cantidades dictadas sin «pesos», ligadas directamente a pago,
  saldo o monto, y formatos híbridos como «mil 216». Un artículo «un» no se
  interpreta como un saldo de un peso.
- Una reiteración de un pago ya hecho no constituye otro pago futuro. Tres
  cantidades distintas de propuestas no se suman automáticamente como un plan.
  Un importe expresamente incierto permanece pendiente de comprobante.
- Se reconoce la aceptación inmediata de una confirmación de monto y respuestas
  como «hoy lo hago». Dictar/repetir un teléfono no cancela ese compromiso.
  Una instrucción de nuevo pago sin aceptación conserva revisión, aunque antes
  se haya reportado un pago y se solicite comprobante.
- La identificación nominal puede incluir una presentación acotada de la empresa
  antes de «sí, dígame». No se convierte un traspaso de llamada en titular.
- «Para que no se tome como pago parcial» no es un acuerdo de pago parcial.
  La parcialidad real sin explicación conserva su penalización.
- Una lista de establecimientos puede responder a la pregunta anterior. La
  negación de un establecimiento no niega otra cláusula afirmativa. Se mantiene
  el mínimo de dos lugares y la validación independiente de transferencias.
- El resumen Excel distingue clasificación calculada, discrepancias de estatus
  detectadas por reglas y validación financiera; no duplica rótulos ambiguos.

## Resultado y alcance

Con 22 identificadores de nombre corregidos en una copia conforme a la instrucción
previa del usuario (usar numero_de_tarjeta de Excel), el lote queda en:

| Resultado | r21 | r22 |
|---|---:|---:|
| APROBADO | 8 | 11 |
| REVISAR | 85 | 82 |
| FALLA_GRAVE | 2 | 2 |
| ERROR técnico | 0 | 0 |

Las 8 aprobaciones anteriores permanecen. Las correcciones de nombres tienen
registro de antes/después: no cambian tarjeta de origen, estatus, saldos,
transcripciones ni validaciones financieras. No certifican lo ocurrido en audio.
El reporte privado de auditoría enumera las 85 llamadas iniciales y las acciones
necesarias para cada pendiente. Esos archivos privados no forman parte del código.

En las 82 pendientes se superponen 72 bloqueos de estatus, 48 de identidad,
27 financieros, 23 de privacidad, 22 de lugares de pago, 17 de duración menor de
60 segundos, 8 de datos bancarios y 4 de trato. Los conteos no se suman.
No se declaran 82 infracciones comprobadas ni se fuerzan aprobaciones por puntaje.

El reanálisis ordinario actualiza JSON y Excel; no renombra ni copia audios y no
corrige por sí solo los nombres de la relación. Para conservar las correcciones
entregadas, use el checkpoint corregido. Si se vuelve a usar un checkpoint viejo,
vuelven sus datos de origen y sus bloqueos de nombre.

## Validación reproducible

- Python 3.10: 692 pruebas, sin fallos; compilación de app y herramientas.
- 268 evaluaciones sobre cinco checkpoints históricos, contra la migración
  original y contra r21: cero violaciones de invariantes y cero retiros de
  penalizaciones sin causa documentada y comprobable.
- PEN009 conserva su valor de 10 puntos. Se retira únicamente donde se reconoce
  aceptación textual sustentada. Para nuevas aprobaciones con ese retiro, el
  auditor exige titular confirmado, estatus coincidente, evidencia, fechas,
  validación financiera y puerta común de aprobación; no basta un resultado
  cacheado. Se comprueban casos de manipulación de evidencia.
- Las 36 llamadas anteriores conservan sus 7 aprobaciones, las 13 correcciones
  previas de nombre y las confirmaciones de importes, saldo y acuerdo final.
- Las 95 filas del reporte principal se comparan celda por celda con su JSON.

Comando de regresión desde la aplicación, con datos y salidas fuera del repositorio:

```bash
python tools/regression_checkpoints.py \
  --input-dir /ruta/privada/pruebas_checkpoints \
  --baseline-source /ruta/privada/version_original/proyecto/MRS_Speech_Analytics_v3.6.19_Revision \
  --reviewed-changes tests/reviewed_r22_from_original.json \
  --output-dir /ruta/privada/regresion_r22
```

Para base r21, use su carpeta de aplicación y `tests/reviewed_r22_changes.json`.
`tests/reviewed_baseline_changes.json` se conserva sin cambios como historial.
Los documentos de cambios contienen hashes y reglas verificables; no contienen
nombres, tarjetas, transcripciones ni aprobaciones obligatorias.

No se afirma prueba acústica nueva, ejecución nativa de r22 en Windows ni cierre
de las 85 llamadas o de todos los 13 problemas. Se conserva Python 3.10, el mismo
Whisper y los lanzadores de Windows. No se requiere instalar otro transcriptor.
