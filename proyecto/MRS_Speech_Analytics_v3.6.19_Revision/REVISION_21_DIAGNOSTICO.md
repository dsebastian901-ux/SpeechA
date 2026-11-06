# Revisión 21 · aprobación y seguimiento de pagos

Se corrigen bloqueos reproducidos al comparar el lote actual de 95 llamadas
con el reporte de la versión anterior. Las etiquetas antiguas no se usan como
verdad de referencia. El reporte antiguo contenía 31 aprobados, con umbral 70;
siete de ellos tenían Resultado IA REVISAR y clasificación física APROBADO.
La versión actual mantiene el umbral configurado y la puerta común de decisión.

## Regla operativa aclarada por el usuario

El 28/oct/2026 el usuario indicó que se debe conservar CONVENIO o NO DEFINE
FECHA DE PAGO en llamadas de seguimiento cuando el cliente informa que pagó
y se gestiona el comprobante. La coincidencia queda documentada como
SEGUIMIENTO_PAGO_REPORTADO_ESTATUS_ORIGINAL y ACLARACION_USUARIO_20261028.
Se conserva también el estatus conversacional PAGO REPORTADO / ACLARACION;
no se fabrica una promesa nueva ni se modifica el Excel.

Un seguimiento con solicitud de comprobante puede cumplir calidad aunque el
importe no se haya informado: se registra como desconocido y NO se afirma que
cubre el mínimo. Un pago previo conocido e insuficiente exige gestionar el
faltante. Una instrucción nueva de pago sin aceptación en un convenio conserva
REVISAR. La regla no perdona maltrato, divulgación, referencias incorrectas,
fechas o montos inválidos, instrucciones inseguras ni evidencia financiera
pendiente. Las negociaciones nuevas siguen requiriendo dos lugares autorizados.

## Correcciones realizadas

- Reconocer pagos reportados en pasiva y plural, separándolos de instrucciones
  futuras como «que ella realice el pago» o «que lo realice por esa cantidad».
- Vincular el importe pagado con la declaración o pregunta correspondiente.
  No convertir días, plazos de 72 horas, teléfonos o saldos anunciados en pagos.
  Reconocer cantidades en palabras, conservar contradicciones y sumar pagos
  distintos solo con evidencia de fechas distintas. No duplicar reiteraciones.
- Reconocer variantes de identificación, honoríficos separados por Whisper
  y autorreferencia de la propia cuenta tras una solicitud nominal. No inferir
  identidad de Excel, de un «sí» suelto ni de una respuesta genérica de dinero.
- Evitar que «no soy atención a clientes» o «el pago no está reflejado» anulen
  indebidamente la identidad. Mantener negativas de identidad, familiares,
  ausencia, roles conocidos y entrega del teléfono como controles separados.
- Reconocer parentescos contestados, aceptación explícita de recados y
  «le paso el dato»; diferenciar una negación directa de «no sé si se comunicó».
  El parentesco solo y el agradecimiento del gestor no confirman un recado.
- Diferenciar la terminación de WhatsApp de una terminación de tarjeta.
  Conservar el cotejo de tarjeta con numero_de_tarjeta del Excel.
- Identificar el rechazo de una propuesta actual aunque se mencione un pago
  histórico; no convertir cualquier pago anterior en seguimiento exclusivo.
- Conservar revisión de posible divulgación cuando se comunica atraso a un
  tercero. Una incertidumbre de voz no se convierte en PEN003 confirmado.
- Ampliar señales de queja de maltrato. Una posible grosería recortada al final
  conserva revisión sin inventar una falta grave ni atribuirla al gestor.
- Eliminar el límite artificial de 79 por estatus no confirmado. El puntaje
  refleja penalizaciones detectadas y REVISAR continúa bloqueando aprobación
  cuando falta evidencia, aunque el puntaje sea 100.

No se reduce el valor de las penalizaciones ni se baja el umbral del lote de 95.
No se agregan excepciones por nombre de persona, archivo, tarjeta o número de
llamada. Las pruebas usan ejemplos sintéticos.

## Resultado comprobado

El lote completo de 95 pasa de 1 APROBADO, 92 REVISAR y 2 FALLA_GRAVE en r20
a 8 APROBADO, 85 REVISAR y 2 FALLA_GRAVE en r21. Las aprobaciones corresponden
a las llamadas 10, 19, 22, 29, 43, 53, 71 y 75 del lote. Se reconocen 40 titulares;
49 llamadas conservan contacto no determinado.

Seis de las 31 aprobaciones antiguas quedan aprobadas; 25 conservan REVISAR,
con el motivo individual en la comparación privada. No se presentan esas
revisiones como incumplimientos ya demostrados ni se promete recuperar las
31 aprobaciones sin comprobar sus bloqueos. La llamada 87 solo mantiene la
inconsistencia del identificador de salida; no debe renombrarse con otra tarjeta.

Los datos y la comparación real se mantienen fuera de Git. El reanálisis no
vuelve a ejecutar Whisper ni mueve audios. Se conservan las transcripciones,
segmentos, datos de cuenta, importes confirmados y registros de validación.

## Verificación

- 645 pruebas unitarias y de integración, sin fallos ni omisiones; compilación
  de app y tools correcta con Python 3.10.
- Regresión de 268 evaluaciones históricas con invariantes de seguridad y
  justificación de penalizaciones retiradas. Se permite aprobar un seguimiento
  bajo la nueva política únicamente con evidencia, hash y causas ya documentadas;
  no se eliminan controles ni se agrega una lista de aprobados por archivo.
- El lote anterior de 36 conserva sus cuatro aprobaciones de r20 y pasa a siete
  bajo las correcciones y la política de seguimiento. Se verifican las 13
  correcciones de nombres y las confirmaciones previas de importe, saldo y plan.
- Reporte del lote de 95 cotejado con su checkpoint y comparación por llamada.

Las reglas se ejecutaron en Linux. La ejecución de esta revisión en Windows y
el cotejo humano de voces siguen pendientes. No se realizó una nueva
transcripción ni escucha humana en esta revisión. Los 13 problemas originales
no se declaran cerrados por esta entrega.

## Uso en Windows

La carpeta de la aplicación sigue siendo
proyecto\MRS_Speech_Analytics_v3.6.19_Revision. Se conserva Python 3.10 y Whisper.
Para aplicar solo las reglas, ejecutar REANALIZAR_CHECKPOINT.bat y seleccionar
el checkpoint del lote completo de 95, o el checkpoint r21 entregado con los
resultados. La consola debe mostrar 3.6.19-r21. Las salidas quedan en
%USERPROFILE%\MRS_Resultados\Reanalisis_MRS_r21_... .

El checkpoint de la versión antigua recibido como comparación está incompleto:
contiene 280 elementos, incluidos 170 pendientes y siete errores de aquella
ejecución. No representa 280 llamadas transcritas ni sustituye el lote completo
de 95 usado para validar esta entrega.
