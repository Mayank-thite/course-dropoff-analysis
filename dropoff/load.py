"""Load the raw CSVs into the database: python -m dropoff.load"""
import logging

from . import config
from .db import Database, load_all

log = logging.getLogger(__name__)


def main() -> None:
    db = Database()
    counts = load_all(db, config.DATA_DIR)
    log.info(f"Loaded into {db.engine} from {config.DATA_DIR}:")
    for table, n in counts.items():
        log.info(f"  {table:<22} {n:>10,}")
    db.close()


if __name__ == "__main__":
    config.setup_logging()
    main()
