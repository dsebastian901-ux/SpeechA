# Revisión independiente de r53 para Codex — 15/11/2026

## Control de versiones: NO alterar lo que la usuaria está probando

- **Base sin tocar:** `codex/entrega-r53`
- **Rama de propuesta:** `review/gpt6-r53-fixes-20261115`
- **No fusionar automáticamente.** Revisar el PR, ejecutar pruebas y cotejar los mismos audios en checkpoint antes de integración.
- **No reemplazar la rama `feature/r51-local-user-access`.** Esta rama tiene otras correcciones y control de usuarios/Whisper que siguen independientes. Una eventual integración requiere reconciliación de ambas historias, no sobreescritura.

## Errores detectados en el código r53

### 1. Excepciones de hostilidad/lascivia — incoherencia de clasificación

En `quality_decision.evaluate_quality`, `verified_exception` con `output_label['valid']` generaba `APROBADO_ETIQUETA_CORREGIDA` y, cuando la llamada era menor de 60 segundos, podía acabar en `APROBADO_DURACION_MENOR`.
Adicionalmente `APROBADO_CON_EXCEPCION` tenía `calidad_aprobada=True` pero `aprobado=False`.

**Corrección propuesta:** conservar `APROBADO_CON_EXCEPCION` como categoría exclusiva en todos los casos, incluso cuando hay etiqueta corregible o duración menor. Marcar `aprobado=True` únicamente si los cuatro criterios de excepción están confirmados (audio verificado, interlocutor hostil/lascivo, impide guion y gestor profesional), no hay bloqueos de seguridad y supera umbral. `output_label_correction` se conserva como información, pero no cambia la carpeta ni renombra el archivo. La categoría entra en `APPROVED_RESULTS`.

**Pruebas:** 4 combinaciones de duración/etiqueta y una alerta de privacidad independiente. Comprobar carpeta `APROBADO_CON_EXCEPCION` y consistencia de conteos con el lote.

### 2. Información de calidad inválida cuando falta la relación Excel

`batch_report_service._row_from_item` podía usar `analytics.compliance_status='cumple'` aunque la clase definitiva fuera `SIN_RELACION_EXCEL`.

**Corrección propuesta:** `Resultado Calidad = NO VALIDABLE - FALTA RELACION EXCEL` y `Validación Dictamen = SIN RELACION EXCEL`. Conserva score únicamente como cálculo provisional, no aprobación de cuenta/estatus.

**Prueba:** un item sintético con score 100, clase `SIN_RELACION_EXCEL` y `analytics.compliance_status='cumple'` debe figurar NO VALIDABLE en la fila del Excel.

## Fuera de alcance de este PR

- No se aprueba ninguna de las 106 llamadas en REVISAR solo para bajar cifras.
- No se reejecuta Whisper ni se alteran audios, checkpoints, transcripciones, referencias o datos de cuenta.
- No se cambian criterios operativos de recados, aviso genérico de atraso, ARCO, mora o protección de datos decididos por la usuaria.
- No se incorpora r51 o r53 entre sí automáticamente ni se modifica el instalador.

## Validación solicitada a Codex

1. Ejecutar las regresiones de `tests/test_review_r53_exceptions_and_excel.py` y toda la suite r53.
2. Verificar en la interfaz, carpeta física, Excel, tablero y resumen por gestor que **APROBADO_CON_EXCEPCION** sea exclusivo y figure correctamente en aprobados.
3. Revisar que un score alto sin Excel permanezca **SIN_RELACION_EXCEL / NO VALIDABLE**.
4. Reanalizar de forma comparativa el **mismo checkpoint de 207 transcripciones**, sin Whisper, manteniendo 6 fallas graves y documentando cada cambio de clasificación con evidencia.
5. Registrar conflictos potenciales con `feature/r51-local-user-access` antes de proponer una integración.

## Estado

Código y pruebas agregados en rama independiente para revisión. **Las pruebas completas no se han ejecutado desde este chat y no debe declararse r53 validada en Windows.** No se ha solicitado fusión.
