#!/bin/bash

# Script para controlar la aplicación en Google Cloud Run
# Uso: ./cloud-control.sh [start|stop|status|restart]

SERVICE_NAME="interprete-panaderia"
REGION="us-central1"
PROJECT_ID="poc-interprete-panaderia"

case "$1" in
  "start")
    echo "🚀 Habilitando aplicación..."
    gcloud run services update $SERVICE_NAME \
      --region=$REGION \
      --min-instances=0 \
      --max-instances=10
    echo "✅ Aplicación habilitada"
    ;;
  
  "stop")
    echo "⏸️  Deshabilitando aplicación..."
    gcloud run services update $SERVICE_NAME \
      --region=$REGION \
      --min-instances=0 \
      --max-instances=1
    echo "✅ Aplicación deshabilitada (escala a 0 cuando no hay tráfico)"
    ;;
  
  "pause")
    echo "🛑 Pausando tráfico..."
    gcloud run services update-traffic $SERVICE_NAME \
      --region=$REGION \
      --to-revisions=LATEST=0
    echo "✅ Tráfico pausado"
    ;;
  
  "resume")
    echo "▶️  Reanudando tráfico..."
    gcloud run services update-traffic $SERVICE_NAME \
      --region=$REGION \
      --to-revisions=LATEST=100
    echo "✅ Tráfico reanudado"
    ;;
  
  "status")
    echo "📊 Estado de la aplicación:"
    gcloud run services describe $SERVICE_NAME \
      --region=$REGION \
      --format="table(status.url,status.conditions[0].status,spec.template.metadata.annotations['autoscaling.knative.dev/minScale'],spec.template.metadata.annotations['autoscaling.knative.dev/maxScale'])"
    ;;
  
  "logs")
    echo "📋 Logs de la aplicación:"
    gcloud run services logs tail $SERVICE_NAME --region=$REGION
    ;;
  
  "restart")
    echo "🔄 Reiniciando aplicación..."
    gcloud run services update $SERVICE_NAME \
      --region=$REGION \
      --min-instances=0 \
      --max-instances=10
    echo "✅ Aplicación reiniciada"
    ;;
  
  *)
    echo "Uso: $0 {start|stop|pause|resume|status|logs|restart}"
    echo ""
    echo "Comandos disponibles:"
    echo "  start   - Habilitar aplicación (escalado normal)"
    echo "  stop    - Deshabilitar aplicación (escala a 0)"
    echo "  pause   - Pausar tráfico (mantiene instancias)"
    echo "  resume  - Reanudar tráfico"
    echo "  status  - Ver estado actual"
    echo "  logs    - Ver logs en tiempo real"
    echo "  restart - Reiniciar aplicación"
    exit 1
    ;;
esac
