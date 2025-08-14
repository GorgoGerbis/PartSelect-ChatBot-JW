"""
Models for the chat API stuff
Pretty standard pydantic models, nothing fancy
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime

class ChatRequest(BaseModel):
    # basic chat request - kept it simple
    query: str = Field(..., min_length=1, max_length=1000)
    conversation_id: Optional[str] = None  # for keeping track of conversations
    stream: bool = True  # default to streaming because it feels faster

class ChatResponse(BaseModel):
    # what we send back to the frontend
    response: str
    conversation_id: str
    response_time: float  # for debugging performance issues
    tools_used: List[str] = []
    metadata: Dict[str, Any] = {}

class StreamChunk(BaseModel):
    # streaming response chunks - had to add this for the real-time updates
    type: Literal["chunk", "complete", "error"]
    content: Optional[str] = None
    conversation_id: Optional[str] = None
    tools_used: Optional[List[str]] = None  # only set on complete
    error: Optional[str] = None

class HealthResponse(BaseModel):
    # health check stuff - probably overkill but whatever
    status: Literal["healthy", "degraded", "unhealthy"]
    timestamp: datetime = Field(default_factory=datetime.now)
    components: Dict[str, Dict[str, Any]] = {}
    version: str = "1.0.0"

class ToolListResponse(BaseModel):
    # for listing what MCP tools we have available
    tools: List[Dict[str, Any]]
    server_status: str
    total_tools: int

class ConversationHistoryRequest(BaseModel):
    conversation_id: str
    limit: Optional[int] = 50  # don't want to return too much at once

class ConversationMessage(BaseModel):
    # individual message in a conversation
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
    tools_used: Optional[List[str]] = None

class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: List[ConversationMessage]
    total_messages: int

class ResetConversationRequest(BaseModel):
    conversation_id: Optional[str] = None  # if None, creates new conversation

class ResetConversationResponse(BaseModel):
    conversation_id: str
    message: str

class ErrorResponse(BaseModel):
    # standard error format
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)

# internal models for query processing
class QueryAnalysis(BaseModel):
    # figure out if the user is asking about appliance parts
    is_in_scope: bool
    needs_retrieval: bool  # do we need to search for parts data
    confidence: float  # how sure are we about this analysis
    reasoning: str
    suggested_tools: List[str] = []

class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}
    
class ToolResult(BaseModel):
    # what we get back from MCP tools
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    execution_time: float
    success: bool
    error: Optional[str] = None

class ResponseValidation(BaseModel):
    # check if our response is good before sending it
    is_appropriate: bool
    stays_in_scope: bool  # did we stick to appliance parts
    has_hallucination: bool = False
    confidence: float
    feedback: Optional[str] = None
    issues: List[str] = []
