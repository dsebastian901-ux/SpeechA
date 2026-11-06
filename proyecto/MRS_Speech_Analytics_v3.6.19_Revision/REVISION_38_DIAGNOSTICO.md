# Revisión 38 — reglas contextuales y motivos de no pago

Base: ZIP r37 recibido del usuario. No cambia requisitos ni el modelo de Whisper.

## Uso en Windows

1. Extraiga el paquete completo en una carpeta nueva.
2. Para llamadas ya transcritas, ejecute REANALIZAR_CHECKPOINT.bat de la raíz y seleccione su último checkpoint completo, preferentemente el recuperado con r37. Conserve disponible la carpeta de transcripciones para recuperar los JSON de fallos antiguos. No reinstale Whisper ni vuelva a procesar los audios para aplicar estas reglas.
3. Abra el nuevo reporte de calidad y Reporte_Motivos_No_Pago.xlsx en la misma carpeta 04_Reportes. El reanálisis muestra ambas rutas. En lotes nuevos, la aplicación incluye el botón «Motivos de no pago» y el reporte de calidad contiene un enlace al adicional.
4. Para audios nuevos, use el programa habitual en proyecto/MRS_Speech_Analytics_v3.6.19_Revision/INICIAR_MRS.bat con el mismo Excel y modelo que venía usando.

Las herramientas generan copias; no sustituyen transcripciones, checkpoints ni audios de entrada. El reporte de motivos se genera al final, también en reanálisis, y no se regenera en cada reporte parcial.

## Correcciones comprobadas por caso

- 577: reconoce «me contestaron muy mal» y «una me amenazó». La denuncia bloquea aprobación y se registra con evidencia, sin atribuir automáticamente maltrato al gestor actual.
- 44: señala «nada más sería como chisme» como trato despectivo. Conserva REVISAR con causa explícita; no inventa tono acústico.
- 939: detecta la variante ASR «chinguy chinguy» al final. La atribución incierta bloquea aprobación; la hostilidad del cliente requiere la validación de excepción ya existente. No confunde un fragmento de tarjeta como «tarjetaunching» con insulto confirmado.
- 995: «retirado de mi casa» expresa distancia y ya no produce amenaza de retiro de bienes. Se conservan las amenazas operativas explícitas y visitas prohibidas en 1–2 PV.
- 328, 331, 109 y 909: desconocer al gestor, su nombre o su propósito no significa desconocer al deudor. Las demás faltas o incertidumbres permanecen; no se aprueban automáticamente.
- 161 y 175: una negativa a liquidar o una pregunta sin puntuación no se confirma como oferta de liquidación. Las ofertas directas posteriores conservan su penalización.
- 648: propuesta de colgar y devolver la llamada requiere confirmar acuerdo/continuación; no se trata automáticamente como abandono grave. Un anuncio unilateral separado sigue bloqueado.
- 820: un mes sin año que se lleva automáticamente al año siguiente con un salto mayor de 90 días queda pendiente de confirmar. No se toma ese año calculado como evidencia acústica ni se aprueba el convenio; fechas con año explícito y cruces próximos diciembre/enero conservan validación de vencimiento. Una promesa posterior al vencimiento tampoco se aprueba por faltar etiqueta CONVENIO.
- 236: una terminación de teléfono con contexto posterior de número personal no se compara como tarjeta.
- 140: una posible corrección fragmentada de terminación pasa a revisión; no se reconstruye el número desde el Excel.
- 128: reconoce Del Sol y Kiosco dentro de «el pago lo estaría aplicando…»; mantiene los demás incumplimientos. Reconoce también la instrucción plural «pueden aplicar».
- Identidad/recados: reconoce «Servidor» como respuesta a una pregunta nominal y «le paso su recado» como aceptación contextual. No infiere parentesco ni entrega del mensaje por esas frases solas.
- ARCO: reconoce «derecho que se llama ARCO» como mención. No sustituye la explicación del procedimiento, correo oficial, INE y comprobante de línea requeridos.

## Reporte adicional de motivos de no pago

Hojas: RESUMEN_MOTIVOS, POR_GESTOR (incluye supervisor), POR_MORA, DETALLE_LLAMADAS, DATOS_EXCEL y NOTAS.

Agrupa desempleo, salud/accidente, fallecimiento referido, desconocimiento o disputa del adeudo, impedimento para pagar, espera de ingreso/quincena, ingresos insuficientes, falta de liquidez, olvido y negativa expresa cuando existe evidencia textual. Separa pago ya reportado, tercero sin motivo del titular, no conoce al deudor, motivo no identificado y transcripción ausente.

Cuenta una sola causa principal por llamada y muestra secundarias y ventanas ASR aparte. No toma las preguntas o palabras identificadas del gestor como motivos del cliente ni atribuye la falta de dinero del familiar al titular ausente. El motivo comercial no cambia el dictamen de calidad ni comprueba un pago en banco.

El detalle incluye los campos de cuenta de la relación vinculada al mismo archivo. En nuevos lotes se guardan también todas las columnas originales del Excel; en checkpoints antiguos solo se muestran los datos efectivamente disponibles, indicándolo. Tarjetas y demás cadenas se escriben como texto para preservar ceros y evitar ejecución de fórmulas.

Si el Excel adicional está abierto o falla su escritura, el reporte de calidad se conserva y muestra el error en MOTIVOS_NO_PAGO. No abre silenciosamente un reporte viejo.

## Regresión de esta entrega

Python 3.10.22, Linux: **1,470 pruebas aprobadas, 7 omitidas por necesitar pantalla Tk, cero fallos**. Comprobados compilación, dependencias y apertura del reporte adicional desde el controlador sin pantalla. La interfaz y ejecución de Windows requieren comprobación en la computadora del usuario; no se afirma validación nativa de Windows ni escucha humana.

- Lote de 103: 21 APROBADO, 73 REVISAR, 9 FALLA_GRAVE. Ninguna clasificación cambió. Se conservaron relaciones, transcripciones, quince lecturas y confirmaciones por archivo/contexto, incluidos los recados previamente confirmados.
- Lote de 1,007 recibido: 25 APROBADO, 916 REVISAR, 11 FALLA_GRAVE y 55 ERROR por transcripción ausente. Se analizaron 952 textos. Frente a las reglas r36/r37, nueve graves pasan a revisión; 577 deja de aprobarse y 54 recupera aprobación al reconocerse identidad. Todos los cambios conservan el resto de los bloqueos.
- Verificadas 1,110 filas y 105,450 celdas de los reportes de calidad contra su checkpoint, cero discrepancias. Ambos reportes de motivos suman exactamente sus llamadas y conservan una fila por archivo. Sin fórmulas ejecutables en el reporte nuevo.

Las 55 llamadas sin texto ya venían con error histórico. r37/r38 conservan y recuperan los JSON guardados, pero esos JSON recuperados no están en los archivos recibidos aquí. El diagnóstico histórico r37 declara recuperación en otra computadora: no se presenta como repetida en esta auditoría. Utilice su checkpoint más completo; no lo sustituya por una base incompleta.

## Límites que siguen abiertos

No se certifican cerrados los trece problemas generales. Quedan revisiones de interlocutor, atribución de voz, fechas/importes y calidad ASR que requieren evidencia adicional. REVISAR no es una falta probada. No se relajaron criterios para recuperar una cuota de aprobación.

Los 400 identificadores nombre_final discordantes con numero_de_tarjeta siguen separados del cumplimiento hablado. Para corregirlos existe REANALIZAR_CON_TARJETA_EXCEL.bat sobre un checkpoint completo; conserva la tarjeta de origen y corrige el nombre solo en copia, con trazabilidad. No se desactiva ese control ni se inventan referencias de audio.

Los casos de este diagnóstico pertenecen al lote de 1,007; no trasladar confirmaciones por número de fila al lote de 103 ni a otros lotes. Los documentos r06–r37 se conservan como historial. La validación vigente de esta entrega está en VALIDACION_R38.json.
