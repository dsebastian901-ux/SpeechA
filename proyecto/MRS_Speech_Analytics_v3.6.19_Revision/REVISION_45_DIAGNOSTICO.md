# r45 — evaluación integral, etiquetas corregidas y acciones para el gestor

## Qué cambia

La clasificación usa una decisión común para procesamiento nuevo, reanálisis y exportación, con evidencia y resultados separados para los trece grupos. Una deducción de puntos, una duda y una falla grave conservan tratamientos distintos. No se aplica una cuota de aprobaciones.

La conversación comprobada determina el procedimiento aplicable: una etiqueta de convenio no impone obligaciones de convenio a un recado real; una etiqueta de NO CONOCEN no impone ARCO a un titular identificado. El Excel conserva su función de fuente de datos de la cuenta y se compara después con el estatus detectado. No se toma el estatus de Excel como prueba de identidad.

Se revisan identidad contextual, aceptación de recados, desconocimiento del titular, privacidad, tarjeta, ARCO completo, lugares autorizados, amenazas, expresiones ofensivas hasta el cierre, hostilidad, denuncias de atención previa y esperas de 65 segundos. Las dudas de voz o datos conservan REVISAR. Decir saldo pendiente sin cantidad no prueba divulgación; un importe protegido revelado por el gestor a un tercero conserva su bloqueo. Recibir del tercero un reporte de pago no equivale a divulgarlo.

Se distingue una oferta de un compromiso aceptado y de un pago anterior reportado. Las negativas condicionales o sobre intereses, compras o una cantidad no se convierten en negativa total. Se descartan instrucciones futuras como prueba de pago anterior. Las frases sobre anotar un teléfono o que un pago aún no se refleja no definen por sí solas un estatus de pago. Las quejas de llamadas anteriores permanecen bloqueadas, sin atribuir automáticamente culpa al gestor actual.

Se corrige el cálculo de planes explícitos de dos y tres pagos, incluido un último importe diferente; no se suman cifras sueltas de alternativas, teléfonos o referencias. Se conservan las restricciones de mora, corte, vencimiento y la prohibición de liquidación/cancelación en 1–3 PV confirmada por la usuaria. La omisión de dos lugares resta 20 puntos y puede permitir aprobar con 80 si cumple todos los demás filtros.

## Catálogo confirmado

| Estatus | Código |
| --- | --- |
| MENSAJE CON TERCERO | 3EROS |
| MENSAJE CON FAMILIAR | 3EROS |
| MENSAJE EN TRABAJO | 3EROS |
| RECADO REF1 | 3EROS |
| ACLARACION | ACLARA |
| NO CONOCEN A DEUDOR | NC |
| NEGATIVA DE PAGO | NP |
| CONVENIO | PP |
| NO DEFINE FECHA DE PAGO | TH |

RECADO REF2 se admite al leer datos históricos; no se genera como nuevo estatus. Un catálogo con estatus deshabilitados no se vuelve a autorizar desde las filas del Excel.

## Copias con etiqueta corregida

Si alcanza el mínimo y cumple todos los filtros, y existe evidencia alta de otro estatus válido, se clasifica APROBADO_ETIQUETA_CORREGIDA. En TARJETA_1PV_352_TH_GESTOR_MRS_FECHA cambia únicamente el cuarto componente, índice 3, correspondiente a TH/PP/NP/3EROS/ACLARA/NC. Los demás componentes se preservan. La tarjeta de numero_de_tarjeta prevalece sobre el identificador numérico de nombre_final, según autorización previa, y esa normalización se audita por separado.

La copia se guarda en APROBADOS_ETIQUETA_CORREGIDA. No se modifica el Excel ni el audio original. No se copia como aprobada una llamada con otra duda o falla de seguridad. Si dos llamadas producen el mismo nombre, se conservan los nombres completos usando subcarpetas de duplicados. Una fuente ausente, ambigua o modificada interrumpe la copia y no se registra como completa.

## Reporte final para corrección por el gestor

CUENTAS_REETIQUETADAS incluye cuenta/tarjeta como texto, archivo, gestor, supervisor, fecha, estatus y código anteriores y correctos, nombres anterior y nuevo, puntaje, motivo/evidencia y acción para el gestor. Distingue ETIQUETA CALCULADA; COPIA PENDIENTE de COPIA GENERADA, con ruta cuando se realizó. El programa no escribe automáticamente sobre el Excel de cuentas.

RESUMEN_REETIQUETADO agrupa por gestor, supervisor y cambio de estatus; muestra llamadas y cuentas distintas. EVALUACION_13_REGLAS y RESUMEN_13_REGLAS muestran todos los grupos y sus hallazgos. Se conserva el reporte adicional de motivos de no pago al finalizar el lote.

## Cómo aplicar a un checkpoint existente

1. Extraiga TODO el ZIP en una carpeta nueva.
2. Ejecute REANALIZAR_Y_CORREGIR_ETIQUETAS.bat, disponible también dentro de proyecto/MRS_Speech_Analytics_v3.6.19_Revision.
3. Seleccione el último checkpoint completo que incluya sus confirmaciones.
4. Cuando lo solicite, seleccione la carpeta de los audios originales.
5. Espere el cierre: se generan checkpoint nuevo, reporte de calidad con las hojas anteriores, motivos de no pago y copias corregidas en otra carpeta. La consola muestra las rutas.

No requiere retranscribir ni descargar otro Whisper. El reanálisis usa las transcripciones y validaciones guardadas. REANALIZAR_CHECKPOINT.bat conserva la opción de generar reportes sin copiar audios; esas etiquetas se muestran pendientes de copia. En lotes nuevos, la clasificación y copia se integran al flujo habitual.

## Validación y alcance

2,108 pruebas correctas, 7 gráficas omitidas, cero fallos; preparación futura con 2,128 correctas y 7 omitidas. Se comprobaron 2,317 evaluaciones en cinco salidas, correspondientes a 1,210 nombres de audio únicos. Las dos salidas de 100 incluyen la comparación con el archivo original recibido; no representan 200 audios distintos.

Resultado de las 100 recibidas: {'APROBADO': 20, 'REVISAR': 59, 'NO_APROBADO_MENOR_80': 14, 'APROBADO_ETIQUETA_CORREGIDA': 4, 'FALLA_GRAVE': 3}. Se verificaron transcripciones originales, datos de cuenta, confirmaciones, invariantes de seguridad, celdas de Excel, totales de motivos y listados de reetiquetado. Tras el último filtro de salida de etiquetas se repitió la decisión común en todas las evaluaciones, comprobando que los módulos de extracción no cambiaron por hash; las decisiones afectadas se reanalizaron completamente. También se copiaron 4 audios reales y se compararon sus hashes con los originales. Los reportes reales son privados y no van en este ZIP.

Las revisiones que persisten requieren resolver evidencia ambigua o incumplimientos; no se declaran todas corregidas. No se realizó escucha humana ni se sustituyeron transcripciones. Pruebas en Linux/Python 3.10, sin certificación nativa Windows. Este paquete completo de código conserva las funciones del piloto; el instalador final con usuarios, permisos e icono continúa como trabajo separado.
