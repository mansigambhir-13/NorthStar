/* NorthStar Dashboard — SPA logic */

const API = '/api';
let ws = null;
let pdsChart = null;
let leverageChart = null;
let goalsChart = null;

// ── Tab Navigation ──────────────────────────────────────────────────

document.querySelectorAll('.tab-link').forEach(link => {
    link.addEventListener('click', e => {
        e.preventDefault();
        const tab = link.dataset.tab;
        document.querySelectorAll('.tab-link').forEach(l => l.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        link.classList.add('active');
        document.getElementById(`tab-${tab}`).classList.add('active');

        // Load data on tab switch
        if (tab === 'dashboard') loadDashboard();
        else if (tab === 'tasks') loadTasks();
        else if (tab === 'goals') loadGoals();
        else if (tab === 'chat') initChat();
        else if (tab === 'config') loadConfig();
    });
});

// ── API Helpers ─────────────────────────────────────────────────────

async function api(path, opts = {}) {
    const url = `${API}${path}`;
    const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...opts,
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(`${res.status}: ${text}`);
    }
    return res.json();
}

function severityClass(severity) {
    return `severity-${severity || 'green'}`;
}

// ── Dashboard ───────────────────────────────────────────────────────

async function loadDashboard() {
    try {
        const [status, pds, pdsHistory, tasks, decisions] = await Promise.all([
            api('/status'),
            api('/pds'),
            api('/pds/history'),
            api('/tasks'),
            api('/decisions?limit=5'),
        ]);

        // PDS Card
        const score = pds.score || 0;
        const severity = pds.severity || 'green';
        document.getElementById('pds-score').textContent = Math.round(score);
        document.getElementById('pds-score').className = `pds-score ${severityClass(severity)}`;
        document.getElementById('pds-severity').textContent = severity.toUpperCase();
        document.getElementById('pds-severity').className = `pds-severity ${severityClass(severity)}`;
        document.getElementById('pds-diagnosis').textContent = pds.diagnosis || '';

        // Top 5 Priorities
        const topList = document.getElementById('top-priorities');
        const topTasks = (status.top_tasks || []).slice(0, 5);
        topList.innerHTML = topTasks.map(t =>
            `<li><strong>${esc(t.title)}</strong> <small>(leverage: ${Math.round(t.leverage)})</small></li>`
        ).join('');
        if (!topTasks.length) topList.innerHTML = '<li>No tasks found</li>';

        // PDS Trend Chart
        renderPDSTrend(pdsHistory.history || []);

        // Task Leverage Chart
        const allTasks = (tasks.tasks || []).slice(0, 10);
        renderLeverageChart(allTasks);

        // Decisions
        const decList = document.getElementById('decisions-list');
        const decs = decisions.decisions || [];
        decList.innerHTML = decs.map(d =>
            `<p><small>${(d.timestamp || '').slice(0, 19)}</small> ${esc(d.event_type)}: ${esc(d.task_title || d.reason || '')}</p>`
        ).join('') || '<p>No decisions logged.</p>';

        // Load goals for coverage chart
        loadGoalsCoverage();

    } catch (err) {
        console.error('Dashboard load error:', err);
    }
}

function renderPDSTrend(history) {
    const ctx = document.getElementById('pds-chart').getContext('2d');
    if (pdsChart) pdsChart.destroy();

    const labels = history.map(h => {
        const d = new Date(h.calculated_at);
        return `${d.getMonth()+1}/${d.getDate()}`;
    });
    const data = history.map(h => h.score);

    pdsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'PDS',
                data,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59,130,246,0.1)',
                fill: true,
                tension: 0.3,
            }],
        },
        options: {
            responsive: true,
            scales: { y: { beginAtZero: true } },
            plugins: { legend: { display: false } },
        },
    });
}

function renderLeverageChart(tasks) {
    const ctx = document.getElementById('leverage-chart').getContext('2d');
    if (leverageChart) leverageChart.destroy();

    leverageChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: tasks.map(t => t.title ? t.title.slice(0, 25) : ''),
            datasets: [{
                label: 'Leverage',
                data: tasks.map(t => t.leverage_score || 0),
                backgroundColor: 'rgba(59,130,246,0.6)',
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            plugins: { legend: { display: false } },
        },
    });
}

async function loadGoalsCoverage() {
    try {
        const data = await api('/goals');
        const goals = data.goals || [];
        const ctx = document.getElementById('goals-chart').getContext('2d');
        if (goalsChart) goalsChart.destroy();

        if (!goals.length) return;

        const colors = ['#22c55e', '#3b82f6', '#eab308', '#f97316', '#ef4444', '#8b5cf6'];
        goalsChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: goals.map(g => g.title),
                datasets: [{
                    data: goals.map(() => 1),
                    backgroundColor: goals.map((_, i) => colors[i % colors.length]),
                }],
            },
            options: {
                responsive: true,
                plugins: { legend: { position: 'bottom' } },
            },
        });
    } catch (err) {
        console.error('Goals coverage error:', err);
    }
}

// ── Tasks ───────────────────────────────────────────────────────────

async function loadTasks() {
    try {
        const data = await api('/tasks');
        const tasks = data.tasks || [];
        const tbody = document.getElementById('tasks-body');
        tbody.innerHTML = tasks.map(t => `
            <tr>
                <td><span class="status-badge status-${t.status}">${t.status}</span></td>
                <td>${esc(t.title)}</td>
                <td>${Math.round(t.leverage_score || 0)}</td>
                <td>${esc(t.goal_id || '-')}</td>
                <td>${t.impact || '-'}</td>
                <td>${t.effort_hours || '-'}</td>
                <td class="task-actions">
                    <select onchange="updateTaskStatus('${esc(t.id)}', this.value)">
                        <option value="" disabled selected>Change...</option>
                        <option value="pending">Pending</option>
                        <option value="in_progress">In Progress</option>
                        <option value="completed">Completed</option>
                        <option value="deferred">Deferred</option>
                        <option value="cancelled">Cancelled</option>
                    </select>
                </td>
            </tr>
        `).join('');
        if (!tasks.length) tbody.innerHTML = '<tr><td colspan="7">No tasks found. Run analysis first.</td></tr>';
    } catch (err) {
        console.error('Tasks load error:', err);
    }
}

async function updateTaskStatus(taskId, status) {
    try {
        await api(`/tasks/${taskId}`, {
            method: 'PATCH',
            body: JSON.stringify({ status }),
        });
        loadTasks();
    } catch (err) {
        alert(`Failed to update: ${err.message}`);
    }
}

// Add Task dialog
document.getElementById('btn-add-task').addEventListener('click', () => {
    document.getElementById('add-task-dialog').showModal();
});

document.getElementById('add-task-form').addEventListener('submit', async e => {
    e.preventDefault();
    const input = document.getElementById('task-desc-input');
    const desc = input.value.trim();
    if (!desc) return;

    try {
        await api('/tasks', {
            method: 'POST',
            body: JSON.stringify({ description: desc }),
        });
        input.value = '';
        document.getElementById('add-task-dialog').close();
        loadTasks();
    } catch (err) {
        alert(`Failed to add task: ${err.message}`);
    }
});

// ── Goals ───────────────────────────────────────────────────────────

async function loadGoals() {
    try {
        const data = await api('/goals');
        const goals = data.goals || [];
        const container = document.getElementById('goals-list');
        container.innerHTML = goals.map(g => `
            <article class="goal-card">
                <header>${esc(g.title)}</header>
                <p>${esc(g.description || '')}</p>
                <p>Priority: <strong>${g.priority}</strong></p>
                <p>Status: <span class="status-badge status-${g.status === 'active' ? 'in_progress' : 'completed'}">${g.status}</span></p>
                ${g.deadline ? `<p>Deadline: ${g.deadline}</p>` : ''}
            </article>
        `).join('');
        if (!goals.length) container.innerHTML = '<p>No goals found. Initialize the project first.</p>';
    } catch (err) {
        console.error('Goals load error:', err);
    }
}

// ── Chat ────────────────────────────────────────────────────────────

function initChat() {
    if (ws && ws.readyState === WebSocket.OPEN) return;

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws/agent`);

    ws.onopen = () => {
        addChatMessage('agent', 'Connected to NorthStar agent. Ask me anything about your priorities!');
    };
    ws.onclose = () => {
        addChatMessage('error', 'Disconnected from agent.');
        ws = null;
    };
    ws.onerror = () => {
        addChatMessage('error', 'WebSocket connection error.');
    };
    ws.onmessage = e => {
        const data = JSON.parse(e.data);
        if (data.type === 'token') {
            appendToLastAgent(data.content);
        } else if (data.type === 'done') {
            finishAgentMessage();
        } else if (data.type === 'error') {
            addChatMessage('error', data.content);
        }
    };
}

let currentAgentMsg = null;

function addChatMessage(role, text) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;
    div.textContent = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;

    if (role === 'agent') {
        currentAgentMsg = div;
    }
    return div;
}

function appendToLastAgent(text) {
    if (!currentAgentMsg) {
        currentAgentMsg = addChatMessage('agent', '');
    }
    // Remove cursor if present
    const cursor = currentAgentMsg.querySelector('.typing-cursor');
    if (cursor) cursor.remove();

    currentAgentMsg.textContent += text;

    // Add cursor
    const span = document.createElement('span');
    span.className = 'typing-cursor';
    currentAgentMsg.appendChild(span);

    const container = document.getElementById('chat-messages');
    container.scrollTop = container.scrollHeight;
}

function finishAgentMessage() {
    if (currentAgentMsg) {
        const cursor = currentAgentMsg.querySelector('.typing-cursor');
        if (cursor) cursor.remove();
    }
    currentAgentMsg = null;
}

document.getElementById('chat-form').addEventListener('submit', e => {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    sendChatMessage(msg);
    input.value = '';
});

document.querySelectorAll('.quick-actions button').forEach(btn => {
    btn.addEventListener('click', () => {
        const action = btn.dataset.action;
        if (action) sendChatMessage(action);
    });
});

function sendChatMessage(msg) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        initChat();
        setTimeout(() => sendChatMessage(msg), 500);
        return;
    }
    addChatMessage('user', msg);
    currentAgentMsg = null;
    ws.send(JSON.stringify({ message: msg }));
}

// ── Config ──────────────────────────────────────────────────────────

async function loadConfig() {
    try {
        const data = await api('/config');
        document.getElementById('config-display').textContent =
            data.display || JSON.stringify(data.config, null, 2);
    } catch (err) {
        document.getElementById('config-display').textContent = `Error: ${err.message}`;
    }
}

document.getElementById('btn-reload-config').addEventListener('click', loadConfig);

// ── Analyze Button ──────────────────────────────────────────────────

document.getElementById('btn-analyze').addEventListener('click', async () => {
    const btn = document.getElementById('btn-analyze');
    btn.disabled = true;
    btn.innerHTML = 'Analyzing<span class="spinner"></span>';
    try {
        await api('/analyze', { method: 'POST' });
        loadDashboard();
    } catch (err) {
        alert(`Analysis failed: ${err.message}`);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Run Full Analysis';
    }
});

// ── Utility ─────────────────────────────────────────────────────────

function esc(s) {
    if (!s) return '';
    const div = document.createElement('div');
    div.textContent = String(s);
    return div.innerHTML;
}

// ── Init ────────────────────────────────────────────────────────────

loadDashboard();
