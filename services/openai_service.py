"""OpenAI service for LLM and voice processing."""
import os
from typing import List, Optional
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from config import OPENAI_API_KEY, OPENAI_MODEL


class OpenAIService:
    """Service for OpenAI API interactions."""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.llm = ChatOpenAI(
            model=OPENAI_MODEL,
            temperature=0.7,
            api_key=OPENAI_API_KEY,
        )
    
    def transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribe audio to text using Whisper."""
        with open(audio_file_path, "rb") as audio_file:
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"  # English
            )
        return transcript.text
    
    def generate_response(
        self,
        messages: List[BaseMessage],
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate response using GPT-4."""
        if system_prompt:
            # Add system message if provided
            from langchain_core.messages import SystemMessage
            messages = [SystemMessage(content=system_prompt)] + messages
        
        response = self.llm.invoke(messages)
        return response.content
    
    def get_llm(self) -> ChatOpenAI:
        """Get the LLM instance."""
        return self.llm
