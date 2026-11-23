# Arranque desde VS Code en una computadora nueva

La usuaria confirmó que es la primera instalación en su equipo. El error
observado fue `ModuleNotFoundError: No module named 'customtkinter'` estando
en la rama de integración y commit `bc7f834`. Descargar código desde GitHub
no instala los paquetes de Python ni el modelo local de Whisper.

Además, el lanzador anterior prefería el Python global y no examinaba los
entornos del repositorio ni el runtime portable. `INSTALAR.bat` anunciaba
componentes listos por la sola existencia de `runtime/python/python.exe`.

## Corrección

- `ENTORNO_MRS.bat` comparte la selección entre instalación/comprobación y
  arranque: Python explícito, entorno activado, `.venv`/`venv` locales,
  runtime portable y candidatos PATH/py. Solo usa un candidato que supere
  la comprobación; no considera suficiente que exista el ejecutable.
- `tools/check_startup_environment.py` verifica Python >=3.10 de 64 bits,
  Tkinter y los paquetes de requirements, incluidas sus importaciones nativas.
  Informa todos los faltantes y errores DLL. No abre GUI, cuentas ni modelos,
  ni ejecuta pip o descargas de pesos.
- `INICIAR_MRS.bat` usa el entorno verificado y conserva el código de salida
  real de main. `INSTALAR.bat` comprueba lo mismo sin abrir main; mantiene
  un código de error cuando faltan dependencias.
- `LEEME_INSTALACION.txt` distingue instalación inicial de paquetes, uso
  offline, preparación desde ruedas locales y modelo Small por USB. El
  modelo no se descarga ni se activa por comprobar dependencias.

## Evidencia

| Ejecución | Resultado |
|---|---|
| Dos regresiones con scripts originales de bc7f834 | 2 fallan: CustomTkinter del entorno local ignorado y runtime incompleto anunciado listo |
| Ocho pruebas reales de CMD con Python Windows bajo Wine | 8 pasan |
| Preflight, usuarios/permisos y criterios de dictaminación | 72 pasan, 0 fallan |

Los escenarios de CMD prueban entorno activo, `.venv` del repositorio,
entorno local de aplicación, Python explícito, fallback cuando un entorno
está incompleto, runtime bueno/malo y propagación de errores de main.
Usan un main controlado que importa CustomTkinter real y registra el Python
ejecutado, con rutas que contienen espacios y paréntesis. No simulan paquetes
instalados con módulos vacíos. Las pruebas no descargan paquetes: los entornos
temporales usan las bibliotecas locales del Python de pruebas.

**No se declaró validación en Windows físico ni apertura real de la GUI en
estos escenarios de CMD.** El fallback de `py` registrado debe comprobarse en
el equipo físico. En Linux, las ocho pruebas de CMD se omiten por plataforma;
su ejecución comprobada se realizó con el runtime Windows bajo Wine.

Las fuentes dentro de `app/` coinciden con las de la última suite completa de
criterios (3248 pasan, 0 fallan, 2 omitidas). Esa suite no se vuelve a presentar
como ejecutada para este cambio de scripts: aquí se ejecutó la regresión
focal de 72 y los ocho casos CMD. Se verificaron 780 hashes protegidos de R57
sin cambios. No se compilaron ejecutables ni se activó Medium experimental.

[ARRANQUE_WINDOWS_20261123.json](ARRANQUE_WINDOWS_20261123.json) contiene
resultados, hashes de fuentes y hashes de los registros privados.

## Preparación en el equipo de la usuaria

Con terminal PowerShell en la raíz de SpeechA, usar un Python 3.10 de 64 bits
para crear `.venv` e instalar los requisitos completos; luego abrir
`INICIAR_PROGRAMA.bat`. La preparación inicial con pip requiere conexión,
salvo que se disponga de todas las ruedas compatibles por USB. El uso
posterior offline requiere además un modelo Whisper local completo.
El éxito de las pruebas no afirma que los paquetes ya estén instalados en
la computadora de la usuaria; esa instalación todavía requiere ejecutarse.
