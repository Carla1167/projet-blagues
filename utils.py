# utils.py
import os
import csv
import json
from google.cloud import storage, aiplatform as vertexai
from vertexai.generative_models import GenerativeModel
from google.api_core.exceptions import NotFound, PermissionDenied

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
        from io import StringIO
        output = StringIO()
        fieldnames = data[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        blob.upload_from_string(output.getvalue())
    else:
        raise Exception("Format de fichier non supporté")

def init_vertex_ai():
    try:
        vertexai.init(project=os.getenv("GCP_PROJECT_ID"), location=os.getenv("GCP_LOCATION"))
        print(" Vertex AI initialisé")
        return True
    except Exception as e:
        print(" Erreur Vertex AI :", e)
        return False

def generate_joke():
    try:
        if not init_vertex_ai():
            raise Exception("Impossible d'initialiser Vertex AI")
        model = GenerativeModel("gemini-2.5-pro-preview-05-06")
        print(" Modèle Gemini chargé")
        import random
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
        prompt = random.choice(joke_types)
        response = model.generate_content(prompt + " Réponds uniquement avec la blague, sans introduction ni conclusion.")
        return response.text.encode('utf-8').decode('utf-8')
    except (NotFound, PermissionDenied, Exception) as e:
        print(" Erreur génération blague :", e)
        raise e
