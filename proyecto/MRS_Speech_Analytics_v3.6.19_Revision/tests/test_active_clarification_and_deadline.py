from copy import deepcopy
import pytest
from app.services.active_clarification_evidence import active_clarification
from app.services.definitive_rejection import definitive_rejection
from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel

TEXT=('Ya tengo una aclaración porque no sé qué me están cobrando. '
      '¿Me puede dar el folio de esa aclaración? Me mandaron el folio. '
      'Le voy a dejar un número de WhatsApp para que me envíe el folio. '
      '¿Cuándo le dieron la fecha de resolución? Mañana en la tarde. '
      'Es importante verificar ese folio. Hasta luego.')


def test_open_dispute_followup_is_not_new_collection_attempt_or_bank_confirmation():
    proof=active_clarification(TEXT)
    assert proof['confirmed'] and not proof['bank_confirmation']
    t=TranscriptionModel.from_dict({'archivo':'ejemplo.ogg','texto':'Habla MRS. Soy yo. '+TEXT,
                                  'duracion_segundos':150,'segmentos':[]})
    result=A.analyze_transcription(t,{'estatus_grabacion':'ACLARACION'}).metadata
    assert result['clarification_validation']['active_dispute_followup']
    assert result['negotiation_validation']['dispute_guidance']
    assert not result['negotiation_validation']['missing_collection_attempt_penalty']
    assert result['status_validation']['detected_status']=='ACLARACION'


@pytest.mark.parametrize('text',[
    TEXT.replace('Ya tengo una aclaración','Quiero levantar una aclaración'),
    TEXT.replace('Me mandaron el folio','No me mandaron el folio'),
    TEXT.replace('Mañana en la tarde','No me dieron ninguna fecha'),
    'Gestor: '+TEXT,
    TEXT.replace('Ya tengo una aclaración','Diga que ya tengo una aclaración'),
])
def test_unopened_unacknowledged_undated_or_quoted_case_is_not_confirmed(text):
    assert not active_clarification(text)['confirmed']


def metadata():
    return {'quality_contact_type':'TITULAR','negotiation_validation':{'financial_validation_applicable':True,'valid':False,
        'payment_date_confirmed':True,'commitment_confirmed':True,'amount_confirmed':True,
        'promise_date':'2026-11-13','mora_payment_policy':{'window_end':'2026-11-12'}}}


def test_confirmed_single_payment_outside_policy_closes_rejection_with_other_alerts_preserved():
    m=metadata();before=deepcopy(m)
    result=definitive_rejection(m,[{'severity':'REVIEW','code':'UNCERTAIN_DISCLOSURE'}],100)
    assert result['code']=='CONFIRMED_PAYMENT_DATE_OUTSIDE_POLICY'
    assert m==before


@pytest.mark.parametrize('change',[
    {'payment_date_confirmed':False}, {'commitment_confirmed':False},
    {'amount_confirmed':False}, {'date_year_rollover_review':True},
    {'review_required':True},
    {'multipago_detectado':True}, {'payment_confirmation_case':True},
    {'installment_window':{'applies':True}}, {'accepted_schedule':{'confirmed':True}},
    {'promise_date':'2026-11-12'}, {'promise_date':'fecha ilegible'},
])
def test_unknown_unaccepted_or_installment_payment_does_not_close_as_single_date_failure(change):
    m=metadata();m['negotiation_validation'].update(change)
    assert definitive_rejection(m,[],100)is None


def test_confirmed_critical_failure_keeps_priority_over_ordinary_date_failure():
    assert definitive_rejection(metadata(),[{'severity':'CRITICAL'}],100)is None


def test_unidentified_recipient_does_not_certify_a_debtors_single_payment_promise():
    m=metadata();m['quality_contact_type']='CONTACTO NO DETERMINADO'
    assert definitive_rejection(m,[],100)is None
