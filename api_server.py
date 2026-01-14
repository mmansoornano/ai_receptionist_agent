"""Agent API server using FastAPI."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from main import process_message

app = FastAPI(title="AI Receptionist Agent API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MessageRequest(BaseModel):
    message: str
    phone_number: str
    channel: str = "sms"
    language: str = "en"
    conversation_id: Optional[str] = None
    customer_id: Optional[str] = None


class MessageResponse(BaseModel):
    success: bool
    response: str
    error: Optional[str] = None


@app.post("/process", response_model=MessageResponse)
async def process_message_endpoint(request: MessageRequest):
    """Process a message through the agent."""
    try:
        response = process_message(
            message=request.message,
            phone_number=request.phone_number,
            channel=request.channel,
            language=request.language,
            conversation_id=request.conversation_id,
            customer_id=request.customer_id
        )
        return MessageResponse(success=True, response=response)
    except Exception as e:
        return MessageResponse(
            success=False,
            response="",
            error=str(e)
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Port can be configured via environment variable for microservices
    port = int(os.getenv('AGENT_API_PORT', '8001'))
    host = os.getenv('AGENT_API_HOST', '0.0.0.0')
    
    uvicorn.run(app, host=host, port=port)
