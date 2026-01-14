"""Dummy calendar tools for LangGraph agents (using in-memory data)."""
from typing import Optional
from datetime import datetime, timedelta
from langchain_core.tools import tool
from utils.logger import log_tool_call

# In-memory storage for dummy calendar events
_calendar_events = []
_event_counter = 1


@tool
def check_availability(start_time: str, end_time: str) -> str:
    """Check if a time slot is available in the calendar.
    
    Args:
        start_time: Start time in ISO format (YYYY-MM-DDTHH:MM:SS)
        end_time: End time in ISO format (YYYY-MM-DDTHH:MM:SS)
    
    Returns:
        String indicating availability status
    """
    log_tool_call("check_availability", {"start_time": start_time, "end_time": end_time})
    try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00').replace('+00:00', ''))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00').replace('+00:00', ''))
        
        # Check for overlapping events
        overlapping = [
            e for e in _calendar_events
            if not (e['end'] <= start_dt or e['start'] >= end_dt)
        ]
        
        if not overlapping:
            result = f"Time slot {start_time} to {end_time} is available."
        else:
            result = f"Time slot is occupied. Found {len(overlapping)} booking(s)."
        log_tool_call("check_availability", {"start_time": start_time, "end_time": end_time}, result)
        return result
    except Exception as e:
        result = f"Error checking availability: {str(e)}"
        log_tool_call("check_availability", {"start_time": start_time, "end_time": end_time}, result)
        return result


@tool
def create_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    attendee_email: Optional[str] = None
) -> str:
    """Create a new calendar event.
    
    Args:
        summary: Event title/summary
        start_time: Start time in ISO format (YYYY-MM-DDTHH:MM:SS)
        end_time: End time in ISO format (YYYY-MM-DDTHH:MM:SS)
        description: Event description
        attendee_email: Optional attendee email
    
    Returns:
        Event ID if successful, error message otherwise
    """
    log_tool_call("create_calendar_event", {
        "summary": summary,
        "start_time": start_time,
        "end_time": end_time,
        "attendee_email": attendee_email
    })
    try:
        global _event_counter
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00').replace('+00:00', ''))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00').replace('+00:00', ''))
        
        event_id = f"dummy_event_{_event_counter}"
        _event_counter += 1
        
        event = {
            'id': event_id,
            'summary': summary,
            'description': description,
            'start': start_dt,
            'end': end_dt,
            'attendee_email': attendee_email
        }
        _calendar_events.append(event)
        
        result = f"Booking created. Event ID: {event_id}"
        log_tool_call("create_calendar_event", {"summary": summary}, result)
        return result
    except Exception as e:
        result = f"Error creating booking: {str(e)}"
        log_tool_call("create_calendar_event", {"summary": summary}, result)
        return result


@tool
def cancel_calendar_event(event_id: str) -> str:
    """Cancel a calendar event.
    
    Args:
        event_id: Calendar event ID
    
    Returns:
        Success or error message
    """
    log_tool_call("cancel_calendar_event", {"event_id": event_id})
    try:
        global _calendar_events
        original_count = len(_calendar_events)
        _calendar_events = [e for e in _calendar_events if e['id'] != event_id]
        
        if len(_calendar_events) < original_count:
            result = f"Booking {event_id} has been cancelled."
        else:
            result = f"Booking {event_id} not found."
        log_tool_call("cancel_calendar_event", {"event_id": event_id}, result)
        return result
    except Exception as e:
        result = f"Error cancelling booking: {str(e)}"
        log_tool_call("cancel_calendar_event", {"event_id": event_id}, result)
        return result


@tool
def list_upcoming_events(max_results: int = 10) -> str:
    """List upcoming calendar events.
    
    Args:
        max_results: Maximum number of events to return
    
    Returns:
        String listing upcoming events
    """
    log_tool_call("list_upcoming_events", {"max_results": max_results})
    try:
        now = datetime.now()
        upcoming = [
            e for e in _calendar_events
            if e['start'] >= now
        ]
        upcoming.sort(key=lambda x: x['start'])
        upcoming = upcoming[:max_results]
        
        if not upcoming:
            result = "No upcoming appointments."
        else:
            result = "Upcoming appointments:\n"
            for event in upcoming:
                start_str = event['start'].strftime('%Y-%m-%d %H:%M:%S')
                result += f"- {event.get('summary', 'No title')}: {start_str}\n"
        
        log_tool_call("list_upcoming_events", {"max_results": max_results}, result[:200])
        return result
    except Exception as e:
        result = f"Error fetching appointments: {str(e)}"
        log_tool_call("list_upcoming_events", {"max_results": max_results}, result)
        return result


# Export all tools
CALENDAR_TOOLS = [
    check_availability,
    create_calendar_event,
    cancel_calendar_event,
    list_upcoming_events,
]
