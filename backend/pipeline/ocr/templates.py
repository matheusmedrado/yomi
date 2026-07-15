from __future__ import annotations

import os
import pickle
from dataclasses import dataclass

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(HERE, "templates_db", "templates.pkl")


class TemplateDBError(FileNotFoundError):
    pass


@dataclass
class TemplateDB:
    images: np.ndarray
    labels: list[str]
    fonts: list[str]
    size: int
    chars: list[str]

    @classmethod
    def load(cls, db_path: str = DEFAULT_DB) -> "TemplateDB":
        if not os.path.exists(db_path):
            raise TemplateDBError(
                f"Banco de templates nao encontrado em {db_path}. "
                "Rode: python backend/pipeline/ocr/build_templates.py"
            )
        with open(db_path, "rb") as fh:
            data = pickle.load(fh)
        return cls(
            images=data["images"],
            labels=data["labels"],
            fonts=data["fonts"],
            size=int(data["size"]),
            chars=list(data["chars"]),
        )

    def unique_labels(self) -> list[str]:
        return self.chars
