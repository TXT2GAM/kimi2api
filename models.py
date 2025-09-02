from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(BaseModel):
    role: MessageRole
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None

class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str

class StreamChoice(BaseModel):
    index: int
    delta: Dict[str, Any]
    finish_reason: Optional[str] = None

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: Usage

class ChatCompletionStreamResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[StreamChoice]

class KimiStreamEvent(BaseModel):
    event: str
    text: Optional[str] = None
    id: Optional[str] = None
    msg: Optional[Dict[str, Any]] = None