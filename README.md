# MRS Speech Analytics — programa r49

Programa completo para crear proyectos y procesar lotes desde la interfaz. Las correcciones se aplican desde el procesamiento inicial de todos los audios.

Extraiga todo el ZIP en una carpeta nueva y abra **INICIAR_PROGRAMA.bat**. Compruebe **Versión 3.6.19-r49**. En **Procesamiento por lotes**, cargue audios y Excel. Utilice el Python, las dependencias y el modelo local de Whisper de su instalación existente. Los pesos del modelo no están incluidos.

Esta revisión distingue **NO_APROBADO** ante incumplimientos ordinarios comprobables y **REVISAR** ante incertidumbre. Las fallas graves conservan prioridad; una duda de seguridad no se cierra como incumplimiento ordinario. La duración mínima de 60 segundos ya existente se cierra como NO_APROBADO cuando está comprobada y no hay dudas de seguridad independientes. La regla de espera de 65 segundos se conserva.

Se amplía el reconocimiento de aceptación de recados, parentesco y contactos de trabajo, dictado interrumpido y teléfono previamente anotado. Se corrigen falsas aceptaciones por frases del gestor y falsas identificaciones del titular. Los ecos de un fragmento de teléfono no acreditan un contacto completo. Se mejora la lectura del diálogo ARCO sin completar dominios dudosos ni omitir requisitos.

El contador final separa aprobados, NO_APROBADO, REVISAR, fallas graves y errores. Las copias NO_APROBADO van a **NO_APROBADOS**. Este es un resultado de evaluación, no un nuevo estatus de grabación. Se mantienen los nueve estatus operativos autorizados.

Al terminar se generan el reporte de calidad, las cuentas con estatus corregido y el reporte de motivos de no pago. Las copias con estatus corregido van a **APROBADOS_ETIQUETA_CORREGIDA**. Se conserva numero_de_tarjeta del Excel como fuente del identificador. El Excel y los audios originales se mantienen intactos.

Consulte [REVISION_49_PROGRAMA.md](proyecto/MRS_Speech_Analytics_v3.6.19_Revision/REVISION_49_PROGRAMA.md) y VALIDACION_R49.json para comprobaciones, cifras y límites. La comparación mantiene el mismo conjunto de llamadas y los textos recibidos; no se declara escucha humana ni nueva transcripción acústica de todo el lote. La revisión manual sigue siendo alta y no se garantiza una tasa de aprobación.

Esta entrega usa el entorno Python ya instalado. El futuro instalador autónomo offline con usuarios y permisos se desarrolla por separado.
