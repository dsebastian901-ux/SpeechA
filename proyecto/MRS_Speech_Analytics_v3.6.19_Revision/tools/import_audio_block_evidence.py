"""Incorporar lectura adicional al lote actual sin cambiar transcripciones."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.audio_block_evidence import attach_audio_block,binding


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path)
    parser.add_argument('--evidence',type=Path)
    parser.add_argument('--source-checkpoint',type=Path)
    parser.add_argument('--output-dir',type=Path)
    parser.add_argument('--confirm-family',action='store_true',help='Registrar además un parentesco ya confirmado por el usuario.')
    parser.add_argument('--family-call',type=int,help='Número de llamada de este checkpoint con parentesco confirmado.')
    parser.add_argument('--family-relationship',help='Parentesco confirmado, por ejemplo HIJA.')
    args=parser.parse_args()
    if (args.family_call is None)!=(args.family_relationship is None):
        parser.error('Indique juntos --family-call y --family-relationship.')
    if args.checkpoint is None or args.evidence is None:
        from tkinter import Tk,filedialog
        root=Tk();root.withdraw()
        try:
            for field,title in [('checkpoint','Seleccionar checkpoint completo ACTUAL'),('evidence','Seleccionar revision_audios_bloque.json')]:
                if getattr(args,field) is None:
                    value=filedialog.askopenfilename(title=title,filetypes=[('JSON','*.json')])
                    if not value:print('Cancelado.');return 0
                    setattr(args,field,Path(value))
            master=json.loads(args.checkpoint.read_text(encoding='utf-8-sig'));evi=json.loads(args.evidence.read_text(encoding='utf-8-sig'))
            items={i['file_name']:i for i in master['items']}
            same=evi.get('source_checkpoint_sha256')==hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
            linked=all(r.get('file_name') in items and r.get('source_binding')==binding(
                items[r['file_name']].get('result') or {},items[r['file_name']].get('relation') or {}) for r in evi.get('items') or [])
            if not same and not linked and args.source_checkpoint is None:
                value=filedialog.askopenfilename(title='Seleccionar checkpoint ORIGEN usado para generar las lecturas',filetypes=[('JSON','*.json')])
                if not value:print('Cancelado. El lote actual permanece intacto.');return 0
                args.source_checkpoint=Path(value)
        except Exception as error:
            print('No se incorporaron las lecturas:',error);return 1
        finally:root.destroy()
    try:
        confirmations={}
        if args.confirm_family or args.family_call is not None:
            master=json.loads(args.checkpoint.read_text(encoding='utf-8-sig'))
            items=master.get('items') or []
            if not items or not all(isinstance(i.get('result'),dict) for i in items):
                raise ValueError('Seleccione el checkpoint completo para registrar el parentesco.')
            if args.family_call is None:
                from tkinter import Tk,simpledialog
                root=Tk();root.withdraw()
                try:
                    args.family_call=simpledialog.askinteger('Parentesco ya confirmado',
                        'Número de llamada de este checkpoint cuyo parentesco ya confirmó:',minvalue=1,maxvalue=len(items),parent=root)
                    if args.family_call is None:print('Cancelado; no se modificaron los originales.');return 0
                    item=items[args.family_call-1]
                    args.family_relationship=simpledialog.askstring('Parentesco ya confirmado',
                        f"Llamada {args.family_call}: {item['file_name']}\nEscriba el parentesco confirmado (por ejemplo, HIJA).",parent=root)
                    if not args.family_relationship:print('Cancelado; no se modificaron los originales.');return 0
                finally:root.destroy()
            if not 1<=args.family_call<=len(items):raise ValueError('Número de llamada fuera del checkpoint seleccionado.')
            from app.services.family_contact_review import make_family_confirmation
            item=items[args.family_call-1]
            review=make_family_confirmation(item['result'],item.get('relation') or {},args.family_relationship,user_confirmed=True)
            confirmations[item['file_name']]=review['relationship']
        result=attach_audio_block(args.checkpoint,args.evidence,args.output_dir,source_checkpoint=args.source_checkpoint,
                                  family_confirmations=confirmations)
    except Exception as error:
        print('No se incorporaron las lecturas:',error);return 1
    print('Lecturas incorporadas:',result['matched_calls'])
    print('Revisión del motor:',result['engine_revision'])
    print('Evaluaciones:',result['evaluations'])
    print('Resultados:',result['outcomes'])
    if confirmations:print('Parentescos registrados por confirmación del usuario:',len(confirmations))
    print('Checkpoint nuevo:',result['checkpoint'])
    print('Reporte nuevo:',result['report'])
    print('No se ejecutó Whisper. Se conservaron los textos y el historial de validaciones.')
    return 0


if __name__=='__main__':raise SystemExit(main())
