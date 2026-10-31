# Revisión 26: procedimiento completo de derechos ARCO

El usuario aclara que el proceso completo incluye mencionar expresamente
derecho(s) ARCO. Su aclaración posterior sustituye la respuesta anterior que
permitía explicar la baja sin nombrarlos. Se contrasta con SCR011, EST010,
RN022 y RN023 del manual recibido. No se modifica el umbral de aprobación.

## Requisitos y evidencia

- Mención expresa de derecho(s) ARCO y explicación del trámite.
- Correo oficial de privacidad confirmado, sin completar dominios dudosos.
- Solicitud de INE/identificación oficial **y** comprobante de la línea;
  mencionarlos o pedir uno u otro no acredita ambas solicitudes.
- Desconocimiento del titular y antigüedad de la línea confirmados para validar
  NO CONOCEN A DEUDOR. «Toda la vida» puede acreditar antigüedad cualitativa
  cuando responde a esa pregunta; no se inventa un número de años.

«No la conocemos aquí» se reconoce como declaración plural de desconocimiento.
No se toma una pregunta, una cita o la intervención del gestor como respuesta.
Una identificación contradictoria del titular o familiar impide confirmarla.

La baja del número sin mencionar derechos ARCO nunca satisface el procedimiento.
Si hay indicios positivos de orientación (baja y ambos documentos, o referencia
ARCO con correo confirmado/solicitud de documento), pero falta la mención expresa,
se conserva REVISAR para cotejar audio. No se certifica una omisión acústica ni
se aprueba la llamada. La omisión sin esos indicios y la negación expresa del
trámite conservan PEN_ARCO_OMISION crítico. Las demás reglas siguen vigentes.

## Resultado del lote real y conservación

Se parte del checkpoint final r25 devuelto desde Windows, no del intermedio.

| Resultado | r25 | r26 |
|---|---:|---:|
| APROBADO | 13 | 13 |
| REVISAR | 80 | 80 |
| FALLA_GRAVE | 2 | 2 |
| ERROR técnico | 0 | 0 |

La llamada 21 reconoce desconocimiento, antigüedad cualitativa y ambos documentos.
Conserva REVISAR: no está confirmada la mención expresa de derechos ARCO ni el
dominio dictado. No se reconstruye el correo a partir del valor esperado.
La llamada 12 conserva el correo confirmado en r24 y revisión por procedimiento
incompleto y privacidad pendiente. Su transcripción presenta deformaciones;
no se afirma haberla escuchado. Ninguna de estas dos llamadas se aprueba.

Los 95 puntajes, penalizaciones anteriores, textos, segmentos, cuentas, tarjetas,
22 revisiones de nombre y diez registros ASR permanecen iguales. Solo se añaden
dos indicadores de revisión ARCO de cero puntos, sin retirar bloqueos previos.
El lote anterior de 36 conserva 7 APROBADO, 29 REVISAR, 13 revisiones de nombre
y todas las confirmaciones de importe, saldo y parcialidades.

## Pruebas y límites

- 893 pruebas aprobadas, incluidas 53 del procedimiento, documentos,
  negaciones, atribución, plural de desconocimiento, antigüedad y exportación.
- 268 evaluaciones históricas frente a r25: cero cambios de clasificación,
  cero violaciones de invariantes y cero retiros de penalizaciones sin causa.
- El Excel añade cinco columnas a las 90 previas: mención de derechos, correo,
  INE, comprobante y procedimiento completo. También conserva las columnas
  anteriores en el modo solo audios. Se comprueban las 9.025 celdas del lote
  actual y 3.420 del anterior contra sus JSON recalculados.
- Compilación de aplicación y herramientas con Python 3.10 en Linux.

No se ejecutó Whisper, no se crearon confirmaciones humanas ni se movieron
audios. La reconstrucción/exportación r25 ya fue verificada en Windows con los
archivos devueltos; esta revisión de reglas r26 aún no tiene ejecución nativa
devuelta. No se certifica el cierre de los 13 problemas ni de los 80 REVISAR.
Las dudas de voz de las llamadas 6 y 11 y el recado de la 7 siguen pendientes.

## Uso

Extraer el programa completo y ejecutar `REANALIZAR_CHECKPOINT.bat` dentro de
`proyecto/MRS_Speech_Analytics_v3.6.19_Revision`. Seleccionar el checkpoint final
`Checkpoint_r25_95_Audios.json` que ya se generó en su PC. La consola muestra
`3.6.19-r26` y guarda otro checkpoint y reporte en una carpeta independiente.
No hace falta volver a reconstruir la base, procesar audios ni instalar otro
Whisper/Python. El reanálisis no copia ni renombra físicamente las grabaciones.

Si se necesita reconstruir una base distinta, el lanzador de compatibilidad
`RECONSTRUIR_BASE_R25.bat` sigue disponible; ahora imprime el motor vigente y
nombra el checkpoint según esa revisión. Se conservan la corrección UTF-8 y
la validación de origen de las lecturas. Los datos privados no se incluyen en Git.
