# Revisión 31: recepción de información y reporte de pago previo

## Llamada 59: recado aceptado que no se reconocía

El texto original contiene la oferta «le puedo dejar una información con usted»
y la respuesta «sí». Después se dicta un teléfono completo para que el titular
se comunique, y la persona se identifica como familiar. El detector reconocía
«recado» y «mensaje», pero no esta secuencia con «información». Por ello dejaba
sin confirmar la recepción y la transmisión, aunque ambas tenían evidencia.

Se reconoce la oferta con respuesta afirmativa, propósito de retorno y teléfono
completo de diez dígitos, también dictado por grupos en palabras. Se conserva
la evidencia original y no se rellenan ceros ni se reconstruyen dígitos faltantes.
Un «sí» aislado, un agradecimiento, una pregunta, una cita, una negación, una
respuesta condicional o palabras conocidas del gestor no prueban aceptación.
Sin propósito de retorno o sin teléfono completo, este nuevo método no confirma
la entrega. La identidad familiar sigue siendo un control independiente.

La 59 queda APROBADO con los mismos 100 puntos y sin retirar penalizaciones.
La evidencia del estatus aparece en el JSON y en la columna existente del Excel.
Se acredita la secuencia textual del recado, no verificación acústica de voces
ni certificación de cada dígito del teléfono de la hipótesis ASR.

## Llamada 67: pago reportado, no monto negociado

El usuario confirmó que el tercero informa de un pago y el gestor recibe esa
información. La frase «ya se hizo un pago» no era reconocida por el extractor
estructurado de pago previo. La pregunta de cuándo se hizo se convertía además
en una fecha futura candidata, y la explicación de cancelación con «saldo
restante» se interpretaba como una afirmación de regularización sin monto.

Se reconocen las formas declarativas «ya se hizo/realizó el/un pago» y se
excluyen negaciones, preguntas, hipótesis, citas y turnos conocidos del gestor.
Las fechas de ese antecedente no confirman una promesa futura. «Saldo restante»
por sí solo no afirma regularización; sigue sirviendo para detectar contradicción
si coexiste con una oferta real de liquidación o nueva negociación.

El reporte de un tercero no obliga a acreditar un monto negociado que no existió.
No se inventa el importe del pago ni se afirma que cubra el mínimo de Excel.
Los controles de monto, plazo, compromiso y seguridad siguen aplicándose cuando
se identifica una nueva negociación o instrucción de pago.

La 67 conserva REVISAR con 100 puntos. Se elimina el falso bloqueo financiero,
pero no se acredita un recado aceptado y transmitido que respalde el estatus
MENSAJE CON FAMILIAR. No se cambia el estatus del Excel por conjetura ni se usa
el parentesco para dar por recibido un mensaje.

## Resultado del lote y conservación

| Clasificación | r30 devuelta | r31 |
|---|---:|---:|
| APROBADO | 13 | 14 |
| REVISAR | 83 | 82 |
| FALLA_GRAVE | 7 | 7 |

Solo cambia de categoría la 59. Se conservan los 103 puntajes y sus penalizaciones,
las 13 aprobaciones previas, las 103 moras, 31 correcciones de nombre, cinco
lecturas, el parentesco confirmado de la 74 y PEN003 confirmado de la 10.
Se preservan tarjetas, cuentas, textos, segmentos, duraciones y hechos financieros.
No se modifica el umbral de aprobación ni se ejecuta Whisper o escucha humana
en la nube para esta revisión.

## Aplicación local

1. Extraer el ZIP completo y ejecutar `REANALIZAR_CHECKPOINT.bat` en la raíz.
2. Seleccionar el último `checkpoint_reanalizado.json` **final r30 de estas 103
   llamadas**, devuelto después de confirmar la divulgación de la llamada 10.
3. Esperar a que la consola muestre motor r31 y las rutas del nuevo checkpoint
   y `Reporte_Reanalisis_Reglas.xlsx`. La salida se crea en otra carpeta de
   `%USERPROFILE%\MRS_Resultados`.

No se repiten las lecturas ni las confirmaciones, no se selecciona otro Excel
ni se corrigen nombres otra vez. Los originales se conservan. La base siguiente
es el nuevo checkpoint final, no un archivo intermedio.

## Pruebas y límites

- 1.189 pruebas aprobadas, incluidas 52 nuevas de aceptación, teléfonos en
  palabras, parentesco, negación, citas, pago previo, fechas y seguridad.
- Las cuatro pruebas gráficas reales de la ventana corregida siguen pasando.
- 268 evaluaciones históricas: mismas categorías y cero violaciones de seguridad.
  Dos reportes de pago previo tenían falsos requisitos de convenio nuevo: se
  corrigieron cinco penalizaciones y sus puntajes, de 70 a 100. Se revisaron las
  declaraciones de pago pasado, fecha y seguimiento de comprobante. La única
  alerta de transferencia retirada correspondía a un pago ya realizado, sin
  instrucción futura ni cuenta no autorizada. Ambos casos permanecen REVISAR.
  Cada retiro tiene una comprobación de evidencia y hash del checkpoint; no hay
  retiros de otras penalizaciones sin revisar.
- Los lotes anteriores de 95 y 36 conservan categorías, puntajes, penalizaciones,
  lecturas y hechos confirmados, con 13 y siete aprobaciones respectivamente.
- Las 9.785 celdas del reporte de las 103 llamadas coinciden con el JSON.
- Se prueba en Python 3.10 y Tk gráfico real en Linux. Las salidas nativas r30
  ya se verificaron. El checkpoint final r31 devuelto también se comprobó;
  todavía no se recibió el Excel nativo correspondiente a r31.

## Checkpoint r31 devuelto y verificado

Se recibió el checkpoint final generado por el usuario. Coincide el hash de
origen con su último checkpoint final r30 y las 103 evaluaciones coinciden con
la entrega verificada, salvo la fecha de ejecución del análisis. No se encontraron
errores de procesamiento ni violaciones de los controles de seguridad.

Se confirman 14 APROBADO, 82 REVISAR y siete FALLA_GRAVE. Solo la 59 cambia de
categoría frente a r30 y conserva 100 puntos. La 67 mantiene 100 puntos, sin
alerta de privacidad o revisión financiera; conserva la revisión independiente
del estatus y del recado. La 10 mantiene PEN003 confirmado y la 74 conserva el
parentesco confirmado y su aprobación. Permanecen intactos los 103 puntajes y
penalizaciones, las 103 moras, 31 nombres corregidos, cinco lecturas, tarjetas,
cuentas, transcripciones y las dos confirmaciones del usuario.

La base para continuar es este último `checkpoint_reanalizado.json` r31. No
hace falta repetir el reanálisis ni descargar otra versión. Esta verificación
se limita al checkpoint recibido: no incluye un nuevo cotejo del Excel r31 ni
escucha acústica en la nube.

Los resultados y datos reales permanecen fuera del repositorio público. Esta
revisión corrige los bloqueos descritos; no cierra los otros casos pendientes.
