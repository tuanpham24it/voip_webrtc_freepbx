# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
import json


class VoipEvent(models.Model):
    _name = 'voip.event'
    _description = 'VoIP Event Log'
    _order = 'timestamp desc'
    _rec_name = 'event_summary'

    # Basic Event Information
    event_type = fields.Char(
        string='Event Type',
        required=True,
        help='Type of VoIP event (e.g., Newchannel, Hangup, PeerStatus)'
    )
    
    timestamp = fields.Datetime(
        string='Timestamp',
        required=True,
        help='When the event occurred'
    )
    
    server_id = fields.Many2one(
        'voip.server',
        string='VoIP Server',
        required=True,
        help='The server that generated this event'
    )
    
    # Event Data
    raw_data = fields.Text(
        string='Raw Event Data',
        help='Complete raw JSON data from the webhook'
    )
    
    event_data = fields.Text(
        string='Parsed Event Data',
        help='Parsed and formatted event data'
    )
    
    # Call Information (if applicable)
    channel = fields.Char(
        string='Channel',
        help='SIP channel identifier'
    )
    
    caller_id_num = fields.Char(
        string='Caller ID Number',
        help='Caller phone number'
    )
    
    caller_id_name = fields.Char(
        string='Caller ID Name',
        help='Caller display name'
    )
    
    connected_line_num = fields.Char(
        string='Connected Line Number',
        help='Connected party number'
    )
    
    connected_line_name = fields.Char(
        string='Connected Line Name',
        help='Connected party name'
    )
    
    extension = fields.Char(
        string='Extension',
        help='Called extension number'
    )
    
    context = fields.Char(
        string='Context',
        help='SIP context'
    )
    
    unique_id = fields.Char(
        string='Unique ID',
        help='Unique call identifier'
    )
    
    linked_id = fields.Char(
        string='Linked ID',
        help='Linked call identifier'
    )
    
    # Event Status
    event_summary = fields.Char(
        string='Event Summary',
        compute='_compute_event_summary',
        store=True,
        help='Human-readable event summary'
    )
    
    is_call_event = fields.Boolean(
        string='Is Call Event',
        compute='_compute_is_call_event',
        store=True,
        help='Whether this is a call-related event'
    )
    
    # Server Information
    server_hostname = fields.Char(
        string='Server Hostname',
        help='Hostname of the server that sent the event'
    )
    
    server_ami_host = fields.Char(
        string='AMI Host',
        help='Asterisk Manager Interface host'
    )
    
    server_ami_username = fields.Char(
        string='AMI Username',
        help='Asterisk Manager Interface username'
    )
    
    # Statistics
    total_events = fields.Integer(
        string='Total Events',
        help='Total events from this server'
    )
    
    sent_events = fields.Integer(
        string='Sent Events',
        help='Successfully sent events'
    )
    
    failed_events = fields.Integer(
        string='Failed Events',
        help='Failed to send events'
    )
    
    skipped_events = fields.Integer(
        string='Skipped Events',
        help='Skipped events'
    )
    
    # Processing Status
    processed = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Processed')
    ], string='Status', default='draft', help='Processing status of the event')
    
    processing_notes = fields.Text(
        string='Processing Notes',
        help='Notes about event processing'
    )
    
    @api.depends('event_type', 'caller_id_num', 'caller_id_name', 'extension', 'channel')
    def _compute_event_summary(self):
        for record in self:
            if record.event_type == 'Newchannel':
                record.event_summary = f"New call from {record.caller_id_num or 'Unknown'} to {record.extension or 'Unknown'}"
            elif record.event_type == 'Hangup':
                record.event_summary = f"Call ended: {record.channel or 'Unknown channel'}"
            elif record.event_type == 'PeerStatus':
                record.event_summary = f"Peer status change: {record.channel or 'Unknown peer'}"
            else:
                record.event_summary = f"{record.event_type} event"
    
    @api.depends('event_type')
    def _compute_is_call_event(self):
        call_events = ['Newchannel', 'Hangup', 'Dial', 'DialBegin', 'DialEnd', 'Bridge', 'Unbridge']
        for record in self:
            record.is_call_event = record.event_type in call_events
    
    @api.model
    def create_from_webhook(self, event_data, server_id):
        """
        Create a new event record from webhook data
        """
        try:
            # Extract basic information
            event_type = event_data.get('event_type', 'Unknown')
            timestamp_str = event_data.get('timestamp', '')
            
            # Parse timestamp
            timestamp = None
            if timestamp_str:
                try:
                    # Handle different timestamp formats
                    if 'T' in timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()
            
            # Extract event data
            data = event_data.get('data', {})
            server_info = event_data.get('server_info', {})
            statistics = event_data.get('statistics', {})
            
            # Create event record
            event_record = self.create({
                'event_type': event_type,
                'timestamp': timestamp,
                'server_id': server_id,
                'raw_data': json.dumps(event_data, indent=2),
                'event_data': json.dumps(data, indent=2),
                'channel': data.get('Channel'),
                'caller_id_num': data.get('CallerIDNum'),
                'caller_id_name': data.get('CallerIDName'),
                'connected_line_num': data.get('ConnectedLineNum'),
                'connected_line_name': data.get('ConnectedLineName'),
                'extension': data.get('Exten'),
                'context': data.get('Context'),
                'unique_id': data.get('Uniqueid'),
                'linked_id': data.get('Linkedid'),
                'server_hostname': server_info.get('hostname'),
                'server_ami_host': server_info.get('ami_host'),
                'server_ami_username': server_info.get('ami_username'),
                'total_events': statistics.get('total_events', 0),
                'sent_events': statistics.get('sent_events', 0),
                'failed_events': statistics.get('failed_events', 0),
                'skipped_events': statistics.get('skipped_events', 0),
            })
            
            return event_record
            
        except Exception as e:
            # Log error but don't fail the webhook
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Failed to create event record: {str(e)}")
            return None
    
    def action_mark_processed(self):
        """Mark event as processed"""
        self.write({'processed': True})
    
    def action_view_related_events(self):
        """View related events (same call)"""
        domain = []
        if self.unique_id:
            domain.append(('unique_id', '=', self.unique_id))
        elif self.linked_id:
            domain.append(('linked_id', '=', self.linked_id))
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Related Events',
            'res_model': 'voip.event',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'default_server_id': self.server_id.id}
        }










