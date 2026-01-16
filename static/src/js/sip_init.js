/** @odoo-module **/

/**
 * SIP.js Library Loader for Odoo 18
 * 
 * This module ensures SIP.js UMD library is loaded and available on window.SIP.
 * Since Odoo 18 uses ES6 modules, UMD libraries need special handling.
 * 
 * Strategy: Dynamically load sip.min.js as a script tag if it's not available on window.SIP.
 */

let sipLoadPromise = null;

/**
 * Load SIP.js library dynamically if not already available
 */
function loadSipLibrary() {
    // Return existing promise if already loading
    if (sipLoadPromise) {
        return sipLoadPromise;
    }
    
    // Check if already loaded
    if (typeof window !== 'undefined' && typeof window.SIP !== 'undefined') {
        return Promise.resolve(window.SIP);
    }
    
    // Create promise to load library
    sipLoadPromise = new Promise((resolve, reject) => {
        // Check if already available (loaded via script tag or other means)
        if (typeof window !== 'undefined' && typeof window.SIP !== 'undefined') {
            resolve(window.SIP);
            return;
        }
        
        // Get the module URL - construct from document location or existing scripts
        let sipUrl;
        
        // Try to find asset base URL from existing scripts
        const scripts = document.querySelectorAll('script[src]');
        let baseUrl = window.location.origin;
        
        // Find base URL from existing Odoo asset scripts
        for (let script of scripts) {
            const src = script.src;
            if (src.includes('/assets/')) {
                const assetIndex = src.indexOf('/assets/');
                if (assetIndex > 0) {
                    baseUrl = src.substring(0, assetIndex);
                    // Remove /web if present (it's added by Odoo routing but not needed for static files)
                    if (baseUrl.endsWith('/web')) {
                        baseUrl = baseUrl.substring(0, baseUrl.length - 4);
                    }
                    break;
                }
            }
        }
        
        // Construct SIP.js URL - static files are served directly from module path
        sipUrl = `${baseUrl}/voip_webrtc_freepbx/static/src/js/sip.min.js`;
        
        console.debug('[VoIP] Attempting to load SIP.js from:', sipUrl);
        
        // Load script dynamically
        const script = document.createElement('script');
        script.type = 'text/javascript';
        script.src = sipUrl;
        script.async = false; // Load synchronously to ensure SIP is available
        
        script.onload = () => {
            // Wait a bit for UMD wrapper to execute
            setTimeout(() => {
                if (typeof window.SIP !== 'undefined') {
                    console.debug('[VoIP] SIP.js library loaded successfully via script tag');
                    resolve(window.SIP);
                } else {
                    const error = new Error('SIP.js library loaded but window.SIP is not defined');
                    console.error('[VoIP]', error);
                    reject(error);
                }
            }, 100);
        };
        
        script.onerror = () => {
            const error = new Error(`Failed to load SIP.js from ${sipUrl}`);
            console.error('[VoIP]', error);
            reject(error);
        };
        
        // Add to document head
        document.head.appendChild(script);
    });
    
    return sipLoadPromise;
}

// Export the loader function
export { loadSipLibrary };

// Also try to load immediately (but don't block)
if (typeof window !== 'undefined') {
    // Give UMD wrapper time to execute if already loaded via module
    setTimeout(async () => {
        if (typeof window.SIP === 'undefined') {
            try {
                await loadSipLibrary();
            } catch (error) {
                console.warn('[VoIP] Could not pre-load SIP.js:', error);
            }
        }
    }, 50);
}
