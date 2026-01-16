# -*- coding: utf-8 -*-
"""
Debug controller for VoIP system
"""

from odoo import http, fields
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class VoipDebugController(http.Controller):
    
    @http.route('/voip/debug/test', type='json', auth='user', csrf=False)
    def debug_test(self, **kwargs):
        """Simple debug test"""
        try:
            _logger.info("🔧 Debug Test: Starting")
            
            # Test basic functionality
            user = request.env.user
            _logger.info(f"🔧 Debug Test: User: {user.name} (ID: {user.id})")
            
            # Test database connection
            try:
                voip_users = request.env['voip.user'].search([])
                _logger.info(f"🔧 Debug Test: Found {len(voip_users)} VoIP users")
            except Exception as e:
                _logger.error(f"🔧 Debug Test: Database error: {e}")
                return {'error': f'Database error: {e}'}
            
            # Test current user VoIP config
            try:
                voip_user = request.env['voip.user'].search([
                    ('user_id', '=', user.id),
                    ('active', '=', True)
                ], limit=1)
                
                if voip_user:
                    _logger.info(f"🔧 Debug Test: User has VoIP config: {voip_user.name}")
                    return {
                        'success': True,
                        'message': 'VoIP system is working',
                        'user': {
                            'name': user.name,
                            'id': user.id
                        },
                        'voip_user': {
                            'name': voip_user.name,
                            'server': voip_user.server_id.name if voip_user.server_id else None,
                            'sip_username': voip_user.sip_username
                        }
                    }
                else:
                    _logger.warning("🔧 Debug Test: No VoIP user found")
                    return {
                        'success': False,
                        'error': 'No VoIP user configuration found',
                        'user': {
                            'name': user.name,
                            'id': user.id
                        }
                    }
                    
            except Exception as e:
                _logger.error(f"🔧 Debug Test: VoIP user check error: {e}")
                return {'error': f'VoIP user check error: {e}'}
                
        except Exception as e:
            _logger.error(f"🔧 Debug Test: General error: {e}")
            return {'error': f'General error: {e}'}
    
    @http.route('/voip/debug/models', type='json', auth='user', csrf=False)
    def debug_models(self, **kwargs):
        """Debug model availability"""
        try:
            models_info = {}
            
            # Test voip.user model
            try:
                voip_users = request.env['voip.user'].search([])
                models_info['voip.user'] = {
                    'exists': True,
                    'count': len(voip_users),
                    'error': None
                }
            except Exception as e:
                models_info['voip.user'] = {
                    'exists': False,
                    'count': 0,
                    'error': str(e)
                }
            
            # Test voip.server model
            try:
                voip_servers = request.env['voip.server'].search([])
                models_info['voip.server'] = {
                    'exists': True,
                    'count': len(voip_servers),
                    'error': None
                }
            except Exception as e:
                models_info['voip.server'] = {
                    'exists': False,
                    'count': 0,
                    'error': str(e)
                }
            
            # Test voip.call model
            try:
                voip_calls = request.env['voip.call'].search([])
                models_info['voip.call'] = {
                    'exists': True,
                    'count': len(voip_calls),
                    'error': None
                }
            except Exception as e:
                models_info['voip.call'] = {
                    'exists': False,
                    'count': 0,
                    'error': str(e)
                }
            
            return {
                'success': True,
                'models': models_info
            }
            
        except Exception as e:
            return {'error': f'Models debug error: {e}'}




