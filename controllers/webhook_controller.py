# -*- coding: utf-8 -*-
#################################################################################
#
# Module Name: Voip Webrtc Freepbx - Webhook Controller
# Description: Controller for managing webhook events and notifications
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
from odoo import http
from odoo.http import request, Response
import json
import logging
from .base_controller import VoipBaseController

_logger = logging.getLogger(__name__)


class VoipWebhookController(VoipBaseController):
    """Controller for managing webhook events and notifications"""

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
            ], limit=1)

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
                ], limit=1)

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
            ], limit=1)
            
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
            ], limit=1)
            
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
            ], limit=1)
            
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

    @http.route('/voip/webhook/notification', type='json', auth='none', methods=['POST'], csrf=False)
    def handle_webhook_notification(self, **kwargs):
        """Handle webhook notifications to update user status"""
        try:
            _logger.info("🔔 Webhook notification received")
            
            # Get notification data
            notification_data = request.jsonrequest or {}
            _logger.info(f"🔔 Notification data: {notification_data}")
            
            # Extract user information
            user_extension = notification_data.get('extension') or notification_data.get('user')
            user_status = notification_data.get('status') or notification_data.get('state')
            event_type = notification_data.get('event') or notification_data.get('type')
            
            _logger.info(f"🔔 User: {user_extension}, Status: {user_status}, Event: {event_type}")
            
            if not user_extension:
                _logger.warning("🔔 No user extension found in notification")
                return {'success': False, 'error': 'No user extension provided'}
            
            # Find user by SIP username or extension
            voip_user = request.env['voip.user'].sudo().search([
                '|',
                ('sip_username', '=', user_extension),
                ('extension', '=', user_extension)
            ], limit=1)
            
            if not voip_user:
                _logger.warning(f"🔔 User not found for extension: {user_extension}")
                return {'success': False, 'error': f'User not found for extension: {user_extension}'}
            
            # Update user status based on event type
            old_status = voip_user.status
            new_status = old_status
            
            if event_type in ['call_start', 'call_ringing', 'call_connected']:
                new_status = 'busy'
            elif event_type in ['call_end', 'call_hangup', 'call_completed']:
                new_status = 'available'
            elif user_status:
                # Use status from notification if provided
                new_status = user_status
            elif event_type == 'user_online':
                new_status = 'available'
            elif event_type == 'user_offline':
                new_status = 'offline'
            
            # Update user status if changed
            if new_status != old_status:
                voip_user.write({'status': new_status})
                _logger.info(f"🔔 User {voip_user.name} status updated: {old_status} → {new_status}")
                
                # Log the change
                _logger.info(f"🔔 User status change: {voip_user.name} ({voip_user.sip_username}) - {old_status} → {new_status}")
            else:
                _logger.info(f"🔔 User {voip_user.name} status unchanged: {old_status}")
            
            return {
                'success': True,
                'user_id': voip_user.id,
                'user_name': voip_user.name,
                'old_status': old_status,
                'new_status': new_status,
                'event_type': event_type
            }
            
        except Exception as e:
            _logger.exception("Error handling webhook notification: %s", str(e))
            return {
                'success': False,
                'error': str(e)
            }




