# Próxima actualización: usuarios sin internet

Objetivo de entrega solicitado: 14 de noviembre de 2026. La versión r41 ya
publicada permanece intacta para la prueba en curso. No hay aún un instalador
final ni inicio de sesión integrado; esta carpeta contiene la preparación.

## Decisiones vigentes de la usuaria

- Computadoras separadas, sin internet y sin servidor remoto.
- Una sola administradora con todas las funciones.
- Operadores: procesamiento por lotes, dashboard y reportes.
- Las revisiones alternas se conservan exclusivamente para la administradora.
  Esta es la aclaración final y reemplaza la indicación intermedia de retirarlas
  también de su cuenta.
- Altas, bajas y cambios de cuentas se transportan por USB. Una baja no se aplica
  en una computadora que todavía no haya importado el catálogo actualizado.
- Cada lote se cuenta por separado en los reportes, incluso si repite llamadas
  de otro lote o reanálisis.
- No modificar los criterios de análisis ni perder las correcciones previas.

El nombre de la cuenta titular se guarda en la preparación privada, no en el
código público. La contraseña se configurará localmente y no se pide por chat.

## Matriz

| Operación | Administradora | Operador |
| --- | --- | --- |
| Procesar lotes y consultar sus reportes | Sí | Sí |
| Dashboard, consulta, escucha y exportaciones permitidas | Sí | Sí |
| Reportes consolidados Excel y Word | Sí | Sí |
| Crear/desactivar usuarios y cambiar credenciales | Sí | No |
| Configuración, modelos y reglas | Sí | No |
| Gestión de proyectos, audios y transcripciones individuales | Sí | No |
| Revisiones alternas y confirmaciones humanas | Sí | No |
| Crear otra administradora, desactivar o demover a la titular | No | No |

La selección de un proyecto existente dentro de lotes/dashboard/reportes no
concede permiso para administrar proyectos. La exportación de resultados
calculados no equivale a modificar un dictamen.

## Base implementada y probada, todavía aislada de la aplicación

`offline_accounts.py` implementa catálogos USB firmados, contraseñas con hash y
sal individual, una administradora activa, operadores con tres permisos,
validación de la clave pública de confianza, rechazo de cambios de rol/manipulación,
rechazo de catálogos antiguos, persistencia local y sesiones temporales.
La clave privada de administración se exporta solo cifrada y nunca se incluye
en el paquete de operadores. Las pruebas usan identidades y claves sintéticas.

La firma verifica procedencia e integridad; no cifra el catálogo de usuarios.
El catálogo contiene verificadores de contraseña y se administra como archivo
privado. No debe publicarse en repositorios, reportes ni descargas generales.

## Trabajo pendiente antes de distribuir

1. Integrar login, cierre de sesión y administración de usuarios en la GUI.
2. Aprovisionar la clave pública de confianza desde la instalación autorizada;
   un operador no debe poder elegir otra autoridad o registrar una administradora.
3. Conectar validaciones de sesión y permiso a menús, navegación directa,
   acciones y revisiones administrativas. No basta ocultar botones.
4. Integrar importación/exportación USB y respaldo cifrado de la clave privada;
   las sesiones anteriores se invalidan al importar un catálogo actualizado.
5. Registrar identidad del usuario que inicia cada lote o hace una corrección,
   sin reescribir confirmaciones previas ni evidencias ASR.
6. Separar cuentas, proyectos y resultados de los archivos que reemplaza el instalador.
7. Empaquetar Python, dependencias, modelos completos y acceso directo con icono.
   El equipo final no debe necesitar pip ni descargar modelos.
8. Probar el candidato instalado en dos Windows 10 sin internet: administradora,
   operador, actualización USB, rechazo de revisiones, lotes, dashboard y reportes.

El alcance son permisos de aplicación y catálogos firmados. No se presenta
el empaquetado como defensa contra quien controle Windows o modifique el
propio ejecutable. La protección de archivos y de la clave privada forma parte
de la instalación y debe verificarse junto con el flujo de aplicación.
