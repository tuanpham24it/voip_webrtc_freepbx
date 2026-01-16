# -*- coding: utf-8 -*-
#################################################################################
#
# Module Name: Voip Webrtc Freepbx - Recording Controller
# Description: Controller for managing VoIP call recordings
#
# Copyright (c) 2025
# Author: Mohamed Samir Abouelez 
# Website: https://odoo-vip.com
# Email: kenzey0man@gmail.com
# Phone: +20 100 057 3614
#
# License: Odoo Proprietary License v1.0 (OPL-1)
# License URL: https://www.odoo.com/documentation/master/legal/licenses.html#odoo-proprietary-license
#
# ---------------------------------------------------------------------------
# ⚠️ Usage and Modification Restrictions:
#
# - This software is licensed under the Odoo Proprietary License (OPL-1).
# - You are NOT permitted to modify, copy, redistribute, or reuse any part of
#   this source code without the explicit written consent of the author.
# - Partial use, extraction, reverse engineering, or integration of this code
#   into other projects without authorization is strictly prohibited.
# - Any commercial use or deployment must be approved directly by:
#     Mohamed Samir Abouelez 
#     Email: kenzey0man@gmail.com
#
# ---------------------------------------------------------------------------
# © 2025 — All Rights Reserved — Mohamed Samir Abouelez 
#################################################################################
from odoo import http, fields
from odoo.http import request, Response
import json
import base64
import time
import logging
from .base_controller import VoipBaseController

_logger = logging.getLogger(__name__)


class VoipRecordingController(VoipBaseController):
    """Controller for managing VoIP call recordings"""

    @http.route('/voip/recording/create', type='json', auth='user', csrf=False)
    def create_recording(self, call_id, **kwargs):
        """Create a recording record"""
        try:
            call = request.env['voip.call'].browse(call_id)
            
            if not call.exists():
                return {'success': False, 'error': 'Call not found'}
            
            recording_data = {
                'name': kwargs.get('name', f"Recording - {call.name}"),
                'call_id': call_id,
                'recording_type': kwargs.get('recording_type', 'automatic'),
                'state': kwargs.get('state', 'recording'),
                'format': kwargs.get('format', 'wav'),
            }
            
            recording = request.env['voip.recording'].sudo().create(recording_data)
            
            return {
                'success': True,
                'recording_id': recording.id
            }
        except Exception as e:
            _logger.exception("Error creating recording: %s", str(e))
            return {'success': False, 'error': str(e)}

    @http.route('/voip/recording/upload', type='http', auth='user', methods=['POST'], csrf=False)
    def upload_recording(self, recording_id, **kwargs):
        """Upload recording file"""
        try:
            recording = request.env['voip.recording'].sudo().browse(int(recording_id))
            
            if not recording.exists():
                return Response(
                    json.dumps({'success': False, 'error': 'Recording not found'}),
                    content_type='application/json',
                    status=404
                )
            
            file_data = request.httprequest.files.get('file')
            if not file_data:
                return Response(
                    json.dumps({'success': False, 'error': 'No file provided'}),
                    content_type='application/json',
                    status=400
                )
            
            import base64
            file_content = base64.b64encode(file_data.read())
            
            recording.write({
                'recording_file': file_content,
                'recording_filename': file_data.filename,
                'file_size': len(file_content),
                'state': 'completed',
            })
            
            return Response(
                json.dumps({'success': True, 'recording_id': recording.id}),
                content_type='application/json'
            )
        except Exception as e:
            _logger.exception("Error uploading recording: %s", str(e))
            return Response(
                json.dumps({'success': False, 'error': str(e)}),
                content_type='application/json',
                status=500
            )

    @http.route('/voip_webrtc_freepbx/save_recording', type='http', auth='user', methods=['POST'], csrf=False)
    def save_recording(self):
        """Save call recording to server"""
        try:
            _logger.info('🔧 VoIP Controller Debug: ===== SAVE RECORDING START =====')
            _logger.info('🔧 VoIP Controller Debug: User: %s', request.env.user.name)
            _logger.info('🔧 VoIP Controller Debug: User ID: %s', request.env.user.id)
            _logger.info('🔧 VoIP Controller Debug: Request method: %s', request.httprequest.method)
            _logger.info('🔧 VoIP Controller Debug: Content type: %s', request.httprequest.content_type)
            _logger.info('🔧 VoIP Controller Debug: Content length: %s', request.httprequest.content_length)
            
            # Get uploaded file
            recording_file = request.httprequest.files.get('recording')
            call_id_str = request.httprequest.form.get('call_id', 'unknown')
            duration = int(request.httprequest.form.get('duration', 0))
            
            _logger.info('🔧 VoIP Controller Debug: Call ID string: %s', call_id_str)
            _logger.info('🔧 VoIP Controller Debug: Duration from request: %s seconds', duration)
            _logger.info('🔧 VoIP Controller Debug: Recording file: %s', recording_file)
            
            if not recording_file:
                _logger.error('🔧 VoIP Controller Debug: No recording file provided')
                return json.dumps({'error': 'No recording file provided'})
            
            _logger.info('🔧 VoIP Controller Debug: Recording file name: %s', recording_file.filename)
            _logger.info('🔧 VoIP Controller Debug: Recording file size: %s bytes', len(recording_file.read()))
            recording_file.seek(0)  # Reset file pointer
            
            # Handle call_id - it can be Odoo call ID, SIP Call ID, or "unknown"
            call_id = None
            call = None
            
            if call_id_str and call_id_str != 'unknown':
                # First try to find by Odoo call ID (numeric)
                try:
                    call_id_int = int(call_id_str)
                    call = request.env['voip.call'].browse(call_id_int)
                    if call.exists():
                        call_id = call.id
                        _logger.info('🔧 VoIP Controller Debug: Found call by Odoo ID: %s', call_id)
                except (ValueError, TypeError):
                    pass
                
                # If not found, try to find by SIP Call ID
                if not call_id:
                    call = request.env['voip.call'].search([
                        ('call_id', '=', call_id_str)
                    ], limit=1, order='create_date desc')
                    
                    if call:
                        call_id = call.id
                        _logger.info('🔧 VoIP Controller Debug: Found call by SIP Call ID: %s -> %s', call_id_str, call_id)
                    else:
                        _logger.warning('🔧 VoIP Controller Debug: No call found for SIP Call ID: %s', call_id_str)
            
            # If call found, update timing information if needed (especially for recordings saved after call ends)
            if call and call.exists():
                # Update end_time if not set
                if not call.end_time:
                    call.write({'end_time': fields.Datetime.now()})
                    _logger.info('🔧 VoIP Controller Debug: Updated call end_time from recording save')
                
                # Auto-update state if end_time exists but state is still 'ringing'
                if call.end_time and call.state == 'ringing':
                    if call.answer_time:
                        call.write({'state': 'completed'})
                        _logger.info('🔧 VoIP Controller Debug: Updated call state to completed')
                    else:
                        call.write({'state': 'missed'})
                        _logger.info('🔧 VoIP Controller Debug: Updated call state to missed')
                
                # Don't set answer_time here - it should only be set when call is actually answered
                # answer_time will be set when call state changes to 'in_progress' via update_call
            
            # Check if recording already exists for this call (one recording per call)
            recording = None
            if call_id:
                # Search for existing recording for this call
                existing_recording = request.env['voip.recording'].sudo().search([
                    ('call_id', '=', call_id)
                ], limit=1, order='create_date desc')
                
                if existing_recording:
                    recording = existing_recording
                    _logger.info('🔧 VoIP Controller Debug: Found existing recording ID: %s for call ID: %s', recording.id, call_id)
                else:
                    _logger.info('🔧 VoIP Controller Debug: No existing recording found for call ID: %s, will create new one', call_id)
            
            # If no call found, create a standalone recording
            if not call_id:
                _logger.info('🔧 VoIP Controller Debug: Creating standalone recording without call reference')
                call_id = None
            
            # Use duration from JavaScript (calculated from actual call time)
            _logger.info('🔧 VoIP Controller Debug: Using duration from JavaScript: %s seconds', duration)
            
            # Read file data
            file_data = recording_file.read()
            _logger.info('🔧 VoIP Controller Debug: File data size: %s bytes', len(file_data))
            
            # Encode to base64
            attachment_data = base64.b64encode(file_data)
            _logger.info('🔧 VoIP Controller Debug: Base64 data size: %s bytes', len(attachment_data))
            
            # Prepare recording data
            if call_id:
                recording_filename = f'call_recording_{call_id}_{int(time.time())}.webm'
            else:
                recording_filename = f'standalone_recording_{call_id_str}_{int(time.time())}.webm'
            
            # If recording exists, update it instead of creating new one
            if recording:
                _logger.info('🔧 VoIP Controller Debug: Updating existing recording ID: %s', recording.id)
                recording.write({
                    'recording_file': attachment_data,
                    'recording_filename': recording_filename,
                    'file_size': len(file_data),
                    'duration': duration,
                    'state': 'completed',
                })
                _logger.info('🔧 VoIP Controller Debug: Recording updated successfully')
            else:
                # Create new recording record
                if call_id:
                    recording_data = {
                        'name': f'Call Recording - {call_id}',
                        'call_id': call_id,
                        'duration': duration,
                        'state': 'completed',  # Mark as completed since we have the file
                        'user_id': request.env.user.id,  # Set current user
                        'recording_file': attachment_data,
                        'recording_filename': recording_filename,
                        'file_size': len(file_data),
                        # caller/callee will be auto-populated by create() method
                    }
                    _logger.info('🔧 VoIP Controller Debug: Call duration (for reference): %s seconds', call.duration if call else 0)
                else:
                    recording_data = {
                        'name': f'Standalone Recording - {call_id_str}',
                        'call_id': False,  # No call reference
                        'duration': duration,
                        'state': 'completed',  # Mark as completed since we have the file
                        'user_id': request.env.user.id,  # Set current user
                        'recording_file': attachment_data,
                        'recording_filename': recording_filename,
                        'file_size': len(file_data),
                    }
                    _logger.info('🔧 VoIP Controller Debug: Creating standalone recording')
                
                # _logger.info('🔧 VoIP Controller Debug: Recording data: %s', recording_data)
                
                # Create recording record (attachment will be auto-created because attachment=True)
                recording = request.env['voip.recording'].sudo().create(recording_data)
                _logger.info('🔧 VoIP Controller Debug: Recording record created with ID: %s', recording.id)
            
            _logger.info('🔧 VoIP Controller Debug: Recording saved successfully')
            _logger.info('🔧 VoIP Controller Debug: Final recording ID: %s', recording.id)
            _logger.info('🔧 VoIP Controller Debug: File size: %s bytes', recording.file_size)
            _logger.info('🔧 VoIP Controller Debug: ===== SAVE RECORDING END =====')
            
            return json.dumps({
                'success': True,
                'recording_id': recording.id,
                'file_size': recording.file_size,
                'message': 'Recording saved successfully'
            })
            
        except Exception as e:
            _logger.error('🔧 VoIP Controller Debug: ===== SAVE RECORDING ERROR =====')
            _logger.error('🔧 VoIP Controller Debug: Error type: %s', type(e).__name__)
            _logger.error('🔧 VoIP Controller Debug: Error message: %s', str(e))
            _logger.error('🔧 VoIP Controller Debug: Error details: %s', repr(e))
            _logger.error('🔧 VoIP Controller Debug: ===== END ERROR =====')
            return json.dumps({'error': str(e)})
