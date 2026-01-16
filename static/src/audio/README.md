# Hold Music Audio Files

This directory contains hold music audio files for the VoIP system.

## Supported Formats
- MP3 (.mp3)
- WAV (.wav)
- OGG (.ogg)
- M4A (.m4a)

## Adding Hold Music Files

1. **Upload via Odoo Interface:**
   - Go to VoIP → Hold Music
   - Click "Create" to add new music
   - Upload your audio file
   - Set name, description, and other properties

2. **Add Default Files:**
   - Place audio files in this directory
   - Name them descriptively (e.g., `corporate_hold_music.mp3`)
   - Files will be available as default options

## Default Hold Music

The system will look for a default hold music file named `default_hold_music.mp3` in this directory.
If not found, it will use the first available music from the database.

## File Requirements

- **Duration:** 30 seconds to 5 minutes recommended
- **Quality:** 128kbps or higher
- **Format:** MP3 preferred for compatibility
- **Size:** Keep under 10MB for web performance

## Usage

Hold music is automatically played when:
- A call is put on hold
- The hold music menu is activated during a call
- The system is configured to play hold music

## Troubleshooting

If hold music doesn't play:
1. Check file format compatibility
2. Verify file is not corrupted
3. Check browser audio permissions
4. Ensure file is properly uploaded to Odoo