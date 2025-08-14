# System Architecture Overview

## High-Level Architecture Flow

```mermaid
---
title: "SYSTEM ARCHITECTURE OVERVIEW"
config:
  theme: default
  themeVariables:
    primaryColor: '#1565c0'
    primaryTextColor: '#000'
    primaryBorderColor: '#1565c0'
    lineColor: '#666'
    sectionBkgColor: '#f8f9fa'
    altSectionBkgColor: '#fff'
    gridColor: '#e0e0e0'
    tertiaryColor: '#f5f5f5'
    titleColor: '#1565c0'
    c0: '#1565c0'
    c1: '#1976d2'
    c2: '#1e88e5'
    c3: '#2196f3'
    fontFamily: 'Arial, sans-serif'
    fontSize: '18px'
    titleFontSize: '28px'
---
graph TD
    subgraph Frontend["<b>FRONTEND LAYER</b>"]
        A["React Frontend<br/>Streaming Interface<br/>SSE Client"]
    end
    
    subgraph Backend["<b>BACKEND LAYER</b>"]
        B["FastAPI Backend<br/>Orchestrator + Context<br/>Async Request Handling"]
        C["MCP Orchestrator<br/>Tool Coordination<br/>Query Analysis & Routing"]
    end
    
    subgraph Intelligence["<b>INTELLIGENCE LAYER</b>"]
        D["Custom MCP Tools<br/>Domain Intelligence<br/>9 Specialized Functions"]
    end
    
    subgraph Data["<b>DATA LAYER</b>"]
        E[("PostgreSQL Database<br/>Parts + Models + Brands<br/>9,580+ Parts Catalog")]
        F[("Vector Stores<br/>FAISS Indexes<br/>Semantic Search Ready")]
    end
    
    subgraph AI["<b>AI LAYER</b>"]
        G["DeepSeek LLM<br/>Response Generation<br/>Cost: $0.14/M Tokens"]
        
        H{{"Performance Optimization<br/>Pipeline"}}
        
        I["Tier 1: Cache<br/>Memory-based responses"]
        J["Tier 2: Fast Lookup<br/>Direct database queries"] 
        K["Tier 3: Service Optimizer<br/>FAQ-style responses"]
        L["Tier 4: Full AI Pipeline<br/>Complete RAG processing"]
    end
    
    subgraph Response["<b>RESPONSE LAYER</b>"]
        M[/"Streaming SSE<br/>Progressive Updates<br/>Real-time delivery"/]
    end
    
    %% MAIN FLOW (thick arrows with step numbers)
    A ==>|"<b>1. User Query</b>"| B
    B ==>|"<b>2. Route Request</b>"| C
    C ==>|"<b>3. Execute Domain Tools</b>"| D
    D ==>|"<b>6. Generate Response</b>"| G
    G ==>|"<b>7. Stream Response</b>"| M
    M ==>|"<b>8. Real-time Updates</b>"| A
    
    %% Data connections (medium arrows with sub-steps)
    D -->|"4a. Retrieve Data"| E
    D -->|"4b. Vector Search"| F
    
    %% Performance optimization flow (medium arrows with sub-steps)
    B -->|"2a. Query Processing"| H
    H -->|"2b. Try Cache First"| I
    I -->|"2c. Cache Miss"| J
    J -->|"2d. No Direct Match"| K
    K -->|"2e. Complex Query"| L
    L -->|"5. Complex Reasoning"| G
    
    %% Alternative success paths (dotted for shortcuts)
    I -.->|"2b-alt. Cache Hit"| M
    J -.->|"2c-alt. Direct Match"| M
    K -.->|"2d-alt. FAQ Match"| M
    
    %% Styling with visual hierarchy
    classDef frontend fill:#e3f2fd,stroke:#1565c0,stroke-width:4px,color:#000
    classDef backend fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px,color:#000
    classDef intelligence fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px,color:#000
    classDef data fill:#fff3e0,stroke:#ef6c00,stroke-width:3px,color:#000
    classDef ai fill:#fce4ec,stroke:#c2185b,stroke-width:3px,color:#000
    classDef perf fill:#f1f8e9,stroke:#558b2f,stroke-width:2px,color:#000
    classDef response fill:#fff8e1,stroke:#f57f17,stroke-width:4px,color:#000
    
    class A frontend
    class B,C backend
    class D intelligence
    class E,F data
    class G,H ai
    class I,J,K,L perf
    class M response
```

## Component Legend

| Layer | Component | Performance Target | Business Value |
|-------|-----------|-------------------|----------------|
| **Frontend** | React Frontend | <50ms UI updates | Real-time user feedback |
| **Backend** | FastAPI Backend | 100+ concurrent users | Scalable request handling |
| **Backend** | MCP Orchestrator | <100ms tool routing | Intelligent query analysis |
| **Intelligence** | Custom MCP Tools | <200ms average execution | Appliance domain expertise |
| **Data** | PostgreSQL Database | <150ms queries | 3,948 parts catalog access |
| **Data** | Vector Stores | <200ms semantic search | Natural language part discovery |
| **AI** | DeepSeek LLM | $0.14/M tokens | Cost-effective response generation |
| **Response** | Streaming SSE | <80ms chunk delivery | Progressive response updates |

## Architecture Benefits

### Layered Approach
- **Separation of concerns**: UI handles display, backend handles logic, MCP handles domain tools, providers handle data
- **Scalability**: Each layer can be scaled independently based on load patterns
- **Maintainability**: Changes to one layer don't cascade through the entire system

### Performance Optimization
- **Multi-tier response system**: Cache → Fast Lookup → Service Optimizer → Full AI Pipeline
- **Progressive degradation**: System provides value even when external services fail
- **Cost optimization**: Avoid expensive LLM calls for simple/repeated queries

### Technical Innovation
- **Custom MCP implementation**: Domain-specific appliance intelligence
- **Real-time streaming**: Server-Sent Events for immediate user feedback
- **Enterprise patterns**: Modular provider architecture for technology flexibility
