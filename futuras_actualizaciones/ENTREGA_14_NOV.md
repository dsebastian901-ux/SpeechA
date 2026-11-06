# Objetivo: entrega del 14 de noviembre de 2026

## Alcance confirmado

- Instalador Windows con icono de escritorio e inicio de sesión.
- Trabajo sin internet: modelos Whisper y dependencias completos en la instalación.
- Equipos separados; gestión y actualización de cuentas mediante USB.
- Una administradora; operadores limitados a lotes, dashboard y reportes.
- Revisiones alternas exclusivamente para la administradora.
- Reportes consolidados por gestor, supervisor o global; cada lote cuenta por
  separado aunque repita llamadas de otros lotes.
- General y detallado, causas de no pago, errores frecuentes, recomendaciones y
  fallas graves en Excel y Word, con ejemplos trazables a audio/fecha/tarjeta/gestor.

## Avance actual

- Implementado el servicio de reportes y su diálogo dentro de Reportes.
- Generación local de Excel y Word, sin ejecutar Whisper ni cambiar dictámenes.
- Modelo Whisper resuelto exclusivamente desde disco/caché local; se comprueba
  tokenizer y se evita la descarga automática de modelos o tokenizadores.
- Base de cuentas offline firmadas implementada y probada por separado; aún
  no conectada al inicio ni a los permisos de la aplicación.
- Icono ICO preparado a partir del logotipo existente.
- Receta Inno Setup con acceso de escritorio y menú Inicio. Las verificaciones
  de entrega permanecen bloqueadas hasta integrar y probar el candidato.

## Pendiente de aceptación

- Concluir la integración de login, permisos, USB, dashboard y datos de usuario.
- Compilar el ejecutable y el instalador en Windows, incluyendo modelos completos.
- Probar instalación limpia y actualización sin internet en dos computadoras.
- Revisar los 100 audios nuevos reales de la prueba solicitada; los casos de
  integración sintéticos no reemplazan esa validación.
- Repetir la regresión sobre el candidato final instalado y verificar restricciones
  de operador, conservación de datos y generación de los reportes requeridos.

La fecha es un objetivo solicitado; este archivo no programa ejecución futura
automática ni declara listo un instalador que todavía no se ha compilado.
