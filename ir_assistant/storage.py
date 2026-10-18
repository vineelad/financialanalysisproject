import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def write_jsonl(path: Path, records: list[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        for item in records:
            stream.write(item.model_dump_json() + "\n")
    temp.replace(path)


def read_jsonl(path: Path, model: type[T]) -> list[T]:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path.name}. Run the preceding prepare/index step.")
    return [model.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
