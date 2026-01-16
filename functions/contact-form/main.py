"""
Cloud Function: Contact Form Handler for Plazo Landing

Receives form submissions and publishes them to Pub/Sub as email messages,
triggering the Agendify orchestrator to respond with appointment options.
"""
import os
import json
import uuid
import functions_framework
from datetime import datetime, timezone
from google.cloud import pubsub_v1
from flask import jsonify

# Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "plazo-infra")
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "plazoapp-emails-incoming")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "contacto@plazo-app.com")

# Pub/Sub client
publisher = pubsub_v1.PublisherClient()


def add_cors_headers(response):
    """Add CORS headers to response."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@functions_framework.http
def contact_form(request):
    """
    Handle contact form submissions.

    Expected POST body (JSON or form-data):
    {
        "nombre": "Juan García",
        "email": "juan@empresa.com",
        "despacho": "Asesoría García",
        "tamano": "1-3",
        "comentario": "Me interesa..." (optional)
    }
    """
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        return add_cors_headers(response)

    if request.method != "POST":
        response = jsonify({"error": "Method not allowed"}), 405
        return add_cors_headers(response[0]), response[1]

    # Parse request data
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
    except Exception as e:
        response = jsonify({"error": f"Invalid request body: {e}"}), 400
        return add_cors_headers(response[0]), response[1]

    # Validate required fields
    required_fields = ["nombre", "email", "despacho", "tamano"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        response = jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
        return add_cors_headers(response[0]), response[1]

    # Extract fields
    nombre = data.get("nombre", "").strip()
    email = data.get("email", "").strip().lower()
    despacho = data.get("despacho", "").strip()
    tamano = data.get("tamano", "").strip()
    comentario = data.get("comentario", "").strip()

    # Basic email validation
    if "@" not in email or "." not in email:
        response = jsonify({"error": "Invalid email address"}), 400
        return add_cors_headers(response[0]), response[1]

    # Compose email body
    body_lines = [
        f"Hola,",
        f"",
        f"Me llamo {nombre} y trabajo en {despacho} ({tamano} personas).",
        f"",
        f"Me gustaría solicitar una demo de Plazo para ver cómo puede ayudarnos a gestionar las citas de nuestros clientes.",
    ]

    if comentario:
        body_lines.extend([
            f"",
            f"Comentario adicional: {comentario}",
        ])

    body_lines.extend([
        f"",
        f"¿Podríamos concertar una cita para la demostración?",
        f"",
        f"Gracias,",
        f"{nombre}",
        f"{email}",
    ])

    text_body = "\n".join(body_lines)

    # Create email message for Pub/Sub (same format as Gmail ingester)
    message_id = f"form-{uuid.uuid4()}"
    received_at = datetime.now(timezone.utc).isoformat()

    email_message = {
        "message_id": message_id,
        "received_at": received_at,
        "from_addr": f"{nombre} <{email}>",
        "to_addr": [CONTACT_EMAIL],
        "cc_addr": [],
        "subject": f"Solicitud de demo - {despacho}",
        "text_body": text_body,
        "html_body": "",
    }

    # Publish to Pub/Sub
    try:
        topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC)
        message_bytes = json.dumps(email_message, ensure_ascii=False).encode("utf-8")

        future = publisher.publish(
            topic_path,
            message_bytes,
            message_id=message_id,
            subject=email_message["subject"][:100],
            sender=email,
            source="landing-form"
        )
        future.result(timeout=10)

        print(f"[ContactForm] Published form submission from {email} to {PUBSUB_TOPIC}")

        response = jsonify({
            "success": True,
            "message": "Solicitud recibida. Te contactaremos pronto."
        })
        return add_cors_headers(response)

    except Exception as e:
        print(f"[ContactForm] Error publishing to Pub/Sub: {e}")
        response = jsonify({"error": "Error processing request. Please try again."}), 500
        return add_cors_headers(response[0]), response[1]
