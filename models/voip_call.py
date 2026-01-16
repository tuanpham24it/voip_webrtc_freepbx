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

_logger = logging.getLogger(__name__)


class VoipCall(models.Model):
    _name = 'voip.call'
    _description = 'VoIP Call Log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_time desc'

    name = fields.Char(
        string='Call Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    user_id = fields.Many2one(
        'voip.user',
        string='VoIP User',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    
    server_id = fields.Many2one(
        'voip.server',
        string='VoIP Server',
        related='user_id.server_id',
        store=True,
        readonly=True
    )
    
    odoo_user_id = fields.Many2one(
        'res.users',
        string='Odoo User',
        related='user_id.user_id',
        store=True,
        readonly=True
    )
    
    direction = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
    ], string='Direction', required=True, tracking=True)
    
    state = fields.Selection([
        ('ringing', 'Ringing'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('failed', 'Failed'),
        ('busy', 'Busy'),
        ('rejected', 'Rejected'),
    ], string='Status', default='ringing', required=True, tracking=True)
    
    from_number = fields.Char(
        string='From Number',
        required=True,
        tracking=True
    )
    
    to_number = fields.Char(
        string='To Number',
        required=True,
        tracking=True
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        tracking=True,
        help='Contact associated with this call'
    )
    
    start_time = fields.Datetime(
        string='Start Time',
        required=True,
        default=fields.Datetime.now,
        tracking=True
    )
    
    answer_time = fields.Datetime(
        string='Answer Time',
        tracking=True
    )
    
    end_time = fields.Datetime(
        string='End Time',
        tracking=True
    )
    
    response_time = fields.Integer(
        string='Response Time (seconds)',
        compute='_compute_response_time',
        store=True,
        help='Time between start time and answer time in seconds'
    )
    
    duration = fields.Float(
        string='Duration (seconds)',
        compute='_compute_duration',
        store=True,
        help='Call duration in seconds'
    )
    
    duration_display = fields.Char(
        string='Duration',
        compute='_compute_duration_display'
    )
    
    call_id = fields.Char(
        string='SIP Call ID',
        help='Unique SIP call identifier'
    )
    
    recording_ids = fields.One2many(
        'voip.recording',
        'call_id',
        string='Recordings'
    )
    
    recording_count = fields.Integer(
        string='Number of Recordings',
        compute='_compute_recording_count',
        store=True
    )
    
    has_recording = fields.Boolean(
        string='Has Recording',
        compute='_compute_recording_count',
        store=True,
        search='_search_has_recording'
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    hangup_reason = fields.Char(
        string='Hangup Reason',
        help='Reason for call termination'
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('voip.call') or _('New')
        return super(VoipCall, self).create(vals)

    @api.depends('start_time', 'answer_time')
    def _compute_response_time(self):
        """Calculate response time in seconds between start_time and answer_time"""
        for record in self:
            if record.start_time and record.answer_time:
                delta = record.answer_time - record.start_time
                record.response_time = int(delta.total_seconds())
            else:
                record.response_time = 0

    @api.depends('answer_time', 'end_time', 'start_time')
    def _compute_duration(self):
        for record in self:
            if record.end_time:
                # If answer_time exists, calculate from answer_time to end_time
                if record.answer_time:
                    delta = record.end_time - record.answer_time
                    record.duration = delta.total_seconds()
                # If no answer_time but end_time exists, calculate from start_time to end_time
                elif record.start_time:
                    delta = record.end_time - record.start_time
                    record.duration = delta.total_seconds()
                else:
                    record.duration = 0.0
            else:
                record.duration = 0.0

    @api.depends('duration')
    def _compute_duration_display(self):
        for record in self:
            if record.duration:
                hours = int(record.duration // 3600)
                minutes = int((record.duration % 3600) // 60)
                seconds = int(record.duration % 60)
                
                if hours > 0:
                    record.duration_display = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    record.duration_display = f"{minutes:02d}:{seconds:02d}"
            else:
                record.duration_display = "00:00"

    @api.depends('recording_ids')
    def _compute_recording_count(self):
        for record in self:
            record.recording_count = len(record.recording_ids)
            record.has_recording = record.recording_count > 0
            _logger.info('🔧 VoIP Call Debug: Call %s has %s recordings', record.name, record.recording_count)
    
    def _search_has_recording(self, operator, value):
        """Search method for has_recording field"""
        if operator == '=' and value:
            # Find calls that have recordings
            return [('recording_count', '>', 0)]
        elif operator == '=' and not value:
            # Find calls without recordings
            return [('recording_count', '=', 0)]
        elif operator == '!=' and value:
            # Find calls without recordings
            return [('recording_count', '=', 0)]
        elif operator == '!=' and not value:
            # Find calls that have recordings
            return [('recording_count', '>', 0)]
        else:
            return []

    @api.onchange('from_number', 'to_number', 'direction')
    def _onchange_find_partner(self):
        if self.direction == 'inbound':
            phone = self.from_number
        else:
            phone = self.to_number
        
        if phone:
            # Clean phone number for search
            clean_phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            
            # Search for partner by phone
            partner = self.env['res.partner'].search([
                '|', '|',
                ('phone', 'ilike', clean_phone),
                ('mobile', 'ilike', clean_phone),
                ('phone', 'ilike', phone)
            ], limit=1)
            
            if partner:
                self.partner_id = partner

    def action_view_recordings(self):
        self.ensure_one()
        return {
            'name': _('Call Recordings'),
            'type': 'ir.actions.act_window',
            'res_model': 'voip.recording',
            'view_mode': 'list,form',
            'domain': [('call_id', '=', self.id)],
            'context': {'default_call_id': self.id}
        }

    def action_start_call(self):
        self.ensure_one()
        if self.state == 'ringing':
            self.write({
                'state': 'in_progress',
                'answer_time': fields.Datetime.now()
            })

    def action_end_call(self, reason='normal'):
        self.ensure_one()
        vals = {
            'end_time': fields.Datetime.now(),
            'hangup_reason': reason
        }
        
        if self.state == 'ringing':
            vals['state'] = 'missed'
        elif self.state == 'in_progress':
            vals['state'] = 'completed'
        
        self.write(vals)

    def action_mark_as_missed(self):
        self.ensure_one()
        self.write({
            'state': 'missed',
            'end_time': fields.Datetime.now()
        })
