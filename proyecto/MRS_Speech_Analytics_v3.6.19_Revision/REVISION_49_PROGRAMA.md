# Revisión 49 del programa

Los mismos cambios se aplican al procesamiento normal y al reanálisis. No existen excepciones por número de llamada ni se alteran las transcripciones o los datos originales para conseguir aprobaciones.

## Decisión y carpetas

- NO_APROBADO cierra el rechazo expreso a recibir o transmitir un recado, o un incumplimiento ordinario verificable, cuando no subsisten dudas de seguridad independientes. La negativa posterior invalida una aceptación anterior; una aceptación y entrega posteriores pueden resolver una negativa inicial.
- La incapacidad de anotar un número de WhatsApp en una conversación con el titular no se interpreta como rechazo de recado de un tercero.
- La duración comprobada inferior al mínimo de 60 segundos ya existente puede cerrarse como NO_APROBADO, con su motivo. No confundir con espera de 65 segundos.
- REVISAR conserva las dudas de interlocutor, privacidad, referencias, seguridad y negociación. FALLA_GRAVE mantiene prioridad.
- GUI, resumen y Excel separan REVISAR de NO_APROBADO, FALLA_GRAVE y ERROR. Las copias del nuevo resultado se guardan en NO_APROBADOS.

## Recados y privacidad

Se reconocen respuestas naturales al dictado, aclaraciones de parentesco, lectura de vuelta del teléfono y confirmación de contacto ya anotado. La pregunta del gestor puede expresar el propósito del mensaje cuando se acredita aceptación y entrega. La frase del gestor «le digo, hablamos de MRS» no es aceptación del interlocutor. Aceptar una oferta de información no demuestra que ya se haya entregado. Un teléfono prometido requiere entrega o confirmación de que ya está disponible. Los ecos repetidos de un fragmento no acreditan un contacto completo.

La detección de dictado fonético no certifica los dígitos exactos del teléfono; no se utiliza para corregir tarjeta, importes o referencia. Se conservan las protecciones sobre importes, mora concreta, deuda explícita, tarjeta completa y estado financiero protegido. Solo las expresiones autorizadas «saldo pendiente» y «saldo vencido» sin cantidad están permitidas. Los defectos de ASR no se convierten en divulgación humana confirmada.

## Identidad y ARCO

No se confunde «su hija» con un nombre de titular. Se reconocen negativas a una lista explícita que incluye conocido y familiar, y respuestas de antigüedad aclaradas en varios turnos. La adquisición reciente de la línea se registra como descripción cualitativa, sin inventar días. Se reconoce la dictación literal de arroba y del dominio oficial completo cuando Whisper fusiona palabras; no se completa un dominio incompleto o distinto.

Derechos ARCO y el procedimiento completo siguen siendo obligatorios cuando corresponden. Las quejas por atención previa, groserías, amenazas, tiempos de espera y dudas de negociación conservan sus filtros.

## Validación y límites

VALIDACION_R49.json contiene el resultado exacto de pruebas, regresiones y comparación sobre las mismas 362 llamadas. La r48 publicada reprodujo exactamente las clasificaciones y puntajes del checkpoint recibido. El lote de 362 es un subconjunto del lote original de 403; no deben compararse sus totales directamente. En 51 llamadas cambió el texto al retranscribir.

Se ejecutan pruebas del lote normal con ASR controlado, copias de audio verificadas por hash, carpetas y reportes. Esto no equivale a una nueva transcripción acústica de todo el lote ni a escucha humana. La revisión manual continúa siendo alta. No se declara instalación nativa de Windows verificada en esta sesión ni entrega del futuro instalador autónomo con usuarios.
