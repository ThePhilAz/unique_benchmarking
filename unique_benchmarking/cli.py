import subprocess
from pathlib import Path


def start():
    # Get the path to app.py relative to this CLI script
    app_path = Path(__file__).parent / "app.py"
    subprocess.run(["streamlit", "run", str(app_path)])
