"""El reporte de pago y una explicación de cancelación no son una negociación."""
import pytest

from app.models.transcriptions import TranscriptionModel
from app.services.analytics_service import AnalyticsService as A
from app.services.conversation_evidence import completed_payment


def analyze(text, status='MENSAJE CON FAMILIAR'):
    return A.analyze_transcription(TranscriptionModel('sample.ogg','sample.ogg',text,duration_seconds=120),
        {'estatus_grabacion':status,'asignacion':'1PV','pago_minimo':700,'saldo_total':1300,
         'fecha':'2026-10-29','vencimiento':'2026-11-25'})


@pytest.mark.parametrize('phrase', ['Ya se hizo un pago.', 'Ya se realizó el pago.', 'Ya se hizo el pago.'])
def test_past_payment_passive_form_is_recognized_without_assuming_payment_covers_minimum(phrase):
    a=analyze('Habla MRS. Es mi mujer. '+phrase+' Entonces, ¿lo realizó el domingo o el lunes? Lunes. '
              'Para cancelar el crédito, una vez reflejado el saldo restante, llame al número en el reverso.')
    n=a.metadata['negotiation_validation']
    assert n['completed_payment_evidence']['confirmed'] and n['payment_confirmation_case']
    assert n['prior_payment_total'] is None and not n['prior_payment_covers_minimum']
    assert n['promise_date'] is None and not n['payment_date_confirmed']
    assert not n['commitment_confirmed'] and not n['liquidation_detected']
    assert n['valid'] and not n['review_required'] and n['validacion_monto']=='NO APLICA'
    assert a.metadata['final_result']=='REVISAR'  # Sigue faltando recepción del recado.
    assert not a.metadata['status_validation']['recado_evidence']['confirmed_recado']


@pytest.mark.parametrize('phrase', [
    'No es cierto que ya se hizo un pago.', 'Si ya se hizo un pago, envíe su comprobante.',
    'Cuando ya se realizó el pago, se registra.', 'Dice que ya se hizo el pago.',
    'No sé si ya se hizo el pago.', 'Creo que ya se hizo un pago.',
    '¿Ya se hizo un pago?', 'Gestor: Ya se hizo un pago.', 'Se hará un pago mañana.',
])
def test_unverified_or_conditional_payment_is_not_a_confirmed_payment(phrase):
    assert not completed_payment(phrase)['confirmed']


def test_remaining_balance_alone_does_not_assert_regularization():
    a=analyze('Habla MRS. Soy su esposo. Para cancelar la tarjeta debe comunicarse '
              'al número del reverso una vez que el saldo restante esté cubierto.')
    n=a.metadata['negotiation_validation']
    assert n['validacion_monto']=='NO APLICA' and n['valid']
    assert not a.metadata['shared_classification']['aprobado']


def test_payment_report_does_not_waive_a_later_total_settlement_offer_in_early_mora():
    a=analyze('Habla MRS. Soy su esposo. Ya se hizo un pago. '
              'Gestor: Con este pago liquida su cuenta.')
    assert 'PEN004' in {p['id'] for p in a.metadata['penalties']}
    assert a.metadata['final_result']=='FALLA_GRAVE'


def test_unknown_payment_amount_for_holder_remains_pending():
    a=analyze('Habla MRS. Soy yo. Ya se hizo un pago.',status='NO DEFINE FECHA DE PAGO')
    assert a.metadata['negotiation_validation']['reported_payment_amount_pending']
    assert not a.metadata['shared_classification']['aprobado']


def test_actual_new_commitment_after_past_payment_keeps_amount_and_date_controls():
    a=analyze('Habla MRS. Soy yo. Ya se hizo un pago. '
              'Gestor: Le propongo pagar 1000 pesos mañana. '
              'Titular: Me comprometo a pagar 1000 pesos mañana.',status='CONVENIO')
    n=a.metadata['negotiation_validation']
    assert n['commitment_confirmed'] and not n['payment_confirmation_case']
    assert n['promise_date'] is not None
    assert not a.metadata['shared_classification']['aprobado']  # Aún faltan controles de convenio.


@pytest.mark.parametrize('phrase', ['Ya se hizo el pago ayer.', 'Ya se realizó el pago el domingo.'])
def test_passive_completed_payment_followup_does_not_require_a_new_commitment_or_payment_places(phrase):
    a=analyze('Habla MRS. Soy yo. '+phrase+
              ' ¿Cuenta con el comprobante? Lo tengo, fue por transferencia.',status='CONVENIO')
    n=a.metadata['negotiation_validation']
    assert n['payment_confirmation_case'] and n['payment_followup_case']
    assert not n['commitment_confirmed']
    assert not {'PEN009','PEN_CONV_LUGARES','PEN_CONV_TRANSFER_REV'} & {p['id'] for p in a.metadata['penalties']}
    assert a.metadata['convenio_payment_validation']['reported_transfer_only']


def test_passive_payment_report_does_not_waive_new_transfer_instructions():
    a=analyze('Habla MRS. Soy yo. Ya se hizo el pago ayer. ¿Tiene el comprobante? '
              'Gestor: Para el próximo pago transfiera a una cuenta BBVA 5551234567.',status='CONVENIO')
    assert not a.metadata['convenio_payment_validation']['reported_transfer_only']
    assert not a.metadata['shared_classification']['aprobado']
