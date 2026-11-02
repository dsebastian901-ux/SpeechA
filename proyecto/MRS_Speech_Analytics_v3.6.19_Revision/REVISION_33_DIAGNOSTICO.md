# Revisión 33: aceptación de recado confirmada por el usuario

## Base comprobada

Se verificaron el checkpoint final r32 devuelto por el usuario y las 9.785
celdas de resultados de su Excel: 103 llamadas, 17 APROBADO, 77 REVISAR y
9 FALLA_GRAVE. Se conservaron las quince lecturas y los hechos previamente
confirmados sobre parentesco y divulgación/advertencia. No se escuchó audio
nuevo en la nube.

## Alcance del nuevo hecho

En la llamada 96 el usuario confirmó que la familiar toma el recado. El
checkpoint ya identifica parentesco y contexto de contacto; su texto original
no acredita por sí solo la aceptación. Esa confirmación resuelve únicamente
la recepción, mediante `recado_acceptance_confirmation`. La aclaración sobre
la queja de horario tampoco atribuye las llamadas anteriores a este despacho;
esa llamada no tenía penalización por horario o maltrato en la base r32.

El registro no cambia el texto ni los segmentos de Whisper, no certifica cada
dígito telefónico, no agrega parentesco y no asigna roles al resto de las voces.
Se vincula mediante hash al archivo, cuenta, texto, segmentos, duración y mora.
Cambiar el nombre final de salida no invalida la identidad. Cambiar el contexto,
alterar el registro o revocarlo obliga a revisión. La confirmación se conserva
en reanálisis sucesivos.

No hay excepciones para privacidad, rechazo del mensaje, desconocimiento del
titular, tarjeta incorrecta, queja de maltrato, groserías, amenaza u otros controles.
La recepción sin familiar identificado o sin mensaje/contacto no acredita por sí
sola MENSAJE CON FAMILIAR. El motor decide de nuevo; la herramienta no fuerza
una categoría ni resta penalizaciones.

## Resultado y validación

- Lote actual: **18 APROBADO, 76 REVISAR y 9 FALLA_GRAVE**.
- Solo la 96 cambia de REVISAR a APROBADO, conservando 100 puntos.
- Las otras 102 categorías y los 103 puntajes y penalizaciones permanecen.
- Las quince lecturas, datos originales y todas las confirmaciones previas
  permanecen intactos; 9.785 celdas del nuevo Excel comprobadas.
- **1.282 pruebas** aprobadas, incluidas las cinco verificaciones gráficas
  Linux existentes y 32 pruebas nuevas de aceptación, aislamiento y persistencia.
- Regresión de **268 evaluaciones**, cinco checkpoints, contra r32: cero cambios
  de categoría, cero retiros de penalizaciones y cero fallos de seguridad.

La validación nueva es funcional en Linux/Python 3.10; la ejecución nativa de
esta nueva herramienta en Windows sigue pendiente. No se cambian dependencias,
Whisper, sistema operativo ni modelo. Los 13 problemas operativos no se declaran
cerrados: continúan las revisiones por llamada.

## Uso local

`CONFIRMAR_ACEPTACION_RECADO.bat` aparece en la raíz del ZIP y en la carpeta
de aplicación. Solicita el checkpoint completo actual, número de llamada y
confirmación de aceptación; no tiene una llamada o aceptación preseleccionada.
La salida final está en `Confirmacion_Recado_MRS_…/resultados`, junto a su Excel.
El archivo `checkpoint_con_recado_confirmado.json` es intermedio y aún contiene
los dictámenes anteriores. Continúe con el `checkpoint_reanalizado.json` final.

Equivalente para una confirmación ya comprobada en consola:

```text
py -3.10 -X utf8 tools\confirm_recado_acceptance.py --checkpoint "RUTA_CHECKPOINT_FINAL.json" --call NUMERO --confirm-acceptance
```

No se sobrescriben los archivos de origen ni se ejecuta Whisper, y no se copian
o mueven audios. Los checkpoints, reportes y evidencias reales quedan fuera de Git.
