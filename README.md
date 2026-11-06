# Preparación de la entrega offline del 14/nov/2026

El código de trabajo incorpora Reportes de varios lotes: calidad/mejoras, motivos de no pago y fallas graves; agrupación global, por gestor o supervisor; nivel general o detallado; Excel y recopilación Word de fallas graves. Cada lote se cuenta por separado por decisión de la usuaria. Consulte `proyecto/MRS_Speech_Analytics_v3.6.19_Revision/REPORTES_CONSOLIDADOS.md`.

El uso debe ser sin internet. Whisper se resuelve exclusivamente desde disco/caché local y exige el tokenizer completo; no descarga componentes automáticamente. El futuro instalador debe incluir runtime, dependencias y modelo. El código de cuentas USB firmadas permanece aislado de la GUI mientras se integran inicio de sesión y permisos; la receta de Windows continúa bloqueada como NO_LISTO_PARA_DISTRIBUIR.

La entrega r41 ya publicada sigue siendo la referencia de la prueba de 100 llamadas. Este código de preparación **todavía no es el instalador final con usuarios**. La titular será la única administradora y conservará las revisiones alternas; operadores: solo lotes, dashboard y reportes. Detalle y pendientes en `futuras_actualizaciones/ENTREGA_14_NOV.md`.

---

# Entrega r41

Bloquea toda aprobación ante una queja de mala atención/agresión, incluso de una llamada anterior y aunque el porcentaje supere el mínimo. Bloquea también esperas de 65 segundos o más sin retoma, incluidas las anunciadas. El reporte muestra evidencia y ventanas de tiempo; el estado es REVISAR salvo una falta grave independiente ya confirmada. No atribuye por sí solo culpa al gestor actual.

Extraiga el ZIP completo en una carpeta nueva. Para la prueba de 100 audios NUEVOS use el procesamiento normal de lote con su Excel correcto y el mismo modelo Whisper, guardando resultados en una carpeta nueva. Al finalizar se generan automáticamente el Excel de calidad y el adicional de motivos de no pago. Revise las columnas nuevas de queja/espera y conserve batch_checkpoint.json junto al reporte.

Para audios YA procesados use `REANALIZAR_CHECKPOINT.bat` con su último checkpoint completo, sin volver a ejecutar Whisper. Si necesita también la corrección autorizada de nombres desde numero_de_tarjeta, `REANALIZAR_CON_TARJETA_EXCEL.bat` incluye el reanálisis. Se generan copias y ambos reportes; no se modifican originales ni se mueven las copias físicas antiguas.

Consulte `proyecto/MRS_Speech_Analytics_v3.6.19_Revision/REVISION_41_DIAGNOSTICO.md` y `VALIDACION_R41.json`. Incluyen límites de las marcas ASR y distinguen la integración controlada de 100 archivos del lote real pendiente. Conserva las correcciones r40 de lugares de pago, MRS, comprobantes, privacidad, ARCO y negociación. Los apartados siguientes son historial.

---

# Entrega r40

Corrige listas completas de lugares de pago: ofertas como «el pago lo puede hacer», «puede realizarlo» y enumeraciones consecutivas. Conserva las correcciones r39 de MRS, ticket/comprobante y seguridad. Dos marcas autorizadas distintas; sin bancos sin convenio ni cadenas duplicadas.

Extraiga el ZIP completo en una carpeta nueva. Para audios ya procesados use `REANALIZAR_CHECKPOINT.bat` con su último checkpoint completo. Si necesita también corregir nombres con `numero_de_tarjeta`, use `REANALIZAR_CON_TARJETA_EXCEL.bat`, que incluye el reanálisis. Se generan copias y ambos reportes en `04_Reportes`, sin Whisper.

En audios nuevos, el procesamiento normal de lote genera automáticamente el reporte de calidad y `Reporte_Motivos_No_Pago_FECHA_HORA.xlsx` al finalizar. El reporte adicional agrupa motivos y conserva los datos originales del Excel. No necesita un reanálisis manual para generarlo.

Consulte `proyecto/MRS_Speech_Analytics_v3.6.19_Revision/REVISION_40_DIAGNOSTICO.md` y `VALIDACION_R40.json`. Los apartados siguientes son historial; la validación actual es r40. Los datos reales permanecen separados del programa.

---

# Entrega r39

Corrige reconocimiento de M.A.R.S./M.R./DMRS/MIRS en la presentación, listas de lugares de pago y peticiones de ticket/comprobante. El Excel distingue la solicitud del documento y su canal. Conserva las correcciones de seguridad y el reporte adicional de motivos de no pago de r38.

Extraiga el ZIP completo en una carpeta nueva. Use `REANALIZAR_CHECKPOINT.bat` con su último checkpoint completo. Para corregir también las discordancias de nombre frente a la tarjeta del Excel, use directamente `REANALIZAR_CON_TARJETA_EXCEL.bat`: ya incluye el reanálisis y guarda una copia.

Se generan ambos Excel en `04_Reportes`. No hace falta reinstalar Whisper ni retranscribir para cambiar reglas. Consulte `proyecto/MRS_Speech_Analytics_v3.6.19_Revision/REVISION_39_DIAGNOSTICO.md` y `VALIDACION_R39.json`. Los documentos siguientes son historial; la validación actual es la de r39. Los datos reales quedan separados del programa.

---

# Entrega r38

Correcciones contextuales de trato, privacidad/ARCO, amenazas, liquidación, fechas, identidad, teléfonos/tarjetas y lugares de pago. Añade el Excel de motivos de no pago con los datos de cuentas.

**Para lo ya transcrito:** extraiga el ZIP completo en otra carpeta y ejecute `REANALIZAR_CHECKPOINT.bat` con su último checkpoint completo. No reinstale Whisper ni retranscriba para cambiar reglas. El proceso genera el reporte de calidad y el de motivos en `04_Reportes`.

Consulte `proyecto/MRS_Speech_Analytics_v3.6.19_Revision/REVISION_38_DIAGNOSTICO.md` y `VALIDACION_R38.json`. Los documentos siguientes son historial de versiones; no sustituyen esta validación. Los datos reales se entregan separados del programa.

---

# Entrega r37

Recuperación de transcripciones ante errores de análisis. Consulte `proyecto/MRS_Speech_Analytics_v3.6.19_Revision/REVISION_37_DIAGNOSTICO.md` y `VALIDACION_R37.json` para alcance y pruebas actuales. Los resultados privados se entregan por separado.

# MRS Speech Analytics · revisión 36 — confirmar varias llamadas en una operación

Continuación de la versión 06 recibida en el paquete de migración. El código de
la aplicación está en `proyecto/MRS_Speech_Analytics_v3.6.19_Revision/`.

La revisión incorpora correcciones para fallos reproducidos del lote informado. Los 13 errores siguen pendientes de validación por casos reales.
Es una versión candidata: no está certificada en Windows ni mediante escucha de
las llamadas originales. Consulte `REVISION_36_DIAGNOSTICO.md` dentro de la aplicación para
resultados, cambios y límites por regla. Los documentos de validación anteriores
se conservan como historial, no como certificación de esta revisión.

## Windows

La herramienta anterior admitía una llamada por ejecución. R36 añade
**`CONFIRMAR_RECADOS_LOTE.bat`**, con una sola selección de checkpoint y una
ventana para registrar varias confirmaciones juntas, revisar sus archivos y
generar un único checkpoint y Excel.

Para el bloque ya comprobado por el usuario:

1. Extraiga el ZIP completo y ejecute `CONFIRMAR_RECADOS_LOTE.bat` desde su raíz.
2. Seleccione el checkpoint completo de 103 llamadas. Puede utilizar el último
   `checkpoint_con_recado_confirmado.json` recibido, que conserva las quince
   lecturas y solo contiene aceptación de la 67 además de los hechos anteriores.
3. En **Aceptación del recado**, escriba `4,57,96` y marque que ya comprobó esas
   aceptaciones. En **Recado y contacto entregados**, escriba una línea:
   `67 | Número para que negocie el restante`. Marque los dos hechos ya comprobados.
4. Pulse **Revisar llamadas seleccionadas**, compruebe los cuatro archivos y
   después **Guardar todas y generar checkpoint y Excel**.
5. Al terminar, **Abrir resultados** lleva a la carpeta del checkpoint final y
   el Excel. Continúe con `checkpoint_reanalizado.json`, dentro de `resultados`.

El resultado calculado sigue siendo **21 APROBADO, 73 REVISAR y 9 FALLA_GRAVE**.
Se aplica el mismo motor de reglas y hechos de r35: no se restan penalizaciones
ni se obliga a aprobar las llamadas seleccionadas. La ventana permanece activa
mientras se genera el reporte. Todos los hechos se validan antes de escribir;
si una selección es inválida no se registra parcialmente. El archivo intermedio
queda en `auditoria/entrada.json`, marcado como pendiente de reanálisis; la
salida final queda identificada como tal en `resultados`.

Las entradas y casillas empiezan vacías. No se ejecuta Whisper, no se mueven
audios y se conservan los archivos originales. La ejecución nativa de r36 en
Windows sigue pendiente; la ventana y el trabajo en segundo plano se probaron
con Tk en Linux.

### Historial: recado y contacto confirmados r35

R35 conserva dos hechos distintos: la aceptación de recado ya soportada en
r33/r34, y la entrega efectiva de un recado y un contacto para el titular
confirmada por el usuario. Esta última no exige inventar los dígitos que ASR no
recoge ni atribuye al gestor todo lo que dice el familiar. El parentesco, los
rechazos y los demás controles siguen aplicando.

En la llamada 67 el usuario confirmó que se deja un número para que la titular
negocie el restante. Se conserva su aclaración anterior: el familiar reporta
el pago y el gestor no divulga un saldo. Con los hechos previos de 4, 57 y 96,
el resultado calculado es **21 APROBADO, 73 REVISAR y 9 FALLA_GRAVE**. Solo la
67 cambia desde la copia r34: conserva 100 puntos. Los 103 puntajes y todas las
penalizaciones permanecen; 29 y 39 siguen en revisión por no haberse dejado recado.

Para guardar localmente los hechos ya comprobados, extraiga el ZIP completo:

1. Use el último checkpoint completo de 103 llamadas, conservando las
   confirmaciones existentes. Si faltan las aceptaciones de **4, 57 y 96**,
   regístrelas con `CONFIRMAR_ACEPTACION_RECADO.bat`, una llamada por ejecución.
2. Ejecute **`CONFIRMAR_RECADO_Y_CONTACTO.bat`** para la **67**. Confirme por
   separado que se entrega el recado y el contacto, y describa el mensaje
   comprobado: número para que la titular negocie el restante.
3. En cada paso seleccione el checkpoint **final nuevo** del anterior, dentro
   de `MRS_Resultados/Confirmacion_Recado_MRS_…/resultados`. No use el archivo
   intermedio `checkpoint_con_recado_confirmado.json` para continuar.

Cada operación genera checkpoint y Excel nuevos, sin Whisper ni copia/movimiento
de audios. Si los hechos ya están guardados, `REANALIZAR_CHECKPOINT.bat` de r35
los conserva. Las cifras locales dependen de las confirmaciones presentes en
la base; la ejecución nativa de r35 en Windows sigue pendiente.

### Historial: contenido del recado de retorno r34

R34 reconoce el contenido «a ese número que se comunique con nosotros» cuando
ya existe una aceptación del recado confirmada por el usuario y dictado numérico
cercano atribuible al gestor o de voz no determinada. No convierte la instrucción
sola en recepción, no reconstruye un teléfono a partir de grupos repetidos y
excluye preguntas, negaciones, citas y ejemplos condicionales. Las demás reglas
siguen aplicando.

La llamada 57 tenía parentesco y contexto de retorno, pero faltaba reconocer ese
contenido sin exigir la palabra «recado». Con la aceptación confirmada por el
usuario pasa a APROBADO con 100 puntos. Partiendo de la copia que ya incluye
las confirmaciones de 4 y 96, el resultado calculado es **20 APROBADO,
74 REVISAR y 9 FALLA_GRAVE**. Solo la 57 cambia de categoría; ningún puntaje
o penalización se retira. Las llamadas 29 y 39, donde el usuario confirmó que
no se dejó recado, mantienen revisión de dictamen.

Use `CONFIRMAR_ACEPTACION_RECADO.bat` para registrar localmente una recepción
que ya comprobó, seleccionando el último checkpoint completo y la llamada.
Si ya tiene la confirmación guardada en el checkpoint, basta con
`REANALIZAR_CHECKPOINT.bat` de esta revisión. Continúe siempre desde la salida
final nueva, sin repetir las confirmaciones anteriores ni ejecutar Whisper.
El resultado en su equipo depende de cuáles confirmaciones contenga su base;
las nuevas salidas r33/r34 aún no han sido devueltas para validación nativa.

### Historial: aceptación confirmada r33

La devolución final r32 ya se comprobó: 103 llamadas y 9.785 celdas del Excel
coinciden, con 17 APROBADO, 77 REVISAR y 9 FALLA_GRAVE. Ese checkpoint final
es la base para continuar, sin reconstruir el lote ni volver a confirmar las
llamadas anteriores.

El usuario confirmó que la familiar **sí toma el recado en la llamada 96**.
R33 registra exclusivamente esa aceptación, vinculada al archivo, cuenta y
transcripción. No corrige el ASR, no inventa dígitos del teléfono ni confirma
todas las voces. El parentesco y el contexto de contacto ya están presentes;
el motor vuelve a comprobar las demás reglas antes de aprobar.

Para registrar localmente una aceptación ya comprobada, extraiga el ZIP completo
y ejecute **`CONFIRMAR_ACEPTACION_RECADO.bat`** desde la carpeta principal.
Seleccione el último checkpoint **final r32**, indique la llamada confirmada
y acepte únicamente si ya comprobó la recepción del recado. No hay llamada
preseleccionada. La salida se guarda bajo `MRS_Resultados`, en una carpeta
`Confirmacion_Recado_MRS_…`, y dentro de ella en `resultados`:

- `checkpoint_reanalizado.json`
- `04_Reportes/Reporte_Reanalisis_Reglas.xlsx`

Con la confirmación de la 96, el resultado calculado es **18 APROBADO,
76 REVISAR y 9 FALLA_GRAVE**. Solo cambia la categoría de esa llamada, con
100 puntos; los 103 puntajes, penalizaciones, quince lecturas y confirmaciones
previas permanecen. Si ya dispone de esta copia final, úsela directamente.
Reanalizarla conserva la confirmación. La aceptación no exime rechazos,
desconocimiento del titular, privacidad, amenazas, maltrato, ARCO, referencia
de tarjeta o cualquier otro control aplicable. No se ejecuta Whisper ni se
copian audios. Las 76 revisiones pendientes no equivalen a 76 faltas confirmadas.

### Historial: segundo bloque y seguridad confirmada r32

La revisión incorpora las diez lecturas del segundo bloque conservando el
checkpoint final r31. Recupera aprobaciones con evidencia en las llamadas
11 (aclaración), 65 y 88 (recado). El usuario confirmó divulgación del monto al
esposo en la 56 y advertencia de recuperación en domicilio en la 90, cuenta 1PV.
Corresponden a PEN003 y PEN012: ambas quedan FALLA_GRAVE con registro separado.

Para reproducir el resultado local, extraiga el ZIP completo y use las herramientas
de la carpeta principal en este orden. **En cada paso seleccione el checkpoint
nuevo generado por el anterior.**

1. `INCORPORAR_LECTURAS_BLOQUE.bat`: seleccione el último checkpoint final r31
   de las 103 llamadas y el `revision_audios_bloque.json` de las **diez** lecturas.
   La consola debe informar diez lecturas incorporadas. El origen anterior de
   la lectura se admite solo cuando archivo, cuenta y transcripción coinciden.
2. `CONFIRMAR_DIVULGACION_A_TERCERO.bat`: seleccione el checkpoint recién
   generado, indique **56**, elija el fragmento ORIGINAL **81,88–83,88 segundos**
   y marque las dos afirmaciones ya confirmadas: gestor y destinatario tercero.
3. `CONFIRMAR_ADVERTENCIA_DOMICILIO.bat`: seleccione la salida del paso 2,
   indique **90**, elija ORIGINAL **68,95–77,33 segundos** y marque que lo dice
   el gestor y que confirmó la advertencia en el audio. No hay datos preseleccionados.

El resultado calculado final es **17 APROBADO, 77 REVISAR y 9 FALLA_GRAVE**.
Se conservan las 14 aprobaciones previas, 103 moras, 31 nombres corregidos y
las confirmaciones de las llamadas 10 y 74. Las quince lecturas quedan separadas
del texto original; los cierres repetitivos de 4 y 39 se marcan como advertencias
técnicas, sin penalizar al gestor. Estas operaciones no ejecutan Whisper,
no mueven audios y generan checkpoints y reportes nuevos. No se necesitan
otra transcripción del bloque ni un nuevo modelo.

### Historial: recepción y pago previo r31

Para aplicar r31 al lote ya confirmado, extraiga el ZIP completo y ejecute
`REANALIZAR_CHECKPOINT.bat` desde la carpeta principal. Seleccione el último
`checkpoint_reanalizado.json` **final r30 de las 103 llamadas**. No seleccione el
archivo intermedio `checkpoint_con_divulgacion_confirmada.json` ni el batch original.
No pide volver a registrar la llamada 10, el parentesco de la 74 o las lecturas.

La 59 recupera aprobación al reconocer «dejar una información», respuesta
afirmativa y teléfono completo de retorno, con familiar identificado. La 67
conserva revisión de estatus/recado, pero ya se reconoce su reporte de pago
previo y no se trata «saldo restante» como una afirmación de regularización.
El resultado calculado es **14 APROBADO, 82 REVISAR y 7 FALLA_GRAVE**.
Solo la 59 cambia de categoría; todos los puntajes y penalizaciones del lote
se conservan. Se mantienen las 103 moras, 31 nombres, cinco lecturas y las dos
confirmaciones del usuario. El reanálisis genera otro checkpoint y Excel sin
Whisper, sin mover audios y sin cambiar los originales. Continúe desde esa salida.

El checkpoint final r31 devuelto por el usuario ya se verificó: sus 103
evaluaciones coinciden con la entrega comprobada y conservan todos los datos
y confirmaciones anteriores. Si ya lo generó, úselo como base sin repetir el
reanálisis. Esta última devolución incluyó el checkpoint, no el Excel r31.

### Historial: saldo genérico y divulgación confirmada r30

Si la herramienta anterior se quedaba después de pedir el número de llamada,
use el ZIP r30 corregido. Se reprodujo y corrigió una ventana de confirmación
invisible asociada a una raíz oculta. Ahora aparece la selección de fragmento y
las dos casillas; la consola también informa cuándo está generando las salidas.
Las reglas y resultados de r30 se conservan.

La aclaración del usuario permite decir **«saldo pendiente» sin cantidad**.
La regla distingue esa mención de revelar el importe a un tercero. Se aplica
tanto al texto original como a las lecturas adicionales; no se confunden
teléfonos o terminaciones con montos. Las demás protecciones se conservan.

Para registrar la divulgación del importe ya confirmada en la llamada **10**,
extraiga el ZIP completo y ejecute `CONFIRMAR_DIVULGACION_A_TERCERO.bat` desde
la carpeta principal. Seleccione el **checkpoint final r29 de 103 llamadas**,
indique **10**, seleccione el fragmento **ASR_ADICIONAL, 25,87–30,89 segundos**
y marque los dos hechos ya confirmados: lo dice el gestor y lo recibe un tercero.
Pulse «Registrar confirmación y generar reporte». No hay campos preseleccionados.
No registre las llamadas 59 o 67 como divulgación: la 59 solo menciona saldo
pendiente sin monto; en la 67 el tercero reporta su pago y el gestor recibe esa
información. Se retiran sus alertas genéricas de privacidad y mantienen revisión
por los otros controles pendientes.

Genera otro checkpoint y Excel con **13 APROBADO, 83 REVISAR y 7 FALLA_GRAVE**.
Solo la 10 cambia de categoría y puntaje por PEN003 confirmado. Las 13 aprobaciones,
103 moras, 31 nombres corregidos, cinco lecturas y parentesco de la 74 se conservan.
Continúe desde el nuevo `checkpoint_reanalizado.json`. No se ejecuta Whisper
ni se necesitan otra instalación de modelo o nuevas lecturas del bloque.

Las salidas r30 devueltas por el usuario ya se comprobaron: 103 evaluaciones y
9.785 celdas del Excel coincidentes, sin pérdida de las confirmaciones ni datos
anteriores. Si ya generó estas salidas, conserve `checkpoint_reanalizado.json`
como base; `checkpoint_con_divulgacion_confirmada.json` es el archivo intermedio
con los dictámenes previos. No hace falta repetir el paso.

### Historial: incorporación de lecturas y parentesco r29

Para incorporar el bloque devuelto de cinco lecturas y el parentesco ya
confirmado, extraiga el ZIP completo y ejecute `INCORPORAR_Y_CONFIRMAR_PARENTESCO.bat`
en la carpeta principal. Seleccione el checkpoint final de r28 y después
`revision_audios_bloque.json`. Indique la llamada **74** y el parentesco **HIJA**
para guardar esa confirmación en el archivo local. El programa no incluye los
datos privados del lote. El parentesco no se aplica a otra llamada por número
de fila: se vincula al archivo y su contexto de cuenta y transcripción.

Se conservan las 103 moras, 31 nombres corregidos y las cinco lecturas como
evidencia separada, sin modificar el texto de Whisper. La 47 recupera aprobación
al reconocer la solicitud de dictado del teléfono; la 74 se aprueba con el
parentesco confirmado y la recepción del mensaje. El resultado calculado es
13 APROBADO, 84 REVISAR y 6 FALLA_GRAVE. Los 103 puntajes y penalizaciones no
cambian. Las 10, 59 y 67 conservan revisión de privacidad con voz sin confirmar.

No se ejecuta Whisper ni se mueven audios durante la incorporación. La consola
imprime motor r29 y las rutas de otro checkpoint y Excel. Conserve ese checkpoint
para continuar: la confirmación se preserva en posteriores reanálisis.
`INCORPORAR_LECTURAS_BLOQUE.bat` también está en la raíz para bloques que no
requieren registrar un parentesco nuevo. Los campos de confirmación comienzan vacíos.

`REVISAR_BLOQUE_AUDIOS.bat` está disponible en la carpeta principal del ZIP y
dentro de `proyecto/MRS_Speech_Analytics_v3.6.19_Revision`. Si ya tiene el paquete
anterior, puede usar el lanzador de esa subcarpeta. El acceso de la carpeta
principal abre la misma herramienta de lectura adicional con el modelo existente.
Extraiga el ZIP completo antes de ejecutar cualquiera de los lanzadores.

## Historial: carga de mora r28

La devolución de r27 desde Windows se comprobó: 103 llamadas, 11 APROBADO,
86 REVISAR, 6 FALLA_GRAVE, las 31 correcciones de nombre intactas y las 9.785
celdas del reporte coincidentes. La mora faltaba porque el Excel tiene la columna
`mora` y el lector solo aceptaba `asignacion`; los datos sí estaban en el archivo.

R28 acepta ambas columnas. Para completar el lote ya procesado, extraiga el ZIP
y ejecute `ACTUALIZAR_MORAS_Y_REANALIZAR.bat` desde la carpeta principal.
Seleccione primero `Checkpoint_r27_Recuperado.json` y luego `Calidad Noviembre.xlsx`.
Genera otro `checkpoint_reanalizado.json` y Excel en una carpeta `Reanalisis_MRS_r28_...`.
Se recuperan las 103 moras, cotejando archivo, tarjeta y los datos existentes;
se conservan transcripciones, tarjetas, importes, nombres corregidos y originales.
No se ejecuta Whisper ni se mueve audio. Conserve el nuevo checkpoint como base.

El resultado sigue siendo 11 APROBADO, 86 REVISAR y 6 FALLA_GRAVE: completar mora
no elimina otros motivos de revisión. Los 1.053 registros del Excel se cargan
con su mora para los próximos análisis. Los textos de las hojas de instrucciones
no se usan como reglas del programa. El checkpoint r28 devuelto desde Windows
ya se comprobó: las 103 moras y 31 correcciones de nombre coinciden con la
entrega verificada, sin cambios de puntaje, penalizaciones o clasificación.
Esta comprobación corresponde al checkpoint; no incluye cotejo de un Excel r28
devuelto ni certifica el procesamiento completo de audio nuevo o la escucha humana.

## Historial de la comparación y recuperación r27

Para el lote nuevo de 103, extraiga el ZIP completo y ejecute
`REANALIZAR_CON_TARJETA_EXCEL.bat` desde la carpeta principal. Seleccione el
`batch_checkpoint.json` de r26 de este lote. La consola muestra `3.6.19-r27`.
Genera `Checkpoint_r27_Recuperado.json` y su Excel en una carpeta independiente,
sin Whisper ni lecturas adicionales. Corrige solo el identificador de nombre_final
según numero_de_tarjeta, siguiendo la política de origen autorizada. No cambia
las tarjetas, cuentas o transcripciones. El Excel de cuentas original no se modifica.

En el lote devuelto se corrigieron 31 identificadores y los falsos bloqueos de
recados y teléfonos: el resultado calculado es 11 APROBADO, 86 REVISAR y
6 FALLA_GRAVE. De las 51 aprobaciones anteriores, diez se recuperan; otra llamada
antes mal dictaminada obtiene aprobación. Las otras 41 no se certifican como
correctas: 22 requieren atribución de privacidad, una tiene bloqueo ARCO y
18 conservan otras verificaciones. No se cambió el umbral de 80 ni se escuchó audio.

Las 103 cuentas son iguales entre versiones; 86 transcripciones son idénticas y
17 difieren. R26 también obtiene cero aprobadas al evaluar los textos anteriores:
la diferencia no se explica solo por Whisper. La mora está vacía en ambos
checkpoints; hace falta el Excel de cuentas para investigar su carga. No se
infiere una mora ausente del nombre del audio. Las reglas nuevas también se
aplican al procesamiento normal, que conserva sus funciones de copia de audio.
El reanálisis actualiza clasificaciones y reporte, sin mover ni renombrar audios.

Si ya generó `Checkpoint_r25_95_Audios.json` en Windows, conserve esa base y
ejecute `REANALIZAR_CHECKPOINT.bat` desde la carpeta de la aplicación r27.
Seleccione ese checkpoint final. No repita la reconstrucción ni las diez lecturas.
La consola debe mostrar `3.6.19-r27`; genera otro JSON y Excel sin ejecutar Whisper.

En NO CONOCEN A DEUDOR se exige mencionar expresamente derecho(s) ARCO,
explicar el trámite, indicar el correo oficial y solicitar INE/identificación
oficial **y** comprobante de la línea. Explicar solo la baja o pedir un documento
en lugar del otro no acredita cumplimiento. Los indicios parciales de orientación
conservan REVISAR cuando falta cotejar la transcripción; no autorizan aprobación.
La omisión sin indicios del procedimiento y la negación expresa conservan el bloqueo crítico.

El reporte añade cinco columnas ARCO después de las 90 anteriores. El lote de 95
conserva 13 APROBADO, 80 REVISAR y 2 FALLA_GRAVE, sus puntajes, 22 revisiones de
nombre y diez lecturas. Las llamadas 12 y 21 siguen pendientes de evidencia;
no se da por cumplido el guion. Se conservan los controles de privacidad y negociación.

Si no puede descargar el checkpoint privado del chat, este paquete incorpora
`RECONSTRUIR_BASE_R25.bat` en la carpeta principal del ZIP, junto a este README.
Extraiga el paquete completo antes de ejecutarlo. Windows puede mostrar el nombre
sin la extensión `.bat`. El lanzador también se conserva dentro de la aplicación.
Seleccione su último `checkpoint_reanalizado.json`
completo de 95 llamadas, `revision_audios_bloque.json` con las diez lecturas y,
si se solicita, el `batch_checkpoint.json` original usado para esas lecturas.
El segundo archivo es el resultado anterior de `REVISAR_BLOQUE_AUDIOS`, guardado
junto a `Comparacion_Bloque_Audios.xlsx`; no viene dentro del ZIP del programa.
El selector distingue tipos de JSON y permite volver a elegir si se confunden.
Genera localmente `Checkpoint_r27_95_Audios.json` y su Excel, recuperando los
nombres según `numero_de_tarjeta` previamente autorizado y conservando las
lecturas. No ejecuta Whisper ni procesa de nuevo audios. Las reglas siguen siendo
las del motor vigente r27; el lanzador conserva su nombre R25 por compatibilidad.
Consulte `RECUPERAR_CHECKPOINT_SIN_DESCARGAR.txt` dentro de la aplicación.

El lanzador actualizado muestra `RECONSTRUCTOR R25 - CORRECCION UTF-8` y activa
el modo UTF-8 de Python. Se corrigió la lectura del JSON generado que dependía
de la codificación regional de Windows y podía fallar con `charmap`, byte `0x81`.
No se eliminan tildes ni se modifican datos para evitar el error. Cuando el lote
seleccionado es el mismo `batch_checkpoint.json` que generó las lecturas, bastan
ese archivo y `revision_audios_bloque.json`: no solicita un tercer archivo.

La reconstrucción corregida ya se comprobó en Windows con el checkpoint final y
el Excel devueltos: 95 llamadas, 13 APROBADO, 80 REVISAR, 2 FALLA_GRAVE, las 22
correcciones de nombre y las diez lecturas intactas. Las 8.550 celdas del reporte
coinciden con el JSON. Conserve `Checkpoint_r25_95_Audios.json` como base final;
`checkpoint_con_lecturas.json` es un archivo intermedio con etiquetas anteriores.
Esta comprobación corresponde a la reconstrucción y exportación, no certifica
todo el procesamiento de audio nuevo ni el cierre de los 13 problemas operativos.

Use Python 3.10 de 64 bits. Extraiga el paquete completo, abra la carpeta de la
aplicación y ejecute `INSTALAR.bat`; después `INICIAR_MRS.bat`. Los lanzadores y
dependencias originales se conservan. La primera transcripción de audio nuevo
necesita descargar el modelo de Whisper desde Hugging Face.

Para probar las reglas nuevas sobre textos guardados, ejecute
`REANALIZAR_CHECKPOINT.bat`. La consola debe mostrar `3.6.19-r27` y crear una
carpeta `Reanalisis_MRS_r27_...`. Este paso no vuelve a transcribir audios.
Si ya recuperó importes, seleccione el checkpoint final de esa recuperación;
así se conserva la evidencia sin volver a ejecutar Whisper.

Para recuperar un importe omitido, ejecute `RECUPERAR_IMPORTES.bat`, seleccione
el checkpoint y la carpeta de sus audios originales. Se releen únicamente
ventanas de ofertas incompletas; se conservan los textos originales y se genera
un checkpoint nuevo y un Excel dentro de `Recuperacion_MRS_r27_.../resultados`.
La evidencia aparece en las columnas finales de recuperación. Un importe
recuperado por ASR conserva revisión de evidencia. El efecto del mínimo se valida
por mora: regularización/mensualidad o liquidación. En las moras de liquidación,
el mínimo del Excel es la referencia; no se exige el saldo total ni una columna
adicional de autorización por la diferencia entre mínimo y saldo.
Este control también se aplica al procesar audios nuevos. Se usa el mismo modelo
configurado, sin instalar otro Whisper ni actualizar Python.

La revisión 15 contrasta las hojas 04, 05, 06, 13 y 14 del manual recibido.
Por aclaración expresa del usuario, 3HN, 4PV–6PV, C1–C4, B y A se liquidan
durante el mes de la llamada: un vencimiento posterior no prolonga ese plazo.
En 1PV–3PV y 1-FLP se conservan corte y vencimiento. En dos exhibiciones, la
primera queda dentro de tres días de la llamada y la segunda hasta siete días
desde la primera, sin exceder el vencimiento. Sin esa excepción, rige el plazo
general de tres días. La excepción no prolonga el mes permitido para liquidación.

Para registrar un importe recuperado ya comprobado por una persona, ejecute
`VALIDAR_IMPORTES.bat` y seleccione el checkpoint final. Las casillas comienzan
desmarcadas. Confirme solo los importes comprobados; si el identificador de
nombre_final difiere de numero_de_tarjeta, puede corregirlo en una copia usando
la tarjeta de origen. Guarde para generar un checkpoint y reporte nuevos en
`Validacion_MRS_r27_.../resultados`. Cuando se localiza o selecciona el Excel
de cuentas, también se genera `Datos_Cuentas_Corregidos.xlsx` sin cambiar el original.
En análisis individual existe el botón Validar importe. La confirmación se
conserva para reanálisis posteriores y no exime las demás reglas de calidad.

En revisión 18, la misma herramienta permite registrar un saldo confirmado en
audio cuando ASR lo transcribió distinto, o confirmar el plan final de
parcialidades después de propuestas con cantidades diferentes. El saldo se
escribe en un campo inicialmente vacío; las casillas siguen desmarcadas.
Se conservan las confirmaciones previas de otras llamadas aunque no se vuelvan
a marcar. No se rellenan importes usando el saldo esperado del Excel.

Los hechos confirmados se guardan por separado, ligados a la llamada y su
evidencia. El texto original de Whisper y las propuestas iniciales se conservan.
El Excel añade las columnas Confirmación financiera, Saldo ASR original,
Saldo confirmado por usuario, Parcialidades finales confirmadas e Historial de
propuestas de parcialidades. Un reanálisis conserva las confirmaciones válidas.
La herramienta también permite revocarlas y volver a evaluar la lectura ASR.

Para incorporar las confirmaciones de una muestra al lote completo, ejecute
`INCORPORAR_VALIDACIONES.bat`. Seleccione primero el checkpoint del lote completo
y después el checkpoint final de la muestra ya validada. Las llamadas se cruzan
por nombre exacto, texto, segmentos, duración y datos de cuenta. Si hay una
diferencia o una confirmación incompatible, se detiene la incorporación.

La salida está en `%USERPROFILE%\MRS_Resultados\Integracion_MRS_r27_...\resultados`.
Conserva todas las llamadas y sus datos originales, agrega la evidencia recuperada
necesaria y las confirmaciones válidas, y recalcula las clasificaciones.
No se trasladan etiquetas de aprobación ni puntajes mínimos de la muestra.
Solo se corrige un nombre de salida si lleva su confirmación explícita anterior.
Si se localiza el Excel de cuentas, se genera una copia con esos nombres corregidos.
La consola y la hoja NOTA_REANALISIS indican los archivos nuevos y el alcance.
No se ejecuta Whisper ni se copian audios.

La revisión 21 incorpora la aclaración del usuario: se conserva CONVENIO o
NO DEFINE FECHA DE PAGO en un seguimiento de pago reportado y comprobante.
Se separan importes de fechas, plazos y teléfonos; una terminación de WhatsApp
no se compara como tarjeta. Se reconocen variantes de identidad, parentesco,
aceptación de recados y rechazo de una negociación posterior a un pago histórico.
Se mantienen la atribución de liquidaciones, privacidad, maltrato, fechas,
montos y dos lugares autorizados cuando hay una negociación nueva.

El puntaje refleja las penalizaciones observadas; se retira el límite artificial
de 79 por estatus no confirmado. Una llamada con evidencia pendiente conserva
REVISAR aunque obtenga 100 puntos. Los textos ASR y datos de cuenta se conservan.
La revisión 22 corrige fechas tomadas de teléfonos/convenios, importes dictados
sin «pesos», advertencias de parcialidad negadas, aceptación de pagos y
reiteraciones de un pago histórico que se volvían a sumar. Un importe reportado
como incierto conserva revisión. El resumen Excel distingue clasificación
calculada, discrepancias de estatus y validación financiera.

El lote privado de 95, con 22 nombres corregidos según la instrucción expresa de
usar numero_de_tarjeta, obtiene en r25 13 APROBADO, 80 REVISAR y 2 FALLA_GRAVE.
Se conservan las 12 aprobaciones de r23. El reanálisis ordinario no corrige nombres
por sí solo: use el checkpoint corregido entregado para conservar esos cambios.
El reporte de auditoría identifica los bloqueos de cada una de las 85 llamadas
que estaban pendientes; REVISAR no significa falta confirmada. Se incorporaron
las diez lecturas nuevas devueltas por el usuario, sin nueva escucha humana ni
ejecución de Whisper en esta nube.

Para aplicar estas reglas a un lote existente, use REANALIZAR_CHECKPOINT.bat
con el checkpoint más reciente de ese lote. La aprobación calculada y el
renombrado físico son pasos distintos: este reanálisis actualiza JSON y Excel,
conservando los audios. Las llamadas nuevas usan las reglas al procesarse.

Las tres herramientas guardan ahora cada ejecución en una carpeta independiente
dentro de `%USERPROFILE%\MRS_Resultados` (por ejemplo,
`C:\Users\Usuario\MRS_Resultados`). No se anidan dentro del checkpoint anterior:
esto corrige el fallo de guardado al acumular recuperaciones y reanálisis.
Antes de generar archivos se comprueba que las rutas de salida, incluido el Excel
temporal, quepan en el límite conservador de Windows. `--output-dir` permite elegir
otra carpeta corta, nueva y vacía al ejecutar las herramientas desde la consola.

Para reproducir las pruebas en esa carpeta:

```bat
py -3.10 -m pip install -r requirements-dev.txt -c constraints-tested.txt
py -3.10 -m pytest -q
```

Las versiones de `constraints-tested.txt` fueron ejecutadas en Linux con Python
3.10.22. Los archivos recibidos acreditan el lector de bloques r23 y la
reconstrucción/exportación corregida r25 en el Windows del usuario. La validación
completa de la aplicación r27 y de su procesamiento de audio nuevo sigue pendiente.

## Entorno de desarrollo en la nube

Desde `/workspace/SpeechA`, ejecute `bash setup-cloud.sh`. Las dependencias quedan
en `/workspace/SpeechA/.venv`; después:

```bash
cd proyecto/MRS_Speech_Analytics_v3.6.19_Revision
/workspace/SpeechA/.venv/bin/python -m pytest -q
```

Para comparar la base original con esta revisión, conserve el ZIP original
extraído en una ubicación privada y ejecute, desde la carpeta de la aplicación:

```bash
python tools/regression_checkpoints.py \
  --input-dir /ruta/privada/pruebas_checkpoints \
  --baseline-source /ruta/privada/proyecto/MRS_Speech_Analytics_v3.6.19_Revision \
  --reviewed-changes tests/reviewed_r22_from_original.json \
  --output-dir /ruta/privada/resultados_revision_actual
```

No suba checkpoints, audios ni resultados reales a un repositorio público.
El paquete de código excluye esos datos; los resultados privados se conservan fuera de Git.

La regresión contra r21 usa como base su carpeta de aplicación extraída y
`--reviewed-changes tests/reviewed_r22_changes.json`. El documento original de
cambios permanece intacto. Ambos recorridos de 268 evaluaciones verifican hashes
de origen, causas de retiro de penalizaciones e invariantes; no copian etiquetas
históricas de aprobación. La suite actual contiene 1.064 pruebas. La regresión
de r29 con 268 evaluaciones contra r28 no cambia clasificaciones ni retira
penalizaciones sin causa.

## Revisión adicional de un bloque de audio

Extraiga la aplicación y ejecute `REVISAR_BLOQUE_AUDIOS.bat` en el mismo Windows
donde ya funciona Whisper. Seleccione el checkpoint completo más reciente y la
carpeta de hasta 10 audios originales del bloque. No hace falta instalar otro
Whisper: la herramienta exige que el mismo modelo usado en el checkpoint ya esté
localmente disponible; no descarga otro modelo ni cambia la configuración.

Se crea una carpeta `Revision_Audios_r27_...` en `%USERPROFILE%\MRS_Resultados`
con `revision_audios_bloque.json` y `Comparacion_Bloque_Audios.xlsx`. Guarda una
lectura completa con marcas de palabra y otra del cierre sin VAD, ambas como
hipótesis ASR. No cambia el checkpoint, sus validaciones, los dictámenes ni los
audios. No atribuye hablantes ni marca escucha humana. El JSON de lectura se
comparte para revisar; no es un checkpoint para REANALIZAR_CHECKPOINT.

Las diez lecturas r23 recibidas se cruzaron con los audios y el lote actual. Se
detectaron fragmentos repetitivos o mal alineados en tres llamadas; el lector
r24 los advierte sin tratarlos como infracciones. El texto bruto se conserva.

El paquete privado r24 ya contiene las diez lecturas vinculadas al checkpoint de
95 y el reporte final: no hace falta volver a transcribir ni repetir el lote.
La llamada 12 reconoce el correo ARCO dictado con dominio literal, pero conserva
la revisión de privacidad. No se confirman voces ni aceptación de recados por ASR.

Para incorporar resultados de otros bloques, use `INCORPORAR_LECTURAS_BLOQUE.bat`:
seleccione el checkpoint completo actual y `revision_audios_bloque.json`. Para
lecturas r23 generadas sobre otro checkpoint, se solicita también aquel origen.
Se comprueban texto, segmentos, duración y cuenta; no se importan aprobaciones ni
puntajes. Se conserva todo lo anterior y se genera otra copia con JSON y Excel,
sin ejecutar Whisper. El reporte añade tres columnas a las 87 anteriores.

El reconocimiento nuevo se ejecutó en el equipo del usuario, no en esta nube.
Las pruebas locales incluyen casos sintéticos y los resultados recibidos;
no acreditan escucha humana ni ejecución nativa de r27 en Windows. La verificación
nativa devuelta de r25 corresponde a reconstrucción y exportación.

## Correcciones de interlocutor y negociación (r25)

Se reconoce «somos conocidos/amigos» como tercero, sin inferir parentesco ni
aceptación del recado. Revisar cargos antes de pagar y «si corresponde, pagaré»
no acreditan un compromiso firme. Se separan pagos anteriores de instrucciones
nuevas y se evita confundir una fecha mensual con un cargo recurrente.

La llamada 83 recupera aprobación de calidad con NO DEFINE FECHA DE PAGO; no se
inventa un convenio aceptado. La 7 conserva revisión. Los 95 puntajes permanecen
iguales; el lote queda en 13 APROBADO, 80 REVISAR y 2 FALLA_GRAVE. Se conservan
las correcciones y confirmaciones anteriores.

La entrega r25 ya incluye el reporte y `Checkpoint_r25_95_Audios.json`; use ese
checkpoint para el próximo cambio de reglas. No necesita volver a transcribir
los audios ni repetir el reanálisis para obtener el reporte entregado.
