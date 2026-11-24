"""Comparación privada de dos resultados del mismo lote, por nombre original."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.checkpoint_comparison import compare_checkpoints


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path,required=True)
    parser.add_argument('--after',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=compare_checkpoints(args.before,args.after,args.output)
    # La consola no vuelca nombres, conversaciones, cuentas ni relaciones.
    print('Llamadas comparadas:',result['calls'])
    print('Antes:',result['before'])
    print('Después:',result['after'])
    print('Cambios:',result['changed'])
    print('Detalle local guardado en la ruta solicitada.')


if __name__=='__main__':
    from app.services.access_service import require_admin_tool
    require_admin_tool()
    main()
