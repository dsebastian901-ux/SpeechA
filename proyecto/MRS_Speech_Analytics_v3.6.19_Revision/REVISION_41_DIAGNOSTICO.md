# Revisión 41 — quejas de atención y espera sin retoma

Base: paquete completo r40 entregado. Conserva la GUI, Whisper, instalación Windows, reportes, clasificación física, filtros anteriores, datos de cuenta y confirmaciones por archivo/contexto. No cambia el modelo ni los requisitos de instalación.

## Bloqueo por queja de mala atención o agresión

Una queja de mala atención, agresión o maltrato, incluso en una llamada anterior, bloquea todas las aprobaciones aunque el puntaje sea 80, 90 o 100. Incluye APROBADO, APROBADO_SIN_ETIQUETAR y APROBADO_CON_EXCEPCION. El seguimiento de un pago y la excepción por interlocutor hostil no eliminan ese bloqueo.

Se amplían las expresiones reconocidas: «me atendieron de mala manera», «recibí mala atención en la llamada anterior», «fue agresiva/prepotente», «me estuvo gritando», «se burló de mí» y otras equivalentes acotadas. También se contemplan quejas de familiares, sujetos plurales y atención recibida por otra persona cuando el contexto identifica la llamada o al asesor. Se conserva la frase, el rol y los tiempos ASR disponibles.

Una queja no resuelta queda en REVISAR, sin aprobar ni imputar por sí sola una falla grave al gestor actual. Se distinguen negaciones, hipótesis, preguntas del gestor y agresiones personales ajenas a la gestión. Un «sí, me atendieron mal» cuenta como queja; no se descarta como supuesto condicional.

## Espera de 65 segundos o más

La aclaración operativa del usuario del 6/nov/2026 establece 65 segundos. Se aplica el límite inclusivo: 64.999 no alcanza el límite; 65.000 sí. Una espera anunciada también bloquea si no se retoma el contacto dentro del límite. No se acumulan pausas cortas separadas por una retoma del gestor.

Se detectan intervalos entre segmentos/palabras ASR y la cola de una conversación abierta hasta el final del archivo. Una espera explícita se sigue hasta la retoma: los «¿bueno?, ¿me escucha?» del cliente no acreditan regreso del gestor. Se aprovechan los roles explícitos disponibles; un ID SPEAKER_00/01 no identifica por sí mismo al gestor. Con voz desconocida se trabaja con los indicios textuales y temporales disponibles.

Se excluyen el tiempo anterior al inicio de la conversación, anotaciones de música como supuesta retoma, solapamientos de segmentos y la cola de grabación posterior a una despedida normal. No se inventan intervalos desde tiempos inválidos o segmentos ajenos a la transcripción. Se usan marcas por palabra solo cuando cubren el texto completo del segmento; de lo contrario se conserva la resolución del segmento.

La alineación temporal usa el ASR original. Normalizar la presentación de un importe para las reglas financieras no descarta el segmento hablado ni crea un hueco de espera. Se comprueba también el límite exacto de 65 s con marcas decimales, sin confundir 64.999 s con incumplimiento.

La detección genera PEN_ESPERA_PROLONGADA y REVISAR con cero puntos de descuento: bloquea por regla, aunque el porcentaje supere el mínimo. No confirma silencio acústico, tono, abandono ni responsable y no genera por sí sola FALLA_GRAVE. Sin tiempos ASR utilizables, la columna indica NO EVALUABLE; no se afirma haber comprobado la espera. La validación acústica requiere revisar el audio.

## Evidencia en el Excel

El reporte de calidad agrega seis columnas en los modos A y B:

- Queja de atención/maltrato.
- Evidencia queja atención/maltrato.
- Validación espera 65 s.
- Mayor intervalo sin retoma (s).
- Intervalos espera 65 s.
- Evidencia espera.

Se conservan todas las columnas anteriores, los campos finales financieros/lecturas y los cinco campos ARCO. El checkpoint guarda la regla aplicada, el límite de 65 s, los intervalos y la evidencia. Las transcripciones originales no se reescriben.

## Prueba con 100 audios nuevos en Windows

1. Extraiga r41 completo en una carpeta nueva. Mantenga el mismo modelo Whisper y el Excel correcto de cuentas.
2. Procese un lote nuevo de 100 audios en una carpeta de resultados nueva, mediante el procesamiento normal del programa. No use un checkpoint de otro lote como entrada para esas llamadas nuevas.
3. Al finalizar, revise el Excel de calidad, las seis columnas nuevas y las carpetas físicas de clasificación. Las llamadas con queja o espera marcada deben estar en REVISAR, aunque su porcentaje sea alto; una falta grave ya confirmada conserva su categoría.
4. Se generan automáticamente ambos Excel en 04_Reportes, incluido el de motivos de no pago con los datos originales disponibles del Excel de cuentas.
5. Para validar el lote real, comparta su batch_checkpoint.json y el reporte de calidad. El programa no presupone que los 100 deban aprobar ni rechazar.

Para audios ya procesados, use REANALIZAR_CHECKPOINT.bat con su último checkpoint completo: guarda una copia, aplica r41 y genera ambos reportes sin volver a ejecutar Whisper ni modificar originales. No mueve retroactivamente las copias físicas de audios del lote anterior.

## Validación y límites

La suite incluye una integración de 100 archivos con ASR controlado: 25 controles limpios, 25 quejas de mala atención previa, 25 esperas anunciadas de 65 s y 25 huecos sin anuncio de 65 s. Los 100 tienen puntaje suficiente; se comprueban 25 APROBADO y 75 REVISAR, copias físicas, checkpoint, datos originales y ambos reportes finales. Esta prueba demuestra el flujo; no es escucha ni procesamiento Whisper de los 100 audios nuevos del usuario.

La regresión compara también los checkpoints disponibles de 1,007 y 103 registros contra r40, y por separado la copia de 1,007 con nombres ya corregidos desde numero_de_tarjeta. Se verifica que los textos, datos de cuenta, lecturas y confirmaciones previas se conserven, que las celdas de calidad coincidan con el checkpoint y que cuadren los totales de motivos de no pago. Los resultados exactos se guardan en VALIDACION_R41.json.

Pruebas en Python 3.10.22/Linux; las pruebas de GUI que necesitan pantalla quedan identificadas como omitidas. No se certifica ejecución nativa Windows ni precisión acústica. Los datos reales permanecen privados y se excluyen del paquete fuente y del repositorio público. No se declaran resueltos todos los casos generales de los trece problemas históricos.

## Resultados exactos de entrega

- Suite completa: 1,660 aprobadas, 7 gráficas omitidas, cero fallos.
- Lote real de 1,007 con nombres conservados: 969 REVISAR, 27 APROBADO, 11 FALLA_GRAVE.
- Copia de 1,007 con nombres ya corregidos desde tarjeta Excel: 950 REVISAR, 45 APROBADO, 11 FALLA_GRAVE, 1 NO_APROBADO_MENOR_80.
- Lote real de 103: 73 REVISAR, 21 APROBADO, 9 FALLA_GRAVE.
- Se detectan 5 llamadas con espera prolongada en el lote grande; ninguna estaba aprobada en r40. Se conservan sus otros motivos de revisión y todas las aprobaciones anteriores.
- Verificadas todas las celdas de calidad contra los tres checkpoints y los totales de los reportes de motivos de no pago. Cero discrepancias; textos, datos de cuenta y confirmaciones previas conservados.
- Prueba controlada de 100: 25 APROBADO, 75 REVISAR; todos con puntaje suficiente. No representa resultados de los 100 audios nuevos reales.
