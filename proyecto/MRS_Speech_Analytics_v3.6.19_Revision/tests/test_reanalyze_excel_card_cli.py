"""El reanálisis autorizado corrige solo el nombre en copia y no exige releer audio."""
import json
from pathlib import Path
import sys

from tools.reanalyze_checkpoint import main


def test_authorized_cli_uses_excel_card_without_asking_for_additional_readings(tmp_path,monkeypatch,capsys):
    source=tmp_path/'source.json'
    item={'file_name':'sample.ogg','result':{'archivo':'sample.ogg','texto':
        'Habla MRS. Soy su hermana. ¿Podré dejar un recado? Sí. Que se comunique al número telefónico 5551234567.',
        'duracion_segundos':120,'segmentos':[]},'relation':{
        'estatus_grabacion':'MENSAJE CON FAMILIAR','numero_de_tarjeta':'1234567890123456',
        'nombre_final':'0001234567890123000_1PV_REF'},'classification':{'puntaje_minimo':80}}
    source.write_text(json.dumps({'items':[item]}),encoding='utf-8');raw=source.read_bytes()
    out=tmp_path/'out'
    monkeypatch.setattr(sys,'argv',['reanalyze_checkpoint.py','--checkpoint',str(source),
                                   '--output-dir',str(out),'--use-excel-card'])
    main()
    outputs=list(out.glob('Checkpoint_*.json'));assert len(outputs)==1
    actual=json.loads(outputs[0].read_text(encoding='utf-8'))['items'][0]
    assert source.read_bytes()==raw
    assert actual['result']==item['result']
    assert actual['relation']==dict(item['relation'],nombre_final='0001234567890123456_1PV_REF')
    assert actual['classification']['clasificacion']=='APROBADO'
    assert actual['output_name_review']['source']=='EXPLICIT_USER_CHOICE_NUMERO_DE_TARJETA'
    assert not actual['analytics_metadata']['account_source_validation']['review_required']
    assert not actual.get('audio_block_evidence')
    assert 'No se ejecutó Whisper' in capsys.readouterr().out
