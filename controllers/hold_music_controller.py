# -*- coding: utf-8 -*-
#################################################################################
#
# Module Name: Voip Webrtc Freepbx - Hold Music Controller
# Description: Controller for managing hold music functionality
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
from odoo import http
from odoo.http import request, Response
import json
import base64
import time
import logging
from .base_controller import VoipBaseController

_logger = logging.getLogger(__name__)


class VoipHoldMusicController(VoipBaseController):
    """Controller for managing hold music functionality"""

    @http.route('/voip/hold-music/list', type='json', auth='user', methods=['POST'], csrf=False)
    def get_hold_music_list_legacy(self, **kwargs):
        """Get list of available hold music files (legacy endpoint)"""
        return self.get_hold_music_list(server_id=kwargs.get('server_id'))

    @http.route('/voip/hold_music/list', type='json', auth='user', csrf=False)
    def get_hold_music_list(self, server_id=None, **kwargs):
        """Get list of available hold music"""
        try:
            # Try to get existing music first
            music_list = []
            try:
                music_list = request.env['voip.hold.music'].get_available_music(server_id)
            except Exception as e:
                _logger.warning(f"Error getting existing music: {e}")
                music_list = []
            
            # If no music found, create default music only if no uploaded files exist
            if not music_list:
                # Check if there are any uploaded music files (even if corrupted)
                uploaded_music = request.env['voip.hold.music'].search([
                    ('music_file', '!=', False),
                    ('active', '=', True)
                ])
                
                if not uploaded_music:
                    _logger.info("No hold music found, creating default music...")
                    try:
                        default_music = self.create_default_hold_music()
                        if default_music:
                            music_list = [default_music]
                    except Exception as e:
                        _logger.error(f"Error creating default music: {e}")
                        music_list = []
                else:
                    _logger.info("Found uploaded music files, not creating default music")
            else:
                # Check if existing music files are corrupted and fix them
                _logger.info("Checking for corrupted music files...")
                try:
                    self.fix_corrupted_music_files()
                except Exception as e:
                    _logger.warning(f"Error fixing corrupted music: {e}")
            
            return {
                'success': True,
                'music_list': music_list,
                'total': len(music_list)
            }
        except Exception as e:
            _logger.exception("Error getting hold music list: %s", str(e))
            return {'success': False, 'error': str(e)}

    @http.route('/voip_webrtc_freepbx/hold_music/file/<int:music_id>', type='http', auth='user', methods=['GET'])
    @http.route('/voip/hold_music/file/<int:music_id>', type='http', auth='user', methods=['GET'])
    def get_hold_music_file(self, music_id):
        """Serve hold music file"""
        try:
            music = request.env['voip.hold.music'].browse(music_id)
            
            if not music.exists():
                return Response('Music not found', status=404)
            
            if not music.music_file:
                return Response('No music file', status=404)
            
            # Increment usage count
            music.action_increment_usage()
            
            # Determine content type
            content_type = 'audio/mpeg'
            if music.format == 'wav':
                content_type = 'audio/wav'
            elif music.format == 'ogg':
                content_type = 'audio/ogg'
            elif music.format == 'm4a':
                content_type = 'audio/mp4'
            
            # Decode the binary data
            import base64
            try:
                music_data = base64.b64decode(music.music_file)
            except Exception as e:
                _logger.error(f"Error decoding music file: {e}")
                return Response('Invalid music file', status=500)
            
            return Response(
                music_data,
                content_type=content_type,
                headers=[
                    ('Content-Disposition', f'inline; filename="{music.music_filename or music.name}"'),
                    ('Cache-Control', 'public, max-age=3600'),
                    ('Content-Length', str(len(music_data))),
                ]
            )
            
        except Exception as e:
            _logger.exception("Error serving hold music file: %s", str(e))
            return Response('Error serving music file', status=500)

    @http.route('/voip_webrtc_freepbx/hold_music/test/<int:music_id>', type='http', auth='user', methods=['GET'])
    @http.route('/voip/hold_music/test/<int:music_id>', type='http', auth='user', methods=['GET'])
    def test_hold_music(self, music_id):
        """Test hold music with a simple player"""
        try:
            music = request.env['voip.hold.music'].browse(music_id)
            
            if not music.exists():
                return Response('Music not found', status=404)
            
            if not music.music_file:
                return Response('No music file available', status=404)
            
            # Get music URL
            music_url = f'/voip_webrtc_freepbx/hold_music/file/{music_id}'
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Test Hold Music - {music.name}</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        margin: 0;
                        padding: 20px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                    }}
                    .test-container {{
                        background: white;
                        border-radius: 15px;
                        padding: 40px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                        text-align: center;
                        max-width: 500px;
                        width: 100%;
                    }}
                    .music-icon {{
                        font-size: 64px;
                        color: #667eea;
                        margin-bottom: 20px;
                    }}
                    h1 {{
                        color: #333;
                        margin-bottom: 10px;
                    }}
                    .music-info {{
                        color: #666;
                        margin-bottom: 30px;
                        font-size: 16px;
                    }}
                    .audio-player {{
                        width: 100%;
                        margin: 20px 0;
                        border-radius: 10px;
                        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    }}
                    .controls {{
                        margin-top: 20px;
                    }}
                    .btn {{
                        background: #667eea;
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 25px;
                        cursor: pointer;
                        font-size: 16px;
                        margin: 0 10px;
                        transition: all 0.3s ease;
                    }}
                    .btn:hover {{
                        background: #5a6fd8;
                        transform: translateY(-2px);
                    }}
                    .status {{
                        margin-top: 20px;
                        padding: 15px;
                        border-radius: 10px;
                        background: #f8f9fa;
                        border-left: 4px solid #667eea;
                    }}
                    .volume-control {{
                        margin: 20px 0;
                        text-align: left;
                    }}
                    .volume-control label {{
                        display: block;
                        margin-bottom: 10px;
                        font-weight: bold;
                        color: #333;
                    }}
                    .volume-slider {{
                        width: 100%;
                        height: 8px;
                        border-radius: 5px;
                        background: #ddd;
                        outline: none;
                        -webkit-appearance: none;
                    }}
                    .volume-slider::-webkit-slider-thumb {{
                        -webkit-appearance: none;
                        appearance: none;
                        width: 20px;
                        height: 20px;
                        border-radius: 50%;
                        background: #667eea;
                        cursor: pointer;
                    }}
                </style>
            </head>
            <body>
                <div class="test-container">
                    <div class="music-icon">🎵</div>
                    <h1>Test Hold Music</h1>
                    <div class="music-info">
                        <strong>{music.name}</strong><br>
                        Format: {music.format.upper()}<br>
                        Size: {music.file_size or 'Unknown'} bytes<br>
                        Quality: {music.quality or 'Unknown'}
                    </div>
                    
                    <audio id="musicPlayer" class="audio-player" controls preload="auto">
                        <source src="{music_url}" type="audio/{music.format}">
                        Your browser does not support the audio element.
                    </audio>
                    
                    <div class="volume-control">
                        <label for="volumeSlider">Volume: <span id="volumeValue">70</span>%</label>
                        <input type="range" id="volumeSlider" class="volume-slider" 
                               min="0" max="100" value="70" step="1">
                    </div>
                    
                    <div class="controls">
                        <button class="btn" onclick="playMusic()">▶️ Play</button>
                        <button class="btn" onclick="pauseMusic()">⏸️ Pause</button>
                        <button class="btn" onclick="stopMusic()">⏹️ Stop</button>
                        <button class="btn" onclick="testLoop()">🔄 Test Loop</button>
                    </div>
                    
                    <div class="status" id="status">
                        Ready to test music. Click Play to start.
                    </div>
                </div>
                
                <script>
                    const audio = document.getElementById('musicPlayer');
                    const volumeSlider = document.getElementById('volumeSlider');
                    const volumeValue = document.getElementById('volumeValue');
                    const status = document.getElementById('status');
                    
                    // Set initial volume
                    audio.volume = 0.7;
                    
                    // Volume control
                    volumeSlider.addEventListener('input', function() {{
                        const volume = this.value / 100;
                        audio.volume = volume;
                        volumeValue.textContent = this.value;
                    }});
                    
                    // Audio event listeners
                    audio.addEventListener('loadstart', () => {{
                        status.innerHTML = '🔄 Loading music file...';
                    }});
                    
                    audio.addEventListener('canplay', () => {{
                        status.innerHTML = '✅ Music loaded successfully! Ready to play.';
                    }});
                    
                    audio.addEventListener('play', () => {{
                        status.innerHTML = '▶️ Playing: ' + audio.currentSrc;
                    }});
                    
                    audio.addEventListener('pause', () => {{
                        status.innerHTML = '⏸️ Music paused';
                    }});
                    
                    audio.addEventListener('ended', () => {{
                        status.innerHTML = '🏁 Music finished playing';
                    }});
                    
                    audio.addEventListener('error', (e) => {{
                        status.innerHTML = '❌ Error loading music: ' + e.message;
                        console.error('Audio error:', e);
                    }});
                    
                    // Control functions
                    function playMusic() {{
                        audio.play().catch(e => {{
                            status.innerHTML = '❌ Error playing music: ' + e.message;
                        }});
                    }}
                    
                    function pauseMusic() {{
                        audio.pause();
                    }}
                    
                    function stopMusic() {{
                        audio.pause();
                        audio.currentTime = 0;
                    }}
                    
                    function testLoop() {{
                        audio.loop = !audio.loop;
                        status.innerHTML = audio.loop ? '🔄 Loop enabled' : '🔄 Loop disabled';
                    }}
                    
                    // Auto-play when loaded (if user interaction allows)
                    audio.addEventListener('canplay', () => {{
                        // Only auto-play if user has interacted with the page
                        if (document.hasFocus()) {{
                            audio.play().catch(() => {{
                                // Auto-play blocked, that's okay
                            }});
                        }}
                    }});
                </script>
            </body>
            </html>
            """
            
            return Response(html, content_type='text/html')
            
        except Exception as e:
            _logger.exception("Error in test_hold_music: %s", str(e))
            return Response('Error loading test page', status=500)

    @http.route('/voip_webrtc_freepbx/hold_music/preview/<int:music_id>', type='http', auth='user', methods=['GET'])
    def preview_hold_music(self, music_id):
        """Preview hold music in a new window"""
        try:
            music = request.env['voip.hold.music'].browse(music_id)
            
            if not music.exists():
                return Response('Music not found', status=404)
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Hold Music Preview - {music.name}</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background: #f5f5f5;
                        margin: 0;
                        padding: 20px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                    }}
                    .preview-container {{
                        background: white;
                        border-radius: 10px;
                        padding: 30px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                        text-align: center;
                        max-width: 400px;
                    }}
                    .music-icon {{
                        font-size: 48px;
                        color: #9b8bb3;
                        margin-bottom: 20px;
                    }}
                    .music-name {{
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 10px;
                        color: #333;
                    }}
                    .music-description {{
                        color: #666;
                        margin-bottom: 20px;
                    }}
                    audio {{
                        width: 100%;
                        margin: 20px 0;
                    }}
                    .controls {{
                        margin-top: 20px;
                    }}
                    .btn {{
                        background: #9b8bb3;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 5px;
                        cursor: pointer;
                        margin: 0 5px;
                    }}
                    .btn:hover {{
                        background: #8a7ba3;
                    }}
                </style>
            </head>
            <body>
                <div class="preview-container">
                    <div class="music-icon">🎵</div>
                    <div class="music-name">{music.name}</div>
                    <div class="music-description">{music.description or 'No description'}</div>
                    
                    <audio controls>
                        <source src="/voip_webrtc_freepbx/hold_music/file/{music_id}" type="audio/{music.format}">
                        Your browser does not support the audio element.
                    </audio>
                    
                    <div class="controls">
                        <button class="btn" onclick="window.close()">Close</button>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return Response(html, content_type='text/html')
            
        except Exception as e:
            _logger.exception("Error previewing hold music: %s", str(e))
            return Response('Error loading preview', status=500)

    def create_default_hold_music(self):
        """Create default hold music if none exists"""
        try:
            # Check if default music already exists
            existing_music = request.env['voip.hold.music'].search([
                ('name', '=', 'Default Hold Music'),
                ('active', '=', True)
            ], limit=1)
            
            if existing_music:
                return existing_music.get_music_config()
            
            # Create default music record
            default_server = request.env['voip.server'].search([('active', '=', True)], limit=1)
            if not default_server:
                return None
            
            # Create a proper WAV file for default music
            import base64
            import io
            import wave
            import math
            
            # Create a pleasant melody
            sample_rate = 44100
            duration = 30  # 30 seconds
            buffer = io.BytesIO()
            
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                
                # Create a pleasant melody
                melody_notes = [
                    (440, 2),    # A4
                    (523.25, 2), # C5
                    (659.25, 2), # E5
                    (783.99, 2), # G5
                    (659.25, 2), # E5
                    (523.25, 2), # C5
                    (440, 2),    # A4
                    (392, 2),    # G4
                ]
                
                total_samples = int(sample_rate * duration)
                samples = []
                sample_index = 0
                
                for note_freq, note_duration in melody_notes:
                    note_samples = int(sample_rate * note_duration)
                    end_index = min(sample_index + note_samples, total_samples)
                    
                    for i in range(sample_index, end_index):
                        time = i / sample_rate
                        # Create a pleasant tone with harmonics
                        sample = (math.sin(2 * math.pi * note_freq * time) * 0.1 +
                                 math.sin(2 * math.pi * note_freq * 2 * time) * 0.05 +
                                 math.sin(2 * math.pi * note_freq * 3 * time) * 0.02)
                        
                        # Add some vibrato
                        vibrato = math.sin(2 * math.pi * 5 * time) * 0.01
                        sample *= (1 + vibrato)
                        
                        # Convert to 16-bit PCM (little-endian)
                        pcm_sample = int(max(-32768, min(32767, sample * 32767)))
                        # Convert to bytes (little-endian)
                        samples.append(pcm_sample & 0xFF)  # Low byte
                        samples.append((pcm_sample >> 8) & 0xFF)  # High byte
                    
                    sample_index = end_index
                    
                    # If we've filled the duration, break
                    if sample_index >= total_samples:
                        break
                
                # Write the samples
                wav_file.writeframes(bytes(samples))
            
            wav_data = buffer.getvalue()
            wav_base64 = base64.b64encode(wav_data).decode('utf-8')
            
            # Create hold music record
            music_record = request.env['voip.hold.music'].create({
                'name': 'Default Hold Music',
                'description': 'Generated default hold music',
                'server_id': default_server.id,
                'music_file': wav_base64,
                'music_filename': 'default_hold_music.wav',
                'format': 'wav',
                'volume': 0.7,
                'loop': True,
                'active': True,
                'is_default': True,
                'sequence': 1
            })
            
            return music_record.get_music_config()
            
        except Exception as e:
            _logger.exception("Error creating default hold music: %s", str(e))
            return None

    def fix_corrupted_music_files(self):
        """Fix corrupted music files by regenerating them"""
        try:
            # Find music files with corrupted data
            corrupted_music = request.env['voip.hold.music'].search([
                ('active', '=', True),
                ('music_file', '!=', False)
            ])
            
            for music in corrupted_music:
                try:
                    # Check if record still exists
                    if not music.exists():
                        _logger.warning(f"Music record {music.id} no longer exists, skipping...")
                        continue
                    
                    # Try to decode the base64 data
                    import base64
                    music_data = base64.b64decode(music.music_file)
                    
                    # Check if it's a valid WAV file
                    if not music_data.startswith(b'RIFF') or not b'WAVE' in music_data[:12]:
                        _logger.info(f"Regenerating corrupted music file: {music.name}")
                        self.regenerate_music_file(music)
                        
                except Exception as e:
                    _logger.warning(f"Music file {music.name} is corrupted, regenerating...")
                    try:
                        self.regenerate_music_file(music)
                    except Exception as regen_error:
                        _logger.error(f"Failed to regenerate music file {music.name}: {regen_error}")
                    
        except Exception as e:
            _logger.exception("Error fixing corrupted music files: %s", str(e))

    def regenerate_music_file(self, music_record):
        """Regenerate a music file"""
        try:
            import base64
            import io
            import wave
            import math
            
            # Create a pleasant melody
            sample_rate = 44100
            duration = 30  # 30 seconds
            buffer = io.BytesIO()
            
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                
                # Create a pleasant melody
                melody_notes = [
                    (440, 2),    # A4
                    (523.25, 2), # C5
                    (659.25, 2), # E5
                    (783.99, 2), # G5
                    (659.25, 2), # E5
                    (523.25, 2), # C5
                    (440, 2),    # A4
                    (392, 2),    # G4
                ]
                
                total_samples = int(sample_rate * duration)
                samples = []
                sample_index = 0
                
                for note_freq, note_duration in melody_notes:
                    note_samples = int(sample_rate * note_duration)
                    end_index = min(sample_index + note_samples, total_samples)
                    
                    for i in range(sample_index, end_index):
                        time = i / sample_rate
                        # Create a pleasant tone with harmonics
                        sample = (math.sin(2 * math.pi * note_freq * time) * 0.1 +
                                 math.sin(2 * math.pi * note_freq * 2 * time) * 0.05 +
                                 math.sin(2 * math.pi * note_freq * 3 * time) * 0.02)
                        
                        # Add some vibrato
                        vibrato = math.sin(2 * math.pi * 5 * time) * 0.01
                        sample *= (1 + vibrato)
                        
                        # Convert to 16-bit PCM (little-endian)
                        pcm_sample = int(max(-32768, min(32767, sample * 32767)))
                        # Convert to bytes (little-endian)
                        samples.append(pcm_sample & 0xFF)  # Low byte
                        samples.append((pcm_sample >> 8) & 0xFF)  # High byte
                    
                    sample_index = end_index
                    
                    # If we've filled the duration, break
                    if sample_index >= total_samples:
                        break
                
                # Write the samples
                wav_file.writeframes(bytes(samples))
            
            wav_data = buffer.getvalue()
            wav_base64 = base64.b64encode(wav_data).decode('utf-8')
            
            # Update the music record
            music_record.write({
                'music_file': wav_base64,
                'music_filename': f'{music_record.name.lower().replace(" ", "_")}.wav',
                'format': 'wav',
                'file_size': len(wav_data)
            })
            
            _logger.info(f"Regenerated music file: {music_record.name}")
            
        except Exception as e:
            _logger.exception(f"Error regenerating music file {music_record.name}: %s", str(e))

    @http.route('/voip/hold_music/upload_large', type='http', auth='user', methods=['POST'], csrf=False)
    def upload_large_music_file(self, **kwargs):
        """Handle large music file uploads"""
        try:
            _logger.info("🎵 [DEBUG] Large music file upload started")
            
            # Get uploaded file
            music_file = request.httprequest.files.get('music_file')
            if not music_file:
                return Response('No file uploaded', status=400)
            
            # Get other parameters
            music_id = request.httprequest.form.get('music_id')
            name = request.httprequest.form.get('name', 'Large Music File')
            format_type = request.httprequest.form.get('format', 'wav')
            volume = float(request.httprequest.form.get('volume', 0.7))
            loop = request.httprequest.form.get('loop', 'true').lower() == 'true'
            
            _logger.info(f"🎵 [DEBUG] Uploading file: {music_file.filename}")
            _logger.info(f"🎵 [DEBUG] File size: {len(music_file.read())} bytes")
            _logger.info(f"🎵 [DEBUG] Music ID: {music_id}")
            
            # Reset file pointer
            music_file.seek(0)
            
            # Read file data
            file_data = music_file.read()
            file_size = len(file_data)
            
            # Convert to base64
            import base64
            file_base64 = base64.b64encode(file_data).decode('utf-8')
            
            # Update or create music record
            if music_id:
                music_record = request.env['voip.hold.music'].browse(int(music_id))
                if music_record.exists():
                    music_record.write({
                        'music_file': file_base64,
                        'music_filename': music_file.filename,
                        'format': format_type,
                        'file_size': file_size,
                        'volume': volume,
                        'loop': loop,
                    })
                    _logger.info(f"🎵 [DEBUG] Updated music record: {music_record.id}")
                else:
                    return Response('Music record not found', status=404)
            else:
                # Create new record
                default_server = request.env['voip.server'].search([('active', '=', True)], limit=1)
                if not default_server:
                    return Response('No active server found', status=400)
                
                music_record = request.env['voip.hold.music'].create({
                    'name': name,
                    'music_file': file_base64,
                    'music_filename': music_file.filename,
                    'format': format_type,
                    'file_size': file_size,
                    'volume': volume,
                    'loop': loop,
                    'server_id': default_server.id,
                    'active': True,
                })
                _logger.info(f"🎵 [DEBUG] Created new music record: {music_record.id}")
            
            return Response('File uploaded successfully', status=200)
            
        except Exception as e:
            _logger.exception("Error uploading large music file: %s", str(e))
            return Response(f'Error uploading file: {str(e)}', status=500)

    @http.route('/voip/hold_music/cleanup', type='json', auth='user', csrf=False)
    def cleanup_corrupted_music(self, **kwargs):
        """Clean up corrupted music files"""
        try:
            _logger.info("Starting music files cleanup...")
            
            # Delete all existing music files
            existing_music = request.env['voip.hold.music'].search([])
            for music in existing_music:
                music.unlink()
            
            _logger.info("Deleted all existing music files")
            
            # Create fresh default music
            default_music = self.create_default_hold_music()
            
            return {
                'success': True,
                'message': 'Music files cleaned up and regenerated',
                'default_music': default_music
            }
        except Exception as e:
            _logger.exception("Error cleaning up music files: %s", str(e))
            return {'success': False, 'error': str(e)}

    @http.route('/voip/hold_music/default', type='json', auth='user', csrf=False)
    def get_default_hold_music(self, server_id=None, **kwargs):
        """Get default hold music"""
        try:
            default_music = request.env['voip.hold.music'].get_default_music(server_id)
            
            return {
                'success': True,
                'default_music': default_music
            }
        except Exception as e:
            _logger.exception("Error getting default hold music: %s", str(e))
            return {'success': False, 'error': str(e)}
