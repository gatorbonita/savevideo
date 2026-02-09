from flask import Flask, request, send_file, render_template_string, Response
import os
import time
import re
import subprocess
from playwright.sync_api import sync_playwright
import urllib.request

app = Flask(__name__)

def get_url(t):
    m = re.search(r'https?://[^\s]+douyin\.com[^\s]*', t)
    return m.group(0) if m else None

def find_video_url(u):
    with sync_playwright() as p:
        page = p.chromium.launch(headless=True).new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
        ).new_page()
        videos = []
        def cb(r):
            ct = r.headers.get('content-type', '')
            cl = r.headers.get('content-length', '0')
            try:
                cl = int(cl)
            except:
                cl = 0
            if 'video' in ct and cl > 100000:
                videos.append({'url': r.url, 'size': cl})
        page.on('response', cb)
        page.goto(u, wait_until='domcontentloaded', timeout=30000)
        vid = page.url.split('/video/')[1].split('?')[0] if '/video/' in page.url else str(int(time.time()))
        page.wait_for_timeout(15000)
    if videos:
        best = max(videos, key=lambda x: x['size'])
        return best['url'], vid
    return None, vid

def extract_audio(vpath, apath):
    subprocess.run(['ffmpeg', '-y', '-i', vpath, '-vn', '-acodec', 'libmp3lame', '-q:a', '2', apath],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>Dr. Will's Video & Audio Downloader</title>
    <link rel="icon" href="/icon" type="image/jpeg">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
               min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .container { background: white; padding: 50px 45px; border-radius: 24px;
                     box-shadow: 0 20px 60px rgba(0,0,0,0.3); width: 100%; max-width: 520px; }
        .logo { text-align: center; margin-bottom: 15px; }
        .logo img { width: 80px; height: 80px; border-radius: 50%; box-shadow: 0 8px 25px rgba(0,0,0,0.2); }
        h1 { text-align: center; color: #333; margin-bottom: 5px; font-size: 22px; }
        .subtitle { text-align: center; color: #888; font-size: 14px; margin-bottom: 25px; }
        input { width: 100%; padding: 15px; border: 2px solid #eee; border-radius: 10px;
                font-size: 15px; margin-bottom: 15px; }
        input:focus { outline: none; border-color: #667eea; }
        .btn-group { display: flex; gap: 10px; margin-bottom: 15px; }
        button { flex: 1; padding: 15px; border: none; border-radius: 10px;
                 font-size: 15px; cursor: pointer; color: white; font-weight: bold; }
        .btn-video { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .btn-audio { background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); }
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(0,0,0,0.2); }
        button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .progress { display: none; margin-top: 20px; }
        .progress.show { display: block; }
        .progress-bar { height: 30px; background: #f0f0f0; border-radius: 15px; overflow: hidden; position: relative; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #667eea, #764ba2);
                        width: 0%; transition: width 0.5s; position: absolute; left: 0; top: 0; border-radius: 15px; }
        .progress-percent { position: absolute; width: 100%; text-align: center;
                          line-height: 30px; font-weight: bold; color: #333; font-size: 13px; z-index: 1; }
        .status { margin-top: 15px; padding: 12px; border-radius: 8px; display: none; text-align: center; }
        .status.show { display: block; }
        .status.success { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .status.info { background: #d1ecf1; color: #0c5460; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; }
        .disclaimer { font-size: 11px; color: #888; line-height: 1.6; }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <img src="/icon" alt="Dr. Will">
        </div>
        <h1>Dr. Will's Video & Audio Downloader</h1>
        <p class="subtitle">Download video or extract audio</p>
        <input type="text" id="url" placeholder="Paste Douyin link...">
        <div class="btn-group">
            <button class="btn-video" onclick="start('video')">Download Video</button>
            <button class="btn-audio" onclick="start('audio')">Extract Audio</button>
        </div>
        <div id="progress" class="progress">
            <div class="progress-bar">
                <div id="fill" class="progress-fill"></div>
                <div id="percent" class="progress-percent">0%</div>
            </div>
        </div>
        <div id="status" class="status"></div>
        <div class="footer">
            <p class="disclaimer"><strong>Disclaimer:</strong> For educational use only. Users must have permission to download any content. We do not support unauthorized distribution of copyrighted material.</p>
        </div>
    </div>
    <script>
        async function start(type) {
            const url = document.getElementById('url').value.trim();
            if (!url) { show('Enter a URL', 'error'); return; }
            document.querySelectorAll('button').forEach(b => b.disabled = true);
            show('Loading... 15-30 seconds...', 'info');
            document.getElementById('progress').classList.add('show');
            
            let pct = 5;
            document.getElementById('fill').style.width = pct + '%';
            document.getElementById('percent').textContent = pct + '%';
            
            let animInterval = setInterval(() => {
                pct += 2;
                if (pct > 45) pct = 45;
                document.getElementById('fill').style.width = pct + '%';
                document.getElementById('percent').textContent = pct + '%';
            }, 500);

            try {
                const response = await fetch('/download?url=' + encodeURIComponent(url) + '&type=' + type);
                const blob = await response.blob();
                clearInterval(animInterval);
                document.getElementById('fill').style.width = '100%';
                document.getElementById('percent').textContent = '100%';
                
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = response.headers.get('filename') || (type === 'audio' ? 'audio.mp3' : 'video.mp4');
                a.click();
                show('Done! Saved to default download folder', 'success');
            } catch (e) {
                clearInterval(animInterval);
                show('Download failed: ' + e.message, 'error');
            }
            enable();
        }
        function enable() { document.querySelectorAll('button').forEach(b => b.disabled = false); }
        function show(msg, type) {
            const s = document.getElementById('status');
            s.className = 'status show ' + type;
            s.textContent = msg;
        }
    </script>
</body>
</html>'''

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/icon')
def icon():
    return send_file('Dr. Will.jfif', mimetype='image/jpeg')

@app.route('/download')
def download():
    url = request.args.get('url', '')
    dtype = request.args.get('type', 'video')
    
    try:
        u = get_url(url)
        if not u:
            return 'Invalid URL', 400
        
        video_url, vid = find_video_url(u)
        if not video_url:
            return 'Video not found', 404
        
        if dtype == 'audio':
            with urllib.request.urlopen(video_url) as r:
                from io import BytesIO
                video_data = BytesIO(r.read())
            
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                tmp.write(video_data.getvalue())
                vpath = tmp.name
            
            apath = vpath.replace('.mp4', '.mp3')
            extract_audio(vpath, apath)
            
            with open(apath, 'rb') as f:
                data = f.read()
            
            os.unlink(vpath)
            os.unlink(apath)
            
            response = Response(data, mimetype='audio/mpeg')
            response.headers['filename'] = f'a_{vid}.mp3'
            return response
        else:
            req = urllib.request.Request(video_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as r:
                data = r.read()
            
            response = Response(data, mimetype='video/mp4')
            response.headers['filename'] = f'v_{vid}.mp4'
            return response
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    p = int(os.environ.get('PORT', 5000))
    print(f'Port {p}')
    app.run(host='0.0.0.0', port=p, debug=False)
