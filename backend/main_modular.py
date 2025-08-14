# TODO: Redis caching?
# FIXME: Error handling could be better in some places

# Usage: python main_modular.py
# Set APP_MODE in .env file (simple/vector/advanced)

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from app_factory import AppFactory
from providers.interfaces import PartSelectApp
from services.conversation_cache import conversation_cache
from services.customer_service_optimizer import customer_service_optimizer
from services.fast_lookup_service import fast_lookup_service
from services.conversation_context_manager import conversation_context_manager

# Simple in-memory session storage (replace with Redis in production)
session_conversations = {}

# Load environment variables
load_dotenv()

# Logging setup - kept it simple for now
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("partselect_app")  # might rename this later

# Global app instance - yeah I know globals aren't ideal but it works
partselect_app: Optional[PartSelectApp] = None

# Request/Response models - added these as I went along
class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None  # for tracking conversations
    stream: bool = False  # might implement streaming later

class ChatResponse(BaseModel):
    response: str
    parts: Optional[List[Dict[str, Any]]] = None
    repairs: Optional[List[Dict[str, Any]]] = None  
    blogs: Optional[List[Dict[str, Any]]] = None    # added blogs after testing
    conversation_id: Optional[str] = None
    response_time: Optional[float] = None  # good for debugging
    app_mode: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    app_mode: str
    components: Dict[str, Any]
    timestamp: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("🚀 Starting PartSelect Modular Application")
    
    global partselect_app
    try:
        # Create app based on environment
        app_mode = os.getenv("APP_MODE", "simple")
        logger.info(f"Initializing in '{app_mode}' mode...")
        
        partselect_app = await AppFactory.create_app(app_mode)
        
        logger.info("✅ PartSelect application initialized successfully")
        logger.info(f"   Mode: {app_mode}")
        logger.info(f"   Available modes: {AppFactory.get_available_modes()}")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down PartSelect application...")

# Create FastAPI app
app = FastAPI(
    title="PartSelect Chat Agent",
    description="Modular AI-powered chat agent for appliance parts assistance",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple conversation tracking - probably should use Redis in production
conversation_history: Dict[str, List[Dict[str, str]]] = {}
# NOTE: This will reset when server restarts, but fine for demo

def get_conversation_id(request_id: Optional[str] = None) -> str:
    """Get or create conversation ID - keeps chats separate"""
    logger.info(f"🔍 get_conversation_id called with: {request_id}")
    logger.info(f"📚 Current conversation_history keys: {list(conversation_history.keys())}")
    
    # If request_id provided, use it directly (frontend manages the ID)
    if request_id:
        if request_id not in conversation_history:
            conversation_history[request_id] = []
            logger.info(f"🆕 Created new conversation: {request_id}")
        else:
            logger.info(f"✅ Found existing conversation: {request_id}")
        return request_id
    
    # Fallback: generate new ID if none provided
    import uuid
    new_id = str(uuid.uuid4())[:8]  # Short ID for demo - easier to debug
    conversation_history[new_id] = []
    logger.info(f"🆕 Created fallback conversation: {new_id}")
    return new_id

def add_to_conversation(conversation_id: str, role: str, content: str):
    """Add message to conversation history and update context"""
    if conversation_id not in conversation_history:
        conversation_history[conversation_id] = []
    
    # Extract and store any part numbers mentioned (legacy support)
    import re
    part_numbers = re.findall(r'\b(PS\d+|WP[A-Z]?\d+)\b', content.upper())
    
    conversation_history[conversation_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "part_numbers": part_numbers  # Track mentioned parts
    })
    
    # Update conversation context with the new message
    conversation_context_manager.update_context(conversation_id, content, role)
    
    # Keep only last 20 messages
    if len(conversation_history[conversation_id]) > 20:
        conversation_history[conversation_id] = conversation_history[conversation_id][-20:]

async def process_chat_request(query: str, conversation_id: str) -> Dict[str, Any]:
    """Process chat request using the pluggable providers"""
    if not partselect_app:
        raise HTTPException(status_code=500, detail="Application not initialized")
    
    start_time = time.time()
    
    try:
        # STEP 1: Check conversation cache first (ULTRA FAST - <100ms)
        cached_response = conversation_cache.get_cached_response(query, conversation_id)
        if cached_response:
            logger.info(f"CACHE HIT! Returning cached response in {(time.time() - start_time)*1000:.1f}ms")
            return {
                "response": cached_response.response,
                "parts": cached_response.parts,
                "repairs": cached_response.repairs,
                "blogs": cached_response.blogs,
                "response_time": time.time() - start_time,
                "source": "cache"
            }
        
        # Fast lookup for specific queries (LIGHTNING FAST - <100ms)
        fast_result = await fast_lookup_service.handle_fast_lookup(query)
        if fast_result:
            logger.info(f"⚡ FAST LOOKUP SUCCESS in {(time.time() - start_time)*1000:.1f}ms")
            return {
                "response": fast_result["response"],
                "parts": fast_result.get("parts", []),
                "repairs": fast_result.get("repairs", []),
                "blogs": fast_result.get("blogs", []),
                "response_time": time.time() - start_time,
                "source": "fast_lookup"
            }
        
        # STEP 2: Customer service optimizer for instant responses (FAST - <200ms)
        cs_response = customer_service_optimizer.analyze_query_fast(query)
        logger.info(f"🎯 Customer service optimizer confidence: {cs_response.confidence:.2f} (type: {cs_response.response_type})")
        
        # Only use optimizer for very high confidence generic questions AND only for first message in conversation
        conversation_history_length = len(conversation_history.get(conversation_id, []))
        is_first_message = conversation_history_length == 0
        
        if (cs_response.confidence > 0.9 and 
            is_first_message and  # Only use canned responses for first message
            not any(word in query.lower() for word in ['part', 'ps', 'model', 'whirlpool', 'ge', 'bosch'])):
            logger.info(f"HIGH CONFIDENCE customer service response ({cs_response.confidence:.2f})")
            
            # Cache this response for future use
            conversation_cache.cache_response(
                query=query,
                response=cs_response.immediate_response,
                parts=[],  # Will be enhanced by background search if needed
                repairs=[],
                blogs=[],
                confidence=cs_response.confidence,
                conversation_id=conversation_id
            )
            
            return {
                "response": cs_response.immediate_response,
                "parts": [],
                "repairs": [],
                "blogs": [],
                "response_time": time.time() - start_time,
                "source": "customer_service_optimizer",
                "confidence": cs_response.confidence,
                "response_type": cs_response.response_type
            }
        
        # STEP 3: Fallback to full search + LLM (slower but gets everything)
        logger.info("Using full search + LLM pipeline")
        
        # Analyze query to determine what to search for
        analysis = await partselect_app.llm_provider.analyze_query(query)
        logger.info(f"Query analysis: {analysis}")
        
        # Check if query is in scope
        if not analysis.get("is_in_scope", True):
            response = "I apologize, but I can only assist with questions about refrigerator and dishwasher parts and repairs. Could you please ask about appliance parts instead?"
            return {
                "response": response,
                "parts": [],
                "repairs": [],
                "response_time": time.time() - start_time,
                "source": "scope_check"
            }
        
        # Run searches in parallel for maximum speed
        parts = []
        repairs = []
        blogs = []
        
        if analysis.get("needs_search", True):
            # Run all searches in parallel - MUCH faster!
            search_tasks = []
            
            # Parts search
            if analysis.get("intent") in ["general", "purchase", "compatibility"] or analysis.get("part_numbers"):
                search_tasks.append(
                    partselect_app.search_provider.search_parts(
                        query, 
                        filters={"category": analysis["appliance_types"][0]} if analysis.get("appliance_types") and len(analysis["appliance_types"]) > 0 else None,
                        limit=5
                    )
                )
            else:
                search_tasks.append(None)
            
            # Repairs search
            if analysis.get("intent") in ["troubleshooting", "installation"] or any(word in query.lower() for word in ["broken", "not working", "install"]):
                search_tasks.append(
                    partselect_app.search_provider.search_repairs(
                        query,
                        appliance_type=analysis["appliance_types"][0] if analysis.get("appliance_types") and len(analysis["appliance_types"]) > 0 else None,
                        limit=3
                    )
                )
            else:
                search_tasks.append(None)
            
            # Blog search (always)
            search_tasks.append(partselect_app.search_provider.search_blogs(query, limit=2))
            
            # Execute all searches in parallel
            try:
                results = await asyncio.gather(*[task for task in search_tasks if task is not None], return_exceptions=True)
                
                # Process results
                result_idx = 0
                if search_tasks[0] is not None:  # Parts
                    if not isinstance(results[result_idx], Exception):
                        parts = [result.dict() for result in results[result_idx]]
                    result_idx += 1
                
                if search_tasks[1] is not None:  # Repairs  
                    if not isinstance(results[result_idx], Exception):
                        repairs = [result.dict() for result in results[result_idx]]
                    result_idx += 1
                
                if search_tasks[2] is not None:  # Blogs
                    if not isinstance(results[result_idx], Exception):
                        blogs = [result.dict() for result in results[result_idx]]
                        
            except Exception as e:
                logger.error(f"Parallel search error: {e}")
                # Fallback to empty results
        
        # Build detailed context for the LLM
        context_parts = []
        if parts:
            context_parts.append("=== RELEVANT PARTS FOUND ===")
            for i, part in enumerate(parts[:5], 1):
                context_parts.append(f"Part {i}: {part.get('name', 'Unknown Part')}")
                context_parts.append(f"  Part Number: {part.get('part_number', 'N/A')}")
                context_parts.append(f"  Price: {part.get('price', 'N/A')}")
                context_parts.append(f"  Brand: {part.get('brand', 'N/A')}")
                if part.get('symptoms'):
                    context_parts.append(f"  Fixes: {part.get('symptoms')}")
                if part.get('install_difficulty'):
                    context_parts.append(f"  Installation: {part.get('install_difficulty')} ({part.get('install_time', 'Unknown time')})")
                if part.get('url'):
                    context_parts.append(f"  Product URL: {part.get('url')}")
                context_parts.append("")  # blank line
        
        if repairs:
            context_parts.append("=== REPAIR GUIDES FOUND ===")
            for i, repair in enumerate(repairs[:3], 1):
                context_parts.append(f"Repair {i}: {repair.get('title', 'Unknown Repair')}")
                context_parts.append(f"  Description: {repair.get('description', 'N/A')}")
                context_parts.append(f"  Difficulty: {repair.get('difficulty', 'N/A')}")
                if repair.get('symptom_detail_url'):
                    context_parts.append(f"  Guide URL: {repair.get('symptom_detail_url')}")
                context_parts.append("")  # blank line
        
        if blogs:
            context_parts.append("=== RELATED ARTICLES ===")
            for i, blog in enumerate(blogs[:3], 1):
                context_parts.append(f"Article {i}: {blog.get('title', 'Unknown Article')}")
                if blog.get('url'):
                    context_parts.append(f"  URL: {blog.get('url')}")
                context_parts.append("")  # blank line
        
        context = "\n".join(context_parts) if context_parts else "No specific parts, repair guides, or articles found in the database."
        
        # NEW: Add intelligent conversation context
        structured_context = conversation_context_manager.get_structured_context_for_llm(conversation_id)
        if structured_context and structured_context != "No conversation context available.":
            context = structured_context + "\n\n" + context
            logger.info(f"🧠 Context for {conversation_id}: {structured_context[:200]}...")
        
        # Get conversation history
        history = conversation_history.get(conversation_id, [])
        
        # Generate AI response with quality validation loop
        max_attempts = 3  # Multiple attempts for better quality
        response = None
        
        for attempt in range(max_attempts):
            try:
                # Generate response
                response = await partselect_app.llm_provider.generate_response(
                    query, 
                    context, 
                    conversation_history=history
                )
                
                # Validate response quality and accuracy
                validation = await partselect_app.llm_provider.validate_response(
                    query, response, context
                )
                
                # Check if response passes validation
                if (validation.get("is_appropriate", True) and 
                    validation.get("stays_in_scope", True) and 
                    not validation.get("hallucination", False)):
                    logger.info(f"✅ Response validation passed on attempt {attempt + 1}")
                    break
                
                # If we have specific feedback, try to improve
                feedback = validation.get("feedback")
                if feedback and attempt < max_attempts - 1:
                    logger.info(f"🔄 Response validation failed, retrying with feedback: {feedback}")
                    # Add feedback to context for next attempt - this actually works pretty well
                    context += f"\n\nIMPROVEMENT NEEDED: {feedback}"
                else:
                    logger.warning(f"⚠️ Response validation failed on attempt {attempt + 1}, using anyway")
                    break
                    
            except Exception as e:
                logger.error(f"Response generation attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:
                    response = "I apologize, but I'm having trouble processing your request right now. Please try rephrasing your question."
        
        # Cache this response for future use
        conversation_cache.cache_response(
            query=query,
            response=response,
            parts=parts,
            repairs=repairs,
            blogs=blogs,
            confidence=0.9,  # High confidence for full search results
            conversation_id=conversation_id
        )
        
        return {
            "response": response,
            "parts": parts,
            "repairs": repairs,
            "blogs": blogs,
            "response_time": time.time() - start_time,
            "source": "full_search_llm"
        }
        
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        return {
            "response": f"I apologize, but I encountered an error processing your request. Please try again.",
            "parts": [],
            "repairs": [],
            "response_time": time.time() - start_time
        }

async def stream_chat_response(query: str, conversation_id: str):
    """Progressive streaming - send each piece as it becomes available"""
    start_time = time.time()
    
    try:
        # Add user message to conversation history FIRST
        add_to_conversation(conversation_id, "user", query)
        logger.info(f"💬 Added user message to conversation {conversation_id}. History length: {len(conversation_history.get(conversation_id, []))}")
        
        # STEP 1: Send immediate acknowledgment
        yield f"data: {json.dumps({'type': 'thinking', 'content': 'Processing your request...', 'conversation_id': conversation_id})}\n\n"
        
        # STEP 2: Check cache first (ULTRA FAST)
        cached_response = conversation_cache.get_cached_response(query, conversation_id)
        if cached_response:
            yield f"data: {json.dumps({'type': 'response', 'content': cached_response.response, 'conversation_id': conversation_id, 'source': 'cache'})}\n\n"
            
            # Stream cached parts/repairs/blogs if available
            if cached_response.parts:
                yield f"data: {json.dumps({'type': 'parts', 'content': cached_response.parts, 'conversation_id': conversation_id})}\n\n"
            if cached_response.repairs:
                yield f"data: {json.dumps({'type': 'repairs', 'content': cached_response.repairs, 'conversation_id': conversation_id})}\n\n"
            if cached_response.blogs:
                yield f"data: {json.dumps({'type': 'blogs', 'content': cached_response.blogs, 'conversation_id': conversation_id})}\n\n"
                
            yield f"data: {json.dumps({'type': 'complete', 'response_time': time.time() - start_time, 'conversation_id': conversation_id})}\n\n"
            return
        
        # STEP 3: Fast lookup service (LIGHTNING FAST for specific queries)
        yield f"data: {json.dumps({'type': 'thinking', 'content': 'Checking for direct database lookup...', 'conversation_id': conversation_id})}\n\n"
        
        fast_result = await fast_lookup_service.handle_fast_lookup(query)
        if fast_result:
            logger.info(f"⚡ Fast lookup SUCCESS for: {query}")
            yield f"data: {json.dumps({'type': 'response', 'content': fast_result['response'], 'conversation_id': conversation_id, 'source': 'fast_lookup'})}\n\n"
            
            # Stream parts if available
            if fast_result.get('parts'):
                yield f"data: {json.dumps({'type': 'parts', 'content': fast_result['parts'], 'conversation_id': conversation_id})}\n\n"
            
            yield f"data: {json.dumps({'type': 'complete', 'response_time': time.time() - start_time, 'conversation_id': conversation_id})}\n\n"
            return
        
        # STEP 4: Customer service optimizer (FAST fallback)
        cs_response = customer_service_optimizer.analyze_query_fast(query)
        if cs_response.confidence > 0.7:
            yield f"data: {json.dumps({'type': 'response', 'content': cs_response.immediate_response, 'conversation_id': conversation_id, 'source': 'optimizer'})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'response_time': time.time() - start_time, 'conversation_id': conversation_id})}\n\n"
            return
        
        # STEP 4: Full pipeline with progressive streaming
        yield f"data: {json.dumps({'type': 'thinking', 'content': 'Analyzing your query...', 'conversation_id': conversation_id})}\n\n"
        
        # Analyze query
        analysis = await partselect_app.llm_provider.analyze_query(query)
        
        if not analysis.get("is_in_scope", True):
            response = "I apologize, but I can only assist with questions about refrigerator and dishwasher parts and repairs. Could you please ask about appliance parts instead?"
            yield f"data: {json.dumps({'type': 'response', 'content': response, 'conversation_id': conversation_id})}\n\n"
            yield f"data: {json.dumps({'type': 'complete', 'response_time': time.time() - start_time, 'conversation_id': conversation_id})}\n\n"
            return
        
        # Start searches and AI response in parallel
        yield f"data: {json.dumps({'type': 'thinking', 'content': 'Searching for relevant information...', 'conversation_id': conversation_id})}\n\n"
        
        # Get conversation history
        history = conversation_history.get(conversation_id, [])
        
        # Start searches first to get better context for AI
        search_results = {"parts": [], "repairs": [], "blogs": []}
        
        # Start searches in parallel
        search_tasks = []
        if analysis.get("needs_search", True):
            if analysis.get("intent") in ["general", "purchase", "compatibility"] or analysis.get("part_numbers"):
                search_tasks.append(("parts", partselect_app.search_provider.search_parts(query, limit=5)))
            if analysis.get("intent") in ["troubleshooting", "installation"] or any(word in query.lower() for word in ["broken", "not working", "install"]):
                search_tasks.append(("repairs", partselect_app.search_provider.search_repairs(query, limit=3)))
            search_tasks.append(("blogs", partselect_app.search_provider.search_blogs(query, limit=2)))
        
        # Execute searches and collect results for AI context
        search_results = {"parts": [], "repairs": [], "blogs": []}
        
        # Execute searches and stream results as they complete
        if search_tasks:
            for search_type, task in search_tasks:
                try:
                    results = await task
                    if results:
                        search_results[search_type] = results
                        result_data = [result.dict() for result in results]
                        yield f"data: {json.dumps({'type': search_type, 'content': result_data, 'conversation_id': conversation_id})}\n\n"
                except Exception as e:
                    logger.error(f"{search_type} search error: {e}")
        
        # Now generate AI response with STREAMING VALIDATION LOOP
        yield f"data: {json.dumps({'type': 'thinking', 'content': 'Generating response with quality validation...', 'conversation_id': conversation_id})}\n\n"
        
        # Build context from search results (same as main function)
        context_parts = []
        
        if search_results.get("parts"):
            parts_context = "**PARTS FOUND:**\n"
            for part in search_results["parts"]:
                parts_context += f"- **{part.name}** (Part #{part.part_number})\n"
                parts_context += f"  - Brand: {part.brand}, Price: {part.price}\n"
                if part.symptoms:
                    parts_context += f"  - Symptoms: {part.symptoms}\n"
                parts_context += f"  - Installation: {part.install_difficulty} ({part.install_time})\n\n"
            context_parts.append(parts_context)
        
        if search_results.get("repairs"):
            repairs_context = "**REPAIR GUIDES:**\n"
            for repair in search_results["repairs"]:
                repairs_context += f"- **{repair.title}** (Difficulty: {repair.difficulty})\n"
                repairs_context += f"  - {repair.description}\n\n"
            context_parts.append(repairs_context)
        
        if search_results.get("blogs"):
            blogs_context = "**HELPFUL ARTICLES:**\n"
            for blog in search_results["blogs"]:
                blogs_context += f"- [{blog.title}]({blog.url})\n"
            context_parts.append(blogs_context)
        
        context = "\n".join(context_parts) if context_parts else "No specific parts, repair guides, or articles found in the database."
        
        # NEW: Add intelligent conversation context for streaming too
        structured_context = conversation_context_manager.get_structured_context_for_llm(conversation_id)
        if structured_context and structured_context != "No conversation context available.":
            context = structured_context + "\n\n" + context
        
        # STREAMING VALIDATION LOOP - Show the validation process in real-time!
        max_attempts = 3
        response = None
        
        for attempt in range(max_attempts):
            try:
                yield f"data: {json.dumps({'type': 'thinking', 'content': f'🤖 Generating response (attempt {attempt + 1}/{max_attempts})...', 'conversation_id': conversation_id})}\n\n"
                
                # Generate response
                response = await partselect_app.llm_provider.generate_response(
                    query, 
                    context, 
                    conversation_history=history
                )
                
                # Stream validation process
                yield f"data: {json.dumps({'type': 'thinking', 'content': '🔍 Validating response quality...', 'conversation_id': conversation_id})}\n\n"
                
                validation = await partselect_app.llm_provider.validate_response(
                    query, response, context
                )
                
                # Check if response passes validation and stream the result
                if (validation.get("is_appropriate", True) and 
                    validation.get("stays_in_scope", True) and 
                    not validation.get("hallucination", False)):
                    yield f"data: {json.dumps({'type': 'thinking', 'content': f'✅ Response validation PASSED on attempt {attempt + 1}!', 'conversation_id': conversation_id})}\n\n"
                    break
                
                # If we have specific feedback, show it and try to improve
                feedback = validation.get("feedback")
                if feedback and attempt < max_attempts - 1:
                    yield f"data: {json.dumps({'type': 'thinking', 'content': f'⚠️ Validation failed: {feedback[:100]}... Retrying with improvements...', 'conversation_id': conversation_id})}\n\n"
                    # Add feedback to context for next attempt - this actually works pretty well
                    context += f"\n\nIMPROVEMENT NEEDED: {feedback}"
                else:
                    yield f"data: {json.dumps({'type': 'thinking', 'content': f'⚠️ Using response despite validation issues (attempt {attempt + 1})', 'conversation_id': conversation_id})}\n\n"
                    break
                    
            except Exception as e:
                logger.error(f"Response generation attempt {attempt + 1} failed: {e}")
                if attempt == max_attempts - 1:
                    response = "I apologize, but I'm having trouble processing your request right now. Please try rephrasing your question."
        
        # Stream the final validated response
        yield f"data: {json.dumps({'type': 'response', 'content': response, 'conversation_id': conversation_id, 'source': 'validated_ai'})}\n\n"
        
        # Add assistant response to conversation history
        add_to_conversation(conversation_id, "assistant", response)
        logger.info(f"🤖 Added assistant response to conversation {conversation_id}. History length: {len(conversation_history.get(conversation_id, []))}")
        
        # Final completion with timing
        yield f"data: {json.dumps({'type': 'complete', 'response_time': time.time() - start_time, 'conversation_id': conversation_id})}\n\n"
        
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e), 'conversation_id': conversation_id})}\n\n"

@app.get("/")
async def root():
    """Root endpoint with system info"""
    app_mode = os.getenv("APP_MODE", "simple")
    available_modes = AppFactory.get_available_modes()
    
    return {
        "message": "PartSelect Chat Agent API",
        "version": "2.0.0 (Modular)",
        "app_mode": app_mode,
        "available_modes": available_modes,
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint with progressive streaming"""
    logger.info(f"📨 Chat request received - Query: '{request.query[:50]}...' ConvID: {request.conversation_id}")
    conversation_id = get_conversation_id(request.conversation_id)
    
    # If streaming requested, use streaming response
    if request.stream:
        return StreamingResponse(
            stream_chat_response(request.query, conversation_id),
            media_type="text/plain"
        )
    
    try:
        # Process the request (non-streaming)
        result = await process_chat_request(request.query, conversation_id)
        
        # Add to conversation history
        add_to_conversation(conversation_id, "user", request.query)
        add_to_conversation(conversation_id, "assistant", result["response"])
        
        # Return response
        return ChatResponse(
            response=result["response"],
            parts=result.get("parts"),
            repairs=result.get("repairs"),
            blogs=result.get("blogs"),
            conversation_id=conversation_id,
            response_time=result.get("response_time"),
            app_mode=os.getenv("APP_MODE", "simple")
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/conversation/{conversation_id}")
async def debug_conversation(conversation_id: str):
    """Debug endpoint to check conversation history"""
    history = conversation_history.get(conversation_id, [])
    return {
        "conversation_id": conversation_id,
        "message_count": len(history),
        "messages": history[-5:] if history else []  # Last 5 messages
    }

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    app_mode = os.getenv("APP_MODE", "simple")
    
    components = {
        "app_mode": app_mode,
        "available_modes": AppFactory.get_available_modes()
    }
    
    if partselect_app:
        try:
            # Get stats from all providers
            components["data_provider"] = partselect_app.data_provider.get_stats()
            components["search_provider"] = partselect_app.search_provider.get_stats()
            components["llm_provider"] = partselect_app.llm_provider.get_stats()
            components["initialized"] = partselect_app.initialized
            status = "healthy"
        except Exception as e:
            components["error"] = str(e)
            status = "degraded"
    else:
        components["error"] = "Application not initialized"
        status = "unhealthy"
    
    return HealthResponse(
        status=status,
        app_mode=app_mode,
        components=components,
        timestamp=datetime.now().isoformat()
    )

@app.post("/api/cache/clear")
async def clear_cache():
    """Clear conversation cache - useful for testing new prompts"""
    conversation_cache.clear_cache()
    return {"status": "cache cleared", "timestamp": datetime.now().isoformat()}

@app.get("/api/cache/stats")
async def cache_stats():
    """Get cache performance statistics"""
    try:
        cache_stats = conversation_cache.get_stats()
        optimizer_stats = customer_service_optimizer.get_stats()
        
        return {
            "cache_performance": cache_stats,
            "optimizer_performance": optimizer_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {"error": str(e)}

@app.post("/api/search/parts")
async def search_parts_endpoint(request: Dict[str, Any]):
    """Direct parts search endpoint"""
    if not partselect_app:
        raise HTTPException(status_code=500, detail="Application not initialized")
    
    query = request.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    try:
        results = await partselect_app.search_provider.search_parts(
            query,
            filters=request.get("filters"),
            limit=request.get("limit", 10)
        )
        return {"results": [result.dict() for result in results]}
    except Exception as e:
        logger.error(f"Parts search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search/repairs")
async def search_repairs_endpoint(request: Dict[str, Any]):
    """Direct repairs search endpoint"""
    if not partselect_app:
        raise HTTPException(status_code=500, detail="Application not initialized")
    
    query = request.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    try:
        results = await partselect_app.search_provider.search_repairs(
            query,
            appliance_type=request.get("appliance_type"),
            limit=request.get("limit", 5)
        )
        return {"results": [result.dict() for result in results]}
    except Exception as e:
        logger.error(f"Repairs search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/part/{part_id}")
async def get_part_details_endpoint(part_id: str):
    """Get detailed part information"""
    if not partselect_app:
        raise HTTPException(status_code=500, detail="Application not initialized")
    
    try:
        result = await partselect_app.search_provider.get_part_details(part_id)
        if result:
            return result.dict()
        else:
            raise HTTPException(status_code=404, detail="Part not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Part details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/compatibility")
async def check_compatibility_endpoint(request: Dict[str, str]):
    """Check part compatibility with model"""
    if not partselect_app:
        raise HTTPException(status_code=500, detail="Application not initialized")
    
    part_id = request.get("part_id")
    model_number = request.get("model_number")
    
    if not part_id or not model_number:
        raise HTTPException(status_code=400, detail="part_id and model_number are required")
    
    try:
        result = await partselect_app.search_provider.check_compatibility(part_id, model_number)
        return result
    except Exception as e:
        logger.error(f"Compatibility check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting PartSelect Modular Application...")
    uvicorn.run(
        "main_modular:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
