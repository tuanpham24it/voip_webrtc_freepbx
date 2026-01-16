# -*- coding: utf-8 -*-
#################################################################################
#
# Module Name: Voip Webrtc Freepbx - Call Controller
# Description: Controller for managing VoIP calls
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
from .base_controller import VoipBaseController
from ..utils.logging_utils import VoipLoggingUtils

_logger = logging.getLogger(__name__)


class VoipCallController(VoipBaseController):
    """Controller for managing VoIP calls"""

    # Removed duplicate /voip/config route - handled by main controller

    @http.route('/voip/call/create', type='json', auth='user', csrf=False)
    def create_call(self, **kwargs):
        """Create a new call record or find existing by SIP Call ID"""
        try:
            user = request.env.user
            voip_user = request.env['voip.user'].sudo().search([
                ('user_id', '=', user.id),
                ('active', '=', True)
            ], limit=1)
            
            if not voip_user:
                return {'success': False, 'error': 'No VoIP user found'}
            
            sip_call_id = kwargs.get('call_id')  # SIP Call ID
            
            # Check if call already exists with this SIP Call ID
            if sip_call_id:
                existing_call = request.env['voip.call'].search([
                    ('call_id', '=', sip_call_id)
                ], limit=1, order='create_date desc')
                
                if existing_call:
                    # Update existing call if needed
                    update_vals = {}
                    if kwargs.get('from_number') and not existing_call.from_number:
                        update_vals['from_number'] = kwargs.get('from_number')
                    if kwargs.get('to_number') and not existing_call.to_number:
                        update_vals['to_number'] = kwargs.get('to_number')
                    if kwargs.get('direction') and not existing_call.direction:
                        update_vals['direction'] = kwargs.get('direction', 'outbound')
                    
                    if update_vals:
                        # Re-browse the record to avoid concurrent update errors
                        existing_call = request.env['voip.call'].browse(existing_call.id)
                        existing_call._invalidate_cache()
                        existing_call.write(update_vals)
                    
                    return {
                        'success': True,
                        'call_id': existing_call.id,
                        'call_name': existing_call.name,
                        'existing': True
                    }
            
            # Create new call record
            call_data = {
                'user_id': voip_user.id,
                'direction': kwargs.get('direction', 'outbound'),
                'from_number': kwargs.get('from_number'),
                'to_number': kwargs.get('to_number'),
                'call_id': sip_call_id,  # SIP Call ID (will be displayed as SIP Call ID)
                'state': kwargs.get('state', 'ringing'),
                'start_time': fields.Datetime.now(),
            }
            
            call = request.env['voip.call'].create(call_data)
            
            return {
                'success': True,
                'call_id': call.id,
                'call_name': call.name,
                'existing': False
            }
        except Exception as e:
            VoipLoggingUtils.log_if_enabled(
                request.env, _logger, 'error', 
                "Error creating call: %s", str(e)
            )
            return {'success': False, 'error': str(e)}

    @http.route('/voip/call/update', type='json', auth='user', csrf=False)
    def update_call(self, call_id=None, sip_call_id=None, state=None, **kwargs):
        """Update call state - can find by call_id or sip_call_id"""
        try:
            call = None
            
            # Handle call_id parameter - check if it's integer (Odoo ID) or string (SIP Call ID)
            if call_id:
                # Check if call_id is integer (Odoo ID) or string (SIP Call ID)
                try:
                    # Try to convert to integer
                    call_id_int = int(call_id)
                    call = request.env['voip.call'].browse(call_id_int)
                    if not call.exists():
                        call = None
                except (ValueError, TypeError):
                    # call_id is not an integer, treat it as SIP Call ID
                    sip_call_id = call_id if not sip_call_id else sip_call_id
                    call_id = None
            
            # If no call found by call_id, try sip_call_id
            if not call and sip_call_id:
                call = request.env['voip.call'].search([
                    ('call_id', '=', sip_call_id)
                ], limit=1, order='create_date desc')
                if not call:
                    return {'success': False, 'error': 'Call not found by SIP Call ID'}
            
            if not call:
                return {'success': False, 'error': 'call_id or sip_call_id required'}
            
            if not call.exists():
                return {'success': False, 'error': 'Call not found'}
            
            update_vals = {}
            
            if state:
                update_vals['state'] = state
            
            # Update answer_time when call is answered
            if state == 'in_progress':
                # Always update answer_time when state changes to 'in_progress'
                if not call.answer_time or kwargs.get('answer_time'):
                    answer_time = kwargs.get('answer_time')
                    if answer_time:
                        try:
                            from datetime import datetime
                            import pytz
                            from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
                            
                            if isinstance(answer_time, str):
                                # Parse ISO string with timezone
                                dt = datetime.fromisoformat(answer_time.replace('Z', '+00:00'))
                                # Convert to naive datetime (remove timezone info)
                                if dt.tzinfo:
                                    # Convert to UTC first, then remove timezone
                                    dt = dt.astimezone(pytz.UTC).replace(tzinfo=None)
                                update_vals['answer_time'] = dt
                            else:
                                update_vals['answer_time'] = fields.Datetime.now()
                        except Exception as e:
                            _logger.warning("Error parsing answer_time: %s, using current time", str(e))
                            update_vals['answer_time'] = fields.Datetime.now()
                    else:
                        update_vals['answer_time'] = fields.Datetime.now()
                    
                    # Note: start_time should remain as sourcing time when call was received (created)
                    # Only answer_time is updated to track when employee actually answered
                    # start_time stays as original call creation time
            
            # Update end_time and hangup_reason when call ends
            if state in ['completed', 'missed', 'failed', 'rejected', 'busy']:
                end_time = kwargs.get('end_time')
                if end_time:
                    try:
                        from datetime import datetime
                        import pytz
                        
                        if isinstance(end_time, str):
                            # Parse ISO string with timezone
                            dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                            # Convert to naive datetime (remove timezone info)
                            if dt.tzinfo:
                                # Convert to UTC first, then remove timezone
                                dt = dt.astimezone(pytz.UTC).replace(tzinfo=None)
                            update_vals['end_time'] = dt
                        else:
                            update_vals['end_time'] = fields.Datetime.now()
                    except Exception as e:
                        _logger.warning("Error parsing end_time: %s, using current time", str(e))
                        update_vals['end_time'] = fields.Datetime.now()
                else:
                    update_vals['end_time'] = fields.Datetime.now()
                
                update_vals['hangup_reason'] = kwargs.get('hangup_reason', 'normal')
            
            # Update SIP Call ID field if provided in kwargs
            # Priority: sip_call_id parameter > call_id in kwargs (if string)
            sip_call_id_to_update = None
            if sip_call_id:
                # sip_call_id parameter takes priority
                sip_call_id_to_update = sip_call_id
            elif 'call_id' in kwargs:
                call_id_value = kwargs.get('call_id')
                # Check if it's a string (SIP Call ID) or integer (shouldn't happen here)
                if isinstance(call_id_value, str) and not call_id_value.isdigit():
                    sip_call_id_to_update = call_id_value
            
            if sip_call_id_to_update:
                if not call.call_id:
                    # Only update if not already set
                    update_vals['call_id'] = sip_call_id_to_update
                elif call.call_id != sip_call_id_to_update:
                    # Always update if different (important for outbound calls where SIP Call ID might change)
                    update_vals['call_id'] = sip_call_id_to_update
            
            # Auto-update state if end_time is set but state is still 'ringing'
            if not state and call.end_time and call.state == 'ringing':
                if call.answer_time:
                    update_vals['state'] = 'completed'
                else:
                    update_vals['state'] = 'missed'
            
            if update_vals:
                # Re-browse the record to avoid concurrent update errors
                call = request.env['voip.call'].browse(call.id)
                call._invalidate_cache()
                call.write(update_vals)
            
            return {
                'success': True,
                'call_id': call.id,
                'duration': call.duration,
                'duration_display': call.duration_display
            }
        except Exception as e:
            _logger.exception("Error updating call: %s", str(e))
            return {'success': False, 'error': str(e)}

    @http.route('/voip/call/update_duration', type='json', auth='user', csrf=False)
    def update_call_duration(self, call_id, duration, **kwargs):
        """Update call duration"""
        try:
            # Handle call_id parameter - check if it's integer (Odoo ID) or string (SIP Call ID)
            call_id_int = None
            if call_id:
                try:
                    call_id_int = int(call_id)
                except (ValueError, TypeError):
                    # call_id is not an integer, treat it as SIP Call ID
                    return {'success': False, 'error': 'call_id must be an integer (Odoo Call ID)'}
            
            if not call_id_int:
                return {'success': False, 'error': 'call_id required and must be integer'}
            
            call = request.env['voip.call'].browse(call_id_int)
            
            if not call.exists():
                return {'success': False, 'error': 'Call not found'}
            
            # Update the call with the provided duration
            # The duration field is computed, so we need to set end_time if not already set
            update_vals = {}
            
            # If end_time is not set, set it to now
            if not call.end_time:
                update_vals['end_time'] = fields.Datetime.now()
            
            # Don't set answer_time here - it should only be set when call is actually answered
            # Answer time will be set via update_call when state changes to 'in_progress'
            
            # Update the call record
            if update_vals:
                # Re-browse the record to avoid concurrent update errors
                call = request.env['voip.call'].browse(call.id)
                call._invalidate_cache()
                call.write(update_vals)
            
            # Force recompute of duration field
            call._compute_duration()
            call._compute_duration_display()
            
            # Log the duration update
            VoipLoggingUtils.log_if_enabled(
                request.env, _logger, 'info', 
                'Updated call duration: %s seconds for call %s (computed: %s)', 
                duration, call.name, call.duration
            )
            
            return {
                'call_id': call.id,
                'duration': call.duration,
                'duration_display': call.duration_display
            }
        except Exception as e:
            VoipLoggingUtils.log_if_enabled(
                request.env, _logger, 'error', 
                "Error updating call duration: %s", str(e)
            )
            return {'error': str(e)}

    @http.route('/voip/call/list', type='json', auth='user', csrf=False)
    def list_calls(self, limit=50, offset=0, **kwargs):
        """Get list of calls for current user"""
        try:
            user = request.env.user

            voip_user = request.env['voip.user'].sudo().search([
                ('user_id', '=', user.id),
                ('active', '=', True)
            ], limit=1)

            if not voip_user:
                VoipLoggingUtils.log_if_enabled(
                    request.env, _logger, 'warning', 
                    "No VoIP user found for user %s", user.name
                )
                return {
                    'success': False,
                    'error': 'No VoIP user found',
                    'calls': [],
                    'total': 0,
                    'count': 0,
                    'offset': offset,
                    'limit': limit
                }

            sip_username = voip_user.sip_username
            VoipLoggingUtils.log_if_enabled(
                request.env, _logger, 'info', 
                "Listing calls for user: %s (SIP: %s, Odoo User ID: %s)", 
                user.name, sip_username, user.id
            )

            # Build domain: Search by odoo_user_id OR by from_number/to_number
            # This ensures we get all calls related to the user
            # Note: Using sudo() to bypass record rules and get all matching calls,
            # then we filter manually to ensure security
            domain = [
                '|',
                ('odoo_user_id', '=', user.id),
                '|',
                ('from_number', '=', sip_username),
                ('to_number', '=', sip_username)
            ]
            
            if kwargs.get('state'):
                domain.append(('state', '=', kwargs.get('state')))
            
            VoipLoggingUtils.log_if_enabled(
                request.env, _logger, 'info', 
                "Search domain: %s", domain
            )
            
            # DEBUG: Get ALL calls without limit to see how numbers are stored
            _logger.info("=" * 100)
            _logger.info("DEBUG: Getting ALL calls for analysis (no limit)")
            _logger.info("=" * 100)
            
            # Get ALL calls for the user (without limit) to analyze number storage format
            all_user_calls_by_odoo = request.env['voip.call'].sudo().search([
                ('odoo_user_id', '=', user.id)
            ], order='start_time desc')
            
            _logger.info("📊 Total calls found by odoo_user_id=%s: %s", user.id, len(all_user_calls_by_odoo))
            
            # Get ALL calls matching SIP username in from_number or to_number (without limit)
            all_user_calls_by_sip = request.env['voip.call'].sudo().search([
                '|',
                ('from_number', '=', sip_username),
                ('to_number', '=', sip_username)
            ], order='start_time desc')
            
            _logger.info("📊 Total calls found by SIP username='%s' (exact match): %s", sip_username, len(all_user_calls_by_sip))
            
            # Get ALL calls with flexible search (ilike)
            all_user_calls_by_sip_flexible = request.env['voip.call'].sudo().search([
                '|',
                ('from_number', 'ilike', sip_username),
                ('to_number', 'ilike', sip_username)
            ], order='start_time desc')
            
            _logger.info("📊 Total calls found by SIP username='%s' (flexible/ilike): %s", sip_username, len(all_user_calls_by_sip_flexible))
            
            # Get ALL calls containing the number anywhere
            all_user_calls_containing = request.env['voip.call'].sudo().search([
                '|',
                ('from_number', 'ilike', '%' + sip_username + '%'),
                ('to_number', 'ilike', '%' + sip_username + '%')
            ], order='start_time desc')
            
            _logger.info("📊 Total calls containing SIP username='%s' anywhere: %s", sip_username, len(all_user_calls_containing))
            
            # Combine all calls for detailed logging
            all_unique_calls = (all_user_calls_by_odoo | all_user_calls_by_sip | all_user_calls_by_sip_flexible | all_user_calls_containing)
            all_unique_calls = all_unique_calls.sorted('start_time', reverse=True)
            
            _logger.info("📊 Total unique calls (combined): %s", len(all_unique_calls))
            _logger.info("=" * 100)
            
            # Log detailed information about ALL calls found
            _logger.info("🔍 DETAILED CALL ANALYSIS - All Calls Found:")
            _logger.info("-" * 100)
            for idx, call in enumerate(all_unique_calls, 1):
                _logger.info(
                    "[%s/%s] Call ID=%s | Name=%s | Direction=%s | State=%s",
                    idx, len(all_unique_calls), call.id, call.name, call.direction, call.state
                )
                _logger.info(
                    "        FROM: '%s' (type: %s, len: %s) | TO: '%s' (type: %s, len: %s)",
                    call.from_number, type(call.from_number).__name__, len(call.from_number) if call.from_number else 0,
                    call.to_number, type(call.to_number).__name__, len(call.to_number) if call.to_number else 0
                )
                _logger.info(
                    "        odoo_user_id=%s | user_id (voip.user)=%s | SIP username match FROM: %s | TO: %s",
                    call.odoo_user_id.id if call.odoo_user_id else None,
                    call.user_id.id if call.user_id else None,
                    'YES' if (call.from_number and sip_username in str(call.from_number)) else 'NO',
                    'YES' if (call.to_number and sip_username in str(call.to_number)) else 'NO'
                )
                _logger.info(
                    "        start_time=%s | duration=%s",
                    call.start_time, call.duration
                )
                _logger.info("-" * 100)
            
            # Use sudo() to bypass record rules and find ALL matching calls (without limit first)
            # This is safe because we filter manually by odoo_user_id or SIP username
            # IMPORTANT: Search without limit first, then filter, then apply limit/offset
            all_calls = request.env['voip.call'].sudo().search(
                domain,
                order='start_time desc'
            )
            
            _logger.info("🔍 After initial domain search (without limit): found %s calls", len(all_calls))
            
            # If no calls found with exact match, try flexible search (for cases like '300@domain.com')
            if not all_calls:
                flexible_domain = [
                    '|',
                    ('odoo_user_id', '=', user.id),
                    '|',
                    ('from_number', 'ilike', sip_username),
                    ('to_number', 'ilike', sip_username)
                ]
                if kwargs.get('state'):
                    flexible_domain.append(('state', '=', kwargs.get('state')))
                
                VoipLoggingUtils.log_if_enabled(
                    request.env, _logger, 'info', 
                    "No exact matches found, trying flexible search with domain: %s", flexible_domain
                )
                
                all_calls = request.env['voip.call'].sudo().search(
                    flexible_domain,
                    order='start_time desc'
                )
                _logger.info("🔍 After flexible search (without limit): found %s calls", len(all_calls))
            
            # Filter calls to ensure security: only show calls where odoo_user_id matches
            # OR where from_number/to_number matches SIP username (for legacy calls)
            # Also check if SIP username is contained in from_number/to_number (for flexible matching)
            filtered_calls = all_calls.filtered(
                lambda c: (c.odoo_user_id and c.odoo_user_id.id == user.id) or
                         (sip_username and (
                             c.from_number == sip_username or 
                             c.to_number == sip_username or
                             (c.from_number and sip_username in str(c.from_number)) or
                             (c.to_number and sip_username in str(c.to_number))
                         ))
            )
            
            _logger.info("🔍 After filtering: found %s calls (from %s total)", len(filtered_calls), len(all_calls))
            
            # Apply offset and limit AFTER filtering
            # This ensures we get the correct pagination results
            calls = filtered_calls[offset:offset + limit]
            
            _logger.info("🔍 After applying offset=%s, limit=%s: returning %s calls", offset, limit, len(calls))
            
            VoipLoggingUtils.log_if_enabled(
                request.env, _logger, 'info', 
                "Summary: Total=%s | After filter=%s | After offset/limit=%s (offset=%s, limit=%s)", 
                len(all_calls), len(filtered_calls), len(calls), offset, limit
            )
            
            # Log final calls being returned
            if calls:
                _logger.info("✅ FINAL CALLS (returning to frontend): %s out of %s total", len(calls), len(filtered_calls))
                for idx, call in enumerate(calls, 1):
                    _logger.info(
                        "[%s/%s] ID=%s | FROM='%s' | TO='%s' | Direction=%s | odoo_user_id=%s | State=%s",
                        idx, len(calls), call.id, call.from_number, call.to_number,
                        call.direction, call.odoo_user_id.id if call.odoo_user_id else None, call.state
                    )
            else:
                _logger.warning("❌ NO CALLS FOUND after filtering and pagination!")
                if filtered_calls:
                    _logger.warning("   But %s calls exist after filtering - check offset/limit values", len(filtered_calls))
            
            _logger.info("=" * 100)
            
            call_list = []
            for call in calls:
                call_list.append({
                    'id': call.id,
                    'name': f"{call.user_id.name} ({call.name})",
                    'direction': call.direction,
                    'state': call.state,
                    'from_number': call.from_number,
                    'to_number': call.to_number,
                    'partner_name': call.partner_id.name if call.partner_id else False,
                    'start_time': call.start_time.isoformat() if call.start_time else False,
                    'duration': call.duration,
                    'duration_display': call.duration_display,
                    'has_recording': call.has_recording,
                })
            
            # Return response in expected format: {success: true, calls: [...]}
            # This matches the frontend expectation in voip_service.js
            return {
                'success': True,
                'calls': call_list,
                'total': len(filtered_calls),  # Total count after filtering (before pagination)
                'count': len(call_list),  # Current page count
                'offset': offset,
                'limit': limit
            }
        except Exception as e:
            _logger.exception("Error listing calls: %s", str(e))
            return {
                'success': False,
                'error': str(e),
                'calls': [],
                'total': 0,
                'count': 0,
                'offset': offset,
                'limit': limit
            }

    @http.route('/voip/search/partner', type='json', auth='user', csrf=False)
    def search_partner(self, phone, **kwargs):
        """Search for partner by phone number"""
        try:
            if not phone:
                return {'success': False, 'error': 'Phone number required'}
            
            # Clean phone number
            clean_phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            
            # Search for partner
            partner = request.env['res.partner'].search([
                '|', '|',
                ('phone', 'ilike', clean_phone),
                ('mobile', 'ilike', clean_phone),
                ('phone', 'ilike', phone)
            ], limit=1)
            
            if partner:
                return {
                    'id': partner.id,
                    'name': partner.name,
                    'phone': partner.phone,
                    'mobile': partner.mobile,
                    'email': partner.email,
                }
            else:
                return None
        except Exception as e:
            _logger.exception("Error searching partner: %s", str(e))
            return None

    @http.route('/voip/contacts/list', type='http', auth='user', methods=['POST', 'GET'], csrf=False)
    def get_contacts_list(self, **kwargs):
        """
        Get contacts list with phone numbers
        
        This endpoint uses type='http' to support standard POST/GET requests
        (not JSON-RPC) for VOIP/FreePBX integration and CURL usage.
        
        Request Body (optional JSON):
        {
            "limit": 100
        }
        
        Query Parameters (alternative):
        ?limit=100
        
        Returns:
            Response: JSON HTTP response with 'success', 'contacts', and optional 'error' keys
            
        Example CURL:
            curl -X POST http://your-odoo/voip/contacts/list \
                 -H "Content-Type: application/json" \
                 -H "Cookie: session_id=xxx" \
                 -d '{"limit": 50}'
        """
        _logger.info("=" * 80)
        _logger.info("🔍 START: Get Contacts List Request (HTTP)")
        _logger.info("=" * 80)
        _logger.info(f"📥 User: {request.env.user.name} (ID: {request.env.user.id})")
        _logger.info(f"📥 HTTP Method: {request.httprequest.method}")
        _logger.info(f"📥 Request URL: {request.httprequest.url}")
        _logger.info(f"📥 Query Params: {kwargs}")
        
        try:
            # Extract limit from JSON body (POST with JSON) or query params (GET/POST)
            limit = 100  # Default value
            request_data = {}
            
            # Try to parse JSON body if present
            if request.httprequest.data:
                try:
                    request_data = json.loads(request.httprequest.data.decode('utf-8'))
                    _logger.info(f"📦 JSON Body: {request_data}")
                    limit = request_data.get('limit', kwargs.get('limit', 100))
                except (json.JSONDecodeError, AttributeError, UnicodeDecodeError) as e:
                    _logger.warning(f"⚠️ Could not parse JSON body: {e}, trying query params")
                    # If JSON parsing fails, try query params
                    limit = kwargs.get('limit', 100)
            else:
                # No JSON body, use query params or kwargs
                limit = kwargs.get('limit', 100)
            
            # Validate limit parameter
            _logger.info(f"🔍 Validating limit parameter: {limit} (type: {type(limit).__name__})")
            try:
                original_limit = limit
                limit = int(limit)
                if limit <= 0 or limit > 1000:
                    _logger.warning(f"⚠️ Limit {limit} out of bounds (0-1000), resetting to 100")
                    limit = 100
                elif limit != original_limit:
                    _logger.info(f"✅ Converted limit from {original_limit} to {limit}")
                else:
                    _logger.info(f"✅ Limit validated: {limit}")
            except (ValueError, TypeError) as e:
                _logger.warning(f"⚠️ Invalid limit value '{limit}' (type: {type(limit).__name__}): {e}, using default 100")
                limit = 100
            
            # Search for partners with phone or mobile numbers
            _logger.info(f"🔍 Searching for partners with phone or mobile numbers (limit: {limit})")
            search_domain = ['|', ('phone', '!=', False), ('mobile', '!=', False)]
            _logger.info(f"📋 Search domain: {search_domain}")
            
            partners = request.env['res.partner'].search(search_domain, limit=limit, order='name')
            _logger.info(f"✅ Found {len(partners)} partners matching criteria")
            
            contacts = []
            for idx, partner in enumerate(partners, 1):
                phone = partner.phone or partner.mobile
                if phone:
                    contact_data = {
                        'id': partner.id,
                        'name': partner.name,
                        'phone': phone,
                        'mobile': partner.mobile or False,
                        'email': partner.email or False,
                        'company': partner.parent_id.name if partner.parent_id else False,
                    }
                    contacts.append(contact_data)
                    if idx <= 3:  # Log first 3 contacts for debugging
                        _logger.info(f"   [{idx}] {contact_data['name']} - {contact_data['phone']}")
            
            _logger.info(f"✅ Processed {len(contacts)} contacts with phone numbers")
            
            # Prepare response data - ensure all values are JSON-serializable
            response_data = {
                'success': True,
                'contacts': contacts,
                'count': len(contacts)
            }
            
            # Log response structure
            _logger.info(f"📤 Response Structure:")
            _logger.info(f"   - success: {response_data['success']} (type: {type(response_data['success']).__name__})")
            _logger.info(f"   - count: {response_data['count']} (type: {type(response_data['count']).__name__})")
            _logger.info(f"   - contacts: list with {len(response_data['contacts'])} items")
            
            # Serialize to JSON
            try:
                json_str = json.dumps(response_data, ensure_ascii=False, default=str)
                _logger.info(f"✅ Response serialized to JSON (size: {len(json_str)} bytes)")
            except (TypeError, ValueError) as e:
                _logger.error(f"❌ Response is NOT JSON-serializable: {e}")
                raise ValueError(f"Response data contains non-JSON-serializable values: {e}")
            
            _logger.info("=" * 80)
            _logger.info("✅ END: Get Contacts List Request - SUCCESS")
            _logger.info("=" * 80)
            
            # Return HTTP Response with JSON content
            return Response(
                json_str,
                content_type='application/json;charset=utf-8',
                status=200
            )
            
        except Exception as e:
            _logger.exception("=" * 80)
            _logger.exception("❌ ERROR: Get Contacts List Request - FAILED")
            _logger.exception("=" * 80)
            _logger.exception(f"❌ Exception Type: {type(e).__name__}")
            _logger.exception(f"❌ Exception Message: {str(e)}")
            _logger.exception(f"❌ Exception Args: {e.args if hasattr(e, 'args') else 'N/A'}")
            import traceback
            _logger.exception(f"❌ Full Traceback:\n{traceback.format_exc()}")
            _logger.exception("=" * 80)
            
            # Prepare error response - ensure it's JSON-serializable
            error_response = {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'contacts': [],
                'count': 0
            }
            
            # Serialize error response to JSON
            try:
                error_json = json.dumps(error_response, ensure_ascii=False, default=str)
                _logger.info("✅ Error response serialized to JSON")
            except Exception as json_err:
                _logger.error(f"❌ Error response is NOT JSON-serializable: {json_err}")
                # Fallback to minimal error response
                error_response = {
                    'success': False,
                    'error': 'Internal server error',
                    'contacts': [],
                    'count': 0
                }
                error_json = json.dumps(error_response, ensure_ascii=False)
            
            # Return HTTP Error Response
            return Response(
                error_json,
                content_type='application/json;charset=utf-8',
                status=500
            )

    @http.route('/voip/users/list', type='json', auth='user', csrf=False)
    def get_voip_users_list(self, **kwargs):
        """Get list of VoIP users for transfer"""
        _logger.info("=" * 80)
        _logger.info("🚀 START: VoIP Users List Request")
        _logger.info("=" * 80)

        try:
            # Get current user
            _logger.info("📌 STEP 1: Getting current user...")
            current_user = request.env.user
            _logger.info(f"✅ Current User ID: {current_user.id}")
            _logger.info(f"✅ Current User Name: {current_user.name}")

            # Get current user's VoIP config
            _logger.info("\n📌 STEP 2: Searching for current user's VoIP configuration...")
            current_voip_user = request.env['voip.user'].sudo().search([
                ('user_id', '=', current_user.id),
                ('active', '=', True)
            ], limit=1)

            if not current_voip_user:
                _logger.error("❌ CRITICAL: No VoIP user found for current user!")
                return {
                    'success': False,
                    'error': 'No VoIP user found for current user',
                    'users': [],
                    'total': 0
                }

            _logger.info(f"✅ Current VoIP User Found: {current_voip_user.name}")

            # Get all active VoIP users (excluding current user) - USE SUDO!
            _logger.info("\n📌 STEP 3: Getting all VoIP users (excluding current)...")

            # ⭐ الحل: استخدم sudo() عشان تتخطى الـ access rights
            all_voip_users = request.env['voip.user'].sudo().search([
                ('active', '=', True),
                ('user_id', '!=', current_user.id),
                ('user_id', '!=', False)  # تأكد إن في Odoo user مربوط
            ])

            _logger.info(f"✅ Found {len(all_voip_users)} VoIP users (excluding current)")

            users_list = []
            for voip_user in all_voip_users:
                _logger.info(f"\n🔍 Processing VoIP User: {voip_user.name}")
                _logger.info(f"   - VoIP ID: {voip_user.id}")
                _logger.info(f"   - SIP Username: {voip_user.sip_username}")
                _logger.info(f"   - Linked Odoo User: {voip_user.user_id.name} (ID: {voip_user.user_id.id})")

                user_data = {
                    'id': voip_user.id,
                    'odoo_user_id': voip_user.user_id.id,
                    'name': voip_user.name,
                    'sip_username': voip_user.sip_username,
                    'extension': voip_user.extension or voip_user.sip_username,
                    'display_name': f"{voip_user.name} ({voip_user.sip_username})",
                    'status': voip_user.status or 'available',
                    'server_id': voip_user.server_id.id if voip_user.server_id else None,
                    'server_name': voip_user.server_id.name if voip_user.server_id else 'Unknown',
                    'has_voip': True
                }
                users_list.append(user_data)
                _logger.info(f"   ✅ Added to list")

            # Summary
            _logger.info("\n" + "=" * 80)
            _logger.info("📊 SUMMARY:")
            _logger.info("=" * 80)
            _logger.info(f"✅ VoIP Users found (excluding current): {len(users_list)}")
            _logger.info(f"✅ Current User (excluded): {current_voip_user.name}")

            if users_list:
                _logger.info(f"\n📋 Users returning to frontend:")
                for i, user in enumerate(users_list, 1):
                    _logger.info(f"   {i}. {user['display_name']}")

            response = {
                'success': True,
                'users': users_list,
                'total': len(users_list)
            }

            _logger.info("\n📤 RESPONSE:")
            _logger.info(f"Response: {response}")
            _logger.info("=" * 80)
            _logger.info("🏁 END: VoIP Users List Request")
            _logger.info("=" * 80)

            return response

        except Exception as e:
            _logger.error("\n" + "=" * 80)
            _logger.error("💥 EXCEPTION OCCURRED!")
            _logger.error("=" * 80)
            _logger.exception(f"❌ Error: {str(e)}")
            _logger.error("=" * 80)

            return {
                'success': False,
                'error': str(e),
                'users': [],
                'total': 0
            }


