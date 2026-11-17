"""AgentSINC local-first backend package."""

from pathlib import Path

from dotenv import load_dotenv

# Load local backend configuration without overriding explicit process env vars.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
