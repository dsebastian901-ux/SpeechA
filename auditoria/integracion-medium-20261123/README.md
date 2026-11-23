# Auditoría e integración de Whisper Medium — antes de compilar

**Actualización del 23/11:** el [cierre individual de los 34 fallos](cierre-34/README.md) corrige 20 y conserva 14 abiertos; suite actual: 3208 pasan, 14 fallan y 2 omitidos. El documento siguiente y sus CSV se conservan como línea base de la intervención anterior (`14cd432`); no describen el estado final del cierre.

**Estado: NO LISTO PARA COMPILAR.** Esta entrega contiene código y evidencia de mejoras comprobadas; conserva fallos abiertos y no se presenta como una versión terminada de producción.

## Base y alcance

Se actualizaron las referencias remotas. La rama funcional más reciente fue `fix/dictaminacion-excepciones-prioridad-20261121`, commit `cddfd0fc33839a1cec8be34119d7c7460dd1ee86`. Contiene la auditoría/permisos r58 y 72 commits posteriores. Se creó `codex/integracion-medium-dictaminacion-20261123` desde esa base, en un worktree separado. No había cambios pendientes al iniciar. No se reemplazó la base por R57 ni por un ZIP histórico.

La revisión identificó rutas productivas de Whisper, modelos locales/caché, ajustes, lotes, dictaminación, permisos, GUI y reportes, y el inventario estructural de 293 archivos Python. Un archivo inventariado no equivale a todas sus ramas probadas; los módulos vacíos no se certifican como motores activos. La matriz de decisiones del 21/nov se conserva como contexto; no se declaran implementados sus 160 criterios ni se alteran reglas para obtener una cuota de aprobaciones.

## Resultados comprobados

| Ejecución | Casos | Pasan | Fallan | Omitidos |
|---|---:|---:|---:|---:|
| Base, antes de editar código | 3172 | 3114 | 58 | 0 |
| Código de integración final | 3206 | 3170 | 34 | 2 |

- 24 pruebas existentes que fallaban pasan ahora. Ninguna de las 3114 pruebas que pasaban al inicio dejó de pasar. **No se modificaron las pruebas antiguas.**
- 32 pruebas automáticas nuevas pasan. Otras dos pruebas nuevas de GUI se omiten en Linux por incompatibilidad verificable de Python 3.10/Menu con Tcl/Tk 9.0.4. Sus dos flujos se probaron adicionalmente con el runtime Windows y Tk 8.6.15 bajo Wine: importación de Medium seleccionada y autorización que expira en el diálogo. No se cambió la aplicación para disimular la incompatibilidad del entorno.
- 17 casos dirigidos se ejecutaron también contra la base: 9 fallaban y 8 pasaban; sus equivalentes pasan con la integración. No se contabiliza como prueba fallida anterior una API que simplemente no existía.
- La suite final verificó que el código y las pruebas no cambiaron durante su ejecución. El manifiesto `FUENTES_PROBADAS_SHA256.json` permite contrastar los archivos comprobados.

## Cambios implementados

El detalle de funciones, líneas y pruebas está en [MATRIZ_CAMBIOS.md](MATRIZ_CAMBIOS.md).

1. Importación offline de modelos CT2 mediante carpeta/USB, disponible en Ajustes para usuarios con permiso `settings`. Valida arquitectura, archivos, copia SHA-256 y carga real del backend antes de publicar. No reemplaza modelos existentes ni modifica la selección guardada hasta pulsar Guardar. Una sesión expirada impide publicar el modelo.
2. Se exige que Medium tenga arquitectura de 24 capas de encoder, 24 de decoder y estado 1024. No se renombra Small para simular Medium. La importación admite el formato binario CT2 v6; ONNX y `.pt` no son paquetes directamente importables por Faster-Whisper.
3. Se conserva el objeto de modelo y su procedencia durante toda la transcripción, reintento VAD y recuperación. Una relectura de contexto resuelve el modelo de la primaria si el cargado cambió. Las transcripciones antiguas sin modelo conocido no se reutilizan para acreditar Medium; la compatibilidad anterior de Small permanece.
4. SIN VOZ ya puede recibir un ASR realmente vacío con duración positiva; una inconsistencia con segmentos hablados se separa como error técnico. SIN VOZ no puede eclipsar evidencia crítica independiente confirmada.
5. Se distinguen teléfono omitido de teléfono ofrecido pero no corroborado, recepción del mensaje de posibilidad de retransmitir y calidad de un convenio declarado de acreditación de su estatus final.
6. Se restauró la aplicabilidad de descuentos existentes por etapas incompletas. Los valores de las penalizaciones, umbral y controles independientes no se rebajaron. Excel solo no crea evidencia de identidad, aceptación ni una gestión inexistente.

## Pruebas con Whisper y alcance del modelo Medium

Se usaron las mismas dos grabaciones disponibles con Small y Medium local, desde la ruta normal de lotes con ASR nuevo, sin conexiones de red, verificando copias SHA-256, originales y reportes de calidad/motivos de no pago. Durante esa comparación Small dejó ambas en REVISAR con 100/100; Medium dejó ambas en REVISAR con 100/80. En una ejecución posterior de una de las grabaciones, ambas configuraciones volvieron a pasar por el backend real. Las ejecuciones con audio son pruebas de funcionamiento durante la integración; la suite final comprueba los cambios posteriores de código. No constituyen escucha humana ni una estimación de precisión del lote completo.

**Los pesos Medium disponibles no se entregan ni se consideran validados para producción.** Existía un paquete público ONNX int8 de Medium, no un paquete CT2 oficial completo. Se preparó una conversión experimental privada para comprobar carga y ejecución. La comparación numérica con ONNX obtuvo error RMS relativo 0.253, superior al límite fijado de 0.1, aunque coincidió el primer token. Esa prueba FALLÓ. No se amplió el umbral ni se declaró equivalencia de pesos. La comparación de palabras/dictámenes con esos pesos no demuestra mejora de precisión. Falta un paquete Medium CT2 verificable y validación acústica antes de adoptarlo en producción.

Los tiempos y resultados exactos de estas muestras están en `PRUEBAS.json`; no son un benchmark de Windows físico. El modelo predeterminado no se cambió a Medium, y se mantienen Small y las demás opciones.

## Pendientes que impiden compilar

`FALLOS_PENDIENTES.csv` contiene los 34 casos que siguen fallando, con archivo, función e identificador de caso. Ninguno se declara corregido. Hay diferencias con criterios operativos posteriores y fallos de validación que requieren cierre; no se omiten ni se reescriben sus expectativas para obtener una suite verde.

- Conciliar los escenarios históricos de rechazo de recado, omisión del teléfono y seguimiento de pago con los criterios 14, 58/146 y 72, manteniendo separadas calidad, estatus y alertas. No asumir que todas las fallas son pruebas obsoletas: permanecen abiertas hasta comprobar su causa por caso.
- Cerrar validaciones de planes/importe y correcciones humanas persistentes, límites de mora y contrato de evidencia entre dictaminador y herramientas de regresión. Los casos exactos siguen en el CSV.
- Validar un paquete Medium CT2 de producción y su comparación con audio de referencia. No se ha certificado reducción de REVISAR, mejor precisión ni identificación de voces por usar Medium.
- Validar Windows físico, ciclo de ventanas y traslado USB físico. Wine no sustituye esa prueba. Sigue sin haber escucha humana en esta auditoría.

No se compilaron instalador ni EXE. No se subieron modelos, audios, checkpoints, Excel de clientes, credenciales ni catálogos reales. Los usuarios/permisos locales, reportes, GUI y métodos existentes se conservaron; este informe no los declara exhaustivamente validados en cada plataforma.

## Reproducción

Con las dependencias de desarrollo instaladas, ejecutar desde la raíz:

```text
python auditoria/ejecutar_pruebas.py --output <directorio-privado-nuevo>
```

En Linux sin pantalla, añadir `--xvfb <ruta-a-Xvfb>`. Con Python 3.10 y Tcl/Tk 9 se informan las dos omisiones de GUI descritas. La suite completa todavía devuelve un código de error por los fallos abiertos; no es evidencia de una versión apta para compilar.

`RESULTADOS_POR_CASO.csv` incluye los 3206 resultados, `FALLOS_RESUELTOS.csv` las 24 regresiones existentes resueltas, y `PRUEBAS.json` las métricas y límites. Los parámetros de los casos se identifican mediante hash para evitar publicar textos o datos innecesarios.

El identificador de cada caso es `SHA256(classname + '::' + name)[:12]` a partir del XML de pytest. Los parámetros no se eliminan al calcular el identificador; solo se evita publicarlos en el CSV.
