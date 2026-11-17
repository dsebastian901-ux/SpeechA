# Corrección del procesamiento habitual — r54

## Uso

Extraer todo el paquete en una carpeta nueva. Abrir su iniciador y comprobar
3.6.19-r54. Crear o abrir el proyecto y ejecutar Procesamiento por lotes con
su Excel. No sustituir checkpoints como método de actualización. Se conservan
los audios y el Excel originales.

## Cambios generales

- Vigencia por llamada: reanudar un lote actualiza dictámenes antiguos,
  incluidos lotes terminados. Cambiar la cabecera no convierte todos los
  resultados en actuales. Archiva el checkpoint anterior y retira únicamente
  la copia clasificada administrada por ese proyecto, sin tocar originales.
- Recupera ASR compatible desde JSON UTF-8 con BOM o desde el checkpoint si
  falta el JSON separado. Cambios conocidos de modelo, configuración o archivo
  invalidan su caché. Un fallo del modelo no se oculta usando una lectura vieja.
- Conserva el contexto completo de cuenta y las confirmaciones vinculadas al
  mismo audio. La falta del Excel físico no borra las relaciones guardadas ni
  inventa las faltantes; conserva el modo de trabajo y el catálogo registrado.
- Los dígitos telefónicos, incluso parciales o con ecos, no se convierten en
  importes. La moneda explícita conserva prioridad. El saldo que el cliente
  refiere de una llamada anterior no se atribuye al gestor actual.
- Confirmar el nombre del receptor del recado no lo convierte en titular.
  Reconoce respuestas familiares y conversación financiera propia después de
  pregunta nominal. Un sí aislado o «sí, lo conozco» no acredita esos hechos.
- Audio nuevo: dos relecturas locales acotadas con beam 5 y 10, antes de cerrar
  REVISAR por identidad o contacto incompleto. Identidad: mismo nombre nominal
  y confirmación del titular en ambas, sin indicios de tercero. Contacto:
  coincidencia de sus diez dígitos, sin reconstrucción por ecos. Siguen siendo
  necesarios cuerpo y aceptación del recado y ausencia de rechazo final.
- Usa el modelo cargado, sin descargas, prompts de cuentas ni sustitución del
  ASR original. No recupera montos, tarjetas ni voces. Error o desacuerdo conserva
  el dictamen sustentado por la transcripción original. Guarda SHA-256 del audio
  y vinculación al texto y cuenta, sin marcar escucha humana.
- Conserva privacidad, quejas, trato, ARCO, negociación, referencia y espera.
  Lenguaje ofensivo detectado en relectura queda visible para confirmar hablante.
- Excel final: relectura realizada, identidad o contacto corroborados y alertas.
  Consolidación local de varios lotes contados por separado: motivos de no pago,
  gestor/supervisor/global, recomendaciones, errores y fallas graves; Excel y Word,
  con opciones general y detallado.

## Alcance comprobado

VALIDACION_R54.json distingue regresión de reglas, integración del servicio,
recuperación, copias y reportes. El adaptador decodifica PCM real con la salida
del modelo controlada en pruebas: eso no equivale a transcribir el lote real.
La comprobación histórica de 175 audios usa su ASR guardado y verifica integridad.

Aquí no están disponibles los pesos CTranslate2 del Faster-Whisper de producción.
Las lecturas ONNX de diagnóstico no se presentan como ese motor ni como escucha
humana. No se afirma haber resuelto todos los REVISAR reales ni se anuncia una
tasa nueva de aprobación de audios nuevos.

El acceso de usuarios/contraseñas y el instalador autónomo continúan pendientes.
