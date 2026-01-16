/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Copy to Clipboard Client Action
 * Used to copy API key to clipboard
 */
function copyToClipboard(env, action) {
    const text = action.params.text;
    const title = action.params.title || "Copied";
    const message = action.params.message || "Text copied to clipboard";
    
    // Use modern Clipboard API
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            env.services.notification.add(message, {
                title: title,
                type: "success",
            });
        }).catch((err) => {
            console.error('Failed to copy text: ', err);
            env.services.notification.add("Failed to copy to clipboard", {
                title: "Error",
                type: "danger",
            });
        });
    } else {
        // Fallback for older browsers
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            const successful = document.execCommand('copy');
            if (successful) {
                env.services.notification.add(message, {
                    title: title,
                    type: "success",
                });
            } else {
                throw new Error('Copy command was unsuccessful');
            }
        } catch (err) {
            console.error('Fallback: Failed to copy', err);
            env.services.notification.add("Failed to copy to clipboard", {
                title: "Error",
                type: "danger",
            });
        }
        
        document.body.removeChild(textArea);
    }
}

registry.category("actions").add("voip_copy_to_clipboard", copyToClipboard);


