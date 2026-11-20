"""Inventario reproducible de código y matriz sin leer datos de clientes.

Uso: python auditoria/generar_matriz.py [--coverage cobertura.json]
La cobertura es evidencia de líneas ejecutadas, nunca de escucha humana.
"""
import argparse
import ast
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'proyecto/MRS_Speech_Analytics_v3.6.19_Revision'
OUT = Path(__file__).resolve().parent


def symbols(tree):
    result = {}
    def visit(body, prefix=''):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + node.name
                result[name] = node.lineno
                if isinstance(node, ast.ClassDef):
                    visit(node.body, name + '.')
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                    if isinstance(target, ast.Name):
                        result[target.id] = node.lineno
    visit(tree.body)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coverage', type=Path)
    args = parser.parse_args()
    coverage = json.loads(args.coverage.read_text())['files'] if args.coverage else {}
    modules, parsed = [], {}
    paths = sorted([*(APP/'app').rglob('*.py'), *(APP/'tools').rglob('*.py'), *APP.glob('*.py')])
    for path in paths:
        relative = path.relative_to(APP).as_posix()
        raw = path.read_bytes()
        tree = ast.parse(raw.decode('utf-8-sig'), filename=relative)
        parsed[relative] = symbols(tree)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
                imports.update(node.module+'.'+a.name for a in node.names)
        cov = coverage.get(relative, {}).get('summary', {})
        tests = []
        module = relative[:-3].replace('/', '.')
        for test in (APP/'tests').glob('test_*.py'):
            if module in test.read_text(encoding='utf-8-sig'):
                tests.append(test.name)
        state = ('VACIO / MARCADOR DE PAQUETE' if not tree.body else
                 'LEGACY SIN IMPORTACION PRODUCTIVA' if path.name.endswith('_BACKUP.py') else
                 'EJECUTADO EN PRUEBAS; ALCANCE SEGUN COBERTURA' if cov.get('covered_lines', 0) else
                 'INSPECCION ESTATICA; EJECUCION NO ACREDITADA POR COBERTURA')
        modules.append({'archivo':relative, 'lineas':len(raw.splitlines()),
            'sha256':hashlib.sha256(raw).hexdigest(), 'revision':state,
            'simbolos':'; '.join(f'{name}:{line}' for name,line in parsed[relative].items()),
            'imports':'; '.join(sorted(imports)), 'pruebas_referencia_directa':'; '.join(tests),
            'lineas_ejecutadas':cov.get('covered_lines',''),
            'lineas_ejecutables':cov.get('num_statements',''),
            'cobertura_lineas_pct':round(cov.get('percent_covered',0),2) if cov else '',
            'limite':'Inspección estructural de este archivo. Cobertura no prueba todas las ramas, reglas ni comportamiento acústico.'})
    for path in sorted(APP.glob('*.bat')):
        modules.append({'archivo':path.name,'lineas':len(path.read_bytes().splitlines()),
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'revision':'INSPECCION ESTATICA; NO EJECUTADO EN WINDOWS FISICO',
            'limite':'Se preserva el instalador/iniciador. No se genera ni certifica un instalador nuevo.'})

    rows = json.loads((OUT/'MATRIZ_ERRORES.json').read_text(encoding='utf-8'))
    for row in rows:
        location = row['archivo_funcion'].split(':')
        assert location[0] in parsed, location[0]
        symbol = location[1] if len(location)>1 else ''
        assert not symbol or symbol in parsed[location[0]], (row['id'], symbol)
        row['linea'] = parsed[location[0]].get(symbol,1)
        test_location = row['regresion'].split('::')
        if test_location[0].endswith('.py'):
            test_path = APP/test_location[0]
            assert test_path.exists(), row['id']
            if len(test_location)>1:
                assert test_location[1] in symbols(ast.parse(test_path.read_text(encoding='utf-8-sig'))), row['id']
    assert set(range(1,14)) <= {r['grupo'] for r in rows}
    def save_csv(name, entries):
        headers=list(dict.fromkeys(k for entry in entries for k in entry))
        with (OUT/name).open('w',encoding='utf-8-sig',newline='')as stream:
            writer=csv.DictWriter(stream,fieldnames=headers);writer.writeheader();writer.writerows(entries)
        return headers
    matrix_headers=save_csv('MATRIZ_ERRORES.csv',rows)
    inventory_headers=save_csv('INVENTARIO_MODULOS.csv',modules)
    workbook=Workbook();workbook.remove(workbook.active)
    for title,entries,headers in [('ERRORES',rows,matrix_headers),('MODULOS',modules,inventory_headers)]:
        ws=workbook.create_sheet(title);ws.append(headers)
        for entry in entries:ws.append([entry.get(k,'') for k in headers])
        ws.freeze_panes='C2';ws.auto_filter.ref=ws.dimensions
        for row in ws:
            for cell in row:
                if isinstance(cell.value,str):cell.data_type='s'
                cell.alignment=Alignment(vertical='top',wrap_text=True)
        for cell in ws[1]:cell.font=Font(bold=True)
        for column in ws.columns:ws.column_dimensions[column[0].column_letter].width=36
    for file,title in [('PRUEBAS_ANTES_DESPUES.csv','REGRESIONES_NUEVAS'),
                       ('RESULTADOS_ANTES_DESPUES.csv','RESULTADOS_ANTES_DESPUES')]:
        if not (OUT/file).exists():continue
        ws=workbook.create_sheet(title)
        with (OUT/file).open(encoding='utf-8-sig',newline='')as stream:
            for row in csv.reader(stream):ws.append(row)
        ws.freeze_panes='B2';ws.auto_filter.ref=ws.dimensions
        for row in ws:
            for cell in row:
                if isinstance(cell.value,str):cell.data_type='s'
                cell.alignment=Alignment(vertical='top',wrap_text=True)
        for column in ws.columns:ws.column_dimensions[column[0].column_letter].width=38
    workbook.save(OUT/'AUDITORIA_INTEGRAL.xlsx');workbook.close()
    text=['# Matriz integral de errores', '',
          'Estado referido al alcance descrito. CORREGIDO acredita el contrato de código con su regresión; no implica escucha humana ni exactitud acústica universal.', '',
          '| ID / grupo | Error | Antes → después | Código / función | Evidencia y regresión | Límite |',
          '|---|---|---|---|---|---|']
    escape=lambda value:str(value).replace('|',' / ').replace('\n',' ')
    for row in rows:
        file=row['archivo_funcion'].split(':')[0]
        link=f"[L{row['linea']}](../proyecto/MRS_Speech_Analytics_v3.6.19_Revision/{file}#L{row['linea']})"
        text.append('| '+' | '.join(map(escape,[str(row['id'])+' / '+str(row['grupo']),row['error'],
            row['estado_antes']+' → '+row['estado_despues'],row['archivo_funcion']+' '+link,
            row['evidencia']+' Regresión: '+row['regresion'],row['limite']]))+' |')
    (OUT/'MATRIZ_ERRORES.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    summary={'issues':len(rows),'groups':13,'states':dict(Counter(r['estado_despues'] for r in rows)),
        'python_modules':len(paths),'entry_scripts':len(modules)-len(paths),
        'app_modules':sum(p.is_relative_to(APP/'app') for p in paths),'ast_errors':0,
        'coverage_imported':bool(coverage),'customer_data_read':False}
    (OUT/'INVENTARIO_RESUMEN.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
