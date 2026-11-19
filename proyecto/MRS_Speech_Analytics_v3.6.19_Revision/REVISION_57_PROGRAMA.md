# Corrección del motor de evaluación r57

La corrección pertenece al programa usado al procesar lotes nuevos. El reanálisis utiliza el mismo motor y permite reutilizar la transcripción existente.

Se relacionan preguntas y respuestas de pago con su objeto y su momento: promesa nueva, pago anterior, importe, fecha, comprobante o teléfono. Las preguntas negativas no confirman por sí solas una negativa nueva. Las respuestas sobre la propia cuenta apoyan la identificación contextual; las instrucciones del gestor y las cortesías no son nombres ni autorreferencias del cliente.

El detector reconoce solicitudes de comprobante como «mandarme foto de su pago», «adjunte» y «agregue». Cuenta ofertas de establecimientos en contexto de pago y reconoce Kiosk. La instrucción de ingresar un importe no se confunde con una referencia de tarjeta. Un cambio de importe posterior al aceptado conserva una alerta para cotejarlo.

Los incumplimientos financieros comprobados pueden cerrar NO_APROBADO con sus alertas independientes visibles. Una conversación de fondo no confirma el regreso del gestor de una espera anunciada. Se mantienen los bloqueos por groserías, privacidad, quejas, ARCO y las demás reglas operativas. Se conservan el acceso de usuarios, la administradora DANIELA SEBASTIAN y los permisos de operadores.

## Comprobación

- 2965 pruebas aprobadas; 7 omitidas por condiciones de sus fixtures. Sin fallos.
- 2327 evaluaciones sobre ASR guardado de seis lotes; los lotes se cuentan por separado. No son 2327 audios nuevos ni una escucha humana de todos ellos.
- REVISAR: 1563 → 1512. Aprobaciones: 384 → 404.
- 175 llamadas por el procesamiento normal usando ASR guardado: dictámenes, puntajes, carpetas, copias y reportes cotejados. Audios, Excel y checkpoint de origen conservados.
- Whisper real local: dos audios nuevos en Linux y uno en el runtime Windows bajo Wine, con conexiones de red bloqueadas. Evaluación final repetida sobre las dos lecturas Linux.
- Inicio y páginas de lotes, dashboard, reportes y usuarios comprobados para administradora y operador bajo Wine. No se probó en hardware Windows físico.

Siguen 1512 evaluaciones pendientes. El Excel privado de auditoría incluye causa, fragmentos y acción por llamada. No equivale a confirmar acústicamente cada motivo. Las dudas de seguridad que acompañan a un rechazo permanecen visibles en ALERTAS_PENDIENTES.

## Uso

Extraiga el ZIP completo en una carpeta nueva y abra INICIAR_PROGRAMA.bat. Incluye Python, dependencias y Whisper small local. Los reportes de los lotes nuevos usan r57. El archivo VALIDACION_R57.json contiene el alcance agregado de las comprobaciones.
