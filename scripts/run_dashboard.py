"""
Launch script for JobPilot AI Streamlit Dashboard.
Usage:
    python scripts/run_dashboard.py
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).resolve().parent.parent
    dashboard_app = project_root / "jobpilot" / "dashboard" / "app.py"

    print("=" * 60)
    print(" ✈️  Starting JobPilot AI Streamlit Dashboard")
    print(f" Dashboard script: {dashboard_app}")
    print("=" * 60)

    cmd = [sys.executable, "-m", "streamlit", "run", str(dashboard_app)]
    try:
        subprocess.run(cmd, cwd=str(project_root))
    except KeyboardInterrupt:
        print("\n[JobPilot AI] Dashboard stopped by user.")


if __name__ == "__main__":
    main()
