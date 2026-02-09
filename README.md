# Dr. Will's Video & Audio Downloader

A simple web tool to download videos or extract audio from Douyin links.

## Features

- Download videos from Douyin
- Extract audio as MP3
- Clean, simple interface
- Works on desktop and mobile browsers

## Setup

1. Install dependencies:
```bash
pip install flask playwright requests
playwright install chromium
```

2. Make sure FFmpeg is installed (for audio extraction)

3. Run the app:
```bash
python app.py
```

4. Open http://localhost:5000 in your browser

## Usage

1. Paste a Douyin link
2. Click "Download Video" or "Extract Audio"
3. File saves to your browser's default download folder

## Disclaimer

For educational use only. Users must have permission to download any content. We do not support unauthorized distribution of copyrighted material.
