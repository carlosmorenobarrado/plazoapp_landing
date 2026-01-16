# Contact Form Cloud Function

Cloud Function que recibe solicitudes del formulario de demo y las publica a Pub/Sub para activar el flujo de Agendify.

## Flujo

```
Usuario rellena formulario en plazo-app.com
         ↓
Landing (JS) → POST → Esta Cloud Function
         ↓
Publica a plazoapp-emails-incoming (Pub/Sub)
         ↓
Email Processor → Orchestrator → Respuesta al usuario
```

## Despliegue

```bash
# Desde el directorio functions/contact-form
cd functions/contact-form

# Desplegar la función
gcloud functions deploy contact-form \
  --gen2 \
  --runtime=python312 \
  --region=europe-west1 \
  --source=. \
  --entry-point=contact_form \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=plazo-infra,PUBSUB_TOPIC=plazoapp-emails-incoming,CONTACT_EMAIL=contacto@plazo-app.com" \
  --project=plazo-infra
```

## Variables de Entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `GCP_PROJECT_ID` | ID del proyecto GCP | `plazo-infra` |
| `PUBSUB_TOPIC` | Topic de Pub/Sub | `plazoapp-emails-incoming` |
| `CONTACT_EMAIL` | Email de destino | `contacto@plazo-app.com` |

## Permisos Necesarios

La Cloud Function necesita permisos para publicar a Pub/Sub. Por defecto usa el service account `PROJECT_ID@appspot.gserviceaccount.com`.

```bash
# Dar permisos de publicación a Pub/Sub
gcloud pubsub topics add-iam-policy-binding plazoapp-emails-incoming \
  --member="serviceAccount:plazo-infra@appspot.gserviceaccount.com" \
  --role="roles/pubsub.publisher" \
  --project=plazo-infra
```

## Test Local

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar localmente
functions-framework --target=contact_form --debug

# Probar
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Test","email":"test@example.com","despacho":"Test SL","tamano":"1-3"}'
```

## URL de Producción

Una vez desplegada:
```
https://europe-west1-plazo-infra.cloudfunctions.net/contact-form
```
