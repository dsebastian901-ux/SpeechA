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

- 1.133 pruebas aprobadas; 69 nuevas de privacidad, contexto, conservación,
  selección, cancelación, mención genérica, importes y voces.
- 268 evaluaciones históricas comparadas con r29: cero cambios de categoría,
  cero violaciones de seguridad y cero retiros de otras penalizaciones.
- Los lotes anteriores de 95 y 36 conservan categorías, puntajes, penalizaciones,
  nombres, lecturas y hechos financieros: 13 y siete aprobaciones respectivamente.
- 9.785 celdas del reporte del lote actual cotejadas con el checkpoint, sin diferencias.
- r29 devuelta por el usuario ya se verificó. El registro r30 se probó en Linux
  con Python 3.10 y selección simulada de archivos; falta la devolución nativa
  de este nuevo paso en Windows. No se declara escucha acústica en la nube.

No se cierran los otros controles pendientes por esta corrección. Los datos
reales y resultados privados permanecen fuera del repositorio público.
