"""Type:  python run.py   -> installs what is needed (first time) and opens the app."""
import subprocess
import sys

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"], check=False)
subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"], check=False)
