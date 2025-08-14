# RAG-Powered PartSelect Chat Assistant with Custom MCP Server - Instalily.ai case study

Conversational AI assistant for [PartSelect](https://www.partselect.com/) specializing in refrigerator and dishwasher parts. Features **custom MCP (Model Context Protocol) server** with 10 specialized appliance domain tools, DeepSeek LLM integration, real-time streaming responses, and intelligent context management. Built with React frontend, FastAPI backend, and PostgreSQL database.
##### Case-Study Context:
* ***Case Study Submission for Instalily.ai**  
* ***Timeline**: 2-day development sprint  
* **Focus**: Production-ready architecture demonstrating enterprise patterns  
* **Evaluation Criteria**: This solution is assessed on interface design, agentic architecture, extensibility/scalability, and query accuracy. The system handles diverse inquiries from installation guidance ("How can I install part number PS11752778?") to compatibility checking ("Is this part compatible with my WDT780SAEM1 model?") and troubleshooting ("The ice maker on my Whirlpool fridge is not working. How can I fix it?").
##### Live Demo

### Interface in Action
![PartSelect Chat Interface](docs/images/instalily_p1_A.gif)
*Real-time chat interface showing compatibility checking, part search, and context management*

### Backend Processing Stream  
![Backend Query Processing](docs/images/instalily_p2_A.gif)
*Backend logs showing query routing, fast lookup detection, and streaming response generation*

  
## Table of Contents
1. [Key Features](#key-features)
2. [Custom MCP Architecture](#custom-mcp-architecture)
   - [Complete MCP Tools (10)](#complete-mcp-tools-implementation)
   - [MCP Quick Reference](#mcp-quick-reference)
   - [Framework Reusability](#framework-reusability)
3. [Technical Highlights](#technical-highlights)
4. [Quick Demo](#quick-demo)
5. [Project Structure](#project-structure)
6. [Docker Architecture](#docker-architecture)
7. [Quick Start](#quick-start)
8. [System Architecture](#system-architecture)
9. [Technical Stack](#technical-stack)
10. [Advanced Architecture Patterns](#advanced-architecture-patterns)
11. [Key Technical Features](#key-technical-features)
12. [Business Logic Intelligence](#business-logic-intelligence)
13. [Implementation Priorities](#implementation-priorities)
14. [Technical Documentation](#technical-documentation)

## Key Features

**Intelligent Parts Discovery**: Keyword-based search across 3,948 parts (PostgreSQL) with contextual recommendations. Vector search infrastructure deployed with 9,582 FAISS vectors for semantic matching ("ice maker not working" → ice maker assemblies)

**Advanced Compatibility Engine**: Cross-brand compatibility checking with intelligent matching. Knows that Kenmore appliances often use Whirlpool parts, prevents refrigerator components being suggested for dishwashers

**Real-time Streaming Interface**: Server-Sent Events deliver progressive response updates (thinking status, AI response, parts data, repairs, blogs) as the AI processes requests, providing immediate feedback to users

**Enterprise Architecture**: Modular provider pattern allows swapping LLM backends or data sources without system changes. Async processing handles concurrent conversations, horizontal scalability ready

## Custom MCP Architecture

### Complete MCP Tools Implementation

Our custom Model Context Protocol server provides **10 specialized tools** that transform generic LLM capabilities into domain-specific appliance intelligence:

#### **Database Tools (5 tools)**
1. **search_parts()** - Advanced part discovery with filtering (brand, appliance type, keyword matching)
2. **get_part_details()** - Complete part specifications and metadata retrieval
3. **check_compatibility()** - Cross-appliance validation preventing $200 ordering mistakes
4. **search_models()** - Appliance model lookup with fuzzy matching for variations
5. **suggest_compatible_parts()** - Model-specific part recommendations based on issue descriptions

#### **Vector Search Tools (2 tools)**
6. **semantic_search_parts()** - Natural language to parts matching ("ice maker broken" → specific assemblies)
7. **find_similar_parts()** - Vector similarity matching for alternative part discovery

#### **Hybrid Intelligence Tools (2 tools)**
8. **smart_part_search()** - Combines database + semantic search for comprehensive results
9. **suggest_compatible_parts()** - Model-specific part recommendations based on issue descriptions

#### **Utility Tools (1 tool)**
10. **get_server_status()** - Server health and component status monitoring

### Key Innovation Features

**Cross-Appliance Validation**: 100% confidence blocking prevents refrigerator parts being ordered for dishwashers, eliminating costly returns

**Brand Intelligence**: Understands that Kenmore appliances often use Whirlpool parts, unlocking cost savings and compatibility options

**Hybrid Search**: Combines SQL database queries with vector similarity search for both exact matches and semantic understanding

**Progressive Context Building**: Remembers appliance type, brand, model, and symptoms across conversation turns, eliminating repetitive questioning

### Framework Reusability

The MCP architecture pattern we've built extends far beyond appliances:
- **Automotive Parts**: Same compatibility logic for car parts and models
- **Electronics Repair**: Component compatibility for phones, laptops, etc.
- **Home Improvement**: Tool and material compatibility for construction projects
- **Medical Equipment**: Device part compatibility for healthcare providers

**Why This Matters for Instalily.ai**: This isn't just an appliance solution - it's a **reusable AI architecture framework** that can be deployed across any domain requiring specialized knowledge and compatibility validation.

### MCP Quick Reference
| Tool | Purpose | Business Impact |
|------|---------|----------------|
| **check_compatibility()** | Validate part-to-model fit | Prevents $200 ordering mistakes |
| **search_parts()** | Advanced part discovery | Fast keyword-based results |
| **get_brand_relationships()** | Corporate ownership mapping | Unlocks cross-brand compatibility |
| **semantic_search_parts()** | Natural language matching | "ice maker broken" → specific parts |
| **smart_part_search()** | Hybrid database + vector search | Comprehensive result coverage |
| **get_part_details()** | Complete part specifications | Price, description, installation notes |
| **search_models()** | Appliance model lookup | Fuzzy matching for model variations |
| **find_similar_parts()** | Alternative part discovery | Compatible alternatives with scores |
| **suggest_compatible_parts()** | Model-specific recommendations | Targeted suggestions based on issues |

### MCP Architecture Overview
![MCP Architecture](docs/images/mcp_architecture_diagram.png)

See detailed system design: [Request Flow Diagram](docs/diagrams/request_flow_diagram.md)

## Technical Highlights

**RAG Infrastructure**: FAISS vector indexing framework with OpenAI embeddings deployed. PostgreSQL database (Docker) with 3,948 parts loaded, FAISS indexes with 9,582 vectors for semantic search

**Custom MCP Implementation**: Built specialized Model Context Protocol server with appliance-domain tools for compatibility checking, part lookup, and cross-brand intelligence. Features async tool orchestration, structured error handling, and modular provider architecture

**Performance Optimized**: Intelligent caching system (sub-100ms for cache hits), instant compatibility validation (<100ms for part-to-appliance type checking), fast lookup service for direct database matches, progressive streaming responses, and multi-level optimization layers that prioritize immediate user value over complete responses

**Production Ready**: Health monitoring endpoints, comprehensive error boundaries with fallback strategies, environment-based configuration, structured logging, and modular architecture supporting horizontal scaling

**Domain Expertise**: Appliance-specific compatibility validation, installation guidance workflows, progressive troubleshooting assistance. Scope-limited to refrigerator and dishwasher parts for accuracy.

## Quick Demo

### 1. Streaming Response in Action
Shows: Your streaming architecture working, not just a static response
### 2. Context Management Proof
**User**: "My dishwasher door won't close"  
**AI**: "I can help with that door issue. What's your dishwasher's brand and model?"  
**User**: "It's a Whirlpool WDT780SAEM1"  
**AI**: "Perfect! For your Whirlpool WDT780SAEM1, door closure issues are commonly caused by..."  
*[Shows specific parts without asking for appliance type again]*
### 3. Compatibility Intelligence Demo
System preventing refrigerator parts being suggested for dishwashers + cross-brand intelligence

**Smart Prevention**:
- Blocks refrigerator ice maker parts for dishwasher queries
- Knows Kenmore appliances often use Whirlpool parts
- Provides compatibility status for part recommendations

## Project Structure

```markdown
partSelect-caseStudy-instalily/
├── backend/                           # FastAPI backend services
│   ├── database/                      # Database models and connection management
│   │   ├── __init__.py
│   │   ├── connection.py              # PostgreSQL connection pooling
│   │   ├── database.py                # Database initialization and models
│   │   ├── models.py                  # SQLAlchemy models for parts, models, brands
│   │   └── test_connection.py         # Database connectivity testing
│   ├── mcp_client/                    # MCP client implementation
│   │   ├── models.py                  # Pydantic models for MCP communication
│   │   └── orchestrator.py            # FastAPI app with MCP integration
│   ├── mcp_servers/                   # Custom MCP tools for appliance domain
│   │   ├── __init__.py
│   │   └── partselect_server.py       # Specialized tools (compatibility, search, lookup)
│   ├── providers/                     # Modular service providers
│   │   ├── __init__.py
│   │   ├── interfaces.py              # Abstract provider interfaces
│   │   ├── data/                      # Data access providers
│   │   │   ├── __init__.py
│   │   │   ├── csv_provider.py        # CSV-based data loading
│   │   │   └── database_provider.py   # PostgreSQL data access
│   │   ├── llm/                       # Language model providers
│   │   │   ├── __init__.py
│   │   │   └── deepseek_provider.py   # DeepSeek API integration
│   │   └── search/                    # Search providers
│   │       ├── __init__.py
│   │       ├── simple_search.py       # Keyword-based search
│   │       └── openai_vector_search.py # Vector similarity search
│   ├── services/                      # Core business logic services
│   │   ├── conversation_cache.py      # Response caching system
│   │   ├── conversation_context_manager.py # Context persistence
│   │   ├── customer_service_optimizer.py   # Fast response optimization
│   │   └── fast_lookup_service.py     # Direct database part lookups
│   ├── scripts/                       # Database setup and utility scripts
│   │   ├── __init__.py
│   │   ├── load_csv_to_postgres.py    # CSV to PostgreSQL loader (primary)
│   │   ├── merge_json_to_csv.py       # Data format conversion
│   │   ├── populate_models.py         # Load appliance models data
│   │   └── populate_vectors.py        # Create FAISS vector indexes
│   ├── data/                          # Parts and models datasets
│   │   ├── parts_dataset.csv          # 3,948 appliance parts (CSV format)
│   │   ├── all_models.csv             # Appliance model database
│   │   ├── dishwasher_repairs.csv     # Repair guides and troubleshooting
│   │   └── refrigerator_repairs.csv   # Refrigerator-specific repairs
│   ├── vector_stores/                 # FAISS indexes for semantic search
│   │   ├── parts/                     # Parts similarity index (9,582 vectors)
│   │   ├── repairs/                   # Repair guides index (21 vectors)
│   │   └── blogs/                     # Installation guides index (217 vectors)
│   ├── web_scraper/                   # Data collection tools
│   │   ├── __init__.py
│   │   ├── scrape_parts.py            # PartSelect parts scraper
│   │   ├── scrape_blog.py             # Installation guides scraper
│   │   ├── scrape_repair.py           # Repair guides scraper
│   │   └── run_scrapers.py            # Orchestrated data collection
│   ├── app_factory.py                 # Application factory pattern
│   ├── config.py                      # Environment configuration
│   ├── main_modular.py                # Primary application entry point
│   ├── requirements.txt               # Python dependencies
│   └── .env                           # Environment variables (API keys, DB config)
├── frontend/                          # React frontend application
│   ├── public/
│   │   ├── index.html
│   │   ├── manifest.json
│   │   ├── partselect-logo.png        # Brand assets
│   │   └── partselect-minilogo.png
│   ├── src/
│   │   ├── components/                # React components
│   │   │   ├── ChatWindow.js          # Main chat interface
│   │   │   └── ChatWindow.css         # Component styling
│   │   ├── api/
│   │   │   └── api.js                 # Backend integration and SSE handling
│   │   ├── App.js                     # Main application component
│   │   ├── App.css                    # Global styling
│   │   └── index.js                   # Application entry point
│   ├── package.json                   # Node.js dependencies
│   └── package-lock.json              # Dependency lock file
├── docs/                              # Comprehensive technical documentation
│   ├── case-study-materials/          # Case study documentation
│   │   ├── case-study.md              # Case study analysis and approach
│   │   └── prompt-engineering.md      # LLM prompt design and optimization
│   ├── diagrams/                      # System architecture diagrams
│   │   ├── DIAGRAM_KEY.md             # Diagram creation guide and conventions
│   │   ├── mcp_architecture_diagram.md # MCP tools architecture
│   │   ├── request_flow_diagram.md    # End-to-end request processing
│   │   ├── system_architecture_diagram.md # High-level system overview
│   │   └── database_schema_diagram.md # Database relationships
│   ├── images/                        # Visual assets and diagrams
│   │   ├── database_schema.png
│   │   ├── mcp_architecture_diagram.png
│   │   ├── request_flow_diagram.png
│   │   ├── system_architecture_diagram.png
│   │   ├── instalily_p1_A.gif         # Interface demo
│   │   └── instalily_p2_A.gif         # Backend processing demo
│   ├── API_DOCUMENTATION.md           # API endpoint specifications
│   ├── FAST_COMPATIBILITY_SYSTEM.md   # Fast compatibility documentation
│   ├── PERFORMANCE_ANALYSIS.md        # Actual performance test results
│   └── style-guide.md                 # PartSelect design system and UI guidelines
├── .gitignore                         # Git ignore patterns
└── README.md                          # Project overview and setup guide
```
### Key Directory Highlights
**Backend Architecture**:
- `mcp_servers/`: Custom MCP implementation with appliance domain expertise
- `providers/`: Modular pattern supporting multiple LLM, data, and search backends
- `services/`: Business logic layer with caching and context management
- `tests/`: Performance validation and system integration testing

**Data Layer**:
- `data/`: 3,948 parts in PostgreSQL + 9,582 FAISS vectors with appliance models and repair guides
- `vector_stores/`: FAISS indexes for semantic search capabilities
- `web_scraper/`: Data collection tools for PartSelect integration

**Frontend**:
- `components/`: React chat interface with streaming response handling
- `api/`: Server-Sent Events integration for real-time updates

**Documentation**:
- Comprehensive technical documentation covering architecture, implementation patterns, and case study analysis

## Docker Architecture

### PostgreSQL Database Container
The system uses a dockerized PostgreSQL database with pgvector extension for production-ready data persistence:

```bash
# PostgreSQL container with pgvector support
docker run --name partselect-postgres \
  -e POSTGRES_USER=partselect \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=partselect_db \
  -p 5432:5432 \
  -d pgvector/pgvector:pg15
```

**Database Specifications**:
- **Container**: `pgvector/pgvector:pg15` with pgvector extension
- **Data**: 3,948 parts loaded from processed datasets
- **Schema**: Advanced schema with JSONB metadata, full-text search indexes
- **Performance**: Sub-150ms queries with optimized indexing

![Database Schema](docs/images/database_schema.png)
*Database relationships showing parts, models, brands, and compatibility tables*

**Why Docker PostgreSQL?**
- **Consistent deployment**: Same database version across development and production
- **pgvector ready**: Vector extension pre-installed for future semantic search
- **Isolation**: Database runs independently of host system configuration
- **Backup/restore**: Easy container-based data management

## Quick Start 

### Prerequisites
- **Docker** ([get Docker here](https://www.docker.com/get-started))
- **Python 3.9+** | **Node.js 16+** | **Git**
- **DeepSeek API key** ([get one here](https://platform.deepseek.com))
- **OpenAI API key** ([get one here](https://platform.openai.com)) - for vector embeddings

### 1. Clone & Setup
```bash
git clone <your-repo-url>
cd partSelect-caseStudy-instalily
```

### 2. Database Setup (Docker PostgreSQL)
```bash
# Start PostgreSQL container with pgvector extension
docker run --name partselect-postgres -e POSTGRES_USER=partselect -e POSTGRES_PASSWORD=password -e POSTGRES_DB=partselect_db -p 5432:5432 -d pgvector/pgvector:pg15

# Verify container is running
docker ps
```

### 3. Backend Setup
```bash
cd backend
pip install -r requirements.txt

# Create .env file with your API keys
echo "DEEPSEEK_API_KEY=your_deepseek_key_here" > .env
echo "OPENAI_API_KEY=your_openai_key_here" >> .env
echo "APP_MODE=advanced" >> .env
echo "DATABASE_URL=postgresql://partselect:password@localhost:5432/partselect_db" >> .env

# Load data into PostgreSQL (3,948 parts after deduplication)
python -m scripts.load_csv_to_postgres

# Start backend server
python main_modular.py
```
✅ **Backend**: http://localhost:8000  
✅ **Database**: PostgreSQL with 3,948 parts loaded  
✅ **Vector Search**: FAISS indexes (9,582 parts, 21 repairs, 217 blogs)

### 4. Frontend Setup
```bash
cd frontend
npm install && npm start
```
✅ **Chat interface**: http://localhost:3000

### 5. Verify Working
- Visit http://localhost:8000/api/health (should show "healthy")
- Chat interface loads and accepts messages
- Responses stream progressively (not all at once)
- Test query: "PS11752778" (should return in ~271ms)

### Quick Fixes
| Issue | Solution |
|-------|----------|
| Backend won't start | Check DEEPSEEK_API_KEY and OPENAI_API_KEY in .env |
| Database connection error | Ensure Docker PostgreSQL container is running |
| Frontend error | Ensure backend running on port 8000 |
| No parts data | Run `python -m scripts.load_csv_to_postgres` |
| Vector search errors | Check FAISS indexes in backend/vector_stores/ |
## System Architecture

### High-Level Architecture Flow
![System Architecture](docs/images/system_architecture_diagram.png)
*Layered architecture showing React frontend, FastAPI backend, MCP tools, and data providers*

**Why this layered approach?**
- **Separation of concerns**: UI handles display, backend handles logic, MCP handles domain tools, providers handle data
- **Scalability**: Each layer can be scaled independently based on load patterns
- **Maintainability**: Changes to one layer don't cascade through the entire system

### Detailed Request Flow
![Request Flow](docs/images/request_flow_diagram.png)
*End-to-end request processing showing fast compatibility path vs full LLM pipeline*
**Why MCP as the core intelligence layer?**
- **Domain expertise**: Standard LLMs don't understand appliance part compatibility
- **Tool orchestration**: Need to coordinate multiple specialized functions (search, validate, recommend)
- **Extensibility**: Easy to add new appliance types or validation rules without retraining models
## Technical Stack

### Backend Architecture
| Component          | Technology                | Why Chosen                                                                                                     |
| ------------------ | ------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Web Framework**  | FastAPI + Uvicorn         | **Async performance** for concurrent conversations + **automatic API docs** for development                    |
| **Language Model** | DeepSeek API              | **Cost-effective** ($0.14 vs $15/M tokens) with **strong reasoning** for complex compatibility logic           |
| **Database**       | PostgreSQL (Docker) + asyncpg | **Structured relationships** (parts→models→brands) with Docker containerization for consistent deployment |
| **Streaming**      | Server-Sent Events        | **Simpler than WebSocket** for one-way communication + **native browser support** without additional libraries |
| **Vector Search**  | FAISS + OpenAI Embeddings | **Local FAISS** for speed vs **cloud vector DBs** for cost + **OpenAI embeddings** for semantic quality        |

### MCP (Model Context Protocol) Integration

**Why we built custom MCP tools instead of using generic APIs:**

| Tool | Business Problem Solved | Technical Approach |
|------|------------------------|-------------------|
| **check_compatibility()** | **Customers order wrong parts** (40% return rate in appliance industry) | Cross-appliance validation + brand relationship mapping with compatibility checking |
| **semantic_search_parts()** | **Users describe problems, not part names** ("ice maker broken" vs "WPW10348269") | Vector embeddings match natural language to technical part descriptions |
| **search_models()** | **Model numbers are complex** (WDT780SAEM1 vs WDT780SAEM0) | Series-level matching + fuzzy search for slight variations |
| **get_brand_relationships()** | **Corporate ownership confusion** (Kenmore made by Whirlpool) | Real-world business relationship mapping with compatibility determination |

**Why MCP over direct API calls?**
- **Standardized interface**: Tools can be reused across different LLM providers
- **Composability**: LLM can orchestrate multiple tools in sequence
- **Error handling**: Built-in tool execution failure management
- **Extensibility**: Add new appliance categories without changing core architectures
## Advanced Architecture Patterns

### Multi-Tier Performance Optimization
```python
# Tier 1: Cache Layer (<100ms)
conversation_cache.get_cached_response(query, conversation_id)

# Tier 2: Fast Lookup Service (<100ms) 
fast_lookup_service.handle_fast_lookup(query)  # Direct DB matches

# Tier 3: Customer Service Optimizer (<200ms)
customer_service_optimizer.analyze_query_fast(query)  # Generic responses

# Tier 4: Full MCP + LLM Pipeline (1-3s)
mcp_orchestrator.execute_tools() + deepseek_llm.generate()
```

**Why this cascading approach?**
- **User psychology**: People expect instant feedback, not 3-second waits
- **Cost optimization**: Avoid expensive LLM calls for simple/repeated queries
- **Resource efficiency**: Cache hits use zero external API calls
- **Graceful degradation**: System provides value even if LLM services fail

### Conversation Context Intelligence
```python
@dataclass
class ConversationContext:
    appliance_type: Optional[str] = None     # 'refrigerator' or 'dishwasher'
    brand: Optional[str] = None              # 'Whirlpool', 'Kenmore', etc.
    model_number: Optional[str] = None       # 'WDT780SAEM1'
    symptoms: List[str] = field(default_factory=list)
    completeness_level: float = 0.0         # Information completeness score
```

**Why persistent context vs stateless requests?**
- **User experience**: Eliminates repetitive "What appliance?" questions
- **Accuracy improvement**: More context = better part recommendations
- **Conversation flow**: Enables natural diagnostic questioning
- **Cost reduction**: Shorter prompts when context is maintained

### Provider Pattern Architecture
```python
class PartSelectApp:
    def __init__(self):
        self.data_provider: DataProvider = CSVDataProvider()
        self.search_provider: SearchProvider = OpenAIVectorSearchProvider()
        self.llm_provider: LLMProvider = DeepSeekProvider()
```

**Why abstracted providers vs direct implementations?**
- **Technology flexibility**: Easy to swap DeepSeek → GPT-4, CSV → PostgreSQL
- **Testing**: Mock providers for unit tests without external API calls
- **Cost management**: Switch to cheaper providers during development
- **Future-proofing**: New AI models or databases can be integrated without rewriting business logic

## Key Technical Features

### 1. Custom MCP Tooling

```python
# Prevents $200 ordering mistakes
if part_appliance_type != model_appliance_type:
    return {
        "compatible": False,
        "explanation": "Cross-appliance incompatibility: refrigerator part cannot be used in dishwasher"
    }
```

### 2. Streaming Response Architecture

```javascript
{"type": "thinking", "content": "Analyzing your dishwasher door issue..."}    // 0.1s
{"type": "response", "content": "For Whirlpool WDT780SAEM1, door issues..."}  // 0.8s
{"type": "parts", "content": [{"name": "Door Latch Assembly"}]}                // 1.5s
{"type": "complete", "response_time": 1.2}                                     // 2.1s
```

### 3. Intelligent Performance Layers
**Problem**: LLM calls can be expensive and slow for simple queries
**Solution**: Smart routing with fallback layers

- **Cache layer**: "What's a water filter?" → instant cached response
- **Fast lookup**: "PS11752778 price?" → direct database query
- **LLM layer**: "Why is my ice maker making noise?" → full AI reasoning

### 4. Production-Ready Patterns
- **External API failures**: DeepSeek/OpenAI services can be unreliable
- **User experience**: Better to show "Try again" than crash the app
- **Business continuity**: System provides basic functionality even during outages

**Why health monitoring endpoints?**
- **Operations visibility**: Know which components are failing before users complain
- **Debugging**: Quickly identify if issue is LLM, database, or vector search
- **Scaling decisions**: See which providers are under load

## Business Logic Intelligence

### Domain-Specific Validation
**Why encode appliance industry knowledge?**

- Prevents compatibility errors by validating part-to-appliance type matching before recommendations
- Builds trust through accurate part suggestions based on actual appliance specifications
### Cross-Brand Compatibility
```python
whirlpool_family = {
    "Kenmore": True,    # Many Kenmore appliances manufactured by Whirlpool
    "Maytag": True,     # Acquired by Whirlpool in 2006
    "KitchenAid": True, # Whirlpool premium brand since 1986
}
```

**Why encode corporate relationships?**

- Enables cross-brand part recommendations when brands share manufacturing and design
- Improves search results by understanding that brand names don't always match actual manufacturers

## Implementation Priorities

### Phase 1: Core Functionality
Critical user-facing features and business requirements
- **DeepSeek LLM Integration**: Appliance-specific prompting with refrigerator/dishwasher domain constraints
- **Streaming Interface**: Server-Sent Events for progressive response delivery
- **Parts Database**: 9,580+ parts catalog with structured search capabilities
- **Context Management**: Remembers appliance type, brand, model, and symptoms across conversation turns

### Phase 2: Intelligence Layer
Advanced AI capabilities and domain expertise
- **MCP Tool Architecture**: Specialized compatibility checking, part lookup, and model search tools
- **Cross-Brand Intelligence**: Corporate relationship mapping (Whirlpool family) with compatibility determination
- **Cross-Appliance Validation**: Prevents refrigerator parts being suggested for dishwashers
- **Performance Optimization**: Multi-tier response system (cache → fast lookup → full AI)

### Phase 3: Production Architecture
Scalability, reliability, and extensibility foundations
- **Modular Provider Pattern**: Pluggable LLM, search, and data providers
- **Error Handling**: Graceful degradation with user-friendly fallbacks
- **Health Monitoring**: /api/health endpoints and structured logging
- **Environment Configuration**: Type-safe settings management with validation

## Technical Documentation

### MCP Implementation Documentation
- [MCP Architecture Diagram](docs/diagrams/mcp_architecture_diagram.md) - Detailed system design
- [Request Flow Diagram](docs/diagrams/request_flow_diagram.md) - End-to-end processing flow
- [Database Schema](docs/diagrams/database_schema_diagram.md) - Data relationships and structure
- [Diagram Creation Guide](docs/diagrams/DIAGRAM_KEY.md) - Technical diagram specifications

### System Architecture Details
- [Case Study Analysis](docs/case-study-materials/case-study.md) - Implementation approach and requirements
- [Prompt Engineering Guide](docs/case-study-materials/prompt-engineering.md) - LLM optimization strategies
- [Performance Analysis](docs/PERFORMANCE_ANALYSIS.md) - Actual test results and metrics
- [Fast Compatibility System](docs/FAST_COMPATIBILITY_SYSTEM.md) - Lightning-fast compatibility checking
- [API Documentation](docs/API_DOCUMENTATION.md) - Endpoint specifications and usage
- [PartSelect Style Guide](docs/style-guide.md) - UI/UX design system and branding