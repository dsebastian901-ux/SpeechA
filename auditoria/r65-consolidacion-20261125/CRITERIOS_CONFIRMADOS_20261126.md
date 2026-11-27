# Decisiones confirmadas por operación — 26/11/2026

Estos criterios prevalecen sobre propuestas anteriores no aprobadas. Mantenerlos separados de la evidencia acústica todavía pendiente.

## 1. Calidad independiente del éxito de cobranza
Una llamada con NO DEFINE puede alcanzar 100 puntos si el gestor cumple todas las acciones aplicables. No descontar por ausencia de compromiso del titular. Los errores reales de procedimiento sí se descuentan conforme a la matriz vigente.

## 2. CONVENIO y aceptación ambigua
Si hay monto y fecha, pero no aceptación concluyente, activar segunda escucha focalizada. Si la aceptación se confirma, dictaminar CONVENIO. Si no, determinar NO DEFINE o REVISAR según evidencia. Nunca aprobar/reetiquetar por monto y fecha únicamente.

## 3. Lugares de pago en CONVENIO
La omisión de uno o ambos lugares requiere la penalización correspondiente; el convenio puede aprobar con 80 puntos o más **solo si no existen bloqueos independientes**. No convertir la omisión por sí sola en rechazo absoluto. No inventar importes de descuento; usar matriz autorizada.

## 4. Presión para vender/empeñar bienes
La indicación de vender o empeñar bienes dispara REVISAR para verificar contexto, hablante y tono. Si se comprueba presión indebida, aplicar bloqueo; no declarar automáticamente maltrato sin escuchar.

## 5. Compromiso fuera del plazo autorizado — CORRECCIÓN EXPRESA DE LA USUARIA
Si el titular aceptó monto y fecha fuera del plazo permitido, conservar **CONVENIO** como estatus real de gestión, pero registrar **ERROR OPERATIVO DE PLAZO** en calidad, no mera observación informativa. El motor ya contempla `CONFIRMED_PAYMENT_DATE_OUTSIDE_POLICY` en `minor_failure_policy.py` y `FALLA_MINIMA`; conservar la no aprobación hasta validar su tratamiento con otras alertas. La categoría exacta de gravedad y el descuento numérico no fueron confirmados: **no asignar puntos ni gravedad nuevos sin autorización**. Si la evidencia de la fecha es ambigua, segunda escucha/revisión; no afirmar error confirmado.

## 6. Segunda y tercera escucha
Si la segunda escucha discrepa de la primera, tercera focalizada; cerrar automáticamente solo con evidencia final consistente y sin otros bloqueos. Si persiste discrepancia, REVISAR. El checkpoint no prueba por sí solo que medium se ejecutó: exigir registro de cada intento, modelo, fragmento, comparación y resultado.

## Validación obligatoria
Demostrar resultados con los 39 audios r65, no solo con pruebas unitarias. Verificar no regresión de aprobaciones correctas; no forzar aprobaciones para reducir REVISAR.
