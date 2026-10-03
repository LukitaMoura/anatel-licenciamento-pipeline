"""Orquestra extração → transformação → carga para cada UF configurada.

Uso:  python -m anatel_pipeline
"""
import logging
import os
import shutil
import sys
import time

from sqlalchemy import create_engine

from . import loader, scraper, transform
from .config import TABLE_NAME, WORK_DIR, load_settings
from .progress import ProgressTracker

log = logging.getLogger("anatel_pipeline")


def setup_logging() -> None:
    os.makedirs(WORK_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(WORK_DIR, "execucao.log"), encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def process_state(uf: str, engine) -> int:
    zip_path = os.path.join(WORK_DIR, f"temp_{uf}.zip")
    extract_dir = os.path.join(WORK_DIR, f"temp_{uf}")
    os.makedirs(extract_dir, exist_ok=True)
    try:
        scraper.download_state_data(uf, zip_path)
        csv_path = transform.extract_zip(zip_path, extract_dir)
        df = transform.clean(transform.read_raw_csv(csv_path))
        log.info("[%s] %d linhas após limpeza", uf, len(df))
        return loader.upsert(df, engine, TABLE_NAME)
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
        shutil.rmtree(extract_dir, ignore_errors=True)


def main() -> None:
    setup_logging()
    settings = load_settings()
    engine = create_engine(settings.database_url)
    progress = ProgressTracker(os.path.join(WORK_DIR, "progresso.json"))
    log.info("Estados a processar: %s", settings.states)

    ok, failed = [], []
    for i, uf in enumerate(settings.states, 1):
        log.info("---- (%d/%d) %s", i, len(settings.states), uf)
        if settings.resume_progress and progress.is_done(uf):
            log.info("[%s] Já processado com sucesso, pulando", uf)
            ok.append(uf)
            continue

        start = time.time()
        try:
            rows = process_state(uf, engine)
        except Exception as e:  # uma UF com falha não derruba as demais
            log.exception("[%s] Falha", uf)
            progress.record(uf, "failed", time.time() - start, error=str(e))
            failed.append(uf)
        else:
            progress.record(uf, "success", time.time() - start, rows=rows)
            ok.append(uf)

        if i < len(settings.states):
            time.sleep(settings.sleep_between_states)  # gentileza com o portal público

    log.info("Concluído. Sucesso: %d %s | Falha: %d %s", len(ok), ok, len(failed), failed)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
