# Revisión 25: interlocutor, respuestas condicionadas y atribución de importes

Se continúa desde el checkpoint r24 recuperado, con las 22 correcciones de nombre
y las diez lecturas adicionales vinculadas. Esta revisión modifica reglas
reproducibles sobre texto guardado; no exige otra transcripción ni instala otro
Whisper. Los datos reales y sus reportes permanecen fuera de Git.

## Correcciones

- «Somos conocidos» y «somos amigos», como afirmación del interlocutor,
  identifican un tercero. No acreditan parentesco, aceptación del recado ni una
  voz humana verificada. Se excluyen preguntas, negaciones, citas y roles
  GESTOR/TITULAR; la frase no desplaza una identificación explícita del titular.
  Se conserva evidencia y tiempo cuando constan en los segmentos originales.
- Revisar los cargos antes de pagar y expresiones como «si corresponde, pagaré»
  se reconocen como respuestas condicionadas. Un «sí» inicial no oculta la
  condición. Preparar un comprobante, una pregunta o la intervención del gestor
  no revocan una promesa firme. Una aceptación posterior inequívoca prevalece.
- Un pago histórico no oculta la respuesta condicionada a una propuesta nueva.
  Con titular identificado y evidencia suficiente se detecta NO DEFINE FECHA
  DE PAGO. Una propuesta condicionada no se convierte en convenio aceptado.
  Se conserva la política del usuario para seguimientos de pago/comprobante.
- «Puede realizar un pago» y variantes no se agregan al importe de un depósito
  anterior. Se reconocen depósito/depositar como anclas financieras y las nuevas
  solicitudes de depósito conservan los controles de negociación.
- Mencionar una fecha que vence «cada mes» no convierte por sí solo una oferta
  actual en anualidad. Los cargos recurrentes se evalúan en su propia oración;
  no borran una propuesta posterior. Las anualidades y cargos mensuales reales
  siguen separados del importe propuesto.

## Resultado del lote de 95

| Dictamen | r24 recuperado | r25 |
|---|---:|---:|
| APROBADO | 12 | 13 |
| REVISAR | 81 | 80 |
| FALLA_GRAVE | 2 | 2 |
| ERROR técnico | 0 | 0 |

La llamada 83 recupera aprobación de calidad al reconocer la respuesta sin
compromiso firme y separar el pago histórico de la oferta actual. Su estatus es
NO DEFINE FECHA DE PAGO; no se afirma que haya aceptado la oferta ni que una
persona la haya confirmado en audio. Los 95 puntajes y todas las penalizaciones
de este lote permanecen iguales. No se cambia el umbral de aprobación.

La llamada 7 ahora identifica un tercero por la relación declarada, pero conserva
REVISAR por parentesco no acreditado, recado contradictorio y privacidad pendiente.
No se convierte RECADO REF1 en un recado familiar aprobado. Las voces de las
llamadas 6 y 11 y la aceptación del recado de la 7 siguen sin confirmación humana.

## Verificación y conservación

- 814 pruebas aprobadas, incluidas 49 nuevas de relación plural, condiciones,
  pagos anteriores, solicitudes nuevas, cargos recurrentes y controles
  independientes de privacidad, trato, tarjeta y seguridad del pago.
- Compilación de aplicación y herramientas.
- 268 evaluaciones históricas contra r24, 196 transcripciones únicas: ninguna
  clasificación cambia, cero violaciones de invariantes y cero retiros de
  penalizaciones sin documentar.
- El lote de 95 conserva textos, segmentos, duración, cuentas, tarjetas, las
  22 revisiones de nombre y los diez registros ASR válidos. Se comprueban las
  8.550 celdas de datos del reporte principal, que mantiene sus 90 columnas.
- El lote anterior de 36 conserva sus 7 aprobaciones, 13 revisiones de nombre y
  los registros de importes, saldo y parcialidades confirmados. No se transfieren
  hechos de un lote a otro por compartir número de fila.
- La evaluación de estas reglas se ejecutó en Linux con Python 3.10. No se
  ejecutó Whisper de nuevo ni se realizó escucha humana; falta comprobar r25
  directamente en Windows.

## Uso de la entrega

El paquete privado incluye `Checkpoint_r25_95_Audios.json` y su reporte ya
recalculado. Conservar este archivo como base del próximo reanálisis. No hace
falta procesar otra vez los audios ni seleccionar un checkpoint original para
obtener el reporte entregado. Las llamadas nuevas usan las reglas r25 al
procesarse con la aplicación completa y el modelo existente.

Los 80 REVISAR conservan sus motivos por llamada en el reporte privado. No se
afirma cierre de esos casos ni de los 13 problemas operativos.
