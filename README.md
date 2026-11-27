# MRS Speech Analytics — r67

Revisión independiente en `codex/consolidacion-r67-20261127`, basada en r66 (`13684a3`). Los cambios se aplican al motor de procesamiento por lotes y a la evaluación de proyectos nuevos. R66 conserva su rama y su código.

Se corrigen la negociación cronológica, los cierres de fecha e importe, las parcialidades completas, la selección de fragmentos y el ciclo de la tercera escucha. Se distingue ejecución de suficiencia acústica. Los hechos recuperados pasan por las mismas reglas financieras y de seguridad; no se modifican las ponderaciones ni el mínimo de 80 puntos.

Consulte [cambios, pruebas y límites](auditoria/r67-20261127/README.md), [matriz de los 12 requisitos](auditoria/r67-20261127/MATRIZ_FUNCIONAL.csv) y [comparativo anónimo de las 23 llamadas](auditoria/r67-20261127/COMPARATIVO_23.csv). Las aprobaciones de casos controlados no representan aprobaciones de llamadas de clientes.

## Actualizar la instalación existente

Con el programa cerrado y los cambios locales guardados, desde la carpeta del repositorio en PowerShell:

```powershell
git fetch origin
git switch codex/consolidacion-r67-20261127
.\INICIAR_PROGRAMA.bat
```

La barra debe mostrar `3.6.19-r67-cronologia-escuchas-20261127-validacion`. Se conserva el entorno Python existente, los modelos locales, la autenticación y el catálogo de usuarios. Las cuentas siguen en su ubicación local habitual; no se incluyen contraseñas ni catálogos de usuarios en los entregables.

La actualización por Git necesita conexión; el procesamiento continúa local y sin internet. No se activa Medium como modelo principal: se utiliza su instalación local para contrastes cuando corresponde. Si falta audio o evidencia suficiente, se conserva el bloqueo y se explica en los reportes.

El ZIP es código fuente y no incluye Python, pesos de modelos ni un instalador EXE. Para conservar r66, extraer en otra carpeta y configurar el entorno y modelos locales mediante las herramientas existentes. No copiar datos de cuentas ni reemplazar originales con archivos del paquete.

## Pruebas reproducibles

Desde `proyecto/MRS_Speech_Analytics_v3.6.19_Revision`, con las dependencias locales instaladas:

```powershell
python -m pytest -q --tb=short
```

La suite completa se conserva en la rama Git. El ZIP incluye las regresiones sintéticas seleccionadas y sus dependencias, sin los datos históricos de clientes.

El informe [PRUEBAS.json](auditoria/r67-20261127/PRUEBAS.json) registra las ejecuciones comprobadas y sus límites. No se afirma prueba en Windows físico ni escucha humana. El lote real de 23 llamadas se contrastó con transcripciones y registros guardados; faltan sus audios originales para nuevas escuchas y cotejo de integridad.
