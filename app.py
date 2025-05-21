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

# Vérification des variables d'environnement
BUCKET_NAME = os.getenv("BUCKET_NAME")
if not BUCKET_NAME:
    raise ValueError("BUCKET_NAME n'est pas défini dans les variables d'environnement")


app = FastAPI()

# Ajoutez cette configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pour le développement, en production il faudra restreindre
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exemple de modèle pour une personne
class Person(BaseModel):
    nom: str
    age: int

# On récupère le nom du bucket et le chemin du fichier depuis les variables d'environnement
FILE_PATH = os.getenv("FILE_PATH")

def read_file_from_gcs():
    client = storage.Client(project=os.getenv("GCP_PROJECT_ID"))
    bucket = client.bucket(os.getenv("BUCKET_NAME"))
    blob = bucket.blob(os.getenv("FILE_PATH"))
    content = blob.download_as_text()
    if os.getenv("FILE_PATH").endswith('.json'):
        return json.loads(content)
    elif os.getenv("FILE_PATH").endswith('.csv'):
        reader = csv.DictReader(content.splitlines())
        return list(reader)
    else:
        return {"error": "Format de fichier non supporté"}

def write_file_to_gcs(new_entry: dict):
    client = storage.Client(project=os.getenv("GCP_PROJECT_ID"))
    bucket = client.bucket(os.getenv("BUCKET_NAME"))
    blob = bucket.blob(os.getenv("FILE_PATH"))

    try:
        content = blob.download_as_text()
        if os.getenv("FILE_PATH").endswith('.json'):
            data = json.loads(content)
            if not isinstance(data, list):
                data = [data]
        elif os.getenv("FILE_PATH").endswith('.csv'):
            reader = csv.DictReader(content.splitlines())
            data = list(reader)
        else:
            raise Exception("Format de fichier non supporté")
    except Exception:
        data = []

    data.append(new_entry)

    if os.getenv("FILE_PATH").endswith('.json'):
        blob.upload_from_string(json.dumps(data, indent=2))
    elif os.getenv("FILE_PATH").endswith('.csv'):
        import csv
        if data:
            fieldnames = data[0].keys()
            from io import StringIO
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            blob.upload_from_string(output.getvalue())
    else:
        raise Exception("Format de fichier non supporté")

def init_vertex_ai():
    """Initialise la connexion à Vertex AI"""
    try:
        # Initialiser Vertex AI
        vertexai.init(project=os.getenv("GCP_PROJECT_ID"), location=os.getenv("GCP_LOCATION"))
        print("✅ Vertex AI initialisé")
        return True
    except Exception as e:
        print("❌ Erreur lors de l'initialisation de Vertex AI :", e)
        return False

def generate_joke():
    """Génère une blague en utilisant le modèle Gemini"""
    try:
        # Initialisation de Vertex AI
        if not init_vertex_ai():
            raise Exception("Impossible d'initialiser Vertex AI")

        # Création du modèle
        model = GenerativeModel("gemini-2.5-pro-preview-05-06")
        print("✅ Modèle Gemini chargé")
        
        # Liste de différents types de blagues pour plus de variété
        joke_types = [
            "Génère une blague courte et drôle en français sur la technologie.",
            "Génère une blague courte et drôle en français sur la vie quotidienne.",
            "Génère une blague courte et drôle en français sur les animaux.",
            "Génère une blague courte et drôle en français sur la nourriture.",
            "Génère une blague courte et drôle en français sur le travail.",
            "Génère une blague courte et drôle en français sur les voyages.",
            "Génère une blague courte et drôle en français sur l'école.",
            "Génère une blague courte et drôle en français sur les relations.",
            "Génère une blague courte et drôle en français sur le sport.",
            "Génère une blague courte et drôle en français sur la météo."
        ]
        
        # Sélectionner aléatoirement un type de blague
        import random
        prompt = random.choice(joke_types)
        
        # Génération de la blague
        response = model.generate_content(
            prompt + " Réponds uniquement avec la blague, sans introduction ni conclusion. Utilise uniquement des caractères ASCII standard."
        )
        print("✅ Réponse du modèle reçue")
        
        # Nettoyage de la réponse
        joke = response.text.encode('utf-8').decode('utf-8')
        return joke
    except NotFound as nf:
        print("❌ Modèle non trouvé. Vérifie que l'API est activée et que tu es dans la bonne région.")
        raise Exception("Modèle non trouvé")
    except PermissionDenied as pd:
        print("❌ Accès refusé. Vérifie que le compte de service a bien accès à Vertex AI.")
        raise Exception("Accès refusé")
    except Exception as e:
        print("❌ Erreur lors de la génération de la blague :", e)
        raise e

@app.get("/hello")
async def hello():
    return {"message": "Bienvenue sur mon API !"}

@app.get("/status")
async def status():
    current_time = datetime.now().isoformat()
    return {
        "status": "ok",
        "timestamp": current_time
    }

@app.get("/data")
async def get_data(
    filename: str = Query(None, description="Nom du fichier à lire (optionnel)"),
    format: Literal["json", "csv"] = Query(None, description="Format du fichier (json ou csv)"),
    action: Literal["read", "write"] = Query("read", description="Action à effectuer (read ou write)"),
    data: Dict[str, Any] = None
):
    """Gère les fichiers dans le bucket (lecture et écriture)"""
    try:
        client = storage.Client(project=os.getenv("GCP_PROJECT_ID"))
        bucket = client.bucket(BUCKET_NAME)
        
        # Si aucun fichier n'est spécifié, retourner la liste des fichiers
        if not filename:
            blobs = bucket.list_blobs()
            files = []
            for blob in blobs:
                files.append({
                    "name": blob.name,
                    "size": blob.size,
                    "updated": blob.updated.isoformat(),
                    "format": blob.name.split('.')[-1] if '.' in blob.name else 'unknown'
                })
            return {"files": files}
        
        # Si un fichier est spécifié
        blob = bucket.blob(filename)
        
        # Si l'action est write et que des données sont fournies
        if action == "write" and data:
            try:
                content = blob.download_as_text()
                if filename.endswith('.json'):
                    existing_data = json.loads(content)
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
                elif filename.endswith('.csv'):
                    reader = csv.DictReader(content.splitlines())
                    existing_data = list(reader)
                else:
                    existing_data = []
            except Exception:
                existing_data = []

            # Ajouter les nouvelles données
            existing_data.append(data)

            # Écrire le fichier
            if filename.endswith('.json'):
                blob.upload_from_string(json.dumps(existing_data, indent=2))
            elif filename.endswith('.csv'):
                if existing_data:
                    fieldnames = existing_data[0].keys()
                    from io import StringIO
                    output = StringIO()
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(existing_data)
                    blob.upload_from_string(output.getvalue())
            
            return {"message": f"Données ajoutées avec succès à {filename}"}
        
        # Si l'action est read ou non spécifiée
        content = blob.download_as_text()
        file_format = filename.split('.')[-1] if '.' in filename else 'text'
        
        if file_format == 'json':
            data = json.loads(content)
            return {
                "filename": filename,
                "format": "json",
                "content": data
            }
        elif file_format == 'csv':
            reader = csv.DictReader(content.splitlines())
            data = list(reader)
            return {
                "filename": filename,
                "format": "csv",
                "content": data
            }
        else:
            return {
                "filename": filename,
                "format": "text",
                "content": content
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/{filename}")
async def add_data(
    filename: str,
    data: Dict[str, Any]
):
    """Ajoute des données à un fichier spécifique"""
    try:
        client = storage.Client(project=os.getenv("GCP_PROJECT_ID"))
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        
        try:
            content = blob.download_as_text()
            if filename.endswith('.json'):
                existing_data = json.loads(content)
                if not isinstance(existing_data, list):
                    existing_data = [existing_data]
            elif filename.endswith('.csv'):
                reader = csv.DictReader(content.splitlines())
                existing_data = list(reader)
            else:
                existing_data = []
        except Exception:
            existing_data = []

        # Ajouter les nouvelles données
        existing_data.append(data)

        # Écrire le fichier
        if filename.endswith('.json'):
            blob.upload_from_string(json.dumps(existing_data, indent=2))
        elif filename.endswith('.csv'):
            if existing_data:
                fieldnames = existing_data[0].keys()
                from io import StringIO
                output = StringIO()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(existing_data)
                blob.upload_from_string(output.getvalue())
        
        return {"message": f"Données ajoutées avec succès à {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/joke")
async def get_joke():
    """Endpoint pour obtenir une blague générée par IA"""
    try:
        joke = generate_joke()
        return {"joke": joke}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/config")
async def check_config():
    """Vérifie la configuration des variables d'environnement"""
    return {
        "bucket_name": os.getenv("BUCKET_NAME"),
        "file_path": os.getenv("FILE_PATH"),
        "credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    }

@app.get("/debug")
async def debug():
    try:
        client = storage.Client(project=os.getenv("GCP_PROJECT_ID"))
        bucket = client.bucket(os.getenv("BUCKET_NAME"))
        blobs = list(bucket.list_blobs())
        return {
            "project_id": os.getenv("GCP_PROJECT_ID"),
            "bucket_name": os.getenv("BUCKET_NAME"),
            "credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            "credentials_exist": os.path.exists(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")),
            "bucket_exists": bucket.exists(),
            "files_in_bucket": [blob.name for blob in blobs],
            "current_working_directory": os.getcwd()
        }
    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "project_id": os.getenv("GCP_PROJECT_ID"),
            "bucket_name": os.getenv("BUCKET_NAME"),
            "credentials_path": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            "credentials_exist": os.path.exists(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")),
            "current_working_directory": os.getcwd()
        }
