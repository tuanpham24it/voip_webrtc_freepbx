# -*- coding: utf-8 -*-
#################################################################################
#
# Module Name: Voip Webrtc Freepbx
# Description: Wizard to show API key in plain text
#
# Copyright (c) 2025
# Author: Mohamed Samir Abouelez 
# Website: https://odoo-vip.com
# Email: kenzey0man@gmail.com
#
#################################################################################

from odoo import models, fields, api


class VoipShowApiKeyWizard(models.TransientModel):
    _name = 'voip.show.api.key.wizard'
    _description = 'Show API Key Wizard'

    server_id = fields.Many2one(
        'voip.server',
        string='VoIP Server',
        required=True,
        readonly=True
    )
    
    api_key = fields.Char(
        string='API Key',
        related='server_id.api_key',
        readonly=True
    )
    
    server_name = fields.Char(
        string='Server Name',
        related='server_id.name',
        readonly=True
    )
    
    websocket_url = fields.Char(
        string='WebSocket URL',
        related='server_id.websocket_url',
        readonly=True
    )
    
    webhook_url = fields.Char(
        string='Webhook URL',
        compute='_compute_webhook_url',
        readonly=True
    )
    
    @api.depends('server_id')
    def _compute_webhook_url(self):
        """Compute the full webhook URL"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            record.webhook_url = f"{base_url}/pbx/webhook"
    
    def action_copy_api_key(self):
        """Copy API key to clipboard"""
        self.ensure_one()
        return self.server_id.action_copy_api_key()
    
    def action_copy_webhook_url(self):
        """Copy webhook URL to clipboard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'voip_copy_to_clipboard',
            'params': {
                'text': self.webhook_url,
                'title': 'Webhook URL Copied',
                'message': 'Webhook URL has been copied to clipboard successfully.',
            }
        }









