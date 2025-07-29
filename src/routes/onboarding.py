from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.database import db
from src.models.user import User
from src.models.onboarding import DocumentSignature, KYCDocument, OnboardingStep
from src.services.signnow_service import SignNowService
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import logging
import uuid

logger = logging.getLogger(__name__)

onboarding_bp = Blueprint('onboarding', __name__)

# Initialize SignNow service
signnow_service = SignNowService()

@onboarding_bp.route('/status', methods=['GET'])
@jwt_required()
def get_onboarding_status():
    """Get user's onboarding status and next steps"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get onboarding steps
        steps = OnboardingStep.query.filter_by(user_id=user_id).order_by(OnboardingStep.step_number).all()
        
        # Get document signatures
        signatures = DocumentSignature.query.filter_by(user_id=user_id).all()
        
        # Get KYC documents
        kyc_docs = KYCDocument.query.filter_by(user_id=user_id).all()
        
        # Determine current step and next action
        current_step = user.onboarding_step
        next_action = _determine_next_action(user, signatures, kyc_docs)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'onboarding_status': user.onboarding_status,
            'current_step': current_step,
            'next_action': next_action,
            'kyc_status': user.kyc_status,
            'agreements_complete': user.agreements_complete,
            'onboarding_complete': user.onboarding_complete,
            'can_access_dashboard': user.can_access_dashboard,
            'steps': [step.to_dict() for step in steps],
            'signatures': [sig.to_dict() for sig in signatures],
            'kyc_documents': [doc.to_dict() for doc in kyc_docs]
        })
        
    except Exception as e:
        logger.error(f"Error getting onboarding status: {e}")
        return jsonify({'error': 'Failed to get onboarding status'}), 500

@onboarding_bp.route('/start-signature', methods=['POST'])
@jwt_required()
def start_document_signature():
    """Start the document signature process"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if SignNow is configured
        if not signnow_service.is_configured():
            return jsonify({'error': 'Document signing service not configured'}), 500
        
        # Check if user already has a pending signature
        existing_signature = DocumentSignature.query.filter_by(
            user_id=user_id,
            document_type='finders_fee_contract',
            status='pending'
        ).first()
        
        if existing_signature:
            return jsonify({
                'success': True,
                'message': 'Document signature already in progress',
                'signature_id': existing_signature.id,
                'signing_url': existing_signature.signing_url,
                'document_id': existing_signature.signnow_document_id
            })
        
        # Create document from template
        user_data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone': user.phone
        }
        
        document_result = signnow_service.create_document_from_template(user_data)
        if not document_result:
            return jsonify({'error': 'Failed to create document'}), 500
        
        # Create embedded signing link
        signing_result = signnow_service.create_embedded_signing_link(
            document_result['document_id'], 
            user_data
        )
        
        if not signing_result:
            return jsonify({'error': 'Failed to create signing link'}), 500
        
        # Save signature record
        signature = DocumentSignature(
            user_id=user_id,
            document_type='finders_fee_contract',
            signnow_document_id=document_result['document_id'],
            document_name=document_result['document_name'],
            signing_url=signing_result['signing_url'],
            status='pending',
            created_at=datetime.utcnow()
        )
        
        db.session.add(signature)
        
        # Update user onboarding step
        user.onboarding_step = 2
        user.onboarding_status = 'document_signing'
        
        db.session.commit()
        
        logger.info(f"Document signature started for user {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Document signature process started',
            'signature_id': signature.id,
            'signing_url': signing_result['signing_url'],
            'document_id': document_result['document_id'],
            'embedded': True
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error starting document signature: {e}")
        return jsonify({'error': 'Failed to start document signature'}), 500

@onboarding_bp.route('/signature-status/<int:signature_id>', methods=['GET'])
@jwt_required()
def check_signature_status(signature_id):
    """Check the status of a document signature"""
    try:
        user_id = get_jwt_identity()
        
        signature = DocumentSignature.query.filter_by(
            id=signature_id,
            user_id=user_id
        ).first()
        
        if not signature:
            return jsonify({'error': 'Signature not found'}), 404
        
        # Get status from SignNow
        if signature.signnow_document_id:
            status_result = signnow_service.get_document_status(signature.signnow_document_id)
            
            if status_result:
                # Update signature status
                old_status = signature.status
                signature.status = 'signed' if status_result['is_signed'] else 'pending'
                signature.signed_at = datetime.utcnow() if status_result['is_signed'] else None
                
                # Update user status if document was just signed
                if old_status != 'signed' and signature.status == 'signed':
                    user = User.query.get(user_id)
                    user.finders_fee_contract_signed = True
                    user.onboarding_step = 3
                    user.onboarding_status = 'kyc_upload'
                    user.update_onboarding_status()
                
                db.session.commit()
                
                logger.info(f"Signature status updated for user {user_id}: {signature.status}")
        
        return jsonify({
            'success': True,
            'signature_id': signature.id,
            'status': signature.status,
            'signed_at': signature.signed_at.isoformat() if signature.signed_at else None,
            'document_type': signature.document_type
        })
        
    except Exception as e:
        logger.error(f"Error checking signature status: {e}")
        return jsonify({'error': 'Failed to check signature status'}), 500

@onboarding_bp.route('/upload-kyc', methods=['POST'])
@jwt_required()
def upload_kyc_document():
    """Upload KYC document (Government ID)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user has signed the contract
        if not user.finders_fee_contract_signed:
            return jsonify({'error': 'Please sign the contract first'}), 400
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        document_type = request.form.get('document_type', 'government_id')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'pdf', 'jpg', 'jpeg', 'png'}
        if not _allowed_file(file.filename, allowed_extensions):
            return jsonify({'error': 'Invalid file type. Please upload PDF, JPG, or PNG'}), 400
        
        # Validate file size (max 10MB)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            return jsonify({'error': 'File too large. Maximum size is 10MB'}), 400
        
        # Generate secure filename
        filename = secure_filename(file.filename)
        unique_filename = f"{user_id}_{document_type}_{uuid.uuid4().hex}_{filename}"
        
        # Create upload directory if it doesn't exist
        upload_dir = current_app.config.get('UPLOAD_FOLDER', '/tmp/uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)
        
        # Save KYC document record
        kyc_doc = KYCDocument(
            user_id=user_id,
            document_type=document_type,
            original_filename=filename,
            stored_filename=unique_filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=file.content_type,
            status='submitted',
            uploaded_at=datetime.utcnow()
        )
        
        db.session.add(kyc_doc)
        
        # Update user status
        user.kyc_status = 'submitted'
        user.onboarding_step = 4
        user.onboarding_status = 'pending_review'
        user.update_onboarding_status()
        
        db.session.commit()
        
        logger.info(f"KYC document uploaded for user {user_id}: {document_type}")
        
        return jsonify({
            'success': True,
            'message': 'Document uploaded successfully',
            'document_id': kyc_doc.id,
            'document_type': document_type,
            'status': 'submitted',
            'next_step': 'admin_review'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error uploading KYC document: {e}")
        return jsonify({'error': 'Failed to upload document'}), 500

@onboarding_bp.route('/next-step', methods=['POST'])
@jwt_required()
def proceed_to_next_step():
    """Proceed to the next onboarding step"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        current_step = user.onboarding_step
        next_action = _determine_next_action(user, [], [])
        
        # Create onboarding step record
        step = OnboardingStep(
            user_id=user_id,
            step_number=current_step,
            step_name=next_action['step'],
            status='completed',
            completed_at=datetime.utcnow()
        )
        
        db.session.add(step)
        
        # Update user step
        user.onboarding_step = current_step + 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'current_step': user.onboarding_step,
            'next_action': _determine_next_action(user, [], [])
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error proceeding to next step: {e}")
        return jsonify({'error': 'Failed to proceed to next step'}), 500

@onboarding_bp.route('/webhook/signnow', methods=['POST'])
def signnow_webhook():
    """Handle SignNow webhook notifications"""
    try:
        data = request.get_json()
        logger.info(f"SignNow webhook received: {data}")
        
        # Extract document information
        document_id = data.get('document_id')
        event_type = data.get('event_type')
        
        if not document_id:
            return jsonify({'error': 'No document ID provided'}), 400
        
        # Find signature record
        signature = DocumentSignature.query.filter_by(
            signnow_document_id=document_id
        ).first()
        
        if not signature:
            logger.warning(f"No signature record found for document {document_id}")
            return jsonify({'message': 'Document not found'}), 404
        
        # Update signature status based on event
        if event_type == 'document.complete':
            signature.status = 'signed'
            signature.signed_at = datetime.utcnow()
            
            # Update user status
            user = User.query.get(signature.user_id)
            if user:
                user.finders_fee_contract_signed = True
                user.onboarding_step = 3
                user.onboarding_status = 'kyc_upload'
                user.update_onboarding_status()
            
            db.session.commit()
            
            logger.info(f"Document signature completed for user {signature.user_id}")
        
        return jsonify({'success': True, 'message': 'Webhook processed'})
        
    except Exception as e:
        logger.error(f"Error processing SignNow webhook: {e}")
        return jsonify({'error': 'Webhook processing failed'}), 500

def _determine_next_action(user, signatures, kyc_docs):
    """Determine the next action for the user"""
    if user.onboarding_complete:
        return {
            'step': 'completed',
            'action': 'access_dashboard',
            'message': 'Onboarding complete! You can now access the full dashboard.'
        }
    
    if user.kyc_status == 'rejected':
        return {
            'step': 'kyc_resubmit',
            'action': 'upload_kyc',
            'message': 'Please resubmit your KYC documents.'
        }
    
    if user.kyc_status == 'submitted':
        return {
            'step': 'pending_review',
            'action': 'wait',
            'message': 'Your documents are under review. You will be notified once approved.'
        }
    
    if not user.finders_fee_contract_signed:
        return {
            'step': 'document_signing',
            'action': 'sign_contract',
            'message': 'Please sign the Finder\'s Fee Contract to continue.'
        }
    
    if user.finders_fee_contract_signed and user.kyc_status == 'pending':
        return {
            'step': 'kyc_upload',
            'action': 'upload_kyc',
            'message': 'Please upload your government-issued ID for verification.'
        }
    
    return {
        'step': 'welcome',
        'action': 'start_onboarding',
        'message': 'Welcome! Let\'s get you set up with document signing and verification.'
    }

def _allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

