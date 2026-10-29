# Revisión 23: bloque recibido y evidencia adicional de audio

El ZIP recibido contiene las llamadas 2, 3, 4, 5, 6, 7, 8, 9, 11 y 12 del lote
de 95. Se decodificaron los diez archivos completos, se registraron sus hashes y
se comprobaron nombres y duraciones contra el checkpoint: 2.064,6 segundos en
total. Los datos privados y los reportes de evidencia permanecen fuera de Git.

La escucha humana y la nueva transcripción no se realizaron en esta nube. El
modelo no está en la caché actual y sus solicitudes públicas en Hugging Face
fallan con proxy CONNECT 403. Una configuración guardada que diga «modelo
cacheado» de una instancia anterior no acredita su presencia en esta instancia.
Se corrigieron las instrucciones guardadas de arranque; guardarlas no aplica
permisos de red ni publica un entorno. No se requieren tokens para este modelo.

## Correcciones comprobadas con el texto guardado

- Enumerar bancos como opciones generales no exige tratar toda la llamada como
  una transferencia sin CLABE. La excepción exige dos alternativas autorizadas,
  sin instrucción bancaria concreta, destino, CLABE, convenio ni transferencia
  nueva desarrollada. No suma los bancos a los lugares válidos ni certifica sus
  datos. Las transferencias reales y las preguntas del cliente, incluso con una
  coma intermedia, conservan validación independiente.
- Se reconoce la negación «no se pueda hacer transferencia».
- Se detecta «qué poca madre», incluido el cierre; con emisor desconocido se
  bloquea aprobación sin inventar falta grave. Un emisor GESTOR explícito conserva
  el tratamiento crítico que ya existía para groserías.
- La evidencia de privacidad se reúne por oración, conservando tiempos y solo
  los roles que sustentan los segmentos. Una frase «presenta una mensualidad
  vencida» no desaparece al cruzar una ventana acústica. Se reconoce también la
  mensualidad en singular. Sin voz atribuida conserva REVISAR, no PEN003 falso.
- «¿No la conoce para nada? No, para nada» confirma desconocimiento; «no» solo,
  una respuesta del gestor o una contradicción posterior no lo confirman.
- «Tengo años con este número» acredita una antigüedad cualitativa; no inventa el
  número de años ni exime el resto del procedimiento ARCO o su correo.
- Una fecha final introducida por «confirmo» no pierde prioridad ante una
  notificación anterior. La respuesta «de mil quinientos» a una pregunta de
  importe se extrae sin exigir la palabra pesos.
- Una enumeración del gestor puede responder a una pregunta de dónde cubrir el
  pago. Los establecimientos que menciona solo el cliente no acreditan el script.

## Resultado del lote por reglas

| Resultado | r22 | r23 |
|---|---:|---:|
| APROBADO | 11 | 12 |
| REVISAR | 82 | 81 |
| FALLA_GRAVE | 2 | 2 |
| ERROR de reanálisis | 0 | 0 |

En los diez recibidos, la llamada 2 recupera aprobación al corregir el bloqueo de
la lista de bancos. Las otras nueve conservan revisión. Estas son evaluaciones
de reglas sobre las transcripciones anteriores; no certificaciones acústicas.

El reporte privado por llamada explica aceptación de recados, atribución de
información financiera, importes y acuerdos, correo ARCO y expresiones de cierre
que todavía necesitan cotejo. No se transfieren hechos confirmados de otro lote
por compartir un número de fila.

## Herramienta para la lectura local pendiente

`REVISAR_BLOQUE_AUDIOS.bat` pide el checkpoint completo y la carpeta de hasta diez
audios. Usa el modelo original ya cacheado con `local_files_only=True`; no
instala ni descarga otro Whisper. Rechaza nombres ambiguos, duplicados y un JSON
de lectura que se seleccione en lugar del checkpoint. Una carpeta mayor de diez
llamadas se rechaza antes de cargar el modelo.

Genera una lectura completa con marcas por palabra y una lectura de los últimos
20 segundos sin VAD. Conserva ambas hipótesis, el texto y segmentos originales,
hash del checkpoint y de cada audio, duración y errores. Guarda por separado
`revision_audios_bloque.json` y `Comparacion_Bloque_Audios.xlsx`. No modifica el
lote ni sus validaciones, no mueve ni renombra audios y no aprueba llamadas.
El nuevo JSON se comparte para revisar evidencia; no es un checkpoint del lote.

El modelo ausente falla antes de crear una salida vacía. Lecturas sin segmentos,
sin texto, con duración discordante o audio modificado se registran como error;
no se cuentan como completadas. Campos de aprobación, confirmación humana o
roles que pudiera aportar un lector alternativo no se importan como hechos.

## Verificación

- 734 pruebas unitarias/integración y compilación de aplicación/herramientas.
- 268 evaluaciones históricas contra r22: sin violaciones de invariantes ni
  retiros de penalizaciones sin causa; las clasificaciones históricas no cambian.
- Regresión contra la migración original con
  `tests/reviewed_r22_from_original.json`, conservando hashes y pruebas de causa.
- Las 36 llamadas anteriores conservan sus 7 aprobaciones, 13 correcciones de
  nombre y todos sus registros de importes, saldo y acuerdo final.
- Los 95 resultados conservan transcripciones, segmentos, tarjetas, datos de
  cuenta y validaciones. El Excel principal mantiene sus 87 columnas.
- Las pruebas del nuevo lector usan dobles explícitos del modelo. Se verifican
  preservación del origen, cruce exacto, errores, caché ausente y exclusión de
  roles/aprobaciones falsos. No equivalen a inferencia real ni prueba en Windows.

No se afirma cierre de los diez audios, de las 81 pendientes ni de los 13 problemas
operativos. Se conserva Python 3.10 y la instalación existente de Whisper.
