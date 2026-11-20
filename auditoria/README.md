# Auditoría integral de MRS Speech Analytics — 20/nov/2026

La corrección está en el programa: motor compartido, procesamiento normal por lotes, copias, acceso local, dashboard y reportes. No consiste en editar resultados de un checkpoint ni en excepciones por número de llamada.

Base exacta: `feature/usuarios-permisos-r58-20261120`, commit `0ddd54b977c503f6d7f9814a69a409699f9451b9`. Rama de trabajo: `codex/auditoria-integral-r58-20261120`. Revisión del código: `3.6.19-r58-auditoria`.

## Entregables y alcance

- [Auditoría en Excel](AUDITORIA_INTEGRAL.xlsx): 89 criterios de los 13 grupos históricos y controles del sistema; inventario, regresiones nuevas y resultados antes/después.
- [Matriz legible](MATRIZ_ERRORES.md), [CSV](MATRIZ_ERRORES.csv) y [JSON](MATRIZ_ERRORES.json): estado inicial/final, archivo, función, evidencia, regresión y límite por criterio.
- [Inventario completo](INVENTARIO_MODULOS.csv): 165 módulos de `app`, 13 módulos/entradas Python adicionales y 18 BAT. Incluye funciones, líneas, imports, SHA256 y alcance de ejecución.
- [Pruebas y procedencia](PRUEBAS.json), [regresiones antes/después](PRUEBAS_ANTES_DESPUES.csv), [resultados](RESULTADOS_ANTES_DESPUES.json) y [hashes del código](FUENTES_SHA256.json).

De los 89 criterios, 68 cumplen el contrato concreto probado; 18 cambiaron a corregidos durante esta auditoría y 50 ya cumplían ese contrato en la base. Otros 16 están parcialmente corregidos y 5 son no verificables con la evidencia disponible. **CORREGIDO no significa que todos los audios históricos estén acústicamente validados.** La matriz explica cada alcance.

Todos los módulos se inspeccionaron estructuralmente; no todos sus métodos se ejecutaron. El inventario distingue módulos activos, vacíos, legacy y archivos sin ejecución acreditada. La cobertura de líneas es exploratoria y parcial; incluye importaciones y no demuestra cobertura de todas las ramas.

## Causas corregidas

1. El dashboard convertía `NO_APROBADO`, errores y falta de relación Excel en `REVISAR`. Ahora utiliza el catálogo común y ofrece filtros separados.
2. Las salidas del dashboard sustituían el dictamen por bandas de puntaje o discrepancias de estatus. Ahora conservan el resultado guardado, incluida aprobación reetiquetada. Un Analytics antiguo sin dictamen muestra `SIN_DICTAMEN`; 100 puntos solos no generan aprobación.
3. Un fallo de copia sobrescribía incluso `FALLA_GRAVE` con `REVISAR`. Se conserva la evaluación, se muestra el error técnico y se permite reintentar sin exigir ASR nuevo. Los reportes mantienen visible la falta grave.
4. Una copia interrumpida o truncada podía quedar publicada. La copia común verifica SHA256, publica de forma atómica y limpia únicamente su archivo temporal. Las salidas de auditoría tampoco sobrescriben audios distintos con el mismo nombre.
5. El consolidado confundía observaciones sin emisor confirmado con errores comunes y contaba más categorías como aprobadas que el lote. Se separan alertas, descuentos e incumplimientos reportados; se conserva la prioridad crítica y no se reabre una excepción expresamente validada.
6. Un login fallido conservaba la sesión anterior. Se revocan sesión y autoridad al intentar otro acceso; las acciones protegidas vuelven a comprobar permisos, incluso desde ventanas ya abiertas.
7. Una respuesta repetida a una pregunta negativa se convertía en decisión de pago. La repetición/cortesía conserva ambigüedad; una explicación personal explícita sigue siendo evidencia.
8. Un antecedente «me dijeron» ocultaba una nueva instrucción bancaria en la misma oración. Se limita su ámbito hasta la transición explícita a la instrucción actual.
9. La puerta de calidad aceptaba metadatos vacíos con puntaje alto y duraciones no finitas. Ahora bloquea la falta de evaluación; puntajes inválidos producen error de entrada técnica.
10. El índice Excel del dashboard podía interpretar cadenas importadas como fórmulas. Se guardan como texto literal.

Se preservan puntajes y penalizaciones, umbral 80, ARCO, privacidad, mora, comprobantes, lugares de pago, quejas y espera de 65 segundos. Se mantienen usuarios locales, GUI, Whisper, procesamiento por lotes y reportes. Las revisiones alternas continúan reservadas a la administradora.

## Resultados verificados

**3,010 pruebas automatizadas pasan, sin fallos ni omisiones**, sobre el código sellado. Incluyen ventanas Tk en pantallas virtuales. De 38 casos seleccionados de regresión, 33 fallan en r58 de origen y los 38 pasan con la corrección. No se redujeron exigencias para hacerlos pasar: las pruebas antiguas de categorías ahora proporcionan evaluación de calidad y las pruebas de controles abren una sesión de operador sintético.

En el procesamiento normal de **175 audios originales con ASR guardado**, se verificaron copias por SHA256, reportes de calidad y motivos de no pago, integridad de originales y coincidencia de los 175 resultados/puntajes con las reglas compartidas.

| Mismos 175 resultados guardados | Dashboard anterior | Dashboard corregido |
|---|---:|---:|
| Mostrados en REVISAR | 133 | 123 |
| Mostrados como NO_APROBADO | 0 | 10 |
| Aprobadas normales/corregidas/cortas | 32 | 32 |

La anterior salida por bandas mezclaba categorías de calidad. La nueva salida conserva los 175 dictámenes y sus carpetas separadas.

La regresión de **2,327 evaluaciones de seis lotes** no cambia dictámenes ni puntajes: 404 aprobadas, 196 rechazadas, 99 fallas graves, 116 sin relación Excel y 1,512 REVISAR. Cada lote cuenta separado. Estos resultados históricos no son etiquetas humanas de referencia. No se afirma que los 1,512 pendientes estén correctamente dictaminados ni que esta auditoría haya eliminado toda revisión manual.

También se procesaron **dos audios originales con Whisper nuevo en Linux**, sin transcripción recuperada, usando el modelo small local. Ambos quedaron REVISAR con 100 puntos; no se forzó aprobación. Se repitió uno con el runtime Win32 bajo Wine, a través del servicio normal de carga local, con `OMP_NUM_THREADS=1`: generó copias y ambos reportes sin conexión de red. La prueba GUI bajo Wine verificó configuración inicial, administración, operador, lotes, dashboard, pestaña de salidas y reportes.

## Límites expresos

- **No se probó Windows físico**, instalación en un equipo limpio, hardware USB, distintas GPU ni todas las combinaciones de DPI/audio/controladores.
- **No se realizó escucha humana**. ASR y marcas temporales no certifican voz, tono, parentesco, silencio acústico ni fidelidad de todos los importes o referencias.
- No se retranscribieron todos los audios pendientes. Las pruebas reales descritas tienen ese alcance; no son una medición de precisión sobre todo el archivo histórico.
- La primera prueba de ASR Win32 bajo Wine, con hilos por defecto y varias pruebas concurrentes, agotó 240 segundos. La repetición con un hilo pasó. **El rendimiento por defecto en Windows físico permanece sin verificar.**
- El arnés GUI que abre/destruye varias raíces produjo avisos de callbacks Tcl al destruir ventanas; terminó correctamente. No se certifica por ello el ciclo completo de uso físico de Windows.
- Las bajas de usuarios en equipos separados se aplican cuando se importa el catálogo USB actualizado. No existe sincronización por internet ni se pretende proteger el código Python contra un administrador del sistema operativo.
- Las diferencias restantes de ASR, atribución y contexto se mantienen parciales o no verificables. No se convierten en incumplimientos comprobados ni en aprobaciones por cuota.

## Reproducción y entrega

Con el entorno de desarrollo local completo y sin cuentas reales:

```text
python auditoria/ejecutar_pruebas.py --output /ruta/privada/nueva
```

En Linux sin pantalla, añadir `--xvfb /ruta/a/Xvfb`; sin pantalla las pruebas Tk informarán omisión. En Windows se requiere un entorno de pruebas con pantalla. El resultado de esta auditoría utilizó cuatro pantallas virtuales y no dejó pruebas omitidas.

Para regenerar el inventario y el Excel: `python auditoria/generar_matriz.py`. La opción `--coverage` admite un JSON de coverage para añadir alcance de líneas ejecutadas. Estos scripts no abren audios ni Excel de clientes.

El ZIP adjunto contiene **código fuente auditado, pruebas y auditoría**. Requiere el Python, dependencias y modelo local correspondientes para ejecutar la aplicación; no es un instalador nuevo ni un EXE. No incluye modelos, audios, checkpoints, Excel de clientes, catálogos de usuarios, claves ni contraseñas reales. Los datos reales de validación permanecen fuera de Git y del ZIP.
