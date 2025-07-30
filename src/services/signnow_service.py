import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class SignNowService:
    """
    SignNow API service based on official documentation
    https://docs.signnow.com/docs/signnow/welcome
    """
    
    def __init__(self):
        self.api_key = os.environ.get('SIGNNOW_API_KEY')
        self.base_url = 'https://api.signnow.com'
        self.template_id = os.environ.get('SIGNNOW_TEMPLATE_ID', '4f5b4511641e44de8d9653a9e850f38fa8e055b5')
        
        if not self.api_key:
            logger.warning("SignNow API key not found. SignNow features will be disabled.")
    
    def is_available(self) -> bool:
        """Check if SignNow service is available"""
        return bool(self.api_key)
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, files: Dict = None) -> Dict:
        """Make authenticated request to SignNow API"""
        if not self.is_available():
            raise Exception("SignNow API key not configured")
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
        }
        
        # Don't set Content-Type for file uploads
        if not files:
            headers['Content-Type'] = 'application/json'
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=data)
            elif method.upper() == 'POST':
                if files:
                    response = requests.post(url, headers=headers, data=data, files=files)
                else:
                    response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            logger.info(f"SignNow API {method} {endpoint}: {response.status_code}")
            
            if response.status_code >= 400:
                logger.error(f"SignNow API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f"API error: {response.status_code}",
                    'details': response.text
                }
            
            return {
                'success': True,
                'data': response.json() if response.content else {}
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"SignNow API request failed: {str(e)}")
            return {
                'success': False,
                'error': f"Request failed: {str(e)}"
            }
        except Exception as e:
            logger.error(f"SignNow API unexpected error: {str(e)}")
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }
    
    def create_document_from_template(self, user_data: Dict) -> Dict:
        """
        Create a document from template with user data
        Based on: https://docs.signnow.com/docs/signnow/api-reference-template-post-template-templateid-copy
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'SignNow not available',
                'message': 'SignNow API key not configured'
            }
        
        try:
            # Step 1: Copy template to create new document
            endpoint = f'/template/{self.template_id}/copy'
            copy_data = {
                'document_name': f"Finder's Fee Agreement - {user_data.get('first_name', '')} {user_data.get('last_name', '')}",
                'client_timestamp': int(datetime.now().timestamp())
            }
            
            result = self._make_request('POST', endpoint, copy_data)
            
            if not result['success']:
                return result
            
            document_id = result['data'].get('id')
            if not document_id:
                return {
                    'success': False,
                    'error': 'No document ID returned from template copy'
                }
            
            # Step 2: Pre-fill document fields (if template has fillable fields)
            prefill_result = self._prefill_document_fields(document_id, user_data)
            if not prefill_result['success']:
                logger.warning(f"Failed to prefill fields: {prefill_result.get('error')}")
            
            return {
                'success': True,
                'document_id': document_id,
                'document_name': copy_data['document_name'],
                'template_id': self.template_id
            }
            
        except Exception as e:
            logger.error(f"Error creating document from template: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to create document: {str(e)}"
            }
    
    def _prefill_document_fields(self, document_id: str, user_data: Dict) -> Dict:
        """
        Pre-fill document fields with user data
        Based on: https://docs.signnow.com/docs/signnow/api-reference-document-put-document-documentid
        """
        try:
            # Map user data to common field names
            field_data = {
                'fields': [
                    {
                        'field_name': 'full_name',
                        'field_value': f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}"
                    },
                    {
                        'field_name': 'first_name',
                        'field_value': user_data.get('first_name', '')
                    },
                    {
                        'field_name': 'last_name',
                        'field_value': user_data.get('last_name', '')
                    },
                    {
                        'field_name': 'email',
                        'field_value': user_data.get('email', '')
                    },
                    {
                        'field_name': 'date',
                        'field_value': datetime.now().strftime('%m/%d/%Y')
                    }
                ]
            }
            
            endpoint = f'/document/{document_id}'
            return self._make_request('PUT', endpoint, field_data)
            
        except Exception as e:
            logger.error(f"Error prefilling document fields: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to prefill fields: {str(e)}"
            }
    
    def create_embedded_signing_invite(self, document_id: str, user_data: Dict) -> Dict:
        """
        Create embedded signing invite for the document
        Based on: https://docs.signnow.com/docs/signnow/api-reference-invite-to-sign-field-invite-post-document-documentid-invite
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'SignNow not available',
                'message': 'SignNow API key not configured'
            }
        
        try:
            endpoint = f'/document/{document_id}/invite'
            
            invite_data = {
                'to': [
                    {
                        'email': user_data.get('email'),
                        'role_name': 'Signer',
                        'role': 'signer',
                        'order': 1,
                        'embedded_signing_enabled': True,
                        'embedded_signing_redirect_url': user_data.get('redirect_url', 'https://agnusfrontend.vercel.app/onboarding?step=kyc'),
                        'embedded_signing_decline_redirect_url': user_data.get('decline_url', 'https://agnusfrontend.vercel.app/onboarding?step=signature&error=declined')
                    }
                ],
                'from': user_data.get('from_email', 'noreply@agnuslink.com'),
                'subject': 'Please sign your Finder\'s Fee Agreement',
                'message': f"Hello {user_data.get('first_name', '')},\n\nPlease review and sign your Finder's Fee Agreement to complete your onboarding process.\n\nThank you,\nAgnus Link Team"
            }
            
            result = self._make_request('POST', endpoint, invite_data)
            
            if not result['success']:
                return result
            
            # Extract invite data
            invite_info = result['data']
            
            return {
                'success': True,
                'invite_id': invite_info.get('id'),
                'document_id': document_id,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating embedded signing invite: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to create signing invite: {str(e)}"
            }
    
    def get_embedded_signing_link(self, document_id: str, user_email: str) -> Dict:
        """
        Get embedded signing link for the document
        Based on: https://docs.signnow.com/docs/signnow/api-reference-embedded-signing-post-link
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'SignNow not available',
                'message': 'SignNow API key not configured'
            }
        
        try:
            endpoint = '/link'
            
            link_data = {
                'document_id': document_id,
                'email': user_email,
                'link_expiration': int((datetime.now() + timedelta(days=30)).timestamp())
            }
            
            result = self._make_request('POST', endpoint, link_data)
            
            if not result['success']:
                return result
            
            signing_url = result['data'].get('url')
            if not signing_url:
                return {
                    'success': False,
                    'error': 'No signing URL returned'
                }
            
            return {
                'success': True,
                'signing_url': signing_url,
                'document_id': document_id,
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting embedded signing link: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to get signing link: {str(e)}"
            }
    
    def get_document_status(self, document_id: str) -> Dict:
        """
        Get document signing status
        Based on: https://docs.signnow.com/docs/signnow/api-reference-document-get-document-documentid
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'SignNow not available',
                'message': 'SignNow API key not configured'
            }
        
        try:
            endpoint = f'/document/{document_id}'
            result = self._make_request('GET', endpoint)
            
            if not result['success']:
                return result
            
            document_data = result['data']
            
            # Determine signing status
            signatures = document_data.get('signatures', [])
            is_completed = all(sig.get('status') == 'signed' for sig in signatures) if signatures else False
            
            return {
                'success': True,
                'document_id': document_id,
                'status': 'completed' if is_completed else 'pending',
                'signatures': signatures,
                'created': document_data.get('created'),
                'updated': document_data.get('updated')
            }
            
        except Exception as e:
            logger.error(f"Error getting document status: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to get document status: {str(e)}"
            }
    
    def download_signed_document(self, document_id: str) -> Dict:
        """
        Download the signed document
        Based on: https://docs.signnow.com/docs/signnow/api-reference-document-get-document-documentid-download
        """
        if not self.is_available():
            return {
                'success': False,
                'error': 'SignNow not available',
                'message': 'SignNow API key not configured'
            }
        
        try:
            endpoint = f'/document/{document_id}/download'
            
            # Make request without JSON parsing (binary content)
            url = f"{self.base_url}{endpoint}"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code >= 400:
                return {
                    'success': False,
                    'error': f"Download failed: {response.status_code}"
                }
            
            return {
                'success': True,
                'content': response.content,
                'content_type': response.headers.get('content-type', 'application/pdf'),
                'filename': f'signed_document_{document_id}.pdf'
            }
            
        except Exception as e:
            logger.error(f"Error downloading signed document: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to download document: {str(e)}"
            }
    
    def handle_webhook(self, webhook_data: Dict) -> Dict:
        """
        Handle SignNow webhook notifications
        Based on: https://docs.signnow.com/docs/signnow/guides-webhooks
        """
        try:
            event_type = webhook_data.get('event_type')
            document_id = webhook_data.get('document_id')
            
            logger.info(f"SignNow webhook received: {event_type} for document {document_id}")
            
            # Handle different event types
            if event_type == 'document.signed':
                return {
                    'success': True,
                    'action': 'document_completed',
                    'document_id': document_id,
                    'status': 'completed'
                }
            elif event_type == 'document.declined':
                return {
                    'success': True,
                    'action': 'document_declined',
                    'document_id': document_id,
                    'status': 'declined'
                }
            else:
                return {
                    'success': True,
                    'action': 'status_update',
                    'document_id': document_id,
                    'event_type': event_type
                }
                
        except Exception as e:
            logger.error(f"Error handling SignNow webhook: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to handle webhook: {str(e)}"
            }
    
    def test_connection(self) -> Dict:
        """Test SignNow API connection"""
        if not self.is_available():
            return {
                'success': False,
                'error': 'SignNow API key not configured'
            }
        
        try:
            # Test with a simple API call
            endpoint = '/user'
            result = self._make_request('GET', endpoint)
            
            return {
                'success': result['success'],
                'message': 'SignNow API connection successful' if result['success'] else 'SignNow API connection failed',
                'details': result.get('error', 'Connected successfully')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Connection test failed: {str(e)}"
            }

# Global instance
signnow_service = SignNowService()

