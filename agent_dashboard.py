"""
Agent Communication Dashboard - Modern Web UI
==========================================
A Flask-based web dashboard for real-time inter-agent communication.

Features:
- Real-time message stream via Server-Sent Events (SSE)
- Modern dark theme UI
- Agent presence indicators
- Message filtering by type/agent
- Toast notifications for new messages

Author: Senior Systems Architect
Version: 1.0 Dashboard
"""

import os
import sys
import json
import time
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify, Response, request

sys.path.insert(0, r'E:\AI-Setup')

app = Flask(__name__)

COORD_DIR = r"E:\AI-Setup\blackboard_data\agent_coordination"
INBOX_DIR = os.path.join(COORD_DIR, "inbox")
STREAM_KEY = "agent_comm:stream"

# ============================================================================
# CONFIGURATION
# ============================================================================

app.config['AGENT_ID'] = None
app.config['LAST_MSG_ID'] = None
app.config['MESSAGES'] = []
app.config['MAX_MESSAGES'] = 100
app.config[' listeners'] = []


def get_my_agent_id():
    """Get this agent's ID"""
    identity_file = os.path.join(COORD_DIR, "state", "identity.json")
    if os.path.exists(identity_file):
        try:
            with open(identity_file, 'r') as f:
                data = json.load(f)
            return data.get("agent_id", "unknown")
        except:
            pass
    return "unknown"


def get_active_agents():
    """Get active agents from state files"""
    agents = []
    state_dir = os.path.join(COORD_DIR, "state")
    
    if not os.path.exists(state_dir):
        return agents
    
    cutoff = datetime.now().timestamp() - 300  # 5 minute timeout
    
    for fname in os.listdir(state_dir):
        if not fname.endswith('.json') or fname == 'identity.json':
            continue
        
        fpath = os.path.join(state_dir, fname)
        try:
            with open(fpath, 'r') as f:
                data = json.load(f)
            
            last_hb = data.get('last_heartbeat', '')
            if last_hb:
                hb_time = datetime.fromisoformat(last_hb).timestamp()
                if hb_time > cutoff:
                    agents.append({
                        'agent_id': data.get('agent_id', 'unknown'),
                        'role': data.get('role', 'unknown'),
                        'status': 'online',
                        'last_seen': last_hb[:19]
                    })
        except:
            pass
    
    return agents


def get_messages_from_redis(limit=50):
    """Get recent messages from Redis stream"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        
        results = r.xrevrange(STREAM_KEY, '+', '-', count=limit)
        
        messages = []
        for msg_id, fields in results or []:
            try:
                msg = json.loads(fields.get("data", "{}"))
                messages.append({
                    'msg_id': msg.get('msg_id', msg_id),
                    'from_agent': msg.get('from_agent', 'unknown'),
                    'to_agent': msg.get('to_agent', 'unknown'),
                    'msg_type': msg.get('msg_type', 'unknown'),
                    'content': msg.get('content', {}),
                    'timestamp': msg.get('timestamp', '')[:19],
                    'priority': msg.get('priority', 1)
                })
            except:
                pass
        
        return messages
    except:
        return []


def get_messages_from_inbox(agent_id, limit=50):
    """Get messages from inbox"""
    inbox_file = os.path.join(INBOX_DIR, agent_id, "inbox.json")
    
    if not os.path.exists(inbox_file):
        return []
    
    try:
        with open(inbox_file, 'r') as f:
            messages = json.load(f)
        
        return [{
            'msg_id': m.get('msg_id', 'unknown'),
            'from_agent': m.get('from_agent', 'unknown'),
            'to_agent': m.get('to_agent', 'unknown'),
            'msg_type': m.get('msg_type', 'unknown'),
            'content': m.get('content', {}),
            'timestamp': m.get('timestamp', '')[:19],
            'priority': m.get('priority', 1)
        } for m in messages[-limit:]]
    except:
        return []


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/status')
def status():
    """Get system status"""
    agent_id = get_my_agent_id()
    agents = get_active_agents()
    
    return jsonify({
        'my_agent_id': agent_id,
        'active_agents': len(agents),
        'agents': agents,
        'redis_connected': check_redis(),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/messages')
def messages():
    """Get recent messages"""
    agent_id = request.args.get('agent_id', get_my_agent_id())
    limit = int(request.args.get('limit', 50))
    
    # Try inbox first
    msgs = get_messages_from_inbox(agent_id, limit)
    
    # If empty, try Redis directly
    if not msgs:
        msgs = get_messages_from_redis(limit)
    
    return jsonify({
        'messages': msgs,
        'count': len(msgs),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/send', methods=['POST'])
def send_message():
    """Send a message"""
    data = request.json
    
    to_agent = data.get('to_agent', 'broadcast')
    msg_type = data.get('msg_type', 'chat')
    content = data.get('content', {})
    
    try:
        from fast_agent_comm import get_fast_comm
        
        comm = get_fast_comm()
        comm.set_agent_id(get_my_agent_id())
        
        if to_agent == 'broadcast':
            msg_id = comm.send_broadcast(msg_type, content)
        else:
            msg_id = comm.send_direct(to_agent, msg_type, content)
        
        return jsonify({'success': True, 'msg_id': msg_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/stream')
def message_stream():
    """Server-Sent Events stream for real-time updates"""
    def generate():
        last_check = time.time()
        
        while True:
            # Check for new messages every second
            if time.time() - last_check > 1:
                messages = get_messages_from_redis(limit=10)
                
                # Filter to only new messages
                new_msgs = []
                for msg in messages:
                    msg_time = msg.get('timestamp', '')
                    if msg_time > app.config.get('last_msg_time', ''):
                        new_msgs.append(msg)
                
                if new_msgs:
                    yield f"data: {json.dumps({'type': 'messages', 'data': new_msgs})}\n\n"
                
                # Check agent status
                agents = get_active_agents()
                yield f"data: {json.dumps({'type': 'agents', 'data': agents})}\n\n"
                
                app.config['last_msg_time'] = datetime.now().isoformat()[:19]
                last_check = time.time()
            
            time.sleep(0.5)
    
    return Response(generate(), mimetype='text/event-stream')


def check_redis():
    """Check Redis connection"""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        return True
    except:
        return False


# ============================================================================
# TEMPLATE
# ============================================================================

def create_template():
    """Create the HTML template"""
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    template_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Communication Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        :root {
            --bg-dark: #0d1117;
            --bg-card: #161b22;
            --bg-hover: #21262d;
            --border: #30363d;
            --text-primary: #f0f6fc;
            --text-secondary: #8b949e;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-orange: #d29922;
            --accent-red: #f85149;
            --accent-purple: #a371f7;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            min-height: 100vh;
        }
        
        .header {
            background: var(--bg-card);
            border-bottom: 1px solid var(--border);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 1.5rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .header h1::before {
            content: '';
            width: 10px;
            height: 10px;
            background: var(--accent-green);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .status-bar {
            display: flex;
            gap: 1.5rem;
            align-items: center;
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            color: var(--text-secondary);
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        
        .status-dot.online { background: var(--accent-green); }
        .status-dot.offline { background: var(--accent-red); }
        
        .main {
            display: grid;
            grid-template-columns: 300px 1fr 350px;
            gap: 1rem;
            padding: 1rem 2rem;
            height: calc(100vh - 70px);
        }
        
        .panel {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .panel-header {
            padding: 1rem;
            border-bottom: 1px solid var(--border);
            font-weight: 600;
            font-size: 0.875rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .panel-content {
            flex: 1;
            overflow-y: auto;
            padding: 0.5rem;
        }
        
        .agent-list {
            list-style: none;
        }
        
        .agent-item {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem;
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.15s;
        }
        
        .agent-item:hover {
            background: var(--bg-hover);
        }
        
        .agent-item.active {
            background: var(--bg-hover);
            border: 1px solid var(--accent-blue);
        }
        
        .agent-avatar {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 0.875rem;
        }
        
        .agent-info {
            flex: 1;
        }
        
        .agent-name {
            font-weight: 500;
            font-size: 0.875rem;
        }
        
        .agent-role {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }
        
        .agent-status {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        
        .agent-status.online { background: var(--accent-green); }
        .agent-status.offline { background: var(--text-secondary); }
        
        .messages-panel {
            display: flex;
            flex-direction: column;
        }
        
        .messages-container {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
        }
        
        .message {
            background: var(--bg-dark);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 0.75rem;
        }
        
        .message-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        
        .message-from {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .message-from .avatar {
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: var(--accent-blue);
            font-size: 0.625rem;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .message-from .name {
            font-weight: 500;
            font-size: 0.875rem;
        }
        
        .message-time {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }
        
        .message-type {
            font-size: 0.625rem;
            padding: 0.125rem 0.5rem;
            border-radius: 3px;
            background: var(--bg-hover);
            color: var(--text-secondary);
            text-transform: uppercase;
        }
        
        .message-type.task { background: var(--accent-orange); color: #000; }
        .message-type.coordinate { background: var(--accent-purple); color: #fff; }
        .message-type.broadcast { background: var(--accent-blue); color: #fff; }
        
        .message-content {
            font-size: 0.875rem;
            line-height: 1.5;
            color: var(--text-secondary);
        }
        
        .message-content pre {
            background: var(--bg-card);
            padding: 0.5rem;
            border-radius: 4px;
            margin-top: 0.5rem;
            overflow-x: auto;
        }
        
        .compose-panel {
            padding: 1rem;
            border-top: 1px solid var(--border);
        }
        
        .compose-input {
            width: 100%;
            background: var(--bg-dark);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 0.75rem;
            color: var(--text-primary);
            font-family: inherit;
            font-size: 0.875rem;
            resize: none;
        }
        
        .compose-input:focus {
            outline: none;
            border-color: var(--accent-blue);
        }
        
        .compose-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.75rem;
        }
        
        .compose-recipient {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }
        
        .btn {
            padding: 0.5rem 1rem;
            border-radius: 6px;
            border: none;
            font-weight: 500;
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.15s;
        }
        
        .btn-primary {
            background: var(--accent-blue);
            color: #fff;
        }
        
        .btn-primary:hover {
            background: #79b8ff;
        }
        
        .btn-secondary {
            background: var(--bg-hover);
            color: var(--text-primary);
        }
        
        .btn-secondary:hover {
            background: var(--border);
        }
        
        .info-panel .panel-content {
            padding: 1rem;
        }
        
        .info-item {
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid var(--border);
        }
        
        .info-item:last-child {
            border-bottom: none;
        }
        
        .info-label {
            color: var(--text-secondary);
            font-size: 0.875rem;
        }
        
        .info-value {
            font-weight: 500;
            font-size: 0.875rem;
        }
        
        .log-container {
            margin-top: 1rem;
        }
        
        .log-entry {
            font-family: 'SF Mono', Monaco, monospace;
            font-size: 0.75rem;
            padding: 0.25rem 0;
            color: var(--text-secondary);
        }
        
        .log-entry.error { color: var(--accent-red); }
        .log-entry.success { color: var(--accent-green); }
        
        .toast-container {
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .toast {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 1rem;
            min-width: 300px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        .toast-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        
        .toast-title {
            font-weight: 600;
            font-size: 0.875rem;
        }
        
        .toast-close {
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 1.25rem;
        }
        
        .toast-content {
            font-size: 0.875rem;
            color: var(--text-secondary);
        }
    </style>
</head>
<body>
    <header class="header">
        <h1>Agent Communication Hub</h1>
        <div class="status-bar">
            <div class="status-item">
                <span class="status-dot" id="redisStatus"></span>
                <span>Redis</span>
            </div>
            <div class="status-item">
                <span class="status-dot online"></span>
                <span id="agentCount">0</span> Agents
            </div>
        </div>
    </header>
    
    <main class="main">
        <aside class="panel">
            <div class="panel-header">Active Agents</div>
            <div class="panel-content">
                <ul class="agent-list" id="agentList">
                    <li class="agent-item">
                        <div class="agent-avatar">?</div>
                        <div class="agent-info">
                            <div class="agent-name">Loading...</div>
                            <div class="agent-role">-</div>
                        </div>
                        <div class="agent-status offline"></div>
                    </li>
                </ul>
            </div>
        </aside>
        
        <section class="panel messages-panel">
            <div class="panel-header">Messages</div>
            <div class="messages-container" id="messageContainer">
                <div class="message">
                    <div class="message-content">Connecting to message stream...</div>
                </div>
            </div>
            <div class="compose-panel">
                <textarea class="compose-input" id="messageInput" rows="2" placeholder="Type a message..."></textarea>
                <div class="compose-actions">
                    <select class="compose-recipient" id="recipientSelect">
                        <option value="broadcast">Broadcast</option>
                    </select>
                    <button class="btn btn-primary" onclick="sendMessage()">Send</button>
                </div>
            </div>
        </section>
        
        <aside class="panel info-panel">
            <div class="panel-header">System Info</div>
            <div class="panel-content">
                <div class="info-item">
                    <span class="info-label">My Agent ID</span>
                    <span class="info-value" id="myAgentId">-</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Stream Length</span>
                    <span class="info-value" id="streamLength">-</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Last Update</span>
                    <span class="info-value" id="lastUpdate">-</span>
                </div>
                
                <div class="log-container" id="logContainer">
                    <div class="log-entry success">System initialized</div>
                </div>
            </div>
        </aside>
    </main>
    
    <div class="toast-container" id="toastContainer"></div>
    
    <script>
        // State
        let agents = [];
        let messages = [];
        
        // Elements
        const agentList = document.getElementById('agentList');
        const messageContainer = document.getElementById('messageContainer');
        const messageInput = document.getElementById('messageInput');
        const recipientSelect = document.getElementById('recipientSelect');
        const myAgentId = document.getElementById('myAgentId');
        const agentCount = document.getElementById('agentCount');
        const redisStatus = document.getElementById('redisStatus');
        const toastContainer = document.getElementById('toastContainer');
        
        // Initialize
        async function init() {
            await loadStatus();
            await loadMessages();
            connectStream();
            setInterval(loadStatus, 5000);
        }
        
        async function loadStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                myAgentId.textContent = data.my_agent_id;
                agentCount.textContent = data.active_agents;
                redisStatus.className = 'status-dot ' + (data.redis_connected ? 'online' : 'offline');
                
                // Update agent list
                agents = data.agents;
                renderAgents();
                
                // Update recipient dropdown
                recipientSelect.innerHTML = '<option value="broadcast">Broadcast</option>';
                agents.forEach(a => {
                    if (a.agent_id !== data.my_agent_id) {
                        recipientSelect.innerHTML += `<option value="${a.agent_id}">${a.role}: ${a.agent_id.slice(-8)}</option>`;
                    }
                });
            } catch (e) {
                log('error', 'Failed to load status: ' + e);
            }
        }
        
        async function loadMessages() {
            try {
                const res = await fetch('/api/messages');
                const data = await res.json();
                messages = data.messages.reverse();
                renderMessages();
                document.getElementById('streamLength').textContent = data.count;
                document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
            } catch (e) {
                log('error', 'Failed to load messages: ' + e);
            }
        }
        
        function renderAgents() {
            agentList.innerHTML = agents.map(a => `
                <li class="agent-item" onclick="selectAgent('${a.agent_id}')">
                    <div class="agent-avatar">${a.role ? a.role[0].toUpperCase() : '?'}</div>
                    <div class="agent-info">
                        <div class="agent-name">${a.agent_id.slice(-8)}</div>
                        <div class="agent-role">${a.role || 'unknown'}</div>
                    </div>
                    <div class="agent-status ${a.status}"></div>
                </li>
            `).join('');
        }
        
        function renderMessages() {
            if (messages.length === 0) {
                messageContainer.innerHTML = '<div class="message"><div class="message-content">No messages yet</div></div>';
                return;
            }
            
            messageContainer.innerHTML = messages.map(m => `
                <div class="message">
                    <div class="message-header">
                        <div class="message-from">
                            <div class="avatar">${(m.from_agent || '?').slice(-2)}</div>
                            <span class="name">${(m.from_agent || 'unknown').slice(-8)}</span>
                            ${m.to_agent !== 'broadcast' ? `→ ${m.to_agent.slice(-8)}` : ''}
                        </div>
                        <div style="display:flex;gap:0.5rem;align-items:center;">
                            <span class="message-type ${m.msg_type}">${m.msg_type}</span>
                            <span class="message-time">${formatTime(m.timestamp)}</span>
                        </div>
                    </div>
                    <div class="message-content">${formatContent(m.content)}</div>
                </div>
            `).join('');
            
            // Scroll to bottom
            messageContainer.scrollTop = messageContainer.scrollHeight;
        }
        
        function formatTime(ts) {
            if (!ts) return '';
            try {
                return new Date(ts).toLocaleTimeString();
            } catch {
                return ts.slice(-8);
            }
        }
        
        function formatContent(content) {
            if (!content) return '';
            if (typeof content === 'string') return content;
            if (content.message) return content.message;
            return JSON.stringify(content, null, 2);
        }
        
        function connectStream() {
            const es = new EventSource('/api/stream');
            
            es.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    
                    if (data.type === 'messages' && data.data.length > 0) {
                        data.data.forEach(msg => {
                            messages.unshift(msg);
                            showToast(msg.msg_type, msg.from_agent.slice(-8), formatContent(msg.content));
                        });
                        messages = messages.slice(0, 50);
                        renderMessages();
                    }
                    
                    if (data.type === 'agents') {
                        agents = data.data;
                        renderAgents();
                        agentCount.textContent = agents.length;
                    }
                } catch (e) {
                    console.error('Stream parse error:', e);
                }
            };
            
            es.onerror = () => {
                log('error', 'Stream connection lost, reconnecting...');
                setTimeout(connectStream, 3000);
            };
        }
        
        async function sendMessage() {
            const content = messageInput.value.trim();
            if (!content) return;
            
            const toAgent = recipientSelect.value;
            const msgType = 'chat';
            
            try {
                const res = await fetch('/api/send', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        to_agent: toAgent,
                        msg_type: msgType,
                        content: { message: content }
                    })
                });
                
                const result = await res.json();
                
                if (result.success) {
                    log('success', 'Message sent: ' + result.msg_id);
                    messageInput.value = '';
                    await loadMessages();
                } else {
                    log('error', 'Send failed: ' + result.error);
                }
            } catch (e) {
                log('error', 'Send error: ' + e);
            }
        }
        
        function showToast(type, from, content) {
            const toast = document.createElement('div');
            toast.className = 'toast';
            toast.innerHTML = `
                <div class="toast-header">
                    <span class="toast-title">${type} from ${from}</span>
                    <button class="toast-close" onclick="this.parentElement.parentElement.remove()">×</button>
                </div>
                <div class="toast-content">${content.slice(0, 100)}</div>
            `;
            toastContainer.appendChild(toast);
            
            setTimeout(() => toast.remove(), 5000);
        }
        
        function log(type, msg) {
            const container = document.getElementById('logContainer');
            const entry = document.createElement('div');
            entry.className = 'log-entry ' + type;
            entry.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
            container.appendChild(entry);
            container.scrollTop = container.scrollHeight;
        }
        
        // Enter to send
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        init();
    </script>
</body>
</html>
'''
    
    template_path = os.path.join(template_dir, 'dashboard.html')
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(template_content)
    
    print(f"Template created: {template_path}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Communication Dashboard")
    parser.add_argument('--port', '-p', type=int, default=5050, help='Port to run on')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    
    args = parser.parse_args()
    
    # Create template
    create_template()
    
    print("=" * 50)
    print("Agent Communication Dashboard")
    print("=" * 50)
    print(f"Starting on http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop")
    
    app.run(host=args.host, port=args.port, debug=False, threaded=True)
