# Revisión 35: recado y contacto entregados, confirmados por el usuario

## Hechos y alcance

En la llamada 67 el usuario confirmó primero que se deja un recado para la
titular y después precisó su contenido: un número para que negocie el restante.
La transcripción recoge principalmente el reporte de un pago por el familiar
y orientación sobre cancelación de tarjeta; no permite reconstruir por sí
sola el contacto de negociación que el usuario comprobó en el audio.

Se incorpora `RECADO_AND_CALLBACK_DELIVERED_ONLY`, separado del alcance anterior
`RECIPIENT_ACCEPTED_RECADO_ONLY`. Exige dos hechos explícitos (entrega del recado
y del contacto) y una descripción del mensaje. El registro queda ligado a
archivo, cuenta, mora, texto, segmentos y duración. No reescribe Whisper, no
inventa dígitos del teléfono y no confirma todas las voces del audio.

La entrega comprobada acredita recepción efectiva sin afirmar que ASR contiene
un «sí» del interlocutor. El registro no agrega parentesco ni exime desconocimiento
del titular, rechazo de recado, privacidad, tarjeta, amenazas, groserías o maltrato.
El familiar que reporta un pago no se convierte en divulgación por el gestor.
Si la descripción humana contiene información financiera protegida, permanece
en revisión: confirmar entrega no autoriza ese contenido ni inventa PEN003 a
partir de un resumen. «Saldo pendiente» sin importe conserva la excepción
operativa ya indicada por el usuario.

Los registros de aceptación anteriores siguen validando y manteniendo su hash.
Cambiar de alcance o descripción conserva historial. Repetir el mismo hecho es
idempotente; cambiar el contexto, alterar el registro o revocarlo exige revisión.
Los reanálisis sucesivos conservan el hecho humano y su alcance.

## Resultado de la copia de trabajo

- **21 APROBADO, 73 REVISAR y 9 FALLA_GRAVE**, de 103 llamadas.
- Solo la 67 cambia respecto a la copia r34; conserva 100 puntos y ningún PEN003.
- Los otros 102 dictámenes y los 103 puntajes y penalizaciones se conservan.
- Se conservan los hechos de 4, 57 y 96, las quince lecturas y todas las
  confirmaciones anteriores. 29 y 39 siguen en revisión por no dejar recado.
- El Excel incluye la hoja `REVISION_USUARIO` con los seis casos revisados.

## Validación

Se ejecutaron **1.363 pruebas**, con 50 pruebas nuevas de alcance, datos mínimos,
doble confirmación, vínculo al contexto, conservación de aceptación antigua,
historial, persistencia, exclusiones de seguridad y cancelación de las ventanas.
La regresión de **268 evaluaciones** contra r34 no cambia categorías ni retira
penalizaciones. Se comprobaron las 9.785 celdas de resultados del Excel sin
diferencias con el checkpoint.

No se ejecutó Whisper ni se escucharon estos audios en la nube. La evidencia
acústica procede de las confirmaciones del usuario. La ejecución nativa de r35
en Windows sigue pendiente. Los 13 problemas operativos no se declaran cerrados.

## Aplicación local

`CONFIRMAR_RECADO_Y_CONTACTO.bat` está en la raíz del ZIP y en la carpeta de
aplicación. Solicita el checkpoint actual y el número de llamada, confirma
recado y contacto por separado y pide la descripción escuchada. Las preguntas
no tienen respuesta afirmativa preseleccionada ni contenido completado.
`CONFIRMAR_ACEPTACION_RECADO.bat` conserva su alcance anterior.

Para una entrega ya comprobada, equivalente en consola desde la aplicación:

```text
py -3.10 -X utf8 tools\confirm_recado_acceptance.py --checkpoint "RUTA_CHECKPOINT_FINAL.json" --call NUMERO --delivered-recado --description "CONTENIDO COMPROBADO" --confirm-message --confirm-callback
```

Las salidas nuevas están bajo `MRS_Resultados/Confirmacion_Recado_MRS_…/resultados`.
Continúe desde `checkpoint_reanalizado.json`, no desde el intermedio. No se
sobrescriben archivos de origen, ejecuta Whisper, ni mueven o copian audios.
El código publicado no contiene checkpoints, reportes o grabaciones reales.
