import pandas as pd
import pickle
import json
from pathlib import Path
import warnings
import sys

warnings.filterwarnings(
    "ignore",
    category=UserWarning,
    module="openpyxl.worksheet._reader"
)

project_root = Path(__file__).resolve().parents[1]
raw_dir = project_root / "data" / "raw" / "taylor_swift"
processed_dir = project_root / "data" / "processed"

excel_file = raw_dir / "Corpus-of-Taylor-Swift-v1.1.xlsx"
json_file = raw_dir / "flat-song-lyrics.json"

pickle_excel_file = processed_dir / "corpus_excel.pkl"
pickle_json_file = processed_dir / "corpus_json.pkl"

def pickle_excel(input_path: Path, output_path: Path):
    """Read Excel and save as Pickle."""
    if not input_path.exists():
        raise FileNotFoundError(f"Excel file not found: {input_path}")

    try:
        df = pd.read_excel(input_path)
        print(f"✅ Excel loaded: {df.shape[0]} rows, {df.shape[1]} columns")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "wb") as f:
            pickle.dump(df, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"💾 Pickle saved at: {output_path}")
        
        # Verify the pickle
        with open(output_path, "rb") as f:
            test_load = pickle.load(f)
        print(f"🔍 Verification: Reloaded {len(test_load)} rows")
        
    except Exception as e:
        print(f"❌ Error processing Excel: {str(e)}")
        raise

def pickle_json(input_path: Path, output_path: Path):
    """Read JSON and save as Pickle."""
    if not input_path.exists():
        raise FileNotFoundError(f"JSON file not found: {input_path}")

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "wb") as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"💾 Pickle saved at: {output_path}")
        
        with open(output_path, "rb") as f:
            test_load = pickle.load(f)
        print(f"🔍 Verification: Reloaded {len(test_load)} items")
        
    except Exception as e:
        print(f"❌ Error processing JSON: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        pickle_excel(excel_file, pickle_excel_file)
        pickle_json(json_file, pickle_json_file)

        print("\n🎯 Both corpora have been pickled successfully!")
    except Exception as e:
        print(f"\n💥 Script failed: {str(e)}")
        sys.exit(1)