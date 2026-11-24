"""Consenso de hechos concretos sobre un único audio, sin votación de voces.

Las lecturas son decodificaciones correlacionadas. La coincidencia corrobora
texto; no crea diarización, una fecha, un pago bancario ni una excepción.
"""
from collections import Counter
import re

from app.services.conversation_evidence import normalize, sentence_evidence

VALIDATOR_REVISION = 'r59-hechos-20261124-v1'
STATES = {'CONFIRMADO', 'DESCARTADO_CON_EVIDENCIA', 'CONTRADICTORIO',
          'SIN_ATRIBUCION', 'EVIDENCIA_INSUFICIENTE'}
OFFENSE = re.compile(r'\b(?:que poca madre|chingad[ao]s?|chingues|chingue|'
                     r'pendej[oa]s?|cabron(?:a|es)?|mierda|pinche|put[ao]s?)\b')
THREAT = re.compile(r'\b(?:vamos a|voy a|iremos a|pasaremos a|se realizara|realizaremos)\b'
                    r'[^.!?]{0,65}\b(?:visita|domicilio|diligencia|embargo)\b')
NONASSERTIVE = re.compile(r'\b(?:dice que|dijo que|diga que|repita|supongamos|'
                          r'por ejemplo|si hubiera|si hubiese)\b')
FACT_RULES = {
    'holder': ('IDENTITY',), 'callback': ('CALLBACK',),
    'financial': ('AMOUNT', 'PAYMENT_DATE', 'COMMITMENT_WITHOUT_DATE',
                  'RECEIPT_REQUEST', 'PAYMENT_PLACES', 'REFERENCE'),
    'safety': ('DISCLOSURE', 'ARCO', 'REFERENCE', 'HOME_WARNING', 'OFFENSE', 'CONFRONTATION',
               'INTERLOCUTOR_HOSTILITY'),
}


def unresolved_cues(text,purpose):
    """Cambios pertinentes a la pregunta pendiente, sin distancia entre textos."""
    source=normalize(text)
    cues=set()
    if purpose in {'holder','general'}:
        from app.services.context_audio_recovery import nominal_words
        cues.update('NOMBRE:'+word for word in nominal_words(text))
        if re.search(r'\b(?:soy yo|exactamente|digame|no soy|soy su)\b',source):
            cues.add('RESPUESTA_NOMINAL_POR_VALIDAR')
    if purpose in {'financial','general'}:
        cues.update('TIEMPO:'+m.group()for m in re.finditer(
            r'\b(?:hoy|manana|ayer|mes|lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b',source))
        cues.update('IMPORTE:'+m.group()for m in re.finditer(r'\b\d+(?:[.,]\d+)?\s+pesos\b',source))
        if re.search(r'\b(?:comprobante|ticket|captura)\b',source):cues.add('COMPROBANTE_POR_VALIDAR')
    if purpose in {'callback','general'} and re.search(r'\b(?:numero|telefono|contacto|comunique)\b',source):
        cues.update('DIGITOS:'+digits for digits in re.findall(r'\d+',source))
    if purpose in {'safety','general'}:
        for name,pattern in [('OFENSA',OFFENSE),('ADVERTENCIA',THREAT),
                             ('ARCO',re.compile(r'\barco\b'))]:
            if pattern.search(source):cues.add(name)
    return cues


def _fact(rule, value, evidence, role='NO DETERMINADO', *, polarity=True, attributed=None):
    return {'rule': rule, 'value': value, 'text': str(evidence), 'speaker_role': role,
            'polarity': polarity, 'attributed': (role != 'NO DETERMINADO'
                                               if attributed is None else attributed)}


def extract_facts(reading, purpose, relation=None):
    """Reutilizar extractores operativos; nunca completar hechos desde Excel."""
    from app.services.context_audio_recovery import nominal_words, nominal_self_reply
    from app.services.conversation_evidence import (
        holder_confirmation, payment_commitment, assess_privacy, dictated_privacy_email,
    )
    from app.services.contextual_identity_evidence import COUNTER, proxy_account_evidence
    from app.services.contact_dialogue_resolution import declared_intermediary
    from app.services.payment_reference_validation import callback_numbers, find_reference
    from app.services.operational_script_evidence import receipt_request_evidence
    from app.services.payment_intent_frames import payment_frames, DATE, CONDITION
    from app.services.current_payment_amounts import explicit_current_amounts
    from app.services.conversation_evidence import _role_at
    text = str(reading.get('text') or '')
    segments = reading.get('segments') or []
    source = normalize(text)
    facts = []
    if purpose in {'holder', 'general'}:
        names = sorted(nominal_words(text))
        third = bool(COUNTER.search(source) or proxy_account_evidence(text, segments)
                     or declared_intermediary(text, segments)['confirmed'])
        if third:
            facts.append(_fact('IDENTITY', names, text, polarity=False, attributed=True))
        elif names and (holder_confirmation(text, segments)['confirmed'] or nominal_self_reply(text)):
            # Atribución CONVERSACIONAL; no se declara una voz identificada por ASR.
            facts.append(_fact('IDENTITY', names, text, 'CONTEXTO_NOMINAL', attributed=True))
    if purpose in {'callback', 'general'}:
        for number in callback_numbers(text):
            facts.append(_fact('CALLBACK', number['digits'], number['text'],
                               'CONTEXTO_DE_RECONTACTO', attributed=True))
    if purpose in {'financial', 'general'}:
        for amount in explicit_current_amounts(text, segments):
            if amount['method'] == 'MONTO_EXPLICITO_DE_OPERACION_DE_PAGO':
                continue  # una instrucción no prueba aceptación del interlocutor
            role = _role_at(text, segments, amount['position'])
            facts.append(_fact('AMOUNT', amount['amount'], amount['evidence'], role,
                               attributed=role in {'TITULAR', 'INTERLOCUTOR'}))
        frames = payment_frames(text, segments)
        for frame in frames:
            if not frame['accepted'] or frame['history']:
                continue
            # La fecha debe pertenecer a la respuesta/objeto aceptados.
            dates = DATE.findall(frame['reply'])
            if not dates:
                candidates=DATE.finditer(frame['question'])
                for match in candidates:
                    if re.match(r'\s*(?:pesos|mil|pagos|meses|por ciento)\b',frame['question'][match.end():]):
                        continue
                    if (frame['kind']=='DATE' or not re.fullmatch(r'(?:el )?(?:dia )?\d{1,2}',match.group())
                            or re.search(r'\b(?:el|dia)\s*$',frame['question'][:match.start()])):
                        dates.append(match.group())
            role = _role_at(text, segments, frame['position'])
            for date in dates:
                facts.append(_fact('PAYMENT_DATE', date, frame['evidence'], role,
                                   attributed=role in {'TITULAR', 'INTERLOCUTOR'}))
        commitment = payment_commitment(text, segments)
        if commitment.get('accepted') and not commitment.get('conditional') and not any(f['rule'] == 'PAYMENT_DATE' for f in facts):
            evidence = commitment.get('evidence') or text
            # No convertir una fecha omitida por el extractor en compromiso sin fecha.
            if not DATE.search(source) and not CONDITION.search(source):
                positions=[e['position']for e in commitment.get('contextual_confirmation_events',[])
                           if isinstance(e.get('position'),int)]
                roles={_role_at(text,segments,p)for p in positions}
                role=next(iter(roles))if len(roles)==1 else 'NO DETERMINADO'
                facts.append(_fact('COMMITMENT_WITHOUT_DATE', True, evidence,
                                   role,attributed=role in {'TITULAR','INTERLOCUTOR'}))
        receipt = receipt_request_evidence(text, segments)
        for item in receipt['request_evidence']:
            facts.append(_fact('RECEIPT_REQUEST', True, item['text'], item['speaker_role'],
                               attributed=item['speaker_role'] == 'GESTOR'))
        for item in receipt['withdrawal_evidence']:
            facts.append(_fact('RECEIPT_REQUEST', True, item['text'], item['speaker_role'],
                               polarity=False, attributed=item['speaker_role'] == 'GESTOR'))
        from app.config.payment_places import AUTHORIZED_PAYMENT_PLACES
        from app.services.conversation_evidence import payment_places
        places = payment_places(text, segments, AUTHORIZED_PAYMENT_PLACES)
        if places:
            facts.append(_fact('PAYMENT_PLACES', sorted({p['place'] for p in places}),
                               ' / '.join(p['text'] for p in places),
                               'GESTOR' if all(p['speaker_role'] == 'GESTOR' for p in places)
                               else 'NO DETERMINADO'))
    if purpose in {'financial','safety','general'}:
        reference = find_reference(text)
        for item in reference['detected']:
            position = source.find(item['evidence'])
            role = _role_at(text, segments, max(0, position))
            facts.append(_fact('REFERENCE', item['digits'], item['evidence'], role,
                               attributed=role == 'GESTOR'))
    if purpose in {'safety', 'general'}:
        privacy = assess_privacy(text, segments,
                                third_party_confirmed=declared_intermediary(text, segments)['confirmed'])
        for item in privacy['evidence']:
            # El mero reporte de un pago por un familiar no es divulgación del gestor.
            if item['speaker_role'] in {'TITULAR', 'TERCERO', 'INTERLOCUTOR'}:
                facts.append(_fact('DISCLOSURE', item.get('phrase'), item['text'],
                                   item['speaker_role'], polarity=False))
            else:
                facts.append(_fact('DISCLOSURE', item.get('phrase'), item['text'],
                                   item['speaker_role'], attributed=item['confirmed']))
        from app.services.arco_validation import assess_arco
        email = dictated_privacy_email(text, segments)['detected'] or bool(re.search(
            r'\bprivacidad1?@bradesco\.com\.mx\b', source))
        arco = assess_arco(text, segments, email_given=email)
        if arco['complete_procedure'] or arco['process_denied']:
            roles = [u['speaker_role'] for u in sentence_evidence(text, segments)
                     if re.search(r'\b(?:arco|ine|comprobante|privacidad)\b', normalize(u['text']))]
            facts.append(_fact('ARCO', 'PROCEDIMIENTO_COMPLETO', text,
                               'GESTOR' if roles and all(r == 'GESTOR' for r in roles)
                               else 'NO DETERMINADO', polarity=not arco['process_denied']))
        for unit in sentence_evidence(text, segments):
            value = normalize(unit['text'])
            for rule, expression in [('OFFENSE', OFFENSE), ('HOME_WARNING', THREAT),
                    ('CONFRONTATION', re.compile(r'\b(?:callese|no me importa|usted es un mentiroso)\b'))]:
                match = expression.search(value)
                if match and not NONASSERTIVE.search(value[:match.start()]):
                    denied = bool(re.search(r'\b(?:no|nunca|jamas)\s*$', value[:match.start()]))
                    facts.append(_fact(rule, match.group(), unit['text'], unit['speaker_role'],
                                       polarity=not denied))
                    if rule == 'OFFENSE' and unit['speaker_role'] in {'TERCERO', 'TITULAR', 'INTERLOCUTOR'}:
                        facts.append(_fact('INTERLOCUTOR_HOSTILITY', match.group(), unit['text'],
                                           unit['speaker_role'], polarity=not denied))
    return facts


def consensus(purpose, attempts, relation=None):
    """Dos coincidencias de hecho; una contradicción explícita nunca se vota fuera."""
    from app.services.context_audio_recovery import reading_quality
    from app.services.context_audio_recovery import digest
    good = [a for a in attempts if not a.get('error') and reading_quality(a)]
    extraction_purpose='safety'if purpose=='safety_tail'else purpose
    observations = [extract_facts(a, extraction_purpose, relation) for a in good]
    rules = sorted(set(FACT_RULES.get(extraction_purpose, ())) |
                   {f['rule'] for values in observations for f in values})
    outcomes = []
    for rule in rules:
        by_reading = [[f for f in values if f['rule'] == rule] for values in observations]
        positive = {digest(f['value']) for row in by_reading for f in row if f['polarity']}
        negative = {digest(f['value']) for row in by_reading for f in row if not f['polarity']}
        count = Counter(key for row in by_reading for key in
                        {digest((f['value'], f['polarity'])) for f in row})
        common = {key for key, value in count.items() if value >= 2}
        matching = [f for row in by_reading for f in row
                    if digest((f['value'], f['polarity'])) in common]
        roles={('INTERLOCUTOR'if f['speaker_role']in{'TITULAR','INTERLOCUTOR','TERCERO'}else
                f['speaker_role'])for f in matching if f['attributed']}
        contradiction = bool((positive and negative) or len(positive) > 1 or len(negative) > 1)
        if contradiction:
            state, reason = 'CONTRADICTORIO', 'VALORES_O_POLARIDAD_INCOMPATIBLES'
        elif len(roles)>1:
            state, reason = 'CONTRADICTORIO', 'EMISORES_INCOMPATIBLES'
            contradiction=True
        elif len(good) < 2:
            state, reason = 'EVIDENCIA_INSUFICIENTE', 'MENOS_DE_DOS_LECTURAS_USABLES'
        elif not common:
            state, reason = 'EVIDENCIA_INSUFICIENTE', 'HECHO_NO_CORROBORADO'
        elif not all(f['attributed'] for f in matching):
            state, reason = 'SIN_ATRIBUCION', 'HECHO_COINCIDENTE_SIN_EMISOR_ACREDITADO'
        else:
            state = 'CONFIRMADO' if matching[0]['polarity'] else 'DESCARTADO_CON_EVIDENCIA'
            reason = 'HECHO_Y_CONTEXTO_COINCIDENTES_EN_MISMO_AUDIO'
        outcome={'rule': rule, 'state': state, 'reason_code': reason,
                         'matching_evidence': matching,
                         'contradictory_evidence': [f for row in by_reading for f in row] if contradiction else [],
                         'speaker_attribution': ('CONTEXTUAL' if rule in {'IDENTITY', 'CALLBACK'}
                                                 and matching else 'EXPLICITA_EN_TEXTO' if matching and
                                                 all(f['attributed'] for f in matching) else 'NO_ACREDITADA'),
                         'resolves_codes': []}
        if rule=='REFERENCE':
            expected=re.sub(r'\D','',str((relation or{}).get('numero_de_tarjeta')or''))
            values={f['value']for f in matching}
            outcome['matches_account']=(values=={expected}if len(expected)==16 and values else None)
        outcomes.append(outcome)
    significant = [o for o in outcomes if o['matching_evidence'] or o['contradictory_evidence']]
    if len(good) < 2:
        reason = 'CALIDAD_ACUSTICA_INSUFICIENTE'
        third = len(good) == 1  # tres fallos/silencios no aportan atribución
    elif any(o['state'] == 'CONTRADICTORIO' for o in outcomes):
        reason, third = 'LECTURAS_CONTRADICTORIAS', True
    elif significant:
        reason = ('COINCIDENCIA_SIN_ATRIBUCION' if any(o['state'] == 'SIN_ATRIBUCION' for o in significant)
                  else 'CONSENSO_DE_HECHOS')
        third = False  # otra decodificación no acredita un hablante ausente
    else:
        reason = 'INFORMACION_INSUFICIENTE'
        cues=[unresolved_cues(a.get('text'),extraction_purpose)for a in good]
        third=bool(cues and any(c!=cues[0]for c in cues[1:]))
    # Coincidir en un hecho no oculta otra cifra/fecha/riesgo que solo una lectura ve.
    signatures = [{(f['rule'], digest(f['value']), f['polarity']) for f in row} for row in observations]
    if len(good) >= 2 and signatures and any(row != signatures[0] for row in signatures[1:]):
        third = True
    return {'purpose': purpose, 'validator_revision': VALIDATOR_REVISION, 'rules': outcomes,
            'reason_code': reason, 'third_recommended': third, 'usable_readings': len(good),
            'same_audio_correlated_readings': True, 'independent_sources': 1,
            'acoustic_quality': ['UTILIZABLE' if a in good else 'NO_UTILIZABLE' for a in attempts]}
