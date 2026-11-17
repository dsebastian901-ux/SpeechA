# r55 — correcciones del programa y recuperación local de dudas

Los cambios se aplican en Procesamiento por lotes, tanto a audio nuevo como
al recuperar transcripciones guardadas. Extraer en carpeta nueva y abrir
INICIAR_PROGRAMA.bat; verificar 3.6.19-r55. Utiliza Python y el modelo local
ya instalados. No es el instalador autónomo ni integra aún el inicio de sesión.

## Cambios comprobables

- La recuperación de contexto ya no se limita al ASR nuevo. Ante dudas de
  identidad o contacto intenta cargar el modelo instalado exclusivamente en
  modo local y leer dos fragmentos acotados. No retranscribe la llamada completa,
  no descarga modelos ni llama a una API. Sin modelo conserva el resultado
  original; intenta cargarlo una sola vez por ejecución del lote.
- La evidencia ya vinculada y válida no se vuelve a generar al actualizar reglas.
  Se conserva el texto original y se verifica audio, cuenta y firma de la evidencia.
- Separa a quien contesta del sujeto de la gestión: identificar a un receptor
  no lo convierte en titular cuando el motivo explícito es localizar a otra
  persona. Conserva referencias, negativas de conocimiento y transferencias.
- Reconoce «para mañana» como respuesta a una pregunta de pago y limitaciones
  personales explícitas de plazo. Una respuesta sobre WhatsApp/documentos no
  se convierte en compromiso; las condiciones y negativas se mantienen.
- Ordena los hechos de pago por su posición real en el texto. No toma «no puedo
  confirmar su pago si no puede anotar WhatsApp» como negativa del cliente.
  Conserva «no lo voy a pagar» como rechazo, aunque antes diga «claro, sí».
- Recupera el reporte de pago «ya» solo con comprobación posterior inequívoca
  de cuándo se hizo, y conserva la extracción independiente del importe y mínimo.
- Reconoce reporta/reporte, foto de pago y solicitudes con un antecedente de
  comprobante cercano. Una petición clara posterior resuelve la duda anterior;
  no confunde INE o comprobante de línea con el ticket de un pago.
- No certifica un número pequeño aislado después de «saldo» sin determinante
  monetario. La cantidad explícitamente ligada al saldo conserva su objeto
  aunque entre ambos se mencione la tarjeta. No completa cifras desde el Excel.
- Reconoce la oferta institucional presente de descuento/liquidación sin
  confundirla con historia, negación o palabras conocidas del interlocutor.
  Las prohibiciones de liquidación en las primeras moras siguen activas.
- Reconoce quejas concretas de corte de llamadas y atención grosera; no convierte
  una mera duda bancaria en queja. Incorpora culero/culera como expresiones
  ofensivas que requieren atribución, sin inventar el hablante.
- Un seguimiento de aclaración abierta con folio reportado, solicitud del folio
  y fecha de resolución no exige fingir una negociación nueva. No acredita
  resolución bancaria ni exime los controles de un pago reportado.
- Una fecha aceptada fuera del plazo se cierra como NO_APROBADO solo con titular,
  fecha, compromiso e importe confirmados y sin incertidumbre financiera propia.
  No aplica esa simplificación a planes de parcialidades ni a pagos anteriores.
  La causa ya resuelta no se conserva como otra alerta manual del mismo hecho.
- Las revisiones pendientes indican recepción del recado, cuerpo, contacto o
  resultado de pago que falta acreditar. La falta de formato de nombre_final
  para un estatus ya probado se reporta como datos de etiqueta, no como una
  nueva solicitud de escucha. Se mantienen los controles de tarjeta y cuenta.

## Validación y límites

VALIDACION_R55.json contiene resultados de regresión y comparación con el ASR
proporcionado. Las pruebas del servicio normal verifican decisiones, copias,
reportes, recuperación y ausencia de retranscripción completa. Controlan la
salida del modelo en las pruebas de relectura; no son reconocimiento real de
las grabaciones. En este entorno no están disponibles los pesos CTranslate2
small del programa, por lo que no se acredita aquí una tasa nueva obtenida
al retranscribir los audios reales con Faster-Whisper.

La comparación de las transcripciones existentes y la justificación individual
se conservan en los entregables privados. No se publican audios, checkpoints,
Excel de cuentas, reportes reales ni credenciales. No se rebaja el umbral ni
se conceden excepciones por número de llamada. La revisión pendiente no se
presenta como una falta confirmada del gestor solo por ausencia de extracción.
