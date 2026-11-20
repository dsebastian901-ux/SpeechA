"""Regresión del programa sin cargar datos de clientes ni utilizar la red.

python auditoria/ejecutar_pruebas.py --output /ruta/privada/pruebas
En Linux sin pantalla: añadir --xvfb /ruta/a/Xvfb para ejecutar también Tk.
En Windows se usa la pantalla del entorno de pruebas. No usar cuentas reales.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--python',default=sys.executable)
    parser.add_argument('--xvfb')
    parser.add_argument('--shards',type=int,choices=range(1,5),default=4)
    args=parser.parse_args()
    app=Path(__file__).resolve().parents[1]/'proyecto/MRS_Speech_Analytics_v3.6.19_Revision'
    root=args.output.resolve();root.mkdir(parents=True,exist_ok=False)
    def hashes():
        return {p.relative_to(app).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for base in ['app','tests'] for p in (app/base).rglob('*.py')}
    before=hashes();tests=sorted((app/'tests').glob('test_*.py'))
    jobs=[];servers=[];streams=[]
    try:
        for group in range(args.shards):
            env=dict(os.environ)
            if args.xvfb:
                display=str(121+group)
                log=(root/f'xvfb_{group}.log').open('w');streams.append(log)
                server=subprocess.Popen([args.xvfb,':'+display,'-screen','0','1366x768x24','-nolisten','tcp'],stdout=log,stderr=subprocess.STDOUT)
                servers.append(server)
                for _ in range(50):
                    if Path('/tmp/.X11-unix/X'+display).exists():break
                    if server.poll()is not None:raise RuntimeError('No inició Xvfb; revise el registro.')
                    time.sleep(.1)
                env['DISPLAY']=':'+display
            log=(root/f'group_{group}.log').open('w');streams.append(log)
            command=[args.python,'-m','pytest','-q',f'--junitxml={root}/group_{group}.xml',
                     f'--basetemp={root}/tmp_{group}',*[str(p.relative_to(app))for p in tests[group::args.shards]]]
            jobs.append(subprocess.Popen(command,cwd=app,env=env,stdout=log,stderr=subprocess.STDOUT))
        codes=[job.wait()for job in jobs]
        counts={k:0 for k in ['tests','errors','failures','skipped']}
        for file in root.glob('group_*.xml'):
            for suite in ET.parse(file).getroot().iter('testsuite'):
                for key in counts:counts[key]+=int(suite.get(key,0))
        counts['passed']=counts['tests']-counts['errors']-counts['failures']-counts['skipped']
        record={'counts':counts,'exit_codes':codes,'source_unchanged':before==hashes(),
                'source_hashes':before,'physical_windows_tested':False,'human_audio_listening':False}
        (root/'validation.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        print(json.dumps(counts))
        return int(any(codes)or not record['source_unchanged'])
    finally:
        for server in servers:server.terminate();server.wait(timeout=10)
        for stream in streams:stream.close()


if __name__=='__main__':raise SystemExit(main())
