"""La confirmación nominal «¿usted es X? sí» no debe generar REVISAR sin razón."""
import pytest
from app.services.conversation_evidence import holder_confirmation


@pytest.mark.parametrize("text", [
    "Busco a González Vargas Guadalupe. Sí. ¿Usted es Guadalupe? Sí, dígame.",
    "Me comunica con Sánchez López María Teresa. ¿Quién habla? "
    "Habla MRS. ¿Usted es María Teresa? Sí.",
    "Busco a Ramírez Morales Miguel Ángel. ¿Perdón? "
    "¿Usted es Miguel Ángel? Sí.",
])
def test_explicit_second_identity_response(text):
    evidence = holder_confirmation(text)
    assert evidence["confirmed"]
    assert evidence["method"] == "CONFIRMACION_NOMINAL_SEGUNDO_PASO"


@pytest.mark.parametrize("text", [
    "Busco a González Vargas Guadalupe. ¿Usted es Guadalupe? No.",
    "Busco a González Vargas Guadalupe. ¿Usted es Guadalupe? Sí, no está aquí.",
    "Busco a González Vargas Guadalupe. ¿Usted es su familiar? Sí.",
    "¿Usted es Guadalupe? Sí.",
    "Busco a González Vargas Guadalupe. ¿Usted es María? Sí.",
])
def test_do_not_assume_titular_without_identity_and_no_contradiction(text):
    result = holder_confirmation(text)
    assert not result["confirmed"]


def test_role_explicitly_third_party_never_confirms_holder():
    text = "Busco a González Vargas Guadalupe. ¿Usted es Guadalupe? Sí."
    segments = [{"texto": text, "inicio": 0, "fin": 12,
                 "speaker_role": "TERCERO"}]
    assert not holder_confirmation(text, segments)["confirmed"]
