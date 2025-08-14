# API Documentation

## Base URL
`http://localhost:8000`

## Endpoints

### Chat Endpoint
**POST** `/api/chat`

Main chat interface with streaming responses.

**Request Body:**
```json
{
  "query": "Is PS11739035 compatible with WDT780SAEM1?",
  "conversation_id": "1755147311539"
}
```

**Response:** Server-Sent Events stream

**Stream Events:**
```javascript
// Immediate acknowledgment
{"type": "thinking", "content": "Processing your request...", "conversation_id": "1755147311539"}

// AI response text
{"type": "response", "content": "Part PS11739035 is not compatible...", "conversation_id": "1755147311539"} 

// Parts data (if found)
{"type": "parts", "content": [{"name": "Door Latch", "price": 45.99, ...}], "conversation_id": "1755147311539"}

// Completion marker
{"type": "complete", "response_time": 0.271, "conversation_id": "1755147311539"}
```

### Health Check
**GET** `/api/health`

System status and component health.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-14T00:55:04.176Z",
  "components": {
    "database": "connected",
    "llm_provider": "ready", 
    "vector_search": "loaded"
  }
}
```

### Cache Management  
**POST** `/api/cache/clear`

Clear conversation cache (useful for testing prompt changes).

**Response:**
```json
{
  "status": "cache cleared",
  "timestamp": "2025-01-14T00:42:10.806Z"
}
```

## Performance Targets
- Health endpoint: <100ms
- Part lookups: <300ms  
- Compatibility checks: <100ms
- Complex queries: 1-3 seconds
- First streaming chunk: <500ms

## Error Handling
All endpoints return structured error responses:

```json
{
  "detail": "Error description",
  "status_code": 500,
  "timestamp": "2025-01-14T00:55:04.176Z"
}
```

Common errors:
- Missing API keys (DeepSeek/OpenAI)
- Database connection issues
- Invalid conversation_id format
