# Revisión 10 · pagos reportados y propuestas, audio pendiente

Continúa la revisión 09 y conserva sus correcciones. Se recibieron dos audios
originales que corresponden a las llamadas 4 y 10 del checkpoint del lote de
36 llamadas. Se verificaron formato y duración, y se localizaron sus textos
existentes. La descarga del modelo de Whisper en la nube quedó bloqueada por
un error 403 del proxy al acceder a us.aws.cdn.hf.co. No se ejecutó una nueva
transcripción ni se certificaron voces, montos o aceptación mediante escucha.

## Errores de reglas reproducidos y corregidos

- «Una vez que realice el pago» era interpretado como un pago ya efectuado.
  Se excluyen instrucciones futuras y negaciones de la evidencia de pago
  realizado. Se conservan los reportes reales en pasado y los pagos anteriores
  que coexisten con instrucciones futuras. Se registra el tramo de evidencia
  que permite extraer cada importe histórico.
- «Depositamos desde el domingo» acreditaba un pago anterior, pero no permitía
  extraer su importe. En el caso 4, el reporte de mil pesos ahora se compara con
  el mínimo esperado y deja de producir una penalización falsa por ausencia de
  intento de negociación. La discrepancia con el estatus del Excel sigue en
  revisión; el texto describe un pago reportado, no una nueva fecha prometida.
- «Hoy ... que tenga buen día» activaba una secuencia de pagos. En el caso 10,
  esto sumaba fragmentos monetarios de una propuesta como si fueran abonos
  distintos. Ahora se exigen señales de parcialidades o fechas de pago para
  sumarlos. El importe seleccionado es dos mil pesos, sin un multipago ficticio
  de tres mil. La aceptación y los lugares de pago siguen pendientes de audio.

## Validación y límites

- Las pruebas nuevas cubren instrucciones futuras, negaciones, reportes en
  pasado, depósito anterior con importe, despedidas y parcialidades reales.
- 195 pruebas aprobadas. La regresión histórica de 268 evaluaciones conserva
  258 REVISAR, 6 FALLA_GRAVE y 4 APROBADO, sin fallos en los controles de seguridad
  ni eliminaciones de penalización sin justificar. El reanálisis del lote usa las mismas
  reglas y comandos documentados en README. Los datos y resultados reales se
  conservan fuera del repositorio. Consulte RELEASE_MANIFEST.json en la raíz
  para los conteos verificados de esta revisión.
- El lote actual sigue con 36 REVISAR. Esto no certifica los dictámenes ni
  cierra los 13 problemas pendientes. No se forzaron aprobaciones.
- La comprobación acústica requiere completar la descarga del modelo en este
  entorno. El dominio pendiente se añadió al borrador de configuración; guardar
  un borrador no aplica la política al entorno en ejecución.
- Python 3.10, Whisper y los lanzadores de Windows se conservan. La instalación
  y operación en Windows siguen pendientes de validación.

Para revisar las reglas con su instalación actual, ejecute
REANALIZAR_CHECKPOINT.bat y seleccione el checkpoint original. Se genera un
Excel nuevo sin retranscribir ni modificar los archivos originales.
