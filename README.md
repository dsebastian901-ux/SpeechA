# MRS Speech Analytics — programa r50

Programa completo para crear proyectos y procesar lotes. Extraiga todo el ZIP en una carpeta nueva, abra **INICIAR_PROGRAMA.bat** y compruebe **3.6.19-r50**. Use el Python, las dependencias y el modelo local de Whisper de su instalación existente. Los pesos del modelo no se incluyen.

Las correcciones se aplican desde el procesamiento inicial. Se revisan las causas de REVISAR: identificación contextual, familiar/intermediario, recepción del recado, referencias de tarjeta, importes, ARCO, seguimiento de pagos y comprobantes, quejas, lenguaje ofensivo y espera. Se conserva la revisión cuando la evidencia sigue siendo insuficiente.

Se separan **NO_APROBADO** ante un incumplimiento ordinario claro, **FALLA_GRAVE** ante una falta crítica confirmada y **REVISAR** ante dudas. Una queja declarada puede cerrar NO_APROBADO; una pregunta o expresión incierta conserva revisión. Las dudas de seguridad independientes mantienen su prioridad.

Se corrigen teléfonos/terminaciones interpretados como tarjetas completas o importes, falsas identificaciones de titular y omisiones de parentesco. En ARCO se consideran correcciones posteriores del correo sin completar un dominio dudoso. Se distinguen envío anterior de comprobante y petición de uno nuevo. Los seguimientos por fallecimiento conservan el estatus original, según la instrucción de la usuaria.

El reporte por gestor cuenta solo las llamadas cuya clasificación sea REVISAR y separa no aprobados, fallas graves y errores técnicos. La nueva hoja **REVISION_PENDIENTE** detalla la causa, acción concreta, campo de evidencia y fragmentos/tiempos disponibles; los motivos de estatus dependientes no se presentan como llamadas adicionales.

Al terminar se generan el reporte de calidad, las cuentas reetiquetadas y el reporte de motivos de no pago. Las copias con cambio de estatus siguen en **APROBADOS_ETIQUETA_CORREGIDA** y los NO_APROBADO en **NO_APROBADOS**. El Excel y los audios originales se conservan; numero_de_tarjeta del Excel sigue siendo la fuente del identificador.

Consulte REVISION_50_PROGRAMA.md y VALIDACION_R50.json. La validación distingue reglas sobre transcripciones recibidas, proyecto nuevo con ASR controlado y escucha humana. La atribución institucional nueva es textual y se limita a la misma cláusula; no se declara diarización o voz acústica identificada. No se garantiza eliminar toda revisión ni alcanzar una cuota de aprobaciones.

Esta entrega utiliza el entorno Python existente. El futuro instalador autónomo offline con usuarios y permisos se prepara por separado.
