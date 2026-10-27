# MRS Speech Analytics · revisión 19 — incorporar validaciones al lote completo

Continuación de la versión 06 recibida en el paquete de migración. El código de
la aplicación está en `proyecto/MRS_Speech_Analytics_v3.6.19_Revision/`.

La revisión incorpora correcciones para fallos reproducidos del lote informado. Los 13 errores siguen pendientes de validación por casos reales.
Es una versión candidata: no está certificada en Windows ni mediante escucha de
las llamadas originales. Consulte `REVISION_19_DIAGNOSTICO.md` dentro de la aplicación para
resultados, cambios y límites por regla. Los documentos de validación anteriores
se conservan como historial, no como certificación de esta revisión.

## Windows

Use Python 3.10 de 64 bits. Extraiga el paquete completo, abra la carpeta de la
aplicación y ejecute `INSTALAR.bat`; después `INICIAR_MRS.bat`. Los lanzadores y
dependencias originales se conservan. La primera transcripción de audio nuevo
necesita descargar el modelo de Whisper desde Hugging Face.

Para probar las reglas nuevas sobre textos guardados, ejecute
`REANALIZAR_CHECKPOINT.bat`. La consola debe mostrar `3.6.19-r19` y crear una
carpeta `Reanalisis_MRS_r19_...`. Este paso no vuelve a transcribir audios.
Si ya recuperó importes, seleccione el checkpoint final de esa recuperación;
así se conserva la evidencia sin volver a ejecutar Whisper.

Para recuperar un importe omitido, ejecute `RECUPERAR_IMPORTES.bat`, seleccione
el checkpoint y la carpeta de sus audios originales. Se releen únicamente
ventanas de ofertas incompletas; se conservan los textos originales y se genera
un checkpoint nuevo y un Excel dentro de `Recuperacion_MRS_r19_.../resultados`.
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
`Validacion_MRS_r19_.../resultados`. Cuando se localiza o selecciona el Excel
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

La salida está en `%USERPROFILE%\MRS_Resultados\Integracion_MRS_r19_...\resultados`.
Conserva todas las llamadas y sus datos originales, agrega la evidencia recuperada
necesaria y las confirmaciones válidas, y recalcula las clasificaciones.
No se trasladan etiquetas de aprobación ni puntajes mínimos de la muestra.
Solo se corrige un nombre de salida si lleva su confirmación explícita anterior.
Si se localiza el Excel de cuentas, se genera una copia con esos nombres corregidos.
La consola y la hoja NOTA_REANALISIS indican los archivos nuevos y el alcance.
No se ejecuta Whisper ni se copian audios.

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
3.10.22; falta verificar la instalación y el audio en Windows.

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
  --reviewed-changes tests/reviewed_baseline_changes.json \
  --output-dir /ruta/privada/resultados_revision_actual
```

No suba checkpoints, audios ni resultados reales a un repositorio público.
El paquete de código excluye esos datos; los resultados privados se conservan fuera de Git.
