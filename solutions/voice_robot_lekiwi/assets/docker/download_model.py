# download_models.py
import openwakeword

# This will download all pre-trained models to ~/.openwakeword/
# You can specify a different directory using openwakeword.utils.download_models(model_dir="your/path")
print("Downloading pre-trained models...")
openwakeword.utils.download_models()
print("Download complete.")
