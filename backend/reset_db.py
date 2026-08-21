import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base

def reset():
    print("Dropping all existing database tables...")
    Base.metadata.drop_all(bind=engine)
    print("Recreating all database tables with latest schema...")
    Base.metadata.create_all(bind=engine)
    print("Database reset successfully with latest tables and columns!")

if __name__ == "__main__":
    reset()
