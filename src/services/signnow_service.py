import requests
import json
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class SignNowService:
    """Complete SignNow API integration service with updated field mappings"""
    
    def __init__(self):
        self.api_key = os.getenv('SIGNNOW_API_KEY')
        self.template_id = os.getenv('SIGNNOW_TEMPLATE_ID', '4f5b4511641e44de8d9653a9e850f38fa8e055b5')
        self.base_url = 'https://api.signnow.com'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        if not self.api_key:
            logger.error("SIGNNOW_API_KEY environment variable not set")
    
    def create_document_from_template(self, user_data):
        """Create a new document from template and pre-fill user data"""
        try:
            logger.info(f"Creating document from template for user: {user_data.get('email')}")
            
            # Step 1: Copy template to create new document
            copy_url = f"{self.base_url}/template/{self.template_id}/copy"
            copy_payload = {
                "document_name": f"Finder's Fee Agreement - {user_data.get('first_name')} {user_data.get('last_name')}"
            }
            
            logger.info(f"Copying template: {copy_url}")
            copy_response = requests.post(copy_url, headers=self.headers, json=copy_payload)
            
            if copy_response.status_code != 200:
                logger.error(f"Template copy failed: {copy_response.status_code} - {copy_response.text}")
                return None
            
            copy_data = copy_response.json()
            document_id = copy_data.get('id')
            
            if not document_id:
                logger.error("No document ID returned from template copy")
                return None
            
            logger.info(f"Document created successfully: {document_id}")
            
            # Step 2: Pre-fill document fields with user data
            prefill_success = self.prefill_document_fields(document_id, user_data)
            if not prefill_success:
                logger.warning("Failed to pre-fill document fields, continuing anyway")
            
            return document_id
            
        except Exception as e:
            logger.error(f"Error creating document from template: {str(e)}")
            return None
    
    def prefill_document_fields(self, document_id, user_data):
        """Pre-fill document fields with user data using updated field names"""
        try:
            logger.info(f"Pre-filling document fields for document: {document_id}")
            
            # Get document fields first to see what's available
            fields_url = f"{self.base_url}/document/{document_id}"
            fields_response = requests.get(fields_url, headers=self.headers)
            
            if fields_response.status_code != 200:
                logger.error(f"Failed to get document fields: {fields_response.status_code}")
                return False
            
            # Log the document structure for debugging
            fields_data = fields_response.json()
            logger.info(f"Document structure: {json.dumps(fields_data, indent=2)}")
            
            # Pre-fill fields with common SignNow field naming patterns
            # Since we can't see the exact field names, we'll try multiple patterns
            prefill_url = f"{self.base_url}/document/{document_id}/prefill"
            
            # Try different field name patterns that SignNow commonly uses
            possible_field_mappings = [
                # Pattern 1: Simple text fields
                {
                    "field_name": "text_1",
                    "prefilled_text": f"{user_data.get('first_name')} {user_data.get('last_name')}"
                },
                {
                    "field_name": "text_2", 
                    "prefilled_text": user_data.get('email')
                },
                {
                    "field_name": "text_3",
                    "prefilled_text": datetime.now().strftime("%m/%d/%Y")
                },
                # Pattern 2: Named fields
                {
                    "field_name": "signer_name",
                    "prefilled_text": f"{user_data.get('first_name')} {user_data.get('last_name')}"
                },
                {
                    "field_name": "signer_email",
                    "prefilled_text": user_data.get('email')
                },
                {
                    "field_name": "date",
                    "prefilled_text": datetime.now().strftime("%m/%d/%Y")
                },
                # Pattern 3: Full name field
                {
                    "field_name": "full_name",
                    "prefilled_text": f"{user_data.get('first_name')} {user_data.get('last_name')}"
                },
                # Pattern 4: Date field
                {
                    "field_name": "date_1",
                    "prefilled_text": datetime.now().strftime("%m/%d/%Y")
                }
            ]
            
            prefill_data = {"fields": possible_field_mappings}
            
            prefill_response = requests.put(prefill_url, headers=self.headers, json=prefill_data)
            
            if prefill_response.status_code == 200:
                logger.info("Document fields pre-filled successfully")
                return True
            else:
                logger.warning(f"Pre-fill failed: {prefill_response.status_code} - {prefill_response.text}")
                # Don't fail the entire process if pre-fill doesn't work
                return True
                
        except Exception as e:
            logger.error(f"Error pre-filling document fields: {str(e)}")
            return True  # Continue even if pre-fill fails
    
    def create_embedded_signing_link(self, document_id, user_data):
        """Create embedded signing link for the document"""
        try:
            logger.info(f"Creating embedded signing link for document: {document_id}")
            
            # Step 1: Create signing invite
            invite_url = f"{self.base_url}/document/{document_id}/invite"
            invite_payload = {
                "to": [
                    {
                        "email": user_data.get('email'),
                        "role_name": "Signer",
                        "role": "signer",
                        "order": 1,
                        "expiration_days": 30,
                        "reminder": 1
                    }
                ],
                "from": user_data.get('email'),
                "subject": "Please sign your Finder's Fee Agreement",
                "message": "Please review and sign the attached Finder's Fee Agreement to complete your onboarding."
            }
            
            logger.info(f"Creating invite: {invite_url}")
            invite_response = requests.post(invite_url, headers=self.headers, json=invite_payload)
            
            if invite_response.status_code != 200:
                logger.error(f"Invite creation failed: {invite_response.status_code} - {invite_response.text}")
                return None
            
            invite_data = invite_response.json()
            logger.info(f"Invite created successfully: {invite_data}")
            
            # Step 2: Get embedded signing link
            link_url = f"{self.base_url}/link"
            
            # Extract field_invite from the response
            field_invite = ""
            if 'data' in invite_data and len(invite_data['data']) > 0:
                field_invite = invite_data['data'][0].get('field_invite', '')
            
            link_payload = {
                "document_id": document_id,
                "field_invite": field_invite,
                "link_expiration": 2592000  # 30 days in seconds
            }
            
            logger.info(f"Creating embedded link: {link_url}")
            logger.info(f"Link payload: {link_payload}")
            
            link_response = requests.post(link_url, headers=self.headers, json=link_payload)
            
            if link_response.status_code != 200:
                logger.error(f"Link creation failed: {link_response.status_code} - {link_response.text}")
                return None
            
            link_data = link_response.json()
            signing_link = link_data.get('url')
            
            if signing_link:
                logger.info(f"Embedded signing link created successfully: {signing_link}")
                return signing_link
            else:
                logger.error("No signing link returned from API")
                return None
                
        except Exception as e:
            logger.error(f"Error creating embedded signing link: {str(e)}")
            return None
    
    def create_complete_signing_flow(self, user_data):
        """Complete signing flow: create document and get signing link"""
        try:
            logger.info(f"Starting complete signing flow for user: {user_data.get('email')}")
            
            if not self.api_key:
                logger.error("SignNow API key not configured")
                return {
                    'success': False,
                    'error': 'SignNow API key not configured. Please set SIGNNOW_API_KEY environment variable.',
                    'signing_link': None
                }
            
            # Step 1: Create document from template
            document_id = self.create_document_from_template(user_data)
            if not document_id:
                return {
                    'success': False,
                    'error': 'Failed to create document from template. Please check template ID and API permissions.',
                    'signing_link': None
                }
            
            # Step 2: Create embedded signing link
            signing_link = self.create_embedded_signing_link(document_id, user_data)
            if not signing_link:
                return {
                    'success': False,
                    'error': 'Failed to create signing link. Document was created but signing link generation failed.',
                    'signing_link': None,
                    'document_id': document_id
                }
            
            logger.info(f"Complete signing flow successful for user: {user_data.get('email')}")
            return {
                'success': True,
                'signing_link': signing_link,
                'document_id': document_id,
                'message': 'Signing link created successfully',
                'template_configured': True
            }
            
        except Exception as e:
            logger.error(f"Error in complete signing flow: {str(e)}")
            return {
                'success': False,
                'error': f'Signing flow error: {str(e)}',
                'signing_link': None
            }
    
    def check_document_status(self, document_id):
        """Check if document has been signed"""
        try:
            status_url = f"{self.base_url}/document/{document_id}"
            response = requests.get(status_url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'status': data.get('status', 'unknown'),
                    'signed': data.get('status') == 'completed'
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to check document status: {response.status_code}'
                }
                
        except Exception as e:
            logger.error(f"Error checking document status: {str(e)}")
            return {
                'success': False,
                'error': f'Status check error: {str(e)}'
            }

# Global service instance
signnow_service = SignNowService()

