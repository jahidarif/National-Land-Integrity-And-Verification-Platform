import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.application.use_cases.auth.seed_admin import SeedAdmin

if __name__ == "__main__":
    SeedAdmin().execute()
