# Utiliser une image Python officielle comme base
FROM python:3.9-slim

# Définir le répertoire de travail
WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le fichier de credentials
COPY blague-d573c0277d93.json /app/credentials.json

# Copier le code de l'application
COPY app.py .

# Créer le fichier .env
RUN echo "BUCKET_NAME=blague1\n\
FILE_PATH=data.json\n\
GCP_PROJECT_ID=blague\n\
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json\n\
GCP_LOCATION=us-central1" > /app/.env

# Exposer le port 8080 (port Cloud Run)
EXPOSE 8080

# Commande pour démarrer l'application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
