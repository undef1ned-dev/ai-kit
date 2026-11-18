"""Replace project files atomically within their destination filesystem."""

from contextlib import contextmanager
import os
import shutil
import tempfile
from pathlib import Path
import uuid


def resolve_workspace(value: str) -> Path:
    # Resolving a relative path directly can duplicate cwd in the Windows sandbox.
    return Path(value).absolute().resolve()


@contextmanager
def staging_directory(workspace: Path):
    if os.name == "nt":
        stage = workspace / f".aikit-update-{uuid.uuid4().hex}"
        # Windows mkdir(0o700) removes the sandbox's inherited access rights.
        stage.mkdir()
    else:
        stage = Path(tempfile.mkdtemp(prefix=".aikit-update-", dir=workspace))
    try:
        yield stage
    finally:
        shutil.rmtree(stage)


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".aikit-update-", delete=False) as output:
        temporary = Path(output.name)
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
