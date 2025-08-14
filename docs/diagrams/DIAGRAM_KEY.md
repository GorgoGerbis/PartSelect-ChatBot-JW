# Diagram Documentation & Recreation Guide

This document provides detailed specifications for all system diagrams, including component descriptions, layouts, and keys. Use this as a reference for recreating or modifying diagrams.


## Flowchart Symbols & Conventions

### Node Shapes & Meanings
| Shape | Symbol | Purpose | Example |
|-------|--------|---------|---------|
| **Rectangle** | `A["Text"]` | Process/Component | FastAPI Backend, React Frontend |
| **Rounded Rectangle** | `A(["Text"])` | Start/End Points | User Input, Final Response |
| **Circle** | `A(("Text"))` | Data Storage | Database, Vector Store |
| **Diamond** | `A{"Text"}` | Decision Point | Cache Hit/Miss, Confidence Check |
| **Hexagon** | `A{{"Text"}}` | Preparation/Setup | Query Analysis, Pipeline Setup |
| **Parallelogram** | `A[/"Text"/]` | Input/Output | Streaming Response, Data Export |
| **Subgraph** | `subgraph Title["<b>LAYER</b>"]` | Logical Grouping | System Layers, Components |

### Arrow Types & Flow Hierarchy
| Arrow Type | Syntax | Purpose | Visual Weight |
|------------|--------|---------|---------------|
| **Main Flow** | `A ==> B` | Primary system flow | Thick, bold labels |
| **Secondary Flow** | `A --> B` | Supporting processes | Medium weight |
| **Alternative Path** | `A -.-> B` | Conditional/fallback | Dotted lines |
| **Bidirectional** | `A <--> B` | Two-way communication | Double arrows |

### Color Coding System
| Layer | Color | Purpose | Border Weight |
|-------|-------|---------|---------------|
| **Frontend** | Light Blue (#e3f2fd) | User interface | Thick (4px) |
| **Backend** | Light Purple (#f3e5f5) | Core processing | Medium (3px) |
| **Intelligence** | Light Green (#e8f5e8) | AI/ML components | Medium (3px) |
| **Data** | Light Orange (#fff3e0) | Storage systems | Medium (3px) |
| **AI** | Light Pink (#fce4ec) | LLM processing | Medium (3px) |
| **Response** | Light Yellow (#fff8e1) | Output delivery | Thick (4px) |

### Typography Conventions
- **Subgraph Titles**: `<b>LAYER NAME</b>` - Bold, uppercase for hierarchy
- **Main Flow Labels**: `<b>Label Text</b>` - Bold for primary paths
- **Component Names**: First line bold, details in subsequent lines
- **Performance Metrics**: Include targets/timing where relevant

## Diagram Suite Overview

1. **System Architecture Overview** - High-level component relationships and data flow
2. **MCP Tools Architecture** - Your custom domain intelligence implementation with specialized appliance tools
3. **Request Processing Flow** - End-to-end sequence with timing and SSE events
4. **Database Schema Relationships** - Data model and business logic relationships

## 1. System Architecture Overview

### Description
High-level system architecture showing the layered approach with performance tiers. Demonstrates separation of concerns and data flow from React frontend through FastAPI backend to AI and data providers.

### Layout Structure
- **Main Flow**: Horizontal left-to-right flow (A → B → C → D)
- **Data Sources**: Two parallel data components (E, F) connected to MCP Tools (D)
- **AI Integration**: DeepSeek LLM (G) connected to Backend (B)
- **Streaming Loop**: SSE (H) creates feedback loop from Backend (B) back to Frontend (A)
- **Performance Tiers**: Separate subgraph showing 4-tier optimization strategy

### Components
| Node ID | Component | Description | Emoji | Performance Note |
|---------|-----------|-------------|-------|------------------|
| A | React Frontend | Streaming Interface, SSE Client | 🖥️ | <50ms UI updates |
| B | FastAPI Backend | Orchestrator + Context, Async Request Handling | ⚡ | 100+ concurrent users |
| C | MCP Orchestrator | Tool Coordination, Query Analysis & Routing | 🔧 | <100ms tool routing |
| D | Custom MCP Tools | Domain Intelligence, 12+ Specialized Functions | 🛠️ | <200ms average |
| E | PostgreSQL Database | Parts + Models + Brands, 9,580+ Parts Catalog | 🗄️ | <150ms queries |
| F | Vector Stores | FAISS Indexes, Semantic Search Ready | 🔍 | <200ms when enabled |
| G | DeepSeek LLM | Response Generation, $0.14/M Tokens | 🤖 | 1-3s generation |
| H | Streaming SSE | Progressive Updates, Sub-second Response | 📡 | <80ms chunks |

### Performance Tiers Subgraph
| Tier | Component | Performance | Purpose |
|------|-----------|-------------|---------|
| I | Cache | <100ms | Repeated queries |
| J | Fast Lookup | <100ms | Direct database matches |
| K | Service Optimizer | <200ms | Generic responses |
| L | Full AI Pipeline | 1-3s | Complex reasoning |



## 2. Request Processing Flow

### Description
Detailed sequence diagram showing the complete request-response cycle for a dishwasher drainage issue. Demonstrates streaming architecture, tool orchestration, and progressive response delivery.

### Participants
| Participant | Display Name | Icon | Role |
|-------------|--------------|------|------|
| U | User | 👤 | Initiates queries |
| F | Frontend | 🖥️ | React + SSE client |
| B | Backend | ⚡ | FastAPI orchestrator |
| M | MCP Tools | 🛠️ | Custom server |
| L | DeepSeek LLM | 🤖 | AI response generation |
| D | Database | 🗄️ | PostgreSQL data source |

### Message Flow & Timing
1. **User Input** (0ms): "My dishwasher won't drain"
2. **API Request** (50ms): POST /api/chat (stream=true)
3. **Thinking Response** (100ms): SSE immediate feedback
4. **Tool Execution** (200ms): check_compatibility() + search_parts()
5. **Database Query** (400ms): Structured appliance-specific query
6. **Data Return** (600ms): Filtered results with metadata
7. **Context Building** (800ms): Parts data + compatibility scores
8. **LLM Processing** (1000ms): Contextual prompt with retrieved data
9. **AI Response** (1200ms): Generated troubleshooting advice
10. **Response Stream** (1300ms): Progressive text delivery
11. **Parts Data** (1350ms): Structured component information
12. **Completion** (1400ms): Total response time tracking

### Notes Positioning
- **Right-side notes**: Explain technical details and timing
- **Above sequence**: Context setting ("Example: Dishwasher Drainage Issue")
- **Inline timing**: Approximate response times at each stage

## 3. Database Schema Relationships

### Description
Entity-relationship diagram showing the database structure with business context. Demonstrates how parts, models, brands, and compatibility data interconnect to enable intelligent recommendations.

### Entities & Relationships
| Entity | Relationship | Target | Cardinality | Business Purpose |
|--------|--------------|--------|-------------|------------------|
| PARTS | has | PART_COMPATIBILITY | One-to-Many | Parts can work with multiple models |
| MODELS | supports | PART_COMPATIBILITY | One-to-Many | Models accept multiple compatible parts |
| BRANDS | manufactures | MODELS | One-to-Many | Brands make multiple appliance models |
| BRANDS | related_to | BRAND_RELATIONSHIPS | One-to-Many | Corporate ownership mapping |

### Entity Attributes
#### PARTS
- **partselect_number**: Primary key (e.g., PS11752778)
- **manufacturer_number**: OEM part number
- **name**: Human-readable description
- **brand**: Manufacturer (Whirlpool, GE, Samsung...)
- **appliance_type**: Constraint (refrigerator OR dishwasher)
- **price**: USD pricing
- **category**: Component type (pump, filter, seal...)
- **stock_status**: Availability (in_stock, backorder, discontinued)
- **url**: PartSelect product page link
- **metadata**: JSON (installation_notes, warranty_info)

#### MODELS
- **model_number**: Primary key (e.g., WDT780SAEM1)
- **brand**: Manufacturer brand
- **appliance_type**: Constraint (refrigerator OR dishwasher)
- **description**: Model specifications
- **compatible_brands**: JSON array for cross-brand compatibility
- **metadata**: JSON (year, series, features)

#### BRANDS
- **brand_name**: Primary key (e.g., Whirlpool)
- **parent_company**: Corporate owner
- **country**: Manufacturing origin
- **subsidiaries**: JSON array of owned brands

#### PART_COMPATIBILITY
- **compatibility_type**: Enum (exact, compatible, incompatible)
- **confidence_score**: Float 0.0-1.0 reliability metric
- **notes**: Human-readable explanation
- **source**: Data origin (database, manual_verification, computed)

#### BRAND_RELATIONSHIPS
- **parent_brand**: Corporate owner (e.g., Whirlpool)
- **subsidiary_brand**: Owned brand (Kenmore, Maytag, KitchenAid)
- **is_compatible**: Boolean interchangeability status
- **appliance_type**: Scope (refrigerator, dishwasher, both)
- **notes**: Historical context (acquisition date, manufacturing notes)

## 4. MCP Tools Architecture

### Description
Detailed view of the custom MCP implementation showing tool orchestration and domain-specific intelligence. Highlights the innovation of encoding appliance industry expertise into AI tools.

### Layout Structure
- **Top Level**: Horizontal flow (A → B → C)
- **Tool Layer**: Four parallel tools (D, E, F, G) branching from MCP Server (C)
- **Implementation Layer**: Two implementations per tool showing specific capabilities
- **Innovation Highlight**: Separate subgraph emphasizing business value

### Components & Capabilities
#### Core Architecture
| Node | Component | Description | Responsibilities |
|------|-----------|-------------|------------------|
| A | FastAPI Orchestrator | Request handling, query analysis, context management, response streaming | Entry point |
| B | MCP Client | Tool coordination, tool selection, parallel execution, error handling | Middleware |
| C | Custom MCP Server | Domain intelligence, 12+ specialized tools, appliance expertise, business logic | Core innovation |

#### Specialized Tools
| Tool | Function | Input | Output | Performance |
|------|----------|-------|--------|-------------|
| D | check_compatibility() | part_number, model | compatibility status | <100ms |
| E | search_parts() | query, filters | ranked results | <100ms |
| F | semantic_search() | natural language | similarity scores | <200ms |
| G | get_brand_relationships() | brand names | compatibility matrix | <50ms |

#### Implementation Details
| Tool | Implementation A | Implementation B | Business Impact |
|------|------------------|------------------|-----------------|
| check_compatibility | Cross-appliance validation | Brand compatibility matching | Prevents $200 mistakes |
| search_parts | Keyword matching | Direct database queries | <100ms response time |
| semantic_search | Vector similarity | Natural language → parts | FAISS + OpenAI embeddings |
| get_brand_relationships | Corporate relationships | Business intelligence | Kenmore → Whirlpool mapping |


