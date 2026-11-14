"""Preparar una etiqueta corregida sin modificar el Excel ni el audio original."""
from pathlib import PureWindowsPath
import re

AUDIO_SUFFIXES={'.ogg','.wav','.mp3','.m4a','.flac','.aac','.wma','.mp4','.webm'}


def audio_output_filename(name, source_suffix):
    """Conservar puntos en nombres/apellidos; retirar solo extensión de audio."""
    suffix=PureWindowsPath(name).suffix
    base=name[:-len(suffix)] if suffix.lower() in AUDIO_SUFFIXES else name
    if source_suffix.lower() not in AUDIO_SUFFIXES:
        raise ValueError('La extensión de audio no está admitida.')
    return base+source_suffix

# La selección del componente se activa al recibir el formato de la usuaria.
STATUS_LABEL_POLICY = {'enabled':True,'component_index':3,
    'folder':'APROBADOS_ETIQUETA_CORREGIDA',
    'codes':{'NO DEFINE FECHA DE PAGO':'TH','CONVENIO':'PP','NEGATIVA DE PAGO':'NP',
             'MENSAJE CON FAMILIAR':'3EROS','MENSAJE CON TERCERO':'3EROS',
             'MENSAJE EN TRABAJO':'3EROS','RECADO REF1':'3EROS','ACLARACION':'ACLARA','NO CONOCEN A DEUDOR':'NC'}}


def corrected_status_label(metadata, policy=None):
    policy = STATUS_LABEL_POLICY if policy is None else policy
    none={'eligible':False,'valid':False,'reason':''}
    if not policy.get('enabled'):
        return none
    status=metadata.get('status_validation') or {}
    if (status.get('matches') is not False or status.get('detection_confidence')!='ALTA'
            or status.get('review_required') or not status.get('evidence_method')
            or not status.get('detected_status') or not status.get('evidence')):
        return none
    if status.get('evidence_method')=='SIN_COMPROMISO_FIRME_RESPUESTA_EXPLICITA':
        from app.services.conversation_evidence import normalize
        evidence=normalize(status['evidence'])
        if (re.search(r'\byo (?:le )?(?:solicito|requiero)(?: lo que es)? (?:el |un |su )?pago\b',evidence)
                or re.search(r'\bsi\b[^.!?]{0,140}\b(?:vuelve|vuelven|hubiera|tuviera|pudiera)\b[^.!?]{0,100}\bno (?:vamos|voy) a pagar\b',evidence)):
            return dict(none,reason='La frase es una instrucción de cobro o una condición hipotética; no acredita el nuevo estatus para reetiquetar.')
    old_status=str(status.get('excel_status') or '')
    old_key='MENSAJE CON FAMILIAR' if old_status=='RECADO REF2' else old_status  # Solo compatibilidad de entrada.
    new_status=str(status['detected_status'])
    codes=policy.get('codes') or {}
    if old_key not in codes or new_status not in codes:
        return dict(none,reason='Estatus sin código de salida configurado; no se inventa una etiqueta.')
    context=metadata.get('operational_context') or {}
    name=str(context.get('nombre_final') or '')
    if not name or PureWindowsPath(name).name!=name or any(c in name for c in '/\\\0'):
        return dict(none,reason='El nombre final no tiene un formato seguro para corregir su etiqueta.')
    parts=name.split('_');index=policy.get('component_index')
    if not isinstance(index,int) or index<1 or index>=len(parts) or len(parts)<7:
        return dict(none,reason='El nombre no contiene el componente de estatus configurado.')
    # El componente inicial pertenece a nombre_final, no a numero_de_tarjeta.
    before=parts[index];target=codes[new_status]
    if before not in {codes[old_key],target} or not re.fullmatch(r'[A-Z0-9]+',target):
        return dict(none,reason='El componente de estatus no coincide con el catálogo; requiere revisión.')
    # Los estatus equivalentes (REF1/REF2/familiar/tercero) ya usan 3EROS.
    # No contar como reetiquetado ni generar otra copia si el codigo no cambia.
    if before == target:
        return dict(none,reason='Estatus equivalente: mismo codigo de salida; no requiere reetiquetado.')
    parts[index]=target
    return {'eligible':True,'valid':True,'original_status':old_status,'corrected_status':new_status,
            'original_name':name,'corrected_name':'_'.join(parts),'component_index':index,
            'original_code':before,'corrected_code':target,'changed':before!=target,
            'folder':policy['folder'],'source':'CONFIRMED_CONVERSATION_STATUS',
            'original_excel_modified':False,'original_audio_modified':False,
            'human_verified':False,'reason':'Dictamen de conversación con evidencia alta; etiqueta de salida corregida en copia.'}
