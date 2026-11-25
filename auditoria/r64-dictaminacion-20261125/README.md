# r64 — correcciones del motor de dictaminación

Base: `e8d2da8e78d8d411950598265221675295054769`, última punta remota obtenida de
`fix/receipt-asr-mandas-envias-20261123`. Versión nueva:
`3.6.19-r64-dictaminacion-20261125`.

Se modifican servicios productivos compartidos por el procesamiento de audios
nuevos y la evaluación de transcripciones guardadas. No hay decisiones por
nombre de archivo, número de llamada, identidad de cliente o cuota de aprobados.
La matriz `CAMBIOS_POR_CAUSA.csv` relaciona cada causa con función, cambio y
regresión. Las sondas sintéticas permiten cotejar la misma entrada contra el
commit base y r64; no son transcripciones de clientes.

## Resultado comprobado sobre las 79 transcripciones

El último checkpoint adjunto disponible es r59 y contiene **38 REVISAR**.
No se dispone del checkpoint específico que habría producido 34. La búsqueda
local también encontró derivados anteriores, sin un checkpoint nuevo con ese
resultado. No se afirma haber reproducido ese archivo ausente.

Para aislar las correcciones se ejecutó primero el motor del commit base sobre
ese mismo adjunto; luego r64 sobre idénticas transcripciones y relaciones.

| Dictamen | Motor base GitHub | r64 |
|---|---:|---:|
| REVISAR | 38 | 30 |
| APROBADO | 7 | 9 |
| APROBADO_ETIQUETA_CORREGIDA | 8 | 9 |
| NO_APROBADO | 0 | 4 |
| NO_APROBADO_MENOR_80 | 1 | 2 |
| FALLA_MINIMA | 6 | 6 |
| SIN_RELACION_EXCEL | 19 | 19 |
| Total | 79 | 79 |

**8 REVISAR resueltos: 3 aprobados y 5 rechazados.** Cuatro rechazos son por
queja de atención corroborada en la conversación, conforme al criterio MRS;
no prueban maltrato del gestor actual. El otro activa las penalizaciones ya
existentes al identificar correctamente al titular. Las alertas independientes
se conservan visibles. Los otros 30 mantienen evidencia insuficiente o
contradictoria; no se han convertido en fallas comprobadas ni en aprobaciones.

La comparación directa contra el adjunto r59 es distinta de la comparación
contra el motor GitHub: ese adjunto tenía 12 aprobaciones, mientras el motor
base ya produce 15; r64 produce 18. Respecto del adjunto hay una aprobación que
pasa a revisión al detectar una advertencia de cobro en bienes sin atribución
segura. Los dos comparativos se entregan por separado para no atribuir a r64
mejoras que ya estaban integradas en GitHub.

Los puntajes pueden cambiar cuando la identificación corregida hace aplicables
reglas que antes se omitían. Las 33 llamadas a `add_penalty` del motor conservan
exactamente los mismos argumentos AST que el commit base. No se redujeron sus
valores ni el umbral mínimo de 80. Los 18 aprobados carecen de hallazgos REVIEW,
PENDING_ALERT o CRITICAL y de faltas graves confirmadas en la evidencia guardada.
Eso no acredita escucha humana ni la exactitud acústica de las transcripciones.

## Pendientes y segunda escucha

El comparativo privado contiene una fila por cada audio; las hojas
`PENDIENTES_REVISAR` y `FRAGMENTOS_MEDIUM` detallan hallazgo, evidencia faltante y
marcas ASR. El reporte productivo añade `SEGUNDA_ESCUCHA_MEDIUM` tanto al reporte
normal del lote como al de evaluación de transcripciones guardadas.

Se generan **176 ventanas sobre 36 llamadas**: incluyen las 30 REVISAR y las
alertas pendientes que sobreviven a otros cierres no aprobados. Cada intervalo
se deriva de segmentos ASR o de la apertura/espera señaladas; no es una marca
precisa de palabra ni prueba de silencio. Las esperas incluyen todo el hueco
ASR y contexto. El módulo conserva `NO_EJECUTADO` y no activa Medium ni descarga
modelos. Si otra entrada carece de tiempos fiables, informa que no puede ubicar
el fragmento; no inventa segundos. Las 19 relaciones de Excel ausentes requieren
las filas del Excel original usado en ese lote, cuya ruta guardada no es
accesible en este entorno, y no se sustituyen por evidencia acústica.

No están disponibles los 79 archivos de audio en este entorno. Por tanto, no
se ejecutó Whisper Medium real ni escucha humana; las decisiones se contrastan
con el texto y metadatos existentes. En los 79 resultados se conservaron íntegros
`result` y la evidencia ASR guardada de origen. No se movieron ni copiaron audios.
Los checkpoints originales conservan sus hashes. La cola de un checkpoint
intermedio conserva también la ausencia original de claves opcionales.

## Pruebas y preservación

Los resultados reales, tiempos, omisiones y fallos antes/después están en
`PRUEBAS.json`. El punto de partida completo arrojó 47 fallos, 3301 pruebas
aprobadas y 22 omitidas. La suite completa posterior terminó con **3388 aprobadas,
0 fallos y 22 omitidas**. La verificación focal final pasó **148/148**; incluye
un caso adicional para comprobar que el texto de la alerta en bienes no inventa
una mora de 1–2 PV. Esa corrección de presentación fue posterior al inicio
de la suite global y se regeneraron las 79 evaluaciones después de ella. Se añadió `test_integrated_dictamination_r64.py` con
casos sintéticos de las causas corregidas y controles negativos. La única
expectativa existente modificada es el literal de versión en
`test_release_recovery_invalidation_20261123.py`, para comprobar r64; no se
alteraron expectativas de dictaminación, puntuación ni seguridad.

Se mantienen GUI, usuarios, permisos, autenticación local, Whisper, lotes,
reetiquetado y reportes. Las pruebas automatizadas no sustituyen una ejecución
de instalación y GUI en Windows físico. No se compiló EXE. Los 780 archivos
protegidos de R57 coinciden con su manifiesto previo. No se incluyeron en el
commit audios, checkpoints, Excel de clientes ni credenciales.

## Reproducir

Desde `proyecto/MRS_Speech_Analytics_v3.6.19_Revision`, con las dependencias de
pruebas instaladas:

```text
python -m pytest tests -q --junitxml=resultado-suite.xml
python -m pytest tests/test_integrated_dictamination_r64.py -q
python -m compileall -q app tools
```

La sonda `SONDA_SINTETICA.py` se puede ejecutar con ese directorio en
`PYTHONPATH`, tanto contra el commit base como contra r64. Para reproducir el
lote privado se usa la API productiva
`reanalyze_checkpoint(checkpoint, carpeta_nueva, acoustic=False)` y
`compare_checkpoints(base, nuevo, salida_nueva)`. Se requieren los adjuntos
privados originales; deliberadamente no se guardan en Git.
