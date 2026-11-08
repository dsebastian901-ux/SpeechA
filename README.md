# MRS Speech Analytics — programa r48

Programa completo para crear proyectos y procesar lotes desde la interfaz. Las correcciones se aplican en el procesamiento inicial y usan las mismas reglas para todas las llamadas.

Extraiga el ZIP completo en una carpeta nueva y abra **INICIAR_PROGRAMA.bat**. Compruebe **Versión 3.6.19-r48**. En **Procesamiento por lotes**, cargue los audios y el Excel. Use el Python, las dependencias y el modelo local de Whisper de su instalación existente. Los pesos del modelo no están incluidos en este ZIP.

Se amplía el reconocimiento de parentesco, aceptación y dictado de recados; se corrigen falsas identificaciones del titular y contradicciones que activaban ARCO; se reconoce el procedimiento ARCO explicado con pausas; se aplica la autorización de decir «saldo pendiente» o «saldo vencido» sin importe; se refuerzan importes, mora y estado de cobranza protegidos. Consulte [REVISION_48_PROGRAMA.md](proyecto/MRS_Speech_Analytics_v3.6.19_Revision/REVISION_48_PROGRAMA.md).

Al terminar se generan el reporte de calidad, las cuentas con estatus corregido y el reporte de motivos de no pago. Las copias con estatus corregido van a APROBADOS_ETIQUETA_CORREGIDA, incluido un cambio entre subtipos que comparten 3EROS. El Excel y los audios originales se conservan.

La validación distingue reglas con ASR controlado, contraste acústico adicional y escucha humana. Una nueva transcripción de Whisper puede producir resultados diferentes. Los pendientes que conserven evidencia insuficiente siguen en REVISAR; esta versión no garantiza aprobar un porcentaje de llamadas. VALIDACION_R48.json detalla comprobaciones y límites.

Esta entrega usa el entorno Python ya instalado. El futuro instalador autónomo offline con usuarios y permisos se desarrolla por separado.
