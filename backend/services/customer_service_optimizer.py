"""
Customer service response optimizer
Provides quick responses for common questions
"""

import re
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CustomerServiceResponse:
    # what we send back for optimized responses
    immediate_response: str
    confidence: float
    response_type: str  # diagnostic informational part_lookup

class CustomerServiceOptimizer:
    # fast customer service responses for common patterns
    
    def __init__(self):
        self.diagnostic_patterns = self._build_diagnostic_patterns()
        logger.info("customer service optimizer ready")
    
    def _build_diagnostic_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Build patterns for quick symptom recognition"""
        return {
            "not_cooling": {
                "patterns": ["not cooling", "not cold", "warm", "hot", "temperature"],
                "response": "I can help with that cooling issue This is usually caused by airflow blockage dirty coils or a failing component Let me ask 1 Is the compressor running do you hear humming 2 Are the vents blocked by food 3 When did you last clean the condenser coils Based on your answers Ill recommend the specific parts you need",
                "confidence": 0.95
            },
            "ice_maker": {
                "patterns": ["ice maker", "icemaker", "no ice", "ice not working"],
                "response": "Ice maker problems are very common Let me help troubleshoot 1 Is the ice maker getting power 2 Is water reaching the refrigerator 3 Any error codes showing 4 When did it last make ice Most issues are water supply problems or the ice maker assembly needs replacement",
                "confidence": 0.95
            },
            "dishwasher_not_cleaning": {
                "patterns": ["not cleaning", "dishes dirty", "spots on dishes", "poor cleaning"],
                "response": "Poor cleaning is frustrating Lets diagnose this 1 Are the spray arms spinning freely 2 Water temperature at 120F 3 Using rinse aid 4 When did you last clean the bottom filter Most cleaning issues come from clogged spray arms or dirty filters",
                "confidence": 0.9
            },
            "not_starting": {
                "patterns": ["won't start", "not starting", "dead", "no power", "not turning on"],
                "response": "A unit that wont start usually has a few common causes Tell me 1 Any lights or sounds when you try to start it 2 Is it getting power 3 Any error codes 4 Did this happen suddenly This is typically a door latch control board or power issue",
                "confidence": 0.9
            },
            "leaking": {
                "patterns": ["leaking", "leak", "water on floor", "puddle", "dripping"],
                "response": "Water leaks need quick attention Let me help find the source 1 Where exactly is the water coming from 2 Constant leak or only during cycles 3 Any recent repairs 4 Is the door seal intact Most leaks are from worn seals or loose connections",
                "confidence": 0.85
            },
            "not_draining": {
                "patterns": ["not draining", "won't drain", "water sitting", "standing water", "water at bottom"],
                "response": "Drainage issues are common Let me help you troubleshoot 1 Is the garbage disposal clear if connected 2 Check the dishwasher filter at the bottom is it clogged 3 Are there any error codes Most drainage problems are caused by a clogged filter blocked drain hose or faulty drain pump",
                "confidence": 0.95
            },
            "categories_support": {
                "patterns": ["what categories", "what do you support", "what can you help", "categories", "support"],
                "response": "I specialize in helping with refrigerator and dishwasher parts and repairs I can help you 1 Find the right parts for your appliance 2 Troubleshoot common issues 3 Check part compatibility with your model 4 Provide installation guidance Just tell me your appliance brand model number and what issue youre experiencing",
                "confidence": 0.9
            }
        }
    
    def analyze_query_fast(self, query: str) -> CustomerServiceResponse:
        """Ultra fast query analysis and response generation"""
        start_time = time.time()
        query_lower = query.lower().strip()
        
        # check for part numbers first - but skip compatibility queries
        part_number_patterns = [r'\bPS\d+\b', r'\bW\d+\b', r'\b[A-Z]{2,}\d+[A-Z]*\b']
        found_part_numbers = []
        for pattern in part_number_patterns:
            matches = re.findall(pattern, query.upper())
            found_part_numbers.extend(matches)
        
        # Skip part number optimization for compatibility queries - let the LLM handle them
        is_compatibility_query = any(word in query_lower for word in [
            'compatible', 'compatibility', 'fit', 'work with', 'works with'
        ])
        
        if found_part_numbers and not is_compatibility_query:
            part_num = found_part_numbers[0]
            response = f"I can help you with part number {part_num} To ensure this is the right part 1 Whats your appliance model number 2 What issue are you fixing 3 Where did you find this part number Ill verify compatibility and provide installation guidance"
            return CustomerServiceResponse(
                immediate_response=response,
                confidence=0.8,
                response_type="part_lookup"
            )
        elif found_part_numbers and is_compatibility_query:
            # Lower confidence for compatibility queries so they go to full LLM pipeline
            logger.info(f"🔄 Part number found but compatibility query detected - lowering confidence to route to LLM")
            return CustomerServiceResponse(
                immediate_response="",
                confidence=0.3,  # Low confidence forces full pipeline
                response_type="compatibility_check"
            )
        
        # quick pattern matching for symptoms
        for symptom_key, symptom_data in self.diagnostic_patterns.items():
            for pattern in symptom_data["patterns"]:
                if pattern in query_lower:
                    processing_time = (time.time() - start_time) * 1000
                    logger.info(f"Fast pattern match for '{symptom_key}' in {processing_time:.1f}ms")
                    
                    return CustomerServiceResponse(
                        immediate_response=symptom_data["response"],
                        confidence=symptom_data["confidence"],
                        response_type="diagnostic"
                    )
        
        # detect appliance type for general help
        appliance = "appliance"
        if "dishwasher" in query_lower:
            appliance = "dishwasher"
        elif "refrigerator" in query_lower or "fridge" in query_lower:
            appliance = "refrigerator"
        
        # general helpful response
        response = f"Im here to help with your {appliance} issue To give you the most accurate assistance 1 What specific problem are you experiencing 2 Whats the make and model 3 When did this issue start I specialize in refrigerator and dishwasher parts so I can walk you through diagnosis and recommend exact parts"
        
        return CustomerServiceResponse(
            immediate_response=response,
            confidence=0.6,
            response_type="informational"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        return {
            "symptom_patterns": len(self.diagnostic_patterns),
            "optimizer_status": "active"
        }

# global optimizer instance
customer_service_optimizer = CustomerServiceOptimizer()
