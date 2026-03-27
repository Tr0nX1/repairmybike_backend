import requests
import logging
from django.conf import settings
from .models import WhatsAppMessage

logger = logging.getLogger(__name__)

def send_whatsapp_message(user, phone_number, message_text):
    """
    Sends a WhatsApp message using the Kapso API.
    """
    if not settings.KAPSO_API_KEY or not settings.KAPSO_PHONE_NUMBER_ID:
        logger.warning("Kapso API Key or Phone Number ID not configured. WhatsApp disabled.")
        return False

    # Clean phone number (remove +, spaces, etc. if needed, but usually API wants digits only)
    # Kapso might handle various formats, but let's keep it simple.
    clean_phone = ''.join(filter(str.isdigit, phone_number))
    
    # Base URL from settings, should end with the phone number id for some APIs, 
    # but let's assume it's the base for messages
    url = f"{settings.KAPSO_BASE_URL}/{settings.KAPSO_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.KAPSO_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": clean_phone,
        "type": "text",
        "text": {
            "body": message_text
        }
    }

    # Create a log entry first
    log_entry = WhatsAppMessage.objects.create(
        user=user,
        phone_number=phone_number,
        message_text=message_text,
        status='sent'
    )

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response_data = response.json()
        
        if response.status_code in [200, 201]:
            # Extract message ID from response (Kapso/Meta format)
            # Typically: {"messages": [{"id": "..."}]}
            if "messages" in response_data and len(response_data["messages"]) > 0:
                log_entry.kapso_message_id = response_data["messages"][0].get("id")
            
            log_entry.status = 'sent'
            log_entry.save()
            logger.info(f"WhatsApp message sent successfully to {phone_number}")
            return True
        else:
            log_entry.status = 'failed'
            log_entry.error_message = response.text
            log_entry.save()
            logger.error(f"Failed to send WhatsApp message: {response.text}")
            return False
            
    except Exception as e:
        log_entry.status = 'failed'
        log_entry.error_message = str(e)
        log_entry.save()
        logger.error(f"Exception while sending WhatsApp message: {str(e)}")
        return False
