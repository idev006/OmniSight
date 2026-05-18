"""
Download MiniFASNet anti-spoofing model (Silent-Face-Anti-Spoofing)

Run:
    my_env/Scripts/python.exe backend/scripts/download_anti_spoof_model.py

Model: 2.7_80x80_MiniFASNetV2.onnx (~400 KB)
Source: https://github.com/minivision-ai/Silent-Face-Anti-Spoofing

After download, enable anti-spoofing in Settings UI:
    anti_spoof_enabled = 1
    anti_spoof_threshold = 0.6
"""
import sys
import urllib.request
from pathlib import Path

# Try multiple sources in order
MODEL_URLS = [
    # Hugging Face mirror (most reliable)
    "https://huggingface.co/datasets/minivision-ai/silent-face-models/resolve/main/2.7_80x80_MiniFASNetV2.onnx",
    # GitHub raw (master branch)
    "https://raw.githubusercontent.com/minivision-ai/Silent-Face-Anti-Spoofing/master/resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.onnx",
    # GitHub raw (main branch)
    "https://raw.githubusercontent.com/minivision-ai/Silent-Face-Anti-Spoofing/main/resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.onnx",
]
MODEL_FILENAME = "2.7_80x80_MiniFASNetV2.onnx"

# Save to project root / models / anti_spoof /
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR    = PROJECT_ROOT / "models" / "anti_spoof"


def download():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    dest = MODEL_DIR / MODEL_FILENAME

    if dest.exists():
        print(f"Model already exists: {dest}")
        print("Delete it manually if you want to re-download.")
        return

    def _progress(count, block_size, total_size):
        if total_size > 0:
            pct = min(100, count * block_size * 100 // total_size)
            sys.stdout.write(f"\r  Progress: {pct}%  ")
            sys.stdout.flush()

    last_err = None
    for url in MODEL_URLS:
        print(f"\nTrying: {url}")
        try:
            urllib.request.urlretrieve(url, dest, reporthook=_progress)
            print(f"\nDone! Saved to {dest} ({dest.stat().st_size / 1024:.0f} KB)")
            print("\nNext steps:")
            print("  1. Restart backend (model loads at startup)")
            print("  2. In Settings UI, set anti_spoof_enabled = 1")
            print("  3. Optionally adjust anti_spoof_threshold (default 0.6)")
            return
        except Exception as e:
            dest.unlink(missing_ok=True)
            last_err = e
            print(f"  Failed: {e}")

    print(f"\nAll download attempts failed. Manual steps:")
    print(f"  1. Clone: git clone https://github.com/minivision-ai/Silent-Face-Anti-Spoofing")
    print(f"  2. Copy:  resources/anti_spoof_models/2.7_80x80_MiniFASNetV2.onnx")
    print(f"  3. Save to: {dest}")
    sys.exit(1)


if __name__ == "__main__":
    download()
