"""Criterio ratificado 25/11 y causas generales: entradas sintéticas."""
from datetime import date
from copy import deepcopy
import pytest
from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel
from app.services.conversation_evidence import assess_recado,holder_confirmation,payment_commitment
from app.services.call_wait_evidence import assess_call_wait
from app.services.payment_instruction_validation import transfer_is_option_listing
from app.services.final_validation_confirmation import confirmed_validation_plan
from app.services.installment_validation import accepted_calendar


@pytest.mark.parametrize('role,confirmed,review',[('GESTOR',True,False),('UNKNOWN',False,True),('TERCERO',False,False)])
def test_third_party_payment_instruction_requires_actual_speaker(role,confirmed,review):
    from app.services.payment_instruction_validation import third_party_payment_guidance
    evidence=[{'text':'Puede pagar en Santander.','speaker_role':role,'start':20,'end':25}]
    result=third_party_payment_guidance(evidence,third_party=True)
    assert result['confirmed'] is confirmed
    assert result['review_required'] is review
    assert not third_party_payment_guidance(evidence,third_party=False)['confirmed']


def test_confirmed_third_party_payment_guidance_is_not_a_fake_critical_failure():
    from app.services.definitive_rejection import definitive_rejection
    guidance={'confirmed':True,'reason':'Instrucción acreditada a tercero.'}
    m={'convenio_payment_validation':{'third_party_guidance':guidance}}
    r=definitive_rejection(m,[],120)
    assert r['code']=='CONFIRMED_THIRD_PARTY_PAYMENT_GUIDANCE'
    assert r['severity']=='CONFIRMED_NONCRITICAL'
    assert definitive_rejection(m,[{'severity':'CRITICAL'}],120) is None


def test_restructuring_question_never_turns_later_schedule_numbers_into_paid_amount():
    from app.services.conversation_evidence import completed_payment
    from app.services.reported_payment_amounts import reported_amounts
    text=('Ya hice un convenio de pago y ya hice el primer abono. ¿Por cuál fue su primer abono? '
          'Mil cincuenta y uno, creo que eran. Hace tres días lo hice. '
          'La reestructuración, me comenta qué meses fueron y por qué cantidad? '
          'No, creo que quedó como 9,78 por mes, en 12 meses, son 12,79.')
    result=reported_amounts(text,completed_payment(text))
    assert 12.79 not in result['amounts']
    assert 9.78 not in result['amounts']
    m=evaluate('Habla MRS. Soy yo. '+text+' Le solicito la carta de reestructuración. '
        'No tengo la carta. Le puedo mandar las capturas.',
        {'estatus_grabacion':'NO DEFINE FECHA DE PAGO','pago_minimo':5700,'saldo_total':10500})
    assert not m['negotiation_validation']['prior_payment_with_current_condition']
    assert not m['shared_classification']['aprobado']
    assert m['negotiation_validation']['review_required']


def test_disputed_historical_bill_is_not_a_new_under_minimum_negotiation():
    m=evaluate('Habla MRS. Soy yo. Mi pago me volvió a llegar casi de tres mil quinientos pesos para no generar interés. '
        'Yo llamaba a atención a clientes y me colgaban. No pude resolverlo.',
        {'estatus_grabacion':'NO DEFINE FECHA DE PAGO','pago_minimo':4600,'saldo_total':10000})
    n=m['negotiation_validation']
    assert not any('menor al mínimo'in reason for reason in n['reasons'])
    assert m['treatment_validation']['mistreatment_report_evidence']
    assert m['shared_classification']['clasificacion']=='REVISAR'


def test_explicit_old_bill_does_not_become_an_under_minimum_current_proposal():
    m=evaluate('Habla MRS. Soy yo. Hace menos de un mes tenía que pagar 500 y algo. '
        'Ahora voy a revisar qué puedo hacer.',
        {'estatus_grabacion':'NO DEFINE FECHA DE PAGO','pago_minimo':1800,'saldo_total':10000})
    assert not any('menor al mínimo'in reason for reason in m['negotiation_validation']['reasons'])


def test_old_bill_does_not_hide_a_separate_current_under_minimum_commitment():
    m=evaluate('Habla MRS. Soy yo. Hace menos de un mes tenía que pagar 500. '
        '¿Puede pagar 900 pesos hoy? Sí. Puede pagar en Chedraui y Farmacias del Ahorro. '
        'Envíe su comprobante por WhatsApp.',
        {'asignacion':'1PV','fecha':'2026-11-20','vencimiento':'2026-11-30',
         'estatus_grabacion':'CONVENIO','pago_minimo':1800,'saldo_total':10000})
    assert m['negotiation_validation']['amount_invalid']
    assert not m['shared_classification']['aprobado']


@pytest.mark.parametrize('text',['Me dijeron que puede pagar en Santander.','No puede pagar en Santander.'])
def test_quoted_or_negated_payment_instruction_does_not_create_third_party_failure(text):
    from app.services.payment_instruction_validation import third_party_payment_guidance
    assert not third_party_payment_guidance([{'text':text,'speaker_role':'GESTOR'}],third_party=True)['confirmed']


def evaluate(text,relation=None,segments=None,duration=120):
    return A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'sample.wav','texto':text,
        'segmentos':segments or[],'duracion_segundos':duration}),relation or{'estatus_grabacion':'NO DEFINE FECHA DE PAGO'}).metadata


@pytest.mark.parametrize('background',['Soy madre soltera.','Soy padre de familia.','Soy madre de dos hijos.'])
def test_family_background_is_not_a_third_party_relationship(background):
    text='¿Me comunica con Marina Robles? Sí. Habla MRS. Mi tarjeta está vencida. '+background+' No puedo pagar.'
    assert not assess_recado(text)['family']
    assert holder_confirmation(text)['confirmed']
    assert evaluate(text)['quality_contact_type']=='TITULAR'


@pytest.mark.parametrize('declaration',['Soy su madre.','Soy madre del titular.','Soy su hija.'])
def test_true_family_relationship_still_blocks_holder(declaration):
    text='¿Me comunica con Marina Robles? No está. '+declaration
    assert assess_recado(text)['family']
    assert not holder_confirmation(text)['confirmed']


def test_third_party_payment_report_does_not_require_holder_minimum_coverage():
    text=('Gestor: Habla MRS. ¿Está la titular? Familiar: No está, soy su madre. '
          'Ya pagué 500 pesos ayer y deposité 600 pesos. Gestor: Envíe su comprobante por WhatsApp. '
          'Dígale que se comunique al número 5512345678. Familiar: Sí, yo le paso el recado.')
    m=evaluate(text,{'estatus_grabacion':'RECADO REF1','pago_minimo':3000,'saldo_total':10000})
    assert m['quality_contact_type'].startswith('TERCERO')
    n=m['negotiation_validation']
    assert not n['followup_coverage_validation']['applies']
    assert not any('mínimo'in r or 'Importes de pagos reportados distintos'in r for r in n['reasons'])
    assert not m['privacy_validation']['confirmed_disclosure']


def test_holder_payment_report_still_requires_minimum_coverage():
    m=evaluate('Habla MRS. Soy yo. Ya pagué 500 pesos ayer. Envíe su comprobante por WhatsApp.',
        {'estatus_grabacion':'CONVENIO','pago_minimo':3000,'saldo_total':10000})
    assert m['negotiation_validation']['followup_coverage_validation']['applies']
    assert not m['shared_classification']['aprobado']


def test_amount_then_own_date_reply_is_personal_context_not_an_isolated_yes():
    text=('Me comunico con Marina Robles. Habla MRS. ¿De qué cantidad lo va a realizar? '
          'Los 900. ¿El pago qué día? Por hoy también, me voy para allá.')
    assert holder_confirmation(text)['confirmed']
    assert not holder_confirmation('Me comunico con Marina Robles. Habla MRS. Sí.')['confirmed']


def test_present_own_payment_without_accepted_date_is_not_a_firm_dated_agreement():
    text='Habla MRS. Soy yo. Entonces hago el pago y envío mi comprobante.'
    m=evaluate(text)
    assert payment_commitment(text)['accepted']
    assert m['status_validation']['detected_status']=='NO DEFINE FECHA DE PAGO'
    assert not m['negotiation_validation']['payment_date_confirmed']


def test_current_attempt_after_historical_payment_does_not_inherit_paid_followup():
    text=('Habla MRS. Soy yo. Ya pagué 500 pesos el mes pasado. '
          'Ahora el banco solicita 900 pesos. Bueno, voy a tratar de realizar ese pago.')
    m=evaluate(text,{'estatus_grabacion':'CONVENIO','pago_minimo':800})
    assert not m['negotiation_validation']['payment_confirmation_case']
    assert m['status_validation']['detected_status']=='NO DEFINE FECHA DE PAGO'


@pytest.mark.parametrize('reply',['Si lo dividimos entre tres pagos.','Si lo realiza mañana se aplica.'])
def test_hypothetical_si_is_not_an_acceptance(reply):
    assert not payment_commitment('¿Podemos contar con 900 pesos hoy? '+reply)['accepted']


def test_route_discussion_does_not_replace_the_accepted_agreement():
    result=payment_commitment('¿Puede pagar 900 pesos mañana? Sí. Creo que lo voy a realizar por medio de transferencia por la aplicación.')
    assert result['accepted']
    assert '900'in result['evidence']and'mañana'in result['evidence'].lower().replace('manana','mañana')


@pytest.mark.parametrize('speaker',['SPEAKER_00','SPEAKER_01','Validador'])
def test_final_validation_never_assigns_holder_from_a_diarization_number(speaker):
    text='Del área de validación. Queda confirmado su pago por la cantidad de 900 pesos mañana. '+speaker+': Sí.'
    assert not confirmed_validation_plan(text)['confirmed']


def test_final_validation_uses_common_conditions_and_immediate_response():
    prefix='Del área de validación. Queda confirmado su pago por la cantidad de 900 pesos mañana. '
    assert confirmed_validation_plan(prefix+'Titular: Sí.')['confirmed']
    assert not confirmed_validation_plan(prefix+'Titular: Sí, si consigo el dinero.')['confirmed']
    assert not confirmed_validation_plan(prefix+'Validador: Ya tiene WhatsApp. Titular: Sí.')['confirmed']


def test_prior_service_complaint_is_review_without_independent_rejection():
    m=evaluate('Habla MRS. Soy yo. No tengo dinero. En la llamada anterior me trataron mal.')
    c=m['shared_classification'];assert c['clasificacion']=='REVISAR'
    assert any(f['code']=='MISTREATMENT_REPORT'and f['severity']=='REVIEW'for f in c['decision_findings'])
    assert not m['critical_failures']


def test_complete_formalized_installments_keep_their_dates_before_quality_scoring():
    m=evaluate('Habla MRS. Soy yo. Activamos convenio por 1000 pesos el 16 de octubre como primer pago '
        'y el segundo por 1200 pesos el 24 de octubre para cubrir la mensualidad vencida. '
        'Me comprometo a pagar el convenio completo. Puede pagar en Chedraui y Farmacias del Ahorro. '
        'Envíe su comprobante por WhatsApp.',
        {'asignacion':'1PV','fecha':'2026-10-13','vencimiento':'2026-10-30','corte':'23',
         'pago_minimo':2000,'saldo_total':50000,'estatus_grabacion':'CONVENIO'})
    n=m['negotiation_validation']
    assert n['promise_date']=='2026-10-24'
    assert n['quality_stage_applicable']
    assert not any(p['id']=='PEN007'for p in m['penalties'])
    assert m['shared_classification']['clasificacion']=='REVISAR'


def test_complete_accepted_under_minimum_plan_closes_rejection_with_wait_alert():
    text=('Habla MRS. Soy yo. El primero sería de 1000 el día de mañana y el segundo pago de 1200 '
          'el día 27, ¿correcto? Sí. Puede pagar en Chedraui y Farmacias del Ahorro. '
          'Envíe su comprobante por WhatsApp. Permítame revisar.')
    rows=[{'inicio':0,'fin':20,'texto':text},{'inicio':20,'fin':100,'texto':'Permítame, permítame.'}]
    m=evaluate(text+' Permítame, permítame.',segments=rows,duration=100,
        relation={'asignacion':'1PV','fecha':'2026-11-20','vencimiento':'2026-11-30',
            'pago_minimo':3000,'saldo_total':10000,'estatus_grabacion':'CONVENIO'})
    c=m['shared_classification']
    assert c['clasificacion']=='NO_APROBADO'
    assert c['requires_alert_review']
    assert any(f['code']=='WAIT_WITHOUT_RESUMPTION'for f in c['pending_alerts'])
    assert not m['critical_failures']


def test_incomplete_or_conflicting_installments_cannot_close_a_financial_rejection():
    from app.services.definitive_rejection import complete_accepted_installments
    n={'commitment_evidence':{'accepted':True},'monto_detectado':2200,
       'installment_validation':{'amounts':[1000,1200],'total':2200},
       'installment_dates':[{'date':'2026-11-21'},{'date':'2026-11-27'}],
       'accepted_schedule':{'confirmed':True,'amounts':[1000,1200],
            'dates':[{'date':'2026-11-21'},{'date':'2026-11-27'}]}}
    assert complete_accepted_installments(n)
    n['installment_dates'].pop()
    assert not complete_accepted_installments(n)
    n['installment_dates'].append({'date':'2026-11-27'})
    n['installment_validation']['review_required']=True
    assert not complete_accepted_installments(n)
    n['installment_validation']['review_required']=False
    n['installment_validation']['total']=float('nan')
    assert not complete_accepted_installments(n)


def test_report_of_bank_cancellation_problem_alone_is_not_mistreatment():
    from app.services.treatment_evidence import mistreatment_reports
    assert not mistreatment_reports('Titular: No me quisieron dar de baja la tarjeta; no reconozco esos cargos.',[],[])
    assert mistreatment_reports('Titular: No me quisieron dar de baja y además me gritaron.',[],['me gritaron'])


def test_subjunctive_payment_purpose_is_not_hostile_imperative():
    m=evaluate('Habla MRS. Soy yo. Esto se toma en cuenta para que pues pague más.')
    assert not m['treatment_validation']['confrontation_details']
    assert evaluate('Habla MRS. Soy yo. Pues pague.')['treatment_validation']['confrontation_details']


def test_reported_hold_in_old_call_is_not_current_wait():
    rows=[{'inicio':0,'fin':10,'texto':'Hablé para allá, sabes qué hacían? Espera un momentito y ya me hablaba otra persona.'},
          {'inicio':10,'fin':80,'texto':'Me atendieron cuatro personas con las mismas preguntas.'},
          {'inicio':80,'fin':90,'texto':'Le comento que debe verificar el folio.'}]
    text=' '.join(r['texto']for r in rows)
    assert not assess_call_wait(text,rows,90)['review_required']


def test_financial_dialogue_resumes_hold_without_magic_courtesy():
    rows=[{'inicio':0,'fin':2,'texto':'Permítame revisar.'},
          {'inicio':3,'fin':10,'texto':'¿Cuánto realizó de pago ayer?'},
          {'inicio':10,'fin':15,'texto':'Pagué 900 pesos.'},
          {'inicio':90,'fin':100,'texto':'Gracias, hasta luego.'}]
    result=assess_call_wait(' '.join(r['texto']for r in rows),rows,100)
    # El hueco ASR de 75 s sigue señalado, pero no una espera ficticia de 88.
    assert all(i['method']!='ESPERA_ANUNCIADA_SIN_RETOMA'for i in result['intervals'])
    assert any(i['method']=='INTERVALO_SIN_TEXTO_ASR'for i in result['intervals'])


def test_sparse_hold_segment_is_uncertain_audio_not_confirmed_silence():
    rows=[{'inicio':0,'fin':80,'texto':'Permítame, permítame.'},
          {'inicio':80,'fin':90,'texto':'Le comento que puede pagar.'}]
    result=assess_call_wait(' '.join(r['texto']for r in rows),rows,90)
    assert result['review_required']
    assert any(i['method']=='PROMPT_DE_ESPERA_EN_SEGMENTO_ASR_IMPRECISO'for i in result['intervals'])


def test_qualified_bank_enumeration_is_not_a_selected_transfer_destination():
    assert transfer_is_option_listing('Mediante transferencia, si es posible, de alguna Santander, BBVA o Banamex.',[],['7-ELEVEN'])
    assert not transfer_is_option_listing('Transfiera a mi cuenta personal Santander 5551234567.',[],['7-ELEVEN'])
    assert not transfer_is_option_listing('Mediante transferencia de BBVA.',[],['7-ELEVEN'])


def test_accepted_calendar_keeps_prior_month_days_and_requires_explicit_month():
    days=accepted_calendar('2000 pesos el día lunes 23-30 y 7 de diciembre, ¿correcto? Sí.',date(2026,11,20),3)
    assert [r['date']for r in days]==['2026-11-23','2026-11-30','2026-12-07']
    assert not accepted_calendar('El día 23 o 30 y 7 de diciembre.',date(2026,11,20),3)
    assert not accepted_calendar('El día 23-30 y 7.',date(2026,11,20),3)


@pytest.mark.parametrize('text',[
    'Gestor: Le recomiendo que pague hoy 900 pesos.',
    'Titular: Mi trato lo hice con la tienda.',
    'Titular: La cancelación la hice ayer, no un pago.',
])
def test_future_instructions_and_nonpayment_acts_are_not_paid_reports(text):
    from app.services.conversation_evidence import completed_payment
    assert not completed_payment(text)['confirmed']


def test_a_real_prior_payment_is_not_removed_by_other_administrative_acts():
    from app.services.conversation_evidence import completed_payment
    assert completed_payment('Titular: Yo pagué 900 pesos ayer. Mi trato lo hice en tienda.')['confirmed']


@pytest.mark.parametrize('text',['Voy a hacer una cosa.','Voy a hacer todo lo humanamente posible.','Voy a pagar una servilleta para anotar.'])
def test_nonfinancial_actions_do_not_create_a_payment_commitment(text):
    assert not payment_commitment(text)['accepted']


def test_personal_two_payment_schedule_is_not_the_first_amount_alone():
    from app.services.accepted_schedule_evidence import accepted_two_part_schedule
    text='Titular: Mañana hago el pago de 500 pesos para que el día 28 hago el otro pago de 2358.'
    plan=accepted_two_part_schedule(text,[],date(2026,11,20))
    assert plan['confirmed']and plan['amounts']==[500,2358]and plan['total']==2858
    assert not accepted_two_part_schedule('Gestor: '+text.split(': ',1)[1],[],date(2026,11,20))['confirmed']


def test_new_accepted_recap_does_not_merge_a_historical_first_payment():
    from app.services.accepted_schedule_evidence import accepted_two_part_schedule
    text=('Mi primer depósito anterior fue de 500. El primero sería de 2000 el día de mañana '
          'y el segundo pago de 2686 el día 27, ¿correcto? Sí.')
    plan=accepted_two_part_schedule(text,[],date(2026,11,20))
    assert plan['confirmed']and plan['amounts']==[2000,2686]


def test_monthly_restructuring_amount_does_not_replace_the_reported_payment():
    from app.services.conversation_evidence import completed_payment
    from app.services.reported_payment_amounts import reported_amounts
    text='Ya pagué 500 pesos ayer. ¿La reestructuración por qué cantidad? Creo que quedó 978 por mes en doce meses.'
    amount=reported_amounts(text,completed_payment(text))
    assert amount['total']==500 and amount['amounts']==[500]
    assert not amount['review_required']


def test_monthly_restructuring_without_paid_amount_does_not_confirm_a_paid_amount():
    from app.services.conversation_evidence import completed_payment
    from app.services.reported_payment_amounts import reported_amounts
    text='El pago lo hice hace tres días. ¿La reestructuración por qué cantidad? Creo que quedó 978 por mes en doce meses.'
    amount=reported_amounts(text,completed_payment(text))
    assert amount['total']is None and not amount['amounts']


def test_relative_helping_the_holder_is_not_the_relative_answering_the_call():
    own=('¿Me comunica con Marina Robles? Sí. Habla MRS. Mi tarjeta está pendiente. '
         'Es mi hija quien me ayuda con mi pago.')
    assert not assess_recado(own)['family']
    assert holder_confirmation(own)['confirmed']
    third='¿Me comunica con Marina Robles? No está. Soy su hija, le ayudo con sus pagos.'
    assert assess_recado(third)['family']and not holder_confirmation(third)['confirmed']
