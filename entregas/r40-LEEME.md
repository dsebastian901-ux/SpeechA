# MRS Speech Analytics r40

Descargue el archivo `r40.zip` de esta carpeta y extráigalo completo en una carpeta nueva. Contiene el programa Windows completo, no solo un parche. No use Code > Download ZIP de esta rama para instalar el programa.

Corrige el reconocimiento de listas completas de lugares de pago. La validación retira 41 penalizaciones falsas frente a r39 en el lote disponible de 1,007 registros, con cero penalizaciones nuevas de ese criterio. Conserva los demás dictámenes y confirmaciones, y el reporte automático de motivos de no pago al terminar un lote nuevo, con los datos originales del Excel.

Para audios ya procesados, ejecute `REANALIZAR_CHECKPOINT.bat` y seleccione su último checkpoint completo. No se ejecuta Whisper ni se modifican originales. Si necesita también corregir nombres desde numero_de_tarjeta del Excel, use `REANALIZAR_CON_TARJETA_EXCEL.bat`, que incluye el reanálisis. Ambos reportes se guardan en 04_Reportes.

1,580 pruebas aprobadas, 7 gráficas omitidas; Python 3.10.22/Linux. Reanálisis de 1,110 llamadas distintas, más verificación de la copia del lote grande con nombres corregidos. No se afirma escucha acústica ni certificación nativa Windows. El ZIP excluye datos reales, reportes, audios y entornos virtuales.

SHA-256: `deb40d113c43aec10374e497a46acc7409fd1f720fe2e2e5a52d328cd2da869b`
