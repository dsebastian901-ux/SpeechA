"""Causas generales r64. Ejemplos sintéticos, sin datos del lote de clientes."""
from copy import deepcopy

import pytest

from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel
from app.services.conversation_evidence import holder_confirmation,assess_home_recovery_warning
from app.services.contact_evidence_graph import nonholder_context
from app.services.payment_instruction_validation import transfer_is_option_listing
from app.services.payment_lifecycle import financial_response_events
from app.services.payment_intent_frames import payment_frames
from app.services.current_payment_amounts import explicit_current_amounts
from app.services.medium_review_plan import plan_for_item,add_medium_plan_sheet


@pytest.mark.parametrize('opening',[
    'Qué uso con Marina Robles? Sí.',
    'Buen día Mecumonico con Marina Robles. Sí.',
    'No puede comunicar con Marina Robles? Sí, diga.',
    'Me comunico con Marina Robles, el motivo de la llamada es su pago.',
])
def test_nominal_variants_require_personal_account_context(opening):
    text=opening+' Habla MRS. Yo no tengo dinero para pagar mi tarjeta.'
    assert holder_confirmation(text)['confirmed']


@pytest.mark.parametrize('suffix',[
    'Soy su hermana y no está.', 'Pago por mi esposo.',
    'No la conozco, es número equivocado.', 'Le paso al titular.',
])
def test_nominal_variants_never_overrule_an_intermediary(suffix):
    text='Mecumonico con Marina Robles. Habla MRS. '+suffix+' No tengo dinero para pagar.'
    assert not holder_confirmation(text)['confirmed']


def test_nominal_variant_and_isolated_yes_do_not_identify_holder():
    assert not holder_confirmation('Qué uso con Marina Robles? Sí. Habla MRS.')['confirmed']


@pytest.mark.parametrize('reply',[
    'Yo creo que la liquido a final de mes.',
    'Voy a saldar el total de la tarjeta.',
    'Hago el pago y envío el comprobante.',
    'Yo tenía ese pago pendiente porque según yo no debía nada.',
])
def test_own_financial_intent_proves_identity_not_a_firm_payment(reply):
    text='Me comunico con Marina Robles, el motivo de mi llamada es su tarjeta. Habla MRS. '+reply
    assert holder_confirmation(text)['confirmed']


def test_searching_payment_date_does_not_declare_an_intermediary():
    text=('¿Me comunica con Marina Robles? Sí, dígame. Habla MRS. Mi aplicación muestra mi pago. '
          '¿Recuerda la fecha del pago? No, pero si me permite lo busco.')
    assert not nonholder_context(text)
    assert holder_confirmation(text)['confirmed']


def test_searching_person_after_nominal_question_still_blocks_holder():
    text='¿Me comunica con Marina Robles? Sí, lo busco. Habla MRS. No tengo dinero.'
    assert nonholder_context(text)
    assert not holder_confirmation(text)['confirmed']


@pytest.mark.parametrize('reply',[
    '¿Sería un pago de 900 pesos el día de hoy? Así es.',
    'Confirma su pago por 900 para el día de mañana. Sí.',
])
def test_direct_recap_is_bound_to_immediate_acceptance(reply):
    assert financial_response_events(reply)


@pytest.mark.parametrize('reply',[
    '¿Sería un pago de 900 pesos hoy? No, no puedo.',
    '¿Sería un pago de 900 pesos hoy? Quizá, si consigo dinero.',
    'Gestor: Confirma su pago por 900 para mañana. Gestor: Sí.',
    '¿Sería el número de WhatsApp 5512345678? Sí.',
])
def test_recap_does_not_turn_refusal_condition_other_object_or_agent_into_acceptance(reply):
    assert not financial_response_events(reply)


def test_joint_amount_date_answer_confirms_only_explicit_terms():
    text=('Gestor: Me podría indicar el monto y la fecha de su pago, por favor? '
          'Titular: Sería el monto es 900, el día 20 de noviembre.')
    frames=payment_frames(text)
    assert frames and frames[-1]['accepted']
    assert {e['amount']for e in explicit_current_amounts(text)}=={900}


def test_old_payment_question_is_not_a_new_joint_amount_date_promise():
    text='¿En qué fecha y por qué monto realizó el pago ayer? Por 900 el día 19 de noviembre.'
    assert not any(f['accepted']for f in payment_frames(text))


def test_two_dated_payments_are_not_rejected_as_a_single_under_minimum_amount():
    from app.services.installment_validation import unresolved_accepted_plan
    text=('Entonces confirma pago de 500 pesos para mañana y 11500 estaría '
          'aplicando para el día lunes 23. Sí, pero mañana primero voy a depositar.')
    result=unresolved_accepted_plan(text,{'amounts':[]},[])
    assert result['review_required'] and result['expected_count']==2
    assert not unresolved_accepted_plan(text,{'amounts':[500,11500]},
        [{'date':'2026-11-21'},{'date':'2026-11-23'}])['review_required']


def test_one_payment_recap_with_balance_context_does_not_invent_a_second_payment():
    from app.services.installment_validation import unresolved_accepted_plan
    text='Confirma su pago de 900 pesos para mañana. Sí.'
    assert not unresolved_accepted_plan(text,{'amounts':[]},[])['review_required']


@pytest.mark.parametrize('venues,wording,listed',[
    (['KIOSKO'],'Alternativas: transferencia por medio de Santander, BBVA o Banamex.',True),
    (['KIOSKO'],'Mediante transferencia de BBVA.',False),
    (['KIOSKO','7-ELEVEN'],'Deposite en una cuenta personal BBVA 5551234567.',False),
])
def test_bank_listing_does_not_waive_an_actual_destination(venues,wording,listed):
    assert transfer_is_option_listing(wording,[],venues)is listed


@pytest.mark.parametrize('role,review,confirmed',[
    ('Gestor',False,True),('Titular',False,False),('',True,False),
])
def test_asset_recovery_preserves_attribution_and_all_moras(role,review,confirmed):
    text=(role+': 'if role else'')+'Los abogados van a recuperar el monto en bienes y muebles.'
    result=assess_home_recovery_warning(text,mora='5PV')
    assert result['review_required']is review
    assert result['confirmed']is confirmed


def test_reported_or_negated_asset_warning_is_not_current_agent_threat():
    for text in ['Me dijeron que los abogados van a recuperar el monto en bienes.',
                 'Los abogados no van a recuperar el monto en bienes.',
                 'No, los abogados no van a recuperar el monto en bienes.']:
        assert not assess_home_recovery_warning(text,mora='5PV')['confirmed']


def test_asset_warning_report_does_not_invent_an_early_mora_assignment():
    raw={'archivo':'sample.wav','texto':'Habla MRS. Soy yo. Los abogados van a recuperar el monto en bienes y muebles.',
         'duracion_segundos':90,'segmentos':[]}
    analysis=A.analyze_transcription(TranscriptionModel.from_dict(raw),
        {'estatus_grabacion':'NO DEFINE FECHA DE PAGO','asignacion':'C2'})
    finding=next(f for f in analysis.metadata['shared_classification']['decision_findings']
                 if f['code']=='HOME_WARNING_UNATTRIBUTED')
    assert 'domicilio o bienes'in ' '.join(finding['reasons'])
    assert '1–2 PV'not in ' '.join(finding['reasons'])


def test_minimum_after_a_balance_does_not_become_wrong_informed_balance():
    from app.services.balance_context_evidence import balance_scope
    text='Cubra 5000 que es su saldo vencido o los 2400 que es el mínimo requerido.'
    at=text.index('2400')
    assert balance_scope(text,[],at,at+4)=='MINIMO_REQUERIDO_NO_SALDO_TOTAL'


def test_own_app_consultation_does_not_accuse_agent_of_incorrect_balance():
    from app.services.balance_context_evidence import balance_scope
    text='Yo ahorita consulté saldo y tengo un saldo de 34 pesos.'
    at=text.index('34')
    assert balance_scope(text,[],at,at+2)=='CONSULTA_PERSONAL_REPORTADA_NO_SALDO_DEL_GESTOR'


def test_hypothetical_missing_peso_does_not_replace_agreed_amount():
    text=('Gestor: Habla MRS. Tengo el gusto con Marina Robles. Titular: Soy yo. '
          'Gestor: ¿Puede pagar 1500 pesos hoy? Titular: Sí, de acuerdo. '
          'Gestor: Si le llega a faltar un peso se seguirán realizando llamadas. '
          'Puede pagar en Kiosko y 7-Eleven. Envíe comprobante por WhatsApp.')
    result=A.calculate_basic_compliance(text,{'estatus_grabacion':'CONVENIO','pago_minimo':1000,
        'saldo_total':2000,'asignacion':'1PV','fecha':'2026-11-20','corte':'2026-11-25','vencimiento':'2026-11-30'})
    assert result['negotiation_validation']['monto_detectado']==1500


def test_complete_primary_complaint_closes_quality_without_false_critical():
    raw={'archivo':'sample.wav','texto':'Habla MRS. Soy yo. Ya pagué 900 pesos. Envíe comprobante. En la llamada anterior me trataron mal.',
         'duracion_segundos':90,'segmentos':[]}
    result=A.analyze_transcription(TranscriptionModel.from_dict(raw),{'estatus_grabacion':'CONVENIO','pago_minimo':800})
    assert result.metadata['shared_classification']['clasificacion']=='REVISAR'
    assert not result.metadata['critical_failures']


def test_medium_plan_uses_real_segment_bounds_without_changing_decision():
    item={'file_name':'sample.wav','result':{'texto':'Solicito su comprobante por WhatsApp.',
          'duracion_segundos':100,'segmentos':[{'texto':'Solicito su comprobante por WhatsApp.','inicio':42,'fin':49}]},
          'classification':{'clasificacion':'REVISAR','decision_findings':[{'code':'RECEIPT_UNCERTAIN','severity':'REVIEW','reasons':['Confirmar petición y emisor']} ]},
          'analytics_metadata':{}}
    original=deepcopy(item);plan=plan_for_item(item)
    assert plan and plan[0]['start']==39 and plan[0]['end']==52
    assert plan[0]['required_model']=='medium'and plan[0]['execution']=='NO_EJECUTADO'
    assert item==original


def test_medium_plan_marks_missing_timestamps_instead_of_inventing_them():
    item={'file_name':'sample.wav','result':{'texto':'La cuenta está pendiente.'},
          'classification':{'clasificacion':'REVISAR','decision_findings':[{'code':'CARD_REFERENCE','severity':'REVIEW','reasons':['Confirmar dígitos']}]}}
    plan=plan_for_item(item)
    assert plan[0]['start']is None and plan[0]['end']is None
    assert plan[0]['location_basis']=='SIN_MARCAS_ASR_SUFICIENTES_PARA_UBICAR'


def test_medium_wait_window_covers_full_65_seconds_and_does_not_certify_silence():
    item={'file_name':'sample.wav','result':{'texto':'Un momento. Gracias.','duracion_segundos':100},
          'classification':{'clasificacion':'REVISAR','decision_findings':[{'code':'WAIT_WITHOUT_RESUMPTION','severity':'REVIEW','reasons':['Comprobar pausa']}]},
          'analytics_metadata':{'wait_validation':{'intervals':[{'start':20,'end':85}]}}}
    plan=plan_for_item(item)
    assert plan[0]['start']==17 and plan[0]['end']==88
    assert 'NO_PRUEBA_SILENCIO_ACUSTICO'in plan[0]['location_basis']


def test_medium_plan_does_not_replace_missing_excel_relation_with_asr():
    item={'classification':{'clasificacion':'SIN_RELACION_EXCEL','decision_findings':[
        {'code':'UNIDENTIFIED_CONTACT','severity':'REVIEW','reasons':['Falta relación']}]},
        'result':{'duracion_segundos':90,'texto':'Buen día.'}}
    assert plan_for_item(item)==[]
