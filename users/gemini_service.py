import os
import json
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from PIL import Image
import io

# Setup logging
logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google GenerativeAI not installed. Install with: pip install google-generativeai")

class GeminiDocumentVerifier:
    def __init__(self):
        if not GEMINI_AVAILABLE:
            raise ImportError("Google GenerativeAI package not installed")
        
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in settings")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def verify_document(self, document_file, document_type: str, user_data: Dict) -> Dict[str, Any]:
        """
        Verify document using Gemini API
        
        Args:
            document_file: Uploaded document file
            document_type: Type of document ('national_id', 'address_proof', 'license')
            user_data: User profile data for matching
            
        Returns:
            Dict with verification results
        """
        try:
            # Prepare image
            image = self._prepare_image(document_file)
            
            # Get verification prompt based on document type
            prompt = self._get_verification_prompt(document_type, user_data)
            
            # Send to Gemini
            response = self.model.generate_content([prompt, image])
            
            # Parse response
            result = self._parse_verification_result(response.text, document_type)
            
            logger.info(f"Document verification completed for {document_type}: {result['status']}")
            return result
            
        except Exception as e:
            logger.error(f"Gemini verification failed: {str(e)}")
            return {
                'status': 'manual_review',
                'confidence': 0.0,
                'extracted_data': {},
                'issues': [f"Verification service error: {str(e)}"],
                'reasoning': 'Technical error occurred during verification'
            }
    
    def _prepare_image(self, document_file) -> Image.Image:
        """Convert document file to PIL Image"""
        try:
            # Handle different file types
            if hasattr(document_file, 'read'):
                # Django UploadedFile
                image_data = document_file.read()
                document_file.seek(0)  # Reset file pointer
            else:
                # File path
                with open(document_file, 'rb') as f:
                    image_data = f.read()
            
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            return image
            
        except Exception as e:
            logger.error(f"Image preparation failed: {str(e)}")
            raise ValueError(f"Invalid image file: {str(e)}")
    
    def _get_verification_prompt(self, document_type: str, user_data: Dict) -> str:
        """Get verification prompt based on document type"""
        
        base_info = f"""
        User Profile Information:
        - Name: {user_data.get('first_name', '')} {user_data.get('last_name', '')}
        - Email: {user_data.get('email', '')}
        - Phone: {user_data.get('phone_number', '')}
        - Address: {user_data.get('address', '')}
        """
        
        if document_type == 'national_id':
            return f"""
            Analyze this National ID/Government ID document and provide verification:
            
            {base_info}
            
            Please verify:
            1. Is this a legitimate government-issued ID document?
            2. Extract the following data: Full name, ID number, date of birth, expiry date, issuing authority
            3. Does the document appear authentic (no signs of tampering, clear text, proper format)?
            4. Does the extracted name match the user profile name above?
            5. Is the document current (not expired)?
            6. Rate authenticity confidence (0-10 scale)
            
            Respond ONLY in this JSON format:
            {{
                "status": "verified|rejected|manual_review",
                "confidence": 0.0-10.0,
                "extracted_data": {{
                    "full_name": "extracted name",
                    "id_number": "extracted ID",
                    "date_of_birth": "YYYY-MM-DD or null",
                    "expiry_date": "YYYY-MM-DD or null",
                    "issuing_authority": "authority name"
                }},
                "name_match": true/false,
                "is_expired": true/false,
                "issues": ["list any issues found"],
                "reasoning": "brief explanation of decision"
            }}
            """
        
        elif document_type == 'address_proof':
            return f"""
            Analyze this address proof document (utility bill, bank statement, etc.):
            
            {base_info}
            
            Please verify:
            1. Is this a valid address proof document (utility bill, bank statement, government mail)?
            2. Extract: Name, address, document date, issuing organization
            3. Is the document recent (within last 3 months)?
            4. Does the extracted name match the user profile name?
            5. Does the address appear complete and legitimate?
            6. Rate authenticity confidence (0-10 scale)
            
            Respond ONLY in this JSON format:
            {{
                "status": "verified|rejected|manual_review",
                "confidence": 0.0-10.0,
                "extracted_data": {{
                    "name": "extracted name",
                    "address": "extracted address",
                    "document_date": "YYYY-MM-DD or null",
                    "issuing_organization": "organization name",
                    "document_type": "utility bill|bank statement|other"
                }},
                "name_match": true/false,
                "is_recent": true/false,
                "issues": ["list any issues found"],
                "reasoning": "brief explanation of decision"
            }}
            """
        
        elif document_type == 'license':
            return f"""
            Analyze this professional/trade license document:
            
            {base_info}
            
            Please verify:
            1. Is this a valid professional or trade license?
            2. Extract: License holder name, license number, profession/trade, expiry date, issuing authority
            3. Does the document appear authentic and official?
            4. Does the extracted name match the user profile name?
            5. Is the license current (not expired)?
            6. Rate authenticity confidence (0-10 scale)
            
            Respond ONLY in this JSON format:
            {{
                "status": "verified|rejected|manual_review",
                "confidence": 0.0-10.0,
                "extracted_data": {{
                    "holder_name": "extracted name",
                    "license_number": "license number",
                    "profession": "profession/trade type",
                    "expiry_date": "YYYY-MM-DD or null",
                    "issuing_authority": "authority name"
                }},
                "name_match": true/false,
                "is_expired": true/false,
                "issues": ["list any issues found"],
                "reasoning": "brief explanation of decision"
            }}
            """
        
        else:
            raise ValueError(f"Unsupported document type: {document_type}")
    
    def _parse_verification_result(self, response_text: str, document_type: str) -> Dict[str, Any]:
        """Parse Gemini response and return structured result"""
        try:
            # Try to extract JSON from response
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            result = json.loads(response_text)
            
            # Validate required fields
            if 'status' not in result:
                result['status'] = 'manual_review'
            if 'confidence' not in result:
                result['confidence'] = 5.0
            if 'extracted_data' not in result:
                result['extracted_data'] = {}
            if 'issues' not in result:
                result['issues'] = []
            if 'reasoning' not in result:
                result['reasoning'] = 'Automated verification completed'
            
            # Ensure confidence is in valid range
            result['confidence'] = max(0.0, min(10.0, float(result['confidence'])))
            
            # Auto-adjust status based on confidence
            if result['confidence'] >= 8.0 and not result['issues']:
                result['status'] = 'verified'
            elif result['confidence'] <= 3.0 or len(result['issues']) > 2:
                result['status'] = 'rejected'
            elif result['status'] not in ['verified', 'rejected', 'manual_review']:
                result['status'] = 'manual_review'
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Response text: {response_text}")
            
            # Fallback: try to extract status from text
            response_lower = response_text.lower()
            if 'verified' in response_lower and 'reject' not in response_lower:
                status = 'verified'
                confidence = 7.0
            elif 'reject' in response_lower:
                status = 'rejected'
                confidence = 2.0
            else:
                status = 'manual_review'
                confidence = 5.0
            
            return {
                'status': status,
                'confidence': confidence,
                'extracted_data': {},
                'issues': ['Response parsing error'],
                'reasoning': f'Could not parse verification response: {str(e)}'
            }
        
        except Exception as e:
            logger.error(f"Unexpected error parsing verification result: {e}")
            return {
                'status': 'manual_review',
                'confidence': 0.0,
                'extracted_data': {},
                'issues': [f'Parsing error: {str(e)}'],
                'reasoning': 'Technical error during result processing'
            } 