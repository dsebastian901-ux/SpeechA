"""Regresión de los hallazgos de las 46 pendientes; ejemplos sintéticos."""
import pytest
from app.services.conversation_evidence import holder_confirmation,payment_commitment,assess_home_recovery_warning
from app.services.installment_validation import installment_plan
from app.services.treatment_evidence import mistreatment_reports,dismissive_message_evidence
from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A

@pytest.mark.parametrize('reply',[
 'Este mes tengo el pago mínimo de 900, es lo que voy a pagar.',
 'El mes pasado tenía un pago mínimo y este mes tengo el pago mínimo de 900.',
 'Yo quiero pagarlo, pero todavía estoy esperando mis incentivos.',
 'No he podido ir a pagar todavía.',
 'Es que no les voy a completar, me atrasé, pero no voy a poder.',
])
def test_personal_financial_conversation_after_named_question(reply):
 assert holder_confirmation('Buenas tardes con la señorita Persona Ejemplo. Habla MRS sobre su tarjeta. '+reply)['confirmed']

@pytest.mark.parametrize('reply',[
 'Soy su hija. Este mes tengo el pago mínimo de 900.',
 'Yo quiero pagarlo a nombre de mi padre.',
 'Si yo tuviera este mes el pago mínimo, lo revisaría.',
 'Gestor: Este mes tengo el pago mínimo de 900.',
 'No está aquí. No he podido ir a pagar todavía.',
])
def test_new_identity_phrases_preserve_counterevidence(reply):
 assert not holder_confirmation('Buenas tardes con la señorita Persona Ejemplo. Habla MRS sobre su tarjeta. '+reply)['confirmed']


def test_named_question_ending_in_comma_and_thanks_still_needs_own_finances():
 opening='Me voy a tener que comunicar con la señorita Persona Ejemplo, gracias. Habla MRS sobre su tarjeta. '
 assert holder_confirmation(opening+'No les voy a completar, me atrasé.')['confirmed']
 assert not holder_confirmation(opening+'Gracias por marcar.')['confirmed']


def test_intervening_question_cannot_turn_own_card_use_denial_into_payment_acceptance():
 assert not payment_commitment('¿Podemos contar con su pago? ¿Cuál pago? Si yo no he usado esa tarjeta.')['accepted']


def test_later_payment_confirmation_supersedes_uncertain_earlier_proposal():
 result=payment_commitment('No sabría decirle si le voy a pagar los 7000. ¿Confirma su pago de 3854 mañana? Sí, por favor.')
 assert result['accepted'] and not result['conditional']
 assert '3854' in result['evidence']


def test_explicit_inability_to_complete_amount_is_not_a_promise():
 result=payment_commitment('Le ofrecen 4500 para mañana. No les voy a completar. No voy a poder.')
 assert result['declined'] and not result['accepted']


def test_speech_amount_for_later_three_payment_proposal_is_not_previous_two_payment_total():
 result=installment_plan('dos pagos de cinco mil cuatrocientos sesenta y cinco pesos. tres pagos de tres mil seiscientos cuarenta y tres. Sería en tres, por favor.',[])
 assert result['amounts']==[3643.0]*3 and result['total']==10929


def test_administrative_today_does_not_replace_explicit_payment_day():
 result=A._extract_payment_promise_date_details('Hoy me confirmaron la falta de movimiento de su pago. Tendría que pagar el monto antes del día 6. Después se actualiza su estado de cuenta.','2026-11-04')
 assert result['date'].isoformat()=='2026-11-06'


def test_calendar_number_after_payment_future_is_not_money():
 text='Soy yo. Lo voy a estar realizando en 15. Me pueden ayudar a tener la fecha para el día 15 para hacer el pago correspondiente, de hecho creo que voy a abonar un poquito más.'
 a=A.analyze_transcription(TranscriptionModel.from_dict({'archivo':'synthetic.wav','texto':text,'duracion_segundos':100}),{'fecha':'2026-11-04','asignacion':'1PV','pago_minimo':1000,'saldo_total':3000})
 assert a.metadata['negotiation_validation']['monto_detectado'] is None

@pytest.mark.parametrize('phrase',[
 'A ese número nunca me contesta.',
 'El soporte nunca me contestan.',
 'Me cortaban la llamada y volvía a marcar.',
 'Le dije que no y me colgaron.',
 'Nadie me quiso resolver en el banco.',
 'Me habló bien enojado que fuera corriendo a pagar.',
 'Casi me mentaba la madre.',
 'Los del jurídico muy groseros, ni me dejan hablar.',
 'Llevo dos meses tratando de arreglar y no me contestan.',
])
def test_customer_reports_of_bad_service_are_retained(phrase):
 assert mistreatment_reports('Titular: '+phrase,[],[])

@pytest.mark.parametrize('phrase',[
 'Gestor: Nunca me contestan.',
 'Titular: Mi esposa nunca me contesta.',
 'Titular: No me colgaron.',
 'Titular: No es cierto que me cortaban la llamada.',
])
def test_known_agent_family_and_denials_do_not_become_customer_complaints(phrase):
 assert not mistreatment_reports(phrase,[],[])

@pytest.mark.parametrize('phrase',[
 'Qué falta de educación, señor.',
 'Ese es el problema de usted.',
 'Qué responsable señor, pero bueno.',
 'Ni le puse una pistola.',
])
def test_contextual_confrontation_requires_review_without_certifying_tone(phrase):
 assert dismissive_message_evidence('Gestor: '+phrase)
 assert not dismissive_message_evidence('Titular: '+phrase)


def test_visit_for_recovery_in_early_mora_is_reviewed_without_inventing_voice():
 r=assess_home_recovery_warning('La visita ocular del día 6 para la recuperación total de su saldo.',[], '1PV')
 assert r['review_required'] and not r['confirmed']
 assert not assess_home_recovery_warning('La visita ocular del día 6 para la recuperación total de su saldo.',[],'4PV')['review_required']


def test_own_budget_reply_can_follow_a_temporal_discussion_of_the_amount_to_cover():
 text='Buenas tardes con la señorita Persona Ejemplo, gracias. Sobre el pago de su tarjeta. Tendría que ser en esas dos fechas para que quedaran cubiertos los 4500. Es que no les voy a completar, me atrasé.'
 assert holder_confirmation(text)['confirmed']


def test_exclamatory_profanity_is_not_silently_approved():
 from app.services.treatment_evidence import offensive_asr_variants
 assert offensive_asr_variants('Ah, chingas.')
 assert not offensive_asr_variants('La señora Chingas solicita información.')
