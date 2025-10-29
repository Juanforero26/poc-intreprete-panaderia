#!/bin/bash

# Script de despliegue para Google Cloud Run
# Uso: ./deploy.sh [PROJECT_ID] [SERVICE_NAME] [REGION]

set -e

# Configuración por defecto
DEFAULT_PROJECT_ID="tu-proyecto-gcp"
DEFAULT_SERVICE_NAME="interprete-panaderia"
DEFAULT_REGION="us-central1"

# Obtener parámetros
PROJECT_ID=${1:-$DEFAULT_PROJECT_ID}
SERVICE_NAME=${2:-$DEFAULT_SERVICE_NAME}
REGION=${3:-$DEFAULT_REGION}

echo "🚀 Desplegando $SERVICE_NAME en proyecto $PROJECT_ID (región: $REGION)"

# Verificar que gcloud esté instalado
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI no está instalado"
    echo "Instálalo desde: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Configurar proyecto
echo "📋 Configurando proyecto..."
gcloud config set project $PROJECT_ID

# Habilitar APIs necesarias
echo "🔧 Habilitando APIs necesarias..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable aiplatform.googleapis.com

# Construir y subir imagen a Container Registry
echo "🏗️  Construyendo imagen Docker..."
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"
gcloud builds submit --tag $IMAGE_NAME .

# Desplegar en Cloud Run
echo "🚀 Desplegando en Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 10 \
    --min-instances 0 \
    --port 8080 \
    --set-env-vars "USE_VERTEX=true,VERTEX_REGION=$REGION,DEBUG_MODE=false,MODEL_NAME=gemini-2.0-flash" \
    --timeout 300

# Obtener URL del servicio
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")

echo "✅ ¡Despliegue completado!"
echo "🌐 URL del servicio: $SERVICE_URL"
echo "📊 Panel de control: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME"
