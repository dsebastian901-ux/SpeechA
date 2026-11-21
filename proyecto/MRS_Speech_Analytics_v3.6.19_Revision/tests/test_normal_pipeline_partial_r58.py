"""Las correcciones se ejecutan desde un proyecto nuevo, sin reanálisis externo."""
import json
from pathlib import Path
import wave
import pytest
from openpyxl import Workbook,load_workbook
from app.services.batch_service import BatchService
from app.services.whisper_service import whisper_service


@pytest.mark.parametrize('text,expected',[
    ('Tercero: Soy su madre Gestor: Tiene una deuda de 1500 pesos','FALLA_GRAVE'),
    ('Gestor: Habla MRS. Titular: Soy yo. Gestor: Esto se interpreta como un chisme.','REVISAR'),
    ('Gestor: Habla MRS. Titular: Soy yo. Gestor: Conunachingada.','FALLA_GRAVE'),
])
def test_new_normal_batch_uses_shared_corrected_extractors(tmp_path,monkeypatch,text,expected):
    path=tmp_path/'synthetic.wav'
    with wave.open(str(path),'wb')as handle:
        handle.setparams((1,2,16000,0,'NONE','not compressed'));handle.writeframes(b'\0\0'*160)
    book=Workbook();sheet=book.active;sheet.title='Relacion_Audios'
    sheet.append(['archivo_original','nombre_final','numero_de_tarjeta','estatus_grabacion','gestor','supervisor','asignacion','fecha'])
    sheet.append([path.name,'1234567890123456_C1_352_3EROS_GESTOR_MRS_20261120','1234567890123456','MENSAJE CON FAMILIAR','Gestor sintético','Supervisor sintético','C1','2026-11-20'])
    excel=tmp_path/'synthetic.xlsx';book.save(excel);book.close();before=excel.read_bytes();asr_calls=[]
    data={'archivo':path.name,'ruta_audio':str(path),'texto':text,'segmentos':[],'duracion_segundos':90}
    def asr(audio_path,output_directory):
        asr_calls.append(audio_path)
        output=Path(output_directory)/'synthetic.json';output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(data));return {'ruta_json':str(output)}
    monkeypatch.setattr(whisper_service,'transcribe_audio',asr)
    batch=BatchService();batch.set_files([path]);batch.set_relation_excel(excel)
    batch.process_all(tmp_path/'new_project/02_Audios/Transcripciones')
    item=batch.items[0]
    assert asr_calls==[str(path)]
    assert item['classification']['clasificacion']==expected
    assert item['result']==data and excel.read_bytes()==before
    assert Path(item['classified_audio_path']).read_bytes()==path.read_bytes()
    assert Path(batch.last_report_path).is_file()
    assert Path(batch.last_nonpayment_report_path).is_file()
