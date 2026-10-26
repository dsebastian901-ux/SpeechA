# MRS Speech Analytics · revisión 14 — recuperación de importes omitidos

Continuación de la versión 06 recibida en el paquete de migración. El código de
la aplicación está en `proyecto/MRS_Speech_Analytics_v3.6.19_Revision/`.

La revisión incorpora correcciones para fallos reproducidos del lote informado. Los 13 errores siguen pendientes de validación por casos reales.
Es una versión candidata: no está certificada en Windows ni mediante escucha de
las llamadas originales. Consulte `REVISION_14_DIAGNOSTICO.md` dentro de la aplicación para
resultados, cambios y límites por regla. Los documentos de validación anteriores
se conservan como historial, no como certificación de esta revisión.

## Windows

Use Python 3.10 de 64 bits. Extraiga el paquete completo, abra la carpeta de la
aplicación y ejecute `INSTALAR.bat`; después `INICIAR_MRS.bat`. Los lanzadores y
dependencias originales se conservan. La primera transcripción de audio nuevo
necesita descargar el modelo de Whisper desde Hugging Face.

Para probar las reglas nuevas sobre textos guardados, ejecute
`REANALIZAR_CHECKPOINT.bat`. La consola debe mostrar `3.6.19-r14` y crear una
carpeta `Reanalisis_MRS_r14_...`. Este paso no vuelve a transcribir audios.

Para recuperar un importe omitido, ejecute `RECUPERAR_IMPORTES.bat`, seleccione
el checkpoint y la carpeta de sus audios originales. Se releen únicamente
ventanas de ofertas incompletas; se conservan los textos originales y se genera
un checkpoint nuevo y un Excel dentro de `Recuperacion_MRS_r14_.../resultados`.
La evidencia aparece en las columnas finales de recuperación. Un importe
recuperado por ASR requiere revisión y no acredita autorización de descuentos.
Este control también se aplica al procesar audios nuevos. Se usa el mismo modelo
configurado, sin instalar otro Whisper ni actualizar Python.

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
