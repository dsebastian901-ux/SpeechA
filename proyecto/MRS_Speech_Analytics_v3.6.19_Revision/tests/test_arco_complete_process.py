"""ARCO obligatorio completo y reconocimiento contextual de NO CONOCEN."""
import pytest
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.arco_validation import document_requests,qualitative_line_tenure
from app.services.conversation_evidence import unknown_recipient_response


RIGHTS='Puede ejercer sus derechos ARCO.'
EMAIL='El correo es privacidad1@bradesco.com.mx.'
DOCS='Debe enviar INE y comprobante de su línea telefónica.'
AGE='Tengo dos años con esta línea.'


def analyze(tail,**context):
    return A.analyze_transcription(TranscriptionModel('sample.ogg','sample.ogg',
        'Habla MRS. No la conocemos aquí. '+tail,duration_seconds=120),
        {'estatus_grabacion':'NO CONOCEN A DEUDOR',**context})


@pytest.mark.parametrize('right',['Puede ejercer sus derechos ARCO.',
    'Para ejercer su derecho ARCO.', 'Para hacer efectivo su derecho ARCO.'])
def test_complete_process_names_arco_and_requires_email_and_both_documents(right):
    a=analyze(' '.join([right,EMAIL,DOCS,AGE]))
    q=a.metadata['arco_validation']
    assert q['rights_mentioned'] and q['complete_procedure'] and q['valid']
    assert q['ine_requested'] and q['line_proof_requested']
    assert a.metadata['quality_contact_type']=='NO CONOCEN A DEUDOR'
    assert a.metadata['final_result']=='APROBADO'


def test_baja_instructions_are_not_a_substitute_for_naming_arco_rights():
    a=analyze('Puede solicitar la baja de su número de la base de datos. '+EMAIL+' '+DOCS+' '+AGE)
    q=a.metadata['arco_validation']
    assert q['partial_guidance_requires_audio'] and not q['complete_procedure']
    assert not q['rights_mentioned'] and not q['valid']
    assert a.metadata['final_result']=='REVISAR'
    assert 'PEN_ARCO_OMISION' not in {p['id'] for p in a.metadata['penalties']}
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('documents',[
    'Envíe INE.', 'Envíe comprobante de teléfono.',
    'Envíe identificación oficial o comprobante de teléfono.',
    'Envíe comprobante de la línea o INE.',
    'No envíe INE. Envíe comprobante de su línea.',
    'Envíe INE. No envíe comprobante de su línea.',
    'Nunca envíe INE. Envíe comprobante de su línea.',
    'Evite enviar INE. Envíe comprobante de su línea.',
])
def test_missing_or_alternative_documents_do_not_satisfy_the_complete_process(documents):
    a=analyze(' '.join([RIGHTS,EMAIL,documents,AGE]))
    assert not a.metadata['arco_validation']['both_documents_requested']
    assert not a.metadata['arco_validation']['valid']
    assert not a.metadata['shared_classification']['aprobado']


@pytest.mark.parametrize('phrase',['INE y comprobante de teléfono.',
    'Cliente: Debe enviar INE y comprobante de teléfono.',
    'Yo puedo enviar INE y comprobante de teléfono.',
    '¿Yo debo enviar INE y comprobante de teléfono?'])
def test_document_mentions_or_known_customer_words_are_not_agent_requests(phrase):
    assert not document_requests(phrase)['both_documents_requested']


def test_document_instruction_can_continue_in_the_next_sentence():
    q=document_requests('Aquí va a proporcionar el comprobante de su línea telefónica. '
                        'Y lo que es su identificación oficial.')
    assert q['both_documents_requested']


def test_attaching_id_instruction_does_not_invent_line_proof_from_a_number():
    q=document_requests('Adjuntando su número personal y su INE.')
    assert q['ine_requested']
    assert not q['line_proof_requested'] and not q['both_documents_requested']


def test_later_clear_and_instruction_replaces_earlier_or_alternative():
    q=document_requests('Envíe INE o comprobante de teléfono. '
        'Corrijo, debe enviar INE y comprobante de teléfono.')
    assert q['both_documents_requested'] and not q['documents_as_alternatives']


@pytest.mark.parametrize('tail',[
    EMAIL+' '+DOCS+' '+AGE,
    'Puede ejercer ARCO. '+EMAIL+' '+DOCS+' '+AGE,
    RIGHTS+' '+DOCS+' '+AGE,
    RIGHTS+' '+EMAIL+' '+DOCS,
])
def test_partial_process_never_approves_even_when_excel_status_is_empty(tail):
    a=analyze(tail,estatus_grabacion='')
    assert not a.metadata['shared_classification']['aprobado']


def test_omission_without_procedural_evidence_keeps_the_critical_block():
    a=analyze(EMAIL)
    assert any(p['id']=='PEN_ARCO_OMISION' and p['invalidates'] for p in a.metadata['penalties'])
    assert a.metadata['final_result']=='FALLA_GRAVE'


@pytest.mark.parametrize('guidance',[EMAIL,'Debe enviar INE.'])
def test_arco_reference_with_partial_guidance_requires_review_without_confirming_compliance(guidance):
    a=analyze('Puede ejercer ARCO. '+guidance+' '+AGE)
    q=a.metadata['arco_validation']
    assert q['partial_guidance_requires_audio']
    assert not q['rights_mentioned'] and not q['complete_procedure'] and not q['valid']
    assert a.metadata['final_result']=='REVISAR'
    assert not any(p['invalidates'] and p['id']=='PEN_ARCO_OMISION' for p in a.metadata['penalties'])


def test_bare_arco_reference_does_not_remove_critical_omission():
    a=analyze('ARCO. '+AGE)
    assert not a.metadata['arco_validation']['partial_guidance_requires_audio']
    assert a.metadata['final_result']=='FALLA_GRAVE'


def test_explicit_denial_is_not_hidden_by_baja_and_document_instructions():
    a=analyze('No voy a explicar el proceso ARCO. Puede solicitar la baja de su número de la base de datos. '
              +EMAIL+' '+DOCS+' '+AGE)
    assert a.metadata['arco_validation']['process_denied']
    assert a.metadata['final_result']=='FALLA_GRAVE'


@pytest.mark.parametrize('opening',['No la conocemos aquí.','No lo conocemos.','No conocemos a esa persona.'])
def test_explicit_plural_unknown_response(opening):
    r=unknown_recipient_response(opening)
    assert r['confirmed'] and r['method']=='DECLARACION_PLURAL_DESCONOCIMIENTO'


@pytest.mark.parametrize('text',[
    '¿No la conocemos aquí?', 'Gestor: No la conocemos aquí.',
    'Dice que no la conocemos aquí.', 'No la conocemos aquí. Sí la conozco.',
    'Soy su hermana. No la conocemos aquí.', 'Soy yo. No la conocemos aquí.',
])
def test_quoted_question_agent_or_contradictory_plural_is_not_unknown_confirmation(text):
    assert not unknown_recipient_response(text)['confirmed']


@pytest.mark.parametrize('answer',['Toda la vida.','Uy, señor, toda la vida.','Muchos años.'])
def test_qualitative_line_tenure_is_not_an_invented_numeric_age(answer):
    r=qualitative_line_tenure('¿Usted hace cuánto tiempo cuenta con su línea telefónica? '+answer)
    assert r['confirmed'] and r['numeric_years'] is None


@pytest.mark.parametrize('text',[
    '¿Hace cuánto tiempo tiene esta línea?',
    '¿Hace cuánto tiempo tiene esta línea? Gestor: Toda la vida.',
    '¿Cuánto tiempo tiene este dolor? Toda la vida.',
    '¿Hace cuánto tiempo tiene esta línea? Toda la vida no, apenas llegué.',
])
def test_missing_agent_wrong_question_or_contradictory_tenure_does_not_confirm(text):
    assert not qualitative_line_tenure(text)['confirmed']


@pytest.mark.parametrize('problem',[
    'Gestor: Tiene una deuda de 500 pesos.',
    'Me trataron mal.',
    'La tarjeta termina en 9999.',
])
def test_complete_arco_does_not_exempt_privacy_treatment_or_wrong_reference(problem):
    a=analyze(' '.join([RIGHTS,EMAIL,DOCS,AGE,problem]),numero_de_tarjeta='1234567890123456')
    assert not a.metadata['shared_classification']['aprobado']


def test_uncertain_dictated_email_is_not_reconstructed_to_the_expected_domain():
    a=analyze('Puede solicitar la baja de su número de la base de datos. '
        'Es privacidad, número uno, arroba, bradesco, punto con punto MX. '
        'Aquí va a proporcionar el comprobante de su línea telefónica. '
        'Y lo que es su identificación oficial. '
        '¿Hace cuánto tiempo cuenta con su línea telefónica? Uy, señor, toda la vida.')
    q=a.metadata['arco_validation']
    assert q['both_documents_requested'] and q['line_tenure_confirmed']
    assert not q['rights_mentioned'] and not q['email_given']
    assert a.metadata['final_result']=='REVISAR'


@pytest.mark.parametrize('text,expected',[
    (' '.join([RIGHTS,EMAIL,DOCS,AGE]),['SI','SI','SI','SI','SI']),
    ('Puede solicitar la baja de su número de la base de datos. '+EMAIL+' '+DOCS+' '+AGE,
     ['NO','SI','SI','SI','NO']),
    (RIGHTS+' '+EMAIL+' Envíe INE. '+AGE,['SI','SI','SI','NO','NO']),
])
def test_report_distinguishes_each_required_step_without_certifying_partial_process(text,expected):
    from app.services.batch_report_service import BatchReportService as B
    a=analyze(text)
    row=B._row_from_item({'path':'sample.ogg','analytics_metadata':a.metadata})
    assert [row[k] for k in B.HEADERS[-5:]]==expected


def test_report_shows_non_applicable_arco_for_an_unrelated_holder_call():
    from app.services.batch_report_service import BatchReportService as B
    a=A.analyze_transcription(TranscriptionModel('sample.ogg','sample.ogg',
        'Habla MRS. Soy el titular.',duration_seconds=120),{})
    row=B._row_from_item({'path':'sample.ogg','analytics_metadata':a.metadata})
    assert [row[k] for k in B.HEADERS[-5:]]==['N/A']*5


def test_both_report_modes_retain_previous_financial_and_audio_columns_before_arco():
    from app.services.batch_report_service import BatchReportService as B
    previous=['Parcialidades finales confirmadas','Historial de propuestas de parcialidades',
              'Lectura adicional audio','Alertas lectura ASR','Riesgos lectura adicional']
    for headers in (B.HEADERS,B.MODE_B_HEADERS):
        assert headers[-10:-5]==previous
        assert headers[-5:]==B.ARCO_HEADERS
        assert len(headers)==len(set(headers))
