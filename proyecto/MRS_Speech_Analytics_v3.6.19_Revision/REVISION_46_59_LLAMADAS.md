# r46 — revisión individual completa de las 59 pendientes

Se leyeron completas las 59 transcripciones que permanecían REVISAR en r45. Cada llamada tiene una conclusión individual, comparación de motivos, evidencia y acción en el informe privado Revision_Individual_59_r46.xlsx. Se contrastaron diez fragmentos con Whisper medium ya disponible localmente; una lectura repetitiva se descartó. No se registra escucha humana ni verificación bancaria ni se sustituye la transcripción original.

De esas 59: una aprobación resuelta, siete rechazos definitivos por puntaje y 51 bloqueos conservados con causa individual. Estos últimos se agrupan en 30 de seguridad/trato, diez financieros/datos, diez de identificación/estatus y una restricción de duración. Una llamada revisada no se convierte en aprobada por tener más de 80 si conserva un riesgo o incumplimiento.

El lote completo de 100 queda con 21 APROBADO, cuatro APROBADO_ETIQUETA_CORREGIDA, 21 NO_APROBADO_MENOR_80, 51 REVISAR y tres FALLA_GRAVE.

## Correcciones generales

- Una terminación explícita repetida dos veces no se interpreta como referencia truncada de 16 dígitos. Las referencias completas o incompletas sin ese contexto conservan su validación contra numero_de_tarjeta.
- Se conservan las fechas del pago vigente y se excluye la fecha informativa de otra mensualidad. Una fecha de enviar/recibir comprobante no crea una promesa de pago.
- Las preguntas sobre cómo se hizo un pago y las transferencias históricas no se tratan como instrucciones nuevas de transferencia. Una CLABE, cuenta de destino, instrucción nueva o convenio bancario inconsistente conserva su revisión.
- Un pago histórico o una compra discutida no se compara como importe de un convenio nuevo. Se conservan las comprobaciones de saldo, documento incierto, oferta vigente y monto fuera de rango.
- Se reconoce orientación de aclaración cuando hay una disputa real y canalización para folio o estado de cuenta; esa orientación no se penaliza por ausencia de negociación.
- Se reconocen denuncias de falta de seguimiento, agentes prepotentes, llamadas reiteradas después de pago reportado y tarjeta no solicitada, respetando emisor, negaciones e hipótesis. Se mantienen quejas de llamadas anteriores, lenguaje ofensivo, visitas y espera de 65 segundos.
- Un calendario de pagos restantes descrito durante seguimiento conserva la validación de sus términos; reportar un pago anterior no lo exime.
- Un plan explícito de dos pagos aceptados y con fechas vinculadas conserva sus importes. Explorar después una alternativa opcional sin aceptarla no reemplaza ese plan. La fecha del segundo pago nunca se completa desde el vencimiento del Excel.
- Si el rechazo por puntaje es definitivo y solo falta fecha contractual ya descontada, puede resolverse automáticamente conservando todas las observaciones. No exime términos financieros incorrectos, privacidad, referencias, quejas ni evidencia incierta de audio.

Se conserva el catálogo confirmado por la usuaria y la prohibición de liquidación/cancelación en 1–3 PV. La falta de dos lugares de pago resta 20 y permite aprobar con 80 únicamente si cumple todos los demás filtros. Los cambios de código de estatus se realizan solo en el cuarto componente del nombre y las copias van a APROBADOS_ETIQUETA_CORREGIDA; el Excel y los audios originales quedan intactos.

## Reportes

El reporte de calidad mantiene CUENTAS_REETIQUETADAS y RESUMEN_REETIQUETADO para que el gestor corrija su base, además del detalle y resumen de los trece grupos de reglas. El reporte de motivos de no pago se conserva al terminar el lote. El informe individual de las 59 incluye las ocho resoluciones, los 51 bloqueos, textos originales con tiempos y los contrastes ASR, indicando los límites de cada evidencia.

## Aplicación posterior

Esta entrega documenta la revisión del mismo lote; no solicita una prueba nueva al usuario. Para aplicar las reglas posteriormente, extraiga TODO el ZIP en carpeta nueva. REANALIZAR_Y_CORREGIR_ETIQUETAS.bat admite el último checkpoint completo y la carpeta de audios originales; REANALIZAR_CHECKPOINT.bat genera reportes sin copiar audios. No es necesario retranscribir ni cambiar o descargar un modelo de Whisper para aplicar las reglas.

## Validación y límites

2,161 comprobaciones automáticas correctas y siete gráficas omitidas; preparación futura con 2,181 correctas y siete omitidas. Regresión en 1,210 evaluaciones de tres lotes de 100, 103 y 1,007. Se verifican ASR original, datos de cuentas, confirmaciones, puertas de seguridad, reportes y origen sin cambios. Tras el último ajuste de seguridad se compararon los tres extractores modificados en cada evaluación; cualquier cambio de evidencia repitió el análisis completo, y las extracciones conservadas se verificaron idénticas con su fuente anterior por hash y contenido. Los informes reales son privados y no se publican en este ZIP de código.

Las 51 retenciones tienen conclusión documental, pero sus causas no permiten liberar aprobación con la evidencia disponible. Los fragmentos ambiguos no se dan por confirmados en voz. Linux/Python 3.10, sin certificación nativa Windows. El instalador final con usuarios, permisos e icono continúa en desarrollo separado.
