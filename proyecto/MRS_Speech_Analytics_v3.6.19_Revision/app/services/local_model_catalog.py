"""Importación de Whisper CTranslate2 desde una carpeta local, sin red."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import tempfile

from app.config.settings import DATA_DIR
from app.services.access_service import require

MODEL_SHAPES={'tiny':(4,384),'base':(6,512),'small':(12,768),'medium':(24,1024),
              'large-v2':(32,1280),'large-v3':(32,1280)}
FILES=('config.json','model.bin','tokenizer.json')
OPTIONAL=('vocabulary.json','preprocessor_config.json')
MANIFEST='mrs_model_manifest.json'


def sha256(path):
    hasher=hashlib.sha256()
    with Path(path).open('rb')as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):hasher.update(block)
    return hasher.hexdigest()


def model_architecture(path):
    """Lee únicamente cabeceras CT2 v6; no ejecuta código ni carga los pesos."""
    path=Path(path);size=path.stat().st_size
    with path.open('rb')as handle:
        def read(count):
            value=handle.read(count)
            if len(value)!=count:raise ValueError('Modelo CTranslate2 truncado.')
            return value
        def number():return struct.unpack('<I',read(4))[0]
        def string():
            length=struct.unpack('<H',read(2))[0]
            if not 1<=length<=4096:raise ValueError('Cabecera de modelo inválida.')
            raw=read(length)
            if raw[-1:]!=b'\0':raise ValueError('Cabecera de modelo inválida.')
            return raw[:-1].decode('utf-8')
        if number()!=6:raise ValueError('Importación compatible con modelos CTranslate2 versión binaria 6.')
        if string()!='WhisperSpec':raise ValueError('El archivo no contiene un modelo Whisper CTranslate2.')
        revision=number();count=number();variables={}
        if not 1<=count<=100000:raise ValueError('Cantidad de variables inválida.')
        for _ in range(count):
            name=string();rank=read(1)[0]
            if rank>8:raise ValueError('Dimensiones de modelo inválidas.')
            shape=tuple(number()for _ in range(rank));dtype=read(1)[0];length=number()
            if dtype>8 or handle.tell()+length>size or name in variables:raise ValueError('Pesos de modelo inválidos o truncados.')
            variables[name]=shape;handle.seek(length,1)
    def layers(side):return len({int(m[1])for name in variables if(m:=re.match(side+r'/layer_(\d+)/',name))})
    convolution=variables.get('encoder/conv1/weight',())
    if len(convolution)!=3:raise ValueError('Falta la arquitectura del encoder Whisper.')
    return {'encoder_layers':layers('encoder'),'decoder_layers':layers('decoder'),
            'hidden_size':convolution[0],'mel_bins':convolution[1],'ct2_revision':revision}


def inspect_model(source,name):
    if name not in MODEL_SHAPES:raise ValueError('Seleccione un modelo de la lista disponible.')
    source=Path(source)
    for file in FILES:
        path=source/file
        if path.is_symlink()or not path.is_file()or path.stat().st_size==0:
            raise ValueError('Modelo local incompleto: '+file+'. Se requiere formato Faster-Whisper/CTranslate2, no ONNX.')
    for file in ('config.json','tokenizer.json'):
        if not isinstance(json.loads((source/file).read_text(encoding='utf-8')),dict):raise ValueError('Archivo de modelo inválido: '+file)
    architecture=model_architecture(source/'model.bin');layers,hidden=MODEL_SHAPES[name]
    if (architecture['encoder_layers'],architecture['decoder_layers'],architecture['hidden_size'])!=(layers,layers,hidden):
        raise ValueError('Los pesos no corresponden al modelo '+name+'; no se cambiará su nombre para simularlo.')
    expected_mels=128 if name=='large-v3' else 80
    if architecture['mel_bins']!=expected_mels:raise ValueError('Entrada acústica incompatible con el modelo seleccionado.')
    return architecture


def imported_model_info(path,verify=False):
    path=Path(path);manifest=path/MANIFEST
    if not manifest.exists():return None
    data=json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(data,dict)or data.get('schema')!=1 or data.get('model_name')not in MODEL_SHAPES:
        raise ValueError('Manifiesto del modelo local inválido.')
    hashes=data.get('files_sha256')
    if not isinstance(hashes,dict)or not set(FILES)<=set(hashes)or not set(hashes)<=set(FILES+OPTIONAL):
        raise ValueError('Archivos del manifiesto local inválidos.')
    if any(not isinstance(v,str)or not re.fullmatch('[0-9a-f]{64}',v)for v in hashes.values()):
        raise ValueError('Huellas del modelo local inválidas.')
    if verify:
        for file,expected in hashes.items():
            if (path/file).is_symlink()or not(path/file).is_file()or sha256(path/file)!=expected:
                raise ValueError('El modelo local cambió o está incompleto: '+file)
    return data


def install_local_model(source,name):
    """Publicar solo después de validar copia y cargar realmente el modelo."""
    require('settings')
    architecture=inspect_model(source,name);source=Path(source)
    root=Path(DATA_DIR)/'models';root.mkdir(parents=True,exist_ok=True);target=root/name
    if target.exists():raise FileExistsError('Ya existe un modelo '+name+'. Se conserva intacto; importe en una instalación sin ese modelo.')
    stage=Path(tempfile.mkdtemp(prefix='.'+name+'-',dir=root))
    try:
        hashes={}
        for file in FILES+OPTIONAL:
            origin=source/file
            if not origin.exists():continue
            if origin.is_symlink()or not origin.is_file():raise ValueError('No se admiten enlaces en un modelo importado.')
            before=sha256(origin);shutil.copy2(origin,stage/file)
            if sha256(stage/file)!=before:raise OSError('Copia del modelo incompleta: '+file)
            hashes[file]=before
        inspect_model(stage,name)
        from faster_whisper import WhisperModel
        checked=WhisperModel(str(stage),device='cpu',compute_type='int8',local_files_only=True,cpu_threads=2)
        del checked
        payload={'schema':1,'model_name':name,'architecture':architecture,'files_sha256':hashes,
                 'installed_at':datetime.now(timezone.utc).isoformat(),'source':'LOCAL_FOLDER','network_used':False}
        (stage/MANIFEST).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
        require('settings')
        if target.exists():raise FileExistsError('El modelo de destino ya existe; se conserva intacto.')
        os.rename(stage,target)
        return {'path':str(target),'manifest':payload}
    finally:
        if stage.exists():shutil.rmtree(stage)
