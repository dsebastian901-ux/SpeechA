"""Copias de audio completas y verificadas, sin modificar el archivo de origen."""
import hashlib
import os
from pathlib import Path
import shutil
import tempfile


def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def copy_verified_audio(source, destination):
    """Devuelve SHA256; un fallo deja únicamente el original y salidas previas."""
    source, destination = Path(source), Path(destination)
    original_digest = file_digest(source)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.mrs_',
                                         suffix='.part', delete=False) as stream:
            temporary = Path(stream.name)
        shutil.copy2(source, temporary)
        if file_digest(temporary) != original_digest or file_digest(source) != original_digest:
            raise OSError('El contenido del audio cambió durante la copia; vuelva a intentarlo.')
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return original_digest
