# Cierre de los criterios del 23/11/2026

**Los 34 casos pasan individualmente. La suite completa queda con 3248 pruebas que pasan, cero fallos y dos omisiones de entorno.**

Rama `codex/integracion-medium-dictaminacion-20261123`, basada en `3f7011b`. Versión trazable del motor: `3.6.19-r58-criterios-20261123`. Las decisiones están en [CRITERIOS_OPERATIVOS_20261123.md](../../CRITERIOS_OPERATIVOS_20261123.md), incluidas las dos confirmaciones adicionales de calidad ante rechazo y carpeta sin etiqueta.

## Qué cambia en el programa

1. **Rechazo del tercero:** mantiene SE NIEGAN A TOMAR RECADO. Se trasladan la evidencia y confianza del rechazo al estatus; antes el motor reconocía la negativa, pero seguía considerando dudoso el estatus. La calidad evalúa los pasos que pudo ejecutar el gestor, sin inventar recepción ni conceder 100 puntos automáticamente.
2. **Etiqueta pendiente:** con estatus probado, calidad suficiente y seguridad cumplida, un nombre que no puede corregirse de forma segura conduce a APROBADO_SIN_ETIQUETAR. El reporte añade estatus correcto y motivo pendiente. No se inventan nombres ni códigos, ni se modifica el original. La calidad aprobada sin etiqueta se mantiene separada de la aprobación para reetiquetar en los contadores existentes.
3. **Pago reportado:** exige confirmar importe y solicitar comprobante. Importe suficiente y solicitud válida siguen como CONVENIO, sin acreditar pago bancario ni exigir una promesa futura inventada.
4. **Diferencia sin aceptación:** si el gestor la gestiona, el estatus es NO DEFINE. Se corrige además la atribución financiera por posiciones: el importe ya pagado no se compara como si fuera una nueva oferta aceptada. Una propuesta posterior de igual importe conserva su validación independiente. Los antecedentes de otro periodo no generan una omisión de comprobante de la gestión actual.
5. **FALLA_MINIMA:** categoría no aprobada con carpeta, contador y hoja Excel propios. Aplica al flujo confirmado de solo comprobante sin confirmar importe o sin gestionar diferencia insuficiente, y a la omisión de comprobante de un pago vigente cuyo importe sí se confirmó. Una pregunta por importe sin respuesta inteligible conserva revisión; no se completa desde Excel.
6. **Fecha fuera del plazo operativo:** conserva el acuerdo real como CONVENIO y se registra FALLA_MINIMA; no se atribuye negativa al titular ni se amplía el plazo. PEN005 por vencimiento y las otras faltas graves conservan prioridad. El rechazo real del cliente continúa siendo NEGATIVA.

FALLA_MINIMA se integra en lotes nuevos, copias, resumen del lote, dashboard, reporte de calidad y consolidación por gestor/supervisor. Las alertas independientes permanecen visibles y prioritarias; una falla mínima con privacidad pendiente no aprueba. En la consolidación se registra como incumplimiento no grave, con causa y evidencia.

## Pruebas y diferencia antes/después

| Ejecución | Casos | Pasan | Fallan | Omitidos |
|---|---:|---:|---:|---:|
| Suite de `3f7011b` | 3224 | 3208 | 14 | 2 |
| 34 individuales antes | 34 | 20 | 14 | 0 |
| 34 individuales después | 34 | 34 | 0 | 0 |
| Focal final de pagos y criterios | 214 | 214 | 0 | 0 |
| Suite completa final | 3250 | 3248 | 0 | 2 |

Se agregaron **26 casos nuevos** con contrastes negativos, prioridades, origen de importes, periodos históricos, etiqueta pendiente e integración de lote/copia/Excel/consolidación. Otras 285 pruebas focalizadas pasaron durante la integración. La suite final y los 34 procesos individuales verificaron fuentes inmutables y coincidentes. No se quitaron pruebas ni parámetros originales.

Las expectativas de **17 archivos de pruebas anteriores** se ajustaron con fundamento en las respuestas de esta sesión. [AJUSTES_PRUEBAS.json](AJUSTES_PRUEBAS.json) registra cada función/fixture, razón, hashes antes/después y el commit original recuperable. Los nombres históricos de algunos tests se conservaron para mantener los identificadores. **Cambiar una expectativa no se presenta por sí solo como reparar el motor**: los casos que ya aprobaban correctamente, como el seguimiento suficiente y su copia PP, están identificados de esa manera.

La comparación ejecutada con el mismo texto y contexto en ambos motores arroja, entre otros:

| Escenario sintético | Antes | Después | Puntos antes/después |
|---|---|---|---:|
| Tercero rechaza, gestor correcto | REVISAR | APROBADO_SIN_ETIQUETAR | 100 / 100 |
| Pago suficiente y comprobante | APROBADO | APROBADO | 100 / 100 |
| Insuficiente, solo comprobante | NO_APROBADO | FALLA_MINIMA | 85 / 85 |
| Gestiona diferencia sin aceptación ni nueva cifra negociada | REVISAR | APROBADO_ETIQUETA_CORREGIDA como NO DEFINE | 100 / 100 |
| Solo comprobante, sin confirmar importe | REVISAR | FALLA_MINIMA | 100 / 100 |
| Fecha fuera del plazo operativo | NO_APROBADO, estatus NEGATIVA | FALLA_MINIMA, estatus CONVENIO | 100 / 100 |
| Privacidad incierta | REVISAR | REVISAR | 100 / 100 |
| Divulgación confirmada | FALLA_GRAVE | FALLA_GRAVE | 0 / 0 |

Los **11 escenarios comparados** conservaron puntos y descuentos. Se verificó también que todas las llamadas de código a `add_penalty` permanecen iguales mediante comparación AST; no se alteraron sus valores para obtener resultados. Cambió la atribución de hechos y su resolución operativa, no el umbral de 80 ni las cantidades de las penalizaciones.

## Evidencia por caso

- [RESULTADOS_34.csv](RESULTADOS_34.csv): identificador, causa/criterio, antes/después, cambio y ajuste de expectativa.
- [RESULTADOS_34.json](RESULTADOS_34.json): funciones/líneas y hashes de los registros individuales, además del detalle anterior.
- [SUITE_ANTES_DESPUES.csv](SUITE_ANTES_DESPUES.csv): los 3250 resultados, incluidos los 26 nuevos y las dos omisiones.
- [COMPORTAMIENTO_ANTES_DESPUES.json](COMPORTAMIENTO_ANTES_DESPUES.json): resultados de los 11 escenarios ejecutados contra ambos motores, con puntos, descuentos y fuentes intactas.
- [PRUEBAS.json](PRUEBAS.json): conteos, controles, módulos conservados y límites.
- [FUENTES_PROBADAS_SHA256.json](FUENTES_PROBADAS_SHA256.json): fuentes exactas verificadas de aplicación, herramientas y pruebas.

Los informes anteriores permanecen como evidencia histórica; no se sobrescribieron los checkpoints de clientes para producir este cierre. Los datos de esta comparación son sintéticos. Los registros detallados y los datos privados no se publicaron.

## Reproducción y límites

Desde la raíz, con dependencias de desarrollo instaladas y directorios de salida nuevos y privados:

```text
python auditoria/integracion-medium-20261123/cierre-34/reproducir_34.py --output <directorio-privado-fuera-del-repositorio>
python auditoria/ejecutar_pruebas.py --output <otro-directorio-privado-nuevo>
```

Para la suite en Linux sin pantalla, añadir `--xvfb <ruta-a-Xvfb>`. Los dos tests omitidos corresponden a diálogos de importación Medium por incompatibilidad Python 3.10/Menu con Tcl/Tk 9 en este entorno. Las otras pruebas de GUI disponibles corrieron con Xvfb.

Se verificaron **780 hashes de las referencias R57, sin cambios**. Autenticación y cuentas locales, permisos, Whisper, importación offline y reanálisis conservan sus módulos y controles; la suite incluye sus regresiones. El procesamiento normal por lotes prueba el motor, las copias y los reportes con ASR controlado.

**No se compilaron EXE ni instalador, no se activó Medium experimental, no se ejecutó ASR real nuevo y no hubo escucha humana ni prueba en Windows físico en este cierre.** La precisión acústica y el funcionamiento en Windows físico siguen pendientes; una suite verde no los certifica ni estima la tasa de aprobación de un lote real.
