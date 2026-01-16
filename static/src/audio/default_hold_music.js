/**
 * Default Hold Music Generator
 * Creates pleasant hold music using Web Audio API
 */

export class DefaultHoldMusicGenerator {
    constructor() {
        this.audioContext = null;
    }
    
    /**
     * Create a pleasant hold music melody
     */
    async createHoldMusic() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            
            const sampleRate = this.audioContext.sampleRate;
            const duration = 30; // 30 seconds
            const buffer = this.audioContext.createBuffer(1, sampleRate * duration, sampleRate);
            const data = buffer.getChannelData(0);
            
            // Create a pleasant melody
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
            }
            
            // Convert to WAV
            const wavBuffer = this.encodeWAV(buffer);
            const base64 = this.arrayBufferToBase64(wavBuffer);
            
            return `data:audio/wav;base64,${base64}`;
            
        } catch (error) {
            console.error('Failed to create hold music:', error);
            throw error;
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
}




