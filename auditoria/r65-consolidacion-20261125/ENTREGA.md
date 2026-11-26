# Entrega r65 para validación · 25/nov/2026

Código productivo consolidado en `codex/consolidacion-r65-20261125`, a partir de `488bfe1`. La rama operativa se conserva. Versión `3.6.19-r65-consolidacion-20261125-validacion`.

## Resultado reproducido sobre las mismas 79 llamadas

| Resultado | r64 | r65 |
|---|---:|---:|
| Aprobadas (incluye etiqueta corregida) | 18 | 25 |
| REVISAR | 30 | 26 |
| FALLA_MINIMA | 6 | 6 |
| NO_APROBADO | 4 | 1 |
| NO_APROBADO_MENOR_80 | 2 | 2 |
| SIN_RELACION_EXCEL | 19 | 19 |

De las 30 iniciales se resuelven **8**: C004/C035/C050/C051 aprobadas, C059/C075 aprobadas con etiqueta corregida, C005 falta mínima confirmada y C055 rechazo por plan completo bajo el mínimo, con alerta de espera visible. Permanecen 22. Las cuatro denuncias previas C001/C008/C028/C077 vuelven a revisión por la última instrucción expresa; se informan separadas y no se cuentan como correcciones favorables. C002, fuera de las 30, pasa de falta mínima a aprobación de 80 por acuerdo actual completo; ahora se aplica el descuento real de 20 por lugares de pago.

Las 18 aprobadas anteriores siguen aprobadas. Las 25 aprobadas nuevas no tienen hallazgos REVIEW, PENDING_ALERT ni CRITICAL en la decisión, y alcanzan el umbral. Esto comprueba coherencia con la evidencia guardada, no sustituye la validación acústica.

La matriz privada documenta **104 hallazgos** originales, incluidos descuentos, sus metadatos íntegros, texto, marcas ASR y todos los bloqueos nuevos/restantes. El Excel comparativo contiene las 79 filas, las 30 iniciales, evidencias, segmentos y recursos faltantes. El reporte principal y el de motivos de no pago fueron generados por el producto. El reporte principal tiene 79 resultados, 13 reglas por cada llamada y 146 ventanas de segunda escucha marcadas sin ejecución.

## Pruebas ejecutadas

- Base `488bfe1`: **3400 aprobadas, 0 fallos, 0 errores, 22 omitidas**.
- Código final: **3459 aprobadas, 0 fallos, 0 errores, 22 omitidas**, 535.15 segundos. Incluye procesamiento normal de lotes, actualización de resultados guardados, usuarios/permisos, finanzas, privacidad y reportes.
- Regresión focalizada final: **244 aprobadas**. Dobles de ASR se identifican como tales en las pruebas.
- Inferencia Medium real: recorte histórico de 8 segundos ajeno a las 79; tres decodificaciones no vacías, cero errores, arquitectura 24/24 capas y 1024 dimensiones. Modelo primario preservado. Registro privado con hashes.
- Flujo normal real `BatchService`, con ese recorte histórico y rutas locales de modelo aisladas: ASR Small real, revisión Medium real sin dobles de salida, checkpoint, copia de audio cotejada por hash, Excel principal y motivos de no pago. Es una prueba de integración con 8 segundos de audio, no una evaluación de calidad de una llamada completa ni del lote de 79. La configuración de esta prueba se aisló dentro del proceso; no se persistió en la aplicación.
- `compileall app tools` y comprobación de diferencias respetando CRLF: salida 0.
- 780 archivos protegidos R57 y 21 de código r64 sin cambios; 33 llamadas/argumentos de penalización idénticos a la base. Fuentes Python finales coinciden con SHA256_CODIGO.json después de probar.
- Las 79 transcripciones originales, relaciones y lecturas adicionales se conservaron. Cambios de puntaje: C002 100→80 por nueva obligación de convenio; C036 50→100 informativo, sigue SIN_RELACION_EXCEL y no se valida financieramente sin su relación original y cotejo del acuerdo.

Los ajustes de expectativas históricas se limitan a la nueva política explícita de quejas previas y al identificador de versión; están enumerados en CAMBIOS_EXPECTATIVAS.json. No se cambiaron expectativas financieras para pasar pruebas.

## Pendientes reales

**No se ejecutó Medium para ninguna de las 79 llamadas.** Ninguno de sus audios originales está accesible aquí; se comprobaron inventario, aliases y contenedores disponibles. El reanálisis registra 43 localizaciones de audio fallidas en llamadas que solicitaron recuperación, no 43 escuchas. Las 146 ventanas del reporte son un plan, no escuchas ejecutadas. El archivo privado RECURSOS_FALTANTES_79.json identifica los 79 nombres/rutas originales y las 19 relaciones Excel ausentes.

Las 22 revisiones iniciales restantes incluyen atribución de emisor en privacidad, advertencias o confrontación; números y términos discordantes del plan; referencias incompletas; recepción del mensaje; instrucciones bancarias elegidas; y segmentos largos con pocas palabras ASR. La matriz separa cada bloqueo y su fragmento. La queja anterior conserva revisión por política incluso si el texto es claro.

No se dispone del checkpoint r63 de 34 REVISAR con las mismas 79 llamadas. No se efectuaron escucha humana, prueba física de Windows ni compilación EXE. Las 22 pruebas omitidas corresponden a pantalla Tk/Windows CMD; el detalle exacto figura en PRUEBAS.json. Esta es una entrega para validación, **no una declaración de disponibilidad para producción**.

## Reproducir

Desde `proyecto/MRS_Speech_Analytics_v3.6.19_Revision`, con las dependencias de desarrollo locales:

```powershell
python -m pytest -q --junitxml=resultado_pruebas_r65.xml
python -m compileall -q app tools
```

Para verificar el lote desde Windows, conservar el proyecto original y usar las herramientas de reanálisis autorizadas para administración, seleccionando una carpeta nueva. `tools/reanalyze_checkpoint.py` admite `--review-model medium`, con autenticación local intacta; requiere audios y Medium local para inferencia real. Si se crea un proyecto nuevo, se utiliza el mismo motor productivo corregido; el resultado acústico puede variar por la nueva transcripción y no está certificado en ausencia de esos audios.

Los artefactos con información de llamadas se entregan de forma privada; ninguno se incorpora al commit. El ZIP de código no contiene cuentas de usuario, contraseñas, modelos ni datos de clientes. La instalación existente conserva sus datos locales.
