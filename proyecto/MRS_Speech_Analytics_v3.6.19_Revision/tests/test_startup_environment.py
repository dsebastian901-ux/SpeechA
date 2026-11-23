"""El preflight informa faltantes completos sin arrancar GUI ni modelos."""
import sys
from tools import check_startup_environment as check
import pytest


def test_all_required_components_are_probed_without_loading_application():
    calls=[]
    assert check.missing_components(calls.append)==[]
    assert calls==[name for name,_ in check.COMPONENTS]
    assert all(not name.startswith('app.') for name in calls)


@pytest.mark.parametrize('failure',[ModuleNotFoundError,OSError,RuntimeError])
def test_missing_gui_or_broken_native_backend_never_reports_ready(failure):
    calls=[]
    def importer(name):
        calls.append(name)
        if name in {'customtkinter','faster_whisper'}:
            raise failure('synthetic dependency failure')
    issues=check.missing_components(importer)
    assert [row[0]for row in issues]==['customtkinter','faster-whisper']
    assert len(calls)==len(check.COMPONENTS)


def test_requirement_packages_and_probe_stay_consistent():
    from pathlib import Path
    import re
    expected=set()
    for line in (Path(__file__).parents[1]/'requirements.txt').read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            expected.add(re.split(r'[<>=]',line)[0].strip().lower())
    assert expected=={package.lower()for module,package in check.COMPONENTS if module!='tkinter'}


@pytest.mark.parametrize('version,pointer', [((3,9),8),((3,10),4)])
def test_unsupported_python_does_not_try_imports(monkeypatch,version,pointer):
    monkeypatch.setattr(check.sys,'version_info',version)
    monkeypatch.setattr(check.struct,'calcsize',lambda _:pointer)
    def fail():raise AssertionError('Must not import incompatible dependencies')
    monkeypatch.setattr(check,'missing_components',fail)
    assert check.main()==1


def test_main_prints_all_failures_and_returns_nonzero(monkeypatch,capsys):
    monkeypatch.setattr(check,'missing_components',lambda:[('customtkinter','ModuleNotFoundError','missing'),('av','OSError','DLL')])
    assert check.main()==1
    output=capsys.readouterr().out
    assert 'customtkinter'in output and'av'in output and sys.executable in output


def test_main_ready_only_when_the_selected_interpreter_is_complete(monkeypatch,capsys):
    monkeypatch.setattr(check,'missing_components',lambda:[])
    assert check.main()==0
    assert 'Componentes locales verificados'in capsys.readouterr().out
