"""La evaluación integral aplica a cualquier llamada, nunca al índice del lote."""
from copy import deepcopy
import pytest
from openpyxl import Workbook,load_workbook
from app.services.quality_decision import evaluate_quality,RULES
from app.services.dialogue_evaluation import scan_dialogue,pending_status
from app.services.conversation_evidence import holder_confirmation,payment_commitment,normalize
from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel
from app.services.rule_audit_report import add_rule_audit_sheets
from app.services.installment_validation import installment_plan
from app.services.payment_sequence_evidence import bounded_two_payment_sequence
from app.services.treatment_evidence import mistreatment_reports


def clean():
    return {'quality_contact_type':'TITULAR','quality_checks':{},'critical_failures':[],
            'penalties':[],'status_validation':{'valid':True,'matches':True,'excel_status':'CONVENIO'},
            'negotiation_validation':{'valid':True},'privacy_validation':{},'card_validation':{},
            'convenio_payment_validation':{'applies':True},'arco_validation':{'applies':False}}


@pytest.mark.parametrize('group,key,value,category',[
    (1,'status_validation',{'valid':False,'matches':None,'excel_status':'CONVENIO'},'REVISAR'),
    (2,'family_contact_validation',{'review_required':True,'reason':'Parentesco pendiente'},'REVISAR'),
    (3,'privacy_validation',{'confirmed_disclosure':True},'FALLA_GRAVE'),
    (4,'quality_contact_type','CONTACTO NO DETERMINADO','REVISAR'),
    (5,'card_validation',{'result':'TARJETA INCORRECTA'},'REVISAR'),
    (6,'arco_validation',{'applies':True,'valid':False},'REVISAR'),
    (8,'home_recovery_warning',{'review_required':True},'REVISAR'),
    (9,'quality_checks',{'groseria_bloquea_aprobacion':True},'REVISAR'),
    (10,'treatment_validation',{'hostile_interlocutor_review_required':True},'REVISAR'),
    (11,'quality_checks',{'queja_maltrato_detectada':True},'REVISAR'),
    (12,'negotiation_validation',{'valid':False,'reasons':['Fecha no verificable']},'REVISAR'),
    (13,'duration_validation',{'valid':False},'REVISAR'),
])
@pytest.mark.parametrize('score',[80,90,100])
def test_each_blocker_is_evaluated_for_all_approval_scores(group,key,value,category,score):
    m=clean();m[key]=deepcopy(value)
    result=evaluate_quality(m,score)
    assert result['clasificacion']==category
    assert len(result['rule_evaluation'])==13
    row=next(row for row in result['rule_evaluation'] if row['id']==group)
    assert row['state'] in {'REQUIERE_REVISION','INCUMPLIMIENTO_CRITICO'}
    assert any(f['rule_group']==group for f in result['decision_findings'])


def test_payment_places_are_a_deduction_in_the_complete_engine():
    m=clean();m['penalties']=[{'id':'PEN_CONV_LUGARES','category':'Negociación','points':20,'reason':'Falta segunda opción'}]
    r=evaluate_quality(m,80)
    assert r['clasificacion']=='APROBADO'
    assert r['rule_evaluation'][6]['state']=='DESCUENTO_APLICADO'
    assert not r['observaciones_conservadas']


@pytest.mark.parametrize('key,value',[
    ('privacy_validation',{'review_required':True}),
    ('privacy_validation',{'confirmed_disclosure':True}),
    ('card_validation',{'result':'REVISAR - REFERENCIA DISTINTA'}),
    ('arco_validation',{'applies':True,'valid':False}),
    ('wait_validation',{'review_required':True}),
    ('quality_checks',{'queja_maltrato_detectada':True}),
])
def test_human_hostility_exception_does_not_remove_other_groups(key,value):
    m=clean();m['quality_checks']['groseria_bloquea_aprobacion']=True
    m['hostile_interlocutor_exception']={k:True for k in ['audio_verified','interlocutor_hostile_or_lascivious','prevented_script','agent_professional']}
    m[key]=value
    assert not evaluate_quality(m,100)['clasificacion'].startswith('APROBADO')


def test_no_rename_when_quality_passes_but_original_status_is_not_authorized():
    result=evaluate_quality(clean(),100,base_classification={'estatus_autorizado':False})
    assert result['clasificacion']=='APROBADO_SIN_ETIQUETAR'
    assert result['calidad_aprobada'] and not result['aprobado']


@pytest.mark.parametrize('reply',[
    'No he podido ir a pagar.',
    'No sería posible realizar ese pago.',
    'Yo no he usado esa tarjeta. No me dieron ningún contrato.',
    'No tengo esa cantidad.',
])
def test_positive_evidence_of_pending_decision_not_absence_of_an_agreement(reply):
    text='Gestor: Podemos contar con su pago?\nTitular: '+reply
    d=scan_dialogue(text)
    assert pending_status(d,{'accepted':False})['detected_status']=='NO DEFINE FECHA DE PAGO'
    assert d['source_sha256']
    for e in d['events']:
        assert not e['human_verified']
        assert e['phrase'] in normalize(text)


@pytest.mark.parametrize('reply',[
    'Gracias, hasta luego.',
    'No me puedo registrar en la aplicación.',
    'Gestor: No sería posible realizar ese pago.',
    'Tercero: No tengo esa cantidad.',
    'Si yo tuviera esa tarjeta no he podido ir a pagar.',
    'El cliente dice que no he podido ir a pagar.',
])
def test_no_status_from_courtesy_app_failure_known_agent_third_or_hypothesis(reply):
    text='El pago de la tarjeta sería de 1000. '+reply
    assert pending_status(scan_dialogue(text),{'accepted':False}) is None


def test_pending_decision_does_not_replace_a_later_accepted_promise_or_followup():
    d=scan_dialogue('No tengo esa cantidad para el pago.')
    assert pending_status(d,{'accepted':True}) is None
    assert pending_status(d,{'accepted':False},True) is None


@pytest.mark.parametrize('amount',[500,900,1300,2500])
def test_unaccepted_small_offer_is_not_an_accepted_invalid_financial_contract(amount):
    text=f'Habla MRS. Soy yo. Le ofrecen un pago de {amount} pesos. No tengo esa cantidad.'
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.wav','texto':text,'duracion_segundos':150}),
        {'estatus_grabacion':'NO DEFINE FECHA DE PAGO','asignacion':'1PV','fecha':'2026-11-05','vencimiento':'2026-11-20','corte':'20','pago_minimo':3000,'saldo_total':6000})
    n=a.metadata['negotiation_validation']
    assert not n['commitment_confirmed'] and not n['hard_invalid']
    assert a.metadata['status_validation']['detected_status']=='NO DEFINE FECHA DE PAGO'
    # La propuesta no se oculta; se conserva como dato de revisión financiera.
    assert n['monto_detectado']==amount


@pytest.mark.parametrize('first,last',[(500,700),(1508,1702),(2000,3500)])
def test_unequal_three_payment_plan_keeps_all_explicit_installments(first,last):
    p=installment_plan(f'Solo tres pagos. Serían dos de {first} y el último sería el día veinte por {last}.',[])
    assert p['amounts']==[first,first,last]
    assert p['total']==2*first+last


def test_two_currency_values_and_repeated_calendar_days_are_not_a_two_payment_plan():
    text='El pago de 5155 pesos. Un peso. Para el día 7 o el día 8.'
    candidates=[(10,0,(11,15,5155,'5155')),(9,0,(23,25,1,'un'))]
    assert not bounded_two_payment_sequence(text,candidates)


def test_local_explicit_today_and_tomorrow_installments_can_be_summed():
    text='Pago de 1000 hoy y otro pago de 1500 mañana.'
    a=text.index('1000');b=text.index('1500')
    assert bounded_two_payment_sequence(text,[(10,0,(a,a+4,1000,'1000')),(10,0,(b,b+4,1500,'1500'))])==[1000,1500]


def test_report_contains_all_thirteen_groups_for_success_and_error_without_formulas(tmp_path):
    w=Workbook();decision=evaluate_quality(clean(),100)
    items=[{'file_name':'=EXAMPLE.ogg','classification':decision,'relation':{'numero_de_tarjeta':'0000000000000004'}},
           {'file_name':'failed.ogg','status':'error'}]
    add_rule_audit_sheets(w,items)
    p=tmp_path/'audit.xlsx';w.save(p);w.close()
    b=load_workbook(p,read_only=True,data_only=False)
    assert b['EVALUACION_13_REGLAS'].max_row==27
    assert b['RESUMEN_13_REGLAS'].max_row==14
    assert b['EVALUACION_13_REGLAS']['F2'].value=='0004'
    assert not any(c.data_type=='f' for ws in b for row in ws for c in row)
    for row in list(b['RESUMEN_13_REGLAS'].values)[1:]:
        assert row[2]==2 and sum(row[3:])==2
    b.close()


def test_explicit_each_payment_amount_and_three_calendar_days_are_a_plan():
    result=installment_plan('Sería el día 6, 13.20 para regularizar la cuenta por 1250 cada pago.',[])
    assert result['amounts']==[1250,1250,1250] and result['total']==3750


@pytest.mark.parametrize('text',[
    'El día 18/11/26 el pago sería por 1250 cada pago.',
    'El teléfono 55,36,25 sería por 1250 cada pago.',
    'El día 6,13,35 el pago sería por 1250 cada pago.',
])
def test_phone_invalid_days_or_one_calendar_date_cannot_create_a_plan(text):
    assert not installment_plan(text,[])['amounts']


def test_name_authority_changes_only_output_identifier_and_preserves_excel_source():
    from app.services.account_source_validation import apply_output_name_authority
    relation={'nombre_final':'0001111222233334444_1PV_A','numero_de_tarjeta':'5555666677778888',
              'datos_excel_original':{'nombre_final':'0001111222233334444_1PV_A'}}
    item={'relation':deepcopy(relation),'file_name':'original.ogg','result':{'texto':'Texto original'}}
    assert apply_output_name_authority(item)
    assert item['relation']['nombre_final']=='0005555666677778888_1PV_A'
    assert item['relation']['numero_de_tarjeta']==relation['numero_de_tarjeta']
    assert item['relation']['datos_excel_original']==relation['datos_excel_original']
    assert item['result']=={'texto':'Texto original'} and item['file_name']=='original.ogg'
    assert not item['output_name_normalization']['human_verified']
    assert not apply_output_name_authority(item)


@pytest.mark.parametrize('card',['1234','555566667777888','5555666677778888.0',''])
def test_incomplete_or_numeric_excel_card_is_not_padded_to_fix_output_name(card):
    from app.services.account_source_validation import apply_output_name_authority
    item={'relation':{'nombre_final':'0001111222233334444_1PV_A','numero_de_tarjeta':card}}
    original=deepcopy(item)
    assert not apply_output_name_authority(item)
    assert item==original


def test_actual_agreement_gets_financial_validation_even_when_excel_says_no_date():
    text='Habla MRS. Soy yo. ¿Podemos contar con su pago de 1000 para el día 10? Sí, de acuerdo.'
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.wav','texto':text,'duracion_segundos':150}),
        {'estatus_grabacion':'NO DEFINE FECHA DE PAGO','asignacion':'1PV','fecha':'2026-11-05','vencimiento':'2026-11-20','corte':'20','pago_minimo':1000,'saldo_total':3000})
    n=a.metadata['negotiation_validation']
    assert n['is_negotiation'] and n['commitment_confirmed']
    assert any('RN004' in r for r in n['reasons'])
    assert not a.metadata['shared_classification']['clasificacion'].startswith('APROBADO')


@pytest.mark.parametrize('phrase',[
    'Ya les había comentado en llamadas anteriores que tienen una falta de comunicación.',
    'En la llamada anterior no hay una buena comunicación entre sus áreas.',
])
def test_reported_prior_service_inconsistency_is_not_approved_as_simple_pending_payment(phrase):
    assert mistreatment_reports('Titular: '+phrase,[],[])


def test_missing_amount_does_not_turn_an_overdue_intention_into_confirmed_severe_agreement():
    text='Habla MRS. Soy yo. Lo voy a realizar el día 15, por favor regístrelo.'
    a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.wav','texto':text,'duracion_segundos':150}),
        {'estatus_grabacion':'NO DEFINE FECHA DE PAGO','asignacion':'1FLP','fecha':'2026-11-05','vencimiento':'2026-11-08','pago_minimo':1000,'saldo_total':3000})
    assert 'PEN005' not in {p['id'] for p in a.metadata['penalties']}
    assert a.metadata['shared_classification']['clasificacion']=='REVISAR'


def test_spanish_two_payment_sequence_does_not_drop_conjunction_inside_amount_span():
    r=A.calculate_basic_compliance('Habla MRS. Soy yo. Me comprometo a pagar mil pesos hoy y dos mil pesos mañana.',
        {'estatus_grabacion':'CONVENIO','pago_minimo':2500,'saldo_total':8000,'fecha':'2026-10-13'})
    assert r['negotiation_validation']['multipago_detectado']
    assert r['negotiation_validation']['total_multipago']==3000


def test_a_four_day_list_is_not_truncated_to_a_three_installment_plan():
    assert not installment_plan('El día 6,13,20,27 sería por 1250 cada pago.',[])['amounts']


def test_critical_financial_failure_is_visible_in_its_rule_group():
    m=clean();m['critical_failures']=[{'id':'PEN005','invalidates':True,'reason':'Pago posterior al vencimiento'}]
    result=evaluate_quality(m,0)
    assert result['rule_evaluation'][11]['state']=='INCUMPLIMIENTO_CRITICO'


def test_final_amount_reply_is_attached_to_payment_and_not_whatsapp_number():
    text='Podemos contar con su pago para el día 9. Sería por 1555. Ajá, está bien.'
    result=payment_commitment(text)
    assert result['accepted']
    assert result['contextual_confirmation_events'][0]['amount']==1555
    assert not payment_commitment('El número de WhatsApp sería por 1555. Ajá, está bien.')['accepted']


def test_final_formatted_amount_links_to_the_accepted_date_instead_of_an_old_offer():
    text=('Su pago. '+'Dato informativo. '*11+
          'Vamos a estar al día 9, ¿le parece bien? Bueno, está bien. Sería por 1.555. Ajá, está bien.')
    result=payment_commitment(text)
    amounts=[e for e in result['contextual_confirmation_events'] if e.get('amount')]
    assert result['accepted'] and amounts[-1]['amount']==1555
    assert 'context_event_position' in amounts[-1]


def test_new_medical_or_receipt_topic_cannot_supply_a_payment_confirmation_amount():
    text=('Su pago. '+'Dato informativo. '*11+
          'Vamos a estar al día 9, ¿le parece bien? Bueno, está bien. '
          'Ahora sobre su cita médica. Sería por 1.555. Ajá, está bien.')
    result=payment_commitment(text)
    assert not any(e.get('amount') for e in result.get('contextual_confirmation_events',[]))
