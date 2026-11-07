"""La revisión de aprobación es distinta de un rechazo ordinario ya resuelto."""
from copy import deepcopy
import pytest
from app.services.analytics_service import AnalyticsService as A


def ordinary():
    return {'quality_contact_type':'CONTACTO NO DETERMINADO',
            'status_validation':{'excel_status':'CONVENIO','matches':None,'valid':False,
                                 'reasons':['Estatus sin evidencia suficiente.']},
            'penalties':[{'id':'PEN001','points':20},{'id':'PEN_CONV_LUGARES','points':20}],
            'convenio_payment_validation':{'applies':True,'minimum_places_met':False},
            'negotiation_validation':{'valid':True}}


def test_low_score_ordinary_failure_is_rejected_without_certifying_unresolved_identity():
    metadata=ordinary();before=deepcopy(metadata)
    r=A.shared_quality_decision(metadata,60,duration_seconds=100)
    assert r['clasificacion']=='NO_APROBADO_MENOR_80'
    assert not r['aprobado'] and r['rechazo_automatico_por_puntaje']
    assert any('Interlocutor sin identificar' in reason for reason in r['observaciones_conservadas'])
    assert any('Estatus' in reason for reason in r['observaciones_conservadas'])
    assert metadata==before


@pytest.mark.parametrize('key,value',[
    ('privacy_validation',{'review_required':True}),
    ('negotiation_validation',{'valid':False,'review_required':True}),
    ('financial_review_validation',{'review_required':True}),
    ('family_contact_validation',{'review_required':True}),
    ('recado_acceptance_validation',{'review_required':True,'reason':'Recado pendiente.'}),
    ('card_validation',{'result':'REVISAR - REFERENCIA DISTINTA'}),
    ('wait_validation',{'review_required':True}),
    ('treatment_validation',{'mistreatment_report_evidence':[{'text':'Me atendieron mal.'}]}),
    ('quality_checks',{'groseria_bloquea_aprobacion':True}),
    ('home_recovery_warning',{'review_required':True}),
    ('audio_block_evidence_validation',{'quality':{'degraded':True},'review_required':True}),
    ('call_end_validation',{'review_required':True}),
])
def test_low_score_does_not_close_safety_or_financial_review(key,value):
    m=ordinary();m[key]=value
    assert A.shared_quality_decision(m,60,duration_seconds=100)['clasificacion']=='REVISAR'


@pytest.mark.parametrize('score',[80,100])
def test_sufficient_score_does_not_bypass_identity_or_status_uncertainty(score):
    assert A.shared_quality_decision(ordinary(),score,duration_seconds=100)['clasificacion']=='REVISAR'


def test_critical_failure_still_has_priority_over_ordinary_rejection():
    m=ordinary();m['critical_failures']=[{'id':'PEN003','invalidates':True}]
    assert A.shared_quality_decision(m,0,duration_seconds=100)['clasificacion']=='FALLA_GRAVE'


def test_an_unexplained_low_score_or_short_call_is_not_automatically_closed():
    m=ordinary();m['penalties']=[]
    assert A.shared_quality_decision(m,60,duration_seconds=100)['clasificacion']=='REVISAR'
    m=ordinary();m['penalties']=[{'id':'PEN001','points':20}]
    assert A.shared_quality_decision(m,60,duration_seconds=100)['clasificacion']=='REVISAR'
    assert A.shared_quality_decision(ordinary(),60,duration_seconds=40)['clasificacion']=='REVISAR'
