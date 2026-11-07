# Revisión 32: segundo bloque, aclaración y seguridad confirmada

## Procedencia y calidad

Se recibieron diez lecturas de las llamadas 4, 11, 29, 39, 56, 57, 65, 88, 90 y
96. El lector es r31, small CPU/int8, beam 5, marcas de palabra y cierre sin VAD.
El hash de origen corresponde al checkpoint final r30 anterior. Se comprobó que
las diez llamadas conservan exactamente sus archivos, datos de cuenta, textos,
segmentos y duraciones en el checkpoint final r31. Por eso se incorporan sobre
esa base más reciente, sin perder la aprobación de la 59 u otras correcciones.

Las diez lecturas terminaron sin errores de ejecución. El Excel de comparación
coincide con sus textos y cierres. La comprobación técnica anterior no marcaba
dos bucles de frases de dos palabras: los cierres de 4 y 39. La nueva evaluación
detecta repetición con compresión o alineación anómalas aunque no alcance la
velocidad extrema exigida antes. Se conservan los textos y se separan los
fragmentos no confiables, sin convertirlos en ofensas, rechazos o infracciones.
Una repetición breve y natural no se descarta por sí sola.

## Recepción y aclaración recuperadas

- **11:** pérdida de tarjeta reportada por el interlocutor, folio confirmado
  y seguimiento de resolución. Se reconoce ACLARACIÓN cuando el titular está
  identificado y no hay compromiso o negociación nueva que prevalezca. Un
  «perdí la tarjeta» aislado o un folio sin respuesta no bastan.
- **65:** «ok, yo le digo» como respuesta concreta al mensaje de retorno.
  Se exige contexto de contacto y se excluyen preguntas, citas e intervenciones
  conocidas del gestor. El parentesco y los demás controles siguen separados.
- **88:** espera inicial seguida de petición explícita de dictado y teléfono
  completo de diez dígitos para que otra persona se comunique. Esperar, agradecer,
  dictar un número incompleto o hablar de una cantidad de pago no prueban recado.

Las tres pasan de REVISAR a APROBADO conservando 100 puntos y sus penalizaciones.
No se certifican voces o cada palabra de Whisper por estas coincidencias textuales.

## Hallazgos confirmados por el usuario

### Llamada 56: monto divulgado al esposo

El usuario confirmó que el gestor proporciona el saldo al esposo de la titular.
La cifra aparece como respuesta a la pregunta de cuánto es el saldo; no repite
la palabra «saldo» en la misma frase. El detector ahora relaciona la pregunta
financiera con su respuesta, conserva el contexto y atribuye la voz únicamente
cuando está sustentada. Se excluyen preguntas de teléfono, folio, referencia,
fechas y reportes de pago. Una voz desconocida conserva REVISAR, nunca PEN003
automático. Se respeta la entrega posterior de la llamada al titular.

La confirmación de la 56 se guarda en `privacy_disclosure_confirmation`, con
contexto de la pregunta y fragmento ORIGINAL 81,88–83,88 s. Solo resuelve que el
gestor divulga ese importe a un tercero; no confirma el valor numérico como
saldo correcto de la cuenta ni atribuye todas las voces ASR. Resultado: PEN003
de 100 puntos, FALLA_GRAVE y puntaje cero. El texto original permanece intacto.

### Llamada 90: advertencia de recuperación en domicilio en 1PV

El usuario confirmó la advertencia del gestor sobre recuperación total en el
domicilio. La cuenta de Excel está en 1PV. Se incorpora ese patrón de amenaza
sin exigir la palabra literal «visita», conservando alcance en 1–2 PV. La voz
desconocida exige revisión; una voz del gestor sustentada activa PEN012 de 100.

El nuevo registro `home_warning_confirmation` queda ligado a archivo, cuenta,
mora, texto, segmentos, duración y evidencia. El fragmento ORIGINAL es
68,95–77,33 s; la lectura adicional ubica la frase entre 70,05 y 75,57 s. No se
cambia «domicil» por otra palabra en el ASR. El registro solo confirma la
advertencia escuchada y su actor. Resultado: FALLA_GRAVE y puntaje cero.

Ambos registros exigen dos hechos explícitos, no tienen opciones preseleccionadas,
persisten al reanalizar y dejan de validar si se altera el contexto o se revocan.
Un registro inválido mantiene revisión y no inventa una falta grave. Las ventanas
conservan el arreglo que evita quedar invisibles tras pedir el número de llamada.

## Resultado del lote

| Clasificación | r31 devuelta | r32 con las dos confirmaciones |
|---|---:|---:|
| APROBADO | 14 | 17 |
| REVISAR | 82 | 77 |
| FALLA_GRAVE | 7 | 9 |

Cambian solo 11, 56, 65, 88 y 90. Las otras 101 puntuaciones y todas las
penalizaciones anteriores se conservan; solo 56 y 90 pasan de 100 a cero por sus
nuevas faltas confirmadas. Se mantienen los datos originales, 103 moras, 31
nombres corregidos y las confirmaciones de la 10 y la 74. Hay quince lecturas
activas: las cinco anteriores y las diez nuevas. Se conserva el historial de
procedencia de la incorporación anterior.

Las 4, 29, 39, 57 y 96 del bloque siguen en revisión: las lecturas nuevas no
sustituyen por sí solas las evidencias faltantes ni autorizan su aprobación.
La 67 conserva el pendiente de estatus/recado ya documentado en r31.

## Aplicación local y comprobaciones

En la raíz del ZIP se incluyen `INCORPORAR_LECTURAS_BLOQUE.bat`,
`CONFIRMAR_DIVULGACION_A_TERCERO.bat` y `CONFIRMAR_ADVERTENCIA_DOMICILIO.bat`.
El README indica el orden de uso. Se incorpora sobre el último checkpoint
final r31 y, para cada confirmación ya dada por el usuario, se selecciona el
checkpoint generado en el paso anterior. Se generan copias y Excel nuevos.
No se retranscriben audios ni se descarga otro modelo para esas operaciones.

- 1.250 pruebas aprobadas, 61 nuevas y cinco pruebas de ventanas Tk reales.
- 268 evaluaciones históricas frente a r31: cero cambios de categoría, cero
  violaciones de seguridad y cero retiros de otras penalizaciones sin revisar.
- Los lotes anteriores de 95 y 36 conservan categorías, puntuaciones,
  penalizaciones y hechos confirmados: 13 y siete aprobaciones respectivamente.
- 9.785 celdas del reporte final de las 103 llamadas cotejadas con el JSON sin
  diferencias. Las diez filas del Excel de comparación recibido también coinciden.
- La validación se hizo con Python 3.10 y Tk gráfico real en Linux. No se ejecutó
  Whisper ni escucha acústica en la nube. Las voces de 56 y 90 proceden de las
  confirmaciones explícitas del usuario, no de diarización automática. Falta la
  devolución de las nuevas salidas r32 generadas en Windows.

Los datos, checkpoints, reportes y audios reales permanecen fuera del repositorio.
