# r47 — correcciones aplicadas al programa de procesamiento inicial

## Uso normal

La entrega es el programa completo. INICIAR_PROGRAMA.bat abre la interfaz, donde se crea un proyecto, se carga el Excel y se procesan los audios en Procesamiento por lotes. No se requiere importar una base anterior, reanalizar, confirmar por número de llamada ni aplicar correcciones manuales para que el motor use sus reglas.

La identificación de revisión de interfaz, configuración y motor procede de una sola constante: 3.6.19-r47. El checkpoint de recuperación que el lote crea automáticamente registra esa revisión. La hoja CONTROL_PROCESAMIENTO registra por archivo la revisión, el flujo y si hubo una transcripción nueva o se recuperó una existente. No se atribuye retrospectivamente origen a llamadas antiguas sin ese registro.

## Reglas generales incluidas

Se conservan todas las correcciones generales de r46: reconocimiento contextual del titular; equivalencia de recados con aceptación real; protección PEN003 con hablante y datos protegidos; tarjeta de 16 dígitos contra numero_de_tarjeta del Excel; terminaciones explícitas repetidas; ARCO completo; lugares autorizados y deducción de 20 puntos; variantes de MRS en la presentación; ticket/ticker como comprobante; amenazas, groserías al final, trato y quejas de atención anterior; espera de 65 segundos; fechas e importes; pagos reportados frente a nuevas instrucciones; planes aceptados frente a alternativas no aceptadas; y clasificación por los trece grupos de reglas. Ninguna de estas reglas se activa mediante una lista de números de llamada.

Se cierra además un hueco en las instrucciones de depósito: una instrucción del gestor a una cuenta bancaria, cuenta de destino, número de cuenta o cuenta personal requiere comprobar los datos aunque no diga «transferencia». Una mención histórica, negada, citada o del interlocutor no se convierte por sí sola en instrucción nueva del gestor. Se mantienen los convenios bancarios autorizados y la separación entre pago bancario y transferencia.

Los nueve estatus y sus códigos, la prohibición de liquidación/cancelación en 1–3 PV, las políticas de mora y la carpeta APROBADOS_ETIQUETA_CORREGIDA permanecen vigentes. Solo se modifica el bloque de estatus de esas copias; las cuentas reetiquetadas aparecen en el reporte para que el gestor corrija su base.

## Verificación del programa

2,188 comprobaciones correctas y siete gráficas omitidas. Incluyen 27 escenarios nuevos del recorrido de proyecto desde carpeta vacía: frontera ASR controlada, lectura real del Excel, análisis, decisión, copias binarias y reportes. No se llama a reanalyze_checkpoint ni se importa una confirmación para resolver esos escenarios. Se cubren seguridad, recados, tarjeta, ARCO, depósitos, plan aceptado, lugares, variantes MRS y ticker, espera de 64/65 segundos, rechazo por puntaje, liquidación prohibida y reetiquetado.

Se procesó un proyecto de 100 llamadas con salidas ASR originales controladas, sin cargar un checkpoint anterior en la aplicación ni importar dictámenes/confirmaciones. Las 100 pasaron por la rama de transcripción nueva. Los 100 dictámenes y puntajes, incluidas las 59 revisadas, coincidieron con la versión corregida; se cotejaron 10,800 celdas del reporte, 100 registros de origen, cuatro cuentas reetiquetadas y los dos reportes finales. Las copias de audio se cotejaron por contenido binario y el Excel de entrada se conservó sin cambios.

El extractor bancario modificado se comparó en 1,210 evaluaciones previas sin cambios de evidencia en esos lotes; el hueco adicional se cubre con escenarios sintéticos positivos y negativos. La rama futura conserva sus extensiones con 2,208 comprobaciones correctas y siete omitidas.

Estos controles verifican el flujo del programa y sus reglas con salidas de ASR controladas; no constituyen una retranscripción acústica nueva de los 100 audios ni una escucha humana. La predicción automática mantiene REVISAR cuando la evidencia es insuficiente. Las pruebas se ejecutaron en Linux/Python 3.10, sin certificación nativa Windows. Los reportes y datos reales son privados y no se incluyen en el ZIP público.
