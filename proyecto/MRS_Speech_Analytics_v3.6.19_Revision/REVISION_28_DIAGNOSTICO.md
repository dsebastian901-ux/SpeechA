# Revisión 28: alias de mora y recuperación del dato de cuenta

La devolución nativa r27 se verificó frente a la entrega comprobada. Coinciden
los 103 resultados, cuentas, clasificaciones, puntajes y metadatos de evaluación.
Las 31 revisiones de nombre solo difieren en la fecha de generación esperada.
Las 9.785 celdas del Excel coinciden con el checkpoint: 11 APROBADO, 86 REVISAR
y 6 FALLA_GRAVE. Esto acredita el reanálisis/exportación r27 en el equipo del
usuario, sin certificar escucha de audio ni todo el procesamiento nuevo.

## Causa reproducida

El Excel recibido tiene 1.053 registros de cuentas y usa `mora` como encabezado.
El lector solo buscaba `asignacion`; por eso guardó ese campo vacío en las 103
llamadas aunque la información estaba presente. El problema afecta a la carga
del dato, no implica que el usuario haya omitido las moras en su Excel.

## Corrección

- El lector acepta `mora` y el encabezado anterior `asignacion`, incluidas sus
  variantes de mayúsculas y acentos. No confunde `fecha_asignacion` con mora.
- Si existen ambas columnas, usa el valor no vacío o conserva la asignación
  equivalente. Una contradicción se informa como error de fila; los encabezados
  de mora duplicados se rechazan. No se selecciona silenciosamente otro dato.
- La recuperación de checkpoints completa solo la mora que falta. Cruza por
  archivo exacto, tarjeta de 16 dígitos y datos de cuenta existentes. Conserva
  nombres previamente corregidos y exige su registro de autorización cuando
  difieren del Excel. No traslada moras de una cuenta distinta.
- Una mora existente se conserva si coincide; una contradicción se detiene antes
  de crear salidas. No se infiere mora del nombre del audio ni se actualizan
  saldos, fechas, montos o nombres desde una hoja diferente.
- Cada dato incorporado registra archivo de origen, hash del Excel, hoja,
  valor anterior y valor importado, sin crear confirmaciones humanas de audio.
  Los registros de evidencia anteriores se conservan; una lectura ASR vinculada
  al contexto anterior no se vuelve a validar silenciosamente al cambiarlo.

## Resultado sobre el lote recibido

Se recuperan las 103 moras: 47 de mora 1, 13 de mora 2, 15 de mora 3 y 28 de
las moras de liquidación restantes. Las reglas existentes reciben ahora 75
cuentas con política de corte/vencimiento y 28 con plazo del mes de la llamada.

El resultado calculado permanece en 11 APROBADO, 86 REVISAR y 6 FALLA_GRAVE.
Los 103 puntajes y penalizaciones permanecen iguales. Se conservan las 31
correcciones de nombre, tarjetas, cuentas, transcripciones y segmentos.
Las 9.785 celdas del reporte actualizado se cotejan con el JSON, sin diferencias.
Completar mora no acredita identidad, recepción del recado o atribución de voz.

## Uso sin retranscripción

Extraer el ZIP completo y ejecutar `ACTUALIZAR_MORAS_Y_REANALIZAR.bat` en la raíz:

1. Seleccionar el `Checkpoint_r27_Recuperado.json` devuelto del lote de 103.
2. Seleccionar el Excel `Calidad Noviembre.xlsx` con el que se procesaron.
3. La consola muestra motor `3.6.19-r28`, 103 moras recuperadas y las rutas nuevas.

El resultado es `checkpoint_reanalizado.json` y `Reporte_Reanalisis_Reglas.xlsx`
en una carpeta independiente dentro de `%USERPROFILE%\MRS_Resultados`.
Conservar ese checkpoint para revisiones posteriores. El reanálisis no mueve
ni renombra físicamente audios. Los originales permanecen intactos.
No necesita otra reconstrucción de 95, lecturas adicionales ni instalar otro
Whisper/Python. La aplicación normal ya lee `mora` al cargar el Excel de cuentas.

Desde consola también admite:

```bash
python tools/reanalyze_checkpoint.py --checkpoint /ruta/checkpoint.json \
  --relation-excel /ruta/cuentas.xlsx --output-dir /ruta/nueva
```

La corrección de nombres y la recuperación de mora son operaciones separadas;
este lote ya trae sus nombres corregidos en r27. No se modifica el archivo Excel.

## Verificación y límites

- 1.016 pruebas aprobadas, incluidas 32 nuevas de alias, contradicciones, cruce,
  preservación, repetición sin cambios e integración con reglas de visitas y
  plazo mensual. Aplicación y herramientas compiladas con Python 3.10 en Linux.
- 268 evaluaciones históricas frente a r27: cero cambios de clasificación,
  cero violaciones de invariantes y cero retiros de penalizaciones sin causa.
- Los lotes anteriores de 95 y 36 conservan respectivamente 13 y 7 aprobaciones,
  las 22 y 13 revisiones de nombre, las diez lecturas ASR del primero y todas
  las confirmaciones financieras anteriores.
- Los 1.053 registros del Excel se leen sin errores de fila. Eso no significa
  que se hayan transcrito o evaluado 1.053 llamadas.
- R28 aún no tiene devolución de ejecución nativa Windows. No se ejecutó
  Whisper ni se escucharon audios en esta revisión. No se declara cierre de
  las 86 revisiones pendientes ni de los 13 problemas operativos.

Los archivos reales, hashes de cuentas, reportes y auditorías permanecen fuera
de Git. La entrega de código permite generar los datos actualizados en el PC.
