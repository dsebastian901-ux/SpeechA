"""Ejecuta cada caso original en un proceso separado; no carga datos de clientes.

Los registros quedan en un directorio nuevo fuera del repositorio. No publica
parámetros de pytest, transcripciones ni archivos generados por las pruebas.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--source', type=Path, help='Raíz de la aplicación; por defecto la de esta rama.')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    app = (args.source or repo / 'proyecto/MRS_Speech_Analytics_v3.6.19_Revision').resolve()
    out = args.output.resolve()
    if out == repo or repo in out.parents:
        parser.error('--output debe estar fuera del repositorio; puede contener evidencia privada.')
    if not (app / 'tests').is_dir():
        parser.error('--source no contiene el directorio tests.')
    with (Path(__file__).resolve().parents[1] / 'FALLOS_PENDIENTES.csv').open(encoding='utf-8-sig', newline='') as stream:
        cases = list(csv.DictReader(stream))
    if len(cases) != 34 or len({c['caso'] for c in cases}) != 34:
        raise ValueError('El manifiesto original debe contener 34 casos distintos.')
    out.mkdir(parents=True, exist_ok=False)

    def sources():
        return {p.relative_to(app).as_posix(): sha(p)
                for part in ('app', 'tests', 'tools') for p in (app / part).rglob('*.py')}

    before = sources()
    command = [args.python, '-m', 'pytest', '--collect-only', '-q',
               *sorted({c['archivo'] for c in cases})]
    collection = subprocess.run(command, cwd=app, capture_output=True, text=True)
    (out / 'collection.log').write_text(collection.stdout + collection.stderr, encoding='utf-8')
    if collection.returncode:
        raise RuntimeError('Falló la colección; ver collection.log en el directorio privado.')
    nodes = {}
    for line in collection.stdout.splitlines():
        if not line.startswith('tests/') or '.py::' not in line:
            continue
        filename, name = line.split('::', 1)
        classname = filename[:-3].replace('/', '.')
        identifier = hashlib.sha256((classname + '::' + name).encode()).hexdigest()[:12]
        if identifier in nodes:
            raise RuntimeError('Identificador de caso duplicado durante la colección.')
        nodes[identifier] = line
    if any(c['caso'] not in nodes for c in cases):
        raise RuntimeError('No se localizaron los 34 parámetros exactos; no ejecutar sustitutos.')
    results = []
    for case in cases:
        folder = out / case['caso']
        folder.mkdir()
        cmd = [args.python, '-m', 'pytest', '-q', nodes[case['caso']],
               '--basetemp=' + str(folder / 'tmp'), '--junitxml=' + str(folder / 'pytest.xml')]
        with (folder / 'pytest.log').open('w', encoding='utf-8') as log:
            run = subprocess.run(cmd, cwd=app, stdout=log, stderr=subprocess.STDOUT)
        xml = folder / 'pytest.xml'
        outcome = 'ERROR_EJECUCION'
        if xml.exists():
            actual = list(ET.parse(xml).getroot().iter('testcase'))
            if len(actual) != 1:
                raise RuntimeError('La ejecución no produjo exactamente un caso: ' + case['caso'])
            node = actual[0]
            outcome = ('FALLA' if node.find('failure') is not None or node.find('error') is not None
                       else 'OMITIDA' if node.find('skipped') is not None else 'PASA')
            if run.returncode and outcome == 'PASA':
                outcome = 'ERROR_EJECUCION'
        results.append({'caso': case['caso'], 'archivo': case['archivo'], 'funcion': case['funcion'],
                        'resultado': outcome, 'exit_code': run.returncode,
                        'log_sha256': sha(folder / 'pytest.log'),
                        'xml_sha256': sha(xml) if xml.exists() else None})
        print(case['caso'], outcome, flush=True)
    unchanged = before == sources()
    summary = {'casos': results, 'fuentes_sin_cambios': unchanged, 'fuentes_sha256': before,
               'windows_fisico_probado': False, 'escucha_humana': False}
    (out / 'resultados.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return int(not unchanged or any(r['resultado'] != 'PASA' for r in results))


if __name__ == '__main__':
    raise SystemExit(main())
