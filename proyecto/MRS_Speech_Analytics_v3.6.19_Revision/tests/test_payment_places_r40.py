"""Ofertas de pago y listas partidas, sin ampliar el catálogo autorizado."""
import pytest

from test_operational_script_r39 import analyze


@pytest.mark.parametrize('phrase,expected', [
    ('Una vez que realiza el pago, ya sea directamente en tienda, farmacias de la Oro, '
     '7-11, Círculo K, tiendas 3B, Bulbor.',
     {'FARMACIAS DEL AHORRO', '7-ELEVEN', 'CIRCLE K', 'TIENDAS 3B', 'WOOLWORTH'}),
    ('El pago lo puede hacer en una tienda del sol, chedragui, farmacias de la Oro, kiosco.',
     {'TIENDAS DEL SOL', 'CHEDRAUI', 'FARMACIAS DEL AHORRO', 'KIOSKO'}),
    ('Lo puede ser el pago directamente en tienda o chedragui, farmacias de la Oro, kiosco.',
     {'CHEDRAUI', 'FARMACIAS DEL AHORRO', 'KIOSKO'}),
    ('Lo puede aplicar en alguna tienda de conveniencia. Normalmente las tiendas de '
     'conveniencia son de 7-11, kiosco, farmacias de la Oro, Abarray.',
     {'7-ELEVEN', 'KIOSKO', 'FARMACIAS DEL AHORRO', 'ABARREY'}),
    ('El pago ya se aplica directamente en tienda o en establecimientos autorizados. '
     'Los establecimientos autorizados son del Sol, Ulbor, Kiosco, Abarray.',
     {'TIENDAS DEL SOL', 'WOOLWORTH', 'KIOSKO', 'ABARREY'}),
    ('El pago ya se lo aplique por transferencia o en alguna tienda de conveniencia, '
     'los sitios de conveniencia son Ulbor, Kiosco, Abarray.',
     {'WOOLWORTH', 'KIOSKO', 'ABARREY'}),
    ('Lo haría directamente en tienda? Sí, directamente en tienda. También lo puede '
     'hacer en Farmacias de la Oro, QIOSCO, CIRCULO-K.',
     {'FARMACIAS DEL AHORRO', 'KIOSKO', 'CIRCLE K'}),
    ('Sus pagos son directamente en tienda? Tienda. También lo puede hacer lo que '
     'es en una... en Farmacias de la Oro, Kiosco, Círculo K extra 7-11.',
     {'FARMACIAS DEL AHORRO', 'KIOSKO', 'CIRCLE K', '7-ELEVEN'}),
    ('Puede realizarlo en farmacias de la Oro, Woolworth, Abarray, Del Sol, 7-Eleven, 7-24-Mix.',
     {'FARMACIAS DEL AHORRO', 'WOOLWORTH', 'ABARREY', 'TIENDAS DEL SOL', '7-ELEVEN', '7/24 MIX'}),
    ('Sus pagos los puede estar realizando directamente en tiendas, tiendas del Sol, '
     'farmacias de la Oro, tiendas 7-Eleven, Circulo-K, tiendas Neto, tiendas 3-B, farmacias Roma.',
     {'TIENDAS DEL SOL', 'FARMACIAS DEL AHORRO', '7-ELEVEN', 'CIRCLE K', 'TIENDAS NETO',
      'TIENDAS 3B', 'FARMACIAS ROMA'}),
    ('Recuerda que Suspago los puede estar realizando directamente en tiendas, '
     'tiendas del Sol, farmacias de la Oro, tiendas 7-Eleven, Circulo-K.',
     {'TIENDAS DEL SOL', 'FARMACIAS DEL AHORRO', '7-ELEVEN', 'CIRCLE K'}),
    ('El pago ya sea que se aplique directamente en tienda o en establecimientos '
     'autorizados que son del sol, Ulbor, 7-11, farmacias de la oro.',
     {'TIENDAS DEL SOL', 'WOOLWORTH', '7-ELEVEN', 'FARMACIAS DEL AHORRO'}),
    ('Usted también puede aplicar su pago a través de farmacias de la Oro, '
     'Tiendas del Sol, solicitando pago de servicios a Bradescard.',
     {'FARMACIAS DEL AHORRO', 'TIENDAS DEL SOL'}),
    ('Puede hacer su pago en tiendas Neto y farmacias Roma.',
     {'TIENDAS NETO', 'FARMACIAS ROMA'}),
    ('Puede realizar su pago en Chedraui y Kiosco para retirar su cuenta de cobranza.',
     {'CHEDRAUI', 'KIOSKO'}),
    ('Le recomiendo los lugares alternos; tenía que realizarlo en farmacias de la Oro, '
     'farmacias Isa y farmacias Roma.',
     {'FARMACIAS DEL AHORRO', 'FARMACIAS YZA', 'FARMACIAS ROMA'}),
    ('¿Algún familiar le ayuda a hacer su pago? ¿Lo puede realizar ahí en tienda? '
     '¿O también en un 7-11, farmacias de la Oro o CIRCULO-K?',
     {'7-ELEVEN', 'FARMACIAS DEL AHORRO', 'CIRCLE K'}),
    ('¿Dónde para realizar su pago? No sé si vaya a sucursal. Puede ser en tiendas '
     '3B, tiendas Neto, farmacias del ahorro, 7-eleven.',
     {'TIENDAS 3B', 'TIENDAS NETO', 'FARMACIAS DEL AHORRO', '7-ELEVEN'}),
    ('Únicamente es el pago hoy. Sin embargo, hay otros lugares, tiendas de '
     'conveniencia como Círculo K, 7-eleven.', {'CIRCLE K', '7-ELEVEN'}),
    ('Le reitero los establecimientos o puntos de pago. 724.000 farmacias de la Oro, '
     'Kiosco, Círculo K, farmacias Roma.',
     {'FARMACIAS DEL AHORRO', 'KIOSKO', 'CIRCLE K', 'FARMACIAS ROMA'}),
    ('Se puede realizar su pago en farmacias de la ahorro, tienda tres B y Chedragüy.',
     {'FARMACIAS DEL AHORRO', 'TIENDAS 3B', 'CHEDRAUI'}),
])
def test_conjugations_and_continued_lists_count_all_distinct_authorized_places(phrase, expected):
    result = analyze(phrase, estatus_grabacion='CONVENIO')
    places = result.metadata['convenio_payment_validation']
    assert set(places['authorized_places_detected']) == expected
    assert 'PEN_CONV_LUGARES' not in {p['id'] for p in result.metadata['penalties']}


@pytest.mark.parametrize('phrase', [
    'Puede hacer compras en Chedraui y Woolworth.',
    'Puede realizar una aclaración en Chedraui y Woolworth.',
    'Lo puede hacer en Chedraui y Woolworth para retirar dinero.',
    'Lo puede hacer en Chedraui y Woolworth para comprar comida.',
    'Su tarjeta es de C&A y Suburbia.',
    'Titular: El pago lo puede hacer en Chedraui y Woolworth.',
    'Gestor: No puede realizar el pago en Chedraui ni Woolworth.',
    'No lo puede hacer en Chedraui ni Woolworth.',
    'Puede pagar en Santander y Banamex.',
    'Chedraui y Woolworth.',
    'Puede pagar en estos establecimientos. Hablemos de otro asunto. Chedraui y Woolworth.',
    'No puede pagar en estos establecimientos. Chedraui. Woolworth.',
    'Puede ser en Chedraui y Woolworth.',
    'Hay otros lugares: Chedraui y Woolworth.',
    '¿Hizo el pago? Hablemos del domicilio. ¿Cómo está el clima? Puede ser en Chedraui y Woolworth.',
    'No puede realizarlo en establecimientos como Chedraui, Woolworth, Kiosco, '
    'farmacias del ahorro, Tiendas del Sol, 7-Eleven, Farmacias Roma ni Tiendas Neto.',
])
def test_other_actions_customer_origin_negation_and_bare_banks_do_not_create_offers(phrase):
    result = analyze(phrase, estatus_grabacion='CONVENIO')
    assert result.metadata['convenio_payment_validation']['authorized_places_count'] == 0


def test_aliases_and_hyphens_never_duplicate_a_brand_or_count_unapproved_stores():
    result = analyze('El pago lo puede hacer en 7-Eleven, 7 eleven, Seven Eleven, '
                     'Extra, Oxxo o un banco Santander.', estatus_grabacion='CONVENIO')
    assert result.metadata['convenio_payment_validation']['authorized_places_detected'] == ['7-ELEVEN']


def test_store_of_origin_before_new_offer_is_not_counted():
    result = analyze('Su tarjeta es de C&A y el pago lo puede hacer en Kiosco.',
                     estatus_grabacion='CONVENIO')
    assert result.metadata['convenio_payment_validation']['authorized_places_detected'] == ['KIOSKO']


def test_enumeration_does_not_cross_a_known_customer_turn():
    result = analyze('Gestor: El pago se realiza en establecimientos autorizados.\n'
                     'Titular: Chedraui y Woolworth.', estatus_grabacion='CONVENIO')
    assert result.metadata['convenio_payment_validation']['authorized_places_count'] == 0


def test_negative_first_option_does_not_erase_following_affirmative_offer():
    result = analyze('No le reciben el pago en C&A, lo puede hacer en Kiosko y Woolworth.',
                     estatus_grabacion='CONVENIO')
    assert set(result.metadata['convenio_payment_validation']['authorized_places_detected']) == {'KIOSKO', 'WOOLWORTH'}


@pytest.mark.parametrize('text, expected', [
    ('Si no lo puede realizar en tiendas del Sol o Woolworth, lo puede realizar '
     'en Farmacias del Ahorro, 7-Eleven y Farmacias Roma.',
     {'FARMACIAS DEL AHORRO', '7-ELEVEN', 'FARMACIAS ROMA'}),
    ('Si usted no puede realizar el pago por la aplicación pueden ir a '
     'Farmacias de la Oro, 7-Eleven, Circulo-K, Tiendas 3B a realizar el pago.',
     {'FARMACIAS DEL AHORRO', '7-ELEVEN', 'CIRCLE K', 'TIENDAS 3B'}),
])
def test_conditional_unavailable_channel_does_not_cancel_authorized_alternatives(text, expected):
    result = analyze(text, estatus_grabacion='CONVENIO')
    assert set(result.metadata['convenio_payment_validation']['authorized_places_detected']) == expected


def test_phrase_role_and_original_segment_times_are_preserved():
    from app.services.conversation_evidence import payment_places
    text = 'El pago lo puede hacer en Circle-K y 7-Eleven.'
    result = payment_places(text, [{'text': text, 'start': 12.5, 'end': 20,
                                  'speaker_role': 'GESTOR'}],
                            {'CIRCLE K': ['circle k'], '7-ELEVEN': ['7 eleven']})
    assert {r['phrase'] for r in result} == {'circle-k', '7-eleven'}
    assert all(r['speaker_role'] == 'GESTOR' and r['start'] == 12.5 and r['end'] == 20 for r in result)
