# r48 — correcciones generales del programa

## Uso

Abra INICIAR_PROGRAMA.bat, cree un proyecto y cargue los audios y el Excel en Procesamiento por lotes. El motor aplica las correcciones desde la primera evaluación. La revisión de interfaz y motor se obtiene de app/config/release.py: 3.6.19-r48. Se conserva el modelo local de Whisper y el procesamiento sin conexión del programa existente.

## Correcciones

Los recados reconocen respuestas naturales a preguntas de parentesco y trabajo, solicitudes de recibir el recado, aceptación del dictado, repetición del contacto y mensajes de retorno como «se contacte» o «se ponga en contacto». Una oferta de dictar el teléfono sin entrega detectada conserva revisión. La recepción del recado requiere evidencia del interlocutor. La interpretación no se obtiene de la etiqueta del Excel.

La identificación del titular admite pregunta nominal y conversación sobre su propia cuenta según el criterio operativo autorizado. Se excluyen ubicaciones interpretadas como nombres y la representación de la cuenta de otra persona. Una negación de conocimiento seguida de parentesco contradictorio conserva revisión de identidad y evita declarar automáticamente una omisión ARCO confirmada.

El procedimiento ARCO reconoce dictado con pausas, siglas separadas y explicación de retirar el número de la base de datos. Conserva mención expresa de derechos ARCO, trámite, correo oficial completo, INE y comprobante de línea. No se inventan letras de un dominio incompleto ni se acepta negar el trámite. Las respuestas de antigüedad de la línea se vinculan a su pregunta.

Por decisión expresa de la usuaria se permiten «saldo pendiente» y «saldo vencido» sin importe. Continúan protegidos los importes, la mora concreta, la deuda explícita y la tarjeta completa. Se amplían formulaciones de incumplimiento de pago, mensualidades, años sin pago, canalización de la cuenta al jurídico e importes anunciados «por la cantidad de» para liquidar o regularizar. El importe informado por el tercero se distingue de una divulgación del gestor. La voz incierta conserva revisión y no se transforma en divulgación confirmada.

Se refuerza la detección de expresiones vulgares y quejas por cobros/costos no informados. Se conservan los trece grupos de reglas y los acuerdos anteriores: umbral de 80 condicionado a seguridad, 20 puntos por lugares de pago cuando corresponde, plazos por mora, segundo pago contado desde el primero, quejas de atención, espera de 65 segundos, terminación de tarjeta contra Excel, comprobante/ticket y todas las restricciones de negociación.

## Salidas

Se conservan el Excel de calidad y el reporte adicional de motivos de no pago al finalizar cada lote. CUENTAS_REETIQUETADAS y RESUMEN_REETIQUETADO muestran los cambios de estatus para que el gestor corrija. Solo cambia el bloque de código de estatus autorizado del nombre de la copia; los subtipos que comparten 3EROS pueden corregir su estatus sin cambiar ese bloque. Las copias se guardan en APROBADOS_ETIQUETA_CORREGIDA. Las cuentas y audios de entrada se mantienen íntegros.

## Validación y límites

VALIDACION_R48.json separa las pruebas automatizadas, el flujo de un proyecto nuevo con salidas ASR controladas, las evaluaciones de transcripciones previas y los contrastes ASR sobre ventanas de audio original. Estas lecturas adicionales no son escucha humana y no certifican voces. Los datos, audios y reportes reales se conservan privados y se excluyen de la distribución pública.

Con la misma transcripción y datos de cuenta se utiliza el mismo motor en lotes nuevos y reanálisis. Volver a ejecutar Whisper puede cambiar la transcripción. Las pruebas de flujo con ASR controlado no acreditan una retranscripción acústica integral. Persisten revisiones por evidencia insuficiente; no se ha completado la validación acústica de todas las llamadas. La ejecución se comprobó en Linux/Python 3.10; la instalación nativa en Windows está pendiente de comprobación en el equipo destino.

La entrega incluye el programa y sus lanzadores para el entorno Python existente. Los modelos, dependencias y runtime del futuro instalador offline autónomo con cuentas de usuario continúan en preparación.
