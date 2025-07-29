import requests
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class SignNowService:
    def __init__(self):
        self.client_id = os.getenv('SIGNNOW_CLIENT_ID')
        self.client_secret = os.getenv('SIGNNOW_CLIENT_SECRET')
        self.api_base = os.getenv('SIGNNOW_API_BASE', 'https://api.signnow.com')
        self.template_id = os.getenv('SIGNNOW_TEMPLATE_ID')
        self.access_token = None
        self.token_expires_at = None
        
        if not all([self.client_id, self.client_secret, self.template_id]):
            logger.warning("SignNow credentials not fully configured")
    
    def is_available(self) -> bool:
        """Check if SignNow service is properly configured"""
        return all([self.client_id, self.client_secret, self.template_id])
    
    def get_access_token(self) -> Optional[str]:
        """Get or refresh access token"""
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
        
        try:
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
            # Set expiration to 1 hour from now (tokens typically last longer)
            self.token_expires_at = datetime.now() + timedelta(hours=1)
            
            logger.info("Successfully obtained SignNow access token")
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to get SignNow access token: {e}")
            return None
    
    def create_document_from_template(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Create a document from template"""
        if not self.is_available():
            logger.error("SignNow service not available")
            return None
            
        token = self.get_access_token()
        if not token:
            return None
        
        try:
            url = f"{self.api_base}/v2/templates/{self.template_id}/documents"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            # Create document from template with user data
            data = {
                'document_name': f"Finder's Fee Contract - {user_data.get('first_name', '')} {user_data.get('last_name', '')}",
                'prefill_fields': {
                    'signer_name': f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}",
                    'signer_email': user_data.get('email', ''),
                    'date': datetime.now().strftime('%Y-%m-%d')
                }
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            document_id = result.get('id')
            
            logger.info(f"Created document from template: {document_id}")
            return document_id
            
        except Exception as e:
            logger.error(f"Failed to create document from template: {e}")
            return None
    
    def create_embedded_signing_invite(self, document_id: str, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create embedded signing invite for a document"""
        if not self.is_available():
            return {"error": "SignNow service not configured"}
            
        token = self.get_access_token()
        if not token:
            return {"error": "Failed to get access token"}
        
        try:
            # First, get the document to find role IDs
            doc_url = f"{self.api_base}/v2/documents/{document_id}"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            doc_response = requests.get(doc_url, headers=headers)
            doc_response.raise_for_status()
            doc_data = doc_response.json()
            
            # Find the first role (assuming single signer)
            roles = doc_data.get('roles', [])
            if not roles:
                return {"error": "No roles found in document"}
            
            role_id = roles[0].get('id')
            
            # Create embedded invite
            invite_url = f"{self.api_base}/v2/documents/{document_id}/embedded-invites"
            
            invite_data = {
                "invites": [
                    {
                        "email": user_data.get('email'),
                        "role_id": role_id,
                        "order": 1,
                        "auth_method": "none",  # No additional authentication
                        "first_name": user_data.get('first_name', ''),
                        "last_name": user_data.get('last_name', ''),
                        "redirect_uri": f"https://agnusfrontend.vercel.app/onboarding?step=signature-complete"
                    }
                ]
            }
            
            response = requests.post(invite_url, headers=headers, json=invite_data)
            response.raise_for_status()
            
            result = response.json()
            invite_id = result.get('data', [{}])[0].get('id')
            
            if invite_id:
                logger.info(f"Created embedded invite: {invite_id}")
                return {
                    "invite_id": invite_id,
                    "document_id": document_id,
                    "role_id": role_id
                }
            else:
                return {"error": "Failed to create invite"}
                
        except Exception as e:
            logger.error(f"Failed to create embedded invite: {e}")
            return {"error": str(e)}
    
    def generate_embedded_signing_link(self, invite_id: str) -> Optional[str]:
        """Generate embedded signing link"""
        if not self.is_available():
            return None
            
        token = self.get_access_token()
        if not token:
            return None
        
        try:
            url = f"{self.api_base}/v2/documents/embedded-invites/{invite_id}/link"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                "auth_method": "password",
                "link_expiration": 45  # 45 minutes
            }
            
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            signing_link = result.get('link')
            
            logger.info(f"Generated embedded signing link for invite: {invite_id}")
            return signing_link
            
        except Exception as e:
            logger.error(f"Failed to generate signing link: {e}")
            return None
    
    def get_document_status(self, document_id: str) -> Dict[str, Any]:
        """Get document signing status"""
        if not self.is_available():
            return {"status": "error", "message": "SignNow service not configured"}
            
        token = self.get_access_token()
        if not token:
            return {"status": "error", "message": "Failed to get access token"}
        
        try:
            url = f"{self.api_base}/v2/documents/{document_id}"
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            # Check if document is signed
            is_signed = result.get('status') == 'completed'
            
            return {
                "status": "completed" if is_signed else "pending",
                "document_id": document_id,
                "signed_date": result.get('updated') if is_signed else None,
                "signers": result.get('roles', [])
            }
            
        except Exception as e:
            logger.error(f"Failed to get document status: {e}")
            return {"status": "error", "message": str(e)}
    
    def create_complete_signing_flow(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete flow: create document, invite, and generate link"""
        if not self.is_available():
            return {
                "success": False,
                "error": "SignNow service not configured. Please add SIGNNOW_CLIENT_ID, SIGNNOW_CLIENT_SECRET, and SIGNNOW_TEMPLATE_ID to environment variables."
            }
        
        try:
            # Step 1: Create document from template
            document_id = self.create_document_from_template(user_data)
            if not document_id:
                return {"success": False, "error": "Failed to create document"}
            
            # Step 2: Create embedded invite
            invite_result = self.create_embedded_signing_invite(document_id, user_data)
            if "error" in invite_result:
                return {"success": False, "error": invite_result["error"]}
            
            invite_id = invite_result["invite_id"]
            
            # Step 3: Generate signing link
            signing_link = self.generate_embedded_signing_link(invite_id)
            if not signing_link:
                return {"success": False, "error": "Failed to generate signing link"}
            
            return {
                "success": True,
                "document_id": document_id,
                "invite_id": invite_id,
                "signing_link": signing_link,
                "message": "Document ready for signing"
            }
            
        except Exception as e:
            logger.error(f"Failed to create complete signing flow: {e}")
            return {"success": False, "error": str(e)}

# Global instance
signnow_service = SignNowService()

