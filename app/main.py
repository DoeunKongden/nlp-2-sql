from fastapi import FastAPI
from app.routes.api import router
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = FastAPI()

# Include the routes
app.include_router(router)

