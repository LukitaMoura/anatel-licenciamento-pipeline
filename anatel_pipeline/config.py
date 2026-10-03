"""Configuração do pipeline lida de variáveis de ambiente (.env)."""
import os
import urllib.parse
from dataclasses import dataclass, field

from dotenv import load_dotenv

ALL_STATES = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK_DIR = os.path.join(BASE_DIR, "materiais")
TABLE_NAME = "dados_robo_anatel"


@dataclass
class Settings:
    db_type: str = "sqlite"
    sqlite_path: str = "licenciamento_anatel.db"
    db_host: str = ""
    db_port: str = ""
    db_user: str = ""
    db_password: str = ""
    db_name: str = ""
    states: list = field(default_factory=lambda: ["AC"])
    resume_progress: bool = True
    sleep_between_states: int = 10

    @property
    def database_url(self) -> str:
        if self.db_type == "sqlite":
            path = self.sqlite_path
            if not os.path.isabs(path):
                path = os.path.join(WORK_DIR, path)
            return f"sqlite:///{path}"
        if self.db_type == "mysql":
            user = urllib.parse.quote_plus(self.db_user)
            password = urllib.parse.quote_plus(self.db_password)
            return f"mysql+pymysql://{user}:{password}@{self.db_host}:{self.db_port}/{self.db_name}"
        raise ValueError(f"Tipo de banco de dados inválido: {self.db_type}")


def parse_states(raw: str) -> list:
    raw = (raw or "").upper().strip()
    if not raw or raw == "ALL":
        return list(ALL_STATES)
    states = [uf.strip() for uf in raw.split(",") if uf.strip()]
    invalid = [uf for uf in states if uf not in ALL_STATES]
    if invalid:
        raise ValueError(f"UF(s) inválida(s): {invalid}")
    return states


def load_settings() -> Settings:
    load_dotenv(override=True)
    return Settings(
        db_type=os.getenv("DB_TYPE", "sqlite").lower(),
        sqlite_path=os.getenv("SQLITE_PATH", "licenciamento_anatel.db"),
        db_host=os.getenv("DB_HOST", ""),
        db_port=os.getenv("DB_PORT", ""),
        db_user=os.getenv("DB_USER", ""),
        db_password=os.getenv("DB_PASSWORD", ""),
        db_name=os.getenv("DB_NAME", ""),
        states=parse_states(os.getenv("STATE_FILTER", "AC")),
        resume_progress=os.getenv("RESUME_PROGRESS", "True").lower() == "true",
        sleep_between_states=int(os.getenv("SLEEP_BETWEEN_STATES", "10")),
    )
