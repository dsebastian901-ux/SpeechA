# Revisión 36: confirmar varias llamadas juntas

## Problema y cambio

La herramienta de recados anterior guarda una sola llamada por ejecución.
Esto obliga a seleccionar varias salidas sucesivas y facilita confundir el
checkpoint intermedio con el final. El último archivo recibido mantiene los
dictámenes r32 (17 aprobadas), quince lecturas y una aceptación de recado de
la 67; aún faltan 4, 57 y 96 y la entrega del contacto de la 67.

`CONFIRMAR_RECADOS_LOTE.bat` permite registrar todos esos hechos en una única
operación. Se elige un checkpoint, se indican las llamadas y sus alcances,
se revisan los archivos seleccionados y se genera una sola salida final. Las
casillas no tienen respuestas afirmativas predeterminadas ni llamadas precargadas.

La selección numérica sirve para mostrar el archivo; cada registro final queda
ligado al archivo, cuenta, texto, segmentos, duración y mora. Si el checkpoint
cambia después de la vista previa, se rechaza la operación. Los hechos inválidos,
duplicados o ajenos al lote se rechazan antes de abrir carpetas o escribir.
Los hechos anteriores permanecen, y los cambios de alcance conservan historial.

La generación se ejecuta en un hilo de trabajo; Tk permanece en el hilo principal
y muestra progreso. Mientras se procesa, no se permiten otro guardado ni el
cierre normal de la ventana. Al terminar se muestra la ruta final y un botón
abre la carpeta de resultados en Windows. El intermedio queda en `auditoria`,
con estado incompleto, y el checkpoint de `resultados` se identifica como final.

## Reglas y resultados

No cambian las reglas de dictaminación de r35. Registrar una confirmación no
exime privacidad, tarjetas, ARCO, amenazas, maltrato o rechazo del recado.
Tampoco obliga a aprobar una llamada que conserve otros incumplimientos.

Sobre el archivo recibido, con los hechos ya confirmados para 4, 57, 67 y 96,
se obtienen **21 APROBADO, 73 REVISAR y 9 FALLA_GRAVE**. Los 103 dictámenes
coinciden con la copia r35 ya comprobada, y los 103 puntajes y penalizaciones,
datos originales y quince lecturas permanecen. La aceptación anterior de la
67 se conserva en historial al registrar la entrega completa del recado/contacto.

Se verificaron **1.386 pruebas**, incluidas 23 nuevas y dos pruebas gráficas
reales de la nueva ventana, con vista previa, casillas vacías, guardado en
segundo plano, cancelación y edición posterior a la vista previa. La regresión
de **268 evaluaciones** contra r35 no cambia categorías ni retira penalizaciones.
Se comprobaron 9.785 celdas de resultados del Excel y las cuatro confirmaciones
de la hoja `RECADOS_CONFIRMADOS`.

No se ejecutó Whisper ni se escuchó audio nuevo en la nube. La ejecución nativa
de esta revisión en Windows sigue pendiente. Los 13 problemas operativos
continúan sujetos a validación por llamadas, no se declaran cerrados en conjunto.

## Uso

1. `CONFIRMAR_RECADOS_LOTE.bat`, presente en la raíz y la aplicación.
2. Seleccionar el checkpoint completo actual de 103 llamadas.
3. Aceptación: `4,57,96`; marcar su confirmación.
4. Recado y contacto: `67 | Número para que negocie el restante`; confirmar
   entrega del recado y entrega del contacto, por separado.
5. Revisar los cuatro archivos y guardar todas las confirmaciones juntas.

La salida queda en `MRS_Resultados/Recados_Lote_MRS_…/resultados`:
`checkpoint_reanalizado.json` y `04_Reportes/Reporte_Reanalisis_Reglas.xlsx`.
El botón **Abrir resultados** lleva a esa carpeta. No se sobrescriben las
entradas ni se copian audios. Las herramientas individuales anteriores siguen
disponibles por compatibilidad.
