# -*- coding: utf-8 -*-
#################################################################################
#
# Module Name: VoIP Logging Utilities
# Description: Utility functions for conditional logging based on server mode
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

import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class VoipLoggingUtils:
    """Utility class for conditional logging based on server mode"""
    
    @staticmethod
    def get_server_logging_mode(env, server_id=None):
        """
        Get the logging mode for a VoIP server
        
        Args:
            env: Odoo environment
            server_id: Server ID to check, if None gets the first active server
            
        Returns:
            str: 'production' or 'test'
        """
        try:
            if server_id:
                # Ensure server_id is an integer to prevent SQL injection and query errors
                try:
                    if not isinstance(server_id, int):
                        server_id = int(server_id)
                except (ValueError, TypeError):
                    _logger.warning(f"Invalid server_id type, expected integer but got: {type(server_id).__name__} - {server_id}")
                    return 'production'
                
                server = env['voip.server'].browse(server_id)
            else:
                # Get the first active server
                server = env['voip.server'].search([('active', '=', True)], limit=1)
            
            if server and server.exists():
                return server.logging_mode
            else:
                # Default to production if no server found
                return 'production'
        except Exception as e:
            _logger.warning(f"Error getting server logging mode: {e}")
            return 'production'
    
    @staticmethod
    def should_log(env, server_id=None, level='info'):
        """
        Check if logging should be enabled based on server mode
        
        Args:
            env: Odoo environment
            server_id: Server ID to check
            level: Log level ('debug', 'info', 'warning', 'error')
            
        Returns:
            bool: True if logging should be enabled, False otherwise
        """
        logging_mode = VoipLoggingUtils.get_server_logging_mode(env, server_id)
        
        # In test mode, disable all logging
        if logging_mode == 'test':
            return False
        
        # In production mode, enable all logging
        return True
    
    @staticmethod
    def log_if_enabled(env, logger, level, message, *args, server_id=None, **kwargs):
        """
        Log a message only if logging is enabled for the server
        
        Args:
            env: Odoo environment
            logger: Logger instance
            level: Log level ('debug', 'info', 'warning', 'error')
            message: Log message
            *args: Additional arguments for logging
            server_id: Server ID to check (keyword-only argument)
            **kwargs: Additional keyword arguments for logging
        """
        if VoipLoggingUtils.should_log(env, server_id, level):
            getattr(logger, level)(message, *args, **kwargs)
    
    @staticmethod
    def get_js_logging_config(env, server_id=None):
        """
        Get JavaScript logging configuration
        
        Args:
            env: Odoo environment
            server_id: Server ID to check
            
        Returns:
            dict: Configuration for JavaScript logging
        """
        logging_mode = VoipLoggingUtils.get_server_logging_mode(env, server_id)
        
        return {
            'enabled': logging_mode == 'production',
            'mode': logging_mode,
            'levels': {
                'debug': logging_mode == 'production',
                'info': logging_mode == 'production',
                'warn': logging_mode == 'production',
                'error': logging_mode == 'production'
            }
        }
