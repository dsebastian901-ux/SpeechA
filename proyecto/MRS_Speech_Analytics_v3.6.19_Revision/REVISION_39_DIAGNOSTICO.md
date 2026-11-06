# Revisión 39 — lugares de pago, comprobante e identificación MRS

Base: paquete completo r38 comprobado. Conserva sus funciones, la recuperación de transcripciones, las confirmaciones por archivo/contexto y el reporte adicional de motivos de no pago. No cambia el modelo de Whisper ni los requisitos de instalación.

## Aplicación en Windows

Extraiga el ZIP completo en una carpeta nueva. Con el checkpoint completo recibido de r38:

- REANALIZAR_CHECKPOINT.bat aplica las reglas nuevas en una copia.
- REANALIZAR_CON_TARJETA_EXCEL.bat combina el reanálisis con la corrección autorizada de identificadores de nombre_final desde numero_de_tarjeta. Es la opción indicada para las 400 discordancias encontradas en este lote. No cambia el número de tarjeta, los demás campos de cuenta ni el texto de Whisper.

Seleccione el JSON del checkpoint. Las herramientas muestran las rutas nuevas al terminar y generan el reporte de calidad y Reporte_Motivos_No_Pago.xlsx en 04_Reportes. No es necesario reinstalar Whisper ni procesar de nuevo los audios para cambiar reglas. No se reclasifican físicamente los audios mediante el reanálisis; la clasificación del Excel es la calculada.

## Cambios

### Identificación de MRS

Reconoce M.A.R.S., M.R., DMRS, MIRS y M.R.C. cuando forman parte de la presentación del despacho. Usa contexto de jurídico, corporativo, consultores o representación; no acepta una sigla aislada, un nombre de persona, un planeta, una negación o palabras identificadas del cliente como presentación del gestor. Conserva la evidencia de la variante y no reescribe Whisper.

Se contrastaron, entre otros, los ejemplos 86, 100, 224, 791 y 818 del lote recibido. La identificación del despacho no confirma por sí misma que el interlocutor sea el titular.

### Lugares de pago

Reconoce variantes ASR acotadas de las mismas cadenas autorizadas: por ejemplo, «farmacia de la horro», «che dragui», «bulbor», «círculo que» y «Abarray». Cuenta marcas distintas, tolera listas repartidas entre oraciones y evita contar dos veces la misma cadena. No añade establecimientos por parecido genérico ni convierte una mención del banco en convenio autorizado.

Se conserva la exclusión de negaciones, palabras del cliente y tiendas mencionadas como origen de tarjeta. Ejemplo 37: de un lugar detectado pasa a siete; el 259 reconoce seis en la instrucción de pago. Que haya dos lugares no exime montos, fechas, privacidad, aceptación o trato.

### Solicitud de comprobante

Según la aclaración operativa del usuario, «espero su ticket/ticker», «quedamos en espera del comprobante», «enviarme el comprobante», «reportar el recibo», «reportar el pago por WhatsApp» y otras instrucciones explícitas equivalentes acreditan la solicitud o expectativa del documento. Se contemplan envíos ya reportados sin afirmar que el banco recibió el pago.

El reporte separa tres columnas nuevas:

- Solicitud comprobante/ticket.
- Canal comprobante.
- Evidencia solicitud comprobante.

El campo histórico Comprobante WhatsApp solo acredita ese canal cuando se detecta. Pedir un ticket no inventa que se indicó WhatsApp. Las menciones de INE/comprobante de línea para ARCO y las palabras aisladas no satisfacen la solicitud de comprobante de pago.

Cuando ASR conserva un documento y el canal, pero no permite confirmar la petición, se muestra REVISAR. No se certifica cumplimiento ni se atribuye automáticamente una omisión de diez puntos. Una negación explícita no queda oculta por esta tolerancia. Se conservan las demás condiciones para exigir el comprobante y los dos lugares.

### Bloqueos comprobados al revisar las nuevas aprobaciones

Corregir errores de reconocimiento no debe promover llamadas con otros problemas:

- En el recado 8, «se le está ditaminando a su negativa» en contexto de pago/cobro requiere atribuir la información financiera. Permanece en revisión; la aceptación del recado no exime privacidad.
- Un «Maldita» aislado al cierre, como en el 68, bloquea aprobación hasta comprobar emisor/contexto; no se culpa automáticamente al gestor.
- En la 296, un pago previo no exime la nueva propuesta del restante sin aceptación clara. Permanece en revisión. No se penaliza como negociación grave confirmada por esa incertidumbre.

Se preservan las alertas de «chisme», maltrato previo, groserías y las reglas de ARCO, visitas, referencias, mora/corte/vencimiento y parcialidades de las revisiones anteriores. No se trasladan confirmaciones por número de fila entre lotes.

## Validación

Los resultados exactos de la suite y de los tres reanálisis se registran en VALIDACION_R39.json. Se contrastan 1,110 llamadas distintas: el lote recibido de 1,007 ya recuperadas y el anterior de 103. Una segunda ejecución del lote grande comprueba la corrección de nombres en copia. Las etiquetas anteriores son referencias de comparación, no verdad acústica.

La validación usa Python 3.10.22 en Linux. No se escucharon audios ni se ejecutó Whisper. Las pruebas que requieren pantalla Tk se omiten por falta de pantalla; no se afirma certificación nativa de Windows. Los checkpoints y reportes reales se conservan fuera del paquete de código y del repositorio público.

Las incertidumbres restantes se conservan en REVISAR. Esta revisión no declara cerrados los trece problemas generales.

## Resultados exactos de la entrega

- Suite completa: **1,535 aprobadas, 7 gráficas omitidas, cero fallos**, Python 3.10.22 / Linux.
- Checkpoint recibido de 1,007, antes: 25 APROBADO, 971 REVISAR, 11 FALLA_GRAVE, cero errores técnicos. Las 55 transcripciones que faltaban en el lote anterior ya están en el checkpoint recibido y se conservaron.
- Mismas 1,007 con reglas r39, conservando nombres: 969 REVISAR, 27 APROBADO, 11 FALLA_GRAVE. Se conservan las 25 aprobaciones recibidas y se contrastan las nuevas aprobaciones.
- R39 más corrección autorizada de los 400 nombres, en copia: 950 REVISAR, 45 APROBADO, 11 FALLA_GRAVE, 1 NO_APROBADO_MENOR_80. Quitar el bloqueo administrativo no elimina una puntuación insuficiente ni otros motivos de revisión.
- Lote anterior de 103: 73 REVISAR, 21 APROBADO, 9 FALLA_GRAVE; ninguna clasificación cambió y se conservaron sus lecturas y confirmaciones previas.
- Verificadas las filas y todas las celdas de los tres reportes de calidad contra sus checkpoints: cero discrepancias. Ambos tipos de reporte se generan correctamente, una fila por llamada en motivos, sin fórmulas ejecutables en ese reporte.

Las cantidades de aprobados de las dos ejecuciones grandes reflejan operaciones distintas: solo reglas, o reglas más nombres corregidos. No se eliminaron bloqueos de interlocutor, privacidad, negociación o trato para aumentar aprobaciones. Los resultados reales permanecen privados.
