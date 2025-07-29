from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.database import db
from src.models.user import User
from src.models.onboarding import DocumentSignature, KYCDocument, OnboardingStep
from datetime import datetime
import os

onboarding_bp = Blueprint('onboarding', __name__)

@onboarding_bp.route('/status', methods=['GET'])
@jwt_required()
def get_onboarding_status():
    """Get current user's onboarding status"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get onboarding steps
        steps = OnboardingStep.query.filter_by(user_id=user_id).all()
        
        # Get document signatures
        signatures = DocumentSignature.query.filter_by(user_id=user_id).all()
        
        # Get KYC documents
        kyc_docs = KYCDocument.query.filter_by(user_id=user_id).all()
        
        return jsonify({
            'success': True,
            'user': user.to_dict(),
            'steps': [step.to_dict() for step in steps],
            'signatures': [sig.to_dict() for sig in signatures],
            'kyc_documents': [doc.to_dict() for doc in kyc_docs]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting onboarding status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@onboarding_bp.route('/next-step', methods=['POST'])
@jwt_required()
def proceed_to_next_step():
    """Proceed to the next onboarding step"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        step_name = data.get('step_name')
        step_data = data.get('data', {})
        
        # Create or update onboarding step
        step = OnboardingStep.query.filter_by(
            user_id=user_id, 
            step_name=step_name
        ).first()
        
        if not step:
            step = OnboardingStep(
                user_id=user_id,
                step_name=step_name,
                step_status='in_progress',
                started_at=datetime.utcnow(),
                data=step_data
            )
            db.session.add(step)
        else:
            step.step_status = 'in_progress'
            step.started_at = datetime.utcnow()
            step.data = step_data
        
        # Update user's onboarding step
        user.onboarding_step = user.onboarding_step + 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Proceeded to {step_name}',
            'step': step.to_dict(),
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error proceeding to next step: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@onboarding_bp.route('/complete-step', methods=['POST'])
@jwt_required()
def complete_step():
    """Mark an onboarding step as completed"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        step_name = data.get('step_name')
        step_data = data.get('data', {})
        
        # Find and update the step
        step = OnboardingStep.query.filter_by(
            user_id=user_id, 
            step_name=step_name
        ).first()
        
        if not step:
            return jsonify({'error': 'Step not found'}), 404
        
        step.step_status = 'completed'
        step.completed_at = datetime.utcnow()
        step.data = step_data
        
        # Update user status based on completed step
        if step_name == 'signature' and step.step_status == 'completed':
            user.finders_fee_contract_signed = True
            user.update_onboarding_status()
        elif step_name == 'kyc' and step.step_status == 'completed':
            user.kyc_status = 'submitted'
            user.update_onboarding_status()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Step {step_name} completed',
            'step': step.to_dict(),
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error completing step: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@onboarding_bp.route('/initiate-signature', methods=['POST'])
@jwt_required()
def initiate_signature():
    """Initiate document signature process (placeholder for SignNow integration)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        document_type = data.get('document_type', 'finders_fee_contract')
        
        # Create document signature record
        signature = DocumentSignature(
            user_id=user_id,
            document_type=document_type,
            signnow_template_id=os.getenv('SIGNNOW_TEMPLATE_ID'),
            signature_status='pending'
        )
        
        db.session.add(signature)
        db.session.commit()
        
        # TODO: Integrate with SignNow API in Phase 2
        # For now, return placeholder response
        
        return jsonify({
            'success': True,
            'message': 'Signature process initiated',
            'signature_id': signature.id,
            'document_type': document_type,
            'status': 'pending',
            'next_step': 'signature_pending'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error initiating signature: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@onboarding_bp.route('/upload-kyc', methods=['POST'])
@jwt_required()
def upload_kyc_document():
    """Upload KYC document (placeholder for file upload)"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # TODO: Implement file upload in Phase 3
        # For now, return placeholder response
        
        data = request.get_json()
        document_type = data.get('document_type')
        file_name = data.get('file_name')
        
        if not document_type or not file_name:
            return jsonify({'error': 'Document type and file name required'}), 400
        
        # Create KYC document record
        kyc_doc = KYCDocument(
            user_id=user_id,
            document_type=document_type,
            file_path=f'/uploads/{user_id}/{file_name}',
            file_name=file_name,
            file_size=0,  # Will be set when actual file upload is implemented
            mime_type='application/pdf',  # Placeholder
            verification_status='pending'
        )
        
        db.session.add(kyc_doc)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'KYC document uploaded successfully',
            'document': kyc_doc.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error uploading KYC document: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@onboarding_bp.route('/kyc-status', methods=['GET'])
@jwt_required()
def get_kyc_status():
    """Get KYC verification status"""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        kyc_docs = KYCDocument.query.filter_by(user_id=user_id).all()
        
        return jsonify({
            'success': True,
            'kyc_status': user.kyc_status,
            'rejection_reason': user.kyc_rejection_reason,
            'documents': [doc.to_dict() for doc in kyc_docs]
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting KYC status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

