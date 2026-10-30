# MRS Speech Analytics · revisión 25 — interlocutor y negociación condicionada

Continuación de la versión 06 recibida en el paquete de migración. El código de
la aplicación está en `proyecto/MRS_Speech_Analytics_v3.6.19_Revision/`.

La revisión incorpora correcciones para fallos reproducidos del lote informado. Los 13 errores siguen pendientes de validación por casos reales.
Es una versión candidata: no está certificada en Windows ni mediante escucha de
las llamadas originales. Consulte `REVISION_25_DIAGNOSTICO.md` dentro de la aplicación para
resultados, cambios y límites por regla. Los documentos de validación anteriores
se conservan como historial, no como certificación de esta revisión.

## Windows

Si no puede descargar el checkpoint privado del chat, este paquete incorpora
`RECONSTRUIR_BASE_R25.bat`. Seleccione su último `checkpoint_reanalizado.json`
completo de 95 llamadas, `revision_audios_bloque.json` con las diez lecturas y,
si se solicita, el `batch_checkpoint.json` original usado para esas lecturas.
Genera localmente `Checkpoint_r25_95_Audios.json` y su Excel, recuperando los
nombres según `numero_de_tarjeta` previamente autorizado y conservando las
lecturas. No ejecuta Whisper ni procesa de nuevo audios. Las reglas siguen siendo
r25. Consulte `RECUPERAR_CHECKPOINT_SIN_DESCARGAR.txt` dentro de la aplicación.

Use Python 3.10 de 64 bits. Extraiga el paquete completo, abra la carpeta de la
aplicación y ejecute `INSTALAR.bat`; después `INICIAR_MRS.bat`. Los lanzadores y
dependencias originales se conservan. La primera transcripción de audio nuevo
necesita descargar el modelo de Whisper desde Hugging Face.

Para probar las reglas nuevas sobre textos guardados, ejecute
`REANALIZAR_CHECKPOINT.bat`. La consola debe mostrar `3.6.19-r25` y crear una
carpeta `Reanalisis_MRS_r25_...`. Este paso no vuelve a transcribir audios.
Si ya recuperó importes, seleccione el checkpoint final de esa recuperación;
así se conserva la evidencia sin volver a ejecutar Whisper.

Para recuperar un importe omitido, ejecute `RECUPERAR_IMPORTES.bat`, seleccione
el checkpoint y la carpeta de sus audios originales. Se releen únicamente
ventanas de ofertas incompletas; se conservan los textos originales y se genera
un checkpoint nuevo y un Excel dentro de `Recuperacion_MRS_r25_.../resultados`.
La evidencia aparece en las columnas finales de recuperación. Un importe
recuperado por ASR conserva revisión de evidencia. El efecto del mínimo se valida
por mora: regularización/mensualidad o liquidación. En las moras de liquidación,
el mínimo del Excel es la referencia; no se exige el saldo total ni una columna
adicional de autorización por la diferencia entre mínimo y saldo.
Este control también se aplica al procesar audios nuevos. Se usa el mismo modelo
configurado, sin instalar otro Whisper ni actualizar Python.

La revisión 15 contrasta las hojas 04, 05, 06, 13 y 14 del manual recibido.
Por aclaración expresa del usuario, 3HN, 4PV–6PV, C1–C4, B y A se liquidan
durante el mes de la llamada: un vencimiento posterior no prolonga ese plazo.
En 1PV–3PV y 1-FLP se conservan corte y vencimiento. En dos exhibiciones, la
primera queda dentro de tres días de la llamada y la segunda hasta siete días
desde la primera, sin exceder el vencimiento. Sin esa excepción, rige el plazo
general de tres días. La excepción no prolonga el mes permitido para liquidación.

Para registrar un importe recuperado ya comprobado por una persona, ejecute
`VALIDAR_IMPORTES.bat` y seleccione el checkpoint final. Las casillas comienzan
desmarcadas. Confirme solo los importes comprobados; si el identificador de
nombre_final difiere de numero_de_tarjeta, puede corregirlo en una copia usando
la tarjeta de origen. Guarde para generar un checkpoint y reporte nuevos en
`Validacion_MRS_r25_.../resultados`. Cuando se localiza o selecciona el Excel
de cuentas, también se genera `Datos_Cuentas_Corregidos.xlsx` sin cambiar el original.
En análisis individual existe el botón Validar importe. La confirmación se
conserva para reanálisis posteriores y no exime las demás reglas de calidad.

En revisión 18, la misma herramienta permite registrar un saldo confirmado en
audio cuando ASR lo transcribió distinto, o confirmar el plan final de
parcialidades después de propuestas con cantidades diferentes. El saldo se
escribe en un campo inicialmente vacío; las casillas siguen desmarcadas.
Se conservan las confirmaciones previas de otras llamadas aunque no se vuelvan
a marcar. No se rellenan importes usando el saldo esperado del Excel.

Los hechos confirmados se guardan por separado, ligados a la llamada y su
evidencia. El texto original de Whisper y las propuestas iniciales se conservan.
El Excel añade las columnas Confirmación financiera, Saldo ASR original,
Saldo confirmado por usuario, Parcialidades finales confirmadas e Historial de
propuestas de parcialidades. Un reanálisis conserva las confirmaciones válidas.
La herramienta también permite revocarlas y volver a evaluar la lectura ASR.

Para incorporar las confirmaciones de una muestra al lote completo, ejecute
`INCORPORAR_VALIDACIONES.bat`. Seleccione primero el checkpoint del lote completo
y después el checkpoint final de la muestra ya validada. Las llamadas se cruzan
por nombre exacto, texto, segmentos, duración y datos de cuenta. Si hay una
diferencia o una confirmación incompatible, se detiene la incorporación.

La salida está en `%USERPROFILE%\MRS_Resultados\Integracion_MRS_r25_...\resultados`.
Conserva todas las llamadas y sus datos originales, agrega la evidencia recuperada
necesaria y las confirmaciones válidas, y recalcula las clasificaciones.
No se trasladan etiquetas de aprobación ni puntajes mínimos de la muestra.
Solo se corrige un nombre de salida si lleva su confirmación explícita anterior.
Si se localiza el Excel de cuentas, se genera una copia con esos nombres corregidos.
La consola y la hoja NOTA_REANALISIS indican los archivos nuevos y el alcance.
No se ejecuta Whisper ni se copian audios.

La revisión 21 incorpora la aclaración del usuario: se conserva CONVENIO o
NO DEFINE FECHA DE PAGO en un seguimiento de pago reportado y comprobante.
Se separan importes de fechas, plazos y teléfonos; una terminación de WhatsApp
no se compara como tarjeta. Se reconocen variantes de identidad, parentesco,
aceptación de recados y rechazo de una negociación posterior a un pago histórico.
Se mantienen la atribución de liquidaciones, privacidad, maltrato, fechas,
montos y dos lugares autorizados cuando hay una negociación nueva.

El puntaje refleja las penalizaciones observadas; se retira el límite artificial
de 79 por estatus no confirmado. Una llamada con evidencia pendiente conserva
REVISAR aunque obtenga 100 puntos. Los textos ASR y datos de cuenta se conservan.
La revisión 22 corrige fechas tomadas de teléfonos/convenios, importes dictados
sin «pesos», advertencias de parcialidad negadas, aceptación de pagos y
reiteraciones de un pago histórico que se volvían a sumar. Un importe reportado
como incierto conserva revisión. El resumen Excel distingue clasificación
calculada, discrepancias de estatus y validación financiera.

El lote privado de 95, con 22 nombres corregidos según la instrucción expresa de
usar numero_de_tarjeta, obtiene en r25 13 APROBADO, 80 REVISAR y 2 FALLA_GRAVE.
Se conservan las 12 aprobaciones de r23. El reanálisis ordinario no corrige nombres
por sí solo: use el checkpoint corregido entregado para conservar esos cambios.
El reporte de auditoría identifica los bloqueos de cada una de las 85 llamadas
que estaban pendientes; REVISAR no significa falta confirmada. Se incorporaron
las diez lecturas nuevas devueltas por el usuario, sin nueva escucha humana ni
ejecución de Whisper en esta nube.

Para aplicar estas reglas a un lote existente, use REANALIZAR_CHECKPOINT.bat
con el checkpoint más reciente de ese lote. La aprobación calculada y el
renombrado físico son pasos distintos: este reanálisis actualiza JSON y Excel,
conservando los audios. Las llamadas nuevas usan las reglas al procesarse.

Las tres herramientas guardan ahora cada ejecución en una carpeta independiente
dentro de `%USERPROFILE%\MRS_Resultados` (por ejemplo,
`C:\Users\Usuario\MRS_Resultados`). No se anidan dentro del checkpoint anterior:
esto corrige el fallo de guardado al acumular recuperaciones y reanálisis.
Antes de generar archivos se comprueba que las rutas de salida, incluido el Excel
temporal, quepan en el límite conservador de Windows. `--output-dir` permite elegir
otra carpeta corta, nueva y vacía al ejecutar las herramientas desde la consola.

Para reproducir las pruebas en esa carpeta:

```bat
py -3.10 -m pip install -r requirements-dev.txt -c constraints-tested.txt
py -3.10 -m pytest -q
```

Las versiones de `constraints-tested.txt` fueron ejecutadas en Linux con Python
3.10.22; falta verificar r25 en Windows. Los archivos recibidos acreditan la
ejecución del lector de bloques r23 en el Windows del usuario.

## Entorno de desarrollo en la nube

Desde `/workspace/SpeechA`, ejecute `bash setup-cloud.sh`. Las dependencias quedan
en `/workspace/SpeechA/.venv`; después:

```bash
cd proyecto/MRS_Speech_Analytics_v3.6.19_Revision
/workspace/SpeechA/.venv/bin/python -m pytest -q
```

Para comparar la base original con esta revisión, conserve el ZIP original
extraído en una ubicación privada y ejecute, desde la carpeta de la aplicación:

```bash
python tools/regression_checkpoints.py \
  --input-dir /ruta/privada/pruebas_checkpoints \
  --baseline-source /ruta/privada/proyecto/MRS_Speech_Analytics_v3.6.19_Revision \
  --reviewed-changes tests/reviewed_r22_from_original.json \
  --output-dir /ruta/privada/resultados_revision_actual
```

No suba checkpoints, audios ni resultados reales a un repositorio público.
El paquete de código excluye esos datos; los resultados privados se conservan fuera de Git.

La regresión contra r21 usa como base su carpeta de aplicación extraída y
`--reviewed-changes tests/reviewed_r22_changes.json`. El documento original de
cambios permanece intacto. Ambos recorridos de 268 evaluaciones verifican hashes
de origen, causas de retiro de penalizaciones e invariantes; no copian etiquetas
históricas de aprobación. La suite actual contiene 829 pruebas. La regresión
de r25 con 268 evaluaciones contra r24 no cambia clasificaciones ni retira
penalizaciones sin causa.

## Revisión adicional de un bloque de audio

Extraiga la aplicación y ejecute `REVISAR_BLOQUE_AUDIOS.bat` en el mismo Windows
donde ya funciona Whisper. Seleccione el checkpoint completo más reciente y la
carpeta de hasta 10 audios originales del bloque. No hace falta instalar otro
Whisper: la herramienta exige que el mismo modelo usado en el checkpoint ya esté
localmente disponible; no descarga otro modelo ni cambia la configuración.

Se crea una carpeta `Revision_Audios_r25_...` en `%USERPROFILE%\MRS_Resultados`
con `revision_audios_bloque.json` y `Comparacion_Bloque_Audios.xlsx`. Guarda una
lectura completa con marcas de palabra y otra del cierre sin VAD, ambas como
hipótesis ASR. No cambia el checkpoint, sus validaciones, los dictámenes ni los
audios. No atribuye hablantes ni marca escucha humana. El JSON de lectura se
comparte para revisar; no es un checkpoint para REANALIZAR_CHECKPOINT.

Las diez lecturas r23 recibidas se cruzaron con los audios y el lote actual. Se
detectaron fragmentos repetitivos o mal alineados en tres llamadas; el lector
r24 los advierte sin tratarlos como infracciones. El texto bruto se conserva.

El paquete privado r24 ya contiene las diez lecturas vinculadas al checkpoint de
95 y el reporte final: no hace falta volver a transcribir ni repetir el lote.
La llamada 12 reconoce el correo ARCO dictado con dominio literal, pero conserva
la revisión de privacidad. No se confirman voces ni aceptación de recados por ASR.

Para incorporar resultados de otros bloques, use `INCORPORAR_LECTURAS_BLOQUE.bat`:
seleccione el checkpoint completo actual y `revision_audios_bloque.json`. Para
lecturas r23 generadas sobre otro checkpoint, se solicita también aquel origen.
Se comprueban texto, segmentos, duración y cuenta; no se importan aprobaciones ni
puntajes. Se conserva todo lo anterior y se genera otra copia con JSON y Excel,
sin ejecutar Whisper. El reporte añade tres columnas a las 87 anteriores.

El reconocimiento nuevo se ejecutó en el equipo del usuario, no en esta nube.
Las pruebas locales incluyen casos sintéticos y los resultados recibidos;
no acreditan escucha humana ni ejecución nativa de r25 en Windows.

## Correcciones de interlocutor y negociación (r25)

Se reconoce «somos conocidos/amigos» como tercero, sin inferir parentesco ni
aceptación del recado. Revisar cargos antes de pagar y «si corresponde, pagaré»
no acreditan un compromiso firme. Se separan pagos anteriores de instrucciones
nuevas y se evita confundir una fecha mensual con un cargo recurrente.

La llamada 83 recupera aprobación de calidad con NO DEFINE FECHA DE PAGO; no se
inventa un convenio aceptado. La 7 conserva revisión. Los 95 puntajes permanecen
iguales; el lote queda en 13 APROBADO, 80 REVISAR y 2 FALLA_GRAVE. Se conservan
las correcciones y confirmaciones anteriores.

La entrega r25 ya incluye el reporte y `Checkpoint_r25_95_Audios.json`; use ese
checkpoint para el próximo cambio de reglas. No necesita volver a transcribir
los audios ni repetir el reanálisis para obtener el reporte entregado.
