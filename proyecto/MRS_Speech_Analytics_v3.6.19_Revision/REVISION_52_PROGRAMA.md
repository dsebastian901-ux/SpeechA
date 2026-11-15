# MRS Speech Analytics 3.6.19-r52

Correcciones del programa aplicadas al lote normal y al reanálisis:

- Separar preguntas y declaraciones dentro de una oración de Whisper, sin cambiar la transcripción ni atribuir voces.
- Reconocer identificación nominal con conversación financiera propia en las variantes admitidas; mantener señales de familiar, transferencia y cuenta de otra persona.
- Vincular confirmaciones de fecha e importe con la respuesta, conservando negativas, condiciones y pagos históricos.
- Una propuesta de fecha del gestor rechazada por el cliente no equivale a un convenio aceptado.
- Combinar propósito de retorno, contacto proporcionado y recepción del recado. Una instrucción o un agradecimiento no acredita recepción.
- Mantener bloqueos por quejas, groserías, posibles moras mal transcritas, amenazas sobre bienes y plazos de remanentes sin resolver.
- Conservar la cola de un checkpoint parcial. Reanalizar sus transcripciones existentes sin fabricar errores en audios pendientes.
- Mostrar PENDIENTE DE PROCESAMIENTO para audios sin dictamen. Calcular el porcentaje de aprobación sobre llamadas procesadas.
- Separar SIN_RELACION_EXCEL de REVISAR. Exportar RELACION_DATOS_ORIGEN para localizar las llamadas sin registro.
- Incluir contexto, fragmentos y tiempos disponibles en REVISION_PENDIENTE. No crear tiempos de palabras ni declarar escucha humana.
- Evitar alineamientos repetidos en una misma evaluación mediante caché temporal aislada, liberada al terminar.
- Calcular los encabezados de cada hoja una sola vez al aplicar formato. Evita recorrer todas las celdas repetidamente al generar reportes grandes, conservando valores y colores.

Se conserva el umbral de 80 puntos, los descuentos autorizados, las prohibiciones por mora, la tarjeta del Excel como fuente y la carpeta APROBADOS_ETIQUETA_CORREGIDA. No hay una cuota de aprobación ni excepciones por número de llamada.

Esta entrega usa el Python y Whisper locales existentes. No incluye un instalador autónomo nuevo ni usuarios compartidos por USB. No requiere un servicio de análisis en internet.

La revisión excesiva continúa siendo un pendiente del proyecto. Esta versión corrige fallos verificables; no declara identificadas las voces cuando la evidencia no lo permite. Para verificar los audios de otro lote y las relaciones ausentes se necesitan sus fuentes originales.

Ver VALIDACION_R52.json para el alcance de las pruebas, comparación y límites. Los datos privados del cliente no forman parte del ZIP público del programa.
