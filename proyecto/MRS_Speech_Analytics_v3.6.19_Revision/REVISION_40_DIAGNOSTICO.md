# Revisión 40 — listas completas de lugares de pago

Base: paquete r39 entregado. Mantiene Whisper, GUI, instalación Windows, clasificación física, reportes, confirmaciones por archivo/contexto y todas las correcciones anteriores. No cambia los requisitos ni el modelo de transcripción.

## Corrección

El detector podía encontrar los nombres de tiendas pero perder la oferta al introducirla con «el pago lo puede hacer», «puede realizarlo», «el pago ya se aplica», «los puede estar realizando» o una enumeración consecutiva. Se reconocen esas instrucciones y sus listas completas, incluidos separadores como Circle-K, 7-Eleven y tiendas 3-B, y las variantes acotadas de las mismas cadenas «tienda tres B», «farmacias de la ahorro» y «Chedragüy».

Se cuentan marcas autorizadas distintas. Repetir una cadena no agrega un lugar. Los bancos siguen requiriendo el convenio/servicio correcto. Se excluyen ofertas negadas, tiendas de origen y turnos identificados del cliente; se distingue una opción no disponible de las alternativas afirmativas que siguen. Compras, retiros de efectivo y consultas no acreditan una instrucción de pago. Una lista sin contexto de pago no se acredita por contener nombres conocidos.

El Excel de calidad conserva las columnas «Lugares Pago Autorizados», «Cantidad Lugares Pago» y «Cumple Mínimo 2 Lugares». La evidencia del checkpoint conserva la frase reconocida, rol y ventanas de tiempo disponibles. No se reescribe la transcripción ni se inventan voces o tiempos.

## Reporte de motivos de no pago al terminar el lote

En un lote nuevo, el flujo normal genera automáticamente el reporte de calidad y el Excel adicional `Reporte_Motivos_No_Pago_FECHA_HORA.xlsx` en `04_Reportes`. La pantalla final informa la ruta y el botón «Motivos de no pago» abre el reporte. No se necesita ejecutar un reanálisis para obtenerlo al procesar audios nuevos.

El reporte adicional agrupa los motivos por categoría, gestor/supervisor y mora, y conserva detalle por llamada y los datos originales de cuentas disponibles. Las hojas son RESUMEN_MOTIVOS, POR_GESTOR, POR_MORA, DETALLE_LLAMADAS, DATOS_EXCEL y NOTAS. Cada llamada tiene un motivo principal; otros motivos se muestran aparte para no duplicar el total. No atribuye al titular las finanzas de un tercero ni inventa un motivo cuando no hay evidencia.

Una prueba de integración de dos audios nuevos, con respuesta ASR controlada y archivos/Excel/análisis/copias/exportaciones reales, comprueba que el reporte adicional se genera una sola vez, después de ambas llamadas, conserva una columna extra del Excel original y registra su ruta en el checkpoint. Los reportes parciales no disparan ese reporte adicional. La prueba no certifica la precisión acústica de Whisper.

## Aplicar en Windows

1. Extraiga el ZIP completo en una carpeta nueva.
2. Para audios ya procesados, ejecute `REANALIZAR_CHECKPOINT.bat` y seleccione su último checkpoint completo. Se guardan una copia y los dos reportes, sin Whisper ni modificación de originales. El reanálisis no mueve las copias físicas de audio ya clasificadas.
3. Si también necesita la corrección ya autorizada de nombres desde `numero_de_tarjeta` del Excel, use `REANALIZAR_CON_TARJETA_EXCEL.bat`; incluye el reanálisis. No use el nombre anterior como autoridad del número de tarjeta.
4. Para audios nuevos, use el procesamiento normal de lote y el Excel de cuentas. Al finalizar se generan ambos reportes automáticamente.

Cumplir los dos lugares no exime privacidad, derechos ARCO, montos, fechas, aceptación de recado, amenazas o trato. Las dudas restantes se mantienen en REVISAR. No se declaran cerrados los trece problemas generales.

## Validación

Los resultados exactos de la suite completa y los reanálisis se incluyen en `VALIDACION_R40.json`. Se compara con la entrega r39 sobre 1,007 registros del lote de noviembre y el lote anterior de 103; la copia del lote grande con nombres corregidos se comprueba aparte. El archivo grande disponible contiene 1,007 registros, aunque en la conversación se denominó lote de 1,011. No se inventan las cuatro llamadas de diferencia.

Las pruebas se ejecutan con Python 3.10.22 en Linux. Las pruebas gráficas que requieren pantalla quedan identificadas como omitidas. No se afirma escucha acústica ni certificación nativa Windows. Checkpoints, reportes y audios reales permanecen privados y se excluyen del paquete de código y del repositorio público.

## Resultados exactos

- Suite completa: 1,580 aprobadas, 7 gráficas omitidas, cero fallos.
- Lote de 1,007 con nombres conservados: 969 REVISAR, 27 APROBADO, 11 FALLA_GRAVE.
- Copia de 1,007 con nombres ya corregidos desde tarjeta Excel: 950 REVISAR, 45 APROBADO, 11 FALLA_GRAVE, 1 NO_APROBADO_MENOR_80.
- Lote de 103: 73 REVISAR, 21 APROBADO, 9 FALLA_GRAVE.
- Se retiran 41 marcas de menos de dos lugares frente a r39; cero penalizaciones nuevas de ese criterio. Las nuevas aprobaciones se revisan con sus demás reglas, sin cambiar el umbral.
- Verificadas todas las celdas de los tres Excel de calidad contra los checkpoints y los totales de motivos de no pago; cero discrepancias. Textos, datos de cuenta y confirmaciones previas conservados.
