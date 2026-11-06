# Reportes de varios lotes

En Reportes, el botón «Reportes de varios lotes» abre la nueva consolidación.
No requiere tener un proyecto abierto. Se cargan varios batch_checkpoint.json,
checkpoint_reanalizado.json o ZIP con un único checkpoint JSON. Los Excel son
salidas; esta primera implementación no importa reportes Excel como fuentes.

Cada lote cuenta por separado, por decisión de la usuaria. Un mismo audio en
dos lotes aporta dos evaluaciones y conserva su procedencia. No se selecciona
silenciosamente un resultado ganador ni se modifican dictámenes o transcripciones.

## Opciones

- Tipo: calidad y mejoras, motivos de no pago o fallas graves.
- Agrupación principal: global, gestor o supervisor.
- Filtros de gestor, supervisor y fechas de llamada.
- General: resúmenes y hasta tres ejemplos por criterio/agrupación.
- Detallado: todas las evaluaciones, errores y datos de cuenta seleccionados.
- Excel en todos los tipos; Word o Excel y Word en fallas graves.

Los Excel incluyen resúmenes por gestor y supervisor, desgloses por lote,
causas de no pago, errores comunes, recomendaciones, ejemplos y fuentes.
El detalle conserva los datos originales disponibles del Excel de cuentas.

## Ejemplos de errores

Fecha real de llamada, día de la semana, tarjeta del Excel como texto, gestor,
supervisor, nombre del audio, código y descripción del error, cita/ventana ASR
cuando esté localizada y lote de origen. Un contexto ASR se etiqueta como contexto,
no como prueba de una omisión. No se inventan citas, tiempos, tarjetas ni fechas.
La fecha de procesamiento no sustituye la fecha desconocida de una llamada.

Las fallas graves se toman del dictamen reportado o de un criterio explícitamente
invalidante. REVISAR y una queja de mala atención previa no se convierten por sí
solos en FALLA_GRAVE. Si origen combina aprobación y criterio crítico, se señala
la contradicción y se conserva la trazabilidad sin redictaminar.

Las recomendaciones se apoyan en criterios/categorías existentes. Una propuesta
de capacitación no es una falta nueva del gestor. Los motivos de terceros,
pago ya realizado y falta de evidencia se mantienen separados de causas de no pago.

## Estado de distribución

Módulo implementado y probado en desarrollo. Forma parte de la preparación
para la entrega offline del 14/nov/2026; no supone que ya exista el instalador
final con usuarios y permisos. El código de cuentas está aislado hasta integrar
las pantallas y validaciones. La receta de instalación no permite declarar listo
ese candidato sin las verificaciones pendientes de Windows.
