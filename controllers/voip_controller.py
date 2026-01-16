# -*- coding: utf-8 -*-
#################################################################################
#
# Module Name: Voip Webrtc Freepbx
# Description: Establishes real-time VoIP communication between Odoo and FreePBX 
#              using WebRTC and PJSIP for seamless browser-based calling integration.
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
import logging
import base64
import time
from ..utils.logging_utils import VoipLoggingUtils

_logger = logging.getLogger(__name__)


class VoipController(http.Controller):

    @http.route('/voip/test', type='json', auth='user', csrf=False)
    def test_endpoint(self, **kwargs):
        """Simple test endpoint to verify controller functionality"""
        return {
            'status': 'success',
            'message': 'VoIP controller is working',
            'timestamp': fields.Datetime.now().isoformat()
        }

    @http.route('/voip/config', type='json', auth='user', csrf=False)
    def get_voip_config(self, **kwargs):
        """Get VoIP configuration for current user"""
        try:
            _logger.info("🔧 VoIP Config Debug: Starting get_voip_config")
            _logger.info(f"🔧 VoIP Config Debug: User: {request.env.user.name} (ID: {request.env.user.id})")
            
            VoipLoggingUtils.log_if_enabled(
                request.env, _logger, 'info', 
                'Getting VoIP config for user %s', request.env.user.name
            )
            
            user = request.env.user
            _logger.info(f"🔧 VoIP Config Debug: Searching for VoIP user for user ID: {user.id}")
            
            voip_user = request.env['voip.user'].sudo().search([
                ('user_id', '=', user.id),
                ('active', '=', True)
            ])
            
            _logger.info(f"🔧 VoIP Config Debug: Found VoIP user: {voip_user.exists()}")
            if voip_user:
                _logger.info(f"🔧 VoIP Config Debug: VoIP user name: {voip_user.name}")
                _logger.info(f"🔧 VoIP Config Debug: VoIP user server: {voip_user.server_id.name if voip_user.server_id else 'None'}")
            
            if not voip_user:
                _logger.warning("🔧 VoIP Config Debug: No VoIP user found for current user")
                return {
                    'error': 'No VoIP configuration found for current user'
                }
            
            _logger.info("🔧 VoIP Config Debug: Updating last login")
            # Update last login
            voip_user.update_last_login()
            
            _logger.info("🔧 VoIP Config Debug: Getting VoIP config from user")
            config = voip_user.get_voip_config()
            _logger.info(f"🔧 VoIP Config Debug: Config retrieved: {bool(config)}")
            
            _logger.info("🔧 VoIP Config Debug: Getting logging config")
            # Add logging configuration
            logging_config = VoipLoggingUtils.get_js_logging_config(request.env, voip_user.server_id.id)
            config['logging'] = logging_config
            _logger.info(f"🔧 VoIP Config Debug: Logging config added: {bool(logging_config)}")
            
            _logger.info("🔧 VoIP Config Debug: Returning config successfully")
            return {
                'success': True,
                'config': config
            }
        except Exception as e:
            _logger.error("🔧 VoIP Config Debug: Exception occurred")
            _logger.error(f"🔧 VoIP Config Debug: Exception type: {type(e).__name__}")
            _logger.error(f"🔧 VoIP Config Debug: Exception message: {str(e)}")
            import traceback
            _logger.error(f"🔧 VoIP Config Debug: Traceback: {traceback.format_exc()}")
            
            VoipLoggingUtils.log_if_enabled(
                request.env, _logger, 'error', 
                "Error getting VoIP config: %s", str(e)
            )
            return {
                'error': str(e)
            }

    # Removed duplicate /voip/call/create - handled by call_controller.py

    # Removed duplicate /voip/call/update - handled by call_controller.py

    # Removed duplicate /voip/call/update_duration - handled by call_controller.py

    # Removed duplicate /voip/call/list - handled by call_controller.py

    # Removed duplicate /voip/recording/create - handled by recording_controller.py

    # Removed duplicate /voip/recording/upload - handled by recording_controller.py

    # Removed duplicate /voip/search/partner - handled by call_controller.py

    # Removed duplicate /voip/contacts/list - handled by call_controller.py
    
    
    @http.route('/voip/hold-music/list', type='json', auth='user', methods=['POST'], csrf=False)
    def get_hold_music_list(self, **kwargs):
        """Get list of available hold music files"""
        try:
            user = request.env.user
            current_voip_user = request.env['voip.user'].search([
                ('user_id', '=', user.id),
                ('active', '=', True)
            ])
            
            if not current_voip_user:
                return {'success': False, 'error': 'No VoIP user found'}
            
            # Get hold music from server configuration
            server = current_voip_user.server_id
            hold_music_list = []
            
            # Parse hold music configuration from server
            if server.hold_music_config:
                try:
                    import json
                    music_config = json.loads(server.hold_music_config)
                    for music in music_config.get('music_files', []):
                        hold_music_list.append({
                            'id': music.get('id'),
                            'name': music.get('name'),
                            'file_path': music.get('file_path'),
                            'server': server.name,
                            'server_id': server.id
                        })
                except (json.JSONDecodeError, KeyError) as e:
                    _logger.warning(f"⚠️ Invalid hold music config: {str(e)}")
            
            # Add default hold music if none configured
            if not hold_music_list:
                hold_music_list.append({
                    'id': 'default',
                    'name': 'Default Hold Music',
                    'file_path': '/var/lib/asterisk/moh/default.wav',
                    'server': server.name,
                    'server_id': server.id
                })
            
            _logger.info(f"🎵 Hold Music List: Found {len(hold_music_list)} music files")
            
            return {
                'success': True,
                'music_list': hold_music_list,
                'total': len(hold_music_list)
            }
            
        except Exception as e:
            _logger.error(f"❌ Failed to get hold music list: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

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
            call_id_str = request.httprequest.form.get('call_id', '0')
            duration = int(request.httprequest.form.get('duration', 0))
            
            # Convert call_id to integer
            try:
                call_id = int(call_id_str)
            except (ValueError, TypeError):
                _logger.error('🔧 VoIP Controller Debug: Invalid call_id: %s', call_id_str)
                return json.dumps({'error': 'Invalid call_id'})
            
            _logger.info('🔧 VoIP Controller Debug: Call ID: %s (type: %s)', call_id, type(call_id).__name__)
            _logger.info('🔧 VoIP Controller Debug: Duration from request: %s seconds', duration)
            _logger.info('🔧 VoIP Controller Debug: Recording file: %s', recording_file)
            
            if not recording_file:
                _logger.error('🔧 VoIP Controller Debug: No recording file provided')
                return json.dumps({'error': 'No recording file provided'})
            
            _logger.info('🔧 VoIP Controller Debug: Recording file name: %s', recording_file.filename)
            _logger.info('🔧 VoIP Controller Debug: Recording file size: %s bytes', len(recording_file.read()))
            recording_file.seek(0)  # Reset file pointer
            
            # Verify call exists
            call = request.env['voip.call'].browse(call_id)
            if not call.exists():
                _logger.error('🔧 VoIP Controller Debug: Call with ID %s not found', call_id)
                return json.dumps({'error': f'Call {call_id} not found'})
            
            # Use duration from JavaScript (calculated from actual call time)
            # Don't use call.duration because end_time might not be updated yet
            _logger.info('🔧 VoIP Controller Debug: Using duration from JavaScript: %s seconds', duration)
            _logger.info('🔧 VoIP Controller Debug: Call duration (for reference): %s seconds', call.duration if call.duration else 0)
            
            # Create voip.recording record
            recording_data = {
                'name': f'Call Recording - {call_id}',
                'call_id': call_id,
                'duration': duration,
                'state': 'completed',  # Mark as completed since we have the file
                # user_id will be auto-populated from call_id.odoo_user_id (related field)
                # caller/callee will be auto-populated by create() method
            }
            
            # _logger.info('🔧 VoIP Controller Debug: Recording data: %s', recording_data)
            
            # Read file data
            file_data = recording_file.read()
            _logger.info('🔧 VoIP Controller Debug: File data size: %s bytes', len(file_data))
            
            # Encode to base64
            attachment_data = base64.b64encode(file_data)
            _logger.info('🔧 VoIP Controller Debug: Base64 data size: %s bytes', len(attachment_data))
            
            # Add recording file and filename to recording data
            recording_data['recording_file'] = attachment_data
            recording_data['recording_filename'] = f'call_recording_{call_id}_{int(time.time())}.webm'
            recording_data['file_size'] = len(file_data)
            
            _logger.info('🔧 VoIP Controller Debug: Updated recording data with file')
            
            # Create recording record (attachment will be auto-created because attachment=True)
            recording = request.env['voip.recording'].create(recording_data)
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

    @http.route(['/pbx/webhook', '/pbx/webhook/jsonrpc'], type='http', auth='public', methods=['POST'], csrf=False)
    def pbx_webhook(self, **kwargs):
        """
        Receive FreePBX AMI events

        IMPORTANT: 
        - auth='public' is required! Do NOT use auth='user'
        - X-API-Key header is REQUIRED for authentication
        - Each VoIP server has its own unique API key
        
        Required Headers:
        - X-API-Key: Your server's unique API key (from voip.server record)
        
        Expected payload:
        {
            "event_type": "Newchannel",
            "timestamp": "2025-10-20T12:00:00",
            "data": {
                "Event": "Newchannel",
                "Channel": "PJSIP/1001-00000001",
                "CallerIDNum": "1001",
                ... (all AMI event data)
            }
        }
        
        Example curl command:
        curl -X POST https://your-odoo-domain/pbx/webhook \\
             -H "Content-Type: application/json" \\
             -H "X-API-Key: your-server-api-key" \\
             -d '{"event_type": "Newchannel", "timestamp": "2025-10-20T12:00:00", "data": {...}}'
        """
        try:
            # Log incoming request
            _logger.info("=" * 80)
            _logger.info("🔔 FREEPBX WEBHOOK RECEIVED")
            _logger.info("=" * 80)
            _logger.info(f"📡 Remote IP: {request.httprequest.remote_addr}")
            _logger.info(f"📡 Method: {request.httprequest.method}")
            _logger.info(f"📡 Content-Type: {request.httprequest.content_type}")
            _logger.info(f"📡 Content-Length: {request.httprequest.content_length}")

            # ===== API KEY AUTHENTICATION (Required) =====
            api_key = request.httprequest.headers.get('X-API-Key')
            _logger.info(f"🔐 API Key: {'Present' if api_key else 'Missing'}")

            # API Key is required
            if not api_key:
                _logger.warning("⚠️  API Key missing!")
                return Response(
                    json.dumps({'success': False, 'error': 'API key required'}),
                    status=401,
                    content_type='application/json'
                )

            # Search for VoIP server by API key
            VoipServer = request.env['voip.server'].sudo()
            server = VoipServer.search([
                ('api_key', '=', api_key),
                ('active', '=', True)
            ])

            if not server:
                _logger.warning(f"❌ Invalid API key from {request.httprequest.remote_addr}")
                return Response(
                    json.dumps({'success': False, 'error': 'Invalid API key - Server not found'}),
                    status=403,
                    content_type='application/json'
                )

            _logger.info(f"✅ API Key validated - Server: {server.name} (ID: {server.id})")
            
            # Store server_id in context for later use
            request.update_context(voip_server_id=server.id)

            # ===== PARSE REQUEST DATA =====
            try:
                raw_data = request.httprequest.data.decode('utf-8')
                _logger.info(f"📥 Raw data (first 500 chars): {raw_data[:500]}")

                data = json.loads(raw_data)
                _logger.info(f"📦 Parsed JSON successfully")
            except json.JSONDecodeError as e:
                _logger.error(f"❌ Invalid JSON: {e}")
                return Response(
                    json.dumps({'success': False, 'error': 'Invalid JSON format'}),
                    status=400,
                    content_type='application/json'
                )

            # ===== EXTRACT EVENT DATA =====
            event_type = data.get('event_type', 'Unknown')
            timestamp = data.get('timestamp')
            event_data = data.get('data', {})

            _logger.info(f"📞 Event Type: {event_type}")
            _logger.info(f"⏰ Timestamp: {timestamp}")
            _logger.info(f"🖥️  Server: {server.name} (ID: {server.id})")
            _logger.info(f"📊 Event Data: {json.dumps(event_data, indent=2)}")
            
            # Save event to database for reporting
            try:
                request.env['voip.event'].sudo().create_from_webhook(event_data, server.id)
            except Exception as e:
                _logger.warning(f"⚠️ Failed to save event to database: {str(e)}")

            # ===== PROCESS EVENT =====
            # Extract common call information
            channel = event_data.get('Channel', 'N/A')
            caller_id = event_data.get('CallerIDNum', 'N/A')
            caller_name = event_data.get('CallerIDName', 'N/A')
            exten = event_data.get('Exten', 'N/A')
            context = event_data.get('Context', 'N/A')
            uniqueid = event_data.get('Uniqueid', 'N/A')

            _logger.info(f"📞 Call Details:")
            _logger.info(f"   - Channel: {channel}")
            _logger.info(f"   - Caller ID: {caller_id} ({caller_name})")
            _logger.info(f"   - Extension: {exten}")
            _logger.info(f"   - Context: {context}")
            _logger.info(f"   - Unique ID: {uniqueid}")

            # ===== YOUR BUSINESS LOGIC HERE =====
            # Process different event types
            if event_type == 'Newchannel':
                _logger.info("📞 Processing New Channel event...")
                # TODO: Create call record, update CRM, etc.

            elif event_type == 'Hangup':
                _logger.info("📞 Processing Hangup event...")
                # TODO: Update call duration, status, etc.

            elif event_type == 'Dial':
                _logger.info("📞 Processing Dial event...")
                # TODO: Track outgoing calls, update contact, etc.

            elif event_type == 'Bridge':
                _logger.info("📞 Processing Bridge event...")
                # TODO: Track call connections, conference, etc.

            elif event_type == 'PeerStatus':
                _logger.info("📞 Processing PeerStatus event...")
                self.handle_peer_status_event(event_data, server.id)

            elif event_type == 'Newstate':
                _logger.info("📞 Processing Newstate event...")
                self.handle_newstate_event(event_data, server.id)

            elif event_type == 'Newchannel':
                _logger.info("📞 Processing Newchannel event...")
                self.handle_newchannel_event(event_data, server.id)

            else:
                _logger.info(f"📞 Event {event_type} received (no specific handler)")

            # ===== EXAMPLE: Search for contact by phone =====
            if caller_id and caller_id != 'N/A':
                Partner = request.env['res.partner'].sudo()
                # Clean phone number (remove spaces, dashes, etc.)
                clean_phone = caller_id.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

                partners = Partner.search([
                    '|', '|',
                    ('phone', 'ilike', clean_phone),
                    ('mobile', 'ilike', clean_phone),
                    ('phone', 'ilike', caller_id)
                ])

                if partners:
                    _logger.info(f"👤 Found contact: {partners[0].name} (ID: {partners[0].id})")
                    # TODO: Update contact activity, create call log, etc.
                else:
                    _logger.info(f"👤 No contact found for: {caller_id}")
                    # TODO: Create notification for new contact, etc.

            # ===== SUCCESS RESPONSE =====
            _logger.info("✅ Event processed successfully!")
            _logger.info("=" * 80)

            return Response(
                json.dumps({
                    'success': True,
                    'message': 'Event received and processed',
                    'server_id': server.id,
                    'server_name': server.name,
                    'event_type': event_type,
                    'uniqueid': uniqueid
                }),
                status=200,
                content_type='application/json'
            )

        except Exception as e:
            _logger.exception("❌ ERROR in FreePBX Webhook")
            _logger.error("=" * 80)
            return Response(
                json.dumps({
                    'success': False,
                    'error': str(e)
                }),
                status=500,
                content_type='application/json'
            )

    @http.route('/voip_webrtc_freepbx/hold_music/file/<int:music_id>', type='http', auth='user', methods=['GET'])
    @http.route('/voip/hold_music/file/<int:music_id>', type='http', auth='user', methods=['GET'])
    def get_hold_music_file(self, music_id):
        """Serve hold music file"""
        try:
            music = request.env['voip.hold.music'].browse(music_id)
            
            if not music.exists():
                return Response('Music not found', status=404)
            
            if not music.music_file:
                return Response('No music file', status=404)
            
            # Increment usage count
            music.action_increment_usage()
            
            # Determine content type
            content_type = 'audio/mpeg'
            if music.format == 'wav':
                content_type = 'audio/wav'
            elif music.format == 'ogg':
                content_type = 'audio/ogg'
            elif music.format == 'm4a':
                content_type = 'audio/mp4'
            
            # Decode the binary data
            import base64
            try:
                music_data = base64.b64decode(music.music_file)
            except Exception as e:
                _logger.error(f"Error decoding music file: {e}")
                return Response('Invalid music file', status=500)
            
            return Response(
                music_data,
                content_type=content_type,
                headers=[
                    ('Content-Disposition', f'inline; filename="{music.music_filename or music.name}"'),
                    ('Cache-Control', 'public, max-age=3600'),
                    ('Content-Length', str(len(music_data))),
                ]
            )
            
        except Exception as e:
            _logger.exception("Error serving hold music file: %s", str(e))
            return Response('Error serving music file', status=500)

    @http.route('/voip_webrtc_freepbx/hold_music/test/<int:music_id>', type='http', auth='user', methods=['GET'])
    @http.route('/voip/hold_music/test/<int:music_id>', type='http', auth='user', methods=['GET'])
    def test_hold_music(self, music_id):
        """Test hold music with a simple player"""
        try:
            music = request.env['voip.hold.music'].browse(music_id)
            
            if not music.exists():
                return Response('Music not found', status=404)
            
            if not music.music_file:
                return Response('No music file available', status=404)
            
            # Get music URL
            music_url = f'/voip_webrtc_freepbx/hold_music/file/{music_id}'
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Test Hold Music - {music.name}</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: 0;
                        padding: 20px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                    }}
                    .test-container {{
                        background: white;
                        border-radius: 15px;
                        padding: 40px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                        text-align: center;
                        max-width: 500px;
                        width: 100%;
                    }}
                    .music-icon {{
                        font-size: 64px;
                        color: #667eea;
                        margin-bottom: 20px;
                    }}
                    h1 {{
                        color: #333;
                        margin-bottom: 10px;
                    }}
                    .music-info {{
                        color: #666;
                        margin-bottom: 30px;
                        font-size: 16px;
                    }}
                    .audio-player {{
                        width: 100%;
                        margin: 20px 0;
                        border-radius: 10px;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    }}
                    .controls {{
                        margin-top: 20px;
                    }}
                    .btn {{
                        background: #667eea;
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 25px;
                        cursor: pointer;
                        font-size: 16px;
                        margin: 0 10px;
                        transition: all 0.3s ease;
                    }}
                    .btn:hover {{
                        background: #5a6fd8;
                        transform: translateY(-2px);
                    }}
                    .status {{
                        margin-top: 20px;
                        padding: 15px;
                        border-radius: 10px;
                        background: #f8f9fa;
                        border-left: 4px solid #667eea;
                    }}
                    .volume-control {{
                        margin: 20px 0;
                        text-align: left;
                    }}
                    .volume-control label {{
                        display: block;
                        margin-bottom: 10px;
                        font-weight: bold;
                        color: #333;
                    }}
                    .volume-slider {{
                        width: 100%;
                        height: 8px;
                        border-radius: 5px;
                        background: #ddd;
                        outline: none;
                        -webkit-appearance: none;
                    }}
                    .volume-slider::-webkit-slider-thumb {{
                        -webkit-appearance: none;
                        appearance: none;
                        width: 20px;
                        height: 20px;
                        border-radius: 50%;
                        background: #667eea;
                        cursor: pointer;
                    }}
                </style>
            </head>
            <body>
                <div class="test-container">
                    <div class="music-icon">🎵</div>
                    <h1>Test Hold Music</h1>
                    <div class="music-info">
                        <strong>{music.name}</strong><br>
                        Format: {music.format.upper()}<br>
                        Size: {music.file_size or 'Unknown'} bytes<br>
                        Quality: {music.quality or 'Unknown'}
                    </div>
                    
                    <audio id="musicPlayer" class="audio-player" controls preload="auto">
                        <source src="{music_url}" type="audio/{music.format}">
                        Your browser does not support the audio element.
                    </audio>
                    
                    <div class="volume-control">
                        <label for="volumeSlider">Volume: <span id="volumeValue">70</span>%</label>
                        <input type="range" id="volumeSlider" class="volume-slider" 
                               min="0" max="100" value="70" step="1">
                    </div>
                    
                    <div class="controls">
                        <button class="btn" onclick="playMusic()">▶️ Play</button>
                        <button class="btn" onclick="pauseMusic()">⏸️ Pause</button>
                        <button class="btn" onclick="stopMusic()">⏹️ Stop</button>
                        <button class="btn" onclick="testLoop()">🔄 Test Loop</button>
                    </div>
                    
                    <div class="status" id="status">
                        Ready to test music. Click Play to start.
                    </div>
                </div>
                
                <script>
                    const audio = document.getElementById('musicPlayer');
                    const volumeSlider = document.getElementById('volumeSlider');
                    const volumeValue = document.getElementById('volumeValue');
                    const status = document.getElementById('status');
                    
                    // Set initial volume
                    audio.volume = 0.7;
                    
                    // Volume control
                    volumeSlider.addEventListener('input', function() {{
                        const volume = this.value / 100;
                        audio.volume = volume;
                        volumeValue.textContent = this.value;
                    }});
                    
                    // Audio event listeners
                    audio.addEventListener('loadstart', () => {{
                        status.innerHTML = '🔄 Loading music file...';
                    }});
                    
                    audio.addEventListener('canplay', () => {{
                        status.innerHTML = '✅ Music loaded successfully! Ready to play.';
                    }});
                    
                    audio.addEventListener('play', () => {{
                        status.innerHTML = '▶️ Playing: ' + audio.currentSrc;
                    }});
                    
                    audio.addEventListener('pause', () => {{
                        status.innerHTML = '⏸️ Music paused';
                    }});
                    
                    audio.addEventListener('ended', () => {{
                        status.innerHTML = '🏁 Music finished playing';
                    }});
                    
                    audio.addEventListener('error', (e) => {{
                        status.innerHTML = '❌ Error loading music: ' + e.message;
                        console.error('Audio error:', e);
                    }});
                    
                    // Control functions
                    function playMusic() {{
                        audio.play().catch(e => {{
                            status.innerHTML = '❌ Error playing music: ' + e.message;
                        }});
                    }}
                    
                    function pauseMusic() {{
                        audio.pause();
                    }}
                    
                    function stopMusic() {{
                        audio.pause();
                        audio.currentTime = 0;
                    }}
                    
                    function testLoop() {{
                        audio.loop = !audio.loop;
                        status.innerHTML = audio.loop ? '🔄 Loop enabled' : '🔄 Loop disabled';
                    }}
                    
                    // Auto-play when loaded (if user interaction allows)
                    audio.addEventListener('canplay', () => {{
                        // Only auto-play if user has interacted with the page
                        if (document.hasFocus()) {{
                            audio.play().catch(() => {{
                                // Auto-play blocked, that's okay
                            }});
                        }}
                    }});
                </script>
            </body>
            </html>
            """
            
            return Response(html, content_type='text/html')
            
        except Exception as e:
            _logger.exception("Error in test_hold_music: %s", str(e))
            return Response('Error loading test page', status=500)

    @http.route('/voip_webrtc_freepbx/hold_music/preview/<int:music_id>', type='http', auth='user', methods=['GET'])
    def preview_hold_music(self, music_id):
        """Preview hold music in a new window"""
        try:
            music = request.env['voip.hold.music'].browse(music_id)
            
            if not music.exists():
                return Response('Music not found', status=404)
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Hold Music Preview - {music.name}</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background: #f5f5f5;
                        margin: 0;
                        padding: 20px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                    }}
                    .preview-container {{
                        background: white;
                        border-radius: 10px;
                        padding: 30px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                        text-align: center;
                        max-width: 400px;
                    }}
                    .music-icon {{
                        font-size: 48px;
                        color: #9b8bb3;
                        margin-bottom: 20px;
                    }}
                    .music-name {{
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 10px;
                        color: #333;
                    }}
                    .music-description {{
                        color: #666;
                        margin-bottom: 20px;
                    }}
                    audio {{
                        width: 100%;
                        margin: 20px 0;
                    }}
                    .controls {{
                        margin-top: 20px;
                    }}
                    .btn {{
                        background: #9b8bb3;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 5px;
                        cursor: pointer;
                        margin: 0 5px;
                    }}
                    .btn:hover {{
                        background: #8a7ba3;
                    }}
                </style>
            </head>
            <body>
                <div class="preview-container">
                    <div class="music-icon">🎵</div>
                    <div class="music-name">{music.name}</div>
                    <div class="music-description">{music.description or 'No description'}</div>
                    
                    <audio controls>
                        <source src="/voip_webrtc_freepbx/hold_music/file/{music_id}" type="audio/{music.format}">
                        Your browser does not support the audio element.
                    </audio>
                    
                    <div class="controls">
                        <button class="btn" onclick="window.close()">Close</button>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return Response(html, content_type='text/html')
            
        except Exception as e:
            _logger.exception("Error previewing hold music: %s", str(e))
            return Response('Error loading preview', status=500)

    # Removed duplicate /voip/hold_music/list - handled by hold_music_controller.py

    def create_default_hold_music(self):
        """Create default hold music if none exists"""
        try:
            # Check if default music already exists
            existing_music = request.env['voip.hold.music'].search([
                ('name', '=', 'Default Hold Music'),
                ('active', '=', True)
            ])
            
            if existing_music:
                return existing_music.get_music_config()
            
            # Create default music record
            default_server = request.env['voip.server'].search([('active', '=', True)])
            if not default_server:
                return None
            
            # Create a proper WAV file for default music
            import base64
            import io
            import wave
            import math
            
            # Create a pleasant melody
            sample_rate = 44100
            duration = 30  # 30 seconds
            buffer = io.BytesIO()
            
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                
                # Create a pleasant melody
                melody_notes = [
                    (440, 2),    # A4
                    (523.25, 2), # C5
                    (659.25, 2), # E5
                    (783.99, 2), # G5
                    (659.25, 2), # E5
                    (523.25, 2), # C5
                    (440, 2),    # A4
                    (392, 2),    # G4
                ]
                
                total_samples = int(sample_rate * duration)
                samples = []
                sample_index = 0
                
                for note_freq, note_duration in melody_notes:
                    note_samples = int(sample_rate * note_duration)
                    end_index = min(sample_index + note_samples, total_samples)
                    
                    for i in range(sample_index, end_index):
                        time = i / sample_rate
                        # Create a pleasant tone with harmonics
                        sample = (math.sin(2 * math.pi * note_freq * time) * 0.1 +
                                 math.sin(2 * math.pi * note_freq * 2 * time) * 0.05 +
                                 math.sin(2 * math.pi * note_freq * 3 * time) * 0.02)
                        
                        # Add some vibrato
                        vibrato = math.sin(2 * math.pi * 5 * time) * 0.01
                        sample *= (1 + vibrato)
                        
                        # Convert to 16-bit PCM (little-endian)
                        pcm_sample = int(max(-32768, min(32767, sample * 32767)))
                        # Convert to bytes (little-endian)
                        samples.append(pcm_sample & 0xFF)  # Low byte
                        samples.append((pcm_sample >> 8) & 0xFF)  # High byte
                    
                    sample_index = end_index
                    
                    # If we've filled the duration, break
                    if sample_index >= total_samples:
                        break
                
                # Write the samples
                wav_file.writeframes(bytes(samples))
            
            wav_data = buffer.getvalue()
            wav_base64 = base64.b64encode(wav_data).decode('utf-8')
            
            # Create hold music record
            music_record = request.env['voip.hold.music'].create({
                'name': 'Default Hold Music',
                'description': 'Generated default hold music',
                'server_id': default_server.id,
                'music_file': wav_base64,
                'music_filename': 'default_hold_music.wav',
                'format': 'wav',
                'volume': 0.7,
                'loop': True,
                'active': True,
                'is_default': True,
                'sequence': 1
            })
            
            return music_record.get_music_config()
            
        except Exception as e:
            _logger.exception("Error creating default hold music: %s", str(e))
            return None
    
    def fix_corrupted_music_files(self):
        """Fix corrupted music files by regenerating them"""
        try:
            # Find music files with corrupted data
            corrupted_music = request.env['voip.hold.music'].search([
                ('active', '=', True),
                ('music_file', '!=', False)
            ])
            
            for music in corrupted_music:
                try:
                    # Check if record still exists
                    if not music.exists():
                        _logger.warning(f"Music record {music.id} no longer exists, skipping...")
                        continue
                    
                    # Try to decode the base64 data
                    import base64
                    music_data = base64.b64decode(music.music_file)
                    
                    # Check if it's a valid WAV file
                    if not music_data.startswith(b'RIFF') or not b'WAVE' in music_data[:12]:
                        _logger.info(f"Regenerating corrupted music file: {music.name}")
                        self.regenerate_music_file(music)
                        
                except Exception as e:
                    _logger.warning(f"Music file {music.name} is corrupted, regenerating...")
                    try:
                        self.regenerate_music_file(music)
                    except Exception as regen_error:
                        _logger.error(f"Failed to regenerate music file {music.name}: {regen_error}")
                    
        except Exception as e:
            _logger.exception("Error fixing corrupted music files: %s", str(e))
    
    def regenerate_music_file(self, music_record):
        """Regenerate a music file"""
        try:
            import base64
            import io
            import wave
            import math
            
            # Create a pleasant melody
            sample_rate = 44100
            duration = 30  # 30 seconds
            buffer = io.BytesIO()
            
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                
                # Create a pleasant melody
                melody_notes = [
                    (440, 2),    # A4
                    (523.25, 2), # C5
                    (659.25, 2), # E5
                    (783.99, 2), # G5
                    (659.25, 2), # E5
                    (523.25, 2), # C5
                    (440, 2),    # A4
                    (392, 2),    # G4
                ]
                
                total_samples = int(sample_rate * duration)
                samples = []
                sample_index = 0
                
                for note_freq, note_duration in melody_notes:
                    note_samples = int(sample_rate * note_duration)
                    end_index = min(sample_index + note_samples, total_samples)
                    
                    for i in range(sample_index, end_index):
                        time = i / sample_rate
                        # Create a pleasant tone with harmonics
                        sample = (math.sin(2 * math.pi * note_freq * time) * 0.1 +
                                 math.sin(2 * math.pi * note_freq * 2 * time) * 0.05 +
                                 math.sin(2 * math.pi * note_freq * 3 * time) * 0.02)
                        
                        # Add some vibrato
                        vibrato = math.sin(2 * math.pi * 5 * time) * 0.01
                        sample *= (1 + vibrato)
                        
                        # Convert to 16-bit PCM (little-endian)
                        pcm_sample = int(max(-32768, min(32767, sample * 32767)))
                        # Convert to bytes (little-endian)
                        samples.append(pcm_sample & 0xFF)  # Low byte
                        samples.append((pcm_sample >> 8) & 0xFF)  # High byte
                    
                    sample_index = end_index
                    
                    # If we've filled the duration, break
                    if sample_index >= total_samples:
                        break
                
                # Write the samples
                wav_file.writeframes(bytes(samples))
            
            wav_data = buffer.getvalue()
            wav_base64 = base64.b64encode(wav_data).decode('utf-8')
            
            # Update the music record
            music_record.write({
                'music_file': wav_base64,
                'music_filename': f'{music_record.name.lower().replace(" ", "_")}.wav',
                'format': 'wav',
                'file_size': len(wav_data)
            })
            
            _logger.info(f"Regenerated music file: {music_record.name}")
            
        except Exception as e:
            _logger.exception(f"Error regenerating music file {music_record.name}: %s", str(e))
    
    def create_valid_music_file(self, music_record):
        """Create a valid music file for testing"""
        try:
            import base64
            import io
            import wave
            import math
            
            # Create a simple but pleasant melody
            sample_rate = 44100
            duration = 10  # 10 seconds
            buffer = io.BytesIO()
            
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                
                # Create a simple melody
                melody_notes = [
                    (440, 1),    # A4
                    (523.25, 1), # C5
                    (659.25, 1), # E5
                    (783.99, 1), # G5
                    (659.25, 1), # E5
                    (523.25, 1), # C5
                    (440, 1),    # A4
                    (392, 1),    # G4
                ]
                
                total_samples = int(sample_rate * duration)
                samples = []
                sample_index = 0
                
                for note_freq, note_duration in melody_notes:
                    note_samples = int(sample_rate * note_duration)
                    end_index = min(sample_index + note_samples, total_samples)
                    
                    for i in range(sample_index, end_index):
                        time = (i - sample_index) / sample_rate
                        # Create a pleasant tone
                        sample = math.sin(2 * math.pi * note_freq * time) * 0.1
                        
                        # Convert to 16-bit PCM (little-endian)
                        pcm_sample = int(max(-32768, min(32767, sample * 32767)))
                        # Convert to bytes (little-endian)
                        samples.append(pcm_sample & 0xFF)  # Low byte
                        samples.append((pcm_sample >> 8) & 0xFF)  # High byte
                    
                    sample_index = end_index
                    
                    # If we've filled the duration, break
                    if sample_index >= total_samples:
                        break
                
                # Write the samples
                wav_file.writeframes(bytes(samples))
            
            wav_data = buffer.getvalue()
            wav_base64 = base64.b64encode(wav_data).decode('utf-8')
            
            # Update the music record
            music_record.write({
                'music_file': wav_base64,
                'music_filename': f'{music_record.name.lower().replace(" ", "_")}.wav',
                'format': 'wav',
                'file_size': len(wav_data)
            })
            
            _logger.info(f"Created valid music file: {music_record.name}")
            return True
            
        except Exception as e:
            _logger.exception(f"Error creating valid music file {music_record.name}: %s", str(e))
            return False

    # Removed duplicate /voip/hold_music/upload_large - handled by hold_music_controller.py

    # Removed duplicate /voip/users/list - handled by call_controller.py


    def handle_peer_status_event(self, event_data, server_id):
        """Handle PeerStatus events to update user status
        Note: Uses sudo() for webhook access to voip.user records
        """
        try:
            _logger.info("🔔 Processing PeerStatus event...")
            
            # Extract peer information
            peer = event_data.get('Peer', '')
            peer_status = event_data.get('PeerStatus', '')
            channel_type = event_data.get('ChannelType', '')
            
            _logger.info(f"🔔 Peer: {peer}, Status: {peer_status}, Type: {channel_type}")
            
            if not peer or not peer_status:
                _logger.warning("🔔 Missing peer or status information")
                return
            
            # Extract extension from peer (e.g., "PJSIP/200" -> "200")
            extension = peer.replace('PJSIP/', '').replace('SIP/', '').strip()
            
            if not extension:
                _logger.warning(f"🔔 Could not extract extension from peer: {peer}")
                return
            
            _logger.info(f"🔔 Extracted extension: {extension}")
            
            # Find user by extension or SIP username
            voip_user = request.env['voip.user'].sudo().search([
                '|',
                ('extension', '=', extension),
                ('sip_username', '=', extension),
                ('sip_username', 'ilike', f'%{extension}%')
            ])
            
            if not voip_user:
                _logger.warning(f"🔔 User not found for extension: {extension}")
                return
            
            # Map PeerStatus to user status
            old_status = voip_user.status
            new_status = old_status
            
            if peer_status == 'Reachable':
                new_status = 'available'
            elif peer_status == 'Unreachable':
                new_status = 'offline'
            elif peer_status == 'Lagged':
                new_status = 'away'
            elif peer_status == 'Busy':
                new_status = 'busy'
            else:
                _logger.info(f"🔔 Unknown peer status: {peer_status}, keeping current status")
                return
            
            # Update user status if changed
            if new_status != old_status:
                voip_user.write({'status': new_status})
                _logger.info(f"🔔 User {voip_user.name} status updated: {old_status} → {new_status}")
                
                # Log the change
                _logger.info(f"🔔 User status change: {voip_user.name} ({voip_user.sip_username}) - {old_status} → {new_status} (Peer: {peer})")
            else:
                _logger.info(f"🔔 User {voip_user.name} status unchanged: {old_status}")
            
        except Exception as e:
            _logger.exception("Error handling PeerStatus event: %s", str(e))

    def handle_newstate_event(self, event_data, server_id):
        """Handle Newstate events to update user status during calls
        Note: Uses sudo() for webhook access to voip.user records
        """
        try:
            _logger.info("🔔 Processing Newstate event...")
            
            # Extract call information
            channel = event_data.get('Channel', '')
            channel_state = event_data.get('ChannelState', '')
            channel_state_desc = event_data.get('ChannelStateDesc', '')
            caller_id = event_data.get('CallerIDNum', '')
            context = event_data.get('Context', '')
            
            _logger.info(f"🔔 Channel: {channel}, State: {channel_state} ({channel_state_desc})")
            
            if not channel or not channel_state:
                _logger.warning("🔔 Missing channel or state information")
                return
            
            # Extract extension from channel (e.g., "PJSIP/200-00000001" -> "200")
            extension = channel.split('/')[1].split('-')[0] if '/' in channel else channel
            
            if not extension:
                _logger.warning(f"🔔 Could not extract extension from channel: {channel}")
                return
            
            _logger.info(f"🔔 Extracted extension: {extension}")
            
            # Find user by extension or SIP username
            voip_user = request.env['voip.user'].sudo().search([
                '|',
                ('extension', '=', extension),
                ('sip_username', '=', extension),
                ('sip_username', 'ilike', f'%{extension}%')
            ])
            
            if not voip_user:
                _logger.warning(f"🔔 User not found for extension: {extension}")
                return
            
            # Map ChannelState to user status
            old_status = voip_user.status
            new_status = old_status
            
            if channel_state == '4':  # Ring
                new_status = 'busy'
            elif channel_state == '6':  # Up (Connected)
                new_status = 'busy'
            elif channel_state == '0':  # Down (Hangup)
                new_status = 'available'
            elif channel_state == '1':  # Reserved
                new_status = 'busy'
            elif channel_state == '2':  # OffHook
                new_status = 'busy'
            elif channel_state == '3':  # Dialing
                new_status = 'busy'
            elif channel_state == '5':  # Busy
                new_status = 'busy'
            else:
                _logger.info(f"🔔 Unknown channel state: {channel_state}, keeping current status")
                return
            
            # Update user status if changed
            if new_status != old_status:
                voip_user.write({'status': new_status})
                _logger.info(f"🔔 User {voip_user.name} status updated: {old_status} → {new_status}")
                
                # Log the change
                _logger.info(f"🔔 User status change: {voip_user.name} ({voip_user.sip_username}) - {old_status} → {new_status} (Channel: {channel}, State: {channel_state})")
            else:
                _logger.info(f"🔔 User {voip_user.name} status unchanged: {old_status}")
            
        except Exception as e:
            _logger.exception("Error handling Newstate event: %s", str(e))

    def handle_newchannel_event(self, event_data, server_id):
        """Handle Newchannel events to update user status when calls start
        Note: Uses sudo() for webhook access to voip.user records
        """
        try:
            _logger.info("🔔 Processing Newchannel event...")
            
            # Extract channel information
            channel = event_data.get('Channel', '')
            channel_state = event_data.get('ChannelState', '')
            caller_id = event_data.get('CallerIDNum', '')
            context = event_data.get('Context', '')
            unique_id = event_data.get('Uniqueid', '')
            
            _logger.info(f"🔔 Channel: {channel}, State: {channel_state}, Caller: {caller_id}")
            
            if not channel:
                _logger.warning("🔔 Missing channel information")
                return
            
            # Extract extension from channel (e.g., "PJSIP/200-00000001" -> "200")
            extension = channel.split('/')[1].split('-')[0] if '/' in channel else channel
            
            if not extension:
                _logger.warning(f"🔔 Could not extract extension from channel: {channel}")
                return
            
            _logger.info(f"🔔 Extracted extension: {extension}")
            
            # Find user by extension or SIP username
            voip_user = request.env['voip.user'].sudo().search([
                '|',
                ('extension', '=', extension),
                ('sip_username', '=', extension),
                ('sip_username', 'ilike', f'%{extension}%')
            ])
            
            if not voip_user:
                _logger.warning(f"🔔 User not found for extension: {extension}")
                return
            
            # Update user status to busy when new channel is created
            old_status = voip_user.status
            new_status = 'busy'  # New channel means user is busy
            
            if new_status != old_status:
                voip_user.write({'status': new_status})
                _logger.info(f"🔔 User {voip_user.name} status updated: {old_status} → {new_status}")
                
                # Log the change
                _logger.info(f"🔔 User status change: {voip_user.name} ({voip_user.sip_username}) - {old_status} → {new_status} (Channel: {channel})")
            else:
                _logger.info(f"🔔 User {voip_user.name} status unchanged: {old_status}")
            
        except Exception as e:
            _logger.exception("Error handling Newchannel event: %s", str(e))

    # Removed duplicate /voip/webhook/notification - handled by webhook_controller.py

    # Removed duplicate /voip/hold_music/cleanup - handled by hold_music_controller.py

    # Removed duplicate /voip/hold_music/default - handled by hold_music_controller.py