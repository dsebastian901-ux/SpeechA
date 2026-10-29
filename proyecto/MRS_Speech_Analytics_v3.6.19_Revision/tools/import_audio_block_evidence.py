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
    args=parser.parse_args()
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
        result=attach_audio_block(args.checkpoint,args.evidence,args.output_dir,source_checkpoint=args.source_checkpoint)
    except Exception as error:
        print('No se incorporaron las lecturas:',error);return 1
    print('Lecturas incorporadas:',result['matched_calls'])
    print('Checkpoint nuevo:',result['checkpoint'])
    print('Reporte nuevo:',result['report'])
    print('No se ejecutó Whisper ni se sustituyeron textos o validaciones humanas.')
    return 0


if __name__=='__main__':raise SystemExit(main())
