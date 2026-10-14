"""Start Lab 10 · AskIT Ops Control Room with ONE command:   python run.py

It installs what the lab needs (first time only), then runs:  streamlit run app.py
Keep this window open.
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEED = ["streamlit", "pandas", "langchain", "langchain_aws", "langchain_openai", "langfuse", "boto3", "dotenv"]   # import names that must be present


def missing():
    return [m for m in NEED if importlib.util.find_spec(m) is None]


def main():
    os.chdir(HERE)
    if sys.version_info < (3, 9):
        print("You need Python 3.9 or newer. Your version is", sys.version.split()[0])
        return 1
    py = sys.executable
    if missing():
        print("Step 1 of 2: installing the lab packages (first time only, a few minutes). Please wait...")
        cmd = [py, "-m", "pip", "install", "--disable-pip-version-check", "-r", "requirements.txt"]
        if sys.prefix == getattr(sys, "base_prefix", sys.prefix):
            cmd.insert(4, "--user")   # normal Python: install for this user only
        rc = subprocess.call(cmd)
        # A first "pip install --user" creates a folder this running Python has not seen yet.
        # Add it and refresh, otherwise the check below wrongly says "not installed".
        try:
            import site
            usp = site.getusersitepackages()
            if usp not in sys.path and os.path.isdir(usp):
                sys.path.append(usp)
        except Exception:
            pass
        importlib.invalidate_caches()
        if rc != 0 or missing():
            print("\nThe install did not work. Check your internet or VPN, then run this command again.")
            print("Still stuck? Tell the trainer in the Teams chat. Write: install failed.")
            return 1
    # Streamlit asks for an email on first start. This empty file skips that question.
    cred = Path.home() / ".streamlit" / "credentials.toml"
    if not cred.exists():
        cred.parent.mkdir(parents=True, exist_ok=True)
        cred.write_text('[general]\nemail = ""\n')
    print("Step 2 of 2: starting the lab. Your browser opens by itself.")
    print("If it does not, open the link below that says Local URL. Keep this window open. Stop with Ctrl+C.\n")
    cmd = [py, "-m", "streamlit", "run", "app.py", "--browser.gatherUsageStats", "false"]
    if os.environ.get("LAB_HEADLESS"):
        cmd += ["--server.headless", "true", "--server.port", os.environ.get("LAB_PORT", "8501")]
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
