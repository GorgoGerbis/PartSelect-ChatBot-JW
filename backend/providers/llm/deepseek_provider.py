import os
import logging
from typing import List, Dict, Any, Optional
import httpx

from ..interfaces import LLMProvider

logger = logging.getLogger(__name__)

class DeepSeekProvider(LLMProvider):
    # deepseek integration - pretty straightforward
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"
        
        if not self.api_key:
            logger.warning("no DEEPSEEK_API_KEY found - responses will be limited")
    
    def _build_system_prompt(self) -> str:
        # prompt for partselect appliance assistant
        return """You're an appliance parts assistant for PartSelect.com. Focus on refrigerator and dishwasher parts only.

CRITICAL: READ THE USER'S QUERY CAREFULLY FOR ALL DETAILS! Never ask for info the user already gave you.

Key rules:
- If user gives part number (PS11739035, WP2180353) use it immediately
- If user gives model number (WDT780SAEM1, RF23J9011SR) use it immediately  
- If user gives appliance type (dishwasher, refrigerator) use it
- If user gives brand (Whirlpool, GE, Samsung) use it

For compatibility questions:
Check appliance types first. PS11739035 is refrigerator part, WDT780SAEM1 is dishwasher = not compatible.

For installation questions:
Use search results to give specific steps, difficulty, time estimates, video links.

For troubleshooting:
Ask for model number if not provided, then suggest specific parts based on symptoms.

Examples:

User: "Is part PS11739035 compatible with my WDT780SAEM1 model?"
Response: "PS11739035 is a refrigerator ice dispenser door chute (Whirlpool) but WDT780SAEM1 is a dishwasher model. Not compatible since refrigerator parts cant be used in dishwashers. For dishwasher door issues with your WDT780SAEM1, what problem are you having?"

User: "How do I install PS11742474?"  
Response: "PS11742474 is a Whirlpool Refrigerator Bimetal Defrost Thermostat. Easy install, takes 30-60 minutes. Fixes freezer not defrosting and temp issues. Here's the video: [link]. Need specific steps for your fridge model?"

User: "My dishwasher wont drain"
Response: "Dishwasher drainage problems are usually clogged drain pump, blocked filter, or kinked drain hose. Whats your dishwasher model so I can find the right parts?"

User: "It needs to be replaced"
Response: "What part of your refrigerator or dishwasher needs replacing? Tell me your appliance model and whats broken, I'll help find the right part."

Business rules:
- Never suggest refrigerator parts for dishwashers
- Whirlpool parts often work in Kenmore/Maytag appliances  
- Ask appliance type, then model, then symptoms, then recommend parts
- Use search results data for recommendations

Check provided context for parts data (names, numbers, prices, compatibility), repair guides (steps, difficulty), and conversation history to avoid repeating questions.

Extract info from current query first, then use context data for specific helpful responses."""
                        
    async def generate_response(self, query: str, context: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """Generate AI response using DeepSeek API"""
        if not self.api_key:
            return "I'm sorry, but the AI service is currently unavailable. Please try again later or contact support."
        
        try:
            # Build messages array
            messages = [
                {"role": "system", "content": self._build_system_prompt()}
            ]
            
            # Add conversation history if provided
            if conversation_history:
                for msg in conversation_history[-10:]:  # Last 10 messages
                    if msg.get("role") in ["user", "assistant"]:
                        messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
            
            # Add current query with context
            user_message = f"User query: {query}"
            if context.strip():
                user_message += f"\n\nRelevant information found:\n{context}"
            
            # Debug: Log what we're actually sending to the LLM
            logger.info(f"🤖 Sending to DeepSeek - Query: {query[:100]}...")
            logger.info(f"🤖 Context length: {len(context)} chars")
            if context.strip():
                logger.info(f"🤖 Context preview: {context[:200]}...")
            
            messages.append({"role": "user", "content": user_message})
            
            # Call DeepSeek API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url, 
                    json=payload, 
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()
                
                result = response.json()
                return result["choices"][0]["message"]["content"]
        
        except httpx.TimeoutException:
            logger.error("DeepSeek API timeout")
            return "I apologize for the delay. The AI service is taking longer than expected. Please try again."
        
        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek API HTTP error: {e.response.status_code}")
            return "I'm experiencing some technical difficulties. Please try again in a moment."
        
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return f"I apologize, but I encountered an error processing your request. Please try rephrasing your question."
    
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """AI-powered query analysis using DeepSeek for better accuracy"""
        if not self.api_key:
            # Fallback to simple analysis if no API key
            return self._simple_analyze_query(query)
        
        try:
            # Use DeepSeek to analyze the query intelligently with enhanced compatibility detection
            analysis_prompt = f"""Analyze this user query for a PartSelect appliance parts assistant:

Query: "{query}"

Determine:
1. Is this about refrigerator or dishwasher parts/repairs? (true/false)
2. What appliance type? (refrigerator, dishwasher, or unknown)
3. What's the intent? (troubleshooting, installation, compatibility, purchase, general, meta)
4. Extract any part numbers (PS12345, W10123456, WPW10491331, etc.)
5. Extract any model numbers (WDT780SAEM1, RF23J9011SR, 106.51133211, etc.)
6. Is this a compatibility question? (asking if part X works with model Y)
7. Extract any brand names mentioned (Whirlpool, GE, Kenmore, etc.)

Respond with ONLY this JSON format:
{{
  "is_in_scope": true/false,
  "appliance_type": "refrigerator/dishwasher/unknown",
  "intent": "troubleshooting/installation/compatibility/purchase/general/meta",
  "part_numbers": ["PS12345"],
  "model_numbers": ["WDT780SAEM1"],
  "brands": ["Whirlpool"],
  "is_compatibility_query": true/false,
  "confidence": 0.9
}}"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": analysis_prompt}],
                "temperature": 0.1,  # Low temperature for consistent analysis
                "max_tokens": 200
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url, 
                    json=payload, 
                    headers=headers,
                    timeout=10.0  # Fast timeout for analysis
                )
                response.raise_for_status()
                
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"].strip()
                
                # Parse JSON response
                import json
                try:
                    analysis = json.loads(ai_response)
                    
                    # Convert to expected format with enhanced fields
                    return {
                        "intent": analysis.get("intent", "general"),
                        "appliance_types": [analysis.get("appliance_type")] if analysis.get("appliance_type") != "unknown" else [],
                        "part_numbers": analysis.get("part_numbers", []),
                        "model_numbers": analysis.get("model_numbers", []),
                        "brands": analysis.get("brands", []),
                        "is_compatibility_query": analysis.get("is_compatibility_query", False),
                        "is_in_scope": analysis.get("is_in_scope", False),
                        "confidence": analysis.get("confidence", 0.5),
                        "needs_search": analysis.get("intent") in ["general", "troubleshooting", "compatibility"] or len(analysis.get("part_numbers", [])) > 0
                    }
                    
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown code blocks
                    import re
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
                    if json_match:
                        try:
                            analysis = json.loads(json_match.group(1))
                            return {
                                "intent": analysis.get("intent", "general"),
                                "part_numbers": analysis.get("part_numbers", []),
                                "model_numbers": analysis.get("model_numbers", []),
                                "brands": analysis.get("brands", []),
                                "is_compatibility_query": analysis.get("is_compatibility_query", False),
                                "is_in_scope": analysis.get("is_in_scope", False),
                                "confidence": analysis.get("confidence", 0.5),
                                "needs_search": analysis.get("intent") in ["general", "troubleshooting", "compatibility"] or len(analysis.get("part_numbers", [])) > 0
                            }
                        except json.JSONDecodeError:
                            pass
                    
                    logger.warning(f"Failed to parse AI analysis: {ai_response}")
                    return self._simple_analyze_query(query)
                    
        except Exception as e:
            logger.error(f"AI query analysis failed: {e}")
            return self._simple_analyze_query(query)
    
    def _simple_analyze_query(self, query: str) -> Dict[str, Any]:
        """Fallback simple query analysis"""
        query_lower = query.lower()
        
        # Detect part/model numbers
        import re
        part_numbers = re.findall(r'\b(PS\d+|W\d+|[A-Z]{2}\d+)\b', query.upper())
        model_numbers = re.findall(r'\b[A-Z]{2,}[\d\w]{4,}\b', query.upper())
        
        # Simple keyword detection
        has_appliance_words = any(word in query_lower for word in [
            'refrigerator', 'fridge', 'dishwasher', 'appliance', 'part',
            'whirlpool', 'ge', 'bosch', 'maytag', 'samsung', 'lg',
            'drain', 'leak', 'clean', 'repair', 'fix', 'broken', 'install'
        ])
        
        is_in_scope = has_appliance_words or len(part_numbers) > 0 or len(model_numbers) > 0
        
        return {
            "intent": "general",
            "appliance_types": ["dishwasher"] if "dishwasher" in query_lower else ["refrigerator"] if any(w in query_lower for w in ['fridge', 'refrigerator']) else [],
            "part_numbers": part_numbers,
            "model_numbers": model_numbers,
            "is_in_scope": is_in_scope,
            "confidence": 0.7 if is_in_scope else 0.3,
            "needs_search": True
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics"""
        return {
            "provider_type": "deepseek",
            "model": self.model,
            "api_configured": bool(self.api_key),
            "api_url": self.api_url
        }
    
    async def validate_response(self, query: str, response: str, context: str = "") -> Dict[str, Any]:
        """Validate response quality and accuracy for PartSelect queries"""
        if not self.api_key:
            # Simple validation if no API
            return {
                "is_appropriate": len(response.strip()) > 20,
                "stays_in_scope": "refrigerator" in response.lower() or "dishwasher" in response.lower(),
                "hallucination": False,
                "feedback": None
            }
        
        try:
            # FIXME: This validation prompt could probably be shorter
            # but it works pretty well for catching bad responses
            validation_prompt = f"""You are a response validator for a PartSelect appliance parts assistant.

Original Query: "{query}"
Retrieved Context: "{context[:500]}..."
Generated Response: "{response}"

Evaluate the response on these criteria:
1. Is it appropriate for a parts assistant? (professional, helpful tone)
2. Does it stay within refrigerator/dishwasher parts scope?
3. Does it hallucinate information not in the context?
4. Does it use specific parts/prices from the context when available?

Respond with ONLY this JSON:
{{
  "is_appropriate": true/false,
  "stays_in_scope": true/false,
  "hallucination": true/false,
  "uses_context_data": true/false,
  "feedback": "specific feedback for improvement or null"
}}"""

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": validation_prompt}],
                "temperature": 0.1,
                "max_tokens": 200
            }
            
            async with httpx.AsyncClient() as client:
                response_obj = await client.post(
                    self.api_url, 
                    json=payload, 
                    headers=headers,
                    timeout=10.0
                )
                response_obj.raise_for_status()
                
                result = response_obj.json()
                ai_response = result["choices"][0]["message"]["content"].strip()
                
                # Parse JSON response - handle markdown wrapping
                import json  # yeah I know this should be at the top but whatever
                try:
                    # Strip markdown code blocks if present
                    json_text = ai_response
                    if "```json" in ai_response:
                        json_text = ai_response.split("```json")[1].split("```")[0].strip()
                    elif "```" in ai_response:
                        json_text = ai_response.split("```")[1].strip()
                    
                    validation = json.loads(json_text)
                    return {
                        "is_appropriate": validation.get("is_appropriate", True),
                        "stays_in_scope": validation.get("stays_in_scope", True),
                        "hallucination": validation.get("hallucination", False),
                        "uses_context_data": validation.get("uses_context_data", True),
                        "feedback": validation.get("feedback")
                    }
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse validation response: {ai_response}")
                    return {
                        "is_appropriate": True,
                        "stays_in_scope": True,
                        "hallucination": False,
                        "uses_context_data": True,
                        "feedback": None
                    }
                    
        except Exception as e:
            logger.error(f"Response validation failed: {e}")
            return {
                "is_appropriate": True,
                "stays_in_scope": True,
                "hallucination": False,
                "uses_context_data": True,
                "feedback": None
            }
