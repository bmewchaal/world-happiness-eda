"""Utility tips for downloading data.

- Kaggle API: https://github.com/Kaggle/kaggle-api
1) pip install kaggle
2) Place kaggle.json (API credentials) in ~/.kaggle/ with 600 permissions.
3) Example:
    kaggle datasets download -d unsdsn/world-happiness -p data/raw --unzip

- World Bank:
  Use the "Download Data" button on indicator pages (CSV), then drop into data/raw/.

These helpers are optional—most people will manually download and place files in data/raw/.
"""
from pathlib import Path

RAW = Path("data/raw")

def check_raw_dir():
    RAW.mkdir(parents=True, exist_ok=True)
    print(f"Raw data dir exists: {RAW.resolve()}")

if __name__ == "__main__":
    check_raw_dir()
