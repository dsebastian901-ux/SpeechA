# r59: recuperación acústica, consenso y dictaminación

Trabajo sobre `fix/receipt-asr-mandas-envias-20261123`, base `8e57508`.
La aplicación conserva su versión r59; el validador de hechos se identifica
como `r59-hechos-20261124-v1`. La huella del código invalida dictámenes
guardados sin obligar a retranscribir una llamada completa.

## Cambios del programa

- El consenso compara hechos y su polaridad, no la igualdad de textos.
  Una tercera lectura requiere una discrepancia pertinente, un hecho
  pendiente recuperable o una lectura utilizable frente a otra degradada.
  Dos textos distintos sin información pertinente ya no bastan. La falta
  de voz no se corrige contando decodificaciones del mismo audio.
- Validadores separados para identidad, importe, fecha, compromiso sin fecha,
  comprobante, lugares, referencia, privacidad, ARCO, advertencia domiciliaria,
  ofensas, confrontación y hostilidad del interlocutor. Sus resultados son
  estados de evidencia; no reemplazan los dictámenes.
- La petición de comprobante corroborada puede resolver únicamente la duda
  de esa petición. El procedimiento ARCO completo y los lugares corroborados
  pasan por sus validadores específicos. Una coincidencia de importe/fecha
  aislada no acredita convenio ni cobertura del mínimo ni pago bancario.
- Una evidencia incompatible no aporta respaldo favorable. Si era necesaria
  y no existe prueba independiente suficiente, conserva revisión. Una lectura
  opcional inválida no provoca rechazo de una gestión demostrada por sí misma.
- Un calendario de varias parcialidades descrito como aceptado, cuyos importes
  y fechas no se han validado, conserva revisión. Una intención posterior sobre
  el canal de pago no puede ocultar ese calendario mediante una nueva etiqueta.
- La recuperación productiva también lee el cierre del audio y conserva riesgos
  de ofensa, advertencia, confrontación y divulgación. La hostilidad detectada
  no genera una excepción humana ficticia ni demuestra falta del gestor.
- Excel incorpora `EVIDENCIA_RELECTURAS`. La tarjeta de la llamada abre el mismo
  detalle completo: huellas, motor/modelo, ventanas, textos, calidad, consenso,
  atribución textual/conversacional, contradicciones, bloqueos y dictámenes.
- El reanálisis reutiliza lecturas vinculadas que ya validó; permite seleccionar
  otra carpeta local de audios y conserva sus entradas. `--no-acoustic` permite
  una validación explícita solo de reglas. La consola informa si hubo escuchas.
- Se conserva la celda B5 de `NOTA_REANALISIS` para la versión del motor.

No se modificaron los argumentos de las 33 llamadas de código a `add_penalty`.
El catálogo compartido conserva exactamente sus 26 entradas, convenios y
variantes. Los puntajes de las 79 llamadas permanecen sin cambio. Ningún
dictamen puede aprobar por debajo de 80, aunque un checkpoint antiguo solicite
un umbral inferior; un umbral superior continúa siendo vinculante.

## Caso prioritario y lote real

Los adjuntos contienen 79 llamadas cada uno y corresponden al mismo lote.
Sus identificadores y el detalle privado se comparan por archivo, nunca por fila.

| Resultado | Original recibido | Reanálisis recibido | Código corregido, solo reglas |
|---|---:|---:|---:|
| APROBADO | 6 | 6 | 6 |
| APROBADO_ETIQUETA_CORREGIDA | 5 | 6 | 5 |
| REVISAR | 39 | 38 | 39 |
| FALLA_MINIMA | 6 | 6 | 6 |
| NO_APROBADO | 4 | 4 | 4 |
| SIN_RELACION_EXCEL | 19 | 19 | 19 |

El único cambio frente al reanálisis recibido es
`APROBADO_ETIQUETA_CORREGIDA → REVISAR`, conservando 100 puntos. La conversación
describe tres parcialidades y el extractor devolvía `SIN_PLAN_EXPLICITO`.
La intención posterior sobre transferencia habilitaba NO DEFINE y la corrección
de etiqueta eliminaba el único hallazgo restante. La identidad mediante
«Exactamente» sí está demostrada por el texto primario; no se revierte esa
corrección. La causa para mantener revisión es validar el plan financiero.
La lectura antigua también tiene versión incompatible; eso no demuestra por
sí solo que el texto primario sea incorrecto ni obliga a rechazar la llamada.

Se analizaron ambos adjuntos con la base y con el código corregido, guardando
salidas separadas. Las otras 78 clasificaciones se conservan. Se mantienen los
19 casos sin relación de Excel: no son errores de Whisper ni aprobaciones.
Las dudas restantes no se convirtieron en infracciones comprobadas.

Sobre las primeras dos transcripciones de los 112 grupos guardados, el nuevo
selector recomendaría tercera lectura en 38 grupos; el resultado recibido
registra 110. Esto es **reproducción del selector con textos guardados**,
no 112 nuevas escuchas, ni medición de tiempo/precisión acústica. Las ventanas
adicionales de cierre también consumen procesamiento; no se promete una mejora
de tiempo total sin medirla.

Las salidas con nombres y conversaciones quedan únicamente en el espacio
privado de validación. Este directorio publica solo resultados agregados,
matriz de criterios y pruebas sintéticas. No incluye checkpoints ni Excel
de clientes, audios, credenciales o ejemplos personales.

## Pruebas y límites

Suite completa final: **3314 pasaron, 0 fallaron, 22 omitidas** (3336 casos).
Base: 3264 pasaron, 1 falló, 22 omitidas. Focal final: 89/89.

Los resultados finales y los casos individuales constan en `RESULTADOS.json`
y `MATRIZ_CRITERIOS.json`. Las pruebas históricas no se editaron ni debilitaron.
Las 40 pruebas solicitadas pasan antes y después. Se añadieron 49 casos.
El fallo previo de la suite general sobre B5 se corrigió en el código productivo.

No hay acceso a los 79 audios de las rutas de Windows desde este entorno.
No se ejecutó nueva inferencia real sobre ellos, ni escucha humana ni prueba
en Windows físico. Se ejercitaron fronteras controladas del modelo, decodificación
de WAV sintético y servicios reales de análisis, checkpoint, copia y Excel.
Los grupos sin atribución o corroboración suficiente siguen pendientes.
Los 780 archivos del manifiesto protegido de R57 permanecen idénticos.
No se activó Whisper Medium experimental ni se compiló EXE.

## Validación reproducible en Windows

Cerrar MRS antes de actualizar. Desde `C:\MRS_Desarrollo\SpeechA`, usar la misma
cuenta administradora local; las herramientas mantienen su autenticación.

```powershell
git switch fix/receipt-asr-mandas-envias-20261123
git pull --ff-only origin fix/receipt-asr-mandas-envias-20261123
$app = '.\proyecto\MRS_Speech_Analytics_v3.6.19_Revision'
Push-Location $app
& 'C:\MRS_Desarrollo\SpeechA\.venv\Scripts\python.exe' -m pytest tests/test_second_listening_20261123.py tests/test_context_audio_recovery.py tests/test_release_recovery_invalidation_20261123.py tests/test_holder_exactamente_20261123.py tests/test_context_fact_consensus_20261124.py -q
Pop-Location
```

Para validar las 79 con el Small ya instalado y sus audios locales, elegir una
carpeta de salida nueva. El primer comando pregunta por el checkpoint si no se
indica `--checkpoint`. No descarga modelos; conserva la transcripción original.

```powershell
& .\.venv\Scripts\python.exe "$app\tools\reanalyze_checkpoint.py" --output-dir 'C:\MRS_Desarrollo\Validacion_r59_integral_20261124'
```

Si los audios cambiaron de carpeta, agregar `--audio-dir 'RUTA_DE_AUDIOS'`.
Para una comparación exclusivamente de reglas, agregar `--no-acoustic`.
Los estados `AUDIO_LOCAL_NO_DISPONIBLE`, `MODELO_LOCAL_NO_DISPONIBLE` o errores
de relectura no acreditan una nueva escucha. El checkpoint y la hoja
`EVIDENCIA_RELECTURAS` muestran qué se pudo validar.

Comparar sin publicar los archivos:

```powershell
& .\.venv\Scripts\python.exe "$app\tools\compare_recovery_checkpoints.py" --before 'RUTA_CHECKPOINT_ORIGINAL' --after 'C:\MRS_Desarrollo\Validacion_r59_integral_20261124\checkpoint_reanalizado.json' --output 'C:\MRS_Desarrollo\comparacion_r59_integral_20261124.json'
```

La comparación exige los mismos identificadores, rechaza duplicados y no
sobrescribe entradas ni una comparación existente. No se debe aprobar una
transición únicamente por desaparecer un código: revisar su justificación,
la evidencia independiente y los bloqueos conservados.
