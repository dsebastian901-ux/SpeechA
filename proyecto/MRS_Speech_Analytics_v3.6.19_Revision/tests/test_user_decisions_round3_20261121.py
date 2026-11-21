"""Decisiones adicionales de monitoreo, lote de 50 respuestas.

Escenarios con datos sintéticos; no sustituyen validación acústica ni QA Windows.
"""
from pathlib import Path
import pytest

from app.services.operational_outcome_resolution import (
    offered_payment_alternatives, reported_unauthorized_venue,
)
from app.services.batch_service import BatchService
from app.services.analytics_service import AnalyticsService as A
from app.models.transcriptions import TranscriptionModel


def _analyze(text, status="CONVENIO"):
    return A.analyze_transcription(TranscriptionModel.from_dict({
        "archivo":"llamada_sintetica.ogg","texto":text,"duracion_segundos":110
    }), {"numero_de_tarjeta":"1234567890123456","nombre_final":
          "1234567890123456_1PV_352_PP_PERSONA_MRS_20261121",
          "estatus_grabacion":status,"asignacion":"1PV",
          "pago_minimo":"1000","saldo_total":"3000",
          "fecha":"2026-11-21","vencimiento":"2026-11-30","corte":"23"})


def test_hangup_overrides_previously_accepted_convenio():
    text=("Gestor: Habla MRS. Titular: Soy yo. "
          "Gestor: ¿Confirma pagar 1000 pesos el 25 de noviembre? "
          "Titular: Sí, me comprometo a pagar 1000 pesos el 25 de noviembre. "
          "Titular: Ya le voy a colgar.")
    status=_analyze(text).metadata["status_validation"]
    assert status["detected_status"]=="NO DEFINE FECHA DE PAGO"


def test_question_alone_is_not_an_alternative_to_save_a_hangup():
    text=("Gestor: Habla MRS. Titular: Soy yo. "
          "Gestor: ¿Cuánto puede pagar? Titular: Voy a colgar.")
    assert not offered_payment_alternatives(text,before_hangup=True)["confirmed"]
    assert _analyze(text,"TITULAR CUELGA").metadata["status_validation"]["detected_status"]=="TITULAR CUELGA"


def test_minimum_payment_offer_counts_as_an_alternative():
    text=("Gestor: Habla MRS. Titular: Soy yo. "
          "Gestor: El pago mínimo es 1000 pesos. Titular: Voy a colgar.")
    assert offered_payment_alternatives(text,before_hangup=True)["confirmed"]
    assert _analyze(text,"TITULAR CUELGA").metadata["status_validation"]["detected_status"]=="NO DEFINE FECHA DE PAGO"


@pytest.mark.parametrize("phrase,expected",[
    ("Titular: Ya pagué 500 pesos en OXXO.", True),
    ("Titular: Hice el pago en Elektra ayer.", True),
    ("Gestor: Le recomiendo pagar en OXXO.", False),
    ("Titular: No pagué en OXXO.", False),
])
def test_venue_is_from_reported_holder_payment_not_agent_instruction(phrase,expected):
    assert reported_unauthorized_venue(phrase)["confirmed"] is expected


@pytest.mark.parametrize("metadata,subdir",[
    ({"convenio_payment_validation":{"prior_unauthorized_venue":{"confirmed":True}}},
     "REVISAR"),
    ({"card_validation":{"result":"REVISAR - REFERENCIA DISTINTA"}},
     "REFERENCIA_POR_CONFIRMAR"),
])
def test_special_output_keeps_underlying_quality_and_original(tmp_path,metadata,subdir):
    source=tmp_path/"llamada_sintetica.ogg"
    source.write_bytes(b"OggS synthetic binary")
    item={"path":str(source),"analytics_metadata":metadata}
    decision={"clasificacion":"REVISAR","aprobado":False}
    batch=BatchService.__new__(BatchService)
    output=Path(batch._copy_classified_audio(item,None,decision,
        tmp_path/"proyecto"/"Transcripciones"))
    assert output.parent.name==subdir
    assert output.parent.parent.name=="LUGARES_NO_AUTORIZADOS"
    assert output.read_bytes()==source.read_bytes()


@pytest.mark.parametrize('person,expected',[
    ('Soy su hermana','MENSAJE CON FAMILIAR'),
    ('Soy compañera de trabajo','MENSAJE EN TRABAJO'),
    ('Soy su vecina','MENSAJE CON TERCERO'),
])
def test_recado_received_is_recado_even_when_recipient_cannot_contact_holder(person,expected):
    text=('Gestor: Habla MRS. ¿Le puedo dejar un recado? '
          f'Tercero: {person}. Sí, dígame. '
          'Gestor: Por favor, dígale que se comunique con nosotros. '
          'Tercero: Sí, recibí el recado, pero no tengo forma de contactarla.')
    a=_analyze(text,expected)
    sv=a.metadata['status_validation']
    assert sv['detected_status']==expected
    assert a.metadata['message_workflow_validation']['recado_aceptado_sin_poder_transmitir']
    assert not a.metadata['message_workflow_validation']['callback_available']
    assert sv['evidence_method']=='RECADO_RECIBIDO_SIN_POSIBILIDAD_DE_TRANSMITIR'


def test_no_contact_without_recado_accepted_is_not_false_recado():
    text=('Gestor: Habla MRS. ¿Le puedo dejar un recado? '
          'Tercero: Soy su hermana. No quiero recibir el recado; '
          'además, no tengo forma de contactarla.')
    a=_analyze(text,'SE NIEGAN A TOMAR RECADO')
    assert a.metadata['status_validation']['detected_status']!='MENSAJE CON FAMILIAR'
    assert not a.metadata['message_workflow_validation']['recado_aceptado_sin_poder_transmitir']
