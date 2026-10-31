# Revisión 27: comparación anterior–r26 y recados

Se compararon los dos checkpoints y reportes devueltos del lote nuevo. Hay 103
archivos coincidentes, sin duplicados; las cuentas y duraciones son iguales.
El usuario confirma el mismo Excel y modelo. Los parámetros guardados también
coinciden: small, CPU/int8, beam 5, VAD activo y sin marcas de palabra. La versión
anterior no serializa una revisión del motor ni versiones de dependencias.
No se afirma que ambas instalaciones sean idénticas en todos sus componentes.

86 textos y segmentos son idénticos; 17 difieren. Se evaluaron las transcripciones
anteriores con las reglas r26: también obtienen cero aprobadas. La caída no se
explica solo por la nueva transcripción. Las etiquetas anteriores son referencia
para comparar, no evidencia de cumplimiento.

## Correcciones verificadas

- Una negativa a dar cantidades, información o descuentos no equivale a rechazar
  el recado. Los rechazos de mensajes reales siguen bloqueando aprobación.
- Se reconocen solicitudes de recado en variantes naturales, ofrecimientos del
  receptor para tomarlo, aceptación de anotar en contexto de mensaje y repetición
  del teléfono solicitada. Una pregunta sin respuesta, una intervención conocida
  del gestor, una cita o un agradecimiento no acreditan recepción.
- El parentesco puede contestarse a una pregunta concreta o confirmarse con «sí».
  Una pregunta posterior («es mi marido, ¿por qué?») no borra la afirmación.
  Una pregunta de confirmación sin respuesta («es mi hermano, ¿verdad?») sigue
  sin acreditar parentesco. Se conservan negaciones y contradicciones.
- Se reconoce al conocido que responde a la pregunta de relación, variantes de
  ausencia y la recepción de un mensaje dirigido a otra persona identificada.
  No se infiere parentesco desde Excel. El método queda registrado sin atribuir
  voz humana ni convertirlo en evidencia de PEN003.
- Se reconocen variantes de llamada de retorno y número telefónico. Diez dígitos
  dictados para devolver una llamada no se confunden con una tarjeta incompleta.
  Una referencia explícita incompleta sigue en revisión; una tarjeta completa
  conserva su comparación de 16 dígitos.
- «Su adeudo» conserva revisión de privacidad cuando no está atribuida la voz.
  No se omite ese riesgo para recuperar una aprobación anterior.
- En ACLARACION no se resta por falta de intento de cobranza. No se da por
  completo el trámite ni se eximen negociaciones nuevas usando esa etiqueta.

## Datos de salida y uso local

El lote tiene 31 identificadores de nombre_final distintos de numero_de_tarjeta.
La diferencia está en los datos compartidos por ambas versiones. La herramienta
`REANALIZAR_CON_TARJETA_EXCEL.bat` aplica la política previa del usuario: usar la
tarjeta Excel como origen y corregir solo el identificador de salida en una copia.
Cada cambio conserva nombre anterior, nuevo y fuente de autorización. No se
cambian tarjetas, importes, fechas ni el archivo Excel de cuentas original.

El lanzador está en la raíz del ZIP y dentro de la aplicación. Seleccionar el
`batch_checkpoint.json` de **r26 del lote nuevo de 103**. No elegir aquí el lote
anterior de 95 ni el JSON de lecturas. Genera otro checkpoint y Excel; imprime
motor, rutas y 31 correcciones. No exige instalar otro Python/Whisper, procesar
audios ni incorporar diez lecturas. Las lecturas y confirmaciones existentes
se preservan si el checkpoint ya las contiene. La reconstrucción R25 anterior
mantiene su validación de origen y su requisito de lecturas cuando corresponde.

El reanálisis no copia ni renombra físicamente los audios. La clasificación que
aparece en Excel es el resultado calculado. El procesamiento normal de audios
nuevos conserva su copia y clasificación con las mismas reglas.

## Resultados calculados

| Resultado | Anterior | r26 | r27 con nombres corregidos |
|---|---:|---:|---:|
| APROBADO | 51 | 0 | 11 |
| REVISAR | 1 | 97 | 86 |
| FALLA_GRAVE | 2 | 6 | 6 |
| NO_APROBADO_MENOR_80 | 30 | 0 | 0 |
| MAL_DICTAMINADO | 19 | 0 | 0 |

Diez aprobaciones anteriores se recuperan; otra llamada antes MAL_DICTAMINADO
se aprueba. De las otras 41 aprobaciones anteriores, 22 requieren revisión de
privacidad, una tiene bloqueo ARCO y 18 mantienen otras verificaciones.
Estos grupos no significan 41 faltas confirmadas. Las reglas r27 sobre los textos
anteriores obtienen diez aprobaciones; la diferencia de una corresponde a ASR,
sin evidencia de una negativa contradictoria en la recepción del recado.

Se preservan todos los resultados de origen, cuentas y tarjetas. Solo cambian
31 nombres y evaluaciones derivadas. Dos PEN_SIN_INTENTO_NEGOCIACION se retiran
por causa documentada: ACLARACION y familiar antes identificado como titular.
No se bajan umbrales ni se eliminan controles de privacidad, ARCO, trato o pago.

## Pruebas y límites

- 984 pruebas aprobadas, 91 nuevas de recados, relaciones, teléfonos y reanálisis
  autorizado sin lecturas. Aplicación y herramientas compiladas en Python 3.10.
- 268 evaluaciones históricas frente a r26: cero cambios de clasificación,
  cero violaciones de invariantes y cero retiros sin causa documentada.
- Lote anterior de 95: 13 APROBADO, 80 REVISAR y 2 FALLA_GRAVE; se conservan
  22 revisiones de nombre y diez registros ASR. Lote anterior de 36: 7 APROBADO
  y 29 REVISAR; 13 revisiones de nombre y confirmaciones financieras intactas.
- Se comprueban las 9.785 celdas del reporte nuevo, 9.025 del lote anterior de
  95 y 3.420 del de 36 contra los JSON recalculados. El reporte conserva 95 columnas.
- No se ejecutó Whisper ni se escucharon los audios nuevos. No se crean hechos
  humanos de voz, recados, importes o hostilidad. R27 aún no tiene devolución
  de ejecución nativa Windows; la validación nativa r25 sigue siendo histórica.

La mora/asignacion está vacía en las 103 cuentas de ambas versiones. Falta el
Excel de cuentas de este lote para investigar la carga; no se rellena desde nombres.
Siguen pendientes las llamadas con dudas reales de identidad, privacidad, ARCO,
estatus o transcripción. No se certifica el cierre de los 13 problemas ni se
recomienda ampliar a 400 antes de revisar los resultados de este bloque.

Los checkpoints, reportes y comparación por llamada contienen datos privados y
permanecen fuera de Git. El ZIP de código permite generar la salida en el PC.
