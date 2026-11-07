# Revisión 15 · mínimo y plazos por mora

Se contrastó el manual operativo recibido, cuya portada indica versión 2.0,
con las hojas 04_Moras_Cortes, 05_Estrategias, 06_Reglas_Negociacion,
13_Reglas_Fechas y 14_Reglas_Montos. Los datos de cuentas y el manual original
se conservan privados. Las correcciones anteriores y la recuperación de
importes de la revisión 14 se mantienen.

## Regla aplicada

| Moras | Efecto del mínimo | Plazo |
| --- | --- | --- |
| 1PV, 2PV, 3PV | Regularización antes de fecha de pago; mensualidad vencida después | Corte/fecha de pago y vencimiento; admite la excepción de dos exhibiciones descrita abajo |
| 1-FLP | Mensualidad vencida; no liquidación total | Vencimiento y excepción de dos exhibiciones; no liquidación total |
| 3HN, 4PV, 5PV, 6PV, C1–C4, B, A | Liquidación, tomando pago_minimo del Excel como referencia y sin exceder saldo_total | Dentro del mes de la llamada; el vencimiento posterior no amplía el mes |

La excepción mensual es una instrucción expresa del usuario y prevalece sobre
el texto general de tres días de MOR045–MOR054 y RN004. Se conserva un vencimiento
anterior como restricción: no se amplía la fecha de origen del banco. El mes se
obtiene de la fecha de la llamada, no de la fecha de procesamiento.

Para dos exhibiciones en moras de regularización, el usuario confirma que la
primera debe quedar dentro de los tres días de la llamada y la segunda puede
quedar hasta siete días desde el primer pago. Ninguna puede superar el
vencimiento. Por ejemplo, llamada el 13, primer pago el 16 y segundo el 23
es temporalmente admisible si el vencimiento lo permite. Un primer pago fuera
de los tres días no obtiene la extensión. Sin dos fechas interpretables no se
inventa la excepción. Las moras de liquidación conservan además su límite mensual.

En las moras de liquidación, una oferta entre el mínimo y el saldo total no se
rechaza por ser inferior al saldo ni exige otro campo de autorización por esa
diferencia. Los importes menores al mínimo siguen sujetos a las reglas de abono
parcial y explicación; no se permite afirmar liquidación con un importe
insuficiente. Una mora desconocida o datos financieros incompletos conservan
revisión. No se inventa una política a partir de palabras de la transcripción.

## Otras correcciones necesarias para aplicar fechas

- La fecha de pago por corte se obtiene en el mes gestionado; ya no se desplaza
  automáticamente al mes siguiente cuando el día de pago es menor al corte.
- Las moras de liquidación no usan un corte del Excel para exigir una fecha
  límite que su tabla del manual no contempla.
- Se conservan las fechas de las parcialidades explícitas. Un recordatorio
  final de enviar el comprobante «hoy» no reemplaza la última exhibición.
- La infracción de plazo de tres días o de mes obliga a revisión; no se inventa
  una penalización bloqueante. PEN005 se conserva para una promesa posterior
  al vencimiento con aceptación confirmada. Una propuesta sin aceptación o
  un plan contradictorio conserva revisión, sin atribuir automáticamente falta grave.
- Fragmentos de teléfono dictados para comprobantes no son fechas del año 2077.
  «Ya le di un abono» es un reporte anterior, no una nueva promesa del viernes.

## Verificación y cambios visibles

- 403 pruebas aprobadas, compilación correcta y 268 evaluaciones históricas.
- Histórico: 262 REVISAR, 2 FALLA_GRAVE y 4 APROBADO; sin fallos de seguridad
  ni eliminaciones de penalización sin justificar. Tres casos se documentan
  con hash y evidencia específica de teléfono o pago anterior, conservando revisión.
- Lote de tres con evidencia recuperada: los tres siguen REVISAR. La llamada 23
  tiene importe válido para liquidación C4 y deja de indicar descuento no verificable;
  conserva el control de evidencia de recuperación. Las otras dos conservan saldo
  discrepante y parcialidades contradictorias; se muestra además el plazo de la última.
- Lote de 36 con textos guardados: conserva 1 APROBADO y 35 REVISAR.
  La llamada 3 mantiene aceptación e importes y se aprueba bajo la excepción
  confirmada: primer pago el día de la llamada y segundo siete días después,
  dentro del vencimiento. La 32 cumple el plazo extendido, pero no se aprueba
  porque existen importes contradictorios para la segunda parcialidad.
- El Excel añade al final Efecto pago mínimo, Política de plazo y Fecha máxima
  de negociación. Se conserva el orden de las 77 columnas anteriores.

Los 13 problemas no se consideran cerrados. La discrepancia entre tarjetas de
nombre_final y numero_de_tarjeta y la columna powe del Excel se registraron en
la auditoría privada y no se modifican en esta revisión. La comprobación de
esta nueva regla se hizo en Linux; falta probar la revisión 15 en Windows.

## Aplicar a resultados existentes

Extraer el paquete completo y ejecutar REANALIZAR_CHECKPOINT.bat. Seleccionar
el checkpoint_reanalizado.json final de la recuperación de la revisión 14,
que ya incluye evidencia de importes. La consola debe mostrar 3.6.19-r15.
Usar el checkpoint y Excel nuevos de Reanalisis_MRS_r15_...; no hace falta
instalar otro Whisper ni repetir la transcripción del lote.
