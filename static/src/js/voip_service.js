/** @odoo-module **/

import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { voipLogger } from "./voip_logging";

export const voipService = {
    dependencies: ["notification"],
    
    start(env, { notification }) {
        let voipClient = null;
        let currentCall = null;
        let config = null;

        /**
         * Initialize VoIP service and load configuration
         */
        async function initialize() {
            try {
                voipLogger.debug('Initializing...');
                const result = await rpc('/voip/config', {});
                if (result.success) {
                    config = result.config;
                    // Update logger configuration
                    voipLogger.updateConfig(config);
                    voipLogger.debug('Config loaded successfully', config);
                    return true;
                } else {
                    voipLogger.error('Failed to load VoIP config:', result.error);
                    return false;
                }
            } catch (error) {
                voipLogger.error('Error initializing VoIP:', error);
                return false;
            }
        }

        /**
         * Get VoIP configuration
         */
        function getConfig() {
            return config;
        }

        /**
         * Make a call or create call record for incoming call
         */
        async function makeCall(phoneNumber, sipCallId = null, direction = 'outbound', fromNumber = null) {
            if (!voipClient && direction === 'outbound') {
                notification.add('VoIP client not initialized', { type: 'danger' });
                return false;
            }

            try {
                // For inbound calls, from_number is the caller, to_number is the current user
                // For outbound calls, from_number is the current user, to_number is the target
                const callParams = {
                    direction: direction,
                    call_id: sipCallId, // SIP Call ID
                };
                
                if (direction === 'inbound') {
                    callParams['from_number'] = fromNumber || phoneNumber; // Caller number
                    callParams['to_number'] = config.user.username; // Current user
                } else {
                    callParams['from_number'] = fromNumber || config.user.username; // Current user
                    callParams['to_number'] = phoneNumber; // Target number
                }
                
                const result = await rpc('/voip/call/create', callParams);

                if (result.success) {
                    // Set currentCall for both inbound and outbound calls
                    currentCall = result.call_id;
                    return result;
                } else {
                    notification.add(result.error || 'Unknown error', { type: 'danger' });
                    return false;
                }
            } catch (error) {
                voipLogger.error('Error making call:', error);
                notification.add('Failed to make call', { type: 'danger' });
                return false;
            }
        }

        /**
         * Answer incoming call
         */
        async function answerCall(callId, answerTime = null) {
            try {
                // Use provided answerTime (recorded when button was clicked) or current time
                const answerTimeToUse = answerTime || new Date().toISOString();
                const result = await rpc('/voip/call/update', {
                    call_id: callId,
                    state: 'in_progress',
                    answer_time: answerTimeToUse, // Answer time recorded when user clicked answer button
                });

                if (result.success) {
                    currentCall = callId;
                    return true;
                } else {
                    notification.add(result.error || 'Unknown error', { type: 'danger' });
                    return false;
                }
            } catch (error) {
                voipLogger.error('Error answering call:', error);
                return false;
            }
        }

        /**
         * Reject incoming call
         */
        async function rejectCall(reason = 'declined', callId = null) {
            // Use provided callId or currentCall
            let callIdToUse = callId || currentCall;
            
            if (!callIdToUse) {
                // Try to get call ID from voipClient if available
                if (voipClient) {
                    // Try Odoo call ID first
                    callIdToUse = voipClient.odooCallId || null;
                    
                    // If no Odoo call ID, try SIP Call ID
                    if (!callIdToUse) {
                        callIdToUse = voipClient.sipCallId || null;
                    }
                }
                
                if (!callIdToUse) {
                    voipLogger.warn('No call ID available for rejection');
                    return false;
                }
            }

            try {
                // If callIdToUse is not a number, it might be a SIP Call ID
                let updateParams = {
                    hangup_reason: reason,
                };
                
                // Check if it's a number (Odoo call ID) or string (SIP Call ID)
                if (typeof callIdToUse === 'number' || (typeof callIdToUse === 'string' && /^\d+$/.test(callIdToUse))) {
                    updateParams.call_id = parseInt(callIdToUse);
                } else {
                    // It's a SIP Call ID
                    updateParams.sip_call_id = callIdToUse;
                }
                
                updateParams.state = 'missed';
                
                const result = await rpc('/voip/call/update', updateParams);

                if (result.success) {
                    currentCall = null;
                    if (voipClient) {
                        voipClient.odooCallId = null;
                    }
                    return true;
                } else {
                    notification.add(result.error || 'Unknown error', { type: 'danger' });
                    return false;
                }
            } catch (error) {
                voipLogger.error('Error rejecting call:', error);
                return false;
            }
        }

        /**
         * Hang up current call
         */
        async function hangupCall(reason = 'normal', sipCallId = null) {
            if (!currentCall && !sipCallId) {
                return false;
            }

            try {
                const endTime = new Date().toISOString();
                const updateParams = {
                    call_id: currentCall, // Odoo Call ID (integer)
                    sip_call_id: sipCallId, // SIP Call ID (string)
                    state: 'completed',
                    end_time: endTime,
                    hangup_reason: reason,
                };
                
                // If no Odoo Call ID but we have SIP Call ID, use that
                if (!currentCall && sipCallId) {
                    delete updateParams.call_id;
                    updateParams.sip_call_id = sipCallId;
                }
                
                const result = await rpc('/voip/call/update', updateParams);
                
                // SIP Call ID should already be set when creating the call record
                // No need to update it separately here

                if (result.success) {
                    currentCall = null;
                    return true;
                } else {
                    notification.add(result.error || 'Unknown error', { type: 'danger' });
                    return false;
                }
            } catch (error) {
                voipLogger.error('Error hanging up call:', error);
                return false;
            }
        }

        /**
         * Get call history
         */
        async function getCallHistory(limit = 50, offset = 0) {
            try {
                const result = await rpc('/voip/call/list', {
                    limit: limit,
                    offset: offset,
                });

                if (result.success) {
                    return result.calls;
                } else {
                    voipLogger.error('Failed to get call history:', result.error);
                    return [];
                }
            } catch (error) {
                voipLogger.error('Error getting call history:', error);
                return [];
            }
        }

        /**
         * Search for partner by phone number
         */
        async function searchPartner(phoneNumber) {
            try {
                const result = await rpc('/voip/search/partner', {
                    phone: phoneNumber,
                });

                if (result.success) {
                    return result.partner;
                } else {
                    voipLogger.error('Failed to search partner:', result.error);
                    return null;
                }
            } catch (error) {
                voipLogger.error('Error searching partner:', error);
                return null;
            }
        }

        /**
         * Set VoIP client instance
         */
        function setVoipClient(client) {
            voipClient = client;
            voipLogger.debug('Client set', client);
        }

        /**
         * Get VoIP client instance
         */
        function getVoipClient() {
            return voipClient;
        }

        /**
         * Get current call ID
         */
        function getCurrentCall() {
            return currentCall;
        }

        /**
         * Update call duration
         */
        async function updateCallDuration(callId, duration) {
            try {
                const result = await rpc('/voip/call/update_duration', {
                    call_id: callId,
                    duration: duration,
                });

                if (result.success) {
                    voipLogger.debug('Call duration updated successfully');
                    return true;
                } else {
                    voipLogger.error('Failed to update call duration:', result.error);
                    return false;
                }
            } catch (error) {
                voipLogger.error('Error updating call duration:', error);
                return false;
            }
        }

        /**
         * Handle incoming call
         */
        function onIncomingCall(callData) {
            voipLogger.debug('Incoming call received', callData);
            currentCall = callData.session;
            
            // DON'T show system notification - Custom UI will handle it
            // notification.add(`Incoming call from ${callData.from}`, {
            //     type: 'info',
            //     sticky: true,
            //     buttons: [
            //         {
            //             text: 'Answer',
            //             primary: true,
            //             onClick: () => answerCall(callData.session)
            //         },
            //         {
            //             text: 'Decline',
            //             onClick: () => hangupCall('declined')
            //         }
            //     ]
            // });
        }

        /**
         * Get contacts list
         * Uses fetch() for type='http' endpoint (supports POST/GET, VOIP/FreePBX integration, CURL)
         */
        async function getContacts(limit = 100) {
            try {
                // Use fetch for type='http' endpoint (not JSON-RPC)
                const response = await fetch('/voip/contacts/list', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ limit: limit }),
                    credentials: 'same-origin', // Include cookies for authentication
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const result = await response.json();

                // Handle structured response with success flag
                if (result && result.success === true) {
                    return result.contacts || [];
                } else {
                    voipLogger.error('Failed to get contacts:', result.error || 'Unknown error');
                    return [];
                }
            } catch (error) {
                voipLogger.error('Error getting contacts:', error);
                return [];
            }
        }

        /**
         * Handle webhook notifications
         */
        async function handleWebhookNotification(notificationData) {
            try {
                console.log('🔔 VoIP Service: Handling webhook notification:', notificationData);
                
                // Send to SIP client if available
                if (window.voipSipClient && window.voipSipClient.handleWebhookNotification) {
                    await window.voipSipClient.handleWebhookNotification(notificationData);
                }
                
                // Send to systray if available
                if (window.voipSystray && window.voipSystray.handleWebhookNotification) {
                    await window.voipSystray.handleWebhookNotification(notificationData);
                }
                
            } catch (error) {
                console.error('VoIP Service: Error handling webhook notification:', error);
            }
        }

        /**
         * Update SIP Call ID in Odoo call record
         */
        async function updateCallSipId(callId, sipCallId) {
            try {
                const result = await rpc('/voip/call/update', {
                    call_id: callId, // Odoo Call ID (integer)
                    sip_call_id: sipCallId, // SIP Call ID (string) - this will update the call_id field in DB
                });

                if (result.success) {
                    return true;
                } else {
                    voipLogger.warn('Failed to update SIP Call ID:', result.error);
                    return false;
                }
            } catch (error) {
                voipLogger.error('Error updating SIP Call ID:', error);
                return false;
            }
        }

        return {
            initialize,
            getConfig,
            makeCall,
            answerCall,
            rejectCall,
            hangupCall,
            getCallHistory,
            searchPartner,
            getContacts,
            setVoipClient,
            getVoipClient,
            getCurrentCall,
            updateCallDuration,
            onIncomingCall,
            handleWebhookNotification,
            updateCallSipId,
        };
    },
};

registry.category("services").add("voip", voipService);
