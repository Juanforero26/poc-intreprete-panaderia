# 🚀 Despliegue en Google Cloud

Esta guía te ayudará a desplegar tu aplicación de intérprete de panadería en Google Cloud Run.

## 📋 Prerrequisitos

1. **Cuenta de Google Cloud** con facturación habilitada
2. **Google Cloud CLI** instalado y configurado
3. **Docker** instalado (opcional, para pruebas locales)

### Instalación de Google Cloud CLI

```bash
# macOS (con Homebrew)
brew install google-cloud-sdk

# O descarga desde:
# https://cloud.google.com/sdk/docs/install
```

### Configuración inicial

```bash
# Iniciar sesión
gcloud auth login

# Configurar proyecto (reemplaza con tu PROJECT_ID)
gcloud config set project TU_PROJECT_ID

# Habilitar APIs necesarias
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

## 🔧 Configuración de Vertex AI

Para usar Gemini en producción, necesitas configurar las credenciales:

### Opción 1: Service Account (Recomendado para producción)

1. Ve a [Google Cloud Console > IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Crea un nuevo Service Account con estos roles:
   - `Vertex AI User`
   - `AI Platform Developer`
3. Descarga la clave JSON
4. Configúrala en Cloud Run (ver sección de despliegue)

### Opción 2: Cuenta de usuario (Para desarrollo)

```bash
# Autenticar con tu cuenta personal
gcloud auth application-default login
```

## 🚀 Despliegue

### Método 1: Script automatizado (Recomendado)

```bash
# Hacer ejecutable el script
chmod +x deploy.sh

# Ejecutar despliegue
./deploy.sh TU_PROJECT_ID interprete-panaderia us-central1
```

### Método 2: Comandos manuales

```bash
# 1. Construir y subir imagen
gcloud builds submit --tag gcr.io/TU_PROJECT_ID/interprete-panaderia .

# 2. Desplegar en Cloud Run
gcloud run deploy interprete-panaderia \
    --image gcr.io/TU_PROJECT_ID/interprete-panaderia \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 1Gi \
    --cpu 1 \
    --max-instances 10 \
    --min-instances 0 \
    --port 8080 \
    --set-env-vars "USE_VERTEX=true,VERTEX_REGION=us-central1,DEBUG_MODE=false,MODEL_NAME=gemini-2.0-flash" \
    --timeout 300
```

### Método 3: Cloud Build (CI/CD)

```bash
# Desplegar usando Cloud Build
gcloud builds submit --config cloudbuild.yaml
```

## 🔐 Configuración de Seguridad

### Variables de entorno en Cloud Run

Puedes configurar variables sensibles en la consola de Cloud Run:

1. Ve a [Cloud Run Console](https://console.cloud.google.com/run)
2. Selecciona tu servicio
3. Ve a "Edit & Deploy New Revision"
4. En la pestaña "Variables & Secrets", agrega:
   - `GOOGLE_CLOUD_PROJECT`: Tu PROJECT_ID
   - `VERTEX_REGION`: us-central1
   - `USE_VERTEX`: true
   - `DEBUG_MODE`: false
   - `MODEL_NAME`: gemini-2.0-flash

### Service Account para Vertex AI

Si usas Service Account, configura la variable:
- `GOOGLE_APPLICATION_CREDENTIALS`: Ruta al archivo JSON

## 🧪 Pruebas

### Prueba local con Docker

```bash
# Construir imagen localmente
docker build -t interprete-panaderia .

# Ejecutar contenedor
docker run -p 8080:8080 \
  -e USE_VERTEX=false \
  -e DEBUG_MODE=true \
  interprete-panaderia

# Probar en http://localhost:8080
```

### Prueba en Cloud Run

```bash
# Obtener URL del servicio
gcloud run services describe interprete-panaderia --region=us-central1 --format="value(status.url)"

# Probar endpoint
curl -X POST "TU_URL/interpretar" \
  -H "Content-Type: application/json" \
  -d '{"texto_libre": "Quiero 5 buñuelos para mañana", "canal": "formulario_web"}'
```

## 📊 Monitoreo

### Logs

```bash
# Ver logs en tiempo real
gcloud run services logs tail interprete-panaderia --region=us-central1

# Ver logs históricos
gcloud run services logs read interprete-panaderia --region=us-central1
```

### Métricas

- Ve a [Cloud Run Console](https://console.cloud.google.com/run)
- Selecciona tu servicio
- Revisa las métricas de CPU, memoria, requests, etc.

## 🔄 Actualizaciones

Para actualizar tu aplicación:

```bash
# Método 1: Script
./deploy.sh TU_PROJECT_ID interprete-panaderia us-central1

# Método 2: Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Método 3: Manual
gcloud builds submit --tag gcr.io/TU_PROJECT_ID/interprete-panaderia .
gcloud run deploy interprete-panaderia --image gcr.io/TU_PROJECT_ID/interprete-panaderia --region=us-central1
```

## 💰 Costos

Cloud Run cobra por:
- **CPU**: Solo cuando hay requests activos
- **Memoria**: Solo cuando hay requests activos
- **Requests**: Por cada invocación
- **Vertex AI**: Por tokens procesados

**Estimación mensual** (con uso moderado):
- Cloud Run: $5-20 USD
- Vertex AI: $10-50 USD (dependiendo del uso)

## 🛠️ Solución de Problemas

### Error de autenticación con Vertex AI

```bash
# Verificar credenciales
gcloud auth list
gcloud auth application-default print-access-token

# Re-autenticar si es necesario
gcloud auth application-default login
```

### Error de permisos

```bash
# Verificar roles del proyecto
gcloud projects get-iam-policy TU_PROJECT_ID

# Agregar roles necesarios
gcloud projects add-iam-policy-binding TU_PROJECT_ID \
    --member="user:TU_EMAIL" \
    --role="roles/aiplatform.user"
```

### Error de memoria

Si ves errores de memoria, aumenta el límite:

```bash
gcloud run deploy interprete-panaderia \
    --memory 2Gi \
    --region us-central1
```

## 📞 Soporte

- [Documentación de Cloud Run](https://cloud.google.com/run/docs)
- [Documentación de Vertex AI](https://cloud.google.com/vertex-ai/docs)
- [Soporte de Google Cloud](https://cloud.google.com/support)
