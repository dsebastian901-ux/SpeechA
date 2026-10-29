"""Releer un bloque con Whisper local y conservar por separado la evidencia."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.audio_block_review import review_audio_block


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint',type=Path)
    parser.add_argument('--audio-dir',type=Path)
    parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args();source=args.checkpoint;folder=args.audio_dir
    if source is None or folder is None:
        from tkinter import Tk,filedialog
        root=Tk();root.withdraw()
        try:
            if source is None:
                name=filedialog.askopenfilename(title='Seleccionar checkpoint completo r22 o posterior',filetypes=[('Checkpoint JSON','*.json')])
                if not name:print('Cancelado.');return 0
                source=Path(name)
            if folder is None:
                name=filedialog.askdirectory(title='Seleccionar carpeta de los audios del bloque')
                if not name:print('Cancelado.');return 0
                folder=Path(name)
        finally:root.destroy()
    try:
        result=review_audio_block(source,folder,args.output_dir,progress=lambda message:print(message,flush=True))
    except Exception as error:
        print('No se completó la lectura:',error);return 1
    print('Audios completados:',result['completed_calls'],'de',result['matched_calls'])
    print('Errores:',result['errors'])
    print('Archivo para compartir en la revisión:',result['evidence'])
    print('Comparación Excel:',result['report'])
    print('El lote original y sus validaciones permanecen intactos. La lectura ASR no certifica voces ni aprobación.')
    return 1 if result['errors'] else 0


if __name__=='__main__':
    raise SystemExit(main())
