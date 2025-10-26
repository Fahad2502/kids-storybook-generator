# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import from our other backend files
from .database import init_database
from .routers import users, stories # <-- ADD THIS IMPORT

# Create the FastAPI app instance
app = FastAPI(
    title="Kids Story API",
    description="API for generating and retrieving children's stories."
)

# Run Database Initialization on Startup
@app.on_event("startup")
async def startup_event():
    """Create database tables when the app starts."""
    init_database()

# Add CORS Middleware
origins = [
    "http://localhost", "http://localhost:8080", "http://127.0.0.1:5500",
    "http://localhost:63342", "null"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Basic Root Endpoint
@app.get("/")
def read_root():
    """Provides a simple message indicating the API is running."""
    return {"message": "Kids Story API (Backend) is running!"}

# --- Include Routers ---
app.include_router(users.router)    # <-- ADD THIS LINE
app.include_router(stories.router)  # <-- ADD THIS LINE
# --- End Include Routers ---

print("Backend main.py loaded and routers included.") # Updated confirmation