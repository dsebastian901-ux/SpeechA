"""Regresión sintética de bloqueos detectados en la revisión del lote pendiente."""
import json
from pathlib import Path

import pytest
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import completed_payment, payment_commitment, payment_places
from app.services.reported_payment_amounts import reported_amounts


def analyze(text, **context):
    return A.analyze_transcription(TranscriptionModel('example.ogg','example.ogg',text,
        duration_seconds=95), {'fecha':'2026-10-22','asignacion':'1PV','corte':'25',
        'vencimiento':'2026-10-25','pago_minimo':'1200','saldo_total':'5029', **context})


@pytest.mark.parametrize('number',['55-22, 01-08, 80','10-40-2-3-7-8','55/22/01/08/80'])
def test_phone_and_agreement_digits_do_not_replace_payment_date(number):
    value=A._extract_payment_promise_date_details(
        'Voy a pagar mañana. Envíe su comprobante de pago al WhatsApp '+number+'.','2026-10-22')
    assert value['date'].isoformat()=='2026-10-23'


def test_numeric_date_with_payment_introduction_is_still_supported():
    value=A._extract_payment_promise_date_details('Confirmo el pago para el 24/10.','2026-10-22')
    assert value['date'].isoformat()=='2026-10-24'


@pytest.mark.parametrize('text',[
    'El pago mínimo es de 1200. ¿Cuándo se venció el pago? El 18. Estamos a 22.',
    'Su saldo vencido es de 5029. El mínimo es de 1200 para el día de mañana.',
    'La tarjeta terminación 8888. Le requiere un pago de 1200 mañana.',
])
def test_calendar_or_previous_card_does_not_hide_the_real_payment_amount(text):
    n=analyze('Habla MRS. Soy yo. '+text).metadata['negotiation_validation']
    assert n['monto_detectado']==1200
    assert n['saldo_informado_detectado'] not in {18,22,8888}


@pytest.mark.parametrize('amount,value',[
    ('mil doscientos',1200),('dos mil treinta',2030),('mil 216',1216),
])
def test_dictated_amount_without_pesos_is_bound_to_direct_financial_clause(amount,value):
    n=analyze('Habla MRS. Soy yo. Le requiere un pago de '+amount+' para mañana.',
        pago_minimo='1000').metadata['negotiation_validation']
    assert n['monto_detectado']==value


@pytest.mark.parametrize('text',[
    'Sí, hoy lo hago.', 'Hoy depósito.', 'Mañana lo realizo.',
    'Confirmo el pago de 1200. Sí.',
])
def test_explicit_current_payment_acceptance(text):
    assert payment_commitment(text)['accepted']


@pytest.mark.parametrize('text',[
    'Gestor: Hoy lo hago.',
    'Confirmo el pago de 1200. Sí, pero no puedo.',
    'Confirmo el pago realizado de 1200. Sí.',
    '¿Le dicto el número de WhatsApp? Sí.',
    'Hoy no lo hago.',
])
def test_agent_historical_payment_or_phone_yes_is_not_future_acceptance(text):
    assert not payment_commitment(text)['accepted']


def test_repeating_a_phone_does_not_cancel_a_firm_payment():
    result=payment_commitment('Voy a pagar mañana. Es el WhatsApp 5512345678, me lo podría repetir, de favor.')
    assert result['accepted']


@pytest.mark.parametrize('text,value',[
    ('Ya hice el pago, ya, señorita, de mil pesos.',1000),
    ('Yo realicé mi pago de mil 216 pesos.',1216),
    ('Fui a abonar 1500 pesos.',1500),
    ('El pago ya lo hice. ¿Sobre qué cantidad se realizó? De 2420 pesos.',2420),
])
def test_prior_amounts_with_natural_introduction(text,value):
    result=reported_amounts(text,completed_payment(text))
    assert result['total']==value


def test_repeated_historic_payment_does_not_double_as_new_complement():
    n=analyze('Habla MRS. Soy yo. Ya pagué 2420 pesos. '
        'Envíe su comprobante de pago de 2420 pesos por WhatsApp.',
        estatus_grabacion='CONVENIO').metadata['negotiation_validation']
    assert n['prior_payment_total']==2420
    assert not n['multipago_detectado']
    assert n['monto_detectado']!=4840


def test_unaccepted_future_instruction_is_not_approved_as_receipt_followup():
    a=analyze('Habla MRS. Soy yo. Ya pagué hace tres meses. '
        'Sería que realice el pago de 1200 pesos. Envíe su comprobante por WhatsApp.',
        estatus_grabacion='CONVENIO')
    assert a.metadata['negotiation_validation']['unaccepted_new_payment_instruction']
    assert a.metadata['final_result']=='REVISAR'


def test_negated_partial_warning_does_not_generate_partial_penalty():
    a=analyze('Habla MRS. Soy yo. Puede pagar 1200 hoy. '
        'De preferencia completo para que no se vaya a tomar como un pago parcial. '
        'Hoy lo hago. Puede pagar en Kiosko o en Tiendas 3B. Envíe el comprobante por WhatsApp.',
        estatus_grabacion='CONVENIO')
    assert 'PEN015' not in {p['id'] for p in a.metadata['penalties']}
    assert a.metadata['final_result']=='APROBADO'


def test_real_partial_without_explanation_keeps_its_penalty():
    a=analyze('Habla MRS. Soy yo. Puede hacer un pago parcial de 500 pesos. Hoy lo hago.',
        estatus_grabacion='CONVENIO')
    assert 'PEN015' in {p['id'] for p in a.metadata['penalties']}
    assert a.metadata['final_result']!='APROBADO'


CATALOG={'KIOSKO':['kiosko'],'3B':['tiendas 3b'],'GUADALAJARA':['farmacia guadalajara']}


def test_payment_place_list_can_answer_a_question_in_previous_sentence():
    found=payment_places('¿Dónde puedo realizar el pago? En Kiosko o tiendas 3B.',(),CATALOG)
    assert {e['place'] for e in found}=={'KIOSKO','3B'}


def test_negation_of_one_place_does_not_negate_a_new_affirmative_clause():
    found=payment_places('No puede pagar en farmacia Guadalajara, puede pagar en Kiosko o en tiendas 3B.',(),CATALOG)
    assert {e['place'] for e in found}=={'KIOSKO','3B'}


@pytest.mark.parametrize('text',[
    'Su tarjeta es de tiendas 3B. Kiosko.',
    'Cliente: Puedo pagar en Kiosko o en tiendas 3B.',
    'No puede pagar en Kiosko ni en tiendas 3B.',
])
def test_origin_customer_and_negated_places_do_not_count(text):
    assert not payment_places(text,(),CATALOG)


@pytest.mark.parametrize('text',[
    '¿Me puedes comunicar a Elena Ruiz? ¿De dónde habla? De Corporativo MRS. Ah, díganme.',
    '¿Me comunican con Pedro Vega? ¿De parte de quién? De Corporativo MRS. Sí, dígame.',
])
def test_identity_can_follow_bounded_company_presentation(text):
    from app.services.conversation_evidence import holder_confirmation
    assert holder_confirmation(text)['confirmed']


@pytest.mark.parametrize('text',[
    '¿Me comunican con Pedro Vega? ¿De parte de quién? De Corporativo MRS, se lo comunico. Dígame.',
    '¿Me puedes comunicar a Elena Ruiz? ¿De dónde habla? De Corporativo MRS. Sí, se la paso.',
    '¿Me comunican con Pedro Vega? ¿De parte de quién? De Corporativo MRS. Gestor: Sí, dígame.',
])
def test_company_presentation_does_not_turn_a_handoff_or_agent_into_holder(text):
    from app.services.conversation_evidence import holder_confirmation
    assert not holder_confirmation(text)['confirmed']


def test_bare_day_in_current_month_is_supported():
    value=A._extract_payment_promise_date_details('Confirmo el pago de 1500 el día 24.','2026-10-22')
    assert value['date'].isoformat()=='2026-10-24'


def test_phone_alone_does_not_confirm_payment_date():
    n=analyze('Habla MRS. Soy yo. Mande su comprobante al WhatsApp 55-22-01-08-80.').metadata['negotiation_validation']
    assert not n['payment_date_confirmed'] and n['promise_date'] is None


def test_uncertain_reported_amount_does_not_acquire_a_false_exact_total():
    text='Ya lo hice ayer. ¿Por qué cantidad lo hizo? 4700, no recuerdo, pero era 4750.'
    n=reported_amounts(text,completed_payment(text))
    assert n['review_required'] and n['total'] is None


def test_article_after_balance_does_not_become_a_one_peso_balance():
    n=analyze('Habla MRS. Soy yo. Ya pagué 1419 pesos. Ya tendría un saldo, '
        'o sea que debe enviar comprobante. Su saldo total es de 5029 pesos.').metadata['negotiation_validation']
    assert n['saldo_informado_detectado']==5029


def test_negative_confirmation_is_not_an_agreement():
    assert not payment_commitment('No confirmo el pago de 1200. Sí.')['accepted']


def test_third_payment_proposal_is_not_summed_as_if_all_three_were_agreed():
    n=analyze('Habla MRS. Soy yo. Un pago inicial de 500 pesos, '
        'otro de 600 pesos, perdón de 1100 pesos la semana siguiente.',
        estatus_grabacion='CONVENIO',pago_minimo='1600').metadata['negotiation_validation']
    assert n['total_multipago']!=2200
    assert n['monto_detectado']!=2200


def test_regression_guard_requires_real_current_agreement_not_cached_approval():
    from copy import deepcopy
    from tools.regression_checkpoints import verified_current_agreement
    a=analyze('Habla MRS. ¿Hablo con Elena Ruiz? Sí. Puede pagar 1200 mañana. '
        'Voy a pagar mañana. Puede pagar en Kiosko o en Tiendas 3B. '
        'Envíe comprobante por WhatsApp.',estatus_grabacion='CONVENIO')
    assert verified_current_agreement(a.metadata)
    changes=[('status_validation','evidence',''),('status_validation','matches',None),
             ('negotiation_validation','valid',False),('negotiation_validation','promise_date','2026-11-01'),
             ('negotiation_validation','unaccepted_new_payment_instruction',True),
             ('privacy_validation','review_required',True),('contact_validation','confirmed',False)]
    for group,key,value in changes:
        m=deepcopy(a.metadata);m[group][key]=value
        assert not verified_current_agreement(m),(group,key)


def test_unrelated_negative_statement_does_not_erase_real_partial_penalty():
    a=analyze('Habla MRS. Soy yo. No pude ayer, hoy realizaré un pago parcial de 500 pesos.',
        estatus_grabacion='CONVENIO')
    assert 'PEN015' in {p['id'] for p in a.metadata['penalties']}


def test_impersonal_negated_payment_places_remain_excluded():
    assert not payment_places('No se puede pagar en Kiosko ni en tiendas 3B.',(),CATALOG)
