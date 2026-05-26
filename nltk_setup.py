# nltk_setup.py
# Run at build time to pre-download required NLTK data
# This avoids runtime downloads on cloud servers with restricted filesystems

import nltk
import os

nltk_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nltk_data')
os.makedirs(nltk_data_dir, exist_ok=True)

print(f"[NLTK Setup] Downloading tokenizer data to: {nltk_data_dir}")
nltk.download('punkt', download_dir=nltk_data_dir)
nltk.download('punkt_tab', download_dir=nltk_data_dir)
print("[NLTK Setup] Done!")
