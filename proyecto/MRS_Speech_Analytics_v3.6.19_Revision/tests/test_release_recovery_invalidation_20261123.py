"""La versión correctiva no debe reutilizar relecturas de la r58 como si fueran r59."""
from app.config.release import ENGINE_REVISION
from app.services.context_audio_recovery import SCHEMA
from app.services import batch_runtime_state


def test_new_release_and_recovery_schema_invalidate_old_results():
    assert ENGINE_REVISION == "3.6.19-r59-segunda-escucha-20261123"
    assert SCHEMA == 2


def test_new_engine_stamp_differs_from_checkpoint_r58(tmp_path):
    item={"path":str(tmp_path/"audio.ogg"),"status":"completado","result":{"texto":"prueba"}}
    old_context={"engine_fingerprint":"r58", "runtime":{}, "mode":"A",
                 "minimum_score":80,"authorized_statuses":[]}
    old_stamp=batch_runtime_state.make_stamp(item,old_context,None)
    item["evaluation_stamp"]=old_stamp
    new_context=dict(old_context,engine_fingerprint=batch_runtime_state.engine_fingerprint())
    assert not batch_runtime_state.is_current(item,new_context,None)
