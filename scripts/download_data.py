"""Download the OULAD CSVs from the UCI Machine Learning Repository.

Source: https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset
License: CC BY 4.0. Files are saved to data/raw/ (not committed, about 450 MB unzipped).
"""
import sys
import urllib.request
import zipfile
from pathlib import Path

URL = "https://archive.ics.uci.edu/static/public/349/open+university+learning+analytics+dataset.zip"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
EXPECTED = [
    "courses.csv", "assessments.csv", "vle.csv", "studentInfo.csv",
    "studentRegistration.csv", "studentAssessment.csv", "studentVle.csv",
]


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    if all((RAW / f).exists() for f in EXPECTED):
        print(f"Data already in {RAW}")
        return 0
    zpath = RAW / "oulad.zip"
    if not zpath.exists():
        print(f"Downloading {URL}")
        urllib.request.urlretrieve(URL, zpath)
    with zipfile.ZipFile(zpath) as z:
        for name in z.namelist():
            if Path(name).name in EXPECTED:
                target = RAW / Path(name).name
                target.write_bytes(z.read(name))
    missing = [f for f in EXPECTED if not (RAW / f).exists()]
    if missing:
        print(f"Missing after unzip: {missing}", file=sys.stderr)
        return 1
    print(f"Saved {len(EXPECTED)} CSV files to {RAW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
