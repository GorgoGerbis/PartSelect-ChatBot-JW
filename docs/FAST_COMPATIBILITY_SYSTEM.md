# Fast Compatibility System

## Overview
Lightning fast compatibility checking between parts and appliance models using pre-built lookup tables. Responds in <100ms vs 20+ seconds for LLM-based checks.

## How It Works

### 1. Appliance Type Mapping
On startup, the system builds two lookup tables from the parts CSV:

```python
part_appliance_map = {
    "PS11739035": "refrigerator",  # Ice dispenser door chute
    "PS8770519": "dishwasher",     # Door spring kit
    # ... 3,948 total parts
}

model_appliance_map = {
    "WDT": "dishwasher",    # WDT780SAEM1 = dishwasher
    "WRF": "refrigerator",  # WRF555SDFZ = refrigerator  
    "RF": "refrigerator",   # RF23J9011SR = refrigerator
    # ... common prefixes
}
```

### 2. Instant Lookup Process
For query: "Is PS11739035 compatible with WDT780SAEM1?"

1. Extract part number: `PS11739035`
2. Extract model number: `WDT780SAEM1` 
3. Lookup part type: `refrigerator`
4. Lookup model type: `dishwasher` (WDT prefix)
5. Compare: `refrigerator != dishwasher` = **INCOMPATIBLE**
6. Response: <100ms

### 3. Integration Points

**Fast Lookup Service** (`backend/services/fast_lookup_service.py`):
- `instant_compatibility_check()` method
- Called before full LLM pipeline
- Returns formatted response or None (fallback to LLM)

**Customer Service Optimizer** (`backend/services/customer_service_optimizer.py`):
- Detects compatibility queries 
- Lowers confidence to route to fast lookup
- Prevents generic "I can help with part number..." responses

## Performance Benefits
- **Before**: 20+ seconds (LLM + vector search + validation)
- **After**: <100ms (hash table lookups only)
- **Fallback**: Still uses LLM for unknown parts/models

## Supported Patterns
- Direct compatibility: "Is PS11739035 compatible with WDT780SAEM1?"
- Natural language: "Does this part fit my WDT780SAEM1?"
- Mixed format: "Will PS11739035 work with my dishwasher model WDT780SAEM1?"

## Limitations
- Only works for parts in CSV dataset
- Model detection based on common prefixes
- Falls back to LLM for edge cases
- No cross-brand compatibility logic (yet)
