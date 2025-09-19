# backend/app/scripts/fetch_kaggle.py
import os, subprocess, sys, pathlib

def main():
    dataset = os.environ.get("KAGGLE_DATASET") or "<owner>/<dataset-slug>"
    outdir = pathlib.Path(os.environ.get("RAW_DIR", "backend/app/data/raw"))
    outdir.mkdir(parents=True, exist_ok=True)

    # Ensure kaggle is configured (kaggle.json in ~/.kaggle)
    try:
        subprocess.check_call([
            sys.executable, "-m", "kaggle", "datasets", "download",
            dataset, "-p", str(outdir), "--unzip"
        ])
    except subprocess.CalledProcessError as e:
        print("Kaggle download failed. Make sure kaggle.json is set up.", file=sys.stderr)
        raise e

if __name__ == "__main__":
    main()
