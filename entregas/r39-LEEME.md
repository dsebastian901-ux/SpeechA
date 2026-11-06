# MRS Speech Analytics r39

Paquete completo del programa: [Descargar r39.zip](r39.zip). Extraiga ese ZIP completo en una carpeta nueva.

Corrige variantes M.A.R.S./M.R./DMRS/MIRS en la presentación, listas de pago autorizadas y solicitud/expectativa del ticket. El Excel distingue comprobante y canal. Mantiene el reporte de motivos de no pago y los controles de seguridad anteriores.

Con su checkpoint completo de r38, ejecute REANALIZAR_CHECKPOINT.bat. Para corregir también los identificadores de nombre_final desde numero_de_tarjeta, ejecute directamente REANALIZAR_CON_TARJETA_EXCEL.bat, que ya incluye el reanálisis y guarda una copia. Se generan ambos reportes en 04_Reportes. No necesita reinstalar Whisper ni volver a transcribir para aplicar reglas.

Validación: Python 3.10.22, 1,535 pruebas aprobadas, 7 gráficas omitidas, cero fallos. No se certifica escucha acústica ni interfaz nativa Windows. Consulte REVISION_39_DIAGNOSTICO.md y VALIDACION_R39.json dentro del paquete para resultados y límites.

El ZIP contiene código, pruebas e instrucciones; no contiene audios, checkpoints ni reportes reales.

SHA-256: `bc859fc2404e5ee20694681703609a1390977b8ea3fc8c52ad5b00fe1cca0613`
