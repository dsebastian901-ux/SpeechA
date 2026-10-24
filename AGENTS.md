# Instrucciones de trabajo para Codex — MRS Speech Analytics

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
2. `PEN003`: falla grave únicamente si está confirmada la revelación por el gestor a un tercero de deuda, saldo, tarjeta o atraso. Una palabra aislada o hablante incierto NO basta. Incertidumbre -> `REVISAR`, no aprobación automática ni falla grave falsa. Revelación confirmada -> nunca aprobar.
3. Validar referencia de tarjeta de **16 dígitos** expresada en audio contra Excel, sin confundir números telefónicos, montos o fechas. Investigar referencia discordante `4812…5012 (número completo en el paquete privado de migración)`.
4. Derechos ARCO obligatorios cuando corresponda; omisión crítica. Lugares de pago: 2 autorizados cuando aplica, ninguno en recado familiar. Prohibir amenazas de visita/diligencia/cobro a domicilio en 1–2 PV.
5. Groserías al final de la llamada: recorrer audio/transcripción completa, identificar hablante y tiempo. No aprobar automáticamente llamadas con groserías confirmadas. `APROBADO_CON_EXCEPCION` exclusivamente cuando hostilidad/ofensas/lascivia del interlocutor impiden script y gestor mantiene profesionalismo; casos ambiguos -> `REVISAR`.
6. Maltrato previo denunciado bloquea aprobación. Evaluar propuestas de negociación, rechazo del cliente, dictaminación vs contenido, fechas y montos. Comprobante por WhatsApp: marcar incumplimiento solo si correspondía.
7. Estados separados: `APROBADO`, `APROBADO_SIN_ETIQUETAR` (>80% pero estatus no reetiquetable), `APROBADO_CON_EXCEPCION`, `REVISAR`, `FALLA_GRAVE`/`ERROR`. `RECADO REF1/REF2` no va a REVISAR por literalidad.

## Regresión disponible
- `pruebas_checkpoints/`: 4 checkpoints del 23/oct/2026 con 27 llamadas cada uno (108 evaluaciones); un checkpoint anterior del 21/oct con lote mayor. Son datos de pruebas anteriores, no verdades de dictaminación.
- `reportes/`: resultados de las revisiones anteriores, discrepancias y auditorías. **No asumir que sus etiquetas son correctas**.
- Auditar ejemplos uno a uno, extraer evidencia textual, hablante y marcas temporales cuando estén disponibles; documentar falsos positivos y negativos.
- Crear pruebas unitarias y de integración para reglas; ejecutar regresión completa; reportar casos individuales, resultados y límites. Cuando falte audio original, indicarlo y no afirmar verificación acústica.

## Entregables
1. Código fuente completo corregido, instalable en Windows, sin perder funciones.
2. Suite de regresión reproducible con resultados por llamada y diferencias antes/después.
3. Registro conciso de errores solucionados y los que requieran audio/validación humana.
