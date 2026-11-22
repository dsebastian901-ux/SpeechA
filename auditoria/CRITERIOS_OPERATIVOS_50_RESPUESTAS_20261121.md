# Matriz de decisiones operativas — 21 noviembre 2026

**Fuente:** respuestas de la usuaria a 50 preguntas de dictaminación, tras fijar otras 10 reglas previas. **No es una certificación de corrección del motor**. En caso de conflicto se conserva evidencia de audio, integridad de datos, cumplimiento y trazabilidad. Umbral de calidad: 80/100.

| N.º | Criterio acordado / aclaración pendiente |
|---:|---|
| 1 | Nombre completo confirmado: puede acreditar identidad del titular sin exigir 'soy yo'. |
| 2 | Solo cuatro dígitos sin nombre: NO acredita titular. |
| 3 | Si familiar transfiere a titular, dictaminar resultado final con titular; conservar cualquier incidente previo. |
| 4 | Un familiar afirma autorización: puede negociar; verificar autorización antes de revelar datos o cerrar acuerdo. |
| 5 | Si primero niega conocer y después confirma parentesco, prevalece declaración final verificable; conservar contradicción como evidencia. |
| 6 | Contestador/grabadora: estatus BUZÓN. |
| 7 | No puede anotar pero acepta recibir y transmitir: recado válido si se acredita mensaje. |
| 8 | Si recibe y acepta el recado aunque después indique que no tiene forma de localizar al titular, **se conserva estatus de RECADO** según tipo de tercero (MENSAJE CON FAMILIAR / MENSAJE CON TERCERO / MENSAJE EN TRABAJO). La imposibilidad de transmitirlo debe constar en la evidencia y no se acredita contacto de retorno inexistente; calidad se evalúa por separado. |
| 9 | Recibe mensaje completo sin prometer retransmisión: válido, siempre que recepción y contenido estén acreditados. |
| 10 | Falta instrucción dirigida al titular para contactar MRS: recado INCOMPLETO. |
| 11 | Compañero de trabajo que acepta mensaje: MENSAJE EN TRABAJO. |
| 12 | Tercero que acepta sin confirmar parentesco: MENSAJE CON TERCERO (interpretación de respuesta '13 mensaje tercero'). |
| 13 | Negativa inicial al recado revocada por aceptación posterior: prevalece aceptación final (interpretación de 'si' restante). |
| 14 | Rechazo del recado no autoriza 100 puntos automáticamente; puntuar etapas ejecutables, sin inventar penalización específica. |
| 15 | Cuelgue no anunciado: resolver por conversación previa, NO enviar automáticamente a REVISAR por fin abrupto. |
| 16 | Titular cuelga luego de aceptar monto y fecha: NO DEFINE. |
| 17 | Una alternativa concreta antes del cuelgue basta para NO DEFINE. |
| 18 | Pregunta '¿cuánto puede pagar?' sin propuesta/alternativa: NO cuenta como alternativa. |
| 19 | Falla técnica acreditada: ERROR DE AUDIO, no TITULAR CUELGA. |
| 20 | Si titular cuelga antes de identificación MRS, SÍ descontar puntos de identificación. |
| 21 | 'Ajá' sin aceptación contextual clara: NO confirma convenio. |
| 22 | Acepta 'el mínimo' sin cifra específica: NO acredita monto confirmado. |
| 23 | Acepta 'todo el saldo' sin cifra: NO acredita monto confirmado. |
| 24 | Fecha propuesta por gestor pero no confirmada por titular: NO DEFINE. |
| 25 | Convenio inicialmente aceptado, luego 'mejor lo pienso': NO DEFINE. |
| 26 | Convenio aceptado, última expresión 'no pagaré': NEGATIVA. |
| 27 | Acepta monto el viernes: CONVENIO solo si cumple fecha límite, asignación y mora. |
| 28 | 'No puedo pagar por ahora': NO DEFINE, no negativa definitiva. |
| 29 | Ofrece otro monto sin fecha: NO DEFINE. |
| 30 | Acepta parcial menor al mínimo: estatus CONVENIO; aprobación requiere explicación expresa de que es pago parcial y no regulariza. Aplicar demás reglas. |
| 31 | Mención del pago mínimo como opción al titular: SÍ cuenta como alternativa. |
| 32 | 'Llámeme mañana para confirmar': NO DEFINE. |
| 33 | Reporta pago por debajo del mínimo y no acepta cubrir diferencia: NO DEFINE. |
| 34 | Pago rechazado/revertido: para CONVENIO el gestor debe dar instrucciones correctas de pago y confirmar día nuevo; sin solución se califica FALLA GRAVE cuando hechos están comprobados. |
| 35 | Pago previo en lugar no autorizado: gestor debe orientar a lugares autorizados; carpeta LUGARES_NO_AUTORIZADOS, separando conducta del cliente y gestor. |
| 36 | Titular rechaza enviar comprobante: NO penalizar al gestor si lo solicitó correctamente. |
| 37 | Referencia distinta: carpeta LUGARES_NO_AUTORIZADOS; no afirmar fraude sin verificar los dígitos. |
| 38 | Familiar reporta haber pagado: CONVENIO si se compromete a enviar comprobante; sin confundir con verificación bancaria. |
| 39 | Tras verificar al titular la usuaria indica NO conservar automáticamente infracción por divulgación anterior; implementar solo si realmente fue al mismo titular, no dispensar divulgación a terceros. |
| 40 | Tercero menciona espontáneamente saldo sin datos nuevos revelados por gestor: correcto en protección de datos. |
| 41 | ARCO explicado correctamente y cliente rechaza documentos: valorar correcto lo ejecutado por gestor. |
| 42 | ARCO interrumpido por cuelgue del titular: evaluar lo ejecutado antes del cuelgue. |
| 43 | Cliente insulta pero gestor profesional y puede completar gestión: calidad normal, no EXCEPCIÓN automática. |
| 44 | Grosería confirmada del GESTOR al final de grabación: FALLA GRAVE. |
| 45 | >=80 y discrepancia de etiqueta probada: APROBADO_ETIQUETA_CORREGIDA, sin revisión innecesaria. |
| 46 | <80 con alerta independiente pendiente: NO APROBADO, mantener alerta auditable. |
| 47 | Emisor de posible grosería no aclarado tras segunda escucha: emitir dictamen CON ALERTA, sin afirmar infracción del gestor ni aprobar una falta confirmada; requiere definir clasificación final si afecta aprobación. |
| 48 | Corrección manual del supervisor con justificación: persistente entre reprocesamientos hasta nueva modificación autorizada. |
| 49 | Mismo audio y misma cuenta en diferentes lotes: reutilizar corrección de forma idempotente, con único historial y auditoría; no transferir a otras cuentas. |
| 50 | Sin códigos inventados para BUZÓN/TITULAR CUELGA/CONVENIO INCUMPLIDO/SE NIEGAN A TOMAR RECADO: si hay error con estatus aprobado y evidencia, reetiquetar solo con código autorizado; en otro caso solo calificar. |

## Límites y validación

- 8: aclarado expresamente: se conserva RECADO cuando el tercero acepta recibirlo, aun si luego no puede contactar al titular. No equivale a confirmar retransmisión ni número de retorno.
- 12/13: la respuesta dictada saltó de 11 a «13 mensaje tercero, si»; se interpreta provisionalmente **12 = MENSAJE CON TERCERO; 13 = sí**, sin borrar la literalidad.
- 14: no se asigna puntaje inventado; dependerá de la matriz de calidad.
- 39: no eliminar una divulgación real a un tercero por identificar posteriormente al titular. La respuesta aplica solo cuando se prueba que el receptor era el propio titular.
- 47: alerta visible y dictamen no es autorización de aprobar groserías confirmadas ni atribuir voces por ASR.
- 50: los códigos nuevos requieren catálogo autorizado. La calificación y el estatus son independientes.
- Las decisiones de usuario no reemplazan análisis acústico, comparación Excel, regresiones, pruebas Windows ni validación independiente. No alterar originales de audio, Excel o checkpoint.

## Estado de ejecución (parcial)

- Cambios publicados en la misma rama y PR borrador para cuelgue confirmado (16), preguntas vs alternativas (17,18,31), origen no autorizado OXXO/Elektra (35) y clasificación aparte de referencias distintas (37), además de la tanda de reglas previa.
- El resto debe pasar por implementación y regresión, sin declarar cubiertos los 50 escenarios ni la reducción de REVISAR.
