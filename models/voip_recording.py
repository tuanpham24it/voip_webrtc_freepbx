from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import base64
import logging

_logger = logging.getLogger(__name__)


class VoipRecording(models.Model):
    _name = 'voip.recording'
    _description = 'VoIP Call Recording'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Recording Name',
        required=True,
        tracking=True
    )
    
    call_id = fields.Many2one(
        'voip.call',
        string='Call',
        ondelete='cascade',
        tracking=True
    )
    
    sip_session_id = fields.Char(
        string='SIP Session ID',
        help='SIP session identifier for standalone recordings',
        tracking=True
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        related='call_id.odoo_user_id',
        store=True,
        readonly=True
    )
    
    # Caller Information
    caller_user_id = fields.Many2one(
        'res.users',
        string='Caller (User)',
        help='Internal user who initiated the call',
        tracking=True
    )
    
    caller_partner_id = fields.Many2one(
        'res.partner',
        string='Caller (Contact)',
        help='External contact who initiated the call',
        tracking=True
    )
    
    caller_display = fields.Char(
        string='Caller',
        compute='_compute_caller_callee_display',
        store=True
    )
    
    # Callee Information
    callee_user_id = fields.Many2one(
        'res.users',
        string='Callee (User)',
        help='Internal user who received the call',
        tracking=True
    )
    
    callee_partner_id = fields.Many2one(
        'res.partner',
        string='Callee (Contact)',
        help='External contact who received the call',
        tracking=True
    )
    
    callee_display = fields.Char(
        string='Callee',
        compute='_compute_caller_callee_display',
        store=True
    )
    
    recording_file = fields.Binary(
        string='Recording File',
        attachment=True,
        help='Audio file of the call recording'
    )
    
    recording_filename = fields.Char(
        string='Filename'
    )
    
    file_size = fields.Integer(
        string='File Size',
        help='File size in bytes'
    )
    
    file_size_display = fields.Char(
        string='Size',
        compute='_compute_file_size_display'
    )
    
    duration = fields.Float(
        string='Duration (seconds)',
        help='Recording duration in seconds'
    )
    
    duration_display = fields.Char(
        string='Duration',
        compute='_compute_duration_display'
    )
    
    recording_type = fields.Selection([
        ('automatic', 'Automatic'),
        ('manual', 'Manual'),
    ], string='Recording Type', default='automatic', required=True)
    
    state = fields.Selection([
        ('recording', 'Recording'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], string='Status', default='recording', required=True, tracking=True)
    
    recording_url = fields.Char(
        string='Recording URL',
        compute='_compute_recording_url',
        help='URL to access the recording file'
    )
    
    shared_with_ids = fields.Many2many(
        'res.users',
        'voip_recording_share_rel',
        'recording_id',
        'user_id',
        string='Shared With',
        tracking=True,
        help='Users who have access to this recording'
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    format = fields.Selection([
        ('wav', 'WAV'),
        ('mp3', 'MP3'),
        ('ogg', 'OGG'),
    ], string='Format', default='wav')
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to automatically populate caller and callee information"""
        for vals in vals_list:
            if vals.get('call_id'):
                call = self.env['voip.call'].browse(vals['call_id'])
                _logger.info('🔧 VoIP Recording Debug: Creating recording for call_id=%s', vals['call_id'])
                
                if call.exists():
                    _logger.info('🔧 VoIP Recording Debug: Call found - from_number=%s, to_number=%s, direction=%s, odoo_user_id=%s', 
                                call.from_number, call.to_number, call.direction, call.odoo_user_id.id if call.odoo_user_id else None)
                    
                    # Populate caller and callee based on call direction
                    caller_info = self._identify_caller_callee(call.from_number, call.direction == 'outbound', call.odoo_user_id)
                    callee_info = self._identify_caller_callee(call.to_number, call.direction == 'inbound', call.odoo_user_id)
                    
                    _logger.info('🔧 VoIP Recording Debug: Caller info: %s', caller_info)
                    _logger.info('🔧 VoIP Recording Debug: Callee info: %s', callee_info)
                    
                    # Set caller fields
                    if not vals.get('caller_user_id') and caller_info.get('user_id'):
                        vals['caller_user_id'] = caller_info['user_id']
                    if not vals.get('caller_partner_id') and caller_info.get('partner_id'):
                        vals['caller_partner_id'] = caller_info['partner_id']
                    
                    # Set callee fields
                    if not vals.get('callee_user_id') and callee_info.get('user_id'):
                        vals['callee_user_id'] = callee_info['user_id']
                    if not vals.get('callee_partner_id') and callee_info.get('partner_id'):
                        vals['callee_partner_id'] = callee_info['partner_id']
                    
                    _logger.info('🔧 VoIP Recording Debug: Final vals - caller_user_id=%s, caller_partner_id=%s, callee_user_id=%s, callee_partner_id=%s',
                                vals.get('caller_user_id'), vals.get('caller_partner_id'), vals.get('callee_user_id'), vals.get('callee_partner_id'))
                else:
                    _logger.warning('🔧 VoIP Recording Debug: Call with ID %s not found!', vals['call_id'])
        
        return super(VoipRecording, self).create(vals_list)
    
    def _identify_caller_callee(self, phone_number, is_internal, odoo_user):
        """
        Identify if a phone number belongs to an internal user or external partner
        
        Args:
            phone_number: Phone number to identify
            is_internal: True if this is the internal party (VoIP user)
            odoo_user: The Odoo user associated with the call
        
        Returns:
            dict: {'user_id': int or False, 'partner_id': int or False}
        """
        _logger.info('🔧 VoIP Recording Debug: _identify_caller_callee called with phone_number=%s, is_internal=%s, odoo_user=%s',
                    phone_number, is_internal, odoo_user.id if odoo_user else None)
        
        result = {'user_id': False, 'partner_id': False}
        
        if not phone_number:
            _logger.info('🔧 VoIP Recording Debug: No phone number provided, returning empty result')
            return result
        
        # If this is the internal party, link to the Odoo user
        if is_internal and odoo_user:
            result['user_id'] = odoo_user.id
            _logger.info('🔧 VoIP Recording Debug: Internal party identified as user_id=%s', odoo_user.id)
            return result
        
        # Otherwise, search for external partner by phone number
        clean_phone = phone_number.replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
        _logger.info('🔧 VoIP Recording Debug: Searching for partner with phone=%s (clean=%s)', phone_number, clean_phone)
        
        # Search for partner with matching phone or mobile
        partner = self.env['res.partner'].search([
            '|', '|',
            ('phone', 'ilike', clean_phone),
            ('mobile', 'ilike', clean_phone),
            ('phone', '=', phone_number)
        ], limit=1)
        
        if partner:
            result['partner_id'] = partner.id
            _logger.info('🔧 VoIP Recording Debug: Partner found: %s (id=%s)', partner.name, partner.id)
        else:
            _logger.info('🔧 VoIP Recording Debug: No partner found with phone number')
        
        # Also check if the phone number belongs to a VoIP user (internal SIP username)
        if not result['partner_id']:
            _logger.info('🔧 VoIP Recording Debug: Searching for VoIP user with sip_username=%s', clean_phone)
            voip_user = self.env['voip.user'].search([
                '|',
                ('sip_username', '=', phone_number),
                ('sip_username', '=', clean_phone)
            ], limit=1)
            
            if voip_user and voip_user.user_id:
                result['user_id'] = voip_user.user_id.id
                _logger.info('🔧 VoIP Recording Debug: VoIP user found: %s (user_id=%s)', voip_user.name, voip_user.user_id.id)
            else:
                _logger.info('🔧 VoIP Recording Debug: No VoIP user found with sip_username')
        
        return result
    
    @api.depends('caller_user_id', 'caller_partner_id', 'callee_user_id', 'callee_partner_id', 'call_id.from_number', 'call_id.to_number')
    def _compute_caller_callee_display(self):
        for record in self:
            # Compute Caller Display
            if record.caller_user_id:
                record.caller_display = f"{record.caller_user_id.name} (User)"
            elif record.caller_partner_id:
                record.caller_display = f"{record.caller_partner_id.name} (Contact)"
            elif record.call_id and record.call_id.from_number:
                record.caller_display = record.call_id.from_number
            else:
                record.caller_display = 'Unknown'
            
            # Compute Callee Display
            if record.callee_user_id:
                record.callee_display = f"{record.callee_user_id.name} (User)"
            elif record.callee_partner_id:
                record.callee_display = f"{record.callee_partner_id.name} (Contact)"
            elif record.call_id and record.call_id.to_number:
                record.callee_display = record.call_id.to_number
            else:
                record.callee_display = 'Unknown'
    
    @api.depends('recording_file', 'recording_filename')
    def _compute_recording_url(self):
        for record in self:
            if record.recording_file and record.id:
                record.recording_url = f'/web/content/voip.recording/{record.id}/recording_file/{record.recording_filename or "recording.webm"}'
            else:
                record.recording_url = False

    @api.depends('file_size')
    def _compute_file_size_display(self):
        for record in self:
            if record.file_size:
                size = record.file_size
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024.0:
                        record.file_size_display = f"{size:.2f} {unit}"
                        break
                    size /= 1024.0
            else:
                record.file_size_display = '0 B'

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

    def action_share_recording(self):
        self.ensure_one()
        return {
            'name': _('Share Recording'),
            'type': 'ir.actions.act_window',
            'res_model': 'voip.recording.share.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_recording_id': self.id}
        }

    def action_download_recording(self):
        self.ensure_one()
        if not self.recording_file:
            raise UserError(_('No recording file available for download.'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/voip.recording/{self.id}/recording_file/{self.recording_filename}?download=true',
            'target': 'self',
        }

    def action_play_recording(self):
        self.ensure_one()
        if not self.recording_file:
            raise UserError(_('No recording file available to play.'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/voip.recording/{self.id}/recording_file/{self.recording_filename}',
            'target': 'new',
        }

    def share_with_users(self, user_ids):
        self.ensure_one()
        self.shared_with_ids = [(4, user_id) for user_id in user_ids]
        
        # Send notification to shared users
        for user in self.env['res.users'].browse(user_ids):
            self.message_post(
                body=_('Recording shared with %s', user.name),
                partner_ids=user.partner_id.ids,
                subtype_xmlid='mail.mt_note'
            )

    def unshare_from_user(self, user_id):
        self.ensure_one()
        self.shared_with_ids = [(3, user_id)]
        
        user = self.env['res.users'].browse(user_id)
        self.message_post(
            body=_('Recording unshared from %s', user.name),
            subtype_xmlid='mail.mt_note'
        )
