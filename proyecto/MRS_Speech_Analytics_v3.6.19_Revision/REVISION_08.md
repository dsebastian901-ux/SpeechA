# Revisión 08 · candidata

Se conserva la revisión 07 y se corrige un caso adicional del error 4: cuando
el rol explícito es TITULAR, mencionar «es mi esposa», «es mi madre» o «es mi
hijo» no lo transforma en un familiar que recibió la llamada. Ese titular
tampoco puede aportar la aceptación de un recado familiar. Se mantiene el caso
positivo de un familiar real que contesta por el titular.

La reproducción anterior fallaba en cuatro casos. Con la corrección pasan los
cinco casos nuevos y la suite completa: **157 pruebas aprobadas**. La regresión
de 268 evaluaciones mantiene 253 REVISAR, 11 FALLA_GRAVE y 4 APROBADO. No se
modificaron las penalizaciones de los checkpoints ni se añadieron aprobaciones.

Los 13 problemas continúan sujetos a validación por casos reales; la existencia
de pruebas no los certifica como cerrados. Las cuatro aprobaciones de los
checkpoints recientes corresponden al mismo caso 016, con aceptación textual
«yo se lo envío» pero sin rol de voz atribuido. Falta verificar esa aceptación
en el audio. Se mantienen las limitaciones y controles de REVISION_07.md.

## Ejecutar una prueba y abrir su reporte

1. Entre en la carpeta que contiene main.py, INSTALAR.bat e INICIAR_MRS.bat.
   Instale con INSTALAR.bat usando Python 3.10 de 64 bits y abra INICIAR_MRS.bat.
2. Cree un proyecto de prueba. En procesamiento por lotes, agregue copias de los
   audios. Elija Modo A · Audios + Excel para comparar los datos de relación,
   o Modo B · Solo audios si no dispone del Excel.
3. Pulse Procesar lote y, al terminar, Abrir reporte Excel. El reporte se guarda
   en 04_Reportes dentro del proyecto. La primera transcripción necesita internet
   para descargar el modelo de Whisper.

Se comprobó generación de Excel con casos sintéticos y reutilización de JSON.
No se ha validado la instalación Windows ni el reconocimiento de audio nuevo
con el modelo: su descarga en la nube devolvió 403. Los dictámenes de la prueba
necesitan revisión humana.
