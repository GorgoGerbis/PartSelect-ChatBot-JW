# Request Processing Flow

## Detailed Processing Sequence

```mermaid
---
title: "REQUEST PROCESSING FLOW - DETAILED PROCESSING SEQUENCE"
config:
  theme: default
  themeVariables:
    primaryColor: '#1565c0'
    primaryTextColor: '#000'
    primaryBorderColor: '#1565c0'
    lineColor: '#666'
    titleColor: '#1565c0'
    c0: '#1565c0'
    c1: '#1976d2'
    c2: '#1e88e5'
    c3: '#2196f3'
    fontFamily: 'Arial, sans-serif'
    fontSize: '18px'
    titleFontSize: '28px'
---
sequenceDiagram
    participant U as User
    participant F as Frontend<br/>(React + SSE)
    participant B as Backend<br/>(FastAPI)
    participant M as MCP Tools<br/>(Custom Server)
    participant L as DeepSeek LLM<br/>($0.14/M tokens)
    participant D as Database<br/>(PostgreSQL)
    
    Note over U,D: Example: Dishwasher Drainage Issue
    
    U->>F: "My dishwasher won't drain"
    Note right of F: User types natural language query
    
    F->>B: POST /api/chat (stream=true)
    Note right of B: Streaming enabled for real-time updates
    
    B->>F: SSE: {"type": "thinking", "content": "Analyzing..."}
    Note right of F: ~100ms - Immediate feedback
    
    alt Fast Compatibility Check
        B->>B: instant_compatibility_check()
        Note right of B: <100ms - Direct lookup tables
        B->>F: SSE: {"type": "response", "content": "Part incompatible..."}
        Note right of F: Instant response for known parts
        B->>F: SSE: {"type": "complete", "response_time": 0.1}
        Note right of F: Fast path complete
    else Complex Query
        B->>M: check_compatibility() + search_parts()
        Note right of M: Multi-tool orchestration
        
        M->>D: Query parts WHERE appliance_type='dishwasher'<br/>AND symptoms LIKE '%drain%'
        Note right of D: Structured database query
        
        D->>M: [Drain pump, Filter assembly, Hose kit...]
        Note right of M: Filtered results with metadata
        
        M->>B: Parts data + Compatibility scores
        Note right of B: ~800ms - Data retrieved
        
        B->>L: Generate response with context:<br/>User: dishwasher drain issue<br/>Parts: [relevant parts]<br/>Context: troubleshooting
        Note right of L: Contextual prompt engineering
        
        L->>B: "For drainage issues in dishwashers, check..."
        Note right of B: ~1.2s - AI response ready
        
        B->>F: SSE: {"type": "response", "content": "For drainage issues..."}
        Note right of F: Streaming text response
        
        B->>F: SSE: {"type": "parts", "data": [{name: "Drain Pump"...}]}
        Note right of F: Structured parts data
        
        B->>F: SSE: {"type": "complete", "response_time": 1.4}
        Note right of F: Total response time tracking
        
        F->>U: Display progressive response with parts
        Note right of U: Complete user experience
    end
```

## Timing Breakdown

| Stage | Time | Component | Action | User Experience |
|-------|------|-----------|--------|-----------------|
| 0ms | User Input | Frontend | Query received | Immediate typing feedback |
| 50ms | API Request | Backend | Stream initiated | Loading state begins |
| 100ms | Thinking | Frontend | First SSE event | "Analyzing your query..." |
| **FAST PATH** | | | |
| 150ms | Compatibility Check | Backend | Instant lookup tables | Hash table lookup |
| 200ms | Response Ready | Frontend | Compatibility result | <100ms total for known parts |
| **COMPLEX PATH** | | | |
| 200ms | Tool Start | MCP Tools | Multi-tool execution | Progress indication |
| 400ms | DB Query | Database | Structured search | Continued progress |
| 600ms | Data Return | MCP Tools | Results filtering | Still processing |
| 800ms | Context Build | Backend | Data + compatibility | Preparing response |
| 1000ms | LLM Start | DeepSeek | Contextual prompt | AI thinking |
| 1200ms | AI Complete | Backend | Response generated | Content ready |
| 1300ms | Text Stream | Frontend | Progressive display | User sees text |
| 1350ms | Parts Data | Frontend | Structured display | Parts appear |
| 1400ms | Complete | User | Full experience | Total satisfaction |

## Streaming Event Types

### SSE Event Format
```json
{
  "type": "thinking|response|parts|repairs|blogs|complete|error",
  "content": "event-specific data",
  "conversation_id": "uuid",
  "timestamp": "ISO-8601",
  "metadata": {}
}
```

### Event Sequence
1. **thinking**: Immediate feedback ("Analyzing your query...")
2. **response**: AI-generated conversational text
3. **parts**: Structured parts data with compatibility scores
4. **repairs**: Related repair guides and troubleshooting steps
5. **blogs**: Installation guides and how-to articles
6. **complete**: Final event with response time metrics

## Business Value

### User Experience Benefits
- **Perceived Performance**: <100ms initial feedback prevents abandonment
- **Progressive Value**: Users see results as they're generated
- **Engagement**: Real-time updates maintain user attention
- **Trust Building**: Transparent processing builds confidence

### Technical Benefits
- **Scalability**: Streaming reduces server memory usage
- **Responsiveness**: Non-blocking I/O handles concurrent requests
- **Error Recovery**: Graceful degradation when services fail
- **Monitoring**: Built-in response time tracking
