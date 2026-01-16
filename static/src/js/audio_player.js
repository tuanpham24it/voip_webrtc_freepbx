/** @odoo-module **/

import { registry } from '@web/core/registry';
import { UrlField, urlField } from '@web/views/fields/url/url_field';

export class VoipAudioPlayer extends UrlField {
    static template = 'voip_webrtc_freepbx.VoipAudioPlayer';
    
    setup() {
        super.setup();
    }
}

export const voipAudioPlayer = {
    ...urlField,
    component: VoipAudioPlayer,
};

registry.category('fields').add('voip_audio_player', voipAudioPlayer);
