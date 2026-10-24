# Revisión 07 · candidata

Se trabaja sobre la versión 06, conservando los componentes de GUI, audio,
Whisper, reportes, clasificación de archivos y lanzadores de Windows. El paquete
original de migración permanece intacto fuera del repositorio. No se reemplazó
la aplicación con un ZIP histórico.

## Los 13 errores

| Nº | Corrección y cobertura reproducible | Límite |
|---|---|---|
| 1 | Una puerta común de decisión para individual, solo audios y Excel. El reporte diferencia dictamen pendiente de discrepancia confirmada. | Una etiqueta histórica no constituye verdad de dictaminación. |
| 2 | RECADO REF1/REF2 equivale a MENSAJE CON FAMILIAR solo con parentesco declarado, mensaje de contacto y recepción explícita sin rechazo. | No se confirma entrega real escuchando audio. |
| 3 | PEN003 conserva 100 puntos y bloqueo crítico para divulgación atribuida al gestor ante tercero confirmado. Una palabra aislada no basta; voz incierta bloquea en REVISAR. | Los checkpoints no incluyen diarización; no se certifican falsos positivos acústicos. |
| 4 | Preguntas, negaciones, palabras del gestor y mencionar a un familiar propio no acreditan identidad del destinatario. Agradecer el recado no acredita aceptación. | Se requiere revisar audio cuando el texto no resuelve quién contestó. |
| 5 | Cotejo de 16 dígitos continuos, por grupos o hablados; sin ceros añadidos ni ventanas que fabriquen tarjetas. Repeticiones y datos Excel incompletos van a revisión. | La transcripción discordante exige contraste con el audio. |
| 6 | ARCO requiere explicación del procedimiento cuando se confirma desconocimiento del titular. Correo solo no basta; INE se coteja como palabra; se comprueba antigüedad de línea y destino de privacidad. Omisión de ARCO es crítica. | Se conservan los destinos de privacidad del código recibido; falta contrastar el manual operativo vigente. |
| 7 | Se cuentan lugares ofrecidos para pagar, distintos y autorizados; se evitan marcas anidadas, negaciones, preguntas del cliente y tienda de origen. Dos en convenio nuevo, ninguno obligatorio en recado o pago ya realizado. | Catálogo y convenios bancarios conservados de la versión 06. |
| 8 | Visitas, diligencias y cobro a domicilio anunciados en 1–2 PV bloquean como amenaza; la negación explícita no lo hace. | Cobertura por construcciones textuales comprobadas, no comprensión ilimitada del lenguaje. |
| 9 | Se recorre todo el texto, incluido el final sin segmentos. Se conserva evidencia con rol y tiempos del segmento cuando existen; ofensa del gestor confirmada es crítica. | Un ID SPEAKER_00 no identifica al gestor; falta escucha original. |
| 10 | Botón **Validar trato** en Analytics. Cuatro confirmaciones humanas requeridas para APROBADO_CON_EXCEPCION; se guardan aparte y se invalidan si cambia la transcripción. | Solo debe marcarse lo comprobado escuchando el audio. No se preselecciona ninguna confirmación. |
| 11 | Denuncia de maltrato previo bloquea aprobación y también la excepción por hostilidad. | La responsabilidad de la denuncia requiere investigación humana. |
| 12 | Pruebas para propuesta válida, mínimos/totales, fechas posteriores al vencimiento, pago ya realizado y liquidación histórica del cliente. Se preservan las reglas financieras anteriores; incertidumbre se muestra como REVISAR. | Descuentos no verificables y ASR ambiguo necesitan respaldo. |
| 13 | Dictamen canónico compartido por interfaz, checkpoint y Excel: APROBADO, APROBADO_SIN_ETIQUETAR, APROBADO_CON_EXCEPCION, REVISAR, FALLA_GRAVE. Se conserva NO_APROBADO_MENOR_80 como resultado por umbral. | Superar el puntaje no elimina bloqueos; solo APROBADO permite el renombrado ordinario. |

## Evidencia de esta entrega

- 152 pruebas unitarias y de integración aprobadas con Python 3.10.22 en Linux.
- 268 evaluaciones reproducidas: 108 recientes y 160 del checkpoint anterior;
  corresponden a 196 textos distintos, no a 268 llamadas independientes.
- Checkpoints recientes: 104 REVISAR y 4 APROBADO, frente a 40 faltas graves,
  64 revisiones y 4 aprobaciones calculadas por la base. Las 40 divulgaciones
  sin atribución comprobada quedan en revisión; no se convierten en aprobación.
- Checkpoint anterior: 149 REVISAR y 11 FALLA_GRAVE. No se añadieron aprobaciones.
- Cero incumplimientos de los invariantes de seguridad comprobados. Se revisó
  expresamente la retirada de PEN010 en el caso 099 del checkpoint anterior:
  «puede tomar una captura de pantalla» no identifica a un tercero. Conserva
  los bloqueos por lugares y transferencia, y sigue en REVISAR.
- La referencia investigada, enmascarada como `4812…5012`, se reconstruye por
  grupos en los casos 019, 033, 053 y 099 del checkpoint anterior. Difiere del
  Excel en los cuatro y queda en REVISAR; no se certifica el número pronunciado.
- GUI iniciada y cerrada en una pantalla virtual de Linux; comprobado el nuevo
  diálogo de validación con cuatro casillas inicialmente desmarcadas.
- Audio WAV nuevo descubierto, validado y decodificado por el decodificador de
  Faster-Whisper. Esto no es una prueba de reconocimiento de voz.

La auditoría privada incluye comparación por evaluación, evidencia textual,
roles y tiempos disponibles, resultados completos y salida JUnit de las pruebas.
No se incluyen esos datos en el paquete de código.

## Qué no se ha verificado

No se dispone de los audios originales. No se verificó la instalación Windows,
la reproducción local en Windows ni la precisión acústica. La descarga del
modelo público de Whisper devolvió **403 del proxy** en este entorno; el paquete
importa correctamente, pero no se ejecutó reconocimiento de audio nuevo.
Se guardan los dominios necesarios en la configuración del entorno para revisión;
guardar un borrador no aplica ni publica esa configuración.

Las pruebas cubren expectativas explícitas y regresión contra el código de base;
no demuestran que todas las transcripciones posibles estén dictaminadas correctamente.

## Validación humana de hostilidad

Abra una llamada en Analytics y use **Validar trato** tras escucharla. Se exige
confirmar escucha, hostilidad/ofensa/lascivia del interlocutor, impedimento para
completar el guion y profesionalismo del gestor. La revisión se guarda en
`.reviews/<transcripcion>.json`, junto a las transcripciones y separada del JSON
original de Whisper. Un cambio del JSON original invalida la revisión anterior.
Privacidad, maltrato previo, amenazas, referencias o fallas financieras siguen
bloqueando la excepción. El lote reutiliza esta revisión al cargar el JSON.
