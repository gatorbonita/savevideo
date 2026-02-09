# Dr. Will's Downloader - Render.com Deployment

## Quick Deploy

1. Push this code to a GitHub repository
2. Go to [render.com](https://render.com) and sign in
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Configure the service:
   - **Name**: dr-will-downloader
   - **Runtime**: Python 3
   - **Build Command**: See below
   - **Start Command**: `python app.py`
   - **Plan**: Free

## Build Command

Render needs to install Chromium and FFmpeg:

```bash
pip install -r requirements.txt && playwright install chromium
```

For FFmpeg, add this Buildpack:
- Environment → Buildpacks → Add: `https://github.com/matthew-brett/render-buildpack-ffmpeg`

## Environment Variables

Set in Render Dashboard → Environment:
- `PORT`: 5000
- `PYTHON_VERSION`: 3.11

## Requirements.txt

```
flask>=2.0
playwright>=1.40
requests>=2.28
```

## Important Notes

- Free tier spins down after 15 minutes of inactivity
- First request after idle may take 30+ seconds to wake
- Free tier has memory limits - may struggle with Playwright
- Consider upgrading for production use

## Troubleshooting

- **Chromium not found**: Ensure `playwright install chromium` is in build command
- **FFmpeg errors**: Add the FFmpeg buildpack
- **Timeouts**: Free tier may timeout - check Render logs
