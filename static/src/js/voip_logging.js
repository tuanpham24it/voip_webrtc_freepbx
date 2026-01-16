/** @odoo-module **/

/**
 * VoIP Logging Utility
 * 
 * Provides conditional logging based on server configuration
 * In Test mode, all logging is disabled
 * In Production mode, all logging is enabled
 */

export class VoipLogger {
    constructor(config = null) {
        this.config = config;
        this.loggingEnabled = true;
        this.updateConfig(config);
    }

    /**
     * Update logging configuration
     */
    updateConfig(config) {
        if (config && config.logging) {
            this.config = config;
            this.loggingEnabled = config.logging.enabled;
        }
    }

    /**
     * Check if logging is enabled
     */
    isEnabled() {
        return this.loggingEnabled;
    }

    /**
     * Log debug message
     */
    debug(message, ...args) {
        if (this.isEnabled()) {
            console.log('🔧 VoIP Debug:', message, ...args);
        }
    }

    /**
     * Log info message
     */
    info(message, ...args) {
        if (this.isEnabled()) {
            console.log('🔧 VoIP Info:', message, ...args);
        }
    }

    /**
     * Log warning message
     */
    warn(message, ...args) {
        if (this.isEnabled()) {
            console.warn('⚠️ VoIP Warning:', message, ...args);
        }
    }

    /**
     * Log error message
     */
    error(message, ...args) {
        if (this.isEnabled()) {
            console.error('❌ VoIP Error:', message, ...args);
        }
    }

    /**
     * Log success message
     */
    success(message, ...args) {
        if (this.isEnabled()) {
            console.log('✅ VoIP Success:', message, ...args);
        }
    }

    /**
     * Log call-related message
     */
    call(message, ...args) {
        if (this.isEnabled()) {
            console.log('📞 VoIP Call:', message, ...args);
        }
    }

    /**
     * Log audio-related message
     */
    audio(message, ...args) {
        if (this.isEnabled()) {
            console.log('🔊 VoIP Audio:', message, ...args);
        }
    }

    /**
     * Log connection-related message
     */
    connection(message, ...args) {
        if (this.isEnabled()) {
            console.log('🔌 VoIP Connection:', message, ...args);
        }
    }

    /**
     * Log registration-related message
     */
    registration(message, ...args) {
        if (this.isEnabled()) {
            console.log('📝 VoIP Registration:', message, ...args);
        }
    }

    /**
     * Log recording-related message
     */
    recording(message, ...args) {
        if (this.isEnabled()) {
            console.log('🔴 VoIP Recording:', message, ...args);
        }
    }
}

// Create global instance
export const voipLogger = new VoipLogger();
