# Revisión 13 · finiquitos y fechas condicionales

Conserva las correcciones anteriores y añade dos ajustes reproducidos al
contrastar los tres audios pendientes con sus textos guardados. Los ocho
audios recibidos hasta ahora tienen una nueva transcripción automatizada con
Whisper small, CPU int8, español, beam 5, VAD y tiempos por palabra. No falta
ninguno de los tres archivos solicitados en la revisión anterior.

## Correcciones y evidencia

- Una oferta de descuento para «finiquitar la deuda» se reconoce como liquidación
  total. Que el importe quede entre el mínimo y el saldo no basta para autorizar
  ese descuento. Sin acreditación de su autorización se conserva REVISAR.
  También se cubren ofertas divididas entre ventanas de Whisper o seguidas de
  una pregunta. Negaciones, relatos históricos y voces identificadas como
  interlocutor no se convierten en nuevas ofertas del gestor.
- «Lo podría hacer» y «yo pagaría» en contexto de pago acreditan una respuesta
  condicional. Permiten identificar NO DEFINE FECHA DE PAGO sin inventar un
  convenio firme. Una aceptación inequívoca posterior puede reemplazarla.
- La discrepancia de saldo inicial y los importes contradictorios para una misma
  parcialidad siguen bloqueando aprobación. No se corrigen automáticamente las
  cantidades transcritas usando los valores esperados de Excel.

Sobre las nuevas transcripciones, la llamada 12 pasa de estatus no determinado
a NO DEFINE FECHA DE PAGO; sigue REVISAR por saldo discrepante. La 23 pasa de
APROBADO con el motor r12 a REVISAR con r13 por descuento no verificable: se
corrige una aprobación indebida reproducida con el mismo texto nuevo. La 32
conserva CONVENIO como estatus y REVISAR como dictamen por contradicción de la
segunda parcialidad. Una etiqueta de convenio no acredita calidad aprobada.

## Verificación

- 289 pruebas aprobadas y compilación de app y herramientas correcta.
- Regresión completa: 268 evaluaciones, 196 textos distintos y 5 checkpoints;
  259 REVISAR, 5 FALLA_GRAVE y 4 APROBADO. Sin fallos de seguridad ni
  eliminaciones de penalización sin justificación. Se conserva el registro
  de cambios revisados de las versiones anteriores.
- Reanálisis del lote completo de 36 con los textos guardados: 35 REVISAR,
  1 APROBADO, sin errores de ejecución. Las tres transcripciones nuevas se
  contrastaron por separado con los motores r12 y r13.
- Originales, transcripciones, reporte comparativo y evidencia temporal se
  conservan en el área privada, fuera de Git.

La transcripción nueva recupera información que faltaba en el checkpoint,
incluido el importe de una oferta. Reanalizar reglas no recupera palabras
omitidas por Whisper. Subsisten errores de reconocimiento de marcas y palabras;
no se interpreta una marca mal transcrita como prueba acústica de omisión.
La atribución de voces y el tono requieren validación humana. Los 13 problemas
no se consideran cerrados y falta la prueba completa en Windows.

## Probar esta entrega

1. Conservar los audios, checkpoint y reportes anteriores.
2. Extraer el paquete completo y ejecutar REANALIZAR_CHECKPOINT.bat desde esta
   versión, seleccionando el checkpoint previo. Debe mostrarse
   «Revisión del motor: 3.6.19-r13»; usar el archivo que la consola identifica
   como «Checkpoint nuevo» dentro de Reanalisis_MRS_r13_...
3. Para contrastar también el reconocimiento, procesar los tres audios en una
   carpeta de prueba independiente. Comparar sus resultados con el reanálisis
   anterior. No es necesario instalar otro Whisper ni cambiar Python 3.10.
