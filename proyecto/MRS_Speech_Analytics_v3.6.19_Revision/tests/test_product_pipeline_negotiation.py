"""BatchService integration, including Excel, recovery, copy and checkpoint.

The controlled run uses declared ASR outputs and silent WAV fixtures. Actual
complete-call recognition is executed separately and never called human truth.
"""
from pathlib import Path
import json
import os
import subprocess
import sys
import pytest


@pytest.fixture(scope='module')
def pipeline(tmp_path_factory):
    root=Path(__file__).resolve().parents[3]
    script=root/'auditoria/r67-flujo-real-20261127/reproducir_flujo_completo.py'
    target=tmp_path_factory.mktemp('pipeline')/'project'
    subprocess.run([sys.executable,str(script),str(target)],cwd=Path(__file__).resolve().parents[1],
        env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1])),
        check=True,capture_output=True,text=True)
    result=json.loads((target/'summary.json').read_text())
    assert result['checkpoint_generated']and result['quality_excel_generated']and result['nonpayment_excel_generated']
    return {row['case']:row for row in result['rows']}


@pytest.mark.parametrize('case,quality,amount,date',[
    ('promesa_personal','APROBADO',1300,'2026-11-22'),
    ('parcialidad_modificada','APROBADO',1800,'2026-11-23'),
    ('recapitulacion_posterior','APROBADO',1200,'2026-11-21'),
    ('nuevo_importe','APROBADO',1200,'2026-11-22'),
    ('nuevo_importe_fuera_plazo','FALLA_GRAVE',1200,'2026-12-01'),
    ('nuevo_importe_inferior_minimo','NO_APROBADO',200,'2026-11-22'),
    ('nuevo_importe_maltrato','REVISAR',1200,'2026-11-22'),
    ('sin_cambio','APROBADO',900,'2026-11-23'),
    ('rechazo_inicial_superado','APROBADO',1200,'2026-11-22'),
    ('medium_resuelve_cierre','APROBADO',1200,'2026-11-22'),
])
def test_one_negotiation_in_facts_final_quality_copy_checkpoint_and_excel(pipeline,case,quality,amount,date):
    row=pipeline[case]
    assert row['classification']==row['metadata_classification']==row['checkpoint_classification']==row['excel_classification']==quality
    assert row['amount']==amount and row['date']==date
    if case not in{'medium_resuelve_cierre','promesa_personal','recapitulacion_posterior'}:
        assert row['plan_facts'][-1]['amount']==amount and row['plan_facts'][-1]['date']==date
    assert row['source_copy_sha256_equal']and row['reason_matches_canonical']
    if quality=='FALLA_GRAVE':assert row['folder']=='NEGOCIACION_INVALIDA'
    if case=='medium_resuelve_cierre':
        assert row['medium_attempts']==2
        assert row['recovered_plan']['amount']==amount


def test_a_real_contradiction_between_decodes_is_not_outvoted(pipeline):
    row=pipeline['medium_contradictorio']
    assert row['medium_attempts']==3 and row['classification']=='REVISAR'
    assert not row['recovered_plan']


@pytest.mark.parametrize('reply',[
    'No entiendo la pregunta.','No se entiende la respuesta.','No le escucho bien.',
    'No puedo escuchar, repita por favor.','Se corta, ¿me puede repetir?',
])
def test_communication_repair_is_not_a_financial_refusal(reply):
    from app.services.conversation_evidence import payment_commitment
    result=payment_commitment('¿Me indica el monto y la fecha de su pago? '+reply)
    assert not result.get('accepted')and not result.get('declined')and not result.get('conditional')


@pytest.mark.parametrize('reply',[
    'No.', 'No puedo pagar.', 'No entiendo, pero no puedo pagar.',
    'No escuché, pero no me comprometo.',
])
def test_real_refusal_still_blocks_acceptance(reply):
    from app.services.conversation_evidence import payment_commitment
    result=payment_commitment('¿Puede realizar su pago mañana? '+reply)
    assert not result['accepted']and(result.get('declined')or result.get('conditional'))


def test_revoked_schedule_does_not_remain_as_an_accepted_obligation(pipeline):
    row=pipeline['revocado']
    assert row['classification']=='APROBADO_ETIQUETA_CORREGIDA'
    assert row['status_detected']=='NO DEFINE FECHA DE PAGO'
    assert not row['plan_facts']
    assert row['reason_matches_canonical']


def test_hearing_confirmation_is_not_a_request_to_repair_the_call():
    from app.services.payment_reply_scope import communication_repair
    assert not communication_repair('Sí, le escucho bien.')
    assert not communication_repair('Ya entendí, gracias.')
    assert communication_repair('No le escucho bien.')
    assert not communication_repair('No entendí, pero me comprometo a pagar mañana.')


def test_partial_component_without_other_terms_cannot_create_a_whole_plan():
    from test_r66_listening_and_deadlines import analysis
    from app.services.reviewed_payment_plan import extract_payment_plans
    from test_r66_listening_and_deadlines import REL,CLOSE
    text='Habla MRS. Soy yo. ¿Me indica el monto y la fecha del segundo pago? 1200 pesos el día 22 de noviembre.'+CLOSE
    assert not extract_payment_plans(text,relation=REL)
    result=analysis(text)
    assert result.metadata['negotiation_validation']['unresolved_accepted_plan']['review_required']
    assert not result.metadata['shared_classification']['aprobado']


def test_incomplete_offer_is_not_assumed_to_be_replaced_by_one_component(pipeline):
    row = pipeline['oferta_incompleta']
    assert row['classification'] == 'REVISAR'
    assert 'NEGOTIATION_INVALID_OR_UNCERTAIN' in row['codes']
    assert row['reason_matches_canonical']


def test_coordinated_amounts_survive_active_scope_in_all_outputs(pipeline):
    row = pipeline['dos_pagos_coordinados']
    assert row['amount'] == 3000
    assert row['classification'] == row['checkpoint_classification'] == row['excel_classification'] == 'APROBADO'
    assert row['date'] == '2026-11-21'
    assert row['reason_matches_canonical'] and row['source_copy_sha256_equal']
