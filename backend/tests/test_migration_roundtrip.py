import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, text


def test_managed_platform_migration_preserves_existing_chat_data(tmp_path):
    database = tmp_path / "legacy-chat.db"
    url = f"sqlite:///{database}"
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    env["PYTHONPATH"] = str(Path(__file__).parents[1])
    root = Path(__file__).parents[1]
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "0001_initial"], cwd=root, env=env, check=True, capture_output=True, text=True)
    engine = create_engine(url)
    now = datetime.now(timezone.utc).isoformat()
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO users (id,full_name,email,password_hash,is_active,created_at,updated_at) VALUES ('legacy-user','Legacy Citizen','legacy@example.com','hash',1,:now,:now)"), {"now":now})
        connection.execute(text("INSERT INTO conversations (id,user_id,title,created_at,updated_at) VALUES ('legacy-chat','legacy-user','Existing chat',:now,:now)"), {"now":now})
        connection.execute(text("INSERT INTO messages (id,conversation_id,role,content,sequence_no,created_at,updated_at) VALUES ('legacy-message','legacy-chat','user','keep this message',1,:now,:now)"), {"now":now})
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root, env=env, check=True, capture_output=True, text=True)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT user_email FROM conversations WHERE id='legacy-chat'")).scalar_one() == "legacy@example.com"
        assert connection.execute(text("SELECT content FROM messages WHERE id='legacy-message'")).scalar_one() == "keep this message"
    subprocess.run([sys.executable, "-m", "alembic", "downgrade", "0001_initial"], cwd=root, env=env, check=True, capture_output=True, text=True)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT title FROM conversations WHERE id='legacy-chat'")).scalar_one() == "Existing chat"
        assert connection.execute(text("SELECT content FROM messages WHERE id='legacy-message'")).scalar_one() == "keep this message"
    engine.dispose()
