
from database import Base, engine
from models import MealAnalysis


def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

    print("Tables:", list(Base.metadata.tables.keys()))


if __name__ == "__main__":
    create_tables()
