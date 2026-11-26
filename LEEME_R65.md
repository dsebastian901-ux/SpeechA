# r65 · Código para validación

La versión es `3.6.19-r65-consolidacion-20261125-validacion`. Conserva los componentes locales, usuarios, permisos y modelos de la instalación existente. El ZIP de fuente no incluye dependencias, modelos, cuentas ni información de clientes; no es un instalador autónomo.

Cerrar MRS antes de cambiar el código. Desde la terminal de Visual Studio Code, en el repositorio instalado, obtener la rama nueva de forma explícita (el repositorio puede tener una configuración de fetch limitada a otra rama):

```powershell
git status --short --branch
git fetch origin codex/consolidacion-r65-20261125:refs/remotes/origin/codex/consolidacion-r65-20261125
git switch --track origin/codex/consolidacion-r65-20261125
.\INICIAR_PROGRAMA.bat
```

La rama operativa no se sobrescribe. Las cuentas y contraseñas existentes permanecen en sus archivos locales; no hay que borrarlas ni volver a crearlas para esta actualización. No se modifica el modelo primario de transcripción por instalar esta versión.

Consultar [la entrega y sus pruebas](auditoria/r65-consolidacion-20261125/ENTREGA.md). La repetición sobre las transcripciones de las mismas 79 llamadas se entrega en el comparativo privado; no acredita nuevas escuchas del lote. Para validar el flujo completo en Windows hacen falta sus audios originales, el Excel que vincule las 19 llamadas pendientes y el acceso local autorizado. El reporte incluye los nombres/rutas y las ventanas que requieren cotejo; esos datos no están en GitHub.

Los proyectos nuevos y la actualización normal de resultados guardados utilizan el motor productivo corregido. Una transcripción nueva puede producir evidencia distinta: no se promete identidad acústica de resultados sin ejecutar esos audios. Medium solo se usa para revisión focalizada cuando está disponible localmente; no se descargan modelos para efectuarla y la falta de emisor acreditado conserva la revisión.

La prueba física de Windows y la escucha humana siguen pendientes. No se compiló EXE ni se declara la versión lista para producción.
