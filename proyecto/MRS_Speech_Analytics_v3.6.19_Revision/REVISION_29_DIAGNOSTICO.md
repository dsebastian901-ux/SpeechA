# Revisión 29: bloque recibido y parentesco confirmado

Se recibieron cinco lecturas adicionales de las llamadas 10, 47, 59, 67 y 74
del lote de 103. Aunque son distintas del bloque sugerido, todas pertenecen al
checkpoint r28 devuelto: coincide el hash del origen y los enlaces de contexto,
textos, segmentos y duraciones. Hay cinco lecturas completas, cero errores de
ejecución y cero alertas de degradación técnica. El Excel de comparación coincide
con los textos completos y cierres del JSON recibido.

El reconocimiento se ejecutó en el equipo del usuario: small, CPU/int8, beam 5,
marcas de palabra y cierre sin VAD. En esta nube no se ejecutó Whisper ni se
escucharon los audios originales. Las lecturas son hipótesis ASR, no asignaciones
de voz verificadas. La ausencia de alertas técnicas no certifica cada palabra.

## Corrección de recepción del recado

En la llamada 47, el receptor pide el dictado («a ver») después de ofrecerle un
teléfono para que el titular se comunique, y a continuación se dicta un número
completo de diez dígitos. El detector solo buscaba algunas respuestas literales
y no reconocía esa secuencia ni la variante «se comunique con nosotros».

Se reconoce la secuencia completa: oferta del número con finalidad de retorno,
solicitud del dictado y teléfono completo. Un «a ver» aislado, un agradecimiento,
una pregunta sin respuesta, una cita, una negación o palabras conocidas del
gestor no bastan. Esto acredita recepción del contacto, no aceptación de un pago.
También se reconoce la finalidad «se comunique inmediatamente con nosotros» y
se conserva la repetición solicitada del teléfono como evidencia de transmisión.

## Parentesco de la llamada 74

Las dos lecturas escriben «tu hija». El usuario primero indicó que no lo había
confirmado y después aclaró que es su hija. Se usa esa última aclaración como
confirmación del usuario, sin sustituir el texto de Whisper por «su hija».

El registro separado tiene alcance FAMILY_RELATIONSHIP_ONLY y queda ligado al
archivo, transcripción, segmentos, duración y datos de cuenta. El parentesco no
se transfiere a otra llamada por compartir número de fila. Se conserva al
reanalizar; si cambia el contexto, el registro deja de validar y requiere revisión.
El cambio autorizado del nombre de salida no cambia la identidad de la cuenta.

La confirmación solo resuelve parentesco. No confirma las voces ASR, no acredita
por sí sola el recado y no exime privacidad, tarjeta, trato, visitas, ARCO o pago.
La recepción se verifica además mediante el teléfono repetido por el interlocutor.
El Excel muestra que el parentesco procede de confirmación del usuario en la
columna existente de evidencia de estatus. No se añaden datos reales al código.

## Resultado y conservación

| Lote de 103 | r28 | r29 con las cinco lecturas y parentesco confirmado |
|---|---:|---:|
| APROBADO | 11 | 13 |
| REVISAR | 86 | 84 |
| FALLA_GRAVE | 6 | 6 |

Solo cambian de categoría las 47 y 74. Se conservan los 103 puntajes y todas sus
penalizaciones; no se cambia el umbral de 80. La 47 permanece en 80 puntos y la
74 en 100. Con las lecturas, pero sin registrar el parentesco confirmado, la 74
conserva REVISAR. No se interpreta automáticamente «tu hija» como parentesco.

Las 10, 59 y 67 conservan revisión por información financiera con voz sin
confirmar. No se convierten en PEN003 crítico a partir de estas lecturas. Las
cinco lecturas originales y sus cierres se conservan sin sustituir transcripciones,
31 revisiones de nombre, 103 importaciones de mora o hechos financieros previos.

## Uso local

1. Extraer el ZIP completo y ejecutar `INCORPORAR_Y_CONFIRMAR_PARENTESCO.bat`
   desde la carpeta principal.
2. Seleccionar el checkpoint **final r28 de estas 103 llamadas**.
3. Seleccionar `revision_audios_bloque.json` del bloque recibido.
4. Indicar llamada **74** y parentesco **HIJA**, ya confirmado por el usuario.

Se comprueba que la llamada elegida pertenece al bloque antes de crear salidas.
No hay un parentesco ni una llamada preseleccionados. Las confirmaciones previas
se conservan y cualquier actualización explícita deja historial. La consola
muestra revisión r29, cinco lecturas, una confirmación y los resultados.

La salida queda en una carpeta independiente de `%USERPROFILE%\MRS_Resultados`,
con `checkpoint_reanalizado.json` y `Reporte_Reanalisis_Reglas.xlsx` nuevos.
No requiere otro modelo, transcribir de nuevo ni mover audios. La incorporación
ordinaria, sin un parentesco nuevo, sigue disponible en
`INCORPORAR_LECTURAS_BLOQUE.bat`, ahora también en la carpeta principal.

## Pruebas y límites

- 1.064 pruebas aprobadas, incluidas 48 nuevas de recepción, confirmación,
  contexto, alteraciones, papel del hablante, conservación y controles independientes.
- 268 evaluaciones históricas frente a r28: cero cambios de clasificación,
  cero violaciones de invariantes y cero retiros de penalizaciones sin causa.
- Los lotes anteriores de 95 y 36 conservan 13 y 7 aprobaciones, las 22 y 13
  revisiones de nombre, las diez lecturas del primero y los hechos financieros.
- Las 9.785 celdas del reporte nuevo se comparan con el JSON sin diferencias;
  se conservan las 95 columnas del reporte y todos los datos de origen.
- El lector r28 ya se ejecutó en Windows. La incorporación y registro de r29
  se probaron en Linux con Python 3.10; falta devolución nativa de ese paso.

No se declara verificación acústica de voces ni cierre de los 13 problemas
operativos. Los archivos reales y las confirmaciones privadas permanecen fuera
de Git. El ZIP permite aplicar la corrección y guardar el dato en el equipo local.
