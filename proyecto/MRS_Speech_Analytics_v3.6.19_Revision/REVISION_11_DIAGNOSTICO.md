# Revisión 11 · identificación, estatus y reporte

Conserva la revisión 10 y corrige causas reproducidas del exceso de REVISAR.
El estatus del Excel se compara con evidencia de la conversación; no se usa
para asumir quién contesta ni para dar por aceptado un convenio.

## Cambios

- Identificación: reconoce más formas de preguntar y responder, nombres tras
  «es usted el caballero», presentaciones con saludos y la entrega posterior
  de la llamada al titular. Una respuesta de familiar, referencia o profesión
  no acredita titular. La ausencia declarada identifica un tercero sin inventar
  parentesco ni recepción del recado.
- Estatus: distingue aceptación firme, cantidad propuesta por el interlocutor,
  rechazo, respuesta condicional y cambio posterior aceptado. Una respuesta
  sobre WhatsApp, un «ok» aislado o silencio no confirman un convenio. Rechazar
  una propuesta por falta de dinero no equivale a negarse definitivamente a pagar.
- Fragmentos de Whisper: se reconstruyen oraciones para que un corte acústico
  no oculte identidad, una oferta o una condición. Se preservan roles y tiempos
  disponibles; no se asigna gestor/titular a SPEAKER_00/01.
- Fechas: 7-11 como tienda no se convierte en fecha. Se reconocen días escritos
  con palabras. La fecha seleccionada y su evidencia proceden del mismo hallazgo.
- Importes: «mil 900 pesos» no suma otros 900. Se distinguen pagos iguales,
  parcialidades identificadas y una cantidad aceptada respecto de ofertas
  anteriores. Una segunda parcialidad con importes diferentes requiere revisión.
- Protección de aprobación: un estatus coincidente no elimina una diferencia
  de saldo, un descuento sin importe confirmado ni lenguaje confrontativo.
- Excel: «Estatus detectado IA» mostraba el tipo de interlocutor antes del
  estatus, por lo que podía mostrar TITULAR donde correspondía CONVENIO. Ahora
  muestra el estatus. Se añaden al final «Interlocutor detectado», «Evidencia
  estatus» y «Método detección estatus», conservando las columnas anteriores.

## Resultados verificados

- 244 pruebas aprobadas; compilación de app y herramientas correcta.
- Regresión histórica: 268 evaluaciones, 196 textos distintos; 259 REVISAR,
  5 FALLA_GRAVE y 4 APROBADO. Sin fallos de los controles de seguridad ni
  eliminaciones de penalización sin justificar. Se documentan dos cambios
  adicionales con hash del checkpoint y condiciones de evidencia: fecha escrita
  con palabras y una falsa falla grave que confundía la tienda 7-11 con fecha.
- Lote devuelto por el usuario: antes 36 REVISAR; ahora 1 APROBADO y 35 REVISAR.
  Los contactos identificados pasan de 20 a 26: 22 titulares y 4 terceros;
  quedan 10 sin identificar. Las coincidencias de estatus pasan de 1 a 5.
- La única aprobación nueva se revisó contra el texto: cambio aceptado de
  propuesta, parcialidades iguales, fecha, importe total y requisitos de pago.
  Otros estatus coincidentes conservan revisión por hallazgos independientes.
- El Excel coincide con el JSON. Las transcripciones originales se conservan;
  el reanálisis no ejecuta Whisper ni copia o mueve audios.

Estos resultados corresponden a las transcripciones guardadas, no a una nueva
comprobación acústica. Los audios privados y reportes permanecen fuera de Git.
El contraste de voces/frases dudosas y la operación completa en Windows siguen
pendientes. Los 13 problemas no se consideran cerrados por esta revisión.

## Comparación en su equipo

Extraiga la revisión 11 en una carpeta nueva, abra la carpeta de la aplicación
y ejecute REANALIZAR_CHECKPOINT.bat. Puede seleccionar el checkpoint original
o el checkpoint_reanalizado.json que devolvió de la revisión 10. Se generará
una carpeta nueva con Excel y JSON; conserve los reportes anteriores para comparar.
Se mantiene Python 3.10 y la instalación existente de Whisper.
