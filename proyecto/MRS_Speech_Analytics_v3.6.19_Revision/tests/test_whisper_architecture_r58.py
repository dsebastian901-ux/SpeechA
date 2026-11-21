"""Las rutas de importación históricas no activan motores distintos o en línea."""
import ast
import inspect
from pathlib import Path
import pytest
from app.services.whisper_service import WhisperService,WhisperServiceError


@pytest.mark.parametrize('name',['app.ai.whisper_service','app.services.whisper_service_BACKUP'])
def test_compatibility_imports_share_the_canonical_offline_engine(name):
    import importlib
    module=importlib.import_module(name)
    assert module.WhisperService is WhisperService
    assert module.WhisperServiceError is WhisperServiceError
    assert inspect.getfile(module.WhisperService)==inspect.getfile(WhisperService)


def test_batch_and_ui_import_the_same_production_service():
    import app.services.batch_service as batch
    import app.ui.views.transcription_view as ui
    from app.services.transcription_services import TranscriptionService
    assert type(batch.whisper_service) is WhisperService
    assert ui.TranscriptionService is TranscriptionService


def test_no_active_module_imports_the_legacy_backup_or_empty_ai_engine():
    root=Path(__file__).resolve().parents[1]/'app'
    imported=[]
    for path in root.rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            if isinstance(node,ast.ImportFrom)and node.module in {'app.services.whisper_service_BACKUP','app.ai.whisper_service'}:
                imported.append(path.relative_to(root).as_posix())
    assert not imported
