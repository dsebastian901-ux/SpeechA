"""Copiar aprobadas con etiqueta corregida, sin mover originales ni ejecutar ASR."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from app.services.account_source_validation import apply_output_name_authority
from app.services.analytics_service import AnalyticsService
from app.services.checkpoint_output import create_checkpoint_output,WINDOWS_PATH_BUDGET
from app.services.checkpoint_reanalysis import transcription_with_saved_reviews


CATEGORY='APROBADO_ETIQUETA_CORREGIDA'
FOLDER='APROBADOS_ETIQUETA_CORREGIDA'


def file_digest(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def export_corrected_labels(checkpoint, audio_directory, output_directory=None):
    source_checkpoint=Path(checkpoint).resolve()
    raw=source_checkpoint.read_bytes()
    payload=json.loads(raw.decode('utf-8-sig'))
    if not isinstance(payload.get('items'),list):
        raise ValueError('Seleccione un checkpoint con llamadas.')
    root=Path(audio_directory).expanduser().resolve()
    if not root.is_dir():
        raise ValueError('Seleccione la carpeta de los audios originales.')
    candidates=[i for i in payload['items'] if (i.get('classification') or {}).get('clasificacion')==CATEGORY]
    plan=[];destinations=set()
    # Validar todos los candidatos antes de copiar un solo archivo. No confiar
    # solo en una etiqueta almacenada: repetir las reglas con la evidencia.
    for original in candidates:
        item=deepcopy(original)
        apply_output_name_authority(item)
        t=transcription_with_saved_reviews(item)
        relation=item.get('relation') or {}
        analysis=AnalyticsService.analyze_transcription(t,relation)
        old=item.get('classification') or {}
        decision=AnalyticsService.shared_quality_decision(analysis.metadata,analysis.compliance_score,
            old.get('puntaje_minimo') or 80,t.duration_seconds,
            {'estatus_autorizado':old.get('estatus_autorizado'),'tiene_nombre_final':bool(relation.get('nombre_final'))})
        label=decision.get('output_label_correction') or {}
        if decision['clasificacion']!=CATEGORY or not label.get('valid'):
            raise ValueError('La llamada ya no cumple los filtros para corregir su etiqueta: '+str(item.get('file_name')))
        saved=old.get('output_label_correction') or {}
        if saved.get('corrected_name')!=label['corrected_name']:
            raise ValueError('La etiqueta guardada difiere de la recalculada. Reanalice el checkpoint.')
        name=str(item.get('file_name') or '')
        if not name or Path(name).name!=name or any(c in name for c in '/\\'):
            raise ValueError('El checkpoint no contiene un nombre original seguro.')
        direct=root/name
        if direct.is_file():
            audio=direct.resolve()
        else:
            matches=[p.resolve() for p in root.rglob('*') if p.is_file() and p.name.casefold()==name.casefold()]
            if len(matches)!=1:
                raise ValueError('Audio ausente o duplicado; seleccione su carpeta original: '+name)
            audio=matches[0]
        if not audio.is_relative_to(root):
            raise ValueError('El audio resuelto está fuera de la carpeta seleccionada.')
        if audio.suffix.lower() not in {'.ogg','.wav','.mp3','.m4a','.flac','.aac','.wma','.mp4','.webm'}:
            raise ValueError('La entrada no es un archivo de audio admitido.')
        from app.services.status_output_label import audio_output_filename
        filename=audio_output_filename(label['corrected_name'],audio.suffix)
        relative=Path(filename)
        if filename.casefold() in destinations:
            # Preservar todos los componentes del nombre, incluso si dos
            # llamadas de la misma cuenta/fecha producen el mismo destino.
            relative=Path('duplicado_'+hashlib.sha256(name.encode()).hexdigest()[:12])/filename
        key=str(relative).casefold()
        if key in destinations:
            raise ValueError('Dos registros intentan copiar la misma llamada; no se sobrescribe.')
        destinations.add(filename.casefold());destinations.add(key)
        plan.append({'source':audio,'relative':relative,'file_name':name,'label':label,'score':analysis.compliance_score})
    target=create_checkpoint_output(output_directory,'Etiquetas_MRS_r45_')
    if os.name=='nt' and any(len(str(target/FOLDER/p['relative']).encode('utf-16-le'))//2>=WINDOWS_PATH_BUDGET for p in plan):
        raise ValueError('Ruta demasiado larga para Windows; elija una carpeta de salida más corta.')
    (target/FOLDER).mkdir(exist_ok=True)
    records=[]
    manifest_path=target/'Registro_Etiquetas_Corregidas.json'
    manifest={'engine_revision':AnalyticsService.ENGINE_REVISION,'source_checkpoint_sha256':hashlib.sha256(raw).hexdigest(),
              'completed':False,'planned_copies':len(plan),'copied':0,'whisper_executed':False,'originals_modified':False,'calls':records}
    def write_manifest():
        temporary_manifest=manifest_path.with_suffix('.nuevo.json')
        temporary_manifest.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
        temporary_manifest.replace(manifest_path)
    write_manifest()
    for entry in plan:
        destination=target/FOLDER/entry['relative']
        destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists():
            raise ValueError('Ya existe una copia de salida; seleccione una carpeta nueva.')
        digest=file_digest(entry['source'])
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent,prefix='.mrs_',suffix='.part',delete=False) as stream:
                temporary=Path(stream.name)
            shutil.copy2(entry['source'],temporary)
            if file_digest(temporary)!=digest or file_digest(entry['source'])!=digest:
                raise ValueError('El audio cambió durante la copia; no se publica una copia incompleta.')
            temporary.replace(destination);temporary=None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        records.append({'file_name':entry['file_name'],'source':str(entry['source']),'destination':str(destination),
                        'audio_sha256':digest,'score':entry['score'],'label':entry['label']})
        manifest['copied']=len(records)
        write_manifest()
    manifest['completed']=True
    write_manifest()
    assert source_checkpoint.read_bytes()==raw
    return {'copied':len(records),'output_directory':str(target),'folder':str(target/FOLDER),
            'manifest':str(manifest_path),'whisper_executed':False}
