# MRS Speech Analytics — piloto r42

Resultado del lote de 100 después del reanálisis y la corrección autorizada de nombres desde tarjeta Excel: **74 REVISAR, 12 APROBADO, 11 NO_APROBADO_MENOR_80, 3 FALLA_GRAVE**. El archivo recibido tenía una aprobada. La mejora es parcial y las pendientes siguen siendo muchas.

Se aplica el criterio de identificación contextual confirmado por el usuario y se corrigen la interpretación de compromisos, pagos anteriores, comprobantes, miles y saldos. La falta de dos lugares de pago conserva la penalización de 20 puntos, sin bloquear por sí sola una aprobación con 80. Se conservan los bloqueos de seguridad, quejas, ARCO, groserías y espera de 65 segundos.

Para aplicar las reglas a las llamadas YA procesadas: extraiga todo en una carpeta nueva, abra REANALIZAR_CON_TARJETA_EXCEL.bat y seleccione el batch_checkpoint.json actual de 100 llamadas. Se generan una copia, el checkpoint y ambos Excel. No ejecuta Whisper ni requiere cambiar el modelo. Espere el mensaje final; un lote grande puede tardar varios minutos.

Consulte proyecto/MRS_Speech_Analytics_v3.6.19_Revision/REVISION_42_DIAGNOSTICO.md y VALIDACION_R42.json. Incluyen resultados, alcance de la muestra ASR y pendientes. Esta versión no incluye el futuro instalador ni el acceso de usuarios de noviembre.

