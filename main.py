import uvicorn
from fastapi import FastAPI
from src.websocket_routes import router as websocket_router
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Include the WebSocket router
app.include_router(websocket_router)

@app.get("/")
def read_root():
    return {"Hello": "World"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
