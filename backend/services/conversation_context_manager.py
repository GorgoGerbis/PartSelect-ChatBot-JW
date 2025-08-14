"""
Context manager for tracking conversation state across messages

The chat was losing track of what users said earlier so this keeps track of
- What appliance theyre working with
- Model numbers they mentioned  
- What problems theyre having
- Parts theyve talked about

Basically prevents the bot from asking what appliance when they already said dishwasher
"""

import re
import logging
import json
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class ConversationStage(Enum):
    """Track where we are in the conversation flow"""
    INITIAL = "initial"
    GATHERING_INFO = "gathering_info"
    DIAGNOSIS = "diagnosis"
    PART_SELECTION = "part_selection"
    COMPATIBILITY_CHECK = "compatibility_check"
    INSTALLATION = "installation"
    COMPLETE = "complete"

@dataclass
class ConversationContext:
    """
    Structured conversation context that builds over time
    This is what gets passed to the LLM for better responses
    """
    # core appliance information
    appliance_type: Optional[str] = None
    brand: Optional[str] = None
    model_number: Optional[str] = None
    series: Optional[str] = None
    
    # problem description
    symptoms: List[str] = field(default_factory=list)
    problem_description: Optional[str] = None
    
    # parts mentioned in conversation
    mentioned_parts: List[str] = field(default_factory=list)
    confirmed_parts: List[str] = field(default_factory=list)
    
    # conversation flow
    stage: ConversationStage = ConversationStage.INITIAL
    confidence_level: float = 0.0
    missing_info: List[str] = field(default_factory=list)
    
    # metadata
    conversation_id: str = ""
    last_updated: Optional[datetime] = None
    message_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['stage'] = self.stage.value
        result['last_updated'] = self.last_updated.isoformat() if self.last_updated else None
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """Create from dictionary"""
        if 'stage' in data and isinstance(data['stage'], str):
            data['stage'] = ConversationStage(data['stage'])
        if 'last_updated' in data and isinstance(data['last_updated'], str):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)

class ConversationContextManager:
    """
    Manages conversation context extraction and progressive information building
    This is the intelligence that decides whats important vs noise
    """
    
    def __init__(self):
        # pattern matching for information extraction
        self.part_number_patterns = [
            r'\b(PS\d{8,})\b',  # PartSelect numbers PS11752778
            r'\b(WP[A-Z]?\d{8,})\b',  # Whirlpool WPW10491331
            r'\b(W\d{8,})\b',  # W10123456
            r'\b([A-Z]{2,3}\d{6,})\b'  # General GE1234567
        ]
        
        self.model_number_patterns = [
            r'\b([A-Z]{2,}[\d\w]{4,})\b',  # WDT780SAEM1 RF23J9011SR
            r'\b(\d{3}\.\d{8,})\b',  # Kenmore 106.51133211
            r'\b([A-Z]+\d+[A-Z]+\d*)\b'   # Mixed WDT780SAEM1
        ]
        
        # brand detection patterns
        self.brand_patterns = {
            'whirlpool': r'\b(whirlpool|WP[A-Z]?\d+)\b',
            'ge': r'\b(ge|general electric)\b',
            'samsung': r'\b(samsung)\b',
            'lg': r'\b(lg)\b',
            'bosch': r'\b(bosch)\b',
            'kitchenaid': r'\b(kitchenaid|kitchen aid)\b',
            'maytag': r'\b(maytag)\b',
            'kenmore': r'\b(kenmore|106\.)\b',
            'frigidaire': r'\b(frigidaire)\b',
            'admiral': r'\b(admiral)\b',
            'amana': r'\b(amana)\b'
        }
        
        # appliance type detection
        self.appliance_patterns = {
            'refrigerator': r'\b(refrigerator|fridge|ice maker|freezer)\b',
            'dishwasher': r'\b(dishwasher|dish washer)\b'
        }
        
        # symptom problem detection
        self.symptom_patterns = {
            'not_cooling': r'\b(not cooling|warm|too hot|temperature)\b',
            'not_draining': r'\b(not draining|won\'t drain|water standing|pooling)\b',
            'leaking': r'\b(leaking|leak|water on floor)\b',
            'noisy': r'\b(noisy|loud|grinding|squealing|banging)\b',
            'not_starting': r'\b(not starting|won\'t start|dead|no power)\b',
            'not_cleaning': r'\b(not cleaning|dirty dishes|spots|film)\b',
            'ice_maker_issues': r'\b(ice maker|no ice|ice not dispensing)\b',
            'door_issues': r'\b(door won\'t close|door seal|latch)\b'
        }
        
        # context storage
        self.contexts: Dict[str, ConversationContext] = {}
    
    def extract_information(self, message: str) -> Dict[str, Any]:
        """
        Extract important information from a message
        This is the core intelligence deciding what matters
        """
        message_lower = message.lower()
        extracted = {
            'part_numbers': [],
            'model_numbers': [],
            'brands': [],
            'appliance_types': [],
            'symptoms': [],
            'confidence': 0.0
        }
        
        # extract part numbers
        for pattern in self.part_number_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            extracted['part_numbers'].extend(matches)
        
        # extract model numbers
        for pattern in self.model_number_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE)
            # filter out part numbers that might match model patterns
            for match in matches:
                if not any(re.match(pp, match, re.IGNORECASE) for pp in self.part_number_patterns):
                    extracted['model_numbers'].append(match)
        
        # extract brands
        for brand, pattern in self.brand_patterns.items():
            if re.search(pattern, message_lower):
                extracted['brands'].append(brand)
        
        # extract appliance types
        for appliance, pattern in self.appliance_patterns.items():
            if re.search(pattern, message_lower):
                extracted['appliance_types'].append(appliance)
        
        # extract symptoms
        for symptom, pattern in self.symptom_patterns.items():
            if re.search(pattern, message_lower):
                extracted['symptoms'].append(symptom)
        
        # calculate confidence based on how much useful info we found
        info_count = (len(extracted['part_numbers']) + 
                     len(extracted['model_numbers']) + 
                     len(extracted['brands']) + 
                     len(extracted['appliance_types']) + 
                     len(extracted['symptoms']))
        
        extracted['confidence'] = min(info_count * 0.2, 1.0)
        
        return extracted
    
    def update_context(self, conversation_id: str, message: str, role: str = "user") -> ConversationContext:
        """
        Update conversation context with new message
        This builds information progressively across messages
        """
        # get or create context
        if conversation_id not in self.contexts:
            self.contexts[conversation_id] = ConversationContext(conversation_id=conversation_id)
        
        context = self.contexts[conversation_id]
        context.message_count += 1
        context.last_updated = datetime.now()
        
        # only extract from user messages not assistant responses
        if role != "user":
            return context
        
        # extract information from the message
        extracted = self.extract_information(message)
        
        # update context with new information
        self._merge_extracted_info(context, extracted, message)
        
        # update conversation stage and confidence
        self._update_stage_and_confidence(context)
        
        # determine what information is still missing
        self._update_missing_info(context)
        
        logger.info(f"Updated context for {conversation_id}: stage={context.stage.value}, confidence={context.confidence_level:.2f}")
        
        return context
    
    def _merge_extracted_info(self, context: ConversationContext, extracted: Dict[str, Any], message: str):
        """Merge extracted information into context, avoiding duplicates"""
        
        # update appliance type take the first one found
        if extracted['appliance_types'] and not context.appliance_type:
            context.appliance_type = extracted['appliance_types'][0]
        
        # update brand take the first one found
        if extracted['brands'] and not context.brand:
            context.brand = extracted['brands'][0].title()
        
        # update model number take the first one found
        if extracted['model_numbers'] and not context.model_number:
            context.model_number = extracted['model_numbers'][0]
            # extract series from model number eg WDT from WDT780SAEM1
            series_match = re.match(r'^([A-Z]{2,4})', context.model_number)
            if series_match:
                context.series = series_match.group(1)
        
        # add new part numbers
        for part in extracted['part_numbers']:
            if part not in context.mentioned_parts:
                context.mentioned_parts.append(part)
        
        # add new symptoms
        for symptom in extracted['symptoms']:
            if symptom not in context.symptoms:
                context.symptoms.append(symptom)
        
        # update problem description with the most descriptive message
        if len(message) > 20 and (not context.problem_description or len(message) > len(context.problem_description)):
            context.problem_description = message
    
    def _update_stage_and_confidence(self, context: ConversationContext):
        """Update conversation stage based on available information"""
        
        # Calculate confidence based on completeness
        info_score = 0
        if context.appliance_type:
            info_score += 0.3
        if context.brand:
            info_score += 0.2
        if context.model_number:
            info_score += 0.3
        if context.symptoms:
            info_score += 0.2
        
        context.confidence_level = info_score
        
        # Update stage based on available information
        if context.mentioned_parts and context.model_number:
            context.stage = ConversationStage.COMPATIBILITY_CHECK
        elif context.mentioned_parts:
            context.stage = ConversationStage.PART_SELECTION
        elif context.appliance_type and context.symptoms:
            context.stage = ConversationStage.DIAGNOSIS
        elif context.appliance_type or context.brand or context.model_number:
            context.stage = ConversationStage.GATHERING_INFO
        else:
            context.stage = ConversationStage.INITIAL
    
    def _update_missing_info(self, context: ConversationContext):
        """Determine what information is still needed"""
        missing = []
        
        if not context.appliance_type:
            missing.append("appliance_type")
        if not context.model_number and context.stage != ConversationStage.INITIAL:
            missing.append("model_number")
        if not context.symptoms and not context.mentioned_parts:
            missing.append("problem_description")
        
        context.missing_info = missing
    
    def get_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get current context for a conversation"""
        return self.contexts.get(conversation_id)
    
    def get_structured_context_for_llm(self, conversation_id: str) -> str:
        """
        Get formatted context string for LLM prompts.
        This provides the LLM with structured, important information.
        """
        context = self.get_context(conversation_id)
        if not context:
            return "No conversation context available."
        
        context_parts = []
        context_parts.append("=== CONVERSATION CONTEXT ===")
        
        # core appliance info
        if context.appliance_type or context.brand or context.model_number:
            context_parts.append("APPLIANCE INFORMATION:")
            if context.appliance_type:
                context_parts.append(f"  - Type: {context.appliance_type.title()}")
            if context.brand:
                context_parts.append(f"  - Brand: {context.brand}")
            if context.model_number:
                context_parts.append(f"  - Model: {context.model_number}")
            if context.series:
                context_parts.append(f"  - Series: {context.series}")
        
        # Problem information
        if context.symptoms or context.problem_description:
            context_parts.append("\nPROBLEM INFORMATION:")
            if context.symptoms:
                context_parts.append(f"  - Symptoms: {', '.join(context.symptoms)}")
            if context.problem_description:
                context_parts.append(f"  - Description: {context.problem_description}")
        
        # Parts mentioned
        if context.mentioned_parts:
            context_parts.append(f"\nPARTS MENTIONED: {', '.join(context.mentioned_parts)}")
        
        # Conversation stage and guidance
        context_parts.append(f"\nCONVERSATION STAGE: {context.stage.value.replace('_', ' ').title()}")
        context_parts.append(f"INFORMATION COMPLETENESS: {context.confidence_level:.0%}")
        
        if context.missing_info:
            missing_readable = {
                'appliance_type': 'appliance type (refrigerator/dishwasher)',
                'model_number': 'specific model number',
                'problem_description': 'description of the problem'
            }
            missing_list = [missing_readable.get(info, info) for info in context.missing_info]
            context_parts.append(f"STILL NEEDED: {', '.join(missing_list)}")
        
        context_parts.append("=== END CONTEXT ===\n")
        
        return "\n".join(context_parts)
    
    def should_request_more_info(self, conversation_id: str) -> bool:
        """Determine if we should ask for more information"""
        context = self.get_context(conversation_id)
        if not context:
            return True
        
        # Request more info if confidence is low and we're missing key information
        return context.confidence_level < 0.6 and len(context.missing_info) > 0
    
    def get_suggested_questions(self, conversation_id: str) -> List[str]:
        """Get suggested follow-up questions based on missing information"""
        context = self.get_context(conversation_id)
        if not context:
            return ["Could you tell me what type of appliance you're working with?"]
        
        questions = []
        
        if 'appliance_type' in context.missing_info:
            questions.append("Is this for a refrigerator or dishwasher?")
        
        if 'model_number' in context.missing_info and context.appliance_type:
            questions.append(f"What's the model number of your {context.appliance_type}? You can usually find it on a sticker inside the appliance.")
        
        if 'problem_description' in context.missing_info:
            questions.append("What specific problem are you experiencing?")
        
        # Stage-specific questions
        if context.stage == ConversationStage.GATHERING_INFO and context.appliance_type and not context.symptoms:
            questions.append(f"What issue are you having with your {context.appliance_type}?")
        
        return questions
    
    def clear_context(self, conversation_id: str):
        """Clear context for a conversation"""
        if conversation_id in self.contexts:
            del self.contexts[conversation_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about context management"""
        return {
            "active_conversations": len(self.contexts),
            "total_messages_processed": sum(ctx.message_count for ctx in self.contexts.values()),
            "conversation_stages": {stage.value: sum(1 for ctx in self.contexts.values() if ctx.stage == stage) for stage in ConversationStage}
        }

# Global instance
conversation_context_manager = ConversationContextManager()
