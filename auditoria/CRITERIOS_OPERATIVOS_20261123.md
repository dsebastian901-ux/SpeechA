# Aclaraciones operativas de la usuaria — 23/11/2026

Fuente: respuesta de la usuaria a los escenarios de los 14 fallos. Estas
aclaraciones prevalecen sobre los criterios anteriores cuando hay conflicto.
No acreditan escucha humana ni autorizan una cuota de aprobaciones.

| Escenario | Criterio |
|---|---|
| Tercero rechaza el recado | Estatus SE NIEGAN A TOMAR RECADO. No acreditar recepción ni inventar código de salida. La usuaria confirmó el estatus; la calidad y seguridad se evalúan separadamente. |
| Pago reportado | Es importante confirmar cuánto pagó el titular y solicitar comprobante. No hace falta inventar una promesa futura ni acreditar pago bancario. Un importe reportado suficiente y solicitud válida permiten el seguimiento CONVENIO según el criterio 72. |
| Pago menor al mínimo, sin compromiso por la diferencia, con acción del gestor | NO DEFINE FECHA DE PAGO. Conservar el importe, la diferencia y evidencia de gestión. No convertir la falta de aceptación en negativa. |
| Solo solicita comprobante sin gestionar un pago insuficiente | FALLA_MINIMA, en carpeta nueva. Mantener puntaje y penalizaciones existentes. |
| Solo solicita comprobante sin confirmar cuánto pagó | FALLA_MINIMA si esa omisión está acreditada en el flujo; una pregunta por importe sin respuesta inteligible conserva incertidumbre. No completar desde Excel. |
| Pago confirmado en importe sin solicitud de comprobante | Falta mínima por omitir el requisito indicado; no inventar ACLARACIÓN. Conservar controles de incertidumbre de ASR y evidencia de solicitud/envío equivalentes. |
| Fecha aceptada fuera del plazo operativo de promesa | No clasificar como NEGATIVA por ese motivo. Conservar acuerdo real y clasificar FALLA_MINIMA. No ampliar el plazo permitido. |
| Dice mañana sin confirmar importe | NO DEFINE FECHA DE PAGO; no inferir aceptación de la cifra que el gestor dice después. |

FALLA_MINIMA es resultado de calidad **no aprobado**, independiente del estatus
de gestión; no es un código para renombrar el audio. Los puntos no cambian por
esta categoría y las alertas independientes permanecen visibles. Una falta
grave confirmada conserva prioridad. PEN005 (fecha posterior al vencimiento)
y las restricciones de liquidación no se desactivan al corregir los dos casos
del plazo operativo de tres días. La aclaración se limita al escenario
consultado; no se sustituye una falta grave por una mínima sin instrucción.

Confirmaciones adicionales de la usuaria en esta misma sesión:

- Ante rechazo del recado, evaluar los pasos que el gestor pudo realizar;
  puede aprobar por calidad si cumple mínimo y seguridad. No otorgar 100
  automáticamente ni aprobar un recado como si hubiera sido recibido.
- Calidad y seguridad cumplidas, estatus correcto probado y nombre que no
  permite reetiquetar con seguridad: APROBADO_SIN_ETIQUETAR. Conservar
  original y registrar corrección pendiente en el reporte. Esta salida no
  elimina dudas independientes ni inventa nombre, código o confirmación.

Las expectativas históricas solo se ajustan con relación explícita a este
documento y al escenario probado. Se conserva el código/test original en Git;
un ajuste de expectativa no se cuenta como corrección del motor.
