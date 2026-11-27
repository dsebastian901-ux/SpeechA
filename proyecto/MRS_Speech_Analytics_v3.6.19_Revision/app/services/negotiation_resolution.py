"""One active negotiation object for analytics, facts and focal listening.

Financial policy is applied by Analytics afterwards. This resolver selects
evidence; it does not approve calls, fill terms from Excel or change amounts.
"""
from copy import deepcopy
import re


def component_index(text):
    from app.services.conversation_evidence import normalize
    match=re.search(r'\b(primer[oa]?|segund[oa]|tercer[oa]?) (?:pago|abono|parcialidad)\b',normalize(text))
    return (1 if match[1].startswith('primer')else 2 if match[1].startswith('segund')else 3)if match else None


def resolve_negotiation(text, segments=(), call_date=None):
    from app.services.conversation_evidence import payment_commitment, normalize
    from app.services.accepted_schedule_evidence import accepted_two_part_schedule
    from app.services.payment_lifecycle import financial_response_events

    commitment = payment_commitment(text, segments)
    schedule = accepted_two_part_schedule(text, segments, call_date)
    superseded = False
    if schedule['confirmed']:
        evidence = normalize(commitment.get('evidence') or '')
        superseded = bool(commitment.get('accepted') and evidence
                          and normalize(text).rfind(evidence) > schedule['end'])
        if superseded:
            schedule = dict(schedule, confirmed=False)
        else:
            commitment = {'accepted': True, 'declined': False, 'conditional': False,
                'evidence': schedule['evidence'], 'position': schedule['position'],
                'contextual_confirmation_events': []}

    # Bind all terms to the very same accepted event. A former installment
    # offer must not become the amount of a later single-payment agreement.
    terms = None
    if commitment.get('accepted') and not schedule['confirmed']:
        terms = next((e for e in reversed(financial_response_events(text, segments))
                      if e.get('method') == 'RESPUESTA_ACTUAL_DE_IMPORTE_Y_FECHA'
                      and e['position'] == commitment.get('position')), None)

    if terms is None and commitment.get('accepted') and not schedule['confirmed']:
        # Primary interpretation may bind an immediately accepted recap. The
        # Medium fact extractor still applies its stricter attribution guard.
        from app.services.current_payment_amounts import explicit_current_amounts
        event=next((e for e in reversed(financial_response_events(text,segments))
                    if e['position']==commitment.get('position')),None)
        amounts=[a for a in explicit_current_amounts(text,segments)
                 if a['position']==commitment.get('position')
                 and a['method']=='IMPORTE_DE_OFERTA_INMEDIATA_ACEPTADA']
        if event and len({a['amount']for a in amounts})==1:
            terms=dict(event,amount=amounts[0]['amount'])

    component=None
    if terms and component_index(terms['offer']):
        index=component_index(terms['offer'])-1
        # A component confirmation updates that component, not the whole debt.
        # Only a complete, already accepted calendar can supply the other parts.
        if schedule.get('amounts') and index<len(schedule['amounts']) and len(schedule.get('dates',[]))==len(schedule['amounts']):
            from app.services.analytics_service import AnalyticsService
            from decimal import Decimal
            parsed=AnalyticsService._extract_payment_promise_date_details(terms['date_evidence'],call_date.isoformat()if call_date else None)
            if parsed.get('date')is not None:
                previous=deepcopy(schedule)
                schedule=deepcopy(schedule)
                schedule['source_start']=max(0,normalize(text).rfind(normalize(schedule['evidence']),0,schedule['end']))
                schedule['amounts'][index]=terms['amount']
                schedule['dates'][index]=dict(schedule['dates'][index],date=parsed['date'].isoformat(),text=parsed['text'],evidence=terms['evidence'])
                schedule.update(confirmed=True,total=float(sum(Decimal(str(v))for v in schedule['amounts'])),
                    evidence=schedule['evidence']+' '+terms['evidence'],position=terms['position'],end=terms['end'])
                component={'installment':index+1,'previous_amount':previous['amounts'][index],'amount':terms['amount']}
                commitment={'accepted':True,'declined':False,'conditional':False,'evidence':schedule['evidence'],
                    'position':schedule['position'],'contextual_confirmation_events':[]}
                superseded=False
        terms=None  # never publish a partial component as a complete single plan

    kind = ('SCHEDULE' if schedule['confirmed'] else 'SINGLE' if terms else 'ACCEPTED' if commitment.get('accepted') else
            'DECLINED' if commitment.get('declined') else
            'CONDITIONAL' if commitment.get('conditional') else 'UNRESOLVED')
    # A referential acceptance ("acepto el convenio completo") needs the
    # surrounding plan. It is not a standalone replacement payment.
    standalone=False
    if kind=='ACCEPTED':
        from app.services.payment_lifecycle import DATE
        from app.services.operational_outcome_resolution import amount_confirmed_for_agreement
        evidence=commitment.get('evidence')or''
        standalone=bool(DATE.search(normalize(evidence)) and re.search(
            r'\b(?:me comprometo a|voy a) (?:pagar|depositar|abonar)|\b(?:pagare|depositare|abonare)\b',normalize(evidence))
            and amount_confirmed_for_agreement(evidence,[],commitment))
    if standalone and not schedule.get('amounts'):
        # An incomplete earlier installment offer is not a validated calendar
        # that this scalar confirmation can safely replace. Preserve its scope
        # until the existing completeness/conflict checks distinguish a new
        # whole payment from a component of that unconfirmed offer.
        from app.services.installment_validation import installment_plan
        prior = normalize(text)[:commitment.get('position') or 0]
        if installment_plan(prior, []).get('amounts'):
            standalone = False
    from app.services.negotiation_chronology import route_uncertainty
    channel_only=route_uncertainty(commitment.get('evidence')or'')
    scoped=(kind in {'SINGLE','SCHEDULE','DECLINED','CONDITIONAL'} or standalone) and not channel_only
    plan_text=commitment['evidence'] if scoped else text
    evidence_at=normalize(text).rfind(normalize(commitment.get('evidence')or''))
    evidence_end=evidence_at+len(normalize(commitment.get('evidence')or'')) if evidence_at>=0 else None
    return {'kind': kind, 'channel_only_intention':channel_only, 'plan_scope_proven':scoped, 'plan_text':plan_text, 'commitment': deepcopy(commitment), 'schedule': deepcopy(schedule),
            'component_update':component, 'single_terms': deepcopy(terms), 'superseded_schedule': superseded,
            'position': commitment.get('position'),
            'start': (schedule.get('source_start',max(0,normalize(text).rfind(normalize(schedule['evidence']),0,schedule['end']))) if schedule['confirmed'] else
                      terms.get('offer_position') if terms else commitment.get('position')),
            'end': (schedule.get('end') if schedule['confirmed'] else
                    terms.get('end') if terms else evidence_end)}
