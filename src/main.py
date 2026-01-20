import sys
sys.path.append("/src")

from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ Application started and database tables created!")
    yield
    print("🛑 Application shutting down!")

# ✅ Crée une seule fois l'application
app = FastAPI(lifespan=lifespan)

# ✅ Déclare les routes après
@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)