"""Database tools for LangGraph agents."""
from typing import Optional, Dict
from langchain_core.tools import tool
import sys
import os
from pathlib import Path
from utils.logger import log_tool_call

# Add backend to path to access Django models
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
if backend_path.exists() or os.getenv('ENABLE_DJANGO_IN_AGENT', 'false').lower() == 'true':
    import django
    
    # Django settings module - can be overridden via env for microservices
    django_settings = os.getenv('DJANGO_SETTINGS_MODULE', 'receptionist.settings.development')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', django_settings)
    
    django.setup()
    
    from apps.core.models import Customer, Appointment
    from apps.conversations.models import Conversation
else:
    # Django not available - tools will need to use REST API instead
    Customer = None
    Appointment = None
    Conversation = None


@tool
def get_customer(phone: str) -> str:
    """Get customer information by phone number.
    
    Args:
        phone: Customer phone number
    
    Returns:
        Customer information as JSON string or "Not found"
    """
    log_tool_call("get_customer", {"phone": phone})
    try:
        customer = Customer.objects.get(phone=phone)
        result = f"Customer: {customer.name}, Phone: {customer.phone}, Email: {customer.email or 'No email'}"
        log_tool_call("get_customer", {"phone": phone}, result)
        return result
    except Customer.DoesNotExist:
        result = "Customer not found."
        log_tool_call("get_customer", {"phone": phone}, result)
        return result


@tool
def create_customer(name: str, phone: str, email: Optional[str] = None) -> str:
    """Create a new customer.
    
    Args:
        name: Customer name
        phone: Customer phone number
        email: Optional customer email
    
    Returns:
        Customer ID if successful, error message otherwise
    """
    log_tool_call("create_customer", {"name": name, "phone": phone, "email": email})
    try:
        customer, created = Customer.objects.get_or_create(
            phone=phone,
            defaults={'name': name, 'email': email}
        )
        if created:
            result = f"New customer created. ID: {customer.id}, Name: {customer.name}"
        else:
            result = f"Customer already exists. ID: {customer.id}, Name: {customer.name}"
        log_tool_call("create_customer", {"name": name, "phone": phone}, result)
        return result
    except Exception as e:
        result = f"Error creating customer: {str(e)}"
        log_tool_call("create_customer", {"name": name, "phone": phone}, result)
        return result


@tool
def get_appointment(appointment_id: int) -> str:
    """Get appointment information by ID.
    
    Args:
        appointment_id: Appointment ID
    
    Returns:
        Appointment information or "Not found"
    """
    log_tool_call("get_appointment", {"appointment_id": appointment_id})
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        result = (
            f"Appointment ID: {appointment.id}, "
            f"Customer: {appointment.customer.name}, "
            f"Date: {appointment.appointment_date}, "
            f"Service: {appointment.service}, "
            f"Status: {appointment.status}"
        )
        log_tool_call("get_appointment", {"appointment_id": appointment_id}, result)
        return result
    except Appointment.DoesNotExist:
        result = "Appointment not found."
        log_tool_call("get_appointment", {"appointment_id": appointment_id}, result)
        return result


@tool
def find_appointment_by_customer(phone: str, date: Optional[str] = None) -> str:
    """Find appointments for a customer.
    
    Args:
        phone: Customer phone number
        date: Optional date filter (YYYY-MM-DD)
    
    Returns:
        List of appointments or "Not found"
    """
    log_tool_call("find_appointment_by_customer", {"phone": phone, "date": date})
    try:
        customer = Customer.objects.get(phone=phone)
        appointments = Appointment.objects.filter(customer=customer)
        
        if date:
            from django.utils.dateparse import parse_date
            filter_date = parse_date(date)
            if filter_date:
                appointments = appointments.filter(appointment_date__date=filter_date)
        
        if not appointments.exists():
            result = "No appointments found."
        else:
            result = f"Appointments for {customer.name}:\n"
            for apt in appointments:
                result += f"- ID: {apt.id}, Date: {apt.appointment_date}, Service: {apt.service}, Status: {apt.status}\n"
        
        log_tool_call("find_appointment_by_customer", {"phone": phone, "date": date}, result[:200])
        return result
    except Customer.DoesNotExist:
        result = "Customer not found."
        log_tool_call("find_appointment_by_customer", {"phone": phone, "date": date}, result)
        return result
    except Exception as e:
        result = f"Error: {str(e)}"
        log_tool_call("find_appointment_by_customer", {"phone": phone, "date": date}, result)
        return result


@tool
def create_appointment(
    customer_id: int,
    appointment_date: str,
    service: str,
    calendar_event_id: Optional[str] = None,
    notes: str = ""
) -> str:
    """Create a new appointment.
    
    Args:
        customer_id: Customer ID
        appointment_date: Appointment date/time in ISO format
        service: Service name
        calendar_event_id: Optional Google Calendar event ID
        notes: Optional notes
    
    Returns:
        Appointment ID if successful, error message otherwise
    """
    log_tool_call("create_appointment", {
        "customer_id": customer_id,
        "appointment_date": appointment_date,
        "service": service
    })
    try:
        from django.utils.dateparse import parse_datetime
        dt = parse_datetime(appointment_date)
        if not dt:
            result = "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)."
            log_tool_call("create_appointment", {"customer_id": customer_id}, result)
            return result
        
        customer = Customer.objects.get(id=customer_id)
        appointment = Appointment.objects.create(
            customer=customer,
            appointment_date=dt,
            service=service,
            calendar_event_id=calendar_event_id,
            notes=notes,
            status='scheduled'
        )
        result = f"Appointment created. ID: {appointment.id}"
        log_tool_call("create_appointment", {"customer_id": customer_id}, result)
        return result
    except Customer.DoesNotExist:
        result = "Customer not found."
        log_tool_call("create_appointment", {"customer_id": customer_id}, result)
        return result
    except Exception as e:
        result = f"Error creating appointment: {str(e)}"
        log_tool_call("create_appointment", {"customer_id": customer_id}, result)
        return result


@tool
def cancel_appointment(appointment_id: int) -> str:
    """Cancel an appointment.
    
    Args:
        appointment_id: Appointment ID
    
    Returns:
        Success or error message
    """
    log_tool_call("cancel_appointment", {"appointment_id": appointment_id})
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        appointment.status = 'cancelled'
        appointment.save()
        result = f"Appointment {appointment_id} has been cancelled."
        log_tool_call("cancel_appointment", {"appointment_id": appointment_id}, result)
        return result
    except Appointment.DoesNotExist:
        result = "Appointment not found."
        log_tool_call("cancel_appointment", {"appointment_id": appointment_id}, result)
        return result
    except Exception as e:
        result = f"Error cancelling appointment: {str(e)}"
        log_tool_call("cancel_appointment", {"appointment_id": appointment_id}, result)
        return result


# Export all tools
DATABASE_TOOLS = [
    get_customer,
    create_customer,
    get_appointment,
    find_appointment_by_customer,
    create_appointment,
    cancel_appointment,
]
