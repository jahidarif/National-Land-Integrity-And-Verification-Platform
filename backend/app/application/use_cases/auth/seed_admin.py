from uuid import uuid4
from app.core.config import settings
from app.domain.models import User, Role
from app.infrastructure.adapters.password_hasher import BcryptPasswordHasher
from app.infrastructure.database import SessionLocal

class SeedAdmin:
    def execute(self) -> bool:
        if not settings.admin_seed_email or not settings.admin_seed_password:
            print("Admin seed skipped: configure ADMIN_SEED_EMAIL and ADMIN_SEED_PASSWORD")
            return False
        db = SessionLocal()
        try:
            email = settings.admin_seed_email.strip().lower()
            if db.query(User).filter(User.email == email).first():
                print(f"Admin seed skipped: {email} already exists")
                return False
            db.add(User(id=str(uuid4()), full_name=settings.admin_seed_name.strip(), email=email,
                        password_hash=BcryptPasswordHasher().hash(settings.admin_seed_password),
                        role=Role.ADMIN, is_active=True))
            db.commit()
            print(f"Admin seed created: {email}")
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
