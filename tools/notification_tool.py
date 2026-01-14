"""Notification tools for email and SMS."""
from typing import Optional
from langchain_core.tools import tool
import sys
import os
from pathlib import Path

# Add backend to path
# Supports both monorepo (relative path) and microservices (absolute path via env)
backend_path_env = os.getenv('BACKEND_PATH')
if backend_path_env:
    backend_path = Path(backend_path_env)
else:
    # Monorepo: relative path
    backend_path = Path(__file__).parent.parent.parent / 'backend'

if backend_path.exists():
    sys.path.insert(0, str(backend_path))

# Setup Django
# Supports both monorepo and microservices via environment variable
# Only setup Django if backend path exists (monorepo) or explicitly enabled
from twilio.rest import Client

if backend_path.exists() or os.getenv('ENABLE_DJANGO_IN_AGENT', 'false').lower() == 'true':
    import django
    
    # Django settings module - can be overridden via env for microservices
    django_settings = os.getenv('DJANGO_SETTINGS_MODULE', 'receptionist.settings.development')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', django_settings)
    
    django.setup()
    
    from django.core.mail import send_mail
    from django.conf import settings
    from apps.core.models import Customer, Appointment
    
    DJANGO_AVAILABLE = True
else:
    # Django not available - tools will need to use REST API instead
    DJANGO_AVAILABLE = False
    Customer = None
    Appointment = None
    settings = type('Settings', (), {
        'DEFAULT_FROM_EMAIL': os.getenv('DEFAULT_FROM_EMAIL', 'noreply@example.com'),
        'TWILIO_ACCOUNT_SID': os.getenv('TWILIO_ACCOUNT_SID', ''),
        'TWILIO_AUTH_TOKEN': os.getenv('TWILIO_AUTH_TOKEN', ''),
        'TWILIO_PHONE_NUMBER': os.getenv('TWILIO_PHONE_NUMBER', ''),
    })()
    
    def send_mail(*args, **kwargs):
        raise NotImplementedError("Django email not available. Use REST API instead.")


def get_twilio_client():
    """Get Twilio client."""
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


@tool
def send_email(to_email: str, subject: str, message: str) -> str:
    """Send an email.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        message: Email message body
    
    Returns:
        Success or error message
    """
    log_tool_call("send_email", {"to_email": to_email, "subject": subject})
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        result = f"Email sent to {to_email}"
        log_tool_call("send_email", {"to_email": to_email, "subject": subject}, result)
        return result
    except Exception as e:
        result = f"Error sending email: {str(e)}"
        log_tool_call("send_email", {"to_email": to_email, "subject": subject}, result)
        return result


@tool
def send_sms(to_phone: str, message: str) -> str:
    """Send an SMS message.
    
    Args:
        to_phone: Recipient phone number (E.164 format)
        message: SMS message body
    
    Returns:
        Success or error message
    """
    log_tool_call("send_sms", {"to_phone": to_phone, "message_length": len(message)})
    try:
        client = get_twilio_client()
        message_obj = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_phone
        )
        result = f"SMS sent to {to_phone}. Message SID: {message_obj.sid}"
        log_tool_call("send_sms", {"to_phone": to_phone}, result)
        return result
    except Exception as e:
        result = f"Error sending SMS: {str(e)}"
        log_tool_call("send_sms", {"to_phone": to_phone}, result)
        return result


@tool
def send_booking_confirmation(appointment_id: int) -> str:
    """Send booking confirmation email and SMS.
    
    Args:
        appointment_id: Appointment ID
    
    Returns:
        Success or error message
    """
    log_tool_call("send_booking_confirmation", {"appointment_id": appointment_id})
    try:
        appointment = Appointment.objects.select_related('customer').get(id=appointment_id)
        customer = appointment.customer
        
        # Format date
        date_str = appointment.appointment_date.strftime('%Y-%m-%d at %H:%M')
        
        # Email subject and message
        email_subject = "Booking Confirmation"
        email_message = f"""Hello {customer.name},

Your appointment has been confirmed:

Date and time: {date_str}
Service: {appointment.service}
Status: {appointment.status}

Thank you for your booking!

Best regards,
AI Receptionist
"""
        
        # SMS message
        sms_message = f"Hello {customer.name}! Your appointment {date_str} for {appointment.service} has been confirmed. Thank you!"
        
        results = []
        
        # Send email if customer has email
        if customer.email:
            email_result = send_email(customer.email, email_subject, email_message)
            results.append(email_result)
        
        # Send SMS
        sms_result = send_sms(customer.phone, sms_message)
        results.append(sms_result)
        
        result = "; ".join(results)
        log_tool_call("send_booking_confirmation", {"appointment_id": appointment_id}, result)
        return result
    
    except Appointment.DoesNotExist:
        result = "Appointment not found."
        log_tool_call("send_booking_confirmation", {"appointment_id": appointment_id}, result)
        return result
    except Exception as e:
        result = f"Error sending confirmation: {str(e)}"
        log_tool_call("send_booking_confirmation", {"appointment_id": appointment_id}, result)
        return result


@tool
def send_cancellation_notification(appointment_id: int) -> str:
    """Send cancellation notification email and SMS.
    
    Args:
        appointment_id: Appointment ID
    
    Returns:
        Success or error message
    """
    log_tool_call("send_cancellation_notification", {"appointment_id": appointment_id})
    try:
        appointment = Appointment.objects.select_related('customer').get(id=appointment_id)
        customer = appointment.customer
        
        date_str = appointment.appointment_date.strftime('%Y-%m-%d at %H:%M')
        
        email_subject = "Appointment Cancelled"
        email_message = f"""Hello {customer.name},

Your appointment has been cancelled:

Date and time: {date_str}
Service: {appointment.service}

If you would like to book a new appointment, please contact us.

Best regards,
AI Receptionist
"""
        
        sms_message = f"Hello {customer.name}! Your appointment {date_str} for {appointment.service} has been cancelled."
        
        results = []
        
        if customer.email:
            email_result = send_email(customer.email, email_subject, email_message)
            results.append(email_result)
        
        sms_result = send_sms(customer.phone, sms_message)
        results.append(sms_result)
        
        result = "; ".join(results)
        log_tool_call("send_cancellation_notification", {"appointment_id": appointment_id}, result)
        return result
    
    except Appointment.DoesNotExist:
        result = "Appointment not found."
        log_tool_call("send_cancellation_notification", {"appointment_id": appointment_id}, result)
        return result
    except Exception as e:
        result = f"Error sending cancellation notification: {str(e)}"
        log_tool_call("send_cancellation_notification", {"appointment_id": appointment_id}, result)
        return result


# Export all tools
NOTIFICATION_TOOLS = [
    send_email,
    send_sms,
    send_booking_confirmation,
    send_cancellation_notification,
]
