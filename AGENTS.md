# Instrucciones de trabajo para Codex — MRS Speech Analytics

> r67, instrucción de la usuaria del 27/nov/2026: aplicar [negociación cronológica y ciclo de escuchas](auditoria/r67-20261127/README.md). Una negativa inicial puede ser sustituida por un cierre posterior firme, con términos localizados; no por una lectura contradictoria del mismo turno. Distinguir tercera escucha pendiente, fallida, insuficiente, contradictoria y ejecutada. Ejecución sin resolución no equivale a pendiente; la insuficiencia sigue bloqueando el consumo favorable. No exigir una tercera lectura por variaciones léxicas sin discrepancia de hechos. Conservar ponderaciones, seguridad y mínimo de 80.

> r66, confirmación posterior de la usuaria (26/nov/2026): un acuerdo firme fuera del plazo autorizado, incluido vencimiento, conserva CONVENIO como dictaminación, FALLA_GRAVE como calidad y NEGOCIACION_INVALIDA como carpeta operativa. Prevalece sobre FALLA_MINIMA de fechas del 23/nov y sobre la gravedad pendiente del documento del 26/nov. No cambia los puntos de la matriz. Aplicar [criterios y pruebas r66](auditoria/r66-20261126/README.md). La tercera escucha requerida debe completarse y validarse antes de consumir evidencia favorable; una contradicción explícita no se elimina por mayoría. No incorporar MRS Academy.

> Actualización 25/nov/2026: aplicar [CRITERIOS_Y_ALCANCE r65](auditoria/r65-consolidacion-20261125/CRITERIOS_Y_ALCANCE.md). La instrucción más reciente de la usuaria exige REVISAR por queja de atención previa sola; no convertirla en rechazo para reducir revisión. Conservar rechazo por incumplimientos independientes confirmados. Este criterio prevalece sobre los cierres por queja descritos abajo.

## Objetivo
Corregir de manera integral MRS Speech Analytics v3.6.19 para Windows. Trabajar sobre `proyecto/MRS_Speech_Analytics_v3.6.19_Revision/` como base más reciente (versión 06). Los ZIP anteriores en `historial_versiones/` son referencias para recuperar reglas que funcionaban; **no reemplazar ciegamente la versión más reciente**.

## Reglas de colaboración
- El usuario exige resultados funcionales, no parches parciales ni explicaciones largas. Arreglar un error por vez y comprobar cada cambio, sin regresiones.
- No afirmar que una regla está validada solo porque el código se ejecuta; contrastar con casos y evidencias.
- No reducir penalizaciones para inflar aprobaciones. Resolver errores de dictaminación con criterios verificables.
- Mantener GUI, procesamiento de audio nuevo, Whisper, exportaciones Excel, clasificación de carpetas, instalación Windows, rendimiento y auditoría de llamadas. No obligar a retranscribir para cambios en reglas.
- Preservar datos personales; no subir checkpoints ni reportes reales a repositorios públicos.

## Reglas funcionales críticas
1. `RECADO REF1` y `RECADO REF2` equivalen a `MENSAJE CON FAMILIAR` **solo** si efectivamente se deja recado a un familiar. No inferir aceptación por «gracias por recibir el recado» dicho por el gestor. Diferenciar «no vive aquí», «no lo conozco», tercero desconocido y familiar.
2. `PEN003`: falla grave únicamente si está confirmada la revelación por el gestor a un tercero de información financiera protegida. Aclaración operativa del usuario: decir «saldo pendiente» o «saldo vencido» sin cantidad está permitido (confirmación de la usuaria el 08/nov/2026); revelar el importe del saldo a un tercero no lo está. El tercero que reporta un pago al gestor no constituye divulgación del gestor. Conservar protección sobre importes, deuda explícita, mora y tarjeta completa. Una palabra aislada o hablante incierto NO basta. Incertidumbre -> `REVISAR`, no aprobación automática ni falla grave falsa. Revelación confirmada -> nunca aprobar. Registrar confirmaciones por archivo y contexto, sin reescribir Whisper ni trasladarlas por fila.
3. Validar referencia de tarjeta de **16 dígitos** expresada en audio contra Excel, sin confundir números telefónicos, montos o fechas. Investigar referencia discordante `4812…5012 (número completo en el paquete privado de migración)`.
4. Derechos ARCO obligatorios cuando corresponda; omisión crítica. Lugares de pago: 2 autorizados cuando aplica, ninguno en recado familiar. Aclaración operativa del usuario: en convenio la omisión resta 20 puntos; puede aprobar con 80 si cumple todos los demás filtros, sin bloqueo adicional por esa omisión. Prohibir amenazas de visita/diligencia/cobro a domicilio en 1–2 PV.
5. Groserías al final de la llamada: recorrer audio/transcripción completa, identificar hablante y tiempo. No aprobar automáticamente llamadas con groserías confirmadas. `APROBADO_CON_EXCEPCION` exclusivamente cuando hostilidad/ofensas/lascivia del interlocutor impiden script y gestor mantiene profesionalismo; casos ambiguos -> `REVISAR`.
6. Maltrato previo denunciado bloquea aprobación. Evaluar propuestas de negociación, rechazo del cliente, dictaminación vs contenido, fechas y montos. Comprobante por WhatsApp: marcar incumplimiento solo si correspondía.
7. Estados separados: `APROBADO`, `APROBADO_SIN_ETIQUETAR` (>80% pero estatus no reetiquetable), `APROBADO_CON_EXCEPCION`, `REVISAR`, `FALLA_GRAVE`/`ERROR`. `RECADO REF1/REF2` no va a REVISAR por literalidad.

## Aclaración de identificación del titular
El usuario acepta identificación mediante pregunta nominal, respuesta y conversación sobre la propia tarjeta o pago, sin indicios de familiar ni transferencia. No exigir literalmente «soy yo / ella habla». Un sí aislado, agradecimiento o estatus del Excel no acredita identidad; conservar los filtros de tercero y actuación por otra persona.

## Regresión disponible
- `pruebas_checkpoints/`: 4 checkpoints del 23/oct/2026 con 27 llamadas cada uno (108 evaluaciones); un checkpoint anterior del 21/oct con lote mayor. Son datos de pruebas anteriores, no verdades de dictaminación.
- `reportes/`: resultados de las revisiones anteriores, discrepancias y auditorías. **No asumir que sus etiquetas son correctas**.
- Auditar ejemplos uno a uno, extraer evidencia textual, hablante y marcas temporales cuando estén disponibles; documentar falsos positivos y negativos.
- Crear pruebas unitarias y de integración para reglas; ejecutar regresión completa; reportar casos individuales, resultados y límites. Cuando falte audio original, indicarlo y no afirmar verificación acústica.

## Entregables
1. Código fuente completo corregido, instalable en Windows, sin perder funciones.
2. Suite de regresión reproducible con resultados por llamada y diferencias antes/después.
3. Registro conciso de errores solucionados y los que requieran audio/validación humana.

## Decisiones confirmadas para r49 (08/nov/2026)
- El usuario confirmó: NO_APROBADO ante incumplimiento claro y REVISAR ante dudas. El rechazo expreso de un recado puede cerrarse como NO_APROBADO cuando no haya dudas de seguridad independientes. Las fallas graves conservan prioridad.
- NO_APROBADO es un resultado de evaluación, no un estatus nuevo de grabación. Separarlo de REVISAR en carpetas, contador, GUI y reportes. La duración mínima ya existente de 60 segundos puede cerrarse de esa forma cuando está comprobada; no confundirla con la espera de 65 segundos.
- Un dato fonético o una repetición del teléfono no certifican sus dígitos. No completar un número parcial por ecos. La incapacidad del titular para anotar un WhatsApp no equivale al rechazo de un recado de un tercero.

## Decisiones y correcciones de r50 (08/nov/2026)
- La usuaria indicó conservar el estatus original en seguimientos por fallecimiento. La conservación requiere evidencia del seguimiento y no exime privacidad, trato ni otros controles.
- Las quejas declaradas pueden cerrar NO_APROBADO cuando tienen evidencia completa y no subsisten dudas de seguridad independientes. Una pregunta/hipótesis o un registro incompleto no se convierte en queja confirmada para cerrar.
- Separar ERROR técnico de REVISAR de calidad y contar únicamente REVISAR en el resumen por gestor. Mantener el detalle de las causas y evidencia en REVISION_PENDIENTE.
- Las atribuciones institucionales nuevas son textuales, limitadas a la misma cláusula con autopresentación; no son diarización ni escucha humana y no se extienden a otros turnos.

## Corrección ratificada por la usuaria para r51
- Un estatus de gestión diferente con evidencia suficiente, calidad >=80 y seguridad debe resolverse con APROBADOS_ETIQUETA_CORREGIDA, no REVISAR solo por la discrepancia. Conservar los bloqueos independientes y el requisito de fragmento probatorio.
- Distinguir resultado de calidad de estatus de gestión. No imputar al gestor una falta solo porque el motor no extrae evidencia.

## Decisiones integrales posteriores, 15/nov/2026
- Aplicar DECISIONES_OPERATIVAS_20261115.md: respuestas explícitas de la usuaria posteriores a estas reglas. Aviso genérico de atraso permitido; aprobación menor de 60 segundos solo con gestión completa y carpeta separada; espera >=65 segundos cuenta aunque anunciada; seguimiento de pago exige cobertura del mínimo; contacto previo confirmado y recepción con aviso condicionado son válidos; separar quejas bancarias de atención; NO_APROBADO por incumplimiento comprobado conserva alertas de seguridad pendientes visibles, con FALLA_GRAVE confirmada prioritaria.
- No producir una entrega por cada duda. Completar la revisión de todas las causas y entregar los cambios generales del programa conjuntamente.

## Aclaraciones del 23/nov/2026
- Aplicar [auditoria/CRITERIOS_OPERATIVOS_20261123.md](auditoria/CRITERIOS_OPERATIVOS_20261123.md), confirmado por la usuaria durante el cierre de los 34 fallos. Prevalece sobre las expectativas históricas contradictorias; todo ajuste de prueba debe quedar trazado.
- Rechazo del tercero: SE NIEGAN A TOMAR RECADO; puntuar los pasos ejecutables del gestor, sin inferir recepción ni rechazo automático de calidad. Calidad y seguridad cumplidas con etiqueta no corregible: APROBADO_SIN_ETIQUETAR, con motivo y estatus correcto pendientes en el reporte.
- Pago reportado vigente: confirmar cuánto pagó y solicitar comprobante. Gestionar diferencia sin aceptación determina NO DEFINE; solo comprobante con importe insuficiente o sin confirmar importe se resuelve como FALLA_MINIMA. No transformar un antecedente de otro periodo en pago/negociación actuales.
- FALLA_MINIMA es resultado de calidad no aprobado, con carpeta y contador propios, conservando puntos y alertas. Fecha fuera del plazo operativo de promesa no es negativa del titular; conservar acuerdo y falta mínima. Faltas graves confirmadas (incluida PEN005 por vencimiento) conservan prioridad; no se rebajan ni se amplían plazos.
