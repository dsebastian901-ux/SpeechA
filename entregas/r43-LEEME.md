# Piloto r43 — revisión de las 46 pendientes con 80 puntos o más

Descargue r43.zip y extraiga TODO en una carpeta nueva. Ejecute REANALIZAR_CHECKPOINT.bat y seleccione el último Checkpoint_r42_Recuperado.json. Se conserva el original y se generan checkpoint_reanalizado.json y ambos Excel de calidad y motivos de no pago. No necesita volver a procesar los audios ni cambiar Whisper.

Se revisaron individualmente texto y reglas de 46 llamadas. Se corrigieron tres falsos bloqueos, conservando puntajes. Quedan 43 con alerta o duda: no se declaran 43 faltas demostradas. Hubo un contraste ASR adicional de cuatro ventanas iniciales de 25 segundos; una repetitiva se descartó. No fue escucha humana de los 46 audios y el ASR alternativo no alimentó las aprobaciones.

Resultado del lote: {'REVISAR': 71, 'APROBADO': 15, 'NO_APROBADO_MENOR_80': 11, 'FALLA_GRAVE': 3}. Corrección parcial; persiste la revisión excesiva. Se conservan filtros de seguridad y penalización de 20 por lugares de pago, sin bloqueo extra si alcanza 80 y pasa los demás filtros.

1,856 pruebas correctas, 7 gráficas omitidas, cero fallos. Sin certificación Windows nativa. No incluye instalador final ni login. La política de cancelación por saldo total sin descuento en 1–3 PV sigue pendiente.

SHA-256: b3db375388e593eb9aa2c230004040759f25fcec9b523db89e50edc9c5e7d5d6

El ZIP contiene solo código y documentación. No incluye audios, checkpoints, reportes reales ni pesos del modelo.
