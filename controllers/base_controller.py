# -*- coding: utf-8 -*-
#################################################################################
#
# Module Name: Voip Webrtc Freepbx - Base Controller
# Description: Base controller with common functionality for VoIP operations
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
from ..utils.logging_utils import VoipLoggingUtils

_logger = logging.getLogger(__name__)


class VoipBaseController(http.Controller):
    """Base controller with common VoIP functionality"""

    def get_current_voip_user(self):
        """Get current user's VoIP configuration"""
        try:
            user = request.env.user
            voip_user = request.env['voip.user'].sudo().search([
                ('user_id', '=', user.id),
                ('active', '=', True)
            ])
            
            if not voip_user:
                return None
                
            # Update last login
            voip_user.update_last_login()
            return voip_user
            
        except Exception as e:
            VoipLoggingUtils.log_if_enabled(
                request.env, _logger, 'error', 
                "Error getting current VoIP user: %s", str(e)
            )
            return None

    def get_voip_config(self):
        """Get VoIP configuration for current user"""
        try:
            VoipLoggingUtils.log_if_enabled(
                request.env, _logger, 'info', 
                'Getting VoIP config for user %s', request.env.user.name
            )
            
            voip_user = self.get_current_voip_user()
            if not voip_user:
                return {
                    'error': 'No VoIP configuration found for current user'
                }
            
            config = voip_user.get_voip_config()
            
            # Add logging configuration
            logging_config = VoipLoggingUtils.get_js_logging_config(request.env, voip_user.server_id.id)
            config['logging'] = logging_config
            
            return config
        except Exception as e:
            VoipLoggingUtils.log_if_enabled(
                request.env, _logger, 'error', 
                "Error getting VoIP config: %s", str(e)
            )
            return {
                'error': str(e)
            }

    def search_partner_by_phone(self, phone):
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
                    'success': True,
                    'partner': {
                        'id': partner.id,
                        'name': partner.name,
                        'phone': partner.phone,
                        'mobile': partner.mobile,
                        'email': partner.email,
                    }
                }
            else:
                return {
                    'success': True,
                    'partner': None
                }
        except Exception as e:
            _logger.exception("Error searching partner: %s", str(e))
            return {'success': False, 'error': str(e)}

    def get_contacts_list(self, limit=100):
        """Get contacts list with phone numbers"""
        try:
            partners = request.env['res.partner'].search([
                '|', ('phone', '!=', False), ('mobile', '!=', False)
            ], limit=limit, order='name')
            
            contacts = []
            for partner in partners:
                phone = partner.phone or partner.mobile
                if phone:
                    contacts.append({
                        'id': partner.id,
                        'name': partner.name,
                        'phone': phone,
                        'mobile': partner.mobile,
                        'email': partner.email,
                        'company': partner.parent_id.name if partner.parent_id else None,
                    })
            
            return {
                'success': True,
                'contacts': contacts
            }
        except Exception as e:
            _logger.exception("Error getting contacts list: %s", str(e))
            return {'success': False, 'error': str(e)}

