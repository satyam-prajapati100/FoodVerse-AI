from fastapi import FastAPI

app = FastAPI(
    title="FoodVerse AI API",
    description="Backend API for the FoodVerse AI food intelligence platform",
    version="0.1.0",
)


@app.get("/")
def home():
    return {
        "message": "Welcome to FoodVerse AI!",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "project": "FoodVerse AI",
    }
