# Revisión 30: mención genérica y divulgación financiera confirmada

## Criterio operativo aclarado por el usuario

El usuario confirma que decir «saldo pendiente» sin comunicar la cantidad es
correcto en su operación. Se distingue esa mención genérica del importe del saldo.
La aclaración se aplica en privacidad a las transcripciones originales, lecturas
adicionales y selección de fragmentos para registrar divulgación confirmada.

No se elimina protección sobre importes numéricos o expresados en palabras,
tarjeta completa, deuda explícita, mora o mensualidades vencidas. Un teléfono,
horario o terminación de tarjeta no convierte la mención genérica en un importe.
«Saldo pendiente. Son 1500 pesos» conserva la atribución del importe: solo es
divulgación confirmada cuando lo dice el gestor ante un tercero confirmado.
El reporte de un pago por parte del interlocutor no es divulgación del gestor.

## Evidencia del lote de 103

| Llamada | Confirmación del usuario | Resultado r30 |
|---|---|---|
| 10 | El gestor proporciona el monto del saldo a un tercero | FALLA_GRAVE, PEN003 de 100 puntos |
| 59 | El gestor dice «saldo pendiente», sin importe | Sin alerta de privacidad; REVISAR por recado pendiente |
| 67 | El tercero reporta un pago y el gestor recibe información, sin dar saldo | Sin alerta de privacidad; REVISAR por otros controles |

La 10 tiene un fragmento financiero en la lectura adicional incorporada, entre
25,87 y 30,89 segundos. La atribución a gestor y tercero procede de la confirmación
del usuario, no de la lectura ASR. No se reescriben los textos ni se atribuyen
automáticamente las demás intervenciones. La pregunta por el saldo no autoriza
al gestor a revelar la cantidad a un tercero.

El nuevo registro `privacy_disclosure_confirmation` queda ligado a archivo,
texto, segmentos, duración, cuenta y fragmento de evidencia. Si procede de una
lectura adicional, también se verifica la lectura y su checksum. No se traslada
la confirmación por el número de fila. Un registro incompleto, alterado, revocado
o ajeno al contexto conserva revisión y no genera un PEN003 falso. El hecho
válido se conserva al reanalizar y no se duplica al incorporarlo otra vez.

## Resultado y conservación

| Clasificación | r29 devuelta | r30 con confirmación de la 10 |
|---|---:|---:|
| APROBADO | 13 | 13 |
| REVISAR | 84 | 83 |
| FALLA_GRAVE | 6 | 7 |

Solo la 10 cambia de categoría y puntaje: de 100 a cero por PEN003 confirmado.
Se conservan los otros 102 puntajes, todas las penalizaciones anteriores, las
103 moras, 31 correcciones de nombre, cinco lecturas y el parentesco de la 74.
La mención genérica era la única causa de revisión de privacidad en otras diez
llamadas, incluidas 59 y 67: se retira esa alerta, sin aprobarlas por defecto.
Los demás controles de estatus, recado, negociación, seguridad y trato siguen
aplicándose y las 13 aprobaciones previas se mantienen.

## Uso en Windows

1. Extraer el ZIP completo y abrir `CONFIRMAR_DIVULGACION_A_TERCERO.bat` desde
   la carpeta principal.
2. Seleccionar el checkpoint **final r29 de estas 103 llamadas**.
3. Indicar **10** y seleccionar **ASR_ADICIONAL, 25,87–30,89 segundos**.
4. Marcar que el gestor dice la información y que la recibe un tercero: son
   los dos hechos que el usuario ya confirmó para esta llamada.
5. Pulsar «Registrar confirmación y generar reporte» y conservar el nuevo
   `checkpoint_reanalizado.json` como base.

Los campos comienzan vacíos y la ventana muestra la identidad de la llamada y
el texto del fragmento. Se generan copias en una carpeta independiente dentro
de `%USERPROFILE%\MRS_Resultados`. El reporte muestra PEN003, la confirmación
del usuario y su evidencia en las columnas existentes; conserva las 95 columnas.
La operación recalcula reglas sin Whisper, no mueve audios y no cambia originales.

## Verificación y límites

- 1.137 pruebas aprobadas; 73 nuevas de privacidad, contexto, conservación,
  selección, cancelación, mención genérica, importes y voces.
- 268 evaluaciones históricas comparadas con r29: cero cambios de categoría,
  cero violaciones de seguridad y cero retiros de otras penalizaciones.
- Los lotes anteriores de 95 y 36 conservan categorías, puntajes, penalizaciones,
  nombres, lecturas y hechos financieros: 13 y siete aprobaciones respectivamente.
- 9.785 celdas del reporte del lote actual cotejadas con el checkpoint, sin diferencias.
- r29 devuelta por el usuario ya se verificó. El registro r30 se probó en Linux
  con Python 3.10 y Tk gráfico real. Después se recibieron del usuario los dos
  JSON y el Excel finales de r30: las 103 evaluaciones coinciden con la entrega
  verificada, salvo fechas de ejecución. No se declara escucha acústica en la nube.

### Corrección de ventana de confirmación

El usuario informó que la herramienta quedaba esperando después del número
de llamada. Se reprodujo en Tk real: el diálogo quedaba retirado e invisible,
pero retenía teclado y ratón. La causa era declararlo transitorio de la raíz
oculta que se usa para seleccionar archivos y número de llamada.

La confirmación solo se hace transitoria cuando la raíz es visible. Se espera
a que aparezca antes de capturar entrada y se le da foco. No se preseleccionan
fragmentos ni hechos. Se añaden mensajes de progreso al buscar los fragmentos,
abrir la confirmación y generar el checkpoint y el reporte.

Cuatro pruebas con ventanas Tk reales verifican raíz oculta y visible, bloqueo
de guardado hasta confirmar ambos hechos, cancelación y el flujo completo desde
el número hasta el checkpoint y Excel. El flujo gráfico también se ejecutó con
el checkpoint real de 103: los resultados coinciden con r30 y se cotejaron las
9.785 celdas del Excel sin diferencias. Las 268 evaluaciones históricas no cambian.
Esta comprobación gráfica se hizo en Linux; no se declara una nueva ejecución
gráfica observada directamente en Windows. El motor sigue siendo r30 y las reglas
no cambian por este arreglo.

### Verificación de las salidas devueltas por el usuario

Se verificaron `checkpoint_con_divulgacion_confirmada.json`,
`checkpoint_reanalizado.json` y `Reporte_Reanalisis_Reglas.xlsx` generados por el
usuario. Coinciden el hash del checkpoint de origen, el del archivo intermedio y
el registro de divulgación de la llamada 10. Las cinco lecturas, el parentesco
confirmado de la 74, las 103 moras y 31 correcciones de nombre permanecen intactos.
Las 103 evaluaciones coinciden con el resultado en nube y las 9.785 celdas del
Excel recibido con el JSON: cero diferencias y cero violaciones de seguridad.

La 10 tiene FALLA_GRAVE y PEN003 de 100 puntos; las otras 102 conservan sus
puntajes y penalizaciones. Las 59 y 67 no tienen alerta de privacidad y mantienen
revisión independiente de estatus y recado; la 67 también conserva un control de
negociación pendiente. Se mantienen las 13 aprobaciones y el lote final contiene
83 revisiones y siete fallas graves.

La base para continuar es `checkpoint_reanalizado.json`. El archivo
`checkpoint_con_divulgacion_confirmada.json` es intermedio y conserva todavía
los dictámenes previos. No es necesario repetir el registro ni descargar otra
versión para conservar el resultado comprobado. La verificación acredita las
salidas de registro, reanálisis y exportación; no supone observación directa de
la ventana de Windows ni certificación de todos los controles o audio nuevo.

No se cierran los otros controles pendientes por esta corrección. Los datos
reales y resultados privados permanecen fuera del repositorio público.
