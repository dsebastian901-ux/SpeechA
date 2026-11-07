# r43 — revisión de las 46 llamadas con 80 puntos o más

## Alcance y resultado

Se revisaron individualmente el texto y las reglas de las 46 llamadas pendientes de r42 con puntaje mínimo de 80. Se contrastaron cuatro ventanas iniciales de 25 segundos con modelo medium local; una lectura repetitiva fue descartada. No fue escucha humana de 46 audios y la lectura alternativa no alimentó las aprobaciones ni sustituyó el ASR original.

Entrada r42: 12 aprobadas, 74 por revisar, 11 rechazadas por puntaje y 3 marcadas graves. Salida r43: 71 REVISAR, 15 APROBADO, 11 NO_APROBADO_MENOR_80, 3 FALLA_GRAVE. Se liberaron 3 de las 46, conservando sus puntajes. Las otras 43 mantienen una alerta o duda; no se declaran 43 faltas demostradas.

La revisión individual privada agrupa sin duplicar: 12 quejas de atención previa, 4 posibles expresiones confrontativas, 2 advertencias de recuperación/visita en 1–2 PV, 4 con lenguaje ofensivo, 1 con espera sin retoma, 3 falsos bloqueos corregidos y 20 pendientes de identidad, finanzas, estatus o calidad ASR. El detalle privado no se publica en el repositorio.

## Cambios

- Reconoce autorreferencias a pago mínimo propio, intención de pagar la propia deuda y falta de fondos tras pregunta nominal. Conserva exclusiones de familiar, pago por otra persona, hipótesis, gestor conocido y respuestas aisladas.
- No interpreta una pregunta intermedia sobre qué pago se reclama como un sí de compromiso. Distingue aceptación final de una propuesta anterior incierta.
- Reconoce importes hablados de planes posteriores de dos/tres pagos aunque no repitan pesos. No completa cantidades con el Excel.
- Distingue el día 15 de un pago de 15 pesos en la expresión temporal «lo voy a estar realizando en 15».
- «Hoy me confirmaron la falta de movimiento» no es una promesa de hoy; conserva fechas explícitas como «antes del 6».
- Registra quejas antes omitidas sobre soporte sin respuesta, llamadas cortadas, trato grosero y falta de solución. Bloquea aprobación sin atribuir automáticamente culpa al gestor actual.
- Mantiene revisión de posibles expresiones confrontativas y advertencias de visita/recuperación en 1–2 PV cuando la voz no está confirmada. No fabrica falta grave ni escucha humana.
- Detecta la exclamación «ah, chingas» con contexto, sin convertir un apellido aislado en grosería.
- Se conserva el descuento de 20 por omitir dos lugares autorizados, con posibilidad de aprobar a 80 si pasa todos los demás filtros. Se conservan privacidad, ARCO, referencias, quejas, espera de 65 segundos y confirmaciones anteriores.

## Cómo aplicar a este lote

1. Extraiga el ZIP completo en una carpeta nueva.
2. Ejecute REANALIZAR_CHECKPOINT.bat.
3. Seleccione Checkpoint_r42_Recuperado.json, el último archivo recibido. Ya contiene la corrección autorizada de nombres desde tarjeta Excel.
4. Espere el mensaje final. Se genera checkpoint_reanalizado.json y ambos Excel de calidad y motivos de no pago en una carpeta nueva.

No requiere procesar otra vez los audios ni cambiar Whisper. Para otro lote que necesite la corrección autorizada de nombres desde numero_de_tarjeta, use REANALIZAR_CON_TARJETA_EXCEL.bat.

## Validación y pendientes

1,856 pruebas correctas, 7 de interfaz omitidas y cero fallos en Linux/Python 3.10. No se certifica Windows nativo. Se compararon 2,217 filas en cuatro salidas de 1,210 llamadas únicas, verificando integridad de cuentas, ASR, confirmaciones, celdas de calidad y totales de motivos de no pago.

La revisión excesiva sigue abierta. La cancelación por saldo total sin descuento en 1–3 PV permanece pendiente de criterio; se conserva la regla anterior. Este piloto no incluye el futuro instalador ni acceso de usuarios.
