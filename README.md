# MRS Speech Analytics — r55

Extraiga todo el ZIP en una carpeta nueva y abra INICIAR_PROGRAMA.bat.
La barra debe mostrar **3.6.19-r55**. Utiliza el Python y el modelo local
ya instalados; la relectura no necesita descargar otro modelo.

Los cambios se aplican al Procesamiento por lotes de proyectos nuevos.
También se corrige la recuperación de lotes anteriores: actualiza los
resultados desactualizados reutilizando la transcripción compatible y
conserva un historial del checkpoint anterior.

Con ASR nuevo o guardado, si queda REVISAR por identidad del interlocutor o contacto
incompleto del recado, intenta dos relecturas locales acotadas con el modelo
local instalado. No retranscribe toda la llamada. Solo incorpora esos hechos con evidencia compatible en ambas.
Conserva el ASR original, no completa datos desde Excel ni certifica voces.
El Excel final muestra la relectura y sus alertas.

Se corrige confundir teléfonos con dinero, atribuir un saldo referido de
una llamada anterior al gestor actual e identificar al receptor del recado
como titular. Reconoce más respuestas familiares y nominales sin omitir
los filtros de privacidad, trato, negociación y seguridad acordados.

Continúan los reportes de motivos de no pago y cuentas reetiquetadas.
Reportes incorpora consolidación local de varios lotes, contados por
separado, con exportación Excel y Word.

Consulte REVISION_55_PROGRAMA.md en la carpeta del programa y VALIDACION_R55.json
para el alcance comprobado. Las pruebas con ASR guardado o salida controlada
del modelo no equivalen a retranscribir el lote real con Faster-Whisper.
No se acredita aquí una reducción de REVISAR mediante transcripción nueva.

Este paquete usa la instalación existente. El inicio de sesión y el
instalador autónomo permanecen pendientes de integración.

También se corrige el orden temporal de las respuestas de pago, el cambio
del sujeto de la gestión al buscar a otra persona, solicitudes de comprobante
y foto de pago, seguimiento de aclaraciones y quejas concretas de atención.
Un incumplimiento de fecha comprobado se cierra como NO_APROBADO; sus alertas
independientes permanecen visibles. Las dudas de un recado se explican por
recepción, cuerpo o contacto, sin presentarlas como una sola duda de estatus.

El programa no agrega APIs ni servicios de pago. La relectura usa únicamente
Faster-Whisper local. Si el modelo completo no está disponible en el equipo,
conserva la transcripción y el resultado sustentado, sin descargar modelos.
