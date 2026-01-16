/** @odoo-module **/

import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { VoipSipClient } from "./voip_sip_client";

/**
 * VoIP Systray Item
 * 
 * Provides quick access to VoIP functionality from the systray
 */
export class VoipSystray extends Component {
    setup() {
        this.voip = useService("voip");
        this.notification = useService("notification");
        this.action = useService("action");
        
        this.state = useState({
            isInitialized: false,
            isRegistered: false,
            showDialer: false,
            phoneNumber: "",
            inCall: false,
            incomingCall: false,
            incomingCallNumber: "",
            incomingCallTime: "",
            callDuration: 0,
            recentCalls: [],
            canControlRecording: false,
            autoStartRecording: false,
            isRecording: false,
            // Call controls state
            isMuted: false,
            isSpeaker: false,
            isOnHold: false,
            // Tabs state
            activeTab: 'dialer', // 'dialer', 'incoming', 'history', 'contacts'
            contacts: [],
            searchQuery: '',
            // VoIP Users for transfer
            voipUsers: [],
            showTransferList: false,
            showTransferDropdown: false,
            // Incoming call tabs
            incomingActiveTab: 'incoming', // 'incoming', 'transfer', 'hold'
            transferSearchQuery: '',
            // Active call tabs
            activeCallTab: 'controls', // 'controls', 'transfer', 'hold'
            // Hold Music
            holdMusicList: [],
            currentHoldMusic: {},
            selectedHoldMusic: null,
            holdMusicPlaying: false,
            showHoldMusicMenu: false,
            holdMusicOptions: [
                { id: 'default', name: 'Default', description: 'Standard hold music' },
                { id: 'classical', name: 'Classical', description: 'Classical music' },
                { id: 'jazz', name: 'Jazz', description: 'Jazz music' },
                { id: 'ambient', name: 'Ambient', description: 'Ambient music' },
                { id: 'corporate', name: 'Corporate', description: 'Corporate music' }
            ],
            selectedMusicId: null,
            holdMusicVolume: 70,
            // Position state for draggable dialer
            position: { x: null, y: null },
            isDragging: false,
        });

        onWillStart(async () => {
            await this.initializeVoip();
        });

        onMounted(() => {
            this.updateCallDuration();
            console.log('🔧 VoIP Systray Debug: Component mounted, isRegistered:', this.state.isRegistered);
            
            // Setup incoming call handler
            this.voip.onIncomingCall = this.onIncomingCall.bind(this);
            
            // Setup call terminated handler
            this.voip.onCallTerminated = this.onCallTerminated.bind(this);
        });
    }

    /**
     * Initialize VoIP client
     */
    async initializeVoip() {
        try {
            console.log('🔧 VoIP Systray Debug: Initializing VoIP...');
            const initialized = await this.voip.initialize();
            if (initialized) {
                const config = this.voip.getConfig();
                console.log('🔧 VoIP Systray Debug: Config loaded', config);
                const voipClient = new VoipSipClient(config, this.voip);
                await voipClient.initialize();
                
                this.voip.setVoipClient(voipClient);
                this.state.isInitialized = true;
                console.log('🔧 VoIP Systray Debug: VoIP initialized successfully');
                this.state.isRegistered = voipClient.isClientRegistered();
                console.log('🔧 VoIP Systray Debug: Registration status:', this.state.isRegistered);
                
                // Force UI update
                this.state.isRegistered = true;
                console.log('🔧 VoIP Systray Debug: Force UI update, isRegistered:', this.state.isRegistered);
                
                // Load recording settings
                this.state.canControlRecording = voipClient.config.user.can_control_recording;
                this.state.autoStartRecording = voipClient.config.user.auto_start_recording;
                console.log('🔧 VoIP Systray Debug: Recording settings loaded', {
                    canControl: this.state.canControlRecording,
                    autoStart: this.state.autoStartRecording
                });
                
                // Load recent calls, VoIP users, and hold music
                await this.loadRecentCalls();
                await this.loadVoipUsers();
                await this.loadHoldMusicList();
                
                // this.notification.add('VoIP connected successfully', { type: 'success' });
            }
        } catch (error) {
            console.error('Failed to initialize VoIP:', error);
            
            // Show user-friendly error
            const errorMsg = error.message || 'Failed to initialize VoIP';
            this.notification.add(errorMsg, { type: 'danger' });
            
            // Show HTTPS requirement if applicable
            if (errorMsg.includes('HTTPS') || errorMsg.includes('WebRTC')) {
                this.notification.add(
                    'VoIP requires HTTPS connection. Please access Odoo via HTTPS.',
                    { type: 'warning', sticky: true }
                );
            }
        }
    }

    /**
     * Load recent calls
     */
    async loadRecentCalls() {
        const calls = await this.voip.getCallHistory(5);
        this.state.recentCalls = calls;
    }
    
    /**
     * Load VoIP users list for call transfer (Real-time)
     */
    async loadVoipUsers() {
        try {
            console.log('🔧 Loading VoIP users in real-time...');
            
            // Use rpc directly (imported from @web/core/network/rpc)
            const response = await rpc('/voip/users/list', {});
            console.log('🔧 VoIP users response:', response);
            
            if (response.success) {
                this.state.voipUsers = response.users || [];
                console.log('🔧 VoIP users loaded:', this.state.voipUsers.length);
                console.log('🔧 VoIP users data:', this.state.voipUsers);
                
                // If no users found, show message instead of demo data
                if (this.state.voipUsers.length === 0) {
                    console.log('🔧 No VoIP users found in database');
                    this.state.voipUsers = [];
                }
            } else {
                console.error('🔧 Failed to load VoIP users:', response.error);
                this.state.voipUsers = [];
            }
        } catch (error) {
            console.error('Failed to load VoIP users:', error);
            this.state.voipUsers = [];
        }
    }

    /**
     * Refresh VoIP users list in real-time
     */
    async refreshVoipUsers() {
        try {
            console.log('🔄 Refreshing VoIP users in real-time...');
            
            // Load fresh data from database
            await this.loadVoipUsers();
            
            // Trigger UI update
            this.render();
            
            console.log('✅ VoIP users refreshed successfully');
        } catch (error) {
            console.error('Failed to refresh VoIP users:', error);
        }
    }
    
    /**
     * Auto-refresh users list every 30 seconds
     */
    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        this.refreshInterval = setInterval(async () => {
            if (this.state.showTransferDropdown) {
                console.log('🔄 Auto-refreshing transfer users...');
                await this.refreshVoipUsers();
            }
        }, 30000); // 30 seconds
        
        console.log('✅ Auto-refresh started for transfer users');
    }

    /**
     * Stop auto-refresh
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
            console.log('🛑 Auto-refresh stopped for transfer users');
        }
    }

    /**
     * Handle webhook notifications to update user status
     */
    async handleWebhookNotification(notificationData) {
        try {
            console.log('🔔 Handling webhook notification:', notificationData);
            
            // Extract user information
            const userExtension = notificationData.extension || notificationData.user;
            const userStatus = notificationData.status || notificationData.state;
            const eventType = notificationData.event || notificationData.type;
            
            console.log(`🔔 User: ${userExtension}, Status: ${userStatus}, Event: ${eventType}`);
            
            if (!userExtension) {
                console.warn('🔔 No user extension found in notification');
                return;
            }
            
            // Find user in current list
            const userIndex = this.state.voipUsers.findIndex(user => 
                user.sip_username === userExtension || user.extension === userExtension
            );
            
            if (userIndex === -1) {
                console.warn(`🔔 User not found for extension: ${userExtension}`);
                return;
            }
            
            // Update user status based on event type
            const oldStatus = this.state.voipUsers[userIndex].status;
            let newStatus = oldStatus;
            
            if (eventType === 'call_start' || eventType === 'call_ringing' || eventType === 'call_connected') {
                newStatus = 'busy';
            } else if (eventType === 'call_end' || eventType === 'call_hangup' || eventType === 'call_completed') {
                newStatus = 'available';
            } else if (userStatus) {
                newStatus = userStatus;
            } else if (eventType === 'user_online') {
                newStatus = 'available';
            } else if (eventType === 'user_offline') {
                newStatus = 'offline';
            }
            
            // Update user status if changed
            if (newStatus !== oldStatus) {
                this.state.voipUsers[userIndex].status = newStatus;
                console.log(`🔔 User ${this.state.voipUsers[userIndex].name} status updated: ${oldStatus} → ${newStatus}`);
                
                // Trigger UI update
                this.render();
            } else {
                console.log(`🔔 User ${this.state.voipUsers[userIndex].name} status unchanged: ${oldStatus}`);
            }
            
        } catch (error) {
            console.error('Error handling webhook notification:', error);
        }
    }

    /**
     * Load hold music list
     */
    async loadHoldMusicList() {
        try {
            console.log('🎵 [DEBUG] Loading hold music list...');
            
            // Try RPC first (using imported rpc function)
            try {
                const response = await rpc('/voip/hold_music/list', {});
                console.log('🎵 [DEBUG] RPC response:', response);
                
                if (response.success) {
                    this.state.holdMusicList = response.music_list || [];
                    this.state.holdMusicOptions = response.music_list || [];
                    console.log('🎵 [DEBUG] Hold music loaded via RPC:', this.state.holdMusicList.length, 'items');
                    console.log('🎵 [DEBUG] Music list:', this.state.holdMusicList);
                    return;
                } else {
                    console.warn('🎵 [DEBUG] RPC failed, trying fetch...');
                }
            } catch (rpcError) {
                console.warn('🎵 [DEBUG] RPC error, trying fetch:', rpcError);
            }
            
            // Fallback to fetch
            console.log('🎵 [DEBUG] Trying fetch request...');
            const response = await fetch('/voip/hold_music/list', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('🎵 [DEBUG] Fetch response:', data);
                
                if (data.success) {
                    this.state.holdMusicList = data.music_list || [];
                    this.state.holdMusicOptions = data.music_list || [];
                    console.log('🎵 [DEBUG] Hold music loaded via fetch:', this.state.holdMusicList.length, 'items');
                    console.log('🎵 [DEBUG] Music list:', this.state.holdMusicList);
                } else {
                    console.warn('🎵 [DEBUG] Fetch failed, using default options');
                    console.log('🎵 [DEBUG] Response error:', data.error);
                }
            } else {
                console.warn('🎵 [DEBUG] Fetch request failed:', response.status);
            }
            
        } catch (error) {
            console.error('🎵 [DEBUG] Failed to load hold music:', error);
            console.log('🎵 [DEBUG] Error details:', error.message);
            // Keep default options if both RPC and fetch fail
        }
    }

    /**
     * Toggle dialer visibility
     */
    toggleDialer(ev) {
        console.log('🔧 Toggle Dialer clicked');
        this.state.showDialer = !this.state.showDialer;
        console.log('🔧 showDialer is now:', this.state.showDialer);
    }

    /**
     * Update phone number input
     */
    onPhoneNumberInput(ev) {
        this.state.phoneNumber = ev.target.value;
    }

    /**
     * Add digit to phone number
     */
    addDigit(digit) {
        console.log('🔧 VoIP Systray Debug: ===== ADD DIGIT =====');
        console.log('🔧 VoIP Systray Debug: Adding digit:', digit);
        console.log('🔧 VoIP Systray Debug: Current phone number:', this.state.phoneNumber);
        console.log('🔧 VoIP Systray Debug: In call state:', this.state.inCall);
        console.log('🔧 VoIP Systray Debug: Show dialer:', this.state.showDialer);
        
        // Just add the digit, don't make call
        this.state.phoneNumber += digit;
        
        console.log('🔧 VoIP Systray Debug: New phone number:', this.state.phoneNumber);
        console.log('🔧 VoIP Systray Debug: Phone number length:', this.state.phoneNumber.length);
        console.log('🔧 VoIP Systray Debug: ===== ADD DIGIT END =====');
        
        // Check if this triggers any automatic behavior
        console.log('🔧 VoIP Systray Debug: Checking if any auto-call is triggered...');
    }

    /**
     * Remove last digit
     */
    backspace() {
        this.state.phoneNumber = this.state.phoneNumber.slice(0, -1);
    }

    /**
     * Make a call
     */
    async makeCall() {
        const startTime = Date.now();
        console.log('🔧 VoIP Systray Debug: ===== MAKE CALL =====', new Date().toISOString());
        console.log('🔧 VoIP Systray Debug: Phone number:', this.state.phoneNumber);
        
        if (!this.state.phoneNumber || this.state.phoneNumber.length < 3) {
            this.notification.add('Please enter a valid phone number (at least 3 digits)', { type: 'warning' });
            return;
        }

        try {
            const voipClient = this.voip.getVoipClient();
            console.log('⏱️ Systray: Got VoIP client at:', Date.now() - startTime, 'ms');
            
            // Update UI immediately for better responsiveness
            this.state.inCall = true;
            this.state.callDuration = 0;
            this.state.activeTab = 'active'; // Switch to active call tab
            console.log('⏱️ Systray: UI updated at:', Date.now() - startTime, 'ms');
            
            // Start SIP call immediately (don't wait for Odoo record)
            console.log('🔧 VoIP Systray Debug: Starting SIP call immediately...');
            console.log('⏱️ Systray: Calling voipClient.makeCall at:', Date.now() - startTime, 'ms');
            
            // Start SIP call and wait for session to be created
            const sipCallPromise = voipClient.makeCall(this.state.phoneNumber);
            
            // Wait for SIP call to start, then get SIP Call ID and create Odoo record
            sipCallPromise.then(() => {
                // Get SIP Call ID from voipClient after call is started
                let sipCallId = null;
                if (voipClient.currentSession) {
                    // Try different ways to get SIP Call ID
                    sipCallId = voipClient.sipCallId ||
                               voipClient.currentSession.id ||
                               (voipClient.currentSession.request && voipClient.currentSession.request.callId) ||
                               (voipClient.currentSession.request && voipClient.currentSession.request.message && voipClient.currentSession.request.message.callId) ||
                               null;
                    console.log('🔧 VoIP Systray Debug: SIP Call ID from session:', sipCallId);
                }
                
                // Create Odoo record with SIP Call ID
                console.log('🔧 VoIP Systray Debug: Creating Odoo record with SIP Call ID...');
                this.voip.makeCall(this.state.phoneNumber, sipCallId).then(result => {
                    const odooTime = Date.now() - startTime;
                    if (result && result.call_id) {
                        voipClient.odooCallId = result.call_id;
                        console.log('🔧 VoIP Systray Debug: Odoo call ID stored:', result.call_id);
                        if (result.existing) {
                            console.log('🔧 VoIP Systray Debug: Found existing call record');
                        }
                        console.log('⏱️ Systray: Odoo record created at:', odooTime, 'ms');
                    }
                }).catch(error => {
                    console.error('🔧 VoIP Systray Debug: Failed to create Odoo record:', error);
                });
            }).catch(error => {
                console.error('🔧 VoIP Systray Debug: SIP call failed:', error);
            });
            
            // Wait for SIP call to start
            console.log('⏱️ Systray: Waiting for SIP call to start...');
            await sipCallPromise;
            console.log('⏱️ Systray: SIP call started at:', Date.now() - startTime, 'ms');
            
            this.notification.add('📞 Call initiated', { type: 'success' });
            console.log('⏱️ Systray: TOTAL TIME:', Date.now() - startTime, 'ms');
            
        } catch (error) {
            console.error('🔧 VoIP Systray Debug: Failed to make call:', error);
            
            // Reset state on error
            this.state.inCall = false;
            
            // Show simplified error message
            const errorMessage = error.message || 'Failed to make call. Please check your settings.';
            
            // For busy/unavailable errors, show simple message (busy tone is already playing)
            if (errorMessage.includes('Busy') || errorMessage.includes('Unavailable') || errorMessage.includes('503') || errorMessage.includes('486')) {
                this.notification.add('📵 Number is busy or unavailable', { 
                    type: 'warning',
                    title: 'Call Failed'
                });
            } else if (errorMessage.includes('HTTPS')) {
                this.notification.add(
                    'VoIP calls require a secure HTTPS connection. Please access Odoo via HTTPS.',
                    { type: 'warning', sticky: true }
                );
            } else if (errorMessage.includes('Not Found') || errorMessage.includes('404')) {
                this.notification.add('📵 Invalid phone number or extension', { 
                    type: 'warning',
                    title: 'Call Failed'
                });
            } else if (errorMessage.includes('Timeout') || errorMessage.includes('408')) {
                this.notification.add('📵 No response from server', { 
                    type: 'warning',
                    title: 'Call Failed'
                });
            } else {
                // Generic error
                this.notification.add(`📵 ${errorMessage}`, { 
                    type: 'danger',
                    title: 'Call Failed'
                });
            }
        }
    }

    /**
     * Hang up call
     */
    async hangup() {
        try {
            const voipClient = this.voip.getVoipClient();
            await voipClient.hangup();
            await this.voip.hangupCall();
            
            this.state.inCall = false;
            this.state.callDuration = 0;
            this.state.phoneNumber = "";
            this.state.showTransferList = false; // Reset transfer list
            
            // Reload recent calls
            await this.loadRecentCalls();
            
            // this.notification.add('Call ended', { type: 'info' });
        } catch (error) {
            console.error('Failed to hang up:', error);
        }
    }
    
    /**
     * Toggle transfer list visibility
     */
    toggleTransferList() {
        this.state.showTransferList = !this.state.showTransferList;
        console.log('🔧 Transfer list toggled:', this.state.showTransferList);
    }
    
    /**
     * Transfer call to another user
     */
    async transferCall(targetUser) {
        try {
            console.log('🔧 Transferring call to:', targetUser);
            
            const voipClient = this.voip.getVoipClient();
            if (!voipClient || !voipClient.currentSession) {
                this.notification.add('No active call to transfer', { type: 'warning' });
                return;
            }
            
            // Perform attended/blind transfer to the extension
            await voipClient.transferCall(targetUser.extension);
            
            this.notification.add(`Call transferred to ${targetUser.name} (${targetUser.extension})`, { 
                type: 'success' 
            });
            
            // Close transfer list
            this.state.showTransferList = false;
            
            // End current call UI (transfer completes the call)
            this.state.inCall = false;
            this.state.callDuration = 0;
            this.state.phoneNumber = "";
            
            // Reload recent calls
            await this.loadRecentCalls();
            
        } catch (error) {
            console.error('Failed to transfer call:', error);
            this.notification.add(`❌ Failed to transfer call: ${error.message || 'Unknown error'}`, { 
                type: 'danger' 
            });
        }
    }
    
    /**
     * Switch incoming call tab
     */
    switchIncomingTab(tabName) {
        this.state.incomingActiveTab = tabName;
        console.log('🔧 Switched to incoming tab:', tabName);
    }
    
    /**
     * Switch active call tab
     */
    switchActiveCallTab(tabName) {
        this.state.activeCallTab = tabName;
        console.log('🔧 Switched to active call tab:', tabName);
    }
    
    /**
     * Transfer incoming call to another user
     */
    async transferIncomingCall(targetUser) {
        try {
            console.log('🔧 Transferring incoming call to:', targetUser);
            
            if (!this.currentSession) {
                this.notification.add('No incoming call to transfer', { type: 'warning' });
                return;
            }
            
            // Perform transfer using SIP REFER
            const voipClient = this.voip.getVoipClient();
            await voipClient.transferCall(targetUser.extension);
            
            this.notification.add(`Incoming call transferred to ${targetUser.name} (${targetUser.extension})`, { 
                type: 'success' 
            });
            
            // Clear incoming call state
            this.state.incomingCall = false;
            this.state.incomingCallNumber = "";
            this.state.incomingCallTime = "";
            this.currentSession = null;
            
        } catch (error) {
            console.error('Failed to transfer incoming call:', error);
            this.notification.add(`❌ Failed to transfer call: ${error.message || 'Unknown error'}`, { 
                type: 'danger' 
            });
        }
    }
    
    /**
     * Select hold music
     */
    selectHoldMusic(music) {
        this.state.selectedHoldMusic = music.id;
        this.state.currentHoldMusic = music;
        console.log('🔧 Selected hold music:', music);
    }
    
    /**
     * Toggle hold music playback
     */
    async toggleHoldMusic() {
        try {
            if (!this.state.currentHoldMusic.id) {
                this.notification.add('Please select a hold music first', { type: 'warning' });
                return;
            }
            
            const voipClient = this.voip.getVoipClient();
            if (!voipClient || !this.currentSession) {
                this.notification.add('No active call to put on hold', { type: 'warning' });
                return;
            }
            
            if (this.state.holdMusicPlaying) {
                // Stop hold music
                await voipClient.stopHoldMusic();
                this.state.holdMusicPlaying = false;
                this.notification.add('Hold music stopped', { type: 'info' });
            } else {
                // Start hold music
                await voipClient.startHoldMusic(this.state.currentHoldMusic);
                this.state.holdMusicPlaying = true;
                this.notification.add(`Hold music started: ${this.state.currentHoldMusic.name}`, { type: 'success' });
            }
            
        } catch (error) {
            console.error('Failed to toggle hold music:', error);
            this.notification.add(`❌ Failed to control hold music: ${error.message || 'Unknown error'}`, { 
                type: 'danger' 
            });
        }
    }

    /**
     * Update call duration
     */
    updateCallDuration() {
        setInterval(() => {
            if (this.state.inCall) {
                this.state.callDuration++;
            }
        }, 1000);
    }

    /**
     * Start call timer
     */
    startCallTimer() {
        this.state.callDuration = 0;
        this.state.callStartTime = Date.now();
    }

    /**
     * Handle incoming call
     */
    onIncomingCall(callData) {
        console.log('🔧 VoIP Systray Debug: Incoming call received', callData);
        
        // Check if there's already an active call
        if (this.state.inCall) {
            console.log('🔧 VoIP Systray Debug: Active call in progress, handling incoming call');
            
            // Put current call on hold
            this.holdCurrentCall();
            
            // Set incoming call state
            this.state.incomingCall = true;
            this.state.incomingCallNumber = callData.from;
            this.state.incomingCallTime = new Date().toLocaleTimeString();
            
            // Keep dropdown open and switch to active tab
            this.state.showDialer = true;
            this.state.activeTab = 'active';
            
            // Store the session for later use
            this.currentSession = callData.session;
            
            // Show notification about incoming call during active call
            this.notification.add(`📞 مكالمة واردة من ${callData.from} أثناء المكالمة النشطة`, { 
                type: 'info',
                sticky: true 
            });
            
        } else {
            // No active call, normal incoming call handling
            this.state.incomingCall = true;
            this.state.incomingCallNumber = callData.from;
            this.state.incomingCallTime = new Date().toLocaleTimeString();
            
            // Auto-open dropdown and switch to active tab
            this.state.showDialer = true;
            this.state.activeTab = 'active';
            
            // Store the session for later use
            this.currentSession = callData.session;
            
            // Create Odoo record immediately when call is received (not when answered)
            // This ensures start_time is recorded when call arrives
            const voipClient = this.voip.getVoipClient();
            if (voipClient) {
                const sipCallId = voipClient.sipCallId || null;
                console.log('🔧 VoIP Systray Debug: Creating Odoo record for incoming call (on receive)...');
                
                // Create call record immediately (non-blocking)
                this.voip.makeCall(
                    callData.from || 'Unknown',
                    sipCallId,
                    'inbound',
                    callData.from || 'Unknown'
                ).then(result => {
                    if (result && result.call_id) {
                        voipClient.odooCallId = result.call_id;
                        console.log('🔧 VoIP Systray Debug: Odoo call ID stored on receive:', result.call_id);
                        if (result.existing) {
                            console.log('🔧 VoIP Systray Debug: Found existing call record');
                        }
                    }
                }).catch(error => {
                    console.error('🔧 VoIP Systray Debug: Failed to create Odoo record on receive:', error);
                    // Don't block - we'll try again when answering
                });
            }
        }
        
        console.log('🔧 VoIP Systray Debug: Dropdown opened for incoming call');
    }

    /**
     * Hold current call
     */
    async holdCurrentCall() {
        try {
            console.log('🔧 VoIP Systray Debug: Holding current call');
            
            const voipClient = this.voip.getVoipClient();
            if (voipClient && voipClient.currentSession) {
                await voipClient.holdCall();
                this.state.isOnHold = true;
                console.log('🔧 VoIP Systray Debug: Call put on hold');
            }
        } catch (error) {
            console.error('Failed to hold call:', error);
            this.notification.add('فشل في وضع المكالمة في الانتظار', { type: 'warning' });
        }
    }

    /**
     * Resume call from hold
     */
    async resumeCall() {
        try {
            console.log('🔧 VoIP Systray Debug: Resuming call from hold');
            
            const voipClient = this.voip.getVoipClient();
            if (voipClient && voipClient.currentSession) {
                await voipClient.resumeCall();
                this.state.isOnHold = false;
                console.log('🔧 VoIP Systray Debug: Call resumed from hold');
            }
        } catch (error) {
            console.error('Failed to resume call:', error);
            this.notification.add('فشل في استئناف المكالمة', { type: 'warning' });
        }
    }

    /**
     * Handle call terminated
     */
    onCallTerminated(session) {
        console.log('🔧 VoIP Systray Debug: ===== CALL TERMINATED IN SYSTRAY =====');
        console.log('🔧 VoIP Systray Debug: Session:', session);
        console.log('🔧 VoIP Systray Debug: Current UI state - inCall:', this.state.inCall);
        console.log('🔧 VoIP Systray Debug: Current UI state - incomingCall:', this.state.incomingCall);
        
        // Reset call state but keep dialer open
        this.state.inCall = false;
        this.state.incomingCall = false;
        this.state.phoneNumber = '';
        this.state.callDuration = 0;
        this.state.isRecording = false;
        this.state.isMuted = false;
        this.state.isSpeaker = false;
        
        // Switch to dialer tab
        this.state.activeTab = 'dialer';
        
        // DON'T close dialer - keep it open
        // this.state.showDialer = false;  ← REMOVED
        
        console.log('🔧 VoIP Systray Debug: UI state reset - inCall:', this.state.inCall);
        console.log('🔧 VoIP Systray Debug: Dialer kept open - showDialer:', this.state.showDialer);
        console.log('🔧 VoIP Systray Debug: ===== CALL TERMINATED IN SYSTRAY END =====');
        
        // this.notification.add('📴 Call ended', { type: 'info' });
        
        // Reload recent calls to show the completed call
        this.loadRecentCalls();
    }

    /**
     * Format call duration
     */
    get formattedDuration() {
        const hours = Math.floor(this.state.callDuration / 3600);
        const minutes = Math.floor((this.state.callDuration % 3600) / 60);
        const seconds = this.state.callDuration % 60;
        
        if (hours > 0) {
            return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        } else {
            return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }
    }

    /**
     * Answer incoming call
     */
    async answerCall(session) {
        try {
            console.log('🔧 VoIP Systray Debug: Answering call', session);
            const voipClient = this.voip.getVoipClient();
            
            if (!voipClient) {
                throw new Error('VoIP client not initialized');
            }
            
            // Update UI immediately for better responsiveness
            this.state.inCall = true;
            this.state.incomingCall = false;
            this.state.activeTab = 'active'; // Switch to active call tab
            this.startCallTimer();
            
            // Get SIP Call ID from voipClient (stored in handleIncomingCall)
            let sipCallId = voipClient.sipCallId || null;
            
            // If not stored yet, try to get it from session
            if (!sipCallId && session) {
                try {
                    if (session.request && session.request.message) {
                        sipCallId = session.request.message.getHeader('Call-ID');
                    }
                    if (!sipCallId) {
                        sipCallId = session.id || 
                                   (session.request && session.request.callId) ||
                                   null;
                    }
                } catch (e) {
                    console.warn('Error getting SIP Call ID from session:', e);
                }
            }
            
            console.log('🔧 VoIP Systray Debug: SIP Call ID for incoming call:', sipCallId);
            
            // Record answer time FIRST (immediately when user clicks answer button)
            const answerTime = new Date().toISOString();
            console.log('🔧 VoIP Systray Debug: Answer time recorded (when button clicked):', answerTime);
            
            // Get or create Odoo record (may have been created on call receive)
            let odooCallId = voipClient.odooCallId || null;
            
            // If no Odoo Call ID yet, create record now
            if (!odooCallId) {
                console.log('🔧 VoIP Systray Debug: Creating Odoo record for incoming call (on answer)...');
                try {
                    // For incoming calls, pass 'inbound' direction and from_number
                    const callResult = await this.voip.makeCall(
                        this.state.incomingCallNumber || 'Unknown', 
                        sipCallId,
                        'inbound',
                        this.state.incomingCallNumber || 'Unknown'
                    );
                    if (callResult && callResult.call_id) {
                        odooCallId = callResult.call_id;
                        voipClient.odooCallId = odooCallId;
                        console.log('🔧 VoIP Systray Debug: Odoo call ID stored:', odooCallId);
                        if (callResult.existing) {
                            console.log('🔧 VoIP Systray Debug: Found existing call record');
                        }
                    }
                } catch (error) {
                    console.error('🔧 VoIP Systray Debug: Failed to create Odoo record:', error);
                    // Continue even if record creation fails
                }
            } else {
                console.log('🔧 VoIP Systray Debug: Using existing Odoo call ID:', odooCallId);
            }
            
            // Answer SIP call
            console.log('🔧 VoIP Systray Debug: Answering SIP call...');
            await voipClient.answerCall();
            
            // Update call state to 'in_progress' with answer_time (recorded when button was clicked)
            if (odooCallId) {
                console.log('🔧 VoIP Systray Debug: Updating call state to in_progress with answer_time:', answerTime);
                this.voip.answerCall(odooCallId, answerTime).catch(error => {
                    console.error('🔧 VoIP Systray Debug: Failed to update answer_time:', error);
                });
            }
            
            console.log('🔧 VoIP Systray Debug: Call answered successfully');
            // this.notification.add('✅ Call answered', { type: 'success' });
            
        } catch (error) {
            console.error('🔧 VoIP Systray Debug: Failed to answer call:', error);
            
            // Reset state on error
            this.state.inCall = false;
            this.state.incomingCall = true;
            
            this.notification.add(`❌ Failed to answer call: ${error.message || 'Unknown error'}`, { type: 'danger' });
        }
    }

    /**
     * Decline incoming call
     */
    async declineCall(session) {
        try {
            console.log('🔧 VoIP Systray Debug: Declining call', session);
            const voipClient = this.voip.getVoipClient();
            
            if (!voipClient) {
                throw new Error('VoIP client not initialized');
            }
            
            // Get the Odoo call ID if available, otherwise use SIP Call ID
            let callIdentifier = voipClient.odooCallId || null;
            
            // If no Odoo call ID, try to get SIP Call ID from session or voipClient
            if (!callIdentifier) {
                let sipCallId = voipClient.sipCallId || null;
                
                // Try to get SIP Call ID from session if available
                if (!sipCallId && session) {
                    try {
                        if (session.request && session.request.message) {
                            sipCallId = session.request.message.getHeader('Call-ID');
                        }
                        if (!sipCallId) {
                            sipCallId = session.id || 
                                       (session.request && session.request.callId) ||
                                       null;
                        }
                    } catch (e) {
                        console.warn('🔧 VoIP Systray Debug: Error getting SIP Call ID from session:', e);
                    }
                }
                
                callIdentifier = sipCallId;
                console.log('🔧 VoIP Systray Debug: Using SIP Call ID for declining:', sipCallId);
            } else {
                console.log('🔧 VoIP Systray Debug: Odoo call ID for declining:', callIdentifier);
            }
            
            console.log('🔧 VoIP Systray Debug: Calling reject on client');
            await voipClient.reject();
            
            console.log('🔧 VoIP Systray Debug: Calling rejectCall on service with call identifier:', callIdentifier);
            // Pass the call ID (Odoo ID or SIP Call ID) to rejectCall to ensure the call is marked as missed
            await this.voip.rejectCall('declined', callIdentifier);
            
            console.log('🔧 VoIP Systray Debug: Call declined successfully');
            // Only reset call-related state, keep dialer open
            this.state.inCall = false;
            this.state.incomingCall = false;
            this.state.phoneNumber = '';
            // Don't close the dialer: this.state.showDialer = false;
            
            this.notification.add('❌ Call declined', { type: 'info' });
        } catch (error) {
            console.error('🔧 VoIP Systray Debug: Failed to decline call:', error);
            this.notification.add(`❌ Failed to decline call: ${error.message || 'Unknown error'}`, { type: 'danger' });
        }
    }

    /**
     * Start recording
     */
    async startRecording() {
        try {
            console.log('🔧 VoIP Systray Debug: Starting recording');
            const voipClient = this.voip.getVoipClient();
            
            if (!voipClient) {
                throw new Error('VoIP client not initialized');
            }
            
            await voipClient.startRecording();
            this.state.isRecording = true;
            
            console.log('🔧 VoIP Systray Debug: Recording state updated:', this.state.isRecording);
            this.notification.add('🔴 Recording started', { type: 'info' });
        } catch (error) {
            console.error('🔧 VoIP Systray Debug: Failed to start recording:', error);
            this.notification.add(`❌ Failed to start recording: ${error.message || 'Unknown error'}`, { type: 'danger' });
        }
    }

    /**
     * Stop recording
     */
    async stopRecording() {
        try {
            console.log('🔧 VoIP Systray Debug: Stopping recording');
            const voipClient = this.voip.getVoipClient();
            
            if (!voipClient) {
                throw new Error('VoIP client not initialized');
            }
            
            await voipClient.stopRecording();
            this.state.isRecording = false;
            
            this.notification.add('⏹️ Recording stopped', { type: 'success' });
        } catch (error) {
            console.error('🔧 VoIP Systray Debug: Failed to stop recording:', error);
            this.notification.add(`❌ Failed to stop recording: ${error.message || 'Unknown error'}`, { type: 'danger' });
        }
    }

    /**
     * Call a recent contact
     */
    async callRecent(phoneNumber) {
        this.state.phoneNumber = phoneNumber;
        await this.makeCall();
    }

    /**
     * Open call history
     */
    openCallHistory() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'voip.call',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    /**
     * Open VoIP settings
     */
    openSettings() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'voip.user',
            views: [[false, 'form']],
            target: 'new',
            context: { search_default_my_config: 1 },
        });
    }

    /**
     * Switch active tab
     */
    switchTab(tab) {
        // If there's an active call, don't allow switching to dialer
        if (this.state.inCall && tab === 'dialer') {
            this.notification.add('لا يمكن استخدام الطالب أثناء المكالمة النشطة', { type: 'warning' });
            return;
        }
        
        this.state.activeTab = tab;
        
        if (tab === 'contacts' && this.state.contacts.length === 0) {
            this.loadContacts();
        }
        if (tab === 'active') {
            // Load VoIP users for transfer if not already loaded
            if (this.state.voipUsers.length === 0) {
                this.loadVoipUsers();
            }
            // Load hold music if not already loaded
            if (this.state.holdMusicList.length === 0) {
                this.loadHoldMusicList();
            }
        }
        if (tab === 'history') {
            this.loadRecentCalls();
        }
        
        console.log('🔧 VoIP Systray Debug: Switched to tab:', tab);
    }

    /**
     * Load contacts from Odoo
     */
    async loadContacts() {
        try {
            const contacts = await this.voip.getContacts();
            this.state.contacts = contacts || [];
        } catch (error) {
            console.error('Failed to load contacts:', error);
        }
    }

    /**
     * Filter contacts based on search query
     */
    get filteredContacts() {
        try {
            if (!this.state || !this.state.contacts || !Array.isArray(this.state.contacts)) {
                return [];
            }
            if (!this.state.searchQuery) {
                return this.state.contacts;
            }
            const query = this.state.searchQuery.toLowerCase();
            return this.state.contacts.filter(contact => 
                (contact && contact.name && contact.name.toLowerCase().includes(query)) ||
                (contact && contact.phone && contact.phone.toLowerCase().includes(query))
            );
        } catch (error) {
            console.warn('Error in filteredContacts:', error);
            return [];
        }
    }
    
    get filteredTransferUsers() {
        try {
            if (!this.state || !this.state.voipUsers || !Array.isArray(this.state.voipUsers)) {
                return [];
            }
            if (!this.state.transferSearchQuery) {
                return this.state.voipUsers;
            }
            const query = this.state.transferSearchQuery.toLowerCase();
            return this.state.voipUsers.filter(user => 
                (user && user.name && user.name.toLowerCase().includes(query)) ||
                (user && user.sip_username && user.sip_username.toLowerCase().includes(query)) ||
                (user && user.extension && user.extension.toLowerCase().includes(query)) ||
                (user && user.server_name && user.server_name.toLowerCase().includes(query))
            );
        } catch (error) {
            console.warn('Error in filteredTransferUsers:', error);
            return [];
        }
    }

    /**
     * Call a contact
     */
    async callContact(phoneNumber) {
        this.state.phoneNumber = phoneNumber;
        this.state.activeTab = 'dialer';
        await this.makeCall();
    }

    /**
     * Start dragging the dialer
     */
    startDrag(ev) {
        ev.preventDefault();
        
        // Get current position from DOM if not set
        if (this.state.position.x === null || this.state.position.y === null) {
            const dialerEl = ev.target.closest('.o_voip_phone_container');
            if (dialerEl) {
                const rect = dialerEl.getBoundingClientRect();
                this.state.position.x = rect.left;
                this.state.position.y = rect.top;
            }
        }
        
        this.state.isDragging = true;
        this.dragStartX = ev.clientX - (this.state.position.x || 0);
        this.dragStartY = ev.clientY - (this.state.position.y || 0);
        
        const boundOnDrag = this.onDrag.bind(this);
        const boundStopDrag = this.stopDrag.bind(this);
        
        document.addEventListener('mousemove', boundOnDrag);
        document.addEventListener('mouseup', boundStopDrag);
        
        // Store bound functions for cleanup
        this.boundOnDrag = boundOnDrag;
        this.boundStopDrag = boundStopDrag;
    }

    /**
     * Handle drag movement
     */
    onDrag(ev) {
        if (this.state.isDragging) {
            this.state.position.x = ev.clientX - this.dragStartX;
            this.state.position.y = ev.clientY - this.dragStartY;
        }
    }

    /**
     * Stop dragging
     */
    stopDrag() {
        this.state.isDragging = false;
        
        // Remove event listeners using stored bound functions
        if (this.boundOnDrag) {
            document.removeEventListener('mousemove', this.boundOnDrag);
        }
        if (this.boundStopDrag) {
            document.removeEventListener('mouseup', this.boundStopDrag);
        }
    }

    /**
     * Toggle minimize - Hide/Show entire dialer
     */
    toggleMinimize(ev) {
        console.log('🔧 Close button clicked');
        this.state.showDialer = false;
        console.log('🔧 showDialer is now:', this.state.showDialer);
    }

    /**
     * Get dialer position style
     */
    get dialerStyle() {
        if (this.state.position.x !== null && this.state.position.y !== null) {
            return `position: fixed; left: ${this.state.position.x}px; top: ${this.state.position.y}px; right: auto; transform: none;`;
        }
        return '';
    }

    /**
     * Toggle mute
     */
    async toggleMute() {
        try {
            const voipClient = this.voip.getVoipClient();
            
            if (!voipClient || !voipClient.currentSession) {
                console.error('No active call to mute');
                return;
            }

            const session = voipClient.currentSession;
            const pc = session.sessionDescriptionHandler.peerConnection;
            
            if (pc) {
                // Get local audio tracks
                const senders = pc.getSenders();
                const audioSender = senders.find(sender => sender.track && sender.track.kind === 'audio');
                
                if (audioSender && audioSender.track) {
                    // Toggle mute state
                    this.state.isMuted = !this.state.isMuted;
                    audioSender.track.enabled = !this.state.isMuted;
                    
                    console.log('🔇 Mute toggled:', this.state.isMuted);
                    // this.notification.add(
                    //     this.state.isMuted ? '🔇 Microphone muted' : '🎤 Microphone unmuted',
                    //     { type: 'info' }
                    // );
                }
            }
        } catch (error) {
            console.error('Failed to toggle mute:', error);
            this.notification.add('Failed to toggle mute', { type: 'warning' });
        }
    }

    /**
     * Toggle speaker
     */
    async toggleSpeaker() {
        try {
            this.state.isSpeaker = !this.state.isSpeaker;
            
            // In browser, speaker is default output
            // This is more of a visual indicator
            console.log('🔊 Speaker toggled:', this.state.isSpeaker);
            
            // this.notification.add(
            //     this.state.isSpeaker ? '🔊 Speaker on' : '🔉 Speaker off',
            //     { type: 'info' }
            // );
        } catch (error) {
            console.error('Failed to toggle speaker:', error);
        }
    }

    /**
     * Toggle transfer dropdown
     */
    async toggleTransferDropdown() {
        if (this.state.showTransferDropdown) {
            // Close dropdown and stop auto-refresh
            this.state.showTransferDropdown = false;
            this.state.transferSearchQuery = ''; // Clear search when closing
            this.stopAutoRefresh();
        } else {
            // Open dropdown with real-time data
            await this.openTransferDropdown();
        }
    }

    /**
     * Transfer call to user
     */
        async transferCall(user) {
            try {
                console.log('🔄 Transferring call to:', user);
                console.log('🔄 User data:', {
                    name: user.name,
                    extension: user.extension,
                    sip_username: user.sip_username,
                    id: user.id,
                    has_voip: user.has_voip
                });
                
                const voipClient = this.voip.getVoipClient();
                if (!voipClient) {
                    throw new Error('VoIP client not initialized');
                }

                // Check if there's an active call
                if (!this.state.inCall && !this.state.incomingCall) {
                    throw new Error('No active call to transfer');
                }

                console.log('🔄 Current call state - inCall:', this.state.inCall, 'incomingCall:', this.state.incomingCall);
                console.log('🔄 Current session:', voipClient.currentSession);
                console.log('🔄 Session state:', voipClient.currentSession ? voipClient.currentSession.state : 'No session');

                // Perform professional SIP transfer
                const extension = user.extension || user.sip_username;
                console.log('🔄 Extension to transfer to:', extension);
                
                if (!extension) {
                    console.error('❌ User data:', user);
                    throw new Error('No extension or SIP username found for user');
                }
                
                // Use professional SIP REFER method
                console.log('🔄 About to call voipClient.transferCall...');
                await voipClient.transferCall(extension);
                console.log('🔄 voipClient.transferCall completed');
                
                // Close dropdown
                this.state.showTransferDropdown = false;
                
                this.notification.add(`📞 Call transferred to ${user.name}`, { type: 'success' });
                
            } catch (error) {
                console.error('Failed to transfer call:', error);
                console.error('Transfer error details:', error.message);
                console.error('Transfer error stack:', error.stack);
                this.notification.add(`❌ Failed to transfer call: ${error.message || 'Unknown error'}`, { type: 'danger' });
            }
        }

    /**
     * Open transfer dropdown with real-time data
     */
    async openTransferDropdown() {
        try {
            console.log('🔄 Opening transfer dropdown with real-time data...');
            
            // Initialize search query
            this.state.transferSearchQuery = '';
            
            // Refresh users list in real-time
            await this.refreshVoipUsers();
            
            // Show dropdown
            this.state.showTransferDropdown = true;
            
            // Start auto-refresh
            this.startAutoRefresh();
            
            console.log('✅ Transfer dropdown opened with fresh data');
        } catch (error) {
            console.error('Failed to open transfer dropdown:', error);
            this.notification.add(`❌ Failed to load transfer users: ${error.message || 'Unknown error'}`, { type: 'danger' });
        }
    }

    /**
     * Toggle microphone mute
     */
    async toggleMute() {
        try {
            const voipClient = this.voip.getVoipClient();
            if (!voipClient) {
                throw new Error('VoIP client not initialized');
            }

            if (this.state.isMuted) {
                // Unmute
                voipClient.unmuteMicrophone();
                this.state.isMuted = false;
                this.notification.add('🎤 Microphone unmuted', { type: 'info' });
            } else {
                // Mute
                voipClient.muteMicrophone();
                this.state.isMuted = true;
                this.notification.add('🔇 Microphone muted', { type: 'info' });
            }
            
            console.log('🎤 Mute toggled:', this.state.isMuted);
            
        } catch (error) {
            console.error('❌ Failed to toggle mute:', error);
            this.notification.add(`❌ Failed to toggle mute: ${error.message || 'Unknown error'}`, { type: 'danger' });
        }
    }

    /**
     * Show hold music menu
     */
    async showHoldMusicMenu() {
        this.state.showHoldMusicMenu = true;
        console.log('🎵 Hold music menu opened');
        // Load hold music list when menu is opened
        await this.loadHoldMusicList();
    }

    /**
     * Close hold music menu
     */
    closeHoldMusicMenu() {
        this.state.showHoldMusicMenu = false;
        console.log('🎵 Hold music menu closed');
    }

    /**
     * Select hold music
     */
    selectHoldMusic(musicId) {
        this.state.selectedMusicId = musicId;
        console.log('🎵 Selected hold music:', musicId);
    }

    /**
     * Start hold music
     */
    async startHoldMusic() {
        try {
            console.log('🎵 [DEBUG] Starting hold music from systray...');
            console.log('🎵 [DEBUG] Selected music ID:', this.state.selectedMusicId);
            console.log('🎵 [DEBUG] Hold music playing state:', this.state.holdMusicPlaying);
            
            if (!this.state.selectedMusicId) {
                console.log('🎵 [DEBUG] No music selected, showing warning');
                this.notification.add('Please select a music first', { type: 'warning' });
                return;
            }

            const voipClient = this.voip.getVoipClient();
            console.log('🎵 [DEBUG] VoIP client available:', !!voipClient);
            
            if (!voipClient) {
                throw new Error('VoIP client not initialized');
            }

            // Start hold music (without muting microphone)
            console.log('🎵 [DEBUG] Calling voipClient.startHoldMusicOnly...');
            await voipClient.startHoldMusicOnly(this.state.selectedMusicId);
            
            this.state.holdMusicPlaying = true;
            console.log('🎵 [DEBUG] Hold music playing state set to:', this.state.holdMusicPlaying);
            
            this.notification.add(`🎵 Hold music started: ${this.state.selectedMusicId}`, { type: 'success' });
            
            console.log('🎵 [DEBUG] Hold music started successfully:', this.state.selectedMusicId);
            
        } catch (error) {
            console.error('❌ [DEBUG] Failed to start hold music:', error);
            console.log('❌ [DEBUG] Error details:', error.message);
            this.notification.add(`❌ Failed to start hold music: ${error.message || 'Unknown error'}`, { type: 'danger' });
        }
    }

    /**
     * Stop hold music
     */
    async stopHoldMusic() {
        try {
            const voipClient = this.voip.getVoipClient();
            if (!voipClient) {
                throw new Error('VoIP client not initialized');
            }

            // Stop hold music
            await voipClient.stopHoldMusic();
            
            this.state.holdMusicPlaying = false;
            this.notification.add('🔇 Hold music stopped', { type: 'info' });
            
            console.log('🔇 Hold music stopped');
            
        } catch (error) {
            console.error('❌ Failed to stop hold music:', error);
            this.notification.add(`❌ Failed to stop hold music: ${error.message || 'Unknown error'}`, { type: 'danger' });
        }
    }

    /**
     * Update hold music volume
     */
    updateHoldMusicVolume() {
        const voipClient = this.voip.getVoipClient();
        if (voipClient && voipClient.holdMusicAudio) {
            voipClient.holdMusicAudio.volume = this.state.holdMusicVolume / 100;
        }
        console.log('🔊 Hold music volume updated:', this.state.holdMusicVolume + '%');
    }

    /**
     * Handle search input keyup event for transfer users
     */
    onTransferSearchKeyup(ev) {
        this.state.transferSearchQuery = ev.target.value;
        console.log('🔍 Transfer search query:', this.state.transferSearchQuery);
    }
}

VoipSystray.template = "voip_webrtc_freepbx.VoipSystray";
VoipSystray.props = {};

export const systrayItem = {
    Component: VoipSystray,
};

registry.category("systray").add("voip_webrtc_freepbx.voip_systray", systrayItem, { sequence: 50 });
