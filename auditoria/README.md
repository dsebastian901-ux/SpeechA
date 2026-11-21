# Auditoría integral r58 — continuación

Base de esta entrega: `b630ae9`, sobre `codex/auditoria-integral-r58-20261120`.

- [Informe de continuación y límites](CONTINUACION_R58.md).
- [Matriz completa: 89 criterios](MATRIZ_ERRORES.md).
- [Los 16 criterios: resultados antes/después](CRITERIOS_CONTINUACION.csv).
- [Pruebas automatizadas y reales](PRUEBAS.json).
- [94 regresiones comparadas contra la base](PRUEBAS_ANTES_DESPUES.csv).
- [2327 evaluaciones históricas: comparativo agregado](RESULTADOS_ANTES_DESPUES.csv).
- [Cinco no verificables: avance y requisitos pendientes](NO_VERIFICABLES.json).
- `AUDITORIA_INTEGRAL.xlsx`: matriz, inventario y regresiones en Excel, sin información de clientes.

3104 pruebas pasan, 0 fallos y 0 omisiones; 64 de las 94 regresiones nuevas fallaban en la base. 16 cierres del contrato de código y S.12 resuelto por arquitectura: matriz final 85 corregidos y 4 no verificables. No se realizó escucha humana ni se probó Windows físico. «Corregido» se refiere al alcance del código y sus pruebas, no a exactitud acústica universal.

El corpus histórico no cambió de dictamen ni puntaje. **No se demuestra una reducción de REVISAR.** Se preservaron umbral, penalizaciones y prioridad de seguridad. R57 conserva sin cambios los 780 archivos protegidos; la actualización usa un perfil local de cuentas separado.

La administradora puede crear operadores y asignarles individualmente lotes, dashboard y reportes. Autenticación local, cuentas y credenciales existentes se conservan al migrar. Exportación/importación por USB; los cambios en otro equipo requieren importar el catálogo actualizado.

Para reproducir las pruebas sin datos privados: `python auditoria/ejecutar_pruebas.py --output <directorio-nuevo>`. En Linux sin pantalla agregar `--xvfb <ruta-a-Xvfb>`. Para regenerar matriz e inventario: `python auditoria/generar_matriz.py`.

El ZIP contiene el código fuente completo, pruebas e informe. Requiere Python, dependencias y modelo Whisper local; no es un EXE ni un instalador nuevo. No contiene audios, checkpoints, Excel de clientes, catálogos reales, claves ni contraseñas. La auditoría anterior se conserva identificada como histórica en `AUDITORIA_PREVIA_B630AE9.md` y `MATRIZ_BASE_B630AE9.json`.
