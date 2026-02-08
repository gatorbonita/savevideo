from flask import Flask, request, send_file, render_template_string, stream_with_context
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
                        width: 0%; transition: width 0.3s; }
        .progress-percent { position: absolute; width: 100%; text-align: center; 
                          line-height: 30px; font-weight: bold; color: #333; }
        .progress-info { display: flex; justify-content: space-between; margin-top: 8px; 
                        font-size: 13px; color: #666; }
        .progress-eta { color: #667eea; font-weight: bold; }
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
            <div class="progress-info">
                <span id="size">0 / 0 MB</span>
                <span id="eta" class="progress-eta">ETA: --</span>
            </div>
        </div>
        <div id="status" class="status"></div>
    </div>
    <script>
        let startTime;
        function start(type) {
            const url = document.getElementById('url').value.trim();
            if (!url) { show('Enter a URL', 'error'); return; }
            document.querySelectorAll('button').forEach(b => b.disabled = true);
            show('Loading... 15-30 seconds...', 'info');
            document.getElementById('progress').classList.add('show');
            document.getElementById('fill').style.width = '5%';
            document.getElementById('percent').textContent = '5%';
            startTime = Date.now();
            
            const es = new EventSource('/progress?url=' + encodeURIComponent(url) + '&type=' + type);
            es.onmessage = function(e) {
                const d = JSON.parse(e.data);
                if (d.error) { show(d.error, 'error'); es.close(); enable(); return; }
                if (d.complete) {
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
                if (d.progress) {
                    const pct = d.pct || 0;
                    document.getElementById('fill').style.width = pct + '%';
                    document.getElementById('percent').textContent = pct + '%';
                    document.getElementById('size').textContent = formatSize(d.loaded) + ' / ' + formatSize(d.total);
                    if (d.loaded > 0) {
                        const elapsed = (Date.now() - startTime) / 1000;
                        const speed = d.loaded / elapsed;
                        const remain = d.total - d.loaded;
                        document.getElementById('eta').textContent = 'ETA: ' + formatTime(remain / speed);
                    }
                }
            };
            es.onerror = function() { es.close(); enable(); };
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
        function formatTime(s) { if (s < 60) return Math.ceil(s) + 's'; 
            if (s < 3600) return Math.ceil(s/60) + 'm'; return Math.ceil(s/3600) + 'h'; }
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
    return videos[0] if videos else None, vid

def download_with_progress(url, path):
    r = requests.get(url, stream=True, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
    total = int(r.headers.get('content-length', 0))
    loaded = 0
    yield {'type': 'progress', 'pct': 5, 'loaded': 0, 'total': total}
    for chunk in r.iter_content(8192):
        if chunk:
            with open(path, 'wb') as f:
                f.write(chunk)
            loaded += len(chunk)
            pct = int(loaded / total * 100) if total else 0
            yield {'type': 'progress', 'pct': pct, 'loaded': loaded, 'total': total}
    yield {'type': 'progress', 'pct': 60, 'loaded': total, 'total': total}

def extract_audio(vpath, apath):
    proc = subprocess.Popen(
        ['ffmpeg', '-y', '-i', vpath, '-vn', '-acodec', 'libmp3lame', '-q:a', '2', apath],
        stderr=subprocess.PIPE, stdout=subprocess.DEVNULL
    )
    total = None
    while True:
        line = proc.stderr.readline()
        if not line and proc.poll() is not None:
            break
        line = line.decode('utf-8', errors='ignore')
        if 'Duration:' in line:
            m = re.search(r'Duration: (\d+):(\d+):(\d+)', line)
            if m:
                total = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        if 'time=' in line and total:
            m = re.search(r'time= (\d+):(\d+):(\d+)', line)
            if m:
                cur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
                pct = int(cur / total * 100)
                yield {'type': 'progress', 'pct': 70 + pct // 3, 'loaded': cur, 'total': total}
    yield {'type': 'progress', 'pct': 100, 'loaded': 100, 'total': 100}

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/progress')
def progress():
    url = request.args.get('url', '')
    dtype = request.args.get('type', 'video')
    if not url:
        return 'data: {"error":"No URL"}\n\n', 200, {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
    
    u = get_url(url)
    if not u:
        return 'data: {"error":"Invalid URL"}\n\n', 200, {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive'}
    
    def generate():
        try:
            vinfo, vid = find_video(u)
            if not vinfo:
                yield 'data: {"error":"Video not found"}\n\n'
                return
            
            vfile = f'v_{vid}.mp4'
            vpath = os.path.join(DOWNLOAD_FOLDER, vfile)
            
            for p in download_with_progress(vinfo['url'], vpath):
                yield 'data: ' + str(p) + '\n\n'
            
            if dtype == 'audio':
                afile = f'a_{vid}.mp3'
                apath = os.path.join(DOWNLOAD_FOLDER, afile)
                for p in extract_audio(vpath, apath):
                    yield 'data: ' + str(p) + '\n\n'
                if os.path.exists(apath):
                    size = os.path.getsize(apath)
                    yield 'data: {"type":"complete","file":"' + afile + '","size":' + str(size) + '}\n\n'
            else:
                if os.path.exists(vpath):
                    size = os.path.getsize(vpath)
                    yield 'data: {"type":"complete","file":"' + vfile + '","size":' + str(size) + '}\n\n'
        except Exception as e:
            yield 'data: {"error":"' + str(e) + '"}\n\n'
    
    return app.response_class(generate(), mimetype='text/event-stream')

@app.route('/get/<f>')
def get(f):
    fp = os.path.join(DOWNLOAD_FOLDER, f)
    if os.path.exists(fp):
        mt = 'audio/mpeg' if f.endswith('.mp3') else 'video/mp4'
        return send_file(fp, as_attachment=True, attachment_filename=f, mimetype=mt)
    return 'Not found', 404

if __name__ == '__main__':
    p = int(os.environ.get('PORT', 5000))
    print(f'Port {p}')
    app.run(host='0.0.0.0', port=p, debug=False)
