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


class VoipHoldMusic(models.Model):
    _name = 'voip.hold.music'
    _description = 'VoIP Hold Music'
    _order = 'sequence, name'

    name = fields.Char(
        string='Music Name',
        required=True,
        help='Display name for the hold music'
    )
    
    description = fields.Text(
        string='Description',
        help='Description of the hold music'
    )
    
    music_file = fields.Binary(
        string='Music File',
        required=False,
        help='Audio file for hold music (MP3, WAV, OGG)'
    )
    
    music_filename = fields.Char(
        string='Filename',
        help='Original filename of the uploaded music file'
    )
    
    file_size = fields.Integer(
        string='File Size (bytes)',
        compute='_compute_file_size',
        store=True,
        help='Size of the music file in bytes'
    )
    
    duration = fields.Float(
        string='Duration (seconds)',
        help='Duration of the music file in seconds'
    )
    
    format = fields.Selection([
        ('mp3', 'MP3'),
        ('wav', 'WAV'),
        ('ogg', 'OGG'),
        ('m4a', 'M4A'),
    ], string='Format', required=True, default='mp3')
    
    quality = fields.Selection([
        ('low', 'Low (64kbps)'),
        ('medium', 'Medium (128kbps)'),
        ('high', 'High (256kbps)'),
        ('lossless', 'Lossless'),
    ], string='Quality', default='medium')
    
    volume = fields.Float(
        string='Default Volume',
        default=0.7,
        help='Default volume level (0.0 to 1.0)'
    )
    
    loop = fields.Boolean(
        string='Loop',
        default=True,
        help='Whether the music should loop continuously'
    )
    
    fade_in = fields.Float(
        string='Fade In (seconds)',
        default=0.0,
        help='Fade in duration in seconds'
    )
    
    fade_out = fields.Float(
        string='Fade Out (seconds)',
        default=0.0,
        help='Fade out duration in seconds'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of display in the music list'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this hold music is available for use'
    )
    
    server_id = fields.Many2one(
        'voip.server',
        string='VoIP Server',
        required=True,
        help='VoIP server this hold music belongs to'
    )
    
    usage_count = fields.Integer(
        string='Usage Count',
        default=0,
        help='Number of times this music has been used'
    )
    
    last_used = fields.Datetime(
        string='Last Used',
        help='When this music was last used'
    )
    
    tags = fields.Char(
        string='Tags',
        help='Comma-separated tags for categorization (e.g., classical, jazz, corporate)'
    )
    
    is_default = fields.Boolean(
        string='Default Music',
        default=False,
        help='Whether this is the default hold music'
    )

    @api.depends('music_file')
    def _compute_file_size(self):
        for record in self:
            if record.music_file:
                record.file_size = len(record.music_file)
            else:
                record.file_size = 0

    @api.constrains('volume')
    def _check_volume(self):
        for record in self:
            if not 0.0 <= record.volume <= 1.0:
                raise ValidationError(_('Volume must be between 0.0 and 1.0'))

    @api.constrains('duration')
    def _check_duration(self):
        for record in self:
            if record.duration and record.duration <= 0:
                raise ValidationError(_('Duration must be positive'))

    @api.constrains('fade_in', 'fade_out')
    def _check_fade_times(self):
        for record in self:
            if record.fade_in < 0 or record.fade_out < 0:
                raise ValidationError(_('Fade times must be non-negative'))
            if record.duration and (record.fade_in + record.fade_out) >= record.duration:
                raise ValidationError(_('Fade times cannot exceed music duration'))

    @api.onchange('music_file')
    def _onchange_music_file(self):
        """Handle music file upload"""
        if self.music_file:
            # Update filename if not set
            if not self.music_filename:
                self.music_filename = 'hold_music.wav'
            
            # Update file size
            self.file_size = len(self.music_file)
            
            # Set format based on filename if not set
            if not self.format:
                if self.music_filename.lower().endswith('.mp3'):
                    self.format = 'mp3'
                elif self.music_filename.lower().endswith('.wav'):
                    self.format = 'wav'
                elif self.music_filename.lower().endswith('.ogg'):
                    self.format = 'ogg'
                else:
                    self.format = 'wav'  # Default to WAV
            
            # Set quality based on file size
            if self.file_size < 100000:  # Less than 100KB
                self.quality = 'low'
            elif self.file_size < 500000:  # Less than 500KB
                self.quality = 'medium'
            else:
                self.quality = 'high'

    @api.onchange('format')
    def _onchange_format(self):
        """Handle format change"""
        if self.format and self.music_filename:
            name_without_ext = self.music_filename.rsplit('.', 1)[0]
            self.music_filename = f"{name_without_ext}.{self.format}"

    @api.onchange('volume')
    def _onchange_volume(self):
        """Handle volume change"""
        if self.volume < 0:
            self.volume = 0.0
        elif self.volume > 1:
            self.volume = 1.0

    @api.onchange('is_default')
    def _onchange_is_default(self):
        """Handle default music change"""
        pass

    @api.onchange('server_id')
    def _onchange_server_id(self):
        """Handle server change"""
        if self.server_id and self.is_default:
            self.is_default = False

    @api.onchange('name')
    def _onchange_name(self):
        """Handle name change"""
        if self.name and not self.music_filename:
            self.music_filename = f"{self.name.lower().replace(' ', '_')}.wav"

    @api.onchange('music_filename')
    def _onchange_music_filename(self):
        """Handle filename change"""
        if self.music_filename and not self.format:
            if self.music_filename.lower().endswith('.mp3'):
                self.format = 'mp3'
            elif self.music_filename.lower().endswith('.wav'):
                self.format = 'wav'
            elif self.music_filename.lower().endswith('.ogg'):
                self.format = 'ogg'
            else:
                self.format = 'wav'

    @api.onchange('active')
    def _onchange_active(self):
        """Handle active change"""
        pass

    @api.model
    def create(self, vals):
        # Set default server if not provided
        if 'server_id' not in vals:
            default_server = self.env['voip.server'].search([('active', '=', True)], limit=1)
            if default_server:
                vals['server_id'] = default_server.id
            else:
                raise ValidationError(_('No active VoIP server found. Please create a VoIP server first.'))
        
        # Ensure only one default music per server
        if vals.get('is_default', False):
            server_id = vals.get('server_id')
            if server_id:
                self.env['voip.hold.music'].search([
                    ('server_id', '=', server_id),
                    ('is_default', '=', True)
                ]).write({'is_default': False})
        
        return super(VoipHoldMusic, self).create(vals)

    def write(self, vals):
        # Handle default music changes
        if 'is_default' in vals and vals['is_default']:
            for record in self:
                self.env['voip.hold.music'].search([
                    ('server_id', '=', record.server_id.id),
                    ('is_default', '=', True),
                    ('id', '!=', record.id)
                ]).write({'is_default': False})
        
        return super(VoipHoldMusic, self).write(vals)

    def action_set_default(self):
        """Set this music as the default for its server"""
        self.ensure_one()
        # Unset other defaults for the same server
        self.env['voip.hold.music'].search([
            ('server_id', '=', self.server_id.id),
            ('is_default', '=', True),
            ('id', '!=', self.id)
        ]).write({'is_default': False})
        
        # Set this as default
        self.write({'is_default': True})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Default Music Set'),
                'message': _('This music is now the default hold music for %s') % self.server_id.name,
                'type': 'success',
            }
        }

    def action_play_preview(self):
        """Play a preview of the hold music"""
        self.ensure_one()
        if not self.music_file:
            raise ValidationError(_('No music file available for preview'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/voip_webrtc_freepbx/hold_music/preview/{self.id}',
            'target': 'new',
        }

    def action_test_music(self):
        """Test the hold music by playing it directly"""
        self.ensure_one()
        if not self.music_file:
            raise ValidationError(_('No music file available for testing'))
        
        # Increment usage count
        self.action_increment_usage()
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/voip_webrtc_freepbx/hold_music/test/{self.id}',
            'target': 'new',
        }

    def action_replace_music(self):
        """Replace the current music file"""
        self.ensure_one()
        if not self.music_file:
            raise ValidationError(_('No music file to replace'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Replace Music File'),
            'res_model': 'voip.hold.music',
            'res_id': self.id,
            'view_mode': 'form',
            'view_id': False,
            'target': 'current',
            'context': {
                'default_name': self.name,
                'default_server_id': self.server_id.id,
                'default_format': self.format,
                'default_volume': self.volume,
                'default_loop': self.loop,
                'default_active': self.active,
                'replace_music': True,
            }
        }

    def action_increment_usage(self):
        """Increment usage count and update last used time"""
        self.ensure_one()
        self.write({
            'usage_count': self.usage_count + 1,
            'last_used': fields.Datetime.now()
        })

    def get_music_url(self):
        """Get the URL for this hold music file"""
        self.ensure_one()
        return f'/voip_webrtc_freepbx/hold_music/file/{self.id}'

    def get_music_config(self):
        """Get configuration for this hold music"""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'url': self.get_music_url(),
            'volume': self.volume,
            'loop': self.loop,
            'fade_in': self.fade_in,
            'fade_out': self.fade_out,
            'duration': self.duration,
            'format': self.format,
            'quality': self.quality,
            'tags': self.tags.split(',') if self.tags else [],
            'is_default': self.is_default,
        }

    @api.model
    def get_available_music(self, server_id=None):
        """Get list of available hold music for a server"""
        try:
            domain = [('active', '=', True)]
            if server_id:
                domain.append(('server_id', '=', server_id))
            
            # First try to get uploaded music files (priority)
            uploaded_domain = domain + [('music_file', '!=', False)]
            music_records = self.search(uploaded_domain, order='sequence, name')
            
            # If no uploaded files, get all music
            if not music_records:
                music_records = self.search(domain, order='sequence, name')
            
            return [music.get_music_config() for music in music_records if music.exists()]
        except Exception as e:
            _logger.warning(f"Error getting available music: {e}")
            return []

    @api.model
    def get_default_music(self, server_id=None):
        """Get the default hold music for a server"""
        try:
            domain = [('active', '=', True), ('is_default', '=', True)]
            if server_id:
                domain.append(('server_id', '=', server_id))
            
            default_music = self.search(domain, limit=1)
            if default_music and default_music.exists():
                return default_music.get_music_config()
            
            # Fallback to first available music
            fallback_domain = [('active', '=', True)]
            if server_id:
                fallback_domain.append(('server_id', '=', server_id))
            
            fallback = self.search(fallback_domain, limit=1)
            if fallback and fallback.exists():
                return fallback.get_music_config()
            
            return None
        except Exception as e:
            _logger.warning(f"Error getting default music: {e}")
            return None


