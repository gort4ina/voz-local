import re
import shutil
from pathlib import Path
from typing import Protocol
from uuid import UUID


class AudioStorage(Protocol):
    def directory(self, job_id: str) -> Path: ...
    def resolve(self, key: str) -> Path: ...
    def delete(self, job_id: str) -> None: ...


class LocalAudioStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def directory(self, job_id: str) -> Path:
        return self.root / str(UUID(job_id))

    def resolve(self, key: str) -> Path:
        target = (self.root / key).resolve()
        if not target.is_relative_to(self.root) or target == self.root:
            raise ValueError("Invalid storage key")
        return target

    def delete(self, job_id: str):
        directory = self.directory(job_id)
        if directory.exists():
            shutil.rmtree(directory)


def sanitize_filename(name: str) -> str:
    name = name.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip()
    return name[:255] or "audio"
