"""
FastAPI backend that coordinates DeepSeek with our MCP server
Handles the chat API and streaming responses
"""

import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

# load env vars first thing
from dotenv import load_dotenv
load_dotenv()

# MCP and AI stuff
from fastmcp import Client as MCPClient
from openai import AsyncOpenAI
import instructor

from models import (
    ChatRequest, ChatResponse, StreamChunk, HealthResponse, 
    ToolListResponse, ErrorResponse, QueryAnalysis, ToolCall, 
    ToolResult, ResponseValidation
)

# basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("partselect_orchestrator")

# global vars - not ideal but works for now
mcp_client: Optional[MCPClient] = None
deepseek_client: Optional[AsyncOpenAI] = None
instructor_client: Optional[AsyncOpenAI] = None
conversation_history: Dict[str, List[Dict[str, Any]]] = {}

# config stuff
MCP_SERVER_PATH = os.path.join(os.path.dirname(__file__), "..", "mcp_servers", "partselect_server.py")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MAX_CONVERSATION_LENGTH = 20  # don't keep too much history

# prompts for the AI
SYSTEM_PROMPT = """You're a PartSelect assistant for refrigerator and dishwasher parts.

What you do:
- Help find the right parts for appliances
- Give installation tips and troubleshooting help  
- Check if parts work with specific models
- ONLY talk about refrigerator and dishwasher parts

Rules:
- Use the tools to search for parts and get real info
- Always check compatibility when people ask about models
- Give helpful responses with part numbers, prices, links
- If not sure about compatibility, tell them to check the website
- Keep it helpful but not too long

Only refrigerators and dishwashers, nothing else."""

QUERY_ANALYSIS_PROMPT = """Figure out what this user is asking:
1. Is it about refrigerator or dishwasher parts?
2. Do we need to search our database?
3. What tools should we use?

Query: {query}

Think about the conversation so far too."""

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic for the FastAPI app"""
    # Startup
    logger.info("Starting PartSelect FastAPI Orchestrator...")
    
    try:
        await initialize_clients()
        logger.info("All clients initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down PartSelect FastAPI Orchestrator...")
    await cleanup_clients()

# Create FastAPI app
app = FastAPI(
    title="PartSelect Chat API",
    description="AI-powered chat API for PartSelect appliance parts assistance",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def initialize_clients():
    """Initialize MCP client and AI clients"""
    global mcp_client, deepseek_client, instructor_client
    
    # Initialize MCP client
    try:
        mcp_client = MCPClient(MCP_SERVER_PATH)
        logger.info(f"MCP client initialized with server: {MCP_SERVER_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize MCP client: {e}")
        raise
    
    # Initialize DeepSeek client
    if DEEPSEEK_API_KEY:
        deepseek_client = AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )
        logger.info("DeepSeek client initialized")
    else:
        logger.warning("DEEPSEEK_API_KEY not found - using OpenAI instead")
        if OPENAI_API_KEY:
            deepseek_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        else:
            raise ValueError("Neither DEEPSEEK_API_KEY nor OPENAI_API_KEY found")
    
    # Initialize instructor client for structured outputs
    if OPENAI_API_KEY:
        base_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        instructor_client = instructor.apatch(base_client)
        logger.info("Instructor client initialized")
    else:
        logger.warning("OPENAI_API_KEY not found - structured prompts disabled")

async def cleanup_clients():
    """Cleanup clients on shutdown"""
    global mcp_client
    if mcp_client:
        # MCP client cleanup is handled by context manager
        pass

def get_conversation_id(request_id: Optional[str] = None) -> str:
    """Get or create conversation ID"""
    if request_id and request_id in conversation_history:
        return request_id
    
    new_id = str(uuid.uuid4())
    conversation_history[new_id] = []
    return new_id

def add_to_conversation(conversation_id: str, role: str, content: str, tools_used: Optional[List[str]] = None):
    """Add message to conversation history"""
    if conversation_id not in conversation_history:
        conversation_history[conversation_id] = []
    
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "tools_used": tools_used or []
    }
    
    conversation_history[conversation_id].append(message)
    
    # Trim conversation if too long
    if len(conversation_history[conversation_id]) > MAX_CONVERSATION_LENGTH:
        conversation_history[conversation_id] = conversation_history[conversation_id][-MAX_CONVERSATION_LENGTH:]

async def analyze_query(query: str, conversation_id: str) -> QueryAnalysis:
    """Analyze query to determine scope and retrieval needs"""
    if not instructor_client:
        # Fallback analysis
        return QueryAnalysis(
            is_in_scope=True,  # Assume in scope
            needs_retrieval=True,  # Assume needs retrieval
            confidence=0.8,
            reasoning="Fallback analysis - instructor client not available",
            suggested_tools=["search_parts"]
        )
    
    try:
        # Get conversation context
        context = ""
        if conversation_id in conversation_history:
            recent_messages = conversation_history[conversation_id][-5:]  # Last 5 messages
            context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])
        
        prompt = QUERY_ANALYSIS_PROMPT.format(query=query)
        if context:
            prompt += f"\n\nRecent conversation context:\n{context}"
        
        result = await instructor_client.chat.completions.create(
            model="gpt-4o-mini",
            response_format=QueryAnalysis,
            messages=[
                {"role": "system", "content": "You are a query analyzer for a PartSelect parts assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Query analysis failed: {e}")
        # Fallback
        return QueryAnalysis(
            is_in_scope=True,
            needs_retrieval=True,
            confidence=0.5,
            reasoning=f"Analysis failed: {str(e)}",
            suggested_tools=["search_parts", "semantic_search_parts"]
        )

async def execute_tools(suggested_tools: List[str], query: str) -> List[ToolResult]:
    """Execute suggested MCP tools"""
    if not mcp_client:
        raise HTTPException(status_code=500, detail="MCP client not initialized")
    
    results = []
    
    async with mcp_client:
        # Get available tools
        available_tools = await mcp_client.list_tools()
        tool_names = [tool.name for tool in available_tools]
        
        for tool_name in suggested_tools:
            if tool_name not in tool_names:
                logger.warning(f"Tool {tool_name} not available")
                continue
            
            start_time = time.time()
            try:
                # Determine arguments based on tool
                if tool_name in ["search_parts", "semantic_search_parts"]:
                    args = {"query": query, "limit": 10}
                elif tool_name == "smart_part_search":
                    args = {"query": query, "use_semantic": True, "limit": 10}
                elif tool_name == "get_server_status":
                    args = {}
                else:
                    # For other tools, try with just query
                    args = {"query": query}
                
                result = await mcp_client.call_tool(tool_name, args)
                execution_time = time.time() - start_time
                
                tool_result = ToolResult(
                    tool_name=tool_name,
                    arguments=args,
                    result=result.content[0].text if result.content else "No result",
                    execution_time=execution_time,
                    success=True
                )
                
                results.append(tool_result)
                logger.info(f"Tool {tool_name} executed successfully in {execution_time:.2f}s")
                
            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = str(e)
                
                tool_result = ToolResult(
                    tool_name=tool_name,
                    arguments=args,
                    result=None,
                    execution_time=execution_time,
                    success=False,
                    error=error_msg
                )
                
                results.append(tool_result)
                logger.error(f"Tool {tool_name} failed: {error_msg}")
    
    return results

async def generate_response(query: str, tool_results: List[ToolResult], conversation_id: str) -> str:
    """Generate natural language response using DeepSeek"""
    if not deepseek_client:
        raise HTTPException(status_code=500, detail="DeepSeek client not initialized")
    
    # Prepare context from tool results
    context_parts = []
    for result in tool_results:
        if result.success:
            context_parts.append(f"Tool: {result.tool_name}\nResult: {result.result}\n")
        else:
            context_parts.append(f"Tool: {result.tool_name}\nError: {result.error}\n")
    
    context = "\n".join(context_parts) if context_parts else "No data retrieved"
    
    # Get conversation history
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    if conversation_id in conversation_history:
        for msg in conversation_history[conversation_id][-10:]:  # Last 10 messages
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
    
    # Add current query and context
    user_message = f"User query: {query}\n\nRetrieved data: {context}"
    messages.append({"role": "user", "content": user_message})
    
    try:
        response = await deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        return f"I apologize, but I encountered an error processing your request: {str(e)}"

async def stream_response(query: str, conversation_id: str) -> AsyncGenerator[str, None]:
    """Generate streaming response"""
    start_time = time.time()
    
    try:
        # Step 1: Analyze query
        yield f"data: {json.dumps({'type': 'chunk', 'content': 'Analyzing your query...', 'conversation_id': conversation_id})}\n\n"
        
        analysis = await analyze_query(query, conversation_id)
        
        if not analysis.is_in_scope:
            response = "I apologize, but I can only assist with questions about refrigerator and dishwasher parts and repairs. Could you please ask about appliance parts instead?"
            add_to_conversation(conversation_id, "user", query)
            add_to_conversation(conversation_id, "assistant", response)
            
            yield f"data: {json.dumps({'type': 'complete', 'content': response, 'conversation_id': conversation_id, 'tools_used': []})}\n\n"
            return
        
        # Step 2: Execute tools if needed
        tools_used = []
        tool_results = []
        
        if analysis.needs_retrieval and analysis.suggested_tools:
            yield f"data: {json.dumps({'type': 'chunk', 'content': 'Searching our parts database...', 'conversation_id': conversation_id})}\n\n"
            
            tool_results = await execute_tools(analysis.suggested_tools, query)
            tools_used = [result.tool_name for result in tool_results if result.success]
        
        # Step 3: Generate response
        yield f"data: {json.dumps({'type': 'chunk', 'content': 'Generating response...', 'conversation_id': conversation_id})}\n\n"
        
        response = await generate_response(query, tool_results, conversation_id)
        
        # Add to conversation history
        add_to_conversation(conversation_id, "user", query)
        add_to_conversation(conversation_id, "assistant", response, tools_used)
        
        response_time = time.time() - start_time
        
        # Send final response
        yield f"data: {json.dumps({'type': 'complete', 'content': response, 'conversation_id': conversation_id, 'tools_used': tools_used, 'response_time': response_time})}\n\n"
        
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        error_response = f"I apologize, but I encountered an error: {str(e)}"
        yield f"data: {json.dumps({'type': 'error', 'error': error_response, 'conversation_id': conversation_id})}\n\n"

# API Endpoints

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint - supports both streaming and non-streaming"""
    conversation_id = get_conversation_id(request.conversation_id)
    
    if request.stream:
        # Return streaming response
        return StreamingResponse(
            stream_response(request.query, conversation_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Conversation-ID": conversation_id
            }
        )
    else:
        # Return single response
        start_time = time.time()
        
        # Analyze query
        analysis = await analyze_query(request.query, conversation_id)
        
        if not analysis.is_in_scope:
            response = "I apologize, but I can only assist with questions about refrigerator and dishwasher parts and repairs."
            add_to_conversation(conversation_id, "user", request.query)
            add_to_conversation(conversation_id, "assistant", response)
            
            return ChatResponse(
                response=response,
                conversation_id=conversation_id,
                response_time=time.time() - start_time,
                tools_used=[]
            )
        
        # Execute tools
        tools_used = []
        tool_results = []
        
        if analysis.needs_retrieval and analysis.suggested_tools:
            tool_results = await execute_tools(analysis.suggested_tools, request.query)
            tools_used = [result.tool_name for result in tool_results if result.success]
        
        # Generate response
        response = await generate_response(request.query, tool_results, conversation_id)
        
        # Add to conversation
        add_to_conversation(conversation_id, "user", request.query)
        add_to_conversation(conversation_id, "assistant", response, tools_used)
        
        return ChatResponse(
            response=response,
            conversation_id=conversation_id,
            response_time=time.time() - start_time,
            tools_used=tools_used
        )

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    components = {}
    status = "healthy"
    
    # Check MCP server
    try:
        if mcp_client:
            async with mcp_client:
                tools = await mcp_client.list_tools()
                components["mcp_server"] = {
                    "status": "healthy",
                    "tools_count": len(tools)
                }
        else:
            components["mcp_server"] = {"status": "not_initialized"}
            status = "degraded"
    except Exception as e:
        components["mcp_server"] = {"status": "error", "error": str(e)}
        status = "unhealthy"
    
    # Check AI clients
    components["deepseek_client"] = {
        "status": "healthy" if deepseek_client else "not_initialized"
    }
    components["instructor_client"] = {
        "status": "healthy" if instructor_client else "not_initialized"
    }
    
    return HealthResponse(
        status=status,
        components=components
    )

@app.get("/api/tools", response_model=ToolListResponse)
async def list_tools():
    """List available MCP tools"""
    if not mcp_client:
        raise HTTPException(status_code=500, detail="MCP client not initialized")
    
    try:
        async with mcp_client:
            tools = await mcp_client.list_tools()
            
            tool_list = []
            for tool in tools:
                tool_info = {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                tool_list.append(tool_info)
            
            return ToolListResponse(
                tools=tool_list,
                server_status="connected",
                total_tools=len(tool_list)
            )
            
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")

@app.post("/api/reset")
async def reset_conversation(conversation_id: Optional[str] = None):
    """Reset conversation history"""
    if conversation_id and conversation_id in conversation_history:
        del conversation_history[conversation_id]
    
    new_id = get_conversation_id()
    
    return {
        "conversation_id": new_id,
        "message": "Conversation reset successfully"
    }

# Error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return ErrorResponse(
        error="Invalid request format",
        details={"validation_errors": exc.errors()}
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return ErrorResponse(
        error=exc.detail,
        error_code=str(exc.status_code)
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return ErrorResponse(
        error="Internal server error",
        details={"exception": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting PartSelect FastAPI Orchestrator...")
    uvicorn.run(
        "orchestrator:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
