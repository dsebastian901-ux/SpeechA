"""Términos propios corroborados por lecturas vinculadas al mismo audio.

No atribuye voces por repetir texto, ni convierte una propuesta y un «sí»
aislado en aceptación. Reutiliza las respuestas actuales de importe y fecha.
"""
from datetime import date
import re


def extract_payment_plans(text,segments=(),relation=None):
    from app.services.payment_lifecycle import financial_response_events
    from app.services.conversation_evidence import payment_commitment,normalize
    from app.services.contact_dialogue_resolution import declared_intermediary
    from app.services.contextual_identity_evidence import nonholder_counter_evidence,proxy_account_evidence
    from app.services.analytics_service import AnalyticsService as A
    if (declared_intermediary(text,segments)['confirmed'] or nonholder_counter_evidence(text,segments)
            or proxy_account_evidence(text,segments)):
        return []
    call=A._parse_context_date((relation or{}).get('fecha'))
    from app.services.negotiation_resolution import resolve_negotiation
    active=resolve_negotiation(text,segments,call)
    schedule=active['schedule']
    if schedule['confirmed']:
        return [{'value':{'amount':schedule['total'],'date':schedule['dates'][-1]['date'],
                          'amounts':schedule['amounts'],'dates':[{'installment':d['installment'],'date':d['date']}for d in schedule['dates']]},'text':schedule['evidence']}]
    commitment=active['commitment']
    if not commitment.get('accepted')or commitment.get('declined')or commitment.get('conditional'):return []
    call=A._parse_context_date((relation or{}).get('fecha'))
    if call is None:return []
    plans=[]
    for event in ([active['single_terms']] if active['single_terms'] else []):
        if event.get('method')!='RESPUESTA_ACTUAL_DE_IMPORTE_Y_FECHA':continue
        if event.get('position')!=commitment.get('position'):continue
        detail=A._extract_payment_promise_date_details(event['date_evidence'],call.isoformat())
        day=detail.get('date')
        if day is None or day<call:continue
        if (day-call).days>90 and not re.search(r'\b20\d{2}\b',normalize(event['date_evidence'])):continue
        plans.append({'value':{'amount':event['amount'],'date':day.isoformat()},'text':event['evidence']})
    return plans


def confirmed_payment_plan(context,*,contact_type,commitment,completed_payment=False):
    from app.services.context_evidence_policy import confirmed_fact
    if (contact_type!='TITULAR' or context.get('model')!='Faster-Whisper:medium'
            or completed_payment or context.get('risks')
            or any(context.get(k)for k in ('third_listening_pending','third_listening_failed','third_listening_insufficient')) or context.get('contradictory_fact_rules')
            or context.get('primary_conflicting_fact_rules')):
        return None
    if any(g.get('purpose')=='financial' and g.get('usable_readings',0)<2
           for g in context.get('fact_validations')or[]):
        return None
    fact=confirmed_fact(context,'PAYMENT_PLAN')
    if not fact:return None
    if commitment.get('declined')or commitment.get('conditional'):
        # A positive decode of the same refused exchange is a contradiction.
        # Only a located later exchange may supersede that source decision.
        declined_end=context.get('source_decision_end')
        starts=[e.get('reading_start')for e in fact.get('matching_evidence',[])]
        if declined_end is None or not starts or any(t is None or t<declined_end for t in starts):return None
    evidence=fact['matching_evidence'];values=[e['value']for e in evidence]
    if not values:return None
    value=values[0]
    if not isinstance(value,dict)or any(v!=value for v in values):return None
    # La huella, archivo, cuenta y calidad ya los verifica validate(); dos
    # lecturas deben confirmar el mismo plan y conservar la procedencia.
    if len({e.get('listening_index')for e in evidence})<2:return None
    return {'amount':value['amount'],'date':date.fromisoformat(value['date']),
            'amounts':value.get('amounts',[]),'dates':value.get('dates',[]),
            'evidence':evidence[0]['text'],'readings':evidence,'source':'LOCAL_AUDIO_CONTEXT',
            'human_verified':False,'speaker_assignment':'CONTEXTUAL_NO_ACOUSTIC_DIARIZATION'}
