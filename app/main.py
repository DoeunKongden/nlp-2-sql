from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.api import router
import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = FastAPI()

# Define allowed origins, including the Next.js frontend (localhost:3000)
origins = [
    "http://localhost:3000",  # Next.js frontend
    "http://127.0.0.1:3000"   # localhost alternative
]

# Add CORS middleware with appropriate settings
# app.add_middleware(
#     middleware_class=CORSMiddleware,
#     allow_origins=origins,
#     # List of allowed origins
#     allow_credentials=True,  # Allow cookies and credentials
#     allow_methods=["*"],  # Allow all HTTP methods
#     allow_headers=["*"],  # Allow all headers
# )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Include the routes
app.include_router(router)
