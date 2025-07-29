import requests
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class SignNowService:
    """SignNow API integration service"""
    
    def __init__(self):
        self.client_id = os.environ.get('SIGNNOW_CLIENT_ID')
        self.client_secret = os.environ.get('SIGNNOW_CLIENT_SECRET')
        self.api_base = os.environ.get('SIGNNOW_API_BASE', 'https://api.signnow.com')
        self.template_id = os.environ.get('SIGNNOW_TEMPLATE_ID')
        self.access_token = None
        self.token_expires_at = None
        
        if not all([self.client_id, self.client_secret, self.template_id]):
            logger.warning("SignNow credentials not fully configured")
    
    def _get_access_token(self) -> Optional[str]:
        """Get or refresh access token"""
        try:
            # Check if current token is still valid
            if (self.access_token and self.token_expires_at and 
                datetime.utcnow() < self.token_expires_at):
                return self.access_token
            
            # Request new token
            url = f"{self.api_base}/oauth2/token"
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # Set expiration time (subtract 5 minutes for safety)
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)
            
            logger.info("SignNow access token obtained successfully")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to get SignNow access token: {e}")
            return None
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make authenticated request to SignNow API"""
        try:
            token = self._get_access_token()
            if not token:
                return None
            
            url = f"{self.api_base}{endpoint}"
            headers = kwargs.get('headers', {})
            headers['Authorization'] = f'Bearer {token}'
            kwargs['headers'] = headers
            
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"SignNow API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            return None
    
    def create_document_from_template(self, user_data: Dict[str, Any]) -> Optional[Dict]:
        """Create a document from template for user to sign"""
        try:
            if not self.template_id:
                logger.error("SignNow template ID not configured")
                return None
            
            # Prepare document data
            document_name = f"Finder's Fee Contract - {user_data.get('first_name', '')} {user_data.get('last_name', '')}"
            
            # Create document from template
            endpoint = f"/template/{self.template_id}/copy"
            data = {
                'document_name': document_name
            }
            
            result = self._make_request('POST', endpoint, json=data)
            if not result:
                return None
            
            document_id = result.get('id')
            if not document_id:
                logger.error("No document ID returned from template copy")
                return None
            
            logger.info(f"Document created from template: {document_id}")
            
            # Pre-fill document fields if needed
            self._prefill_document_fields(document_id, user_data)
            
            return {
                'document_id': document_id,
                'document_name': document_name,
                'template_id': self.template_id
            }
            
        except Exception as e:
            logger.error(f"Failed to create document from template: {e}")
            return None
    
    def _prefill_document_fields(self, document_id: str, user_data: Dict[str, Any]) -> bool:
        """Pre-fill document fields with user data"""
        try:
            # Get document fields
            endpoint = f"/document/{document_id}/fields"
            fields_result = self._make_request('GET', endpoint)
            
            if not fields_result:
                logger.warning("Could not get document fields for pre-filling")
                return False
            
            # Prepare field updates
            field_updates = []
            
            # Map user data to common field names
            field_mappings = {
                'full_name': f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', ''),
                'email': user_data.get('email', ''),
                'phone': user_data.get('phone', ''),
                'date': datetime.utcnow().strftime('%Y-%m-%d')
            }
            
            # Update fields that exist in the document
            fields = fields_result.get('fields', [])
            for field in fields:
                field_name = field.get('name', '').lower()
                if field_name in field_mappings and field_mappings[field_name]:
                    field_updates.append({
                        'field_id': field.get('id'),
                        'data': field_mappings[field_name]
                    })
            
            # Apply field updates if any
            if field_updates:
                update_endpoint = f"/document/{document_id}/fields"
                update_data = {'fields': field_updates}
                
                update_result = self._make_request('PUT', update_endpoint, json=update_data)
                if update_result:
                    logger.info(f"Pre-filled {len(field_updates)} fields in document {document_id}")
                    return True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to pre-fill document fields: {e}")
            return False
    
    def create_signing_link(self, document_id: str, user_data: Dict[str, Any]) -> Optional[Dict]:
        """Create a signing link for the user"""
        try:
            endpoint = f"/document/{document_id}/invite"
            
            # Prepare signing invitation
            data = {
                'to': [{
                    'email': user_data.get('email'),
                    'role_id': '',
                    'role': 'Signer',
                    'order': 1,
                    'expiration_days': 30,
                    'reminder': 1
                }],
                'from': user_data.get('email'),
                'subject': 'Please sign your Finder\'s Fee Contract',
                'message': 'Please review and sign the attached Finder\'s Fee Contract to complete your onboarding.'
            }
            
            result = self._make_request('POST', endpoint, json=data)
            if not result:
                return None
            
            # Get the signing URL
            signing_url = result.get('data', [{}])[0].get('link')
            
            if not signing_url:
                logger.error("No signing URL returned from invite")
                return None
            
            logger.info(f"Signing link created for document {document_id}")
            
            return {
                'signing_url': signing_url,
                'document_id': document_id,
                'expires_in_days': 30
            }
            
        except Exception as e:
            logger.error(f"Failed to create signing link: {e}")
            return None
    
    def get_document_status(self, document_id: str) -> Optional[Dict]:
        """Get document signing status"""
        try:
            endpoint = f"/document/{document_id}"
            result = self._make_request('GET', endpoint)
            
            if not result:
                return None
            
            # Parse document status
            status = result.get('status', 'pending')
            signatures = result.get('signatures', [])
            
            # Determine if document is fully signed
            is_signed = status == 'completed' or all(
                sig.get('status') == 'signed' for sig in signatures
            )
            
            return {
                'document_id': document_id,
                'status': status,
                'is_signed': is_signed,
                'signatures': signatures,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get document status: {e}")
            return None
    
    def create_embedded_signing_link(self, document_id: str, user_data: Dict[str, Any]) -> Optional[Dict]:
        """Create an embedded signing link for seamless integration"""
        try:
            endpoint = f"/document/{document_id}/embedded-invite"
            
            data = {
                'to': [{
                    'email': user_data.get('email'),
                    'role_id': '',
                    'role': 'Signer',
                    'order': 1
                }],
                'from': user_data.get('email'),
                'subject': 'Finder\'s Fee Contract Signature Required'
            }
            
            result = self._make_request('POST', endpoint, json=data)
            if not result:
                return None
            
            # Get embedded signing data
            embedded_data = result.get('data', [{}])[0]
            signing_url = embedded_data.get('link')
            
            if not signing_url:
                logger.error("No embedded signing URL returned")
                return None
            
            logger.info(f"Embedded signing link created for document {document_id}")
            
            return {
                'signing_url': signing_url,
                'document_id': document_id,
                'embedded': True,
                'expires_in_days': 30
            }
            
        except Exception as e:
            logger.error(f"Failed to create embedded signing link: {e}")
            return None
    
    def setup_webhook(self, webhook_url: str) -> bool:
        """Setup webhook for document status updates"""
        try:
            endpoint = "/webhook"
            
            data = {
                'event': 'document.complete',
                'callback_url': webhook_url,
                'use_tls_12': True
            }
            
            result = self._make_request('POST', endpoint, json=data)
            
            if result:
                logger.info(f"Webhook setup successful: {webhook_url}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to setup webhook: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Check if SignNow service is properly configured"""
        return all([
            self.client_id,
            self.client_secret,
            self.template_id
        ])
    
    def test_connection(self) -> bool:
        """Test SignNow API connection"""
        try:
            token = self._get_access_token()
            return token is not None
        except Exception as e:
            logger.error(f"SignNow connection test failed: {e}")
            return False

