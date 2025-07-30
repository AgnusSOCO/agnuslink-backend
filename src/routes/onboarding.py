from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
import logging

from src.database import db
from src.models.user import User
from src.models.onboarding import DocumentSignature, KYCDocument, OnboardingStep
from src.services.signnow_service import signnow_service

logger = logging.getLogger(__name__)

onboarding_bp = Blueprint('onboarding', __name__)

# Allowed file extensions for KYC documents
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        steps = OnboardingStep.query.filter_by(user_id=user_id).all()
        
        # Get document signature status
        signature = DocumentSignature.query.filter_by(user_id=user_id).first()
        
        # Get KYC document status
        kyc_docs = KYCDocument.query.filter_by(user_id=user_id).all()
        
        # Determine current step and progress
        current_step = 'welcome'
        progress = 0
        
        if not signature:
            current_step = 'signature'
            progress = 20
        elif signature.status != 'completed':
            current_step = 'signature'
            progress = 20
        elif not kyc_docs:
            current_step = 'kyc_upload'
            progress = 40
        elif any(doc.status == 'rejected' for doc in kyc_docs):
            current_step = 'kyc_upload'
            progress = 40
        elif all(doc.status == 'approved' for doc in kyc_docs):
            current_step = 'complete'
            progress = 100
            user.onboarding_complete = True
            user.kyc_verified = True
            db.session.commit()
        else:
            current_step = 'review'
            progress = 80
        
        return jsonify({
            'current_step': current_step,
            'progress': progress,
            'onboarding_complete': user.onboarding_complete,
            'kyc_verified': user.kyc_verified,
            'agreement_signed': user.agreement_signed,
            'signature_status': signature.status if signature else 'not_started',
            'kyc_documents': [{
                'id': doc.id,
                'document_type': doc.document_type,
                'status': doc.status,
                'uploaded_at': doc.uploaded_at.isoformat()
            } for doc in kyc_docs],
            'next_action': get_next_action(current_step)
        })
        
    except Exception as e:
        logger.error(f"Error getting onboarding status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def get_next_action(current_step):
    """Get the next action description for the user"""
    actions = {
        'welcome': 'Click "Start Onboarding" to begin the process',
        'signature': 'Sign the Finder\'s Fee Contract to continue',
        'kyc_upload': 'Upload your government-issued ID for verification',
        'review': 'Your documents are under review. You will be notified once approved.',
        'complete': 'Onboarding complete! You now have full access to the platform.'
    }
    return actions.get(current_step, 'Continue with onboarding')

@onboarding_bp.route('/start-signature', methods=['POST'])
@jwt_required()
def start_signature():
    """Start the document signing process"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if signature already exists
        existing_signature = DocumentSignature.query.filter_by(user_id=user_id).first()
        if existing_signature and existing_signature.status == 'completed':
            return jsonify({
                'success': True,
                'message': 'Document already signed',
                'status': 'completed'
            })
        
        # Prepare user data for SignNow
        user_data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email
        }
        
        # Create signing flow with SignNow
        result = signnow_service.create_complete_signing_flow(user_data)
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to create signing flow')
            }), 500
        
        # Save or update signature record
        if existing_signature:
            existing_signature.document_id = result['document_id']
            existing_signature.invite_id = result['invite_id']
            existing_signature.status = 'pending'
            existing_signature.created_at = datetime.utcnow()
        else:
            signature = DocumentSignature(
                user_id=user_id,
                document_id=result['document_id'],
                invite_id=result['invite_id'],
                document_type='finders_fee_contract',
                status='pending'
            )
            db.session.add(signature)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'signing_link': result['signing_link'],
            'document_id': result['document_id'],
            'message': 'Document ready for signing'
        })
        
    except Exception as e:
        logger.error(f"Error starting signature: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@onboarding_bp.route('/signature-status/<document_id>', methods=['GET'])
@jwt_required()
def get_signature_status(document_id):
    """Check the status of a document signature"""
    try:
        user_id = get_jwt_identity()
        
        # Get signature record
        signature = DocumentSignature.query.filter_by(
            user_id=user_id,
            document_id=document_id
        ).first()
        
        if not signature:
            return jsonify({'error': 'Signature not found'}), 404
        
        # Get status from SignNow
        status_result = signnow_service.get_document_status(document_id)
        
        # Update local status if completed
        if status_result.get('status') == 'completed' and signature.status != 'completed':
            signature.status = 'completed'
            signature.signed_at = datetime.utcnow()
            
            # Update user agreement status
            user = User.query.get(user_id)
            user.agreement_signed = True
            
            db.session.commit()
        
        return jsonify({
            'status': signature.status,
            'document_id': document_id,
            'signed_at': signature.signed_at.isoformat() if signature.signed_at else None,
            'signnow_status': status_result
        })
        
    except Exception as e:
        logger.error(f"Error getting signature status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@onboarding_bp.route('/upload-kyc', methods=['POST'])
@jwt_required()
def upload_kyc_document():
    """Upload KYC document"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user has signed agreement
        if not user.agreement_signed:
            return jsonify({'error': 'Please sign the agreement first'}), 400
        
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        document_type = request.form.get('document_type', 'government_id')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload PDF, PNG, or JPG files.'}), 400
        
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join('/tmp', 'kyc_uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate secure filename
        filename = secure_filename(file.filename)
        unique_filename = f\"{user_id}_{document_type}_{uuid.uuid4().hex}_{filename}\"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Save file
        file.save(file_path)
        
        # Check if document already exists for this type
        existing_doc = KYCDocument.query.filter_by(
            user_id=user_id,
            document_type=document_type
        ).first()
        
        if existing_doc:
            # Update existing document
            existing_doc.file_path = file_path
            existing_doc.original_filename = filename
            existing_doc.status = 'submitted'
            existing_doc.uploaded_at = datetime.utcnow()
            existing_doc.reviewed_at = None
            existing_doc.admin_notes = None
            kyc_doc = existing_doc
        else:
            # Create new document record
            kyc_doc = KYCDocument(
                user_id=user_id,
                document_type=document_type,
                file_path=file_path,
                original_filename=filename,
                status='submitted'
            )
            db.session.add(kyc_doc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Document uploaded successfully',
            'document_id': kyc_doc.id,
            'document_type': document_type,
            'status': 'submitted'
        })
        
    except Exception as e:
        logger.error(f"Error uploading KYC document: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@onboarding_bp.route('/next-step', methods=['POST'])
@jwt_required()
def proceed_to_next_step():
    """Proceed to the next onboarding step"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        current_step = data.get('current_step')
        
        # Record step completion
        step = OnboardingStep(
            user_id=user_id,
            step_name=current_step,
            status='completed',
            completed_at=datetime.utcnow()
        )
        db.session.add(step)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Step {current_step} completed'
        })
        
    except Exception as e:
        logger.error(f"Error proceeding to next step: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@onboarding_bp.route('/webhook/signnow', methods=['POST'])
def signnow_webhook():
    """Handle SignNow webhook notifications"""
    try:
        data = request.get_json()
        
        # Extract document ID and status from webhook
        document_id = data.get('document_id')
        event_type = data.get('event_type')
        
        if not document_id:
            return jsonify({'error': 'Missing document_id'}), 400
        
        # Find signature record
        signature = DocumentSignature.query.filter_by(document_id=document_id).first()
        
        if not signature:
            logger.warning(f\"Webhook received for unknown document: {document_id}\")
            return jsonify({'message': 'Document not found'}), 404
        
        # Update signature status based on event
        if event_type == 'document.signed':
            signature.status = 'completed'
            signature.signed_at = datetime.utcnow()
            
            # Update user agreement status
            user = User.query.get(signature.user_id)
            if user:
                user.agreement_signed = True
            
            db.session.commit()
            logger.info(f\"Document {document_id} marked as signed via webhook\")
        
        return jsonify({'message': 'Webhook processed successfully'})
        
    except Exception as e:
        logger.error(f\"Error processing SignNow webhook: {e}\")
        return jsonify({'error': 'Internal server error'}), 500

@onboarding_bp.route('/test', methods=['GET'])
def test_onboarding():
    \"\"\"Test endpoint to verify onboarding routes are working\"\"\"
    return jsonify({
        'message': 'Onboarding routes are working',
        'signnow_available': signnow_service.is_available(),
        'endpoints': [
            '/api/onboarding/status',
            '/api/onboarding/start-signature',
            '/api/onboarding/upload-kyc',
            '/api/onboarding/next-step'
        ]
    })

