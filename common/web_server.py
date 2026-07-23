import os
import json
import secrets
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

from common.config import Config
from common.logger import setup_logger
from common.status_tracker import status_tracker

logger = setup_logger('web_server')

# 保存有效的登录 Token 列表 (简单内存 Session 机制)
VALID_TOKENS = set()

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Emby Scripts 控制台</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 30, 46, 0.7);
            --card-border: rgba(255, 255, 255, 0.08);
            --accent-color: #6366f1;
            --accent-hover: #4f46e5;
            --text-main: #f3f4f6;
            --text-sub: #9ca3af;
            --success-color: #10b981;
            --running-color: #3b82f6;
            --warning-color: #f59e0b;
            --danger-color: #ef4444;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(16, 185, 129, 0.1) 0px, transparent 50%);
            background-attachment: fixed;
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.25rem 2rem;
            background: rgba(15, 23, 42, 0.8);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--card-border);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 1.25rem;
            font-weight: 700;
            background: linear-gradient(135deg, #818cf8 0%, #34d399 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .btn {
            background-color: var(--accent-color);
            color: white;
            border: none;
            padding: 0.6rem 1.2rem;
            border-radius: 0.5rem;
            font-weight: 500;
            font-size: 0.875rem;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s ease;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
        }

        .btn:hover:not(:disabled) {
            background-color: var(--accent-hover);
            transform: translateY(-1px);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            box-shadow: none;
        }

        .btn-outline {
            background: transparent;
            border: 1px solid var(--card-border);
            color: var(--text-sub);
        }

        .btn-outline:hover:not(:disabled) {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
        }

        main {
            flex: 1;
            max-width: 1280px;
            width: 100%;
            margin: 0 auto;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.25rem;
        }

        .card {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 1rem;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
            transition: border-color 0.2s ease;
        }

        .card:hover {
            border-color: rgba(255, 255, 255, 0.15);
        }

        .card-title {
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-sub);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .card-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text-main);
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .status-idle {
            background: rgba(16, 185, 129, 0.15);
            color: var(--success-color);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .status-running {
            background: rgba(59, 130, 246, 0.15);
            color: var(--running-color);
            border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .pulse-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: currentColor;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.2); }
            100% { opacity: 1; transform: scale(1); }
        }

        .logs-section {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 1rem;
            display: flex;
            flex-direction: column;
            height: 550px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
        }

        .logs-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 1.5rem;
            background: rgba(15, 23, 42, 0.6);
            border-bottom: 1px solid var(--card-border);
        }

        .logs-title {
            font-size: 1rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .logs-controls {
            display: flex;
            gap: 0.75rem;
            align-items: center;
        }

        .search-input {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--card-border);
            border-radius: 0.5rem;
            padding: 0.4rem 0.8rem;
            color: white;
            font-size: 0.85rem;
            outline: none;
        }

        .search-input:focus {
            border-color: var(--accent-color);
        }

        .logs-body {
            flex: 1;
            padding: 1.25rem;
            font-family: 'Fira Code', monospace;
            font-size: 0.85rem;
            line-height: 1.6;
            color: #d1d5db;
            background: rgba(5, 8, 15, 0.85);
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }

        /* Modal Auth */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(8px);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 999;
        }

        .modal-card {
            background: #1e293b;
            border: 1px solid var(--card-border);
            border-radius: 1rem;
            padding: 2rem;
            width: 100%;
            max-width: 400px;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
        }

        .modal-title {
            font-size: 1.25rem;
            font-weight: 700;
            text-align: center;
        }

        .input-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .input-group label {
            font-size: 0.875rem;
            color: var(--text-sub);
        }

        .input-group input {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--card-border);
            border-radius: 0.5rem;
            padding: 0.75rem 1rem;
            color: white;
            font-size: 1rem;
            outline: none;
        }

        .input-group input:focus {
            border-color: var(--accent-color);
        }

        .hidden {
            display: none !important;
        }
    </style>
</head>
<body>

    <div id="authModal" class="modal-overlay hidden">
        <div class="modal-card">
            <div class="modal-title">🔐 控制台登录验证</div>
            <div class="input-group">
                <label for="passwordInput">访问密码</label>
                <input type="password" id="passwordInput" placeholder="请输入 WEB_PASSWORD">
            </div>
            <button class="btn" onclick="login()">登录认证</button>
            <div id="authError" style="color: var(--danger-color); font-size: 0.85rem; text-align: center;"></div>
        </div>
    </div>

    <header>
        <div class="logo">
            <span>🎬 Emby Scripts 控制台</span>
        </div>
        <div class="header-actions">
            <button id="triggerBtn" class="btn" onclick="triggerRun()">
                <span>🚀 立即触发运行</span>
            </button>
        </div>
    </header>

    <main>
        <div class="dashboard-grid">
            <div class="card">
                <div class="card-title">运行状态</div>
                <div class="card-value">
                    <span id="statusBadge" class="status-badge status-idle">
                        <span class="pulse-dot"></span>
                        <span id="statusText">IDLE</span>
                    </span>
                </div>
                <div style="font-size: 0.85rem; color: var(--text-sub);" id="currentTaskInfo">当前空闲</div>
            </div>
            <div class="card">
                <div class="card-title">上次运行时间</div>
                <div class="card-value" id="lastRunTime" style="font-size: 1.25rem;">-</div>
            </div>
            <div class="card">
                <div class="card-title">预计下次运行</div>
                <div class="card-value" id="nextRunTime" style="font-size: 1.25rem;">-</div>
            </div>
            <div class="card">
                <div class="card-title">变更更新数</div>
                <div class="card-value" id="updatedItemsCount" style="color: var(--success-color);">0</div>
            </div>
            <div class="card">
                <div class="card-title">无变更跳过数</div>
                <div class="card-value" id="skippedItemsCount" style="color: var(--text-sub);">0</div>
            </div>
        </div>

        <div class="logs-section">
            <div class="logs-header">
                <div class="logs-title">
                    <span>📜 实时系统日志 (logs.log)</span>
                </div>
                <div class="logs-controls">
                    <input type="text" id="logSearch" class="search-input" placeholder="搜索日志..." oninput="filterLogs()">
                    <button class="btn btn-outline" onclick="fetchLogs()">🔄 刷新</button>
                    <button class="btn btn-outline" onclick="scrollToBottom()">⬇ 底部</button>
                </div>
            </div>
            <div class="logs-body" id="logsContainer">加载日志中...</div>
        </div>
    </main>

    <script>
        let authToken = localStorage.getItem('emby_scripts_token') || '';
        let fullLogs = '';

        async function fetchStatus() {
            try {
                const res = await fetch('/api/status', {
                    headers: { 'Authorization': authToken }
                });
                if (res.status === 401) {
                    showAuthModal();
                    return;
                }
                const data = await res.json();
                
                // Update UI Status
                const badge = document.getElementById('statusBadge');
                const text = document.getElementById('statusText');
                const taskInfo = document.getElementById('currentTaskInfo');
                const triggerBtn = document.getElementById('triggerBtn');

                if (data.status === 'RUNNING') {
                    badge.className = 'status-badge status-running';
                    text.innerText = 'RUNNING';
                    taskInfo.innerText = '正在执行: ' + (data.current_task || 'Pipeline');
                    triggerBtn.disabled = true;
                    triggerBtn.innerText = '⌛ 任务运行中...';
                } else {
                    badge.className = 'status-badge status-idle';
                    text.innerText = 'IDLE';
                    taskInfo.innerText = '系统就绪 / 空闲中';
                    triggerBtn.disabled = false;
                    triggerBtn.innerText = '🚀 立即触发运行';
                }

                document.getElementById('lastRunTime').innerText = data.last_run_time || '尚未执行';
                document.getElementById('nextRunTime').innerText = data.next_run_time || '按定时间隔调度';
                document.getElementById('updatedItemsCount').innerText = data.stats.updated_items || 0;
                document.getElementById('skippedItemsCount').innerText = data.stats.skipped_items || 0;

            } catch (err) {
                console.error('Fetch status error:', err);
            }
        }

        async function fetchLogs() {
            try {
                const res = await fetch('/api/logs', {
                    headers: { 'Authorization': authToken }
                });
                if (res.status === 401) return;
                const text = await res.text();
                fullLogs = text;
                filterLogs();
            } catch (err) {
                console.error('Fetch logs error:', err);
            }
        }

        function filterLogs() {
            const query = document.getElementById('logSearch').value.toLowerCase();
            const container = document.getElementById('logsContainer');
            if (!query) {
                container.innerText = fullLogs;
            } else {
                const filtered = fullLogs.split('\n').filter(line => line.toLowerCase().includes(query)).join('\n');
                container.innerText = filtered;
            }
        }

        function scrollToBottom() {
            const container = document.getElementById('logsContainer');
            container.scrollTop = container.scrollHeight;
        }

        async function triggerRun() {
            if (!confirm('确定要立即手动触发运行一次全管道吗？')) return;
            try {
                const res = await fetch('/api/trigger', {
                    method: 'POST',
                    headers: { 'Authorization': authToken }
                });
                const data = await res.json();
                alert(data.message || '触发请求已发送');
                fetchStatus();
                fetchLogs();
            } catch (err) {
                alert('触发失败: ' + err);
            }
        }

        async function login() {
            const pwd = document.getElementById('passwordInput').value;
            const errDiv = document.getElementById('authError');
            errDiv.innerText = '';
            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ password: pwd })
                });
                if (res.ok) {
                    const data = await res.json();
                    authToken = data.token;
                    localStorage.setItem('emby_scripts_token', authToken);
                    document.getElementById('authModal').classList.add('hidden');
                    initDashboard();
                } else {
                    errDiv.innerText = '密码错误，请重试';
                }
            } catch (err) {
                errDiv.innerText = '登录请求错误';
            }
        }

        function showAuthModal() {
            document.getElementById('authModal').classList.remove('hidden');
        }

        function initDashboard() {
            fetchStatus();
            fetchLogs();
            setInterval(fetchStatus, 3000);
            setInterval(fetchLogs, 5000);
        }

        // Init
        fetch('/api/status', { headers: { 'Authorization': authToken } })
            .then(res => {
                if (res.status === 401) {
                    showAuthModal();
                } else {
                    initDashboard();
                }
            });
    </script>
</body>
</html>
"""

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class WebRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text, code=200, content_type='text/plain; charset=utf-8'):
        body = text.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _check_auth(self):
        cfg = Config()
        if not cfg.WEB_PASSWORD:
            return True
        auth_header = self.headers.get('Authorization', '')
        return auth_header in VALID_TOKENS

    def do_GET(self):
        url_path = self.path.split('?')[0]

        if url_path == '/':
            self._send_text(HTML_PAGE, content_type='text/html; charset=utf-8')
            return

        if not self._check_auth():
            self._send_json({'error': 'Unauthorized'}, code=401)
            return

        if url_path == '/api/status':
            self._send_json(status_tracker.to_dict())
        elif url_path == '/api/logs':
            log_file = 'logs.log'
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        recent_lines = ''.join(lines[-1000:])
                        self._send_text(recent_lines)
                except Exception as e:
                    self._send_text(f"Read logs error: {e}", code=500)
            else:
                self._send_text("No logs.log file found yet.")
        else:
            self._send_text("Not Found", code=404)

    def do_POST(self):
        url_path = self.path.split('?')[0]

        if url_path == '/api/login':
            content_length = int(self.headers.get('Content-Length', 0))
            body_data = self.rfile.read(content_length)
            try:
                payload = json.loads(body_data)
                pwd = payload.get('password', '')
                cfg = Config()
                if not cfg.WEB_PASSWORD or pwd == cfg.WEB_PASSWORD:
                    token = secrets.token_hex(16)
                    VALID_TOKENS.add(token)
                    self._send_json({'token': token, 'message': 'Success'})
                else:
                    self._send_json({'error': 'Invalid password'}, code=401)
            except Exception as e:
                self._send_json({'error': str(e)}, code=400)
            return

        if not self._check_auth():
            self._send_json({'error': 'Unauthorized'}, code=401)
            return

        if url_path == '/api/trigger':
            if status_tracker.status == 'RUNNING':
                self._send_json({'message': '任务正在运行中，无法重复触发'}, code=400)
                return

            # 在新后台线程拉起异步管道任务
            from common.pipeline import run_pipeline
            def _async_run():
                cfg = Config()
                try:
                    run_pipeline(cfg)
                except Exception as e:
                    logger.error(f"Manual triggered pipeline error: {e}", exc_info=True)

            t = threading.Thread(target=_async_run, daemon=True)
            t.start()
            self._send_json({'message': '🚀 手动触发管道成功，正在后台运行...'})
        else:
            self._send_text("Not Found", code=404)

def start_web_server(port: int = 3888):
    try:
        server = ThreadingHTTPServer(('0.0.0.0', port), WebRequestHandler)
        logger.info(f"🌐 Web 控制台已启动，监听地址: http://0.0.0.0:{port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Failed to start Web Server on port {port}: {e}")
