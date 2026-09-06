# 24/7 Intelligent Code Reviewer

GCP project using Flask, Cloud Run, Vertex AI Gemini and Firestore.

## Deploy
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com
gcloud artifacts repositories create intelligent-code-reviewer --repository-format=docker --location=asia-south1
gcloud run deploy intelligent-code-reviewer --source . --region asia-south1 --allow-unauthenticated

## Local
gcloud auth application-default login
set GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
set GOOGLE_CLOUD_LOCATION=global
pip install -r requirements.txt
python -m app.main
