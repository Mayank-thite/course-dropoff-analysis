"""Load the raw CSVs into the database: python -m dropoff.load"""
from . import config
from .db import Database, load_all


def main() -> None:
    db = Database()
    counts = load_all(db, config.DATA_DIR)
    print(f"Loaded into {db.engine} from {config.DATA_DIR}:")
    for table, n in counts.items():
        print(f"  {table:<22} {n:>10,}")
    db.close()


if __name__ == "__main__":
    main()
