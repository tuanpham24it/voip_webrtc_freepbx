/** @odoo-module **/

import { voipLogger } from "./voip_logging";
import { loadSipLibrary } from "./sip_init";

/**
 * VoIP SIP Client using SIP.js
 * 
 * Based on Browser-Phone project by InnovateAsterisk
 * https://github.com/InnovateAsterisk/Browser-Phone
 * 
 * This implementation uses SIP.js 0.20.0 for WebRTC calls
 * 
 * REQUIREMENTS:
 * - HTTPS connection (required for getUserMedia)
 * - Modern browser with WebRTC support
 * - User microphone permissions
 * - Valid FreePBX/Asterisk server with WebSocket support
 */

export class VoipSipClient {
    constructor(config, voipService) {
        this.config = config;
        this.voipService = voipService;
        this.userAgent = null;
        this.currentSession = null;
        this.isRegistered = false;
        this.remoteAudio = null;
        this.localStream = null;
        this.mediaRecorder = null;
        this.recordedChunks = [];
        
        // Audio feedback elements
        this.ringbackTone = null;
        this.busyTone = null;
        this.ringTone = null;
        
        // Hold music elements (enhanced based on Browser-Phone)
        this.holdMusicAudio = null;
        this.holdMusicAudioContext = null;
        this.holdMusicOscillator1 = null;
        this.holdMusicOscillator2 = null;
        this.holdMusicGainNode = null;
        this.isCallHeld = false;
        
        // Enhanced audio management (Browser-Phone style)
        this.audioContext = null;
        this.audioDestination = null;
        this.audioSources = new Map();
        
        // Call state management (inspired by Browser-Phone)
        this.callState = 'idle'; // idle, ringing, connected, held, ended
        this.callStartTime = null;
        this.callDuration = 0;
        
        // Error handling and retry logic (Browser-Phone approach)
        this.retryCount = 0;
        this.maxRetries = 3;
        this.retryDelay = 1000;
        
        // SIP Call ID storage
        this.sipCallId = null;
        
        // SIP.js will be checked in initialize() method
        // to allow for async loading in Odoo 18
        
        this.initAudioElements();
        this.initCallTones();
        this.initCallStateManagement();
    }
    
    /**
     * Initialize call state management (Browser-Phone style)
     */
    initCallStateManagement() {
        // Initialize call state tracking
        this.callState = 'idle';
        this.callStartTime = null;
        this.callDuration = 0;
        
        // Initialize duration tracking interval
        this.durationInterval = null;
        
    }
    
    /**
     * Update call state (Browser-Phone approach)
     */
    updateCallState(newState) {
        const oldState = this.callState;
        this.callState = newState;
        
        
        // Handle state-specific actions
        switch (newState) {
            case 'ringing':
                this.callStartTime = new Date();
                break;
            case 'connected':
                this.startCallDurationTracking();
                break;
            case 'ended':
            case 'idle':
                this.stopCallDurationTracking();
                break;
        }
    }
    
    /**
     * Start call duration tracking (Browser-Phone style)
     */
    startCallDurationTracking() {
        if (this.durationInterval) {
            clearInterval(this.durationInterval);
        }
        
        this.durationInterval = setInterval(() => {
            if (this.callStartTime) {
                this.callDuration = Math.floor((new Date() - this.callStartTime) / 1000);
                this.onCallDurationUpdate(this.callDuration);
            }
        }, 1000);
    }
    
    /**
     * Stop call duration tracking
     */
    stopCallDurationTracking() {
        if (this.durationInterval) {
            clearInterval(this.durationInterval);
            this.durationInterval = null;
        }
    }
    
    /**
     * Handle call duration updates
     */
    onCallDurationUpdate(duration) {
        // This can be overridden by the parent application
    }
    
    /**
     * Enhanced error handling (Browser-Phone style)
     */
    handleError(error, context = 'unknown') {
        
        // Reset call state on critical errors
        if (this.isCriticalError(error)) {
            this.updateCallState('idle');
            this.cleanup();
        }
        
        // Retry logic for recoverable errors
        if (this.isRetryableError(error)) {
            this.scheduleRetry(context);
        }
    }
    
    /**
     * Check if error is critical
     */
    isCriticalError(error) {
        const criticalErrors = [
            'Not registered',
            'Invalid configuration',
            'WebRTC not supported',
            'Microphone access denied'
        ];
        
        return criticalErrors.some(criticalError => 
            error.message && error.message.includes(criticalError)
        );
    }
    
    /**
     * Check if error is retryable
     */
    isRetryableError(error) {
        const retryableErrors = [
            'Network error',
            'Connection timeout',
            'ICE gathering failed',
            'Server unavailable'
        ];
        
        return retryableErrors.some(retryableError => 
            error.message && error.message.includes(retryableError)
        );
    }
    
    /**
     * Schedule retry for recoverable errors
     */
    scheduleRetry(context) {
        if (this.retryCount < this.maxRetries) {
            this.retryCount++;
            const delay = this.retryDelay * Math.pow(2, this.retryCount - 1); // Exponential backoff
            
            setTimeout(() => {
                this.retry(context);
            }, delay);
        } else {
            this.retryCount = 0;
        }
    }
    
    /**
     * Retry operation
     */
    async retry(context) {
        try {
            switch (context) {
                case 'registration':
                    await this.register();
                    break;
                case 'call':
                    // Retry call logic would go here
                    break;
                default:
                    // No retry logic for context
            }
        } catch (error) {
            this.handleError(error, context);
        }
    }
    
    /**
     * Cleanup resources (Browser-Phone style)
     */
    cleanup() {
        // Stop all audio
        this.stopAllTones();
        this.stopHoldMusic();
        
        // Clear intervals
        this.stopCallDurationTracking();
        
        // Reset state
        this.callState = 'idle';
        this.callStartTime = null;
        this.callDuration = 0;
        
        // Reset retry count
        this.retryCount = 0;
        
    }
    
    /**
     * Clean up corrupted music files (Browser-Phone style)
     */
    async cleanupCorruptedMusic() {
        try {
            const response = await fetch('/voip/hold_music/cleanup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            });
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.success) {
                    return true;
                } else {
                    return false;
                }
            } else {
                return false;
            }
            
        } catch (error) {
            return false;
        }
    }
    
    /**
     * Inject hold music stream directly (Browser-Phone style)
     */
    async injectHoldMusicStream() {
        try {
            
            
            if (!this.currentSession) {
                
                return;
            }
            
            if (!this.holdMusicStream) {
                
                return;
            }
            
            const sessionDescriptionHandler = this.currentSession.sessionDescriptionHandler;
            if (!sessionDescriptionHandler || !sessionDescriptionHandler.peerConnection) {
                
                return;
            }
            
            const peerConnection = sessionDescriptionHandler.peerConnection;
            
            
            // Get audio senders
            const senders = peerConnection.getSenders();
            const audioSender = senders.find(sender => 
                sender.track && sender.track.kind === 'audio'
            );
            
            if (audioSender) {
                
                const holdMusicTrack = this.holdMusicStream.getAudioTracks()[0];
                if (holdMusicTrack) {
                    await audioSender.replaceTrack(holdMusicTrack);
                    
                } else {
                    
                }
            } else {
                
            }
            
            
            
        } catch (error) {
            
        }
    }
    
    /**
     * Create hold music stream from real audio files (Browser-Phone style)
     */
    async createHoldMusicStream() {
        try {
            
            
            // First try to get real music from database
            const musicUrl = await this.getHoldMusicUrl(1);
            
            
            // If we have a real music file, use it
            if (musicUrl && !musicUrl.includes('data:audio/wav;base64')) {
                try {
                    
                    return await this.createHoldMusicFromFile(musicUrl);
                } catch (fileError) {
                    
                    // Clean up corrupted files and try again
                    await this.cleanupCorruptedMusic();
                    // Try to get music again after cleanup
                    const newMusicUrl = await this.getHoldMusicUrl(1);
                    if (newMusicUrl && !newMusicUrl.includes('data:audio/wav;base64')) {
                        
                        return await this.createHoldMusicFromFile(newMusicUrl);
                    }
                }
            }
            
            // Fallback to generated tone if no real music
            
            return await this.createHoldMusicTone();
            
        } catch (error) {
            
            throw error;
        }
    }
    
    /**
     * Create hold music from real audio file
     */
    async createHoldMusicFromFile(musicUrl) {
        try {
            
            
            // Check if it's a data URL (generated music)
            if (musicUrl.startsWith('data:audio/wav')) {
                
                return await this.createHoldMusicFromDataUrl(musicUrl);
            }
            
            // For real files, try to load them
            
            
            // Create audio context
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Resume if suspended
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }
            
            // Create audio element for the music file
            const audioElement = new Audio();
            audioElement.crossOrigin = 'anonymous';
            audioElement.loop = true;
            audioElement.volume = 0.7;
            audioElement.src = musicUrl;
            
            // Wait for audio to load
            await new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Audio load timeout'));
                }, 5000);
                
                audioElement.addEventListener('canplaythrough', () => {
                    clearTimeout(timeout);
                    resolve();
                });
                audioElement.addEventListener('error', (e) => {
                    clearTimeout(timeout);
                    reject(e);
                });
                audioElement.load();
            });
            
            // Create media element source
            const source = audioContext.createMediaElementSource(audioElement);
            const gainNode = audioContext.createGain();
            gainNode.gain.setValueAtTime(0.7, audioContext.currentTime);
            
            // Create destination
            const destination = audioContext.createMediaStreamDestination();
            source.connect(gainNode);
            gainNode.connect(destination);
            
            // Start playing
            audioElement.play();
            
            // Store references
            this.holdMusicAudio = audioElement;
            this.holdMusicGainNode = gainNode;
            this.holdMusicAudioContext = audioContext;
            this.holdMusicStream = destination.stream;
            
            
            return destination.stream;
            
        } catch (error) {
            
            throw error;
        }
    }
    
    /**
     * Create hold music from data URL
     */
    async createHoldMusicFromDataUrl(dataUrl) {
        try {
            
            
            // Create audio context
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Resume if suspended
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }
            
            // Create audio element for the data URL
            const audioElement = new Audio();
            audioElement.loop = true;
            audioElement.volume = 0.7;
            audioElement.src = dataUrl;
            
            // Wait for audio to load
            await new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Audio load timeout'));
                }, 3000);
                
                audioElement.addEventListener('canplaythrough', () => {
                    clearTimeout(timeout);
                    resolve();
                });
                audioElement.addEventListener('error', (e) => {
                    clearTimeout(timeout);
                    reject(e);
                });
                audioElement.load();
            });
            
            // Create media element source
            const source = audioContext.createMediaElementSource(audioElement);
            const gainNode = audioContext.createGain();
            gainNode.gain.setValueAtTime(0.7, audioContext.currentTime);
            
            // Create destination
            const destination = audioContext.createMediaStreamDestination();
            source.connect(gainNode);
            gainNode.connect(destination);
            
            // Start playing
            audioElement.play();
            
            // Store references
            this.holdMusicAudio = audioElement;
            this.holdMusicGainNode = gainNode;
            this.holdMusicAudioContext = audioContext;
            this.holdMusicStream = destination.stream;
            
            
            return destination.stream;
            
        } catch (error) {
            
            throw error;
        }
    }
    
    /**
     * Create hold music tone (fallback)
     */
    async createHoldMusicTone() {
        try {
            
            
            // Create audio context
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Resume if suspended
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }
            
            // Create oscillators
            const oscillator1 = audioContext.createOscillator();
            const oscillator2 = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            // Configure oscillators
            oscillator1.frequency.setValueAtTime(440, audioContext.currentTime);
            oscillator2.frequency.setValueAtTime(554.37, audioContext.currentTime);
            oscillator1.type = 'sine';
            oscillator2.type = 'sine';
            
            // Configure gain
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            
            // Connect oscillators to gain
            oscillator1.connect(gainNode);
            oscillator2.connect(gainNode);
            
            // Create destination
            const destination = audioContext.createMediaStreamDestination();
            gainNode.connect(destination);
            
            // Start oscillators
            oscillator1.start();
            oscillator2.start();
            
            // Store references
            this.holdMusicOscillator1 = oscillator1;
            this.holdMusicOscillator2 = oscillator2;
            this.holdMusicGainNode = gainNode;
            this.holdMusicAudioContext = audioContext;
            this.holdMusicStream = destination.stream;
            
            
            return destination.stream;
            
        } catch (error) {
            
            throw error;
        }
    }
    
    /**
     * Debug hold music audio flow (Browser-Phone style)
     */
    debugHoldMusicAudioFlow() {
        // Debug function - no logging needed
    }
    
    /**
     * Enhanced audio quality settings (Browser-Phone style)
     */
    getAudioConstraints() {
        return {
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                sampleRate: 48000,
                channelCount: 1
            },
            video: false
        };
    }
    
    /**
     * Get enhanced WebRTC configuration (Browser-Phone approach)
     */
    getWebRTCConfiguration() {
        return {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' },
                { urls: 'stun:stun2.l.google.com:19302' }
            ],
            iceCandidatePoolSize: 10,
            bundlePolicy: 'max-bundle',
            rtcpMuxPolicy: 'require'
        };
    }
    
    /**
     * Enhanced session description handler options (Browser-Phone style)
     */
    getSessionDescriptionHandlerOptions() {
        return {
            constraints: this.getAudioConstraints(),
            peerConnectionOptions: {
                iceServers: this.getWebRTCConfiguration().iceServers,
                iceCandidatePoolSize: 10,
                bundlePolicy: 'max-bundle',
                rtcpMuxPolicy: 'require'
            },
            iceGatheringTimeout: 5000,
            sessionTimer: 1800
        };
    }

    /**
     * Initialize audio elements for playback (Browser-Phone style)
     */
    initAudioElements() {
        // Create remote audio element for incoming audio
        if (!document.getElementById('voip-remote-audio')) {
            this.remoteAudio = document.createElement('audio');
            this.remoteAudio.autoplay = true;
            this.remoteAudio.id = 'voip-remote-audio';
            this.remoteAudio.playsInline = true; // Important for mobile devices
            document.body.appendChild(this.remoteAudio);
        } else {
            this.remoteAudio = document.getElementById('voip-remote-audio');
        }
        
        // Initialize Web Audio API context (Browser-Phone approach)
        this.initWebAudioContext();
    }
    
    /**
     * Initialize Web Audio API context (inspired by Browser-Phone)
     */
    initWebAudioContext() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.audioDestination = this.audioContext.createMediaStreamDestination();
            
            // Handle audio context suspension (common in mobile browsers)
            if (this.audioContext.state === 'suspended') {
                // Resume on user interaction
                const resumeAudio = () => {
                    this.audioContext.resume().then(() => {
                        document.removeEventListener('click', resumeAudio);
                        document.removeEventListener('touchstart', resumeAudio);
                    });
                };
                document.addEventListener('click', resumeAudio);
                document.addEventListener('touchstart', resumeAudio);
            }
            
            
        } catch (error) {
            
        }
    }

    /**
     * Initialize call tones (ringback, busy, ring)
     */
    initCallTones() {
        // Ringback tone (صوت الرنين عند الاتصال)
        this.ringbackTone = new Audio();
        this.ringbackTone.loop = true;
        this.ringbackTone.volume = 0.5;
        
        // Busy tone (صوت مشغول)
        this.busyTone = new Audio();
        this.busyTone.loop = false;
        this.busyTone.volume = 0.7;
        
        // Ring tone (صوت رنين المكالمة الواردة)
        this.ringTone = new Audio();
        this.ringTone.loop = true;
        this.ringTone.volume = 0.8;
        
        // Generate tones using Web Audio API
        this.generateCallTones();
    }

    /**
     * Generate call tones using Web Audio API
     */
    generateCallTones() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Generate Ringback Tone (440Hz + 480Hz for 2s on, 4s off)
            this.ringbackTone.src = this.createRingbackTone(audioContext);
            
            // Generate Busy Tone (480Hz + 620Hz for 0.5s on, 0.5s off)
            this.busyTone.src = this.createBusyTone(audioContext);
            
            // Generate Ring Tone (440Hz sine wave)
            this.ringTone.src = this.createRingTone(audioContext);
            
        } catch (error) {
            
        }
    }

    /**
     * Create ringback tone
     */
    createRingbackTone(audioContext) {
        const duration = 2;
        const sampleRate = audioContext.sampleRate;
        const buffer = audioContext.createBuffer(1, duration * sampleRate, sampleRate);
        const data = buffer.getChannelData(0);
        
        for (let i = 0; i < buffer.length; i++) {
            const t = i / sampleRate;
            // Mix 440Hz and 480Hz
            data[i] = (Math.sin(2 * Math.PI * 440 * t) + Math.sin(2 * Math.PI * 480 * t)) * 0.3;
        }
        
        return this.bufferToWave(buffer, buffer.length);
    }

    /**
     * Create busy tone
     */
    createBusyTone(audioContext) {
        const duration = 3;
        const sampleRate = audioContext.sampleRate;
        const buffer = audioContext.createBuffer(1, duration * sampleRate, sampleRate);
        const data = buffer.getChannelData(0);
        
        for (let i = 0; i < buffer.length; i++) {
            const t = i / sampleRate;
            const cycle = Math.floor(t * 2); // 0.5s cycles
            if (cycle % 2 === 0) {
                // Mix 480Hz and 620Hz
                data[i] = (Math.sin(2 * Math.PI * 480 * t) + Math.sin(2 * Math.PI * 620 * t)) * 0.4;
            }
        }
        
        return this.bufferToWave(buffer, buffer.length);
    }

    /**
     * Create ring tone
     */
    createRingTone(audioContext) {
        const duration = 2;
        const sampleRate = audioContext.sampleRate;
        const buffer = audioContext.createBuffer(1, duration * sampleRate, sampleRate);
        const data = buffer.getChannelData(0);
        
        for (let i = 0; i < buffer.length; i++) {
            const t = i / sampleRate;
            // 440Hz sine wave with fade in/out
            const envelope = Math.min(t * 10, 1) * Math.min((duration - t) * 10, 1);
            data[i] = Math.sin(2 * Math.PI * 440 * t) * envelope * 0.5;
        }
        
        return this.bufferToWave(buffer, buffer.length);
    }

    /**
     * Convert AudioBuffer to WAV data URL
     */
    bufferToWave(buffer, len) {
        const numOfChan = buffer.numberOfChannels;
        const length = len * numOfChan * 2 + 44;
        const bufferArray = new ArrayBuffer(length);
        const view = new DataView(bufferArray);
        const channels = [];
        let offset = 0;
        let pos = 0;

        // Write WAV header
        const setUint16 = (data) => {
            view.setUint16(pos, data, true);
            pos += 2;
        };
        const setUint32 = (data) => {
            view.setUint32(pos, data, true);
            pos += 4;
        };

        setUint32(0x46464952); // "RIFF"
        setUint32(length - 8); // file length - 8
        setUint32(0x45564157); // "WAVE"
        setUint32(0x20746d66); // "fmt " chunk
        setUint32(16); // length = 16
        setUint16(1); // PCM (uncompressed)
        setUint16(numOfChan);
        setUint32(buffer.sampleRate);
        setUint32(buffer.sampleRate * 2 * numOfChan);
        setUint16(numOfChan * 2);
        setUint16(16);
        setUint32(0x61746164); // "data" - chunk
        setUint32(length - pos - 4);

        // Write interleaved data
        for (let i = 0; i < buffer.numberOfChannels; i++) {
            channels.push(buffer.getChannelData(i));
        }

        while (pos < length) {
            for (let i = 0; i < numOfChan; i++) {
                let sample = Math.max(-1, Math.min(1, channels[i][offset]));
                sample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
                view.setInt16(pos, sample, true);
                pos += 2;
            }
            offset++;
        }

        const blob = new Blob([bufferArray], { type: 'audio/wav' });
        return URL.createObjectURL(blob);
    }

    /**
     * Play ringback tone
     */
    playRingbackTone() {
        this.stopAllTones();
        
        this.ringbackTone.play().catch(e => {
            // Could not play ringback tone
        });
    }

    /**
     * Play busy tone
     */
    playBusyTone() {
        this.stopAllTones();
        
        this.busyTone.play().catch(e => {
            // Could not play busy tone
        });
    }

    /**
     * Play ring tone
     */
    playRingTone() {
        this.stopAllTones();
        
        this.ringTone.play().catch(e => {
            // Could not play ring tone
        });
    }

    /**
     * Stop all tones
     */
    stopAllTones() {
        try {
            this.ringbackTone.pause();
            this.ringbackTone.currentTime = 0;
            this.busyTone.pause();
            this.busyTone.currentTime = 0;
            this.ringTone.pause();
            this.ringTone.currentTime = 0;
        } catch (e) {
            
        }
    }

    /**
     * Initialize SIP User Agent with SIP.js
     */
    async initialize() {
        try {
            // Load SIP.js library using the loader function
            voipLogger.debug('Loading SIP.js library...');
            
            try {
                await loadSipLibrary();
                
                // Verify it's available
                if (typeof window.SIP === 'undefined') {
                    // Give it a bit more time for UMD wrapper to execute
                    let retries = 0;
                    const maxRetries = 50; // Wait up to 5 seconds
                    
                    while (typeof window.SIP === 'undefined' && retries < maxRetries) {
                        await new Promise(resolve => setTimeout(resolve, 100));
                        retries++;
                    }
                }
                
                if (typeof window.SIP === 'undefined') {
                    const errorMsg = 'SIP.js library failed to load. Please check your assets configuration and ensure sip.min.js is accessible.';
                    voipLogger.error(errorMsg);
                    throw new Error(errorMsg);
                }
                
                voipLogger.debug('SIP.js library loaded successfully');
            } catch (loadError) {
                voipLogger.error('Error loading SIP.js library:', loadError);
                throw new Error(`Failed to load SIP.js library: ${loadError.message}`);
            }
            
            // Check WebRTC support
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('WebRTC is not supported. Please use HTTPS and a modern browser.');
            }

            // Build WebSocket URI
            let wsUri = this.config.server.websocket_url;
            
            if (!wsUri) {
                // Auto-detect protocol based on use_tls
                const protocol = this.config.server.use_tls ? 'wss' : 'ws';
                const port = this.config.server.use_tls 
                    ? (this.config.server.secure_port || 8089) 
                    : (this.config.server.port || 8088);
                wsUri = `${protocol}://${this.config.server.host}:${port}/ws`;
            }

            // Build SIP URI
            const sipUri = `sip:${this.config.user.username}@${this.config.server.realm || this.config.server.host}`;

            
            
            

            // Configure ICE servers (STUN)
            const iceServers = this.getIceServers();

            // Create User Agent options
            const userAgentOptions = {
                uri: window.SIP.UserAgent.makeURI(sipUri),
                transportOptions: {
                    server: wsUri,
                    connectionTimeout: 15,
                    keepAliveInterval: 30,
                },
                authorizationUsername: this.config.user.username,
                authorizationPassword: this.config.user.password,
                displayName: this.config.user.display_name || this.config.user.username,
                sessionDescriptionHandlerFactoryOptions: {
                    peerConnectionConfiguration: {
                        iceServers: iceServers,
                        rtcpMuxPolicy: 'require',
                        bundlePolicy: 'max-bundle',
                        iceTransportPolicy: 'all',
                    },
                    iceGatheringTimeout: 500,  // Reduced from 5000ms to 500ms for faster calls
                },
                delegate: {
                    onInvite: (invitation) => {
                        
                        this.handleIncomingCall(invitation);
                    },
                    onMessage: (message) => {
                        
                    },
                    onRefer: (referral) => {
                        
                        // Handle REFER requests if needed
                    },
                    onReferRequest: (referral) => {
                        
                        // Handle REFER requests if needed
                    }
                },
                autoStart: false,
                autoStop: false,
                register: false,
                noAnswerTimeout: 60,
            };

            // Create User Agent
            this.userAgent = new window.SIP.UserAgent(userAgentOptions);

            // Setup transport event handlers
            this.userAgent.transport.onConnect = () => {
                
                
                this.onTransportConnected();
            };

            this.userAgent.transport.onDisconnect = (error) => {
                if (error) {
                    
                    this.onTransportError(error);
                } else {
                    
                    this.onTransportDisconnected();
                }
            };

            // Start the user agent (connect to WebSocket)
            await this.userAgent.start();

            // Wait for connection
            await new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Connection timeout'));
                }, 15000);

                const checkConnection = setInterval(() => {
                    if (this.userAgent.transport.state === window.SIP.TransportState.Connected) {
                        clearTimeout(timeout);
                        clearInterval(checkConnection);
                        resolve();
                    }
                }, 100);
            });

            // Register with server
            await this.register();

            
            return true;

        } catch (error) {
            
            
            // Provide helpful error messages
            let friendlyError = error;
            
            if (error.message && error.message.includes('1006')) {
                // WebSocket connection failed
                friendlyError = new Error(
                    'Failed to connect to VoIP server. Possible causes:\n' +
                    '1. Server is offline or unreachable\n' +
                    '2. SSL certificate expired or invalid\n' +
                    '3. Firewall blocking connection\n' +
                    '4. Wrong WebSocket URL or port\n\n' +
                    'Please check your VoIP server configuration.'
                );
            } else if (error.message && error.message.includes('timeout')) {
                friendlyError = new Error(
                    'Connection timeout. The VoIP server did not respond within 15 seconds.\n' +
                    'Please check if the server is online and accessible.'
                );
            }
            
            throw friendlyError;
        }
    }

    /**
     * Get ICE servers configuration
     */
    getIceServers() {
        // Use default Google STUN servers for NAT traversal
        const iceServers = [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: 'stun:stun1.l.google.com:19302' },
            { urls: 'stun:stun2.l.google.com:19302' }
        ];

        return iceServers;
    }

    /**
     * Register with SIP server
     */
    async register() {
        try {
            if (!this.userAgent) {
                throw new Error('User Agent not initialized');
            }

            

            // Create registerer
            const registererOptions = {
                expires: 300, // 5 minutes
                refreshFrequency: 75, // Re-register at 75% of expiration
            };

            this.userAgent.registerer = new window.SIP.Registerer(this.userAgent, registererOptions);

            // Setup state change listener
            this.userAgent.registerer.stateChange.addListener((state) => {
                
                switch (state) {
                    case window.SIP.RegistererState.Registered:
                        
                        this.isRegistered = true;
                        
                        this.onRegistered();
                        break;
                    case window.SIP.RegistererState.Unregistered:
                        
                        this.isRegistered = false;
                        this.onUnregistered();
                        break;
                    case window.SIP.RegistererState.Terminated:
                        
                        this.isRegistered = false;
                        break;
                }
            });

            // Send REGISTER
            await this.userAgent.registerer.register({
                requestDelegate: {
                    onReject: (response) => {
                        
                        throw new Error(`Registration failed: ${response.message.reasonPhrase}`);
                    },
                    onAccept: (response) => {
                        
                    }
                }
            });

            return true;

        } catch (error) {
            
            throw error;
        }
    }

    /**
     * Make an outbound call
     */
    async makeCall(phoneNumber) {
        const startTime = Date.now();
        
        
        
        
        try {
            if (!this.userAgent || !this.isRegistered) {
                throw new Error('Not registered with SIP server');
            }

            
            

            // Build target URI
            
            const targetUri = window.SIP.UserAgent.makeURI(
                `sip:${phoneNumber}@${this.config.server.realm || this.config.server.host}`
            );

            if (!targetUri) {
                throw new Error('Invalid phone number or server configuration');
            }
            

            // Create inviter (outbound session)
            
            const inviter = new window.SIP.Inviter(this.userAgent, targetUri, {
                sessionDescriptionHandlerOptions: {
                    constraints: {
                        audio: true,
                        video: false
                    },
                    iceGatheringTimeout: 500  // Limit ICE gathering to 500ms
                }
            });
            

            // Setup session event handlers
            this.setupSessionHandlers(inviter);


            // Update call state and play ringback tone
            this.updateCallState('ringing');
            this.playRingbackTone();
            

            // Variable to store rejection error
            let callRejected = false;
            let rejectionError = null;

            // Send INVITE
            
            await inviter.invite({
                requestDelegate: {
                    onReject: (response) => {
                        const reasonPhrase = response.message.reasonPhrase || 'Unknown error';
                        const statusCode = response.message.statusCode;
                        
                        
                        
                        // Stop ringback and play busy tone
                        this.stopAllTones();
                        if (statusCode === 486 || statusCode === 503 || statusCode === 600) {
                            this.playBusyTone();
                        }
                        
                        // Store rejection info
                        callRejected = true;
                        
                        // Provide user-friendly error messages
                        if (statusCode === 503) {
                            rejectionError = 'Service Unavailable';
                        } else if (statusCode === 486) {
                            rejectionError = 'Busy Here';
                        } else if (statusCode === 404) {
                            rejectionError = 'Not Found';
                        } else if (statusCode === 408) {
                            rejectionError = 'Request Timeout';
                        } else if (statusCode === 480) {
                            rejectionError = 'Temporarily Unavailable';
                        } else {
                            rejectionError = reasonPhrase;
                        }
                        
                        
                    }
                }
            });

            

            // Store session reference immediately after INVITE is sent
            this.currentSession = inviter;
            
            // Get SIP Call ID from inviter request (available after invite() completes)
            let sipCallId = null;
            try {
                // SIP Call ID is in the Call-ID header of the INVITE request
                if (inviter.request && inviter.request.message) {
                    const callIdHeader = inviter.request.message.getHeader('Call-ID');
                    if (callIdHeader) {
                        sipCallId = callIdHeader;
                    }
                }
                
                // Fallback: try other locations
                if (!sipCallId) {
                    if (inviter.request && inviter.request.callId) {
                        sipCallId = inviter.request.callId;
                    } else if (inviter.id) {
                        sipCallId = inviter.id;
                    }
                }
                
                // Store SIP Call ID for later use
                if (sipCallId) {
                    this.sipCallId = sipCallId;
                    voipLogger.debug('SIP Call ID captured:', sipCallId);
                } else {
                    voipLogger.warn('SIP Call ID not found in inviter request');
                }
            } catch (e) {
                voipLogger.warn('Error getting SIP Call ID:', e);
            }
            
            // Setup session event handlers
            this.setupSessionHandlers(inviter);
            
            // Check if call was rejected
            if (callRejected) {
                throw new Error(rejectionError);
            }
            
            // Don't start recording here - it will be started in onCallEstablished
            
            return true;

        } catch (error) {
            
            
            // Stop ringback and play busy tone on error
            this.stopAllTones();
            
            // Check if it's a busy/unavailable error
            const errorMsg = error.message || '';
            if (errorMsg.includes('Busy') || errorMsg.includes('Unavailable') || errorMsg.includes('503') || errorMsg.includes('486')) {
                
                this.playBusyTone();
            }
            
            throw this.formatError(error);
        }
    }

    /**
     * Handle incoming call
     */
    async handleIncomingCall(invitation) {
        
        
        
        this.currentSession = invitation;
        
        // Get SIP Call ID from invitation
        let sipCallId = null;
        try {
            // SIP Call ID is in the Call-ID header of the INVITE request
            // For incoming calls, use incomingInviteRequest
            if (invitation.incomingInviteRequest && invitation.incomingInviteRequest.message) {
                const callIdHeader = invitation.incomingInviteRequest.message.getHeader('Call-ID');
                if (callIdHeader) {
                    sipCallId = callIdHeader.trim();
                }
            }
            
            // Fallback: try request.message directly
            if (!sipCallId && invitation.request && invitation.request.message) {
                const callIdHeader = invitation.request.message.getHeader('Call-ID');
                if (callIdHeader) {
                    sipCallId = callIdHeader.trim();
                }
            }
            
            // Fallback: try other locations
            if (!sipCallId) {
                if (invitation.request && invitation.request.callId) {
                    sipCallId = invitation.request.callId;
                } else if (invitation.id) {
                    sipCallId = invitation.id;
                }
            }
            
            // Store SIP Call ID for later use
            if (sipCallId) {
                this.sipCallId = sipCallId;
                voipLogger.debug('SIP Call ID captured from incoming call:', sipCallId);
                console.log('🔧 VoIP Client Debug: SIP Call ID stored:', sipCallId);
            } else {
                voipLogger.warn('SIP Call ID not found in invitation');
                console.warn('🔧 VoIP Client Debug: SIP Call ID not found in invitation');
            }
        } catch (e) {
            voipLogger.warn('Error getting SIP Call ID from invitation:', e);
            console.error('🔧 VoIP Client Debug: Error getting SIP Call ID:', e);
        }

        // Play ring tone for incoming call
        this.playRingTone();
        

        // Setup session event handlers
        this.setupSessionHandlers(invitation);

        // Notify user (this will be handled by voipService)
        if (this.voipService.onIncomingCall) {
            
            this.voipService.onIncomingCall({
                from: invitation.remoteIdentity.uri.user,
                displayName: invitation.remoteIdentity.displayName,
                session: invitation
            });
        }
    }

    /**
     * Start recording
     */
    async startRecording() {
        try {
            
            
            
            
            if (!this.currentSession) {
                throw new Error('No active call to record');
            }

            // Get local and remote streams
            const localStream = this.currentSession.sessionDescriptionHandler.getLocalStream();
            const remoteStream = this.currentSession.sessionDescriptionHandler.getRemoteStream();

            
            
            
            

            if (!localStream && !remoteStream) {
                
                throw new Error('No audio streams available for recording');
            }

            // Create a mixed stream for recording
            let recordingStream;
            
            if (localStream && remoteStream) {
                
                // Mix both streams
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const destination = audioContext.createMediaStreamDestination();
                
                const localSource = audioContext.createMediaStreamSource(localStream);
                const remoteSource = audioContext.createMediaStreamSource(remoteStream);
                
                localSource.connect(destination);
                remoteSource.connect(destination);
                
                recordingStream = destination.stream;
                
            } else if (localStream) {
                
                recordingStream = localStream;
            } else if (remoteStream) {
                
                recordingStream = remoteStream;
            }

            if (recordingStream) {
                
                
                
                
                try {
                    // Check if MediaRecorder supports the stream
                    if (MediaRecorder.isTypeSupported('audio/webm')) {
                        
                        this.mediaRecorder = new MediaRecorder(recordingStream, {
                            mimeType: 'audio/webm'
                        });
                    } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
                        
                        this.mediaRecorder = new MediaRecorder(recordingStream, {
                            mimeType: 'audio/mp4'
                        });
                    } else {
                        
                        this.mediaRecorder = new MediaRecorder(recordingStream);
                    }
                    
                    this.recordedChunks = [];
                    

                    this.mediaRecorder.ondataavailable = (event) => {
                        
                        
                        if (event.data.size > 0) {
                            this.recordedChunks.push(event.data);
                            
                        }
                    };

                    this.mediaRecorder.onstop = () => {
                        
                        // 
                        this.saveRecording();
                    };

                    this.mediaRecorder.onerror = (event) => {
                        
                    };

                    this.mediaRecorder.start(1000); // Record in 1-second chunks
                    
                    
                    
                } catch (recorderError) {
                    
                    
                    // Fallback: Use getUserMedia to record system audio
                    try {
                        
                        const fallbackStream = await navigator.mediaDevices.getUserMedia({ 
                            audio: {
                                echoCancellation: false,
                                noiseSuppression: false,
                                autoGainControl: false
                            } 
                        });
                        
                        
                        this.mediaRecorder = new MediaRecorder(fallbackStream);
                        this.recordedChunks = [];

                        this.mediaRecorder.ondataavailable = (event) => {
                            
                            if (event.data.size > 0) {
                                this.recordedChunks.push(event.data);
                            }
                        };

                        this.mediaRecorder.onstop = () => {
                            
                            this.saveRecording();
                        };

                        this.mediaRecorder.start(1000);
                        
                        
                    } catch (fallbackError) {
                        
                        throw new Error('Recording not supported on this device');
                    }
                }
            }

        } catch (error) {
            
            throw error;
        }
    }

    /**
     * Save recording to server
     */
    async saveRecording() {
        
        
        
        
        
        
        
        try {
            // Check if already saved OR currently saving
            if (this.recordingSaved || this.recordingSaving) {
                
                
                
                return;
            }
            
            if (!this.recordedChunks || this.recordedChunks.length === 0) {
                console.warn('🔧 VoIP Client Debug: No recorded chunks to save!');
                return;
            }
            
            // Mark as saving IMMEDIATELY to prevent duplicate calls (race condition protection)
            this.recordingSaving = true;
            

            
            
            
            
            
            // Calculate duration
            let duration = this.getCallDuration();
            
            
            
            
            
            // Fallback: estimate duration from recording size if callStartTime was not set
            if (duration === 0 && this.recordedChunks.length > 0) {
                // Rough estimate: 1 second of recording ≈ 8-16 KB (depending on quality)
                const totalSize = this.recordedChunks.reduce((sum, chunk) => sum + chunk.size, 0);
                duration = Math.max(1, Math.floor(totalSize / 10000)); // Conservative estimate
                
            }
            
            const blob = new Blob(this.recordedChunks, { type: 'audio/webm' });
            
            
            const formData = new FormData();
            formData.append('recording', blob, `call_${Date.now()}.webm`);
            // Use Odoo 추all ID instead of SIP session ID
            // IMPORTANT: Use this.odooCallId directly (saved before cleanup)
            const callId = this.odooCallId || 'unknown';
            console.log('🔧 VoIP Client Debug: Saving recording with call_id:', callId);
            formData.append('call_id', callId);
            formData.append('duration', duration);
            
            
            
            

            
            
            
            
            console.log('🔧 VoIP Client Debug: Sending recording to server...');
            console.log('🔧 VoIP Client Debug: Blob size:', blob.size, 'bytes');
            console.log('🔧 VoIP Client Debug: Duration:', duration, 'seconds');
            
            // Send to Odoo server
            // Note: Don't set CSRF token manually - Odoo route has csrf=False
            const response = await fetch('/voip_webrtc_freepbx/save_recording', {
                method: 'POST',
                body: formData
            });
            
            console.log('🔧 VoIP Client Debug: Server response status:', response.status);

            
            
            
            

            if (response.ok) {
                
                const result = await response.json();
                
                
                
                
                // Mark as saved after successful save
                this.recordingSaved = true;
                
            } else {
                
                
                const errorText = await response.text();
                
                throw new Error(`Server error: ${response.status} - ${errorText}`);
            }

            

        } catch (error) {
            
            
        } finally {
            // Always unlock the saving flag to allow retry on error
            this.recordingSaving = false;
            
        }
    }

    /**
     * Get call duration
     */
    getCallDuration() {
        if (this.callStartTime) {
            return Math.floor((Date.now() - this.callStartTime) / 1000);
        }
        return 0;
    }

    /**
     * Update call duration in Odoo database
     */
    async updateCallDuration(duration) {
        try {
            if (!this.odooCallId) {
                
                return;
            }

            // Only update if duration is greater than 0
            if (duration <= 0) {
                
                return;
            }

            

            // Use the voipService to update the call
            if (this.voipService && this.voipService.updateCallDuration) {
                const result = await this.voipService.updateCallDuration(this.odooCallId, duration);
                if (result) {
                    
                } else {
                    
                }
            } else {
                
            }
        } catch (error) {
            
        }
    }

    /**
     * Answer incoming call
     */
    async answerCall() {
        try {
            if (!this.currentSession) {
                throw new Error('No incoming call to answer');
            }

            

            await this.currentSession.accept({
                sessionDescriptionHandlerOptions: {
                    constraints: {
                        audio: true,
                        video: false
                    }
                }
            });

            
            
            // Don't start recording here - it will be started in onCallEstablished
            
            return true;

        } catch (error) {
            
            throw this.formatError(error);
        }
    }

    /**
     * Reject incoming call
     */
    async reject() {
        try {
            if (!this.currentSession) {
                
                return false;
            }

            

            // Stop ring tone
            this.stopAllTones();

            // Reject the session
            await this.currentSession.reject();

            
            this.currentSession = null;
            return true;

        } catch (error) {
            
            this.currentSession = null;
            return false;
        }
    }

    /**
     * Hang up current call
     */
    async hangup() {
        try {
            if (!this.currentSession) {
                
                return false;
            }

            

            // Stop recording if active
            this.stopRecording();

            // Clean up media
            if (this.localStream) {
                this.localStream.getTracks().forEach(track => track.stop());
                this.localStream = null;
            }

            // Terminate session
            const state = this.currentSession.state;
            
            if (state === window.SIP.SessionState.Initial || 
                state === window.SIP.SessionState.Establishing) {
                // Cancel outgoing call
                await this.currentSession.cancel();
            } else if (state === window.SIP.SessionState.Established) {
                // Hang up established call
                await this.currentSession.bye();
            } else {
                // Reject incoming call
                await this.currentSession.reject();
            }

            this.currentSession = null;
            

            return true;

        } catch (error) {
            
            this.currentSession = null;
            return false;
        }
    }

    /**
     * Setup session event handlers
     */
    setupSessionHandlers(session) {
        // Session state changes
        session.stateChange.addListener((state) => {
            
            
            switch (state) {
                case window.SIP.SessionState.Establishing:
                    
                    break;
                case window.SIP.SessionState.Established:
                    
                    this.onCallEstablished(session);
                    break;
                case window.SIP.SessionState.Terminated:
                    
                    this.onCallTerminated(session);
                    break;
            }
        });

        // Handle REFER events for call transfer
        session.delegate = {
            ...session.delegate,
            onRefer: (referral) => {
                
                // Handle REFER requests if needed
            },
            onReferRequest: (referral) => {
                
                // Handle REFER requests if needed
            }
        };
    }

    /**
     * Handle call established
     */
    onCallEstablished(session) {
        
        
        
        
        
        // Record call start time for duration calculation
        this.callStartTime = Date.now();
        
        
        // Stop all tones when call is established
        this.stopAllTones();
        
        
        // Setup remote audio
        const sessionDescriptionHandler = session.sessionDescriptionHandler;
        
        
        
        if (sessionDescriptionHandler && sessionDescriptionHandler.peerConnection) {
            const remoteStreamForPlayback = new MediaStream();
            
            sessionDescriptionHandler.peerConnection.getReceivers().forEach((receiver) => {
                if (receiver.track) {
                    remoteStreamForPlayback.addTrack(receiver.track);
                }
            });

            
            this.remoteAudio.srcObject = remoteStreamForPlayback;
            this.remoteAudio.play().catch(e => {
                // Error playing audio
            }); 

            // IMPORTANT: Get confirmed SIP Call ID from the ESTABLISHED session
            // This ensures we have the final Call-ID after server response (fixes Caller ID issue)
            let confirmedSipCallId = null;
            try {
                if (session.dialog && session.dialog.request) {
                    const callIdHeader = session.dialog.request.message.getHeader('Call-ID');
                    if (callIdHeader) {
                        confirmedSipCallId = callIdHeader.trim();
                    }
                }
                if (!confirmedSipCallId && session.request && session.request.message) {
                    const callIdHeader = session.request.message.getHeader('Call-ID');
                    if (callIdHeader) {
                        confirmedSipCallId = callIdHeader.trim();
                    }
                }
                if (!confirmedSipCallId) {
                    confirmedSipCallId = this.sipCallId || session.id || null;
                }
                
                if (confirmedSipCallId && confirmedSipCallId !== this.sipCallId) {
                    console.log('🔧 VoIP Client Debug: Updating SIP Call ID from', this.sipCallId, 'to', confirmedSipCallId);
                    this.sipCallId = confirmedSipCallId;
                    if (this.odooCallId && this.voipService && this.voipService.updateCallSipId) {
                        this.voipService.updateCallSipId(this.odooCallId, confirmedSipCallId).catch(err => {
                            voipLogger.warn('Error updating SIP Call ID in Odoo:', err);
                        });
                    }
                } else if (confirmedSipCallId && !this.sipCallId) {
                    this.sipCallId = confirmedSipCallId;
                    console.log('🔧 VoIP Client Debug: SIP Call ID confirmed:', confirmedSipCallId);
                }
            } catch (e) {
                voipLogger.warn('Error getting confirmed SIP Call ID:', e);
            }

            // Create mixed stream for recording using AudioContext (same as Odoo 17)
            // MediaRecorder does not support recording more than one audio track directly
            // So we need to use AudioContext to mix the streams into a single track
            let recordingStream = null;
            let hasLocalStream = false;
            let hasRemoteStream = false;
            
            console.log('🔧 VoIP Client Debug: Creating mixed stream for recording using AudioContext...');
            
            // Get local stream (microphone input)
            let localStream = null;
            const localSenders = sessionDescriptionHandler.peerConnection.getSenders();
            const localAudioTracks = localSenders
                .filter(sender => sender.track && sender.track.kind === 'audio')
                .map(sender => sender.track)
                .filter(track => track.enabled && track.readyState === 'live');
            
            if (localAudioTracks.length > 0) {
                localStream = new MediaStream(localAudioTracks);
                hasLocalStream = true;
                console.log('🔧 VoIP Client Debug: Found local stream with', localAudioTracks.length, 'audio track(s)');
            }
            
            // Get remote stream (speaker output)
            let remoteStream = null;
            const remoteReceivers = sessionDescriptionHandler.peerConnection.getReceivers();
            const remoteAudioTracks = remoteReceivers
                .filter(receiver => receiver.track && receiver.track.kind === 'audio')
                .map(receiver => receiver.track)
                .filter(track => track.enabled && track.readyState === 'live');
            
            if (remoteAudioTracks.length > 0) {
                remoteStream = new MediaStream(remoteAudioTracks);
                hasRemoteStream = true;
                console.log('🔧 VoIP Client Debug: Found remote stream with', remoteAudioTracks.length, 'audio track(s)');
            }
            
            // Mix both streams using AudioContext (same approach as Odoo 17)
            if (hasLocalStream && hasRemoteStream) {
                console.log('🔧 VoIP Client Debug: Mixing local and remote streams using AudioContext...');
                try {
                    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    const destination = audioContext.createMediaStreamDestination();
                    
                    const localSource = audioContext.createMediaStreamSource(localStream);
                    const remoteSource = audioContext.createMediaStreamSource(remoteStream);
                    
                    localSource.connect(destination);
                    remoteSource.connect(destination);
                    
                    recordingStream = destination.stream;
                    this.recordingAudioContext = audioContext; // Store for cleanup
                    
                    console.log('🔧 VoIP Client Debug: ✅ Mixed stream created with', recordingStream.getTracks().length, 'track(s) (AudioContext)');
                } catch (mixError) {
                    console.error('🔧 VoIP Client Debug: Error mixing streams:', mixError);
                    // Fallback to local stream only
                    if (localStream) {
                        recordingStream = localStream;
                        console.log('🔧 VoIP Client Debug: Fallback to local stream only');
                    }
                }
            } else if (hasLocalStream) {
                // Only local stream available
                recordingStream = localStream;
                console.log('🔧 VoIP Client Debug: Using local stream only');
            } else if (hasRemoteStream) {
                // Only remote stream available
                recordingStream = remoteStream;
                console.log('🔧 VoIP Client Debug: Using remote stream only');
            }
            
            // Store local stream separately for reference
            if (hasLocalStream && localStream) {
                this.localStream = localStream;
            }

            
            

            // Start recording if enabled - use mixed stream (local + remote)
            // Delay slightly to ensure streams are fully ready (FIXES RECORDING ISSUE)
            if (this.config.user.enable_recording && recordingStream && recordingStream.getTracks().length > 0) {
                console.log('🔧 VoIP Client Debug: Starting recording with', recordingStream.getTracks().length, 'track(s) (local:', hasLocalStream, ', remote:', hasRemoteStream, ')');
                
                // Small delay to ensure streams are fully active before starting recording
                setTimeout(() => {
                    if (this.currentSession === session && recordingStream && recordingStream.getTracks().length > 0) {
                        const activeTracks = recordingStream.getTracks().filter(track => track.readyState === 'live');
                        if (activeTracks.length > 0) {
                            console.log('🔧 VoIP Client Debug: Starting recording with', activeTracks.length, 'active track(s)');
                            this.startRecording(recordingStream);
                        } else {
                            voipLogger.warn('No active tracks for recording, will retry...');
                            setTimeout(() => {
                                if (this.currentSession === session && recordingStream) {
                                    const retryTracks = recordingStream.getTracks().filter(track => track.readyState === 'live');
                                    if (retryTracks.length > 0) {
                                        console.log('🔧 VoIP Client Debug: Retry - Starting recording with', retryTracks.length, 'active track(s)');
                                        this.startRecording(recordingStream);
                                    } else {
                                        voipLogger.error('Failed to start recording: No active tracks available');
                                    }
                                }
                            }, 500);
                        }
                    }
                }, 300); // 300ms delay to ensure streams are ready
            } else {
                if (!this.config.user.enable_recording) {
                    voipLogger.debug('Recording is disabled in user config');
                } else {
                    voipLogger.warn('No audio tracks available for recording');
                }
            }
        }

        // Notify service
        if (this.voipService.onCallEstablished) {
            this.voipService.onCallEstablished(session);
        }
        
        
    }

    /**
     * Handle call terminated
     */
    onCallTerminated(session) {
        
        
        
        
        
        
        // Record call end time and log duration
        this.callEndTime = Date.now();
        const duration = this.getCallDuration();
        
        
        
        
        // Get SIP Call ID from session for updating call record
        let sipCallId = null;
        try {
            if (session.request && session.request.message) {
                const callIdHeader = session.request.message.getHeader('Call-ID');
                if (callIdHeader) {
                    sipCallId = callIdHeader;
                }
            }
            
            if (!sipCallId) {
                sipCallId = this.sipCallId || session.id || null;
            }
            
            if (sipCallId && !this.sipCallId) {
                this.sipCallId = sipCallId;
            }
        } catch (e) {
            voipLogger.warn('Error getting SIP Call ID in onCallTerminated:', e);
            sipCallId = this.sipCallId || null;
        }
        
        // Update call in Odoo - try by Odoo call ID first, then by SIP Call ID
        if (this.odooCallId && this.voipService && this.voipService.updateCallDuration) {
            // Update duration
            this.updateCallDuration(this.odooCallId, duration);
            
            // Also update end_time, state, and SIP Call ID via hangupCall
            if (this.voipService.hangupCall) {
                this.voipService.hangupCall('normal', sipCallId).catch(err => {
                    voipLogger.warn('Error updating call on hangup:', err);
                });
            }
        } else if (sipCallId && this.voipService && this.voipService.hangupCall) {
            // Try to update by SIP Call ID
            voipLogger.debug('Updating call by SIP Call ID on termination:', sipCallId);
            this.voipService.hangupCall('normal', sipCallId).catch(err => {
                voipLogger.warn('Error updating call by SIP Call ID:', err);
            });
        }
        
        // Stop all tones when call terminates
        this.stopAllTones();
        
        
        
        
        
        
        // IMPORTANT: Save critical data BEFORE stopping recording and cleaning up
        // Recording is stopped asynchronously, and saveRecording() needs these values
        const savedOdooCallId = this.odooCallId;
        const savedCallStartTime = this.callStartTime;
        const savedCallEndTime = this.callEndTime;
        
        // Stop recording (this will trigger saveRecording() asynchronously via onstop handler)
        console.log('🔧 VoIP Client Debug: Stopping recording, odooCallId:', savedOdooCallId, 'callStartTime:', savedCallStartTime);
        this.stopRecording();
        
        // IMPORTANT: Don't stop recording stream tracks immediately
        // MediaRecorder needs the tracks to remain active until stop() is called
        // Only stop tracks AFTER recording is saved (handled in onstop handler)
        // Just stop playback streams here
        if (this.remoteAudio.srcObject) {
            const remoteTracks = this.remoteAudio.srcObject.getTracks();
            remoteTracks.forEach(track => {
                if (track.readyState !== 'ended') {
                    track.stop();
                }
            });
            this.remoteAudio.srcObject = null;
        }
        
        // Clean up localStream for playback, but keep recording stream alive
        // The recordingStream will be cleaned up after saveRecording() completes
        setTimeout(() => {
            // Only clean up if recording is NOT active
            if (this.localStream && (!this.mediaRecorder || this.mediaRecorder.state === 'inactive')) {
                const tracks = this.localStream.getTracks();
                tracks.forEach(track => {
                    if (track.readyState !== 'ended') {
                        track.stop();
                    }
                });
                this.localStream = null;
            }
        }, 1000); // Longer delay to allow recording to complete
        
        // Reset session reference (but keep odooCallId and timing until recording is saved)
        this.currentSession = null;
        
        // DON'T reset callStartTime, callEndTime, or odooCallId yet - saveRecording() needs them
        // They will be reset after recording is successfully saved in onstop handler


        
        // Notify service
        if (this.voipService.onCallTerminated) {
            this.voipService.onCallTerminated(session);
        }
        
        
    }

    /**
     * Start recording the call
     */
    startRecording(stream) {
        try {
            // Prevent multiple startRecording calls
            if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
                console.warn('🔧 VoIP Client Debug: Recording already in progress, ignoring startRecording call');
                return;
            }
            
            console.log('🔧 VoIP Client Debug: ===== START RECORDING =====');
            console.log('🔧 VoIP Client Debug: Stream tracks:', stream.getTracks().length);
            
            // Reset recording state
            this.recordedChunks = [];
            this.recordingSaved = false;
            this.recordingSaving = false;
            

            // Create MediaRecorder
            const options = MediaRecorder.isTypeSupported('audio/webm') 
                ? { mimeType: 'audio/webm' }
                : { mimeType: 'audio/ogg' };

            
            // Verify stream has active tracks before creating MediaRecorder
            const activeTracks = stream.getTracks().filter(track => track.readyState === 'live' && track.enabled);
            console.log('🔧 VoIP Client Debug: Creating MediaRecorder with', activeTracks.length, 'active tracks');
            
            // Log all tracks details
            stream.getTracks().forEach((track, idx) => {
                console.log('🔧 VoIP Client Debug: Track', idx, '- kind:', track.kind, ', enabled:', track.enabled, ', readyState:', track.readyState, ', muted:', track.muted);
            });
            
            if (activeTracks.length === 0) {
                console.error('🔧 VoIP Client Debug: ERROR - No active tracks in stream for recording!');
                throw new Error('No active audio tracks available for recording');
            }
            
            console.log('🔧 VoIP Client Debug: About to create MediaRecorder...');
            try {
                this.mediaRecorder = new MediaRecorder(stream, options);
                console.log('🔧 VoIP Client Debug: ✅ MediaRecorder created successfully, state:', this.mediaRecorder.state);
            } catch (createError) {
                console.error('🔧 VoIP Client Debug: ❌ ERROR creating MediaRecorder:', createError);
                throw createError;
            }
            
            // Store stream reference to prevent garbage collection
            this.recordingStream = stream;
            console.log('🔧 VoIP Client Debug: Recording stream stored, tracks:', this.recordingStream.getTracks().length);
            
            // Track data events - use object reference so it's accessible in all handlers
            const dataReceivedCountRef = { count: 0 };

            this.mediaRecorder.ondataavailable = (event) => {
                dataReceivedCountRef.count++;
                console.log('🔧 VoIP Client Debug: ===== ondataavailable FIRED #' + dataReceivedCountRef.count + ' =====');
                console.log('🔧 VoIP Client Debug: Event data size:', event.data.size, 'bytes');
                console.log('🔧 VoIP Client Debug: Event data type:', event.data.type);
                if (event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                    console.log('🔧 VoIP Client Debug: Chunk added. Total chunks:', this.recordedChunks.length, ', Total size:', this.recordedChunks.reduce((sum, chunk) => sum + chunk.size, 0), 'bytes');
                } else {
                    console.warn('🔧 VoIP Client Debug: ondataavailable fired but data size is 0!');
                }
            };

            this.mediaRecorder.onstop = () => {
                console.log('🔧 VoIP Client Debug: ===== mediaRecorder.onstop FIRED =====');
                console.log('🔧 VoIP Client Debug: Recorded chunks count:', this.recordedChunks ? this.recordedChunks.length : 0);
                console.log('🔧 VoIP Client Debug: ondataavailable was called', dataReceivedCountRef.count, 'times');
                console.log('🔧 VoIP Client Debug: odooCallId:', this.odooCallId);
                console.log('🔧 VoIP Client Debug: callStartTime:', this.callStartTime);
                console.log('🔧 VoIP Client Debug: MediaRecorder final state:', this.mediaRecorder.state);
                
                // Calculate total size of recorded chunks for debugging
                if (this.recordedChunks && this.recordedChunks.length > 0) {
                    const totalSize = this.recordedChunks.reduce((sum, chunk) => sum + chunk.size, 0);
                    console.log('🔧 VoIP Client Debug: Total recording size:', totalSize, 'bytes');
                    
                    // Call saveRecording to upload to server
                    this.saveRecording().then(() => {
                        console.log('🔧 VoIP Client Debug: Recording saved successfully');
                        // Now safe to reset call timing and state
                        this.callStartTime = null;
                        this.callEndTime = null;
                        this.recordingSaved = false;
                        this.recordingSaving = false;
                    }).catch((error) => {
                        console.error('🔧 VoIP Client Debug: Error saving recording:', error);
                        // Still reset state even on error
                        this.callStartTime = null;
                        this.callEndTime = null;
                        this.recordingSaved = false;
                        this.recordingSaving = false;
                    }).finally(() => {
                        // Clean up recording stream AFTER saving is complete
                        if (this.recordingStream) {
                            console.log('🔧 VoIP Client Debug: Cleaning up recording stream');
                            const tracks = this.recordingStream.getTracks();
                            tracks.forEach(track => {
                                if (track.readyState !== 'ended') {
                                    track.stop();
                                }
                            });
                            this.recordingStream = null;
                        }
                    });
                } else {
                    console.warn('🔧 VoIP Client Debug: onstop fired but no recorded chunks available!');
                }
            };

            this.mediaRecorder.onerror = (event) => {
                console.error('🔧 VoIP Client Debug: MediaRecorder ERROR:', event);
                console.error('🔧 VoIP Client Debug: Error details:', event.error);
            };

            // Check MediaRecorder state before starting
            console.log('🔧 VoIP Client Debug: About to start MediaRecorder, state:', this.mediaRecorder.state);
            
            // Start recording with timeslice (collects data every second)
            try {
                this.mediaRecorder.start(1000);
                console.log('🔧 VoIP Client Debug: MediaRecorder.start() called, state:', this.mediaRecorder.state);
                
                // Verify MediaRecorder is actually recording
                setTimeout(() => {
                    console.log('🔧 VoIP Client Debug: MediaRecorder check after 1.5s - state:', this.mediaRecorder.state);
                    if (this.mediaRecorder.state === 'inactive') {
                        console.error('🔧 VoIP Client Debug: ERROR - MediaRecorder stopped unexpectedly!');
                        console.error('🔧 VoIP Client Debug: Stream tracks:', stream.getTracks().map(t => ({
                            kind: t.kind,
                            enabled: t.enabled,
                            readyState: t.readyState,
                            muted: t.muted
                        })));
                    }
                    console.log('🔧 VoIP Client Debug: Chunks collected so far:', this.recordedChunks ? this.recordedChunks.length : 0);
                }, 1500);
                
            } catch (startError) {
                console.error('🔧 VoIP Client Debug: ERROR starting MediaRecorder:', startError);
                throw startError;
            }
            

        } catch (error) {
            console.error('🔧 VoIP Client Debug: ERROR in startRecording:', error);
            console.error('🔧 VoIP Client Debug: Error stack:', error.stack);
        }
    }

    /**
     * Stop recording
     */
    stopRecording() {
        console.log('🔧 VoIP Client Debug: stopRecording() called');
        console.log('🔧 VoIP Client Debug: mediaRecorder state:', this.mediaRecorder ? this.mediaRecorder.state : 'null');
        console.log('🔧 VoIP Client Debug: recordedChunks length:', this.recordedChunks ? this.recordedChunks.length : 0);
        console.log('🔧 VoIP Client Debug: odooCallId:', this.odooCallId);
        console.log('🔧 VoIP Client Debug: callStartTime:', this.callStartTime);
        
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            console.log('🔧 VoIP Client Debug: Stopping mediaRecorder...');
            try {
                this.mediaRecorder.stop();
                console.log('🔧 VoIP Client Debug: mediaRecorder.stop() called successfully');
            } catch (error) {
                console.error('🔧 VoIP Client Debug: Error stopping mediaRecorder:', error);
                // If stop fails, try to save directly
                if (this.recordedChunks && this.recordedChunks.length > 0) {
                    console.log('🔧 VoIP Client Debug: Attempting to save recording directly after stop error');
                    this.saveRecording();
                }
            }
        } else {
            console.log('🔧 VoIP Client Debug: MediaRecorder is inactive or null, checking for chunks...');
            // If MediaRecorder is already inactive, we still need to save
            if (this.recordedChunks && this.recordedChunks.length > 0) {
                console.log('🔧 VoIP Client Debug: Found recorded chunks, calling saveRecording() directly');
                this.saveRecording();
            } else {
                console.warn('🔧 VoIP Client Debug: No recorded chunks available to save');
            }
        }
    }


    /**
     * Transport event handlers
     */
    onTransportConnected() {
        
    }

    onTransportDisconnected() {
        
        this.isRegistered = false;
    }

    onTransportError(error) {
        
        this.isRegistered = false;
    }

    /**
     * Registration event handlers
     */
    onRegistered() {
        
    }

    onUnregistered() {
        
    }

    /**
     * Disconnect and cleanup
     */
    async disconnect() {
        try {
            // Hang up any active call
            if (this.currentSession) {
                await this.hangup();
            }

            // Unregister
            if (this.userAgent && this.userAgent.registerer) {
                await this.userAgent.registerer.unregister();
            }

            // Stop user agent
            if (this.userAgent) {
                await this.userAgent.stop();
            }

            this.isRegistered = false;
            

            return true;

        } catch (error) {
            
            return false;
        }
    }

    /**
     * Format error messages
     */
    formatError(error) {
        if (error.name === 'NotAllowedError') {
            return new Error('Microphone access denied. Please allow microphone access.');
        } else if (error.name === 'NotFoundError') {
            return new Error('No microphone found. Please connect a microphone.');
        } else if (error.message && error.message.includes('HTTPS')) {
            return error;
        } else {
            return new Error(error.message || 'An error occurred');
        }
    }

    /**
     * Hold current call (based on phone.js working implementation)
     */
    async holdCall() {
        try {
            if (!this.currentSession) {
                throw new Error('No active call to hold');
            }

            if (this.currentSession.isOnHold === true) {
                
                return true;
            }

            
            this.currentSession.isOnHold = true;

            // Set hold options (like phone.js)
            const sessionDescriptionHandlerOptions = this.currentSession.sessionDescriptionHandlerOptionsReInvite;
            sessionDescriptionHandlerOptions.hold = true;
            this.currentSession.sessionDescriptionHandlerOptionsReInvite = sessionDescriptionHandlerOptions;

            const options = {
                requestDelegate: {
                    onAccept: () => {
                        if (this.currentSession && this.currentSession.sessionDescriptionHandler && this.currentSession.sessionDescriptionHandler.peerConnection) {
                            const pc = this.currentSession.sessionDescriptionHandler.peerConnection;
                            
                            // Stop all the inbound streams (like phone.js)
                            pc.getReceivers().forEach((RTCRtpReceiver) => {
                                if (RTCRtpReceiver.track) RTCRtpReceiver.track.enabled = false;
                            });
                            
                            // Stop all the outbound streams (like phone.js)
                            pc.getSenders().forEach((RTCRtpSender) => {
                                // Mute Audio
                                if (RTCRtpSender.track && RTCRtpSender.track.kind === "audio") {
                                    if (RTCRtpSender.track.IsMixedTrack === true) {
                                        if (this.currentSession.data.AudioSourceTrack && this.currentSession.data.AudioSourceTrack.kind === "audio") {
                                            
                                            this.currentSession.data.AudioSourceTrack.enabled = false;
                                        }
                                    }
                                    
                                    RTCRtpSender.track.enabled = false;
                                }
                                // Stop Video
                                else if (RTCRtpSender.track && RTCRtpSender.track.kind === "video") {
                                    RTCRtpSender.track.enabled = false;
                                }
                            });
                        }
                        
                        this.currentSession.isOnHold = true;
                        

                        // Log Hold (like phone.js)
                        if (!this.currentSession.data) this.currentSession.data = {};
                        if (!this.currentSession.data.hold) this.currentSession.data.hold = [];
                        this.currentSession.data.hold.push({ 
                            event: "hold", 
                            eventTime: new Date().toISOString() 
                        });

                        
                    },
                    onReject: () => {
                        this.currentSession.isOnHold = false;
                        
                        throw new Error('Failed to put call on hold');
                    }
                }
            };

            // Send INVITE with hold (like phone.js)
            await this.currentSession.invite(options);
            
            return true;
            
        } catch (error) {
            
            if (this.currentSession) {
                this.currentSession.isOnHold = false;
            }
            throw error;
        }
    }

    /**
     * Resume held call (based on phone.js working implementation)
     */
    async resumeCall() {
        try {
            if (!this.currentSession) {
                throw new Error('No active call to resume');
            }

            if (this.currentSession.isOnHold === false) {
                
                return true;
            }

            
            this.currentSession.isOnHold = false;

            // Set unhold options (like phone.js)
            const sessionDescriptionHandlerOptions = this.currentSession.sessionDescriptionHandlerOptionsReInvite;
            sessionDescriptionHandlerOptions.hold = false;
            this.currentSession.sessionDescriptionHandlerOptionsReInvite = sessionDescriptionHandlerOptions;

            const options = {
                requestDelegate: {
                    onAccept: () => {
                        if (this.currentSession && this.currentSession.sessionDescriptionHandler && this.currentSession.sessionDescriptionHandler.peerConnection) {
                            const pc = this.currentSession.sessionDescriptionHandler.peerConnection;
                            
                            // Restore all the inbound streams (like phone.js)
                            pc.getReceivers().forEach((RTCRtpReceiver) => {
                                if (RTCRtpReceiver.track) RTCRtpReceiver.track.enabled = true;
                            });
                            
                            // Restore all the outbound streams (like phone.js)
                            pc.getSenders().forEach((RTCRtpSender) => {
                                // Unmute Audio
                                if (RTCRtpSender.track && RTCRtpSender.track.kind === "audio") {
                                    if (RTCRtpSender.track.IsMixedTrack === true) {
                                        if (this.currentSession.data.AudioSourceTrack && this.currentSession.data.AudioSourceTrack.kind === "audio") {
                                            
                                            this.currentSession.data.AudioSourceTrack.enabled = true;
                                        }
                                    }
                                    
                                    RTCRtpSender.track.enabled = true;
                                }
                                else if (RTCRtpSender.track && RTCRtpSender.track.kind === "video") {
                                    RTCRtpSender.track.enabled = true;
                    }
                });
            }
            
                        this.currentSession.isOnHold = false;
                        

                        // Log Hold (like phone.js)
                        if (!this.currentSession.data) this.currentSession.data = {};
                        if (!this.currentSession.data.hold) this.currentSession.data.hold = [];
                        this.currentSession.data.hold.push({ 
                            event: "unhold", 
                            eventTime: new Date().toISOString() 
                        });

                        
                    },
                    onReject: () => {
                        this.currentSession.isOnHold = true;
                        
                        throw new Error('Failed to take call off hold');
                    }
                }
            };

            // Send INVITE with unhold (like phone.js)
            await this.currentSession.invite(options);
            
            return true;
            
        } catch (error) {
            
            if (this.currentSession) {
                this.currentSession.isOnHold = true;
            }
            throw error;
        }
    }

    /**
     * Transfer call to another user
     */
    /**
     * Transfer call to another user using SIP REFER
     */
    // async transferCall(extension) {
    //     try {
    //         if (!this.currentSession) {
    //             throw new Error('No active call to transfer');
    //         }

    //         
            
    //         // Check if extension is valid
    //         if (!extension) {
    //             throw new Error('Extension is required for transfer');
    //         }
            
    //         // Use SIP.js refer method for professional transfer
    //         
            
    //         // Get the target URI
    //         const transferTarget = `sip:${extension}@${this.config.server.host}`;
    //         
            
    //         // Check if session has refer method
    //         if (!this.currentSession.refer) {
    //             throw new Error('Session does not support REFER method');
    //         }
            
    //         // Create a promise to handle the REFER response
    //         const referPromise = new Promise((resolve, reject) => {
    //             // Use the session's refer method (correct SIP.js API)
    //             this.currentSession.refer(transferTarget, {
    //                 requestDelegate: {
    //                     onAccept: (response) => {
    //                         
    //                         // Don't hang up immediately - let the server handle the transfer
    //                         
    //                         resolve(true);
    //                     },
    //                     onReject: (response) => {
    //                         
    //                         reject(new Error(`Transfer rejected: ${response.reasonPhrase || 'Unknown reason'}`));
    //                     },
    //                     onProgress: (response) => {
    //                         
    //                     }
    //                 }
    //             });
    //         });
            
    //         // Wait for the REFER response
    //         await referPromise;
            
    //         
    //         return true;
                
    //     } catch (error) {
    //         
    //         throw error;
    //     }
    // }

    /**
     * Transfer call to extension (Complete phone.js implementation)
     */
    async transferCall(extension) {
        try {
            
            
            if (!this.currentSession) {
                throw new Error('No active call to transfer');
            }

            if (this.currentSession.state !== 'Established') {
                throw new Error('Call must be established to transfer');
            }
            
            
            
            
            // Initialize session data if not exists (exact phone.js implementation)
            if (!this.currentSession.data) {
                this.currentSession.data = {};
                
            }
            
            // Get SIP domain from config
            const sipDomain = this.config.server.host;
            const transferTarget = `sip:${extension.replace(/#/g, "%23")}@${sipDomain}`;
            
            
            
            // Initialize transfer data if not exists (exact phone.js implementation)
            if (!this.currentSession.data.transfer) {
                this.currentSession.data.transfer = [];
                
            }
            
            // Add transfer record (exact phone.js structure)
            this.currentSession.data.transfer.push({ 
                type: "Blind", 
                to: extension, 
                transferTime: new Date().toISOString(), 
                disposition: "refer",
                dispositionTime: new Date().toISOString(), 
                accept : {
                    complete: null,
                    eventTime: null,
                    disposition: ""
                }
            });
            
            const transferId = this.currentSession.data.transfer.length - 1;
            
            // Transfer options (exact phone.js implementation)
            const transferOptions = { 
                requestDelegate: {
                    onAccept: (sip) => {
                        
                        
                        
                        
                        
                        // Set session data (exact phone.js)
                        this.currentSession.data.terminateby = "us";
                        this.currentSession.data.reasonCode = 202;
                        this.currentSession.data.reasonText = "Transfer";
                        
                        // Update transfer record (exact phone.js)
                        this.currentSession.data.transfer[transferId].accept.complete = true;
                        this.currentSession.data.transfer[transferId].accept.disposition = sip.message.reasonPhrase;
                        this.currentSession.data.transfer[transferId].accept.eventTime = new Date().toISOString();
                        
                        
                        
                        
                        
                        // Disconnect transferrer after successful transfer (exact phone.js timing)
                        this.currentSession.bye().catch((error) => {
                            
                        });
                        
                        
                    },
                    onReject: (sip) => {
                        
                        
                        // Update transfer record (exact phone.js)
                        this.currentSession.data.transfer[transferId].accept.complete = false;
                        this.currentSession.data.transfer[transferId].accept.disposition = sip.message.reasonPhrase;
                        this.currentSession.data.transfer[transferId].accept.eventTime = new Date().toISOString();
                        
                        
                        
                    }
                }
            };
            
            
            
            
            // Use exact phone.js method
            const referTo = SIP.UserAgent.makeURI(transferTarget);
            
            
            // Call session.refer with options (exact phone.js implementation)
            this.currentSession.refer(referTo, transferOptions).catch((error) => {
                
                throw error;
            });
            
            
            return true;
            
        } catch (error) {
            
            throw error;
        }
    }

    /**
     * Attended Transfer (Complete phone.js implementation)
     */
    async attendedTransfer(extension) {
        try {
            
            
            if (!this.currentSession) {
                throw new Error('No active call to transfer');
            }
            
            if (this.currentSession.state !== 'Established') {
                throw new Error('Call must be established to transfer');
            }
            
            // Initialize session data if not exists (exact phone.js implementation)
            if (!this.currentSession.data) {
                this.currentSession.data = {};
                
            }
            
            // Get SIP domain from config
            const sipDomain = this.config.server.host;
            const transferTarget = `sip:${extension.replace(/#/g, "%23")}@${sipDomain}`;
            
            
            
            // Initialize transfer data if not exists (exact phone.js implementation)
            if (!this.currentSession.data.transfer) {
                this.currentSession.data.transfer = [];
                
            }
            
            // Add transfer record (exact phone.js structure)
            this.currentSession.data.transfer.push({ 
                type: "Attended", 
                to: extension, 
                transferTime: new Date().toISOString(), 
                disposition: "invite",
                dispositionTime: new Date().toISOString(), 
                accept : {
                    complete: null,
                    eventTime: null,
                    disposition: ""
                }
            });
            
            const transferId = this.currentSession.data.transfer.length - 1;
            
            // SDP options (exact phone.js implementation)
            const supportedConstraints = navigator.mediaDevices.getSupportedConstraints();
            const sdpOptions = {
                earlyMedia: true,
                sessionDescriptionHandlerOptions: {
                    constraints: {
                        audio: { deviceId: "default" },
                        video: false
                    }
                }
            };
            
            // Add additional constraints (exact phone.js)
            if (supportedConstraints.autoGainControl) {
                sdpOptions.sessionDescriptionHandlerOptions.constraints.audio.autoGainControl = true;
            }
            if (supportedConstraints.echoCancellation) {
                sdpOptions.sessionDescriptionHandlerOptions.constraints.audio.echoCancellation = true;
            }
            if (supportedConstraints.noiseSuppression) {
                sdpOptions.sessionDescriptionHandlerOptions.constraints.audio.noiseSuppression = true;
            }
            
            
            
            // Create new call session (exact phone.js implementation)
            const targetURI = SIP.UserAgent.makeURI(transferTarget);
            const newSession = new SIP.Inviter(this.userAgent, targetURI, sdpOptions);
            newSession.data = {};
            
            // Set up new session delegate (exact phone.js implementation)
            newSession.delegate = {
                onBye: (sip) => {
                    
                    this.currentSession.data.transfer[transferId].disposition = "bye";
                    this.currentSession.data.transfer[transferId].dispositionTime = new Date().toISOString();
                    
                    
                },
                onSessionDescriptionHandler: (sdh, provisional) => {
                    if (sdh && sdh.peerConnection) {
                        sdh.peerConnection.ontrack = (event) => {
                            const pc = sdh.peerConnection;
                            
                            // Gets Remote Audio Track (exact phone.js implementation)
                            const remoteStream = new MediaStream();
                            pc.getReceivers().forEach((receiver) => {
                                if (receiver.track && receiver.track.kind === "audio") {
                                    remoteStream.addTrack(receiver.track);
                                }
                            });
                            
                            
                        };
                    }
                }
            };
            
            // Store child session (exact phone.js implementation)
            this.currentSession.data.childsession = newSession;
            
            // Inviter options (exact phone.js implementation)
            const inviterOptions = {
                requestDelegate: {
                    onTrying: (sip) => {
                        
                        this.currentSession.data.transfer[transferId].disposition = "trying";
                        this.currentSession.data.transfer[transferId].dispositionTime = new Date().toISOString();
                    },
                    onProgress: (sip) => {
                        
                        this.currentSession.data.transfer[transferId].disposition = "progress";
                        this.currentSession.data.transfer[transferId].dispositionTime = new Date().toISOString();
                    },
                    onAccept: (sip) => {
                        
                        this.currentSession.data.transfer[transferId].disposition = "accepted";
                        this.currentSession.data.transfer[transferId].dispositionTime = new Date().toISOString();
                        
                        
                        
                        // Return the new session for UI to handle completion
                        return newSession;
                    },
                    onReject: (sip) => {
                        
                        this.currentSession.data.transfer[transferId].disposition = sip.message.reasonPhrase;
                        this.currentSession.data.transfer[transferId].dispositionTime = new Date().toISOString();
                        
                        
                    }
                }
            };
            
            // Send INVITE (exact phone.js implementation)
            newSession.invite(inviterOptions).catch((error) => {
                
                throw error;
            });
            
            
            return newSession;
            
        } catch (error) {
            
            throw error;
        }
    }

    /**
     * Complete Attended Transfer (exact phone.js implementation)
     */
    async completeAttendedTransfer(newSession) {
        try {
            
            
            if (!this.currentSession || !newSession) {
                throw new Error('No active sessions for transfer completion');
            }
            
            const transferId = this.currentSession.data.transfer.length - 1;
            
            // Transfer options for completion (exact phone.js implementation)
            const transferOptions = { 
                requestDelegate: {
                    onAccept: (sip) => {
                        
                        
                        this.currentSession.data.terminateby = "us";
                        this.currentSession.data.reasonCode = 202;
                        this.currentSession.data.reasonText = "Attended Transfer";
                        
                        this.currentSession.data.transfer[transferId].accept.complete = true;
                        this.currentSession.data.transfer[transferId].accept.disposition = sip.message.reasonPhrase;
                        this.currentSession.data.transfer[transferId].accept.eventTime = new Date().toISOString();
                        
                        
                        
                        // End the original session (exact phone.js implementation)
                        this.currentSession.bye().catch((error) => {
                            
                        });
                    },
                    onReject: (sip) => {
                        
                        
                        this.currentSession.data.transfer[transferId].accept.complete = false;
                        this.currentSession.data.transfer[transferId].accept.disposition = sip.message.reasonPhrase;
                        this.currentSession.data.transfer[transferId].accept.eventTime = new Date().toISOString();
                        
                        
                    }
                }
            };
            
            // Send REFER to complete transfer (exact phone.js implementation)
            this.currentSession.refer(newSession, transferOptions).catch((error) => {
                
                throw error;
            });
            
            
            return true;
            
        } catch (error) {
            
            throw error;
        }
    }


    /**
     * Mute microphone
     */
    muteMicrophone() {
        try {
            if (this.localStream) {
                this.localStream.getTracks().forEach(track => {
                    if (track.kind === 'audio') {
                        track.enabled = false;
                    }
                });
                
                return true;
            }
        } catch (error) {
            
        }
        return false;
    }

    /**
     * Unmute microphone
     */
    unmuteMicrophone() {
        try {
            if (this.localStream) {
                this.localStream.getTracks().forEach(track => {
                    if (track.kind === 'audio') {
                        track.enabled = true;
                    }
                });
                
                return true;
            }
        } catch (error) {
            
        }
        return false;
    }

    /**
     * Start hold music without muting microphone
     */
    async startHoldMusicOnly(musicId) {
        try {
            
            
            
            
            if (!this.currentSession) {
                throw new Error('No active call to play hold music');
            }

            // Stop any existing hold music
            await this.stopHoldMusic();

            // Try alternative hold music method first
            
            await this.createHoldMusicStream();
            
            // Debug audio flow before injection
            this.debugHoldMusicAudioFlow();
            
            // Inject hold music into the call stream
            
            await this.injectHoldMusicStream();
            
            
            
        } catch (error) {
            
            
        }
    }

    /**
     * Start hold music
     */
    async startHoldMusic(musicId) {
        try {
            
            
            if (!this.currentSession) {
                throw new Error('No active call to play hold music');
            }

            // Stop any existing hold music
            await this.stopHoldMusic();

            // Create hold music using Web Audio API (more reliable)
            await this.createHoldMusicWithWebAudio(musicId);
            
            // Inject hold music into the call stream
            await this.injectHoldMusicIntoCall();
            
            
            return true;
        } catch (error) {
            
            return false;
        }
    }

    /**
     * Stop hold music
     */
    async stopHoldMusic() {
        try {
            
            
            // Stop Web Audio API oscillators
            if (this.holdMusicOscillator1) {
                try {
                    this.holdMusicOscillator1.stop();
                    this.holdMusicOscillator1 = null;
                    
                } catch (error) {
                    
                }
            }
            
            if (this.holdMusicOscillator2) {
                try {
                    this.holdMusicOscillator2.stop();
                    this.holdMusicOscillator2 = null;
                    
                } catch (error) {
                    
                }
            }
            
            // Clean up hold music stream
            if (this.holdMusicStream) {
                this.holdMusicStream.getTracks().forEach(track => track.stop());
                this.holdMusicStream = null;
                
            }
            
            // Clean up audio context
            if (this.holdMusicAudioContext) {
                try {
                    await this.holdMusicAudioContext.close();
                    this.holdMusicAudioContext = null;
                    
                } catch (error) {
                    
                }
            }
            
            // Stop legacy audio element if exists
            if (this.holdMusicAudio) {
                this.holdMusicAudio.pause();
                this.holdMusicAudio.currentTime = 0;
                this.holdMusicAudio = null;
            }
            
            // Stop direct tone if playing
            if (this.holdMusicOscillator) {
                try {
                    this.holdMusicOscillator.stop();
                    this.holdMusicOscillator = null;
                    
                } catch (error) {
                    
                }
            }
            
            // Remove hold music from call stream
            await this.removeHoldMusicFromCall();
            
            
            return true;
        } catch (error) {
            
            return false;
        }
    }

    /**
     * Create hold music using Web Audio API (enhanced Browser-Phone style)
     */
    async createHoldMusicWithWebAudio(musicId) {
        try {
            
            
            // Clean up any existing hold music first
            await this.stopHoldMusic();
            
            // Create new audio context for hold music (don't reuse closed context)
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Resume audio context if suspended
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
                
            }
            
            
            
            // Ensure audio context is running
            if (audioContext.state !== 'running') {
                
                await audioContext.resume();
                
            }
            
            // Create a more pleasant hold music tone (Browser-Phone approach)
            const oscillator1 = audioContext.createOscillator();
            const oscillator2 = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            const filterNode = audioContext.createBiquadFilter();
            const compressor = audioContext.createDynamicsCompressor();
            
            // Configure oscillators for a pleasant chord
            oscillator1.frequency.setValueAtTime(440, audioContext.currentTime); // A4
            oscillator2.frequency.setValueAtTime(554.37, audioContext.currentTime); // C#5
            
            oscillator1.type = 'sine';
            oscillator2.type = 'sine';
            
            // Configure filter for warmer sound
            filterNode.type = 'lowpass';
            filterNode.frequency.setValueAtTime(2000, audioContext.currentTime);
            filterNode.Q.setValueAtTime(1, audioContext.currentTime);
            
            // Configure compressor for better audio quality
            compressor.threshold.setValueAtTime(-24, audioContext.currentTime);
            compressor.knee.setValueAtTime(30, audioContext.currentTime);
            compressor.ratio.setValueAtTime(12, audioContext.currentTime);
            compressor.attack.setValueAtTime(0.003, audioContext.currentTime);
            compressor.release.setValueAtTime(0.25, audioContext.currentTime);
            
            // Configure gain for appropriate volume (louder for remote party)
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            
            // Connect the audio graph (Browser-Phone style)
            oscillator1.connect(filterNode);
            oscillator2.connect(filterNode);
            filterNode.connect(compressor);
            compressor.connect(gainNode);
            
            // Store references for later cleanup
            this.holdMusicOscillator1 = oscillator1;
            this.holdMusicOscillator2 = oscillator2;
            this.holdMusicGainNode = gainNode;
            this.holdMusicAudioContext = audioContext;
            
            // Start the oscillators
            oscillator1.start();
            oscillator2.start();
            
            
            
        } catch (error) {
            
            throw error;
        }
    }

    /**
     * Get hold music URL (enhanced for real music files)
     */
    async getHoldMusicUrl(musicId) {
        try {
            
            
            // Try to get music from database first using fetch
            
            try {
                const response = await fetch('/voip/hold_music/list', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({})
                });
                
                if (response.ok) {
                    const data = await response.json();
                    
                    
                    // Handle JSON-RPC response format
                    const result = data.result || data;
                    
                    
                    if (result.success && result.music_list && result.music_list.length > 0) {
                        
                        // Find music by ID or use first available
                        const music = result.music_list.find(m => m.id === musicId) || result.music_list[0];
                        
                        
                        if (music && music.url) {
                            
                            // Check if it's a real uploaded file (not generated)
                            if (music.url.includes('/voip_webrtc_freepbx/hold_music/file/') || 
                                music.url.includes('/voip/hold_music/file/')) {
                                
                            return music.url;
                            } else {
                                
                            }
                        }
                    } else {
                        
                    }
                } else {
                    
                }
            } catch (fetchError) {
                
            }
        } catch (error) {
            
        }
        
        // If no music from database, try to create a default music file
        
        return await this.createDefaultHoldMusic();
    }
    
    /**
     * Create default hold music file
     */
    async createDefaultHoldMusic() {
        try {
            
            
            // Create a simple but pleasant hold music using Web Audio API
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const sampleRate = audioContext.sampleRate;
            const duration = 30; // 30 seconds
            const buffer = audioContext.createBuffer(1, sampleRate * duration, sampleRate);
            const data = buffer.getChannelData(0);
            
            // Create a more pleasant melody
            const melody = [
                { freq: 440, duration: 2 },   // A4
                { freq: 523.25, duration: 2 }, // C5
                { freq: 659.25, duration: 2 }, // E5
                { freq: 783.99, duration: 2 }, // G5
                { freq: 659.25, duration: 2 }, // E5
                { freq: 523.25, duration: 2 }, // C5
                { freq: 440, duration: 2 },   // A4
                { freq: 392, duration: 2 },   // G4
            ];
            
            let sampleIndex = 0;
            
            for (const note of melody) {
                const noteSamples = sampleRate * note.duration;
                const endIndex = Math.min(sampleIndex + noteSamples, data.length);
                
                for (let i = sampleIndex; i < endIndex; i++) {
                    const time = (i - sampleIndex) / sampleRate;
                    
                    // Create a pleasant tone with harmonics
                    data[i] = Math.sin(2 * Math.PI * note.freq * time) * 0.1 +
                             Math.sin(2 * Math.PI * note.freq * 2 * time) * 0.05 +
                             Math.sin(2 * Math.PI * note.freq * 3 * time) * 0.02;
                    
                    // Add some vibrato
                    const vibrato = Math.sin(2 * Math.PI * 5 * time) * 0.01;
                    data[i] *= (1 + vibrato);
                }
                
                sampleIndex = endIndex;
                
                // If we've filled the duration, break
                if (sampleIndex >= data.length) {
                    break;
                }
            }
            
            // Convert to WAV and create data URL
            const wavBuffer = this.encodeWAV(buffer);
            const base64 = this.arrayBufferToBase64(wavBuffer);
            const dataUrl = `data:audio/wav;base64,${base64}`;
            
            
            return dataUrl;
            
        } catch (error) {
            
            return 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';
        }
    }
    
    /**
     * Encode audio buffer to WAV format
     */
    encodeWAV(buffer) {
        const length = buffer.length;
        const arrayBuffer = new ArrayBuffer(44 + length * 2);
        const view = new DataView(arrayBuffer);
        
        // WAV header
        const writeString = (offset, string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        };
        
        writeString(0, 'RIFF');
        view.setUint32(4, 36 + length * 2, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, 44100, true);
        view.setUint32(28, 88200, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeString(36, 'data');
        view.setUint32(40, length * 2, true);
        
        // Convert float samples to 16-bit PCM
        let offset = 44;
        for (let i = 0; i < length; i++) {
            const sample = Math.max(-1, Math.min(1, buffer[i]));
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
            offset += 2;
        }
        
        return arrayBuffer;
    }
    
    /**
     * Convert ArrayBuffer to base64
     */
    arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return window.btoa(binary);
    }
    
    createSilentAudio() {
        // Create a simple tone using Web Audio API
        
        
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(440, audioContext.currentTime);
            oscillator.type = 'sine';
            gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
            
            // Start the tone
            oscillator.start();
            
            // Stop after 2 seconds
            setTimeout(() => {
                oscillator.stop();
            }, 2000);
            
            
            
            // Return a working audio URL
            return 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';
            
        } catch (error) {
            
            // Return a working audio URL
            return 'data:audio/wav;base64,UklGRigAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';
        }
    }
    
    encodeWAV(buffer) {
        const length = buffer.length;
        const arrayBuffer = new ArrayBuffer(44 + length * 2);
        const view = new DataView(arrayBuffer);
        
        // WAV header
        const writeString = (offset, string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        };
        
        writeString(0, 'RIFF');
        view.setUint32(4, 36 + length * 2, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, 1, true);
        view.setUint32(24, 44100, true);
        view.setUint32(28, 88200, true);
        view.setUint16(32, 2, true);
        view.setUint16(34, 16, true);
        writeString(36, 'data');
        view.setUint32(40, length * 2, true);
        
        // Convert float samples to 16-bit PCM
        let offset = 44;
        for (let i = 0; i < length; i++) {
            const sample = Math.max(-1, Math.min(1, buffer[i]));
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
            offset += 2;
        }
        
        return arrayBuffer;
    }
    
    arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return window.btoa(binary);
    }

    /**
     * Inject hold music into the call stream
     */
    async injectHoldMusicIntoCall() {
        try {
            
            
            
            
            if (!this.currentSession) {
                
                return;
            }

            // Get the peer connection
            const sessionDescriptionHandler = this.currentSession.sessionDescriptionHandler;
            
            
            
            if (!sessionDescriptionHandler || !sessionDescriptionHandler.peerConnection) {
                
                return;
            }

            const peerConnection = sessionDescriptionHandler.peerConnection;
            
            
            // Use existing audio context from hold music creation
            const audioContext = this.holdMusicAudioContext;
            if (!audioContext) {
                
                return;
            }
            
            
            
            // Ensure audio context is running
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
                
            }
            
            // If audio context is closed, create a new one
            if (audioContext.state === 'closed') {
                
                this.holdMusicAudioContext = new (window.AudioContext || window.webkitAudioContext)();
                await this.holdMusicAudioContext.resume();
                
                return; // Exit and let the next call handle it
            }
            
            // Use our stored local stream
            if (this.localStream) {
                
                const localAudioSource = audioContext.createMediaStreamSource(this.localStream);
                const destination = audioContext.createMediaStreamDestination();
                
                
                // Create a mixer for local audio and hold music
                const mixer = audioContext.createGain();
                mixer.gain.setValueAtTime(1.0, audioContext.currentTime);
                
                // Add a limiter to prevent audio clipping
                const limiter = audioContext.createDynamicsCompressor();
                limiter.threshold.setValueAtTime(-3, audioContext.currentTime);
                limiter.knee.setValueAtTime(0, audioContext.currentTime);
                limiter.ratio.setValueAtTime(20, audioContext.currentTime);
                limiter.attack.setValueAtTime(0.001, audioContext.currentTime);
                limiter.release.setValueAtTime(0.01, audioContext.currentTime);
                
                // Connect local audio to mixer
                
                localAudioSource.connect(mixer);
                
                // Connect hold music to mixer (oscillators are already connected to gain node)
                if (this.holdMusicGainNode) {
                    
                    this.holdMusicGainNode.connect(mixer);
                }
                
                // Connect mixer through limiter to destination
                
                mixer.connect(limiter);
                limiter.connect(destination);
                
                
                
                // Replace the local stream in the peer connection
                const senders = peerConnection.getSenders();
                
                
                const audioSender = senders.find(sender => 
                    sender.track && sender.track.kind === 'audio'
                );
                
                
                if (audioSender) {
                    
                    const newTrack = destination.stream.getAudioTracks()[0];
                    
                    await audioSender.replaceTrack(newTrack);
                    
                } else {
                    
                }
            } else {
                
            }
            
            
            
        } catch (error) {
            
            
            
        }
    }

    /**
     * Remove hold music from call stream
     */
    async removeHoldMusicFromCall() {
        try {
            
            
            if (!this.currentSession) {
                
                return;
            }

            const sessionDescriptionHandler = this.currentSession.sessionDescriptionHandler;
            if (!sessionDescriptionHandler || !sessionDescriptionHandler.peerConnection) {
                
                return;
            }

            const peerConnection = sessionDescriptionHandler.peerConnection;
            
            // Get original local stream (without hold music)
            if (this.localStream) {
                
                const senders = peerConnection.getSenders();
                const audioSender = senders.find(sender => 
                    sender.track && sender.track.kind === 'audio'
                );
                
                if (audioSender && this.localStream.getAudioTracks().length > 0) {
                    await audioSender.replaceTrack(this.localStream.getAudioTracks()[0]);
                    
                } else {
                    
                }
            } else {
                
            }
            
            
            
        } catch (error) {
            
        }
    }

    /**
     * Check if registered
     */
    isClientRegistered() {
        return this.isRegistered;
    }

    /**
     * Get current session
     */
    getCurrentSession() {
        return this.currentSession;
    }

    /**
     * Handle webhook notifications to update user status
     */
    async handleWebhookNotification(notificationData) {
        try {
            
            
            // Send notification to systray if available
            if (window.voipSystray && window.voipSystray.handleWebhookNotification) {
                await window.voipSystray.handleWebhookNotification(notificationData);
            }
            
            // Update local state if needed
            const userExtension = notificationData.extension || notificationData.user;
            const eventType = notificationData.event || notificationData.type;
            
            if (userExtension && eventType) {
                
                
                // Update call state based on event
                if (eventType === 'call_start' || eventType === 'call_ringing') {
                    this.callState = 'ringing';
                } else if (eventType === 'call_connected') {
                    this.callState = 'connected';
                } else if (eventType === 'call_end' || eventType === 'call_hangup') {
                    this.callState = 'ended';
                }
            }
            
        } catch (error) {
            
        }
    }
}

