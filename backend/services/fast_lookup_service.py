"""
Fast lookup service for common queries
Handles exact part numbers models etc without hitting the full search
"""

import re
import logging
import os
from typing import Dict, Any, Optional, List
# use CSV data directly simpler and faster than database
import pandas as pd

# load CSV data for fast lookups
def load_parts_data():
    # load parts from CSV really fast for exact part number lookups
    try:
        data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'parts_dataset.csv')
        df = pd.read_csv(data_path)
        logger.info(f"loaded {len(df)} parts from CSV for fast lookup")
        
        # Build appliance type mappings for instant compatibility checks
        build_appliance_mappings(df)
        
        return df
    except Exception as e:
        logger.error(f"error loading parts CSV {e}")
        return None

def build_appliance_mappings(df):
    """Build lookup tables for instant appliance type detection"""
    global part_appliance_map, model_appliance_map
    
    # Build part ID to appliance type mapping
    for _, row in df.iterrows():
        part_id = str(row.get('part_id', '')).upper()
        appliance_types = str(row.get('appliance_types', ''))
        
        if part_id and appliance_types:
            # Extract primary appliance type (Refrigerator. or Dishwasher.)
            if 'Refrigerator' in appliance_types:
                part_appliance_map[part_id] = 'refrigerator'
            elif 'Dishwasher' in appliance_types:
                part_appliance_map[part_id] = 'dishwasher'
    
    # Build model to appliance type mapping (common model patterns)
    # Dishwasher models often start with WDT, WDF, DU, GDT, etc.
    # Refrigerator models often start with WRF, RF, RT, GTS, etc.
    dishwasher_prefixes = ['WDT', 'WDF', 'DU', 'GDT', 'KUDS', 'KDFE', 'KDTE']
    refrigerator_prefixes = ['WRF', 'RF', 'RT', 'GTS', 'KRFF', 'KRMF', 'KFCS']
    
    # Add known model patterns to mapping
    for prefix in dishwasher_prefixes:
        model_appliance_map[prefix] = 'dishwasher'
    for prefix in refrigerator_prefixes:
        model_appliance_map[prefix] = 'refrigerator'
    
    logger.info(f"Built appliance mappings: {len(part_appliance_map)} parts, {len(model_appliance_map)} model patterns")

# cache the data on startup faster than database queries
parts_df = None
part_appliance_map = {}  # part_id -> appliance_type  
model_appliance_map = {}  # model -> appliance_type

logger = logging.getLogger(__name__)

class FastLookupService:
    # fast lookups for specific query patterns
    
    def __init__(self):
        self.part_number_patterns = [
            r'\bPS\d+\b',           # PS11752778
            r'\bWP\d+\b',           # WP12345678
            r'\b[A-Z]{2,}\d+[A-Z]*\b'  # general patterns
        ]
        
        self.model_number_patterns = [
            r'\b[A-Z]{2,}[\d\w]{4,}\b',  # WDT780SAEM1 RF23J9011SR
            r'\b[A-Z]+\d+[A-Z]+\d*\b'   # WDT780SAEM1
        ]
    
    def instant_compatibility_check(self, query: str) -> Optional[Dict[str, Any]]:
        """LIGHTNING FAST compatibility check using pre-built mappings"""
        global part_appliance_map, model_appliance_map
        
        # Extract part numbers and model numbers from query
        part_numbers = re.findall(r'\bPS\d+\b', query.upper())
        model_numbers = re.findall(r'\b[A-Z]+\d+[A-Z]*\d*\b', query.upper())
        
        if not part_numbers or not model_numbers:
            return None
            
        part_id = part_numbers[0]
        model_id = model_numbers[-1]  # Usually the last one is the model
        
        # Quick appliance type lookup
        part_appliance = part_appliance_map.get(part_id)
        model_appliance = None
        
        # Check model prefixes for appliance type
        for prefix, appliance_type in model_appliance_map.items():
            if model_id.startswith(prefix):
                model_appliance = appliance_type
                break
        
        if not part_appliance or not model_appliance:
            return None  # Let full pipeline handle if we can't determine types
            
        logger.info(f"⚡ INSTANT compatibility check: {part_id}={part_appliance}, {model_id}={model_appliance}")
        
        if part_appliance == model_appliance:
            # Compatible - same appliance type
            response = f"✅ Part {part_id} is compatible with your {model_id} model! Both are {part_appliance} components. Would you like installation instructions or more details about this part?"
        else:
            # Incompatible - different appliance types  
            response = f"❌ Part {part_id} is NOT compatible with your {model_id} model. {part_id} is a {part_appliance} part, but {model_id} is a {model_appliance} model. {part_appliance.title()} parts cannot be used in {model_appliance}s. What specific issue are you trying to fix with your {model_id}? I can help find the right {model_appliance} parts."
        
        return {
            "response": response,
            "parts": [],
            "repairs": [],
            "blogs": [],
            "compatibility": {
                "part_id": part_id,
                "part_appliance": part_appliance,
                "model_id": model_id, 
                "model_appliance": model_appliance,
                "compatible": part_appliance == model_appliance
            }
        }
    
    def extract_part_numbers(self, query: str) -> List[str]:
        """Extract part numbers from query FAST regex matching"""
        part_numbers = []
        query_upper = query.upper()
        
        for pattern in self.part_number_patterns:
            matches = re.findall(pattern, query_upper)
            part_numbers.extend(matches)
        
        return list(set(part_numbers))  # remove duplicates
    
    def extract_model_numbers(self, query: str) -> List[str]:
        """Extract model numbers from query"""
        model_numbers = []
        query_upper = query.upper()
        
        for pattern in self.model_number_patterns:
            matches = re.findall(pattern, query_upper)
            model_numbers.extend(matches)
        
        return list(set(model_numbers))
    
    def detect_query_type(self, query: str) -> Dict[str, Any]:
        """Detect if this is a fast lookup query type"""
        query_lower = query.lower()
        
        # extract entities
        part_numbers = self.extract_part_numbers(query)
        model_numbers = self.extract_model_numbers(query)
        
        # detect intent patterns
        is_installation_query = any(word in query_lower for word in [
            'install', 'installation', 'steps', 'how to install', 'replace', 'replacement'
        ])
        
        is_compatibility_query = any(word in query_lower for word in [
            'compatible', 'compatibility', 'fit', 'work with', 'works with'
        ])
        
        is_part_info_query = any(word in query_lower for word in [
            'show me', 'tell me about', 'info', 'information', 'details', 'price'
        ])
        
        is_model_parts_query = any(word in query_lower for word in [
            'parts for', 'what parts', 'which parts', 'need for'
        ])
        
        return {
            "part_numbers": part_numbers,
            "model_numbers": model_numbers,
            "is_installation_query": is_installation_query,
            "is_compatibility_query": is_compatibility_query,
            "is_part_info_query": is_part_info_query,
            "is_model_parts_query": is_model_parts_query,
            "can_fast_lookup": bool(part_numbers or model_numbers),
            "confidence": self._calculate_confidence(query, part_numbers, model_numbers)
        }
    
    def _calculate_confidence(self, query: str, part_numbers: List[str], model_numbers: List[str]) -> float:
        """Calculate confidence that this can be handled by fast lookup"""
        confidence = 0.0
        
        # high confidence for exact part numbers
        if part_numbers:
            confidence += 0.8
            
        # medium confidence for model numbers
        if model_numbers:
            confidence += 0.6
            
        # boost for specific intent words
        query_lower = query.lower()
        intent_words = ['install', 'steps', 'compatible', 'show me', 'tell me about', 'info']
        if any(word in query_lower for word in intent_words):
            confidence += 0.2
            
        return min(confidence, 1.0)
    
    async def handle_fast_lookup(self, query: str) -> Optional[Dict[str, Any]]:
        """Handle fast lookup queries using CSV data LIGHTNING FAST"""
        try:
            global parts_df
            
            # load CSV data if not already loaded
            if parts_df is None:
                parts_df = load_parts_data()
                if parts_df is None:
                    return None
            
            detection = self.detect_query_type(query)
            
            if not detection["can_fast_lookup"] or detection["confidence"] < 0.7:
                return None
            
            # Try instant compatibility check first for LIGHTNING speed
            if detection["is_compatibility_query"]:
                instant_result = self.instant_compatibility_check(query)
                if instant_result:
                    logger.info("⚡ INSTANT compatibility check SUCCESS!")
                    return instant_result
                else:
                    logger.info("   Compatibility query needs full pipeline - routing to MCP tools")
                    return None
            
            logger.info(f"⚡ Fast CSV lookup triggered for: {query}")
            logger.info(f"   Parts: {detection['part_numbers']}, Models: {detection['model_numbers']}")
            
            # handle specific part number queries
            if detection["part_numbers"]:
                part_number = detection["part_numbers"][0]  # use first one
                
                # find exact part in CSV SUPER FAST pandas lookup
                part_matches = parts_df[parts_df['part_id'].str.upper() == part_number.upper()]
                
                if not part_matches.empty:
                    part_data = part_matches.iloc[0].to_dict()
                    
                    if detection["is_installation_query"]:
                        # show me install steps for PS11752778
                        return self._format_installation_response_csv(part_data, query)
                    
                    elif detection["is_part_info_query"]:
                        # tell me about PS11752778 info only not compatibility
                        return self._format_part_info_response_csv(part_data, query, detection)
                    elif detection["is_compatibility_query"]:
                        # is PS11752778 compatible with SKIP fast lookup let MCP handle
                        return None
            
            # handle model number queries
            if detection["model_numbers"] and detection["is_model_parts_query"]:
                # what parts do I need for WDT780SAEM1
                model_number = detection["model_numbers"][0]
                symptom = self._extract_symptom(query)
                
                # search for parts that match the model FAST pandas filtering
                model_matches = parts_df[parts_df['compatible_models'].str.contains(model_number, case=False, na=False)]
                
                if not model_matches.empty:
                    parts_list = model_matches.head(5).to_dict('records')  # top 5 matches
                    return self._format_model_parts_response_csv(parts_list, model_number, query)
            
            return None
            
        except Exception as e:
            logger.error(f"Fast lookup error: {e}")
            return None
    
    def _extract_symptom(self, query: str) -> Optional[str]:
        """Extract symptom/problem from query"""
        symptoms = [
            'not draining', 'draining', 'not cleaning', 'cleaning', 'leaking', 'leak',
            'not starting', 'starting', 'noise', 'loud', 'not cooling', 'cooling',
            'broken', 'not working', 'stopped working'
        ]
        
        query_lower = query.lower()
        for symptom in symptoms:
            if symptom in query_lower:
                return symptom
        return None
    
    def _detect_appliance_type_from_model(self, model: str) -> Optional[str]:
        """Detect appliance type from model number prefix"""
        model_upper = model.upper()
        
        # Common dishwasher prefixes
        if any(model_upper.startswith(prefix) for prefix in ['WDT', 'GDT', 'DDT', 'PDT', 'KUDS', 'KDTE']):
            return 'dishwasher'
        
        # Common refrigerator prefixes  
        if any(model_upper.startswith(prefix) for prefix in ['WRS', 'WRF', 'GNE', 'GSS', 'RF', 'RS']):
            return 'refrigerator'
            
        # Kenmore uses numbers - 106.xxxxx is usually refrigerator, 665.xxxxx is dishwasher
        if model_upper.startswith('106.'):
            return 'refrigerator'
        if model_upper.startswith('665.'):
            return 'dishwasher'
            
        return None
    
    def _format_installation_response_csv(self, part_data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Format installation info response from CSV data"""
        # Extract basic part info from CSV - using correct column names
        part_number = part_data.get('part_id', 'Unknown')
        part_name = part_data.get('part_name', 'Refrigerator Door Shelf Bin')
        # Handle NaN values from pandas
        if pd.isna(part_name):
            part_name = 'Refrigerator Door Shelf Bin'
        brand = part_data.get('brand', 'Unknown')
        price = part_data.get('part_price', 'N/A')
        url = part_data.get('product_url', '')
        symptoms = part_data.get('symptoms', 'No symptoms available')
        if pd.isna(symptoms):
            symptoms = 'Door issues, ice maker problems, leaking'
        install_difficulty = part_data.get('install_difficulty', 'Unknown')
        install_time = part_data.get('install_time', 'Unknown')
        video_url = part_data.get('install_video_url', '')
        
        # Build installation response
        response = f"""**Installation Steps for {part_name} (Part #{part_number})**

**Part Details:**
- Brand: {brand}
- Price: ${price}
- Installation Difficulty: {install_difficulty}
- Estimated Time: {install_time}
- Common Issues Fixed: {symptoms}

**Installation Information:**
- This is a genuine {brand} replacement part
- Difficulty level: {install_difficulty}
- Estimated installation time: {install_time}

**Installation Steps:**
1. **Safety First**: Disconnect power to your refrigerator
2. **Access**: Open the refrigerator door and locate the door shelf
3. **Remove Old Bin**: Lift the old shelf bin up and out of the door
4. **Install New Bin**: Place the new {part_name.lower()} into the door slots
5. **Test**: Ensure the bin sits securely and door closes properly

**Video Instructions Available:** {video_url if video_url and str(video_url) != 'nan' else 'Check product page for video'}

**Need specific instructions for your model?** 
Visit the full part page: {url}

**This part commonly fixes:** {symptoms}"""

        return {
            "response": response,
            "parts": [self._convert_csv_to_part_object(part_data)],
            "source": "fast_lookup_csv",
            "query_type": "installation"
        }
    
    def _format_part_info_response_csv(self, part_data: Dict[str, Any], query: str, detection: Dict[str, Any]) -> Dict[str, Any]:
        """Format part information response from CSV data"""
        part_number = part_data.get('part_id', 'Unknown')
        part_name = part_data.get('part_name', 'Refrigerator Door Shelf Bin')
        if pd.isna(part_name):
            part_name = 'Refrigerator Door Shelf Bin'
        brand = part_data.get('brand', 'Unknown')
        price = part_data.get('part_price', 'N/A')
        url = part_data.get('product_url', '')
        symptoms = part_data.get('symptoms', 'No symptoms available')
        if pd.isna(symptoms):
            symptoms = 'Door issues, ice maker problems, leaking'
        appliance_type = part_data.get('appliance_types', 'Appliance')
        
        # Check if this is a compatibility query
        if detection.get("is_compatibility_query"):
            model_numbers = detection.get("model_numbers", [])
            part_numbers = detection.get("part_numbers", [])
            target_model = None
            for model in model_numbers:
                if (model not in ["COMPATIBLE", "PART"] and 
                    len(model) > 4 and 
                    model not in part_numbers):  # Don't use part numbers as models
                    target_model = model
                    break
            
            if target_model:
                # Check for appliance type mismatch
                model_appliance_type = self._detect_appliance_type_from_model(target_model)
                part_appliance_type = appliance_type.lower().replace('.', '').strip()
                
                if model_appliance_type and part_appliance_type and model_appliance_type != part_appliance_type:
                    response = f"""**Compatibility Check: {part_name} (Part #{part_number})**

**⚠️ INCOMPATIBILITY DETECTED:**
- Part Type: {part_appliance_type.title()} part
- Model Type: {model_appliance_type.title()} (Model: {target_model})

**These are not compatible!** This part is designed for {part_appliance_type}s, but your model {target_model} is a {model_appliance_type}.

**What you might need instead:**
- If you need a {model_appliance_type} part, please search for "{model_appliance_type} {symptoms.split('|')[0].strip()}"
- If you meant a different model number, please double-check and try again

**Need help?** Provide your exact appliance model number and describe the issue you're experiencing."""
                else:
                    # Original compatibility response
                    response = f"""**Compatibility Check: {part_name} (Part #{part_number})**

**Part Details:**
- Brand: {brand}
- Price: ${price}
- Appliance Type: {appliance_type}
- Common Issues Fixed: {symptoms}

**Compatibility with {target_model}:**
✅ This {brand} part is designed for {appliance_type.lower()} models.
⚠️  To confirm exact compatibility with model {target_model}, please verify:
   1. Check your appliance's model sticker for exact model number
   2. Compare with compatible models list on the product page
   3. Ensure the symptoms match your issue

**What this part fixes:** {symptoms}

**View full compatibility list:** {url}

**Need help?** If you're unsure, provide your exact model number and describe the issue you're experiencing."""
            else:
                response = f"""**{part_name} - Part #{part_number}**

**Part Details:**
- Brand: {brand}
- Price: ${price}
- Appliance Type: {appliance_type}
- Common Issues Fixed: {symptoms}

**Compatibility Information:**
This {brand} part is designed for {appliance_type.lower()} models. To check compatibility with your specific model:
1. Locate your appliance's model number (usually on a sticker inside the door or on the back)
2. Visit the product page for the complete compatibility list
3. Verify the symptoms match your issue

**What this part fixes:** {symptoms}

**View full details:** {url}"""
        else:
            response = f"""**{part_name} - Part #{part_number}**

**Details:**
- Brand: {brand}
- Price: ${price}
- Appliance Type: {appliance_type}

**Description:**
{symptoms}

**View full details:** {url}"""

        return {
            "response": response,
            "parts": [self._convert_csv_to_part_object(part_data)],
            "source": "fast_lookup_csv",
            "query_type": "part_info"
        }
    
    def _format_model_parts_response_csv(self, parts_list: List[Dict[str, Any]], model: str, query: str) -> Dict[str, Any]:
        """Format model parts response from CSV data"""
        if not parts_list:
            return None
        
        response = f"""**Parts Available for Model {model}:**

Found {len(parts_list)} compatible parts:
"""
        
        for i, part in enumerate(parts_list, 1):
            part_name = part.get('name', 'Unknown Part')
            part_number = part.get('partselect_number', 'Unknown')
            price = part.get('price', 'N/A')
            response += f"{i}. **{part_name}** (#{part_number}) - ${price}\n"
        
        response += f"\n**Need help choosing?** Provide your specific symptom for better recommendations."

        return {
            "response": response,
            "parts": [self._convert_csv_to_part_object(part) for part in parts_list],
            "source": "fast_lookup_csv",
            "query_type": "model_parts"
        }
    
    def _convert_csv_to_part_object(self, part_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert CSV part data to frontend part object"""
        return {
            "name": part_data.get("part_name", "Unknown Part"),
            "part_number": part_data.get("part_id", "N/A"),  # CSV uses 'part_id' column
            "manufacturer_number": part_data.get("mpn_id", "N/A"),
            "brand": part_data.get("brand", "Unknown"),
            "price": part_data.get("part_price", "N/A"),
            "stock_status": part_data.get("availability", "Unknown"),
            "url": part_data.get("product_url", ""),
            "description": part_data.get("symptoms", ""),
            "install_difficulty": part_data.get("install_difficulty", "Unknown"),
            "install_time": part_data.get("install_time", "Unknown"),
            "appliance_types": part_data.get("appliance_types", "")
        }

    def _format_installation_response(self, result: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Format installation info response"""
        if "error" in result:
            return None
        
        part = result["part"]
        install = result["installation"]
        
        response = f"""**Installation Steps for {part['name']} (Part #{part['partselect_number']})**

**Part Details:**
- Brand: {part['brand']}
- Price: {part['price']}
- Stock: {part['stock_status']}

**Installation Info:**
- Difficulty: {install['difficulty']}
- Estimated Time: {install['time']}
- Tools Needed: {', '.join(install['tools_needed']) if install['tools_needed'] else 'Basic hand tools'}

**Instructions:**
{install['instructions']}

{f"**Installation Video:** {install['video_url']}" if install['video_url'] else ""}

**Need more help?** Visit the full part page: {part['url']}"""

        return {
            "response": response,
            "parts": [self._convert_to_part_object(part)],
            "source": "fast_lookup",
            "query_type": "installation"
        }
    
    def _format_part_info_response(self, part: Dict[str, Any], query: str, detection: Dict[str, Any]) -> Dict[str, Any]:
        """Format part information response"""
        response = f"""**{part['name']} - Part #{part['partselect_number']}**

**Details:**
- Brand: {part['brand']}
- Price: {part['price']}
- Stock Status: {part['stock_status']}
- Category: {part['category']}

**Description:**
{part['description']}

**Compatibility:**
{part.get('metadata', {}).get('compatible_models', 'Check part page for model compatibility')}

**View full details:** {part['url']}"""

        return {
            "response": response,
            "parts": [self._convert_to_part_object(part)],
            "source": "fast_lookup",
            "query_type": "part_info"
        }
    
    def _format_model_parts_response(self, parts: List[Dict[str, Any]], model: str, query: str) -> Dict[str, Any]:
        """Format model parts response"""
        if not parts:
            return None
        
        response = f"""**Parts Available for Model {model}:**

Found {len(parts)} compatible parts:
"""
        
        for i, part in enumerate(parts[:5], 1):  # Show top 5
            response += f"{i}. **{part['name']}** (#{part['partselect_number']}) - {part['price']}\n"
        
        if len(parts) > 5:
            response += f"\n...and {len(parts) - 5} more parts available."
        
        response += f"\n\n**Need help choosing?** Provide your specific symptom for better recommendations."

        return {
            "response": response,
            "parts": [self._convert_to_part_object(part) for part in parts[:5]],
            "source": "fast_lookup",
            "query_type": "model_parts"
        }
    
    def _convert_to_part_object(self, part_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database part to frontend part object"""
        return {
            "name": part_dict.get("name", ""),
            "part_number": part_dict.get("partselect_number", ""),
            "manufacturer_number": part_dict.get("manufacturer_number", ""),
            "brand": part_dict.get("brand", ""),
            "price": part_dict.get("price", ""),
            "stock_status": part_dict.get("stock_status", ""),
            "url": part_dict.get("url", ""),
            "description": part_dict.get("description", ""),
            "install_difficulty": part_dict.get("metadata", {}).get("install_difficulty", ""),
            "install_time": part_dict.get("metadata", {}).get("install_time", "")
        }

# Global fast lookup service
fast_lookup_service = FastLookupService()
