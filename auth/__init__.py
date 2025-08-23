# auth/__init__.py

from .database import engine
from .models import Base

print("Ensuring auth tables exist...")
Base.metadata.create_all(bind=engine)
print("Auth tables ready.")
