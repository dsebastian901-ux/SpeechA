# Hallazgos del checkpoint parcial del 15/nov/2026 — para Codex

**Procedencia:** `batch_checkpoint(20261115-235657).json` aportado en chat privado. **No se almacena ni se adjunta al repositorio** porque contiene datos personales y transcripciones de cobranza.

**Atención:** el checkpoint fue generado por **`3.6.19-r51`**, no por la rama r53. No atribuir sus resultados a Codex r53 ni compararlos con r53 sin reanálisis controlado sobre el mismo checkpoint.

## Estado real del lote

- Total programado: **1,321**; completados: **727**; pendientes: **594**; `completed=false`.
- De los 727 completados: **394 REVISAR**, **230 SIN_RELACION_EXCEL**, **44 NO_APROBADO_MENOR_80**, **26 APROBADO**, **14 NO_APROBADO**, **14 FALLA_GRAVE**, **4 APROBADO_ETIQUETA_CORREGIDA**, **1 MAL_DICTAMINADO**.
- **492** completados sí tienen registro Excel; **394/492 = 80.1%** de los relacionados con Excel están en REVISAR.
- **235** completados carecen de relación; 230 están en SIN_RELACION_EXCEL y 5 conservan FALLA_GRAVE. No esconder faltas graves por falla de relación.
- De los 394 REVISAR: **353** tienen score >=80; **207** score 100; **41** score <80. Un score alto NO exime de seguridad o privacidad.
- REVISAR con bloqueo (superpuestos): **355 STATUS_INVALID**, **225 UNIDENTIFIED_CONTACT**, **159 UNCERTAIN_DISCLOSURE**, **71 NEGOTIATION_INVALID_OR_UNCERTAIN**, **24 CALLBACK_NOT_DELIVERED**, **16 NO_COLLECTION_ATTEMPT**, **12 CARD_REFERENCE**, **11 ARCO_INCOMPLETE**.
- **339/394** no cuentan con `detected_status` (cadena vacía). De los 394, **56** tienen **exclusivamente STATUS_INVALID** como bloqueo, **52** de esos 56 tienen score >=80 y **28** tienen score 100.
- Grupos frecuentes con varias causas, no multiplicar el número de llamadas: **84** tienen STATUS_INVALID+UNIDENTIFIED_CONTACT+UNCERTAIN_DISCLOSURE; **64** STATUS_INVALID+UNIDENTIFIED_CONTACT; **19** STATUS_INVALID+UNCERTAIN_DISCLOSURE; **16** solo UNCERTAIN_DISCLOSURE.
- Estatus Excel más frecuentes entre REVISAR: NO DEFINE FECHA DE PAGO **105**, RECADO REF1 **78**, CONVENIO **72**, MENSAJE CON FAMILIAR **35**, SE NIEGAN A TOMAR RECADO **26**, TITULAR CUELGA **24**, MENSAJE CON TERCERO **23**.

## Diagnóstico propuesto (sin resolver a ciegas)

1. **Prioridad 1, una sola causa:** auditar los 56 casos exclusivos STATUS_INVALID. Verificar evidencia de aceptación efectiva de recado, respuesta de titular sobre alternativas, negativa definitiva, pago ya realizado y decisión pendiente. No inferir `NO DEFINE` por ausencia de aceptación ni `CONVENIO` por oferta del gestor.
2. **Prioridad 2:** revisar atribución de identidad de las 225 llamadas con contacto no determinado. No tomar «sí/dígame» aislado ni otro nombre como prueba de titularidad. Mantener revisión de privacidad cuando se desconoce a quién se divulgó.
3. **Prioridad 3:** examinar los 41 REVISAR con score inferior a 80, distinguendo incumplimiento ordinario comprobado de advertencias de seguridad. Las alertas pendientes no se borran al clasificar un rechazo.
4. **Prioridad 4:** revisar la separación de 235 audios sin relación. Corregir **Excel de origen**, no pedir retranscribir; preservar 5 fallas graves.
5. **Seguridad:** no rebajar ni eliminar UNCERTAIN_DISCLOSURE, ARCO, insultos, referencias bancarias o fallas graves solo para reducir REVISAR.

## Protocolo de validación para Codex

- **Pausar la transcripción del lote** y conservar intacto este checkpoint y los audios ya transcritos; no se requiere completar 1,321 para iniciar diagnóstico.
- Hacer los cambios **solo** en la rama aislada de propuesta, nunca sobre la r51/r53 que se está probando.
- Crear regresiones a partir de **escenarios sintéticos**, no subir nombres, tarjetas, teléfonos ni textos reales de llamadas a GitHub.
- Reanalizar **únicamente 727 transcripciones existentes** con la misma fuente y registrar diferencial `clasificación anterior → clasificación nueva`, causas y referencias internas de evidencia; **594 pendientes siguen pendientes**.
- Diferenciar cambios reales de calidad frente a reclasificación de registros sin Excel.
- Afirmar que bajaron los REVISAR solo cuando la misma muestra haya sido ejecutada y contrastada, con todas las faltas graves y alertas conservadas.

**Estado de este documento:** diagnóstico de datos, no cambio de motor ni ejecución de pruebas en Windows. Las cifras corresponden al checkpoint parcial r51 aportado por la usuaria.
