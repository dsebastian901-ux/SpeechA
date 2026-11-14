# Control local de usuarios sobre MRS Speech Analytics r51

Rama de desarrollo: `feature/r51-local-user-access`, derivada de `codex/entrega-r51`.

## Arranque
Ejecute el lanzador existente `INICIAR_PROGRAMA.bat`. La primera vez se solicitará crear un administrador local, SIN contraseña predeterminada. En ejecuciones posteriores se pide usuario y contraseña antes de abrir la aplicación.

Las cuentas se guardan por equipo en `%LOCALAPPDATA%\\MRS\\SpeechAnalytics\\usuarios.sqlite3` (en Linux: `~/.local/share/MRS/SpeechAnalytics/usuarios.sqlite3`). NO se guardan en el repositorio ni en los directorios de proyecto.

## Controles implementados
- Contraseñas derivadas mediante PBKDF2-HMAC-SHA256, 600000 iteraciones, sal aleatoria por usuario y comparación en tiempo constante.
- Contraseña mínima de 12 caracteres, bloqueo de 15 minutos tras cinco fallos, auditoría de inicios, errores de acceso y administración.
- Roles locales: administrador, calidad, supervisor y consulta. El permiso de consulta se limita a inicio/dashboard; los restantes se gestionan por lista de control local.
- Administrador: creación, cambio de rol, desactivación, restablecimiento de contraseña temporal y consulta del listado de cuentas.
- Cambio de contraseña obligatorio tras restablecimiento; cierre de sesión manual o 30 minutos de inactividad.
- Comprobación del rol y estado activo desde base de datos al abrir las vistas autorizadas. No se puede desactivar el último administrador activo.

## Advertencias de seguridad / alcance
Esta primera integración protege el uso normal de la interfaz gráfica; NO constituye DRM ni protege contra un administrador del sistema operativo que pueda modificar el código y la base local. Los archivos de audio, Excel, exportaciones y checkpoints existentes siguen requiriendo permisos del sistema de archivos, cifrado de disco y controles de acceso Windows. La interfaz no reemplaza controles de autorización internos para cualquier script CLI ni garantiza bloqueo de exportaciones dentro de un dashboard ya abierto. Para uso con información personal real, validar accesos, exportaciones, recuperación de cuenta, permisos Windows y creación de cuentas en ambiente de pruebas.

## Pruebas
`py -3.10 -m pytest -q tests/test_local_user_access.py`
`py -3.10 -m pytest -q`

La publicación del código NO equivale a ejecución de pruebas en Windows. Validar manualmente el primer arranque, login, restablecimiento, bloqueo, cambio de perfil y ruta de datos. La revisión r51 de dictaminación / reetiquetado no se modifica.
