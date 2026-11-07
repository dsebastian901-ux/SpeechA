from datetime import date
import pytest
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import normalize
from app.services.payment_reference_validation import find_reference
from app.services.payment_instruction_validation import transfers_only_reported_or_asked
from app.services.accepted_schedule_evidence import accepted_two_part_schedule
from app.services.treatment_evidence import mistreatment_reports
from app.services.dialogue_evaluation import scan_dialogue,pending_status
from app.services.operational_script_evidence import remaining_payment_proposals
from app.models.transcriptions import TranscriptionModel


@pytest.mark.parametrize('ending',['44-55. 44-55','4455, 4455','44 55. 44 55'])
def test_repeated_explicit_last_four_is_not_a_truncated_sixteen_digit_reference(ending):
    r=find_reference('Son los 16 dígitos de su tarjeta. No, le doy únicamente la terminación '+ending)
    assert not r['requires_review'] and not r['ambiguous']
    assert r['excluded_explicit_terminations'][0]['termination']=='4455'


def test_eight_digits_without_a_last_four_qualification_remain_uncertain():
    assert find_reference('Los 16 dígitos de la tarjeta son 11 22 33 44.')['requires_review']
    assert find_reference('La referencia es 11 22 11 22.')['requires_review']


def test_full_reference_after_a_termination_is_still_compared_in_full():
    r=find_reference('La tarjeta termina 4455. Los 16 dígitos son 11 22 33 44 55 66 77 88.','1122334455667788')
    assert r['detected'] and not r['incorrect']


@pytest.mark.parametrize('text',[
    '¿Pero lo pagó por medio de transferencia? No, en efectivo en tienda.',
    'Yo hice una transferencia ayer. Envíe la captura de pantalla.',
    'Normalmente los pagos los vengo haciendo vía transferencia. Envíe la captura.',
])
def test_historical_or_questioned_payment_channel_is_not_a_new_bank_instruction(text):
    assert transfers_only_reported_or_asked(text)


@pytest.mark.parametrize('text',[
    'Puede transferir el pago mañana.',
    '¿Puedo hacer el pago por transferencia mañana?',
    'Ya hice una transferencia. Deposite en la cuenta bancaria 123456789012345678.',
    'El pago es por transferencia.',
])
def test_new_or_unexplained_transfer_does_not_receive_historical_exemption(text):
    assert not transfers_only_reported_or_asked(text)


def test_another_monthly_payment_is_not_the_current_promise():
    text=('Para poner al corriente su cuenta realice un pago de 2000 pesos y ya tendríamos '
          'hasta el tres de diciembre para realizar otro pago. El pago actual sería al martes 10 a más tardar.')
    r=A._extract_payment_promise_date_details(text,'2026-11-05')
    assert r['date']==date(2026,11,10)
    assert 'diciembre' not in r['text']


def test_explicit_payment_antecedent_is_kept_across_polite_request_words():
    text='Este pago le pido de favor si lo puede realizar a más tardar para el día 8. Ok.'
    assert A._extract_payment_promise_date(text,'2026-11-04')==date(2026,11,8)


def test_receipt_telephone_and_time_do_not_become_payment_dates():
    assert A._extract_payment_promise_date('Este pago ya se hizo. El comprobante por WhatsApp se recibe el día 8.','2026-11-04') is None


@pytest.mark.parametrize('text',[
    'Reporté compras no reconocidas. Nunca me avisaron de la investigación.',
    'Los de cobranza son muy preputantes.',
    'La tarjeta me la ofreció un promotor, me engañó.',
    'Solicité aclaración y no me quisieron dar el folio.',
])
def test_missed_prior_service_complaints_are_not_lost(text):
    assert mistreatment_reports(text,[],[])


@pytest.mark.parametrize('text',[
    'No es cierto que me engañó el promotor de la tarjeta.',
    'Gestor: Los de cobranza son muy preputantes.',
    'La tarjeta no tiene compras no reconocidas.',
])
def test_denials_agent_words_and_plain_disputes_are_not_service_complaints(text):
    assert not mistreatment_reports(text,[],[])


def schedule_text(first='1200',second='4800',day='16'):
    return ('El segundo monto más para el día '+day+' sería de '+second+' pesos. '
        'Entonces, sería el '+first+' pesos el día de hoy? Sí, ahorita paso a pagar. '
        'Y sería uno más por '+second+'. Sí. '
        'Solo que si paga todo mañana serían 5500. Lo voy a intentar. '
        '¿No puedo pagar con otra tarjeta de crédito? No, solo de débito.')


@pytest.mark.parametrize('first,second',[('1200','4800'),('mil','cinco mil'),('1.200','4.800')])
def test_two_accepted_payments_survive_an_optional_unconfirmed_single_payment(first,second):
    r=accepted_two_part_schedule(schedule_text(first,second),[],date(2026,11,5))
    assert r['confirmed']
    assert r['dates'][0]['date']=='2026-11-05' and r['dates'][1]['date']=='2026-11-16'
    assert r['total']==6000 and not r['human_verified']


@pytest.mark.parametrize('change',[
    lambda s:s.replace('Sí, ahorita paso a pagar.','No, no puedo.'),
    lambda s:s.replace('para el día 16','sin fecha'),
    lambda s:s+' No voy a poder, cancela el convenio.',
    lambda s:s.replace('Entonces, sería','Por ejemplo, entonces, sería'),
    lambda s:s.replace('1200 pesos','2 pesos'),
])
def test_incomplete_hypothetical_or_withdrawn_schedule_is_not_promoted(change):
    r=accepted_two_part_schedule(change(schedule_text()),[],date(2026,11,5))
    assert not r['confirmed']


def test_known_agent_cannot_accept_the_customer_schedule():
    text=schedule_text();start=normalize(text).find('si, ahorita')
    # A role-labelled source remains protected even with the same words.
    text=text.replace('Sí, ahorita','Gestor: Sí, ahorita')
    assert not accepted_two_part_schedule(text,[],date(2026,11,5))['confirmed']


def test_historical_payment_is_not_a_new_under_minimum_proposal():
    r=A.calculate_basic_compliance('Habla MRS. Soy yo. Ya pagué 1000 pesos ayer. Envíe su comprobante por WhatsApp.',
        {'estatus_grabacion':'CONVENIO','pago_minimo':2000,'saldo_total':5000,'asignacion':'1PV','fecha':'2026-11-05'})
    n=r['negotiation_validation']
    assert n['payment_confirmation_case'] and not n['is_negotiation']
    assert 'MONTO MENOR' not in n['validacion_monto']
    assert not n['hard_invalid']


def test_new_agreed_under_minimum_payment_still_requires_financial_review():
    r=A.calculate_basic_compliance('Habla MRS. Soy yo. Confirma su pago de 1000 pesos mañana? Sí.',
        {'estatus_grabacion':'CONVENIO','pago_minimo':2000,'saldo_total':5000,'asignacion':'1PV','fecha':'2026-11-05','corte':20,'vencimiento':'2026-11-20'})
    assert r['negotiation_validation']['valid'] is False


def test_dispute_guidance_does_not_require_a_collection_offer_and_keeps_the_complaint():
    text=('Habla MRS. Soy yo. No reconozco esas compras de 1000 pesos en mi tarjeta. '
        'Reporté compras no reconocidas y nunca me avisaron. Llame a servicio a clientes '
        'para solicitar un folio de aclaración por cargos no reconocidos.')
    r=A.calculate_basic_compliance(text,{'estatus_grabacion':'NO DEFINE FECHA DE PAGO','pago_minimo':2000,'saldo_total':5000})
    ids={p['id'] for p in r['penalties']}
    assert r['negotiation_validation']['dispute_guidance']
    assert 'PEN_SIN_INTENTO_NEGOCIACION' not in ids and 'PEN_QUEJA_MALTRATO' in ids


@pytest.mark.parametrize('text,expected',[
    ('Yo no les pedí la tarjeta, me la estuvieron ofreciendo y les dije que no quería.',True),
    ('No es cierto que no les pedí la tarjeta.',False),
    ('Gestor: Yo no les pedí la tarjeta y me la estuvieron ofreciendo.',False),
])
def test_unsolicited_card_complaint_preserves_speaker_and_negation(text,expected):
    assert bool(mistreatment_reports(text,[],[])) is expected


def test_accepted_high_mora_schedule_is_valid_in_call_month_and_keeps_place_deduction():
    text='Habla MRS. Soy yo. Para liquidar su cuenta. '+schedule_text()+' Envíe su comprobante por WhatsApp.'
    context={'estatus_grabacion':'CONVENIO','pago_minimo':6000,'saldo_total':15000,'asignacion':'C1',
             'fecha':'2026-11-05','corte':20,'vencimiento':'2026-12-31'}
    r=A.calculate_basic_compliance(text,context)
    n=r['negotiation_validation'];ids={p['id'] for p in r['penalties']}
    assert n['accepted_schedule']['confirmed'] and n['monto_detectado']==6000
    assert n['promise_date']=='2026-11-16' and n['valid']
    assert 'PEN_CONV_LUGARES' in ids and 'PEN015' not in ids and 'PEN009' not in ids
    assert r['score']==80


def missing_date_analysis():
    t=TranscriptionModel.from_dict({'archivo':'source.ogg','texto':'Habla MRS. Soy yo. Puede realizar un pago de 3000 pesos para regularizar su cuenta.', 'duracion_segundos':150})
    return A.analyze_transcription(t,{'estatus_grabacion':'CONVENIO','pago_minimo':2500,'saldo_total':5000,
        'asignacion':'1PV','fecha':'2026-11-05','corte':20,'vencimiento':'2026-11-20'})


def test_definitive_low_score_rejection_does_not_require_review_just_for_missing_date():
    a=missing_date_analysis()
    assert a.compliance_score<80
    d=A.shared_quality_decision(a.metadata,a.compliance_score,duration_seconds=150)
    assert d['clasificacion']=='NO_APROBADO_MENOR_80'
    assert 'No se pudo confirmar la fecha de pago.' in d['motivo']
    assert a.metadata['negotiation_validation']['valid'] is False


@pytest.mark.parametrize('risk',[
    {'privacy_validation':{'review_required':True}},
    {'financial_review_validation':{'review_required':True}},
    {'wait_validation':{'review_required':True}},
    {'quality_checks':{'queja_maltrato_detectada':True}},
])
def test_missing_date_rejection_never_hides_other_safety_uncertainty(risk):
    a=missing_date_analysis();a.metadata.update(risk)
    assert A.shared_quality_decision(a.metadata,a.compliance_score,duration_seconds=150)['clasificacion']=='REVISAR'


@pytest.mark.parametrize('text',[
    'Necesito hacer el pago. No lo voy a revisar primero.',
    'El pago, no, no, no lo voy a revisar el día.',
])
def test_negated_deliberation_is_not_a_confirmed_pending_payment_decision(text):
    assert pending_status(scan_dialogue(text),{}) is None


@pytest.mark.parametrize('text',[
    'Me habló una señorita y me habló bien grosera.',
    'Ya lo pagué. Ya le estoy recibiendo las llamadas a cada rato.',
    'Solicite su estado de cuenta al banco. Ya fui y tampoco me lo dan.',
])
def test_prior_rude_attention_and_repeated_calls_after_payment_remain_blocking(text):
    assert mistreatment_reports(text,[],[])


@pytest.mark.parametrize('text',[
    'No es cierto que me habló bien grosera.',
    'Gestor: Ya lo pagué. Gestor: Ya le estoy recibiendo las llamadas a cada rato.',
])
def test_denied_or_agent_reports_do_not_create_a_customer_complaint(text):
    assert not mistreatment_reports(text,[],[])


def test_reported_payment_does_not_waive_validation_of_remaining_scheduled_payments():
    text='Ya pagué ayer. Ya nada más quedaría el día 7 por 500 y el día 16 por el mismo monto, ¿verdad? Sí.'
    proposals=remaining_payment_proposals(text)
    assert proposals and proposals[0]['method']=='CALENDARIO_RESTANTE_REQUIERE_VALIDAR_TERMINOS'


@pytest.mark.parametrize('text',[
    'Ya pagué ayer. Ya mandé el comprobante y espero su mensaje de recibido.',
    'Titular: Me dijeron que quedaría el día 7 por 500 y el día 16 por el mismo monto.',
])
def test_pure_followup_or_customer_quote_does_not_create_new_scheduled_instruction(text):
    assert not remaining_payment_proposals(text)
