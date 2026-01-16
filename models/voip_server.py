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
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
import secrets
from ..utils.logging_utils import VoipLoggingUtils

_logger = logging.getLogger(__name__)


class VoipServer(models.Model):
    _name = 'voip.server'
    _description = 'VoIP Server Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Server Name',
        required=True,
        tracking=True,
        help='Name to identify this VoIP server'
    )
    
    host = fields.Char(
        string='Server Host',
        required=True,
        tracking=True,
        help='FreePBX server hostname or IP address'
    )
    
    websocket_url = fields.Char(
        string='WebSocket URL',
        required=True,
        tracking=True,
        help='WebSocket URL for WebRTC connection (e.g., wss://your-server:8089/ws)'
    )
    
    api_key = fields.Char(
        string='API Key',
        required=False,
        tracking=True,
        copy=False,
        default=lambda self: self._generate_api_key(),
        help='Unique API key for webhook authentication. This key must be sent in X-API-Key header when calling the webhook endpoint. Auto-generated if not provided.'
    )
    
    hold_music_config = fields.Text(
        string='Hold Music Configuration',
        help='JSON configuration for hold music files. Format: {"music_files": [{"id": "1", "name": "Music Name", "file_path": "/path/to/file.wav"}]}'
    )
    
    port = fields.Integer(
        string='SIP Port',
        default=5060,
        tracking=True,
        help='SIP port number (default: 5060)'
    )
    
    secure_port = fields.Integer(
        string='Secure SIP Port',
        default=5061,
        help='Secure SIP port number (default: 5061)'
    )
    
    use_tls = fields.Boolean(
        string='Use TLS',
        default=True,
        tracking=True,
        help='Enable TLS encryption for SIP connection'
    )
    
    realm = fields.Char(
        string='Realm',
        help='SIP realm for authentication'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    user_ids = fields.One2many(
        'voip.user',
        'server_id',
        string='VoIP Users'
    )
    
    user_count = fields.Integer(
        string='Number of Users',
        compute='_compute_user_count'
    )
    
    call_ids = fields.One2many(
        'voip.call',
        'server_id',
        string='Calls'
    )
    
    call_count = fields.Integer(
        string='Number of Calls',
        compute='_compute_call_count'
    )
    
    enable_recording = fields.Boolean(
        string='Enable Call Recording',
        default=True,
        tracking=True,
        help='Enable automatic call recording'
    )
    
    recording_path = fields.Char(
        string='Recording Path',
        help='Path where call recordings are stored on FreePBX server'
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    logging_mode = fields.Selection(
        [('production', 'Production'), ('test', 'Test')],
        string='Logging Mode',
        default='production',
        required=True,
        tracking=True,
        help='Production: Enable all logging. Test: Disable all logging for testing purposes.'
    )

    @api.model
    def _generate_api_key(self):
        """Generate a secure random API key"""
        return secrets.token_urlsafe(32)
    
    @api.model
    def create(self, vals):
        """Auto-generate API key if not provided"""
        if not vals.get('api_key'):
            vals['api_key'] = self._generate_api_key()
        return super(VoipServer, self).create(vals)
    
    @api.depends('user_ids')
    def _compute_user_count(self):
        for record in self:
            record.user_count = len(record.user_ids)

    @api.depends('call_ids')
    def _compute_call_count(self):
        for record in self:
            record.call_count = len(record.call_ids)

    @api.constrains('host', 'websocket_url')
    def _check_server_config(self):
        for record in self:
            if not record.host:
                raise ValidationError(_('Server host is required.'))
            if not record.websocket_url:
                raise ValidationError(_('WebSocket URL is required.'))
    
    @api.constrains('api_key')
    def _check_api_key_unique(self):
        """Ensure API key is unique across all servers"""
        for record in self:
            if record.api_key:
                duplicate = self.search([
                    ('api_key', '=', record.api_key),
                    ('id', '!=', record.id)
                ], limit=1)
                if duplicate:
                    raise ValidationError(_(
                        'API Key must be unique! Server "%s" is already using this API key.'
                    ) % duplicate.name)

    def action_test_connection(self):
        self.ensure_one()
        # Log connection test based on logging mode
        self.log_if_enabled('info', 'Connection test initiated for server: %s', self.name)
        
        # This method can be extended to test the connection to FreePBX
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Test Connection'),
                'message': _('Connection test initiated. Check server logs for details.'),
                'type': 'info',
                'sticky': False,
            }
        }
    
    def action_regenerate_api_key(self):
        """Regenerate API key for this server"""
        self.ensure_one()
        new_api_key = self._generate_api_key()
        self.write({'api_key': new_api_key})
        self.log_if_enabled('warning', 'API key regenerated for server: %s', self.name)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('API Key Regenerated'),
                'message': _('A new API key has been generated. Please update your FreePBX webhook configuration.'),
                'type': 'warning',
                'sticky': True,
            }
        }
    
    def action_copy_api_key(self):
        """Copy API key to clipboard using JavaScript"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'voip_copy_to_clipboard',
            'params': {
                'text': self.api_key,
                'title': _('API Key Copied'),
                'message': _('API key has been copied to clipboard successfully.'),
            }
        }

    def action_view_users(self):
        self.ensure_one()
        return {
            'name': _('VoIP Users'),
            'type': 'ir.actions.act_window',
            'res_model': 'voip.user',
            'view_mode': 'list,form',
            'domain': [('server_id', '=', self.id)],
            'context': {'default_server_id': self.id}
        }

    def action_view_calls(self):
        self.ensure_one()
        return {
            'name': _('Call History'),
            'type': 'ir.actions.act_window',
            'res_model': 'voip.call',
            'view_mode': 'list,form',
            'domain': [('server_id', '=', self.id)],
        }
    
    def get_logging_config(self):
        """Get logging configuration for this server"""
        self.ensure_one()
        return VoipLoggingUtils.get_js_logging_config(self.env, self.id)
    
    def should_log(self, level='info'):
        """Check if logging should be enabled for this server"""
        self.ensure_one()
        return VoipLoggingUtils.should_log(self.env, self.id, level)
    
    def log_if_enabled(self, level, message, *args, **kwargs):
        """Log a message only if logging is enabled for this server"""
        self.ensure_one()
        VoipLoggingUtils.log_if_enabled(self.env, _logger, level, message, *args, server_id=self.id, **kwargs)
