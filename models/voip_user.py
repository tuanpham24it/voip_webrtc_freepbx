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
from ..utils.logging_utils import VoipLoggingUtils

_logger = logging.getLogger(__name__)


class VoipUser(models.Model):
    _name = 'voip.user'
    _description = 'VoIP User Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Odoo User',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    server_id = fields.Many2one(
        'voip.server',
        string='VoIP Server',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    sip_username = fields.Char(
        string='SIP Username',
        required=True,
        tracking=True,
        help='SIP extension number or username'
    )
    
    extension = fields.Char(
        string='Extension',
        help='Phone extension number'
    )
    
    sip_password = fields.Char(
        string='SIP Password',
        required=True,
        help='SIP password for authentication'
    )
    
    display_name = fields.Char(
        string='Display Name',
        help='Display name for outgoing calls'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True
    )
    
    status = fields.Selection([
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('offline', 'Offline'),
        ('away', 'Away'),
    ], string='Status', default='available', tracking=True)
    
    auto_answer = fields.Boolean(
        string='Auto Answer',
        default=False,
        help='Automatically answer incoming calls'
    )
    
    call_ids = fields.One2many(
        'voip.call',
        'user_id',
        string='Calls'
    )
    
    incoming_calls_count = fields.Integer(
        string='Incoming Calls',
        compute='_compute_call_stats'
    )
    
    outgoing_calls_count = fields.Integer(
        string='Outgoing Calls',
        compute='_compute_call_stats'
    )
    
    total_call_duration = fields.Float(
        string='Total Call Duration (hours)',
        compute='_compute_call_stats',
        help='Total duration of all calls in hours'
    )
    
    ring_tone = fields.Selection([
        ('default', 'Default'),
        ('classic', 'Classic'),
        ('modern', 'Modern'),
        ('silent', 'Silent'),
    ], string='Ring Tone', default='default')
    
    enable_recording = fields.Boolean(
        string='Enable Recording',
        default=True,
        help='Enable call recording for this user'
    )
    
    auto_start_recording = fields.Boolean(
        string='Auto Start Recording',
        default=True,
        help='Automatically start recording when call begins'
    )
    
    can_control_recording = fields.Boolean(
        string='Can Control Recording',
        default=False,
        help='Allow user to manually start/stop recording during calls'
    )
    
    recording_quality = fields.Selection([
        ('low', 'Low (64kbps)'),
        ('medium', 'Medium (128kbps)'),
        ('high', 'High (256kbps)'),
    ], string='Recording Quality', default='medium')
    
    recording_format = fields.Selection([
        ('webm', 'WebM (Recommended)'),
        ('mp4', 'MP4'),
        ('wav', 'WAV'),
    ], string='Recording Format', default='webm')
    
    last_login = fields.Datetime(
        string='Last Login',
        readonly=True
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    # Additional fields for Kanban view
    avatar = fields.Binary(
        string='Avatar',
        help='User avatar image'
    )
    
    department = fields.Char(
        string='Department',
        help='User department or team'
    )
    
    phone_number = fields.Char(
        string='Phone Number',
        help='Direct phone number'
    )
    
    email = fields.Char(
        string='Email',
        related='user_id.email',
        store=True
    )
    
    # Call statistics for Kanban
    today_calls = fields.Integer(
        string='Today Calls',
        compute='_compute_today_stats'
    )
    
    this_week_calls = fields.Integer(
        string='This Week Calls',
        compute='_compute_week_stats'
    )
    
    average_call_duration = fields.Float(
        string='Average Call Duration (min)',
        compute='_compute_average_duration'
    )

    _sql_constraints = [
        ('unique_user_server', 'unique(user_id, server_id)', 
         'A user can only have one VoIP configuration per server!')
    ]

    @api.depends('user_id', 'sip_username')
    def _compute_name(self):
        for record in self:
            if record.user_id and record.sip_username:
                record.name = f"{record.user_id.name} ({record.sip_username})"
            elif record.user_id:
                record.name = record.user_id.name
            else:
                record.name = record.sip_username or 'New VoIP User'

    @api.depends('call_ids', 'call_ids.direction', 'call_ids.duration')
    def _compute_call_stats(self):
        for record in self:
            incoming_calls = record.call_ids.filtered(lambda c: c.direction == 'inbound')
            outgoing_calls = record.call_ids.filtered(lambda c: c.direction == 'outbound')
            
            record.incoming_calls_count = len(incoming_calls)
            record.outgoing_calls_count = len(outgoing_calls)
            record.total_call_duration = sum(record.call_ids.mapped('duration')) / 3600.0

    def action_view_calls(self):
        self.ensure_one()
        return {
            'name': _('Call History'),
            'type': 'ir.actions.act_window',
            'res_model': 'voip.call',
            'view_mode': 'list,form',
            'domain': [('user_id', '=', self.id)],
            'context': {'default_user_id': self.id}
        }

    def get_voip_config(self):
        self.ensure_one()
        return {
            'server': {
                'host': self.server_id.host,
                'websocket_url': self.server_id.websocket_url,
                'port': self.server_id.port,
                'realm': self.server_id.realm or self.server_id.host,
                'use_tls': self.server_id.use_tls,
            },
            'user': {
                'username': self.sip_username,
                'password': self.sip_password,
                'display_name': self.display_name or self.user_id.name,
                'auto_answer': self.auto_answer,
                'ring_tone': self.ring_tone,
                'enable_recording': self.enable_recording,
                'auto_start_recording': self.auto_start_recording,
                'can_control_recording': self.can_control_recording,
                'recording_quality': self.recording_quality,
                'recording_format': self.recording_format,
            }
        }

    def update_last_login(self):
        self.ensure_one()
        self.last_login = fields.Datetime.now()
        # Log login update based on server logging mode
        VoipLoggingUtils.log_if_enabled(
            self.env, _logger, 'info', 
            'VoIP user %s logged in', self.name, 
            server_id=self.server_id.id
        )
    
    def toggle_active(self):
        """Toggle active status of VoIP user"""
        self.ensure_one()
        self.active = not self.active
        return True
    
    @api.depends('call_ids', 'call_ids.start_time')
    def _compute_today_stats(self):
        today = fields.Date.today()
        for record in self:
            today_calls = record.call_ids.filtered(
                lambda c: c.start_time and c.start_time.date() == today
            )
            record.today_calls = len(today_calls)
    
    @api.depends('call_ids', 'call_ids.start_time')
    def _compute_week_stats(self):
        from datetime import datetime, timedelta
        today = fields.Date.today()
        week_start = today - timedelta(days=today.weekday())
        for record in self:
            week_calls = record.call_ids.filtered(
                lambda c: c.start_time and c.start_time.date() >= week_start
            )
            record.this_week_calls = len(week_calls)
    
    @api.depends('call_ids', 'call_ids.duration')
    def _compute_average_duration(self):
        for record in self:
            if record.call_ids:
                total_duration = sum(record.call_ids.mapped('duration'))
                record.average_call_duration = total_duration / len(record.call_ids) / 60.0
            else:
                record.average_call_duration = 0.0
