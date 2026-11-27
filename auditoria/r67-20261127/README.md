# r67: negociación cronológica y ciclo de escuchas

Base independiente: `codex/consolidacion-r66-20261126`, commit `13684a3406012a0cea9158b6bb6b7ecc7aba35dd`.
R66 permanece en su rama y carpeta. Esta revisión no contiene MRS Academy ni EXE.

## Cambios funcionales

- Respuestas actuales de fecha e importe, también en orden fecha→importe, forman un único cierre financiero. La última decisión firme reemplaza una condición anterior; una revocación posterior mantiene su efecto. No unir datos a través de preguntas de otro objeto o una transferencia de área.
- La elección incierta de transferencia/aplicación se distingue de la aceptación del pago. Los controles sobre el destino autorizado continúan independientes.
- Parcialidades: cantidad de pagos × importe unitario, calendario explícito y respuesta de aceptación. No completar días, elevar importes al mínimo ni redondear diferencias financieras.
- El plan de Medium prioriza preguntas, respuestas y cierre vigente. Conserva la localización explícita de una respuesta ininteligible. Elimina intervalos contenidos y agrupa solapamientos compatibles del mismo objetivo.
- Tercera escucha: `NO_REQUERIDA`, `PENDIENTE`, `FALLIDA`, `INSUFICIENTE`, `CONTRADICTORIA`, `EJECUTADA`. Ejecución y suficiencia son campos distintos. Los estados insuficiente, contradictorio y fallido conservan los bloqueos correspondientes; no generan aprobación automática.
- Una diferencia léxica no exige otra inferencia. Diferencias entre hechos sí la exigen; una contradicción no desaparece por dos votos contra uno. La discrepancia de hechos con el ASR original también bloquea el consumo favorable.
- Los hechos corroborados pasan por las validaciones de negociación, monto, calendario, trato y privacidad antes del dictamen. La transcripción original no se reescribe.
- Petición contextual de comprobante y recepción del recado son hechos locales separados del teléfono. No atribuyen acústicamente una voz ni inventan dígitos.
- Explicación del trámite de cancelación se distingue de una oferta de liquidación. Se conservan las restricciones financieras de liquidación, regularización y mensualidad.
- Instancia Medium separada del modelo principal, caché de decodificaciones idénticas dentro del mismo audio, y trazabilidad de carga/reutilización, decodificación, espera por bloqueo e inferencia. CPU de proceso y tiempo de pared se registran separadamente; CPU incluye actividad del proceso completo.

## Evidencias

`PRUEBAS.json` recoge resultados y huellas de los informes de ejecución. `MATRIZ_FUNCIONAL.csv` relaciona los 12 requisitos con código, pruebas y límites. `COMPARATIVO_CONTROLADO.json` compara las mismas entradas anonimizadas en r66 y r67; sus lectores controlados **no son inferencia real**. `CHECKPOINT_23.json` y `COMPARATIVO_23.csv` contienen únicamente cifras y códigos anónimos. Los originales, audios, transcripciones completas, Excel de clientes y credenciales no se incorporan al repositorio.

## Límite operativo

El checkpoint y Excel del 27/nov contienen las 23 llamadas y las lecturas Medium ya registradas. Los 23 archivos de audio originales no están en este entorno. El reanálisis conserva el requisito de vincular cada prueba favorable al audio original; no sustituye ese control con un archivo ficticio ni declara una nueva escucha inexistente. La corrección del programa y su regresión automatizada no equivalen a aprobar las 23 llamadas.

La inferencia local real utiliza un recorte histórico de 8 segundos distinto de este lote. Verifica ejecución, reutilización del modelo, integridad del original y generación de reportes; no valida dictámenes de llamadas completas ni voces mediante escucha humana.

No se probó Windows físico ni se realizó escucha humana. Los criterios sin evidencia acústica suficiente permanecen sujetos a esos límites.

## Resultado comprobado

Suite final: 3600 correctas, 0 fallidas, 22 omitidas. Regresión focalizada: 200 correctas. Las omisiones requieren pantalla Tk o CMD de Windows. Se ejecutaron 50 casos nuevos.

En el lote real: 23 REVISAR antes y después con los recursos disponibles, 0 aprobaciones nuevas certificadas; C22 recupera CONVENIO y reconoce la solicitud del comprobante, con 80 puntos y bloqueo independiente por destino de transferencia. Los 23 originales faltan para cotejar sus huellas y realizar nuevas escuchas.

Plan final: 148 grupos frente a 173; 296 peticiones iniciales planificadas. En las parejas de lecturas históricas, 50 recomiendan tercera. No se ejecutó este nuevo plan sobre los audios ausentes ni se ofrece un tiempo estimado como medición real.

El intento anómalo de C19 duró 20006.816 s para una ventana de 15 s. La telemetría anterior no permite distinguir inferencia, bloqueo o suspensión; véase TIEMPO_ANOMALO.json.
