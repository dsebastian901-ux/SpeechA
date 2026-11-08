# MRS Speech Analytics — programa r51

Extraiga todo el ZIP en una carpeta nueva y abra INICIAR_PROGRAMA.bat. Debe mostrar 3.6.19-r51. Se usa el Python y modelo local de Whisper existentes; no es el instalador autónomo futuro.

El estatus de gestión del Excel (CONVENIO, NEGATIVA DE PAGO, MENSAJE, ACLARACION, etc.) es distinto del resultado de calidad. Si la llamada cumple 80 puntos y seguridad y se confirma un estatus diferente con evidencia suficiente, se guarda en APROBADOS_ETIQUETA_CORREGIDA. Solo cambia ese bloque del nombre; los originales se conservan. La tabla de cuentas reetiquetadas explica el cambio.

Se corrige la pérdida del fragmento probatorio en seguimientos de pago detectados como ACLARACION. Se incorporan respuestas locales de aceptación de dictado y retorno con teléfono disponible, distinguiéndolas de una instrucción del gestor. Una afirmación «claro, sí, pero no lo voy a pagar» no se interpreta como hipótesis solo por contener sí. No hay excepciones por llamada.

La etiqueta corregible resuelve exclusivamente el bloqueo de estatus. No exime privacidad, quejas, groserías, referencia, negociación, espera ni puntaje. Cuando falta evidencia del nuevo estatus o hay otra alerta, sigue pendiente con su motivo; no se declara una falta del gestor solo porque el detector no la entienda.

Los reportes de calidad, motivos de no pago y reetiquetado siguen generándose al finalizar. REVISION_PENDIENTE muestra causas y evidencia disponible. No sumar códigos de estatus dependientes como llamadas adicionales ni contar carpetas vacías como resultados.

Consulte REVISION_51_PROGRAMA.md y VALIDACION_R51.json. Las validaciones distinguen reglas sobre ASR recibido, proyecto nuevo con ASR controlado, y escucha humana. No se declara nueva escucha humana, retranscripción completa ni prueba nativa Windows.

SHA-256: 006452caf25e29ee98f37b0f273c16853d388a2b537da3e0ba2024c8dac9ca36
