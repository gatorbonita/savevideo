from flask import Flask, request, send_file, render_template_string, Response
import os
import time
import re
import requests
import subprocess
from playwright.sync_api import sync_playwright

app = Flask(__name__)

DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

HTML = '''<!DOCTYPE html>
<html>
<head>
    <title>Douyin Downloader</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
               min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
        .container { background: white; padding: 40px; border-radius: 20px;
                     box-shadow: 0 20px 60px rgba(0,0,0,0.3); width: 100%; max-width: 500px; }
        h1 { text-align: center; color: #333; margin-bottom: 5px; }
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
                        width: 0%; transition: width 0.5s; }
        .progress-percent { position: absolute; width: 100%; text-align: center;
                          line-height: 30px; font-weight: bold; color: #333; }
        .status { margin-top: 15px; padding: 12px; border-radius: 8px; display: none; text-align: center; }
        .status.show { display: block; }
        .status.success { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .status.info { background: #d1ecf1; color: #0c5460; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Douyin Downloader</h1>
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
    </div>
    <script>
        function start(type) {
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

            const es = new EventSource('/progress?url=' + encodeURIComponent(url) + '&type=' + type);
            es.onmessage = function(e) {
                const d = JSON.parse(e.data);
                if (d.error) { 
                    clearInterval(animInterval);
                    show(d.error, 'error'); es.close(); enable(); return; 
                }
                if (d.complete) {
                    clearInterval(animInterval);
                    es.close();
                    fetch('/get/' + d.file).then(r => r.blob()).then(blob => {
                        const a = document.createElement('a');
                        a.href = URL.createObjectURL(blob);
                        a.download = d.file;
                        a.click();
                        show('Done! ' + (type === 'audio' ? 'MP3' : 'MP4') + ' ' + formatSize(d.size), 'success');
                    }).catch(e => show('Download failed', 'error'));
                    enable();
                    return;
                }
                if (d.pct !== undefined) {
                    clearInterval(animInterval);
                    document.getElementById('fill').style.width = d.pct + '%';
                    document.getElementById('percent').textContent = d.pct + '%';
                }
            };
            es.onerror = function() { clearInterval(animInterval); es.close(); enable(); };
        }
        function enable() { document.querySelectorAll('button').forEach(b => b.disabled = false); }
        function show(msg, type) {
            const s = document.getElementById('status');
            s.className = 'status show ' + type;
            s.textContent = msg;
        }
        function formatSize(b) { if (!b) return '0 B'; b = parseInt(b);
            if (b >= 1e6) return (b/1e6).toFixed(1) + ' MB';
            if (b >= 1e3) return Math.round(b/1e3) + ' KB'; return b + ' B'; }
    </script>
</body>
</html>'''

def get_url(t):
    m = re.search(r'https?://[^\s]+douyin\.com[^\s]*', t)
    return m.group(0) if m else None

def find_video(u):
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
        return best, vid
    return None, vid

def download_video(url, path):
    r = requests.get(url, stream=True, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
    with open(path, 'wb') as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)

def extract_audio(vpath, apath):
    subprocess.run(['ffmpeg', '-y', '-i', vpath, '-vn', '-acodec', 'libmp3lame', '-q:a', '2', apath],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/progress')
def progress():
    url = request.args.get('url', '')
    dtype = request.args.get('type', 'video')

    def generate():
        try:
            u = get_url(url)
            if not u:
                yield 'data: {"error":"Invalid URL"}\n\n'
                return

            vinfo, vid = find_video(u)
            if not vinfo:
                yield 'data: {"error":"Video not found"}\n\n'
                return

            yield 'data: {"pct":50}\n\n'

            vfile = f'v_{vid}.mp4'
            vpath = os.path.join(DOWNLOAD_FOLDER, vfile)

            download_video(vinfo['url'], vpath)

            yield 'data: {"pct":60}\n\n'

            if dtype == 'audio':
                afile = f'a_{vid}.mp3'
                apath = os.path.join(DOWNLOAD_FOLDER, afile)
                extract_audio(vpath, apath)
                if os.path.exists(apath):
                    size = os.path.getsize(apath)
                    yield 'data: {"pct":100}\n\n'
                    yield 'data: {"complete":true,"file":"' + afile + '","size":' + str(size) + '}\n\n'
                if os.path.exists(vpath):
                    os.remove(vpath)
            else:
                if os.path.exists(vpath):
                    size = os.path.getsize(vpath)
                    yield 'data: {"pct":100}\n\n'
                    yield 'data: {"complete":true,"file":"' + vfile + '","size":' + str(size) + '}\n\n'
        except Exception as e:
            yield 'data: {"error":"' + str(e) + '"}\n\n'

    return Response(generate(), mimetype='text/event-stream')

@app.route('/get/<f>')
def get(f):
    fp = os.path.join(DOWNLOAD_FOLDER, f)
    if os.path.exists(fp):
        mt = 'audio/mpeg' if f.endswith('.mp3') else 'video/mp4'
        return send_file(fp, as_attachment=True, download_name=f, mimetype=mt)
    return 'Not found', 404

if __name__ == '__main__':
    p = int(os.environ.get('PORT', 5000))
    print(f'Port {p}')
    app.run(host='0.0.0.0', port=p, debug=False)
