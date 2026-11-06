# MRS Speech Analytics r41

Descargue `r41.zip` de esta carpeta y extráigalo completo en una carpeta nueva. Contiene el programa completo para Windows. No use Code > Download ZIP de esta rama para instalar el programa.

Bloquea toda aprobación cuando se reporta mala atención, agresión o maltrato, incluso en una llamada anterior y aunque el puntaje sea mayor a 80 %. Bloquea también 65 segundos o más sin retoma, incluida espera anunciada. Se envía a REVISAR con evidencia; una falta grave independiente conserva su categoría. No atribuye por sí sola la queja al gestor actual ni confirma silencio acústico con solo ASR.

Para la prueba de 100 audios nuevos use el procesamiento normal de lote, el Excel correcto y el mismo modelo Whisper, guardando en una carpeta nueva. Al finalizar genera el reporte de calidad, columnas de queja/espera, carpetas físicas y el reporte adicional de motivos de no pago. Conserve batch_checkpoint.json y el reporte para validar el lote real.

Para audios ya procesados ejecute REANALIZAR_CHECKPOINT.bat con su último checkpoint completo. No retranscribe ni modifica originales. Las copias físicas antiguas no se mueven mediante el reanálisis.

Validación: 1,660 pruebas aprobadas, 7 gráficas omitidas, cero fallos, Python 3.10.22/Linux. Incluye integración controlada de 100 archivos con ASR simulado: 25 controles aprobados y 75 con queja/espera en revisión, todos con puntaje suficiente. No equivale a procesar los 100 audios nuevos reales del usuario. Se conservaron los textos, datos, confirmaciones y aprobaciones de los checkpoints anteriores de 1,007 y 103 registros. Sin certificación acústica ni ejecución nativa Windows. Sin datos reales en el ZIP.

SHA-256: `182a3d133235d094791b9cf7cdc5534aa30fce9b0d9f0eb6e1488af82f5580d6`
