from fastapi import FastAPI
from app.api.routes import api_router
from app.config import settings

app = FastAPI(title="Notification System API")

# Include API routes
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)