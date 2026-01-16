/** @odoo-module **/

/**
 * VoIP Hold Music Manager
 * Handles hold music functionality for VoIP calls
 */

export class VoipHoldMusicManager {
    constructor(voipClient) {
        this.voipClient = voipClient;
        this.currentMusicId = null;
        this.volume = 0.7;
        this.isPlaying = false;
        
        this.initHoldMusicControls();
    }

    /**
     * Initialize hold music controls
     */
    initHoldMusicControls() {
        // Create hold music control panel
        this.createHoldMusicPanel();
        
        // Bind events
        this.bindEvents();
    }

    /**
     * Create hold music control panel
     */
    createHoldMusicPanel() {
        const panel = document.createElement('div');
        panel.className = 'hold-music-controls';
        panel.id = 'hold-music-panel';
        panel.style.display = 'none';
        
        panel.innerHTML = `
            <div class="hold-music-indicator" id="hold-music-indicator">
                <i class="fa fa-music icon"></i>
                <span id="hold-music-status">Hold Music: Stopped</span>
            </div>
            
            <div class="hold-music-selector">
                <label for="hold-music-select">Music:</label>
                <select id="hold-music-select">
                    <option value="default">Default</option>
                    <option value="classical">Classical</option>
                    <option value="jazz">Jazz</option>
                    <option value="ambient">Ambient</option>
                    <option value="corporate">Corporate</option>
                </select>
            </div>
            
            <div class="hold-music-volume">
                <label for="hold-music-volume">Volume:</label>
                <input type="range" id="hold-music-volume" min="0" max="1" step="0.1" value="0.7">
                <span id="volume-display">70%</span>
            </div>
            
            <div class="hold-music-actions">
                <button id="start-hold-music" class="btn btn-sm btn-success">
                    <i class="fa fa-play"></i> Start
                </button>
                <button id="stop-hold-music" class="btn btn-sm btn-danger">
                    <i class="fa fa-stop"></i> Stop
                </button>
            </div>
        `;
        
        // Insert panel into VoIP interface
        const voipInterface = document.querySelector('.voip-interface') || document.body;
        voipInterface.appendChild(panel);
    }

    /**
     * Bind events
     */
    bindEvents() {
        // Music selection
        const musicSelect = document.getElementById('hold-music-select');
        if (musicSelect) {
            musicSelect.addEventListener('change', (e) => {
                this.currentMusicId = e.target.value;
            });
        }

        // Volume control
        const volumeSlider = document.getElementById('hold-music-volume');
        if (volumeSlider) {
            volumeSlider.addEventListener('input', (e) => {
                this.volume = parseFloat(e.target.value);
                this.updateVolumeDisplay();
                this.updateHoldMusicVolume();
            });
        }

        // Start/Stop buttons
        const startBtn = document.getElementById('start-hold-music');
        const stopBtn = document.getElementById('stop-hold-music');
        
        if (startBtn) {
            startBtn.addEventListener('click', () => this.startHoldMusic());
        }
        
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopHoldMusic());
        }
    }

    /**
     * Start hold music
     */
    async startHoldMusic() {
        try {
            if (!this.voipClient || !this.voipClient.currentSession) {
                throw new Error('No active call to play hold music');
            }

            const musicId = this.currentMusicId || 'default';
            
            // Start hold music through VoIP client
            await this.voipClient.startHoldMusic(musicId);
            
            this.isPlaying = true;
            this.updateHoldMusicStatus('Playing: ' + musicId);
            this.updateHoldMusicIndicator(true);
            
            console.log('🎵 Hold music started:', musicId);
            
        } catch (error) {
            console.error('❌ Failed to start hold music:', error);
            this.showHoldMusicStatus('Failed to start hold music', 'error');
        }
    }

    /**
     * Stop hold music
     */
    async stopHoldMusic() {
        try {
            if (this.voipClient) {
                await this.voipClient.stopHoldMusic();
            }
            
            this.isPlaying = false;
            this.updateHoldMusicStatus('Stopped');
            this.updateHoldMusicIndicator(false);
            
            console.log('🔇 Hold music stopped');
            
        } catch (error) {
            console.error('❌ Failed to stop hold music:', error);
            this.showHoldMusicStatus('Failed to stop hold music', 'error');
        }
    }

    /**
     * Update hold music status
     */
    updateHoldMusicStatus(status) {
        const statusElement = document.getElementById('hold-music-status');
        if (statusElement) {
            statusElement.textContent = 'Hold Music: ' + status;
        }
    }

    /**
     * Update hold music indicator
     */
    updateHoldMusicIndicator(playing) {
        const indicator = document.getElementById('hold-music-indicator');
        if (indicator) {
            if (playing) {
                indicator.classList.add('playing');
            } else {
                indicator.classList.remove('playing');
            }
        }
    }

    /**
     * Update volume display
     */
    updateVolumeDisplay() {
        const volumeDisplay = document.getElementById('volume-display');
        if (volumeDisplay) {
            volumeDisplay.textContent = Math.round(this.volume * 100) + '%';
        }
    }

    /**
     * Update hold music volume
     */
    updateHoldMusicVolume() {
        if (this.voipClient && this.voipClient.holdMusicAudio) {
            this.voipClient.holdMusicAudio.volume = this.volume;
        }
    }

    /**
     * Show hold music status notification
     */
    showHoldMusicStatus(message, type = 'info') {
        const statusDiv = document.createElement('div');
        statusDiv.className = `hold-music-status show ${type}`;
        statusDiv.textContent = message;
        
        document.body.appendChild(statusDiv);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            if (statusDiv.parentNode) {
                statusDiv.parentNode.removeChild(statusDiv);
            }
        }, 3000);
    }

    /**
     * Show hold music panel
     */
    showPanel() {
        const panel = document.getElementById('hold-music-panel');
        if (panel) {
            panel.style.display = 'flex';
        }
    }

    /**
     * Hide hold music panel
     */
    hidePanel() {
        const panel = document.getElementById('hold-music-panel');
        if (panel) {
            panel.style.display = 'none';
        }
    }

    /**
     * Get available hold music options
     */
    getHoldMusicOptions() {
        return [
            { id: 'default', name: 'Default', description: 'Standard hold music' },
            { id: 'classical', name: 'Classical', description: 'Classical music' },
            { id: 'jazz', name: 'Jazz', description: 'Jazz music' },
            { id: 'ambient', name: 'Ambient', description: 'Ambient music' },
            { id: 'corporate', name: 'Corporate', description: 'Corporate music' }
        ];
    }

    /**
     * Check if hold music is playing
     */
    isHoldMusicPlaying() {
        return this.isPlaying;
    }

    /**
     * Get current hold music ID
     */
    getCurrentMusicId() {
        return this.currentMusicId;
    }

    /**
     * Get current volume
     */
    getCurrentVolume() {
        return this.volume;
    }
}






