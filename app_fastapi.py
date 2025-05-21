from fastapi import FastAPI, HTTPException, Query
from datetime import datetime
from pydantic import BaseModel
from google.cloud import storage
from typing import Dict, Any, Literal, List
import os
import json
import csv
import vertexai
from vertexai.preview.generative_models import GenerativeModel
from google.api_core.exceptions import NotFound, PermissionDenied
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
 
# Charger les variables d'environnement
load_dotenv()
BUCKET_NAME = os.getenv("BUCKET_NAME")
if not BUCKET_NAME:
    raise ValueError("BUCKET_NAME n'est pas défini dans les variables d'environnement")
 
FILE_PATH = os.getenv("FILE_PATH")
 
app = FastAPI()
 
# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# Modèle Pydantic
class Person(BaseModel):
    nom: str
    age: int
