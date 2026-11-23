# Cierre comprobable de los 34 fallos

**Estado: 20 regresiones corregidas; 14 fallos abiertos. No apto para compilar.**

Rama: `codex/integracion-medium-dictaminacion-20261123`. Base de esta intervención: `14cd4321186a05cae98ab17e6fb29260070989df`. Se mantuvo la rama solicitada y se preservó el CSV original de fallos como línea base.

Se leyeron `AGENTS.md`, `DECISIONES_OPERATIVAS_20261115.md` y los tres documentos de criterios operativos del 21/11. Cada uno de los 34 identificadores se ejecutó en un proceso pytest separado antes y después. No se cambiaron expectativas, archivos ni parámetros de las 112 pruebas existentes. Se añadieron 18 contrastes nuevos.

## Resultado

| Ejecución | Casos | Pasan | Fallan | Omitidos |
|---|---:|---:|---:|---:|
| 34 casos individuales, base | 34 | 0 | 34 | 0 |
| 34 casos individuales, código entregado | 34 | 20 | 14 | 0 |
| Reproducción con el ejecutor incluido | 34 | 20 | 14 | 0 |
| Focal final: pagos, planes, revisiones e importación | 219 | 217 | 0 | 2 |
| Suite completa de la base de esta intervención | 3206 | 3170 | 34 | 2 |
| Suite completa del código entregado | 3224 | 3208 | 14 | 2 |

**Cero regresiones entre las 3170 pruebas que pasaban en la base.** Los 18 casos nuevos pasan. La suite final verificó que las fuentes no cambiaron durante su ejecución. Los 14 fallos de la suite coinciden exactamente con los individuales pendientes; no hay errores de ejecución ni fallos nuevos fuera de esos identificadores.

Las dos omisiones de la ejecución focal corresponden a ventanas Tk sin pantalla; esas pruebas sí pasan en la suite completa con Xvfb. Las dos omisiones de la suite completa son los diálogos de importación Medium de la intervención anterior: incompatibilidad Python 3.10/Menu con Tcl/Tk 9 en Linux. No son las mismas dos pruebas. No se declara validación nueva de Windows físico ni escucha humana.

## Causas corregidas en producción

- **Pagos y dictaminación:** se resolvía el estatus antes de validar el plan financiero y sus confirmaciones. Ahora se decide una vez, con los hechos validados y la ventana de mora aplicable. La aceptación explícita del plan completo remite a sus términos anteriores sin completar cifras desde Excel.
- **Pagos:** compromiso e importe usaban extractores inconsistentes. Se vincula una oferta monetaria explícita con aceptación propia inmediata o con una explicación intermedia del mismo pago. Se excluyen negaciones, citas, historia, comprobantes, otros objetos y cambios de términos. Los nuevos contrastes incluyen estos negativos.
- **Recados:** dos detectores diferentes permitían tratar un teléfono ofrecido pero truncado en ASR como una omisión acreditada de -15. Se comparte la evidencia de entrega incierta; no se reconstruyen dígitos por ecos. La omisión confirmada sigue descontando 15 y puede aprobar con al menos 80 conforme a 58/146.
- **Recados y revisiones:** una confirmación humana de entrega no debe anular una revocación final del destinatario. Se conserva el registro humano, su alcance y la contradicción. Se reconocen rechazos elípticos del objeto recado sin extenderlos a pagos, paquetes o preguntas.
- **Checkpoints:** el fallo de los casos de importación y persistencia se originaba en la resolución financiera posterior, no en el emparejamiento por nombre. Las pruebas completas comprueban integridad de fuentes, contexto, rutas, revocación e idempotencia tras corregir el motor común.
- **Reportes y herramienta de regresión:** se conserva el identificador público del método de convenio y se documenta la aceptación del importe por separado. El validador admite el seguimiento del criterio 72 sin inventar una promesa futura, exigiendo mínimo y controles independientes.

No se alteraron valores de penalizaciones, umbral, catálogo autorizado, autenticación, roles, modelos, GUI ni rutas de exportación. Las correcciones de evidencia sí pueden cambiar la aplicabilidad de un descuento. La suite incluye pruebas de esos controles; no certifica todos los flujos posibles ni la precisión acústica de un lote de clientes.

## Los 14 fallos que siguen bloqueando

No se consideran corregidos ni se ocultan mediante cambios en pruebas:

| Causa | Casos | Qué impide cerrarlos |
|---|---:|---|
| Rechazo del tercero frente a calidad del gestor | 6 | Las expectativas históricas imponen NO_APROBADO por la negativa del tercero. La implementación vigente separa ese estatus de una falta del gestor; 14 no fija una penalización y 50 prohíbe inventar código. Los fixtures conservan discrepancias y, en variantes, alertas. Hace falta conciliar el contrato de calidad/destino, sin fabricar incumplimientos. |
| Seguimiento, aclaración y catálogo | 5 | Se espera ACLARACION, procedencia de octubre o el estatus compuesto no autorizado PAGO REPORTADO / ACLARACION. El criterio 72 prescribe CONVENIO para seguimiento con comprobante. Un caso ya es APROBADO y otro APROBADO_ETIQUETA_CORREGIDA; su fallo no significa exceso de REVISAR. |
| Fecha fuera de mora | 2 | Los escenarios esperan CONVENIO a cuatro días en 1PV con plazo de tres. El criterio 65 lleva a NEGATIVA por política; el programa conserva la aceptación y la causa real. |
| Aceptación del importe no probada | 1 | El titular anuncia el depósito antes de que se diga la cifra; no hay aceptación posterior del importe. Los dos lugares se reconocen correctamente. Sin más contexto o audio no procede forzar APROBADO. |

El detalle de cada identificador, archivo, función, causa, cambio, criterio y resultado está en **[CASOS.md](CASOS.md)** y **[RESULTADOS_34.csv](RESULTADOS_34.csv)**. [RESULTADOS_34.json](RESULTADOS_34.json) añade ubicaciones del código y hashes de la evidencia individual. Una prueba que falla en su primera aserción no certifica las aserciones posteriores; el informe lo distingue.

No se afirma que estos 13 conflictos sean automáticamente pruebas obsoletas: quedan abiertos hasta conciliar su contrato. Tampoco se autoriza aprobar llamadas con privacidad o conducta crítica pendientes para disminuir REVISAR.

## Evidencia y reproducción

- [PRUEBAS.json](PRUEBAS.json): conteos, grupos, controles, límites y hashes de los XML privados.
- [SUITE_ANTES_DESPUES.csv](SUITE_ANTES_DESPUES.csv): los 3224 resultados por identificador, incluidos los fallos y omisiones.
- [FUENTES_PROBADAS_SHA256.json](FUENTES_PROBADAS_SHA256.json): fuentes exactas de aplicación, herramientas y pruebas comprobadas.
- [PRUEBAS_EXISTENTES_SHA256.json](PRUEBAS_EXISTENTES_SHA256.json): 112 archivos de pruebas anteriores sin cambios.

Desde la raíz, con las dependencias de desarrollo instaladas:

```text
python auditoria/integracion-medium-20261123/cierre-34/reproducir_34.py --output <directorio-privado-nuevo-fuera-del-repositorio>
python auditoria/ejecutar_pruebas.py --output <otro-directorio-privado-nuevo>
```

El primer comando localiza los parámetros exactos mediante el hash de pytest y ejecuta un caso por proceso; no sustituye parámetros parecidos. Admite `--python` y `--source` para comparar otra copia de la aplicación. El segundo ejecuta toda la suite; en Linux sin pantalla añadir `--xvfb <ruta-a-Xvfb>`. Ambos devuelven error mientras haya fallos, aunque el resto pase. Los registros detallados permanecen fuera de Git y pueden contener datos de las pruebas.

Se verificaron 780 hashes de los dos árboles protegidos de referencia R57: cero modificaciones. El worktree de la auditoría r58 permaneció limpio. No se publicaron audios, checkpoints, Excel de clientes, credenciales, modelos ni registros privados.

**No se compiló EXE y Medium experimental no se activó.** La configuración productiva de Whisper y los límites de validación del modelo documentados en la intervención anterior se conservan. Las pruebas con lotes de este cierre usan fixtures sintéticos; no se ejecutó nuevo ASR real ni se realizó escucha humana.
