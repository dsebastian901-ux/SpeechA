# MRS Speech Analytics 3.6.19-r53

Criterios confirmados conjuntamente por la usuaria e integrados al procesamiento normal y al reanálisis:

- Aprobación de llamadas menores de 60 segundos únicamente con gestión completa, al menos 80 puntos y seguridad. Carpeta APROBADAS_DURACION_MENOR. Si se corrige el estatus, se aplica a esa única copia y se registra en el reporte de reetiquetadas.
- Espera de 65 segundos o más bloquea aunque haya sido anunciada. Los huecos ASR son indicios para cotejar, no pruebas de silencio acústico.
- El seguimiento de pago exige importe comparable que cubra el mínimo. Un monto desconocido queda pendiente; insuficiencia comprobada sin gestionar complemento rechaza la llamada. El reporte no acredita un depósito bancario.
- Contacto previamente confirmado por el receptor es válido sin repetir dictado. La recepción ya cumplida no se invalida por «cuando lo vea» o «si logro comunicarme».
- Quejas de atención/cobranza bloquean; desacuerdos exclusivamente con cargos/intereses no se convierten automáticamente en mala atención.
- Un incumplimiento confirmado cierra NO_APROBADO aunque subsista otra duda. Las alertas pendientes se conservan visibles y por separado en checkpoint, resumen, ALERTAS_PENDIENTES y Word. Una falta grave confirmada conserva prioridad. No se aprueba una duda de seguridad.
- Avisos genéricos de atraso sin cantidades ni meses/mensualidades están autorizados. Importes, deuda explícita, mora detallada, tarjeta completa y solicitudes de cobro protegidas conservan controles.

Correcciones generales adicionales: separar la propuesta del gestor de la aceptación; no imponer obligaciones de nuevo convenio solo por PP en el Excel; ligar la fecha elegida a la respuesta; excluir horas de las cantidades de pago; reconocer respuestas nominales y autorreferencias con contexto; conservar condicionales, citas, transferencias y respuestas de terceros.

El Excel original permanece intacto. La tarjeta de numero_de_tarjeta sigue siendo la autoridad. Reetiquetar cambia solamente el bloque de estatus. Se conservan derechos ARCO, reglas por mora, umbral de 80 y descuento de 20 puntos por faltar dos lugares cuando aplica.

Se mantienen Python y Whisper locales existentes. Extraer en carpeta nueva y abrir INICIAR_PROGRAMA.bat. Esta distribución de código completo no incluye un nuevo instalador autónomo, modelo Whisper ni gestión de usuarios por USB.

Las pruebas de reglas sobre ASR guardado y el flujo con ASR controlado no equivalen a escuchar o retranscribir audio nuevo. El detalle de validación acompaña la entrega. Las voces y palabras irrecuperables de una transcripción siguen requiriendo su audio; las relaciones ausentes requieren el Excel de origen. No hay cuotas de aprobación ni excepciones por número de llamada.
