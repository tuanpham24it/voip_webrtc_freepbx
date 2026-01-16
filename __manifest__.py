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

{
    'name': 'VoIP WebRTC FreePBX',
    'version': '18.0.1.0.1',
    'category': 'Productivity/VoIP',
    'summary': 'VoIP and WebRTC integration with FreePBX server for call management',
    'description': """
        VoIP WebRTC FreePBX Integration
        ================================
        
        This module provides full VoIP functionality with WebRTC integration:
        
        * Connect to FreePBX server via SIP/WebRTC
        * Make and receive calls directly from Odoo
        * Call recording and playback
        * Call history and analytics
        * Share call recordings with other users
        * Multi-language support (Arabic and English)
        * Clean architecture and code
        
        Technical Features:
        -------------------
        * WebRTC-based calling using open source libraries
        * SIP.js integration for SIP protocol
        * Real-time call status updates
        * Audio recording and storage
        * Call logs and reporting
    """,
    'author': 'Mohamed Samir',
    'maintainer': 'odoo-vip.com',
    'website': 'https://odoo-vip.com',
    'license': 'OPL-1',
    'depends': [
        'base',
        'web',
        'mail',
        'contacts',
    ],
    'data': [
        'security/voip_security.xml',
        'security/ir.model.access.csv',
        'wizards/voip_show_api_key_wizard_views.xml',
        'views/voip_server_views.xml',
        'views/voip_user_views.xml',
        'views/voip_call_views.xml',
        'views/voip_recording_views.xml',
        'views/voip_menus.xml',
        'views/voip_event_views.xml',
        'views/voip_hold_music_views.xml',
        'data/voip_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'voip_webrtc_freepbx/static/src/js/sip.min.js',
            'voip_webrtc_freepbx/static/src/js/sip_init.js',
            'voip_webrtc_freepbx/static/src/js/voip_clipboard.js',
            'voip_webrtc_freepbx/static/src/js/voip_logging.js',
            'voip_webrtc_freepbx/static/src/js/voip_sip_client.js',
            'voip_webrtc_freepbx/static/src/js/voip_service.js',
            'voip_webrtc_freepbx/static/src/js/voip_systray.js',
            'voip_webrtc_freepbx/static/src/js/audio_player.js',
            'voip_webrtc_freepbx/static/src/xml/voip_templates.xml',
            'voip_webrtc_freepbx/static/src/xml/audio_player.xml',
            'voip_webrtc_freepbx/static/src/css/voip_style.css',
            'voip_webrtc_freepbx/static/src/css/audio_player.scss',
            'voip_webrtc_freepbx/static/src/css/hold_music_styles.css',
        ],
    },
    'external_dependencies': {
        'python': [],
    },
    'images': [
        'static/description/cover.png',
    ],
    "pre_init_hook": "pre_init_check",
    'installable': True,
    'application': True,
    'auto_install': False,
    'price': 250.00,
    'currency': 'USD',
}
