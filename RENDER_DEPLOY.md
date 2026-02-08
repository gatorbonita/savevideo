# Douyin Video Downloader - Render.com Deployment

## Quick Deploy

1. Push this code to a GitHub repository
2. Go to [render.com](https://render.com) and sign in
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Configure the service:
   - **Name**: douyin-downloader (or your preferred name)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free

## Environment Variables

Set these in Render Dashboard → Environment:
- `PORT`: 10000 (Render assigns this automatically)

## Requirements

Create `requirements.txt`:
```
flask>=2.0
playwright>=1.40
requests>=2.28
gunicorn>=21.0
```

## Notes

- Playwright browsers will be installed automatically on first run
- The free tier has limited compute and may timeout on slow connections
- Downloads folder is ephemeral on Render's free tier - files are deleted on each deploy
