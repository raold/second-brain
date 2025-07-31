// Second Brain v2.0 - Application JavaScript

// === Constants ===
const API_BASE = '/api/v2';

// === State Management ===
const AppState = {
    activeTab: 'git',
    connectionStatus: 'connected',
    metrics: {
        tests: 430,
        patterns: 24,
        todos: [],
        commits: []
    }
};

// === DOM Elements ===
const elements = {
    connectionStatus: document.getElementById('connection-status'),
    testCount: document.getElementById('test-count'),
    patternCount: document.getElementById('pattern-count'),
    dropzone: document.getElementById('dropzone'),
    fileInput: document.getElementById('file-input'),
    activityList: document.getElementById('activity-list'),
    viewAllButton: document.getElementById('view-all'),
    tabButtons: document.querySelectorAll('.tab-button'),
    tabPanels: document.querySelectorAll('.tab-panel'),
    gitTimeline: document.getElementById('git-timeline'),
    commitList: document.getElementById('commit-list'),
    todoList: document.getElementById('todo-list')
};

// === Initialize Application ===
function init() {
    setupEventListeners();
    initializeDropzone();
    updateMetrics();
    loadGitActivity();
    loadTodos();
    setupWebSocket();
}

// === Event Listeners ===
function setupEventListeners() {
    // Tab switching
    elements.tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            switchTab(tabName);
        });
    });

    // View all button
    elements.viewAllButton.addEventListener('click', () => {
        switchTab('git');
    });

    // Dropzone click to upload
    elements.dropzone.addEventListener('click', () => {
        elements.fileInput.click();
    });

    // File input change
    elements.fileInput.addEventListener('change', handleFileSelect);
}

// === Tab Management ===
function switchTab(tabName) {
    // Update state
    AppState.activeTab = tabName;

    // Update tab buttons
    elements.tabButtons.forEach(button => {
        button.classList.toggle('active', button.dataset.tab === tabName);
    });

    // Update tab panels
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === `${tabName}-tab`);
    });

    // Load tab-specific data
    switch(tabName) {
        case 'git':
            loadGitActivity();
            break;
        case 'todo':
            loadTodos();
            break;
        case 'api':
            loadAPIHealth();
            break;
        case 'docs':
            // Documentation is static
            break;
    }
}

// === Dropzone Functionality ===
function initializeDropzone() {
    const dropzone = elements.dropzone;

    // Drag events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight on drag
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, () => {
            dropzone.classList.remove('drag-over');
        });
    });

    // Handle drop
    dropzone.addEventListener('drop', handleDrop);
}

function handleDrop(e) {
    const files = e.dataTransfer.files;
    handleFiles(files);
}

function handleFileSelect(e) {
    const files = e.target.files;
    handleFiles(files);
}

async function handleFiles(files) {
    for (const file of files) {
        await uploadFile(file);
    }
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE}/memories/ingest`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const result = await response.json();
            showNotification('File uploaded successfully', 'success');
            updateMetrics();
        } else {
            showNotification('Upload failed', 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showNotification('Upload error', 'error');
    }
}

// === Data Loading ===
async function updateMetrics() {
    try {
        const response = await fetch(`${API_BASE}/metrics`);
        if (response.ok) {
            const data = await response.json();
            
            // Update test count
            if (data.tests !== undefined) {
                elements.testCount.textContent = data.tests;
                animateValue(elements.testCount, AppState.metrics.tests, data.tests);
                AppState.metrics.tests = data.tests;
            }
            
            // Update pattern count
            if (data.patterns !== undefined) {
                animateValue(elements.patternCount, AppState.metrics.patterns, data.patterns);
                AppState.metrics.patterns = data.patterns;
            }
        }
    } catch (error) {
        console.error('Failed to load metrics:', error);
    }
}

async function loadGitActivity() {
    try {
        const response = await fetch(`${API_BASE}/git/activity`);
        if (response.ok) {
            const data = await response.json();
            renderGitTimeline(data.timeline);
            renderCommitList(data.commits);
        }
    } catch (error) {
        console.error('Failed to load git activity:', error);
    }
}

async function loadTodos() {
    try {
        const response = await fetch(`${API_BASE}/todos`);
        if (response.ok) {
            const data = await response.json();
            renderTodoList(data.todos);
            updateTodoProgress(data.progress);
        }
    } catch (error) {
        console.error('Failed to load todos:', error);
    }
}

async function loadAPIHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            const data = await response.json();
            updateHealthMetrics(data);
        }
    } catch (error) {
        console.error('Failed to load API health:', error);
    }
}

// === Rendering Functions ===
function renderGitTimeline(timeline) {
    const container = elements.gitTimeline;
    container.innerHTML = '';
    
    // Create timeline points
    timeline.forEach((point, index) => {
        const node = document.createElement('div');
        node.className = 'timeline-node';
        node.style.left = `${(index / (timeline.length - 1)) * 100}%`;
        
        const dot = document.createElement('div');
        dot.className = 'timeline-dot';
        
        const label = document.createElement('div');
        label.className = 'timeline-label';
        label.textContent = point.label;
        
        node.appendChild(dot);
        node.appendChild(label);
        container.appendChild(node);
    });
}

function renderCommitList(commits) {
    const container = elements.commitList;
    container.innerHTML = '';
    
    commits.forEach(commit => {
        const item = document.createElement('div');
        item.className = 'commit-item';
        item.innerHTML = `
            <span class="commit-hash">${commit.hash.substring(0, 7)}</span>
            <span class="commit-message">${commit.message}</span>
            <span class="commit-time">${formatTime(commit.timestamp)}</span>
        `;
        container.appendChild(item);
    });
}

function renderTodoList(todos) {
    const container = elements.todoList;
    container.innerHTML = '';
    
    todos.forEach(todo => {
        const item = document.createElement('div');
        item.className = `todo-item ${todo.status}`;
        item.innerHTML = `
            <input type="checkbox" ${todo.status === 'completed' ? 'checked' : ''}>
            <span class="todo-text">${todo.content}</span>
            <span class="todo-priority ${todo.priority}">${todo.priority}</span>
        `;
        container.appendChild(item);
    });
}

function updateTodoProgress(progress) {
    const progressFill = document.querySelector('.todo-container .progress-fill');
    const progressText = document.querySelector('.todo-container .progress-text');
    
    if (progressFill) {
        progressFill.style.width = `${progress}%`;
    }
    if (progressText) {
        progressText.textContent = `${progress}%`;
    }
}

function updateHealthMetrics(health) {
    // Update each metric bar
    const metrics = {
        uptime: health.uptime || 99.9,
        responseTime: health.responseTime || 0.2,
        memoryUsage: health.memoryUsage || 42
    };
    
    Object.entries(metrics).forEach(([key, value]) => {
        const metricElement = document.querySelector(`[data-metric="${key}"]`);
        if (metricElement) {
            const fill = metricElement.querySelector('.metric-fill');
            const text = metricElement.querySelector('.metric-percent');
            
            if (fill) {
                fill.style.width = `${value}%`;
            }
            if (text) {
                text.textContent = key === 'responseTime' ? `${value}s` : `${value}%`;
            }
        }
    });
}

// === WebSocket Connection ===
function setupWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/v2/ws`);
    
    ws.onopen = () => {
        updateConnectionStatus('connected');
    };
    
    ws.onclose = () => {
        updateConnectionStatus('disconnected');
        // Attempt reconnection after 5 seconds
        setTimeout(setupWebSocket, 5000);
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleRealtimeUpdate(data);
    };
}

function updateConnectionStatus(status) {
    AppState.connectionStatus = status;
    const statusElement = elements.connectionStatus;
    const statusDot = statusElement.querySelector('.status-dot');
    const statusText = statusElement.querySelector('.status-text');
    
    if (status === 'connected') {
        statusDot.style.backgroundColor = 'var(--color-success)';
        statusText.textContent = 'Connected';
    } else {
        statusDot.style.backgroundColor = 'var(--color-error)';
        statusText.textContent = 'Disconnected';
    }
}

function handleRealtimeUpdate(data) {
    switch(data.type) {
        case 'metrics_update':
            updateMetrics();
            break;
        case 'new_activity':
            addActivityItem(data.activity);
            break;
        case 'git_update':
            if (AppState.activeTab === 'git') {
                loadGitActivity();
            }
            break;
    }
}

// === Utility Functions ===
function animateValue(element, start, end, duration = 500) {
    const range = end - start;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const easeOutQuart = 1 - Math.pow(1 - progress, 4);
        const current = Math.round(start + (range * easeOutQuart));
        
        element.textContent = current;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

function addActivityItem(activity) {
    const list = elements.activityList;
    const item = document.createElement('div');
    item.className = 'activity-item';
    item.innerHTML = `
        <span class="activity-indicator"></span>
        <span class="activity-text">${activity.text}</span>
        <span class="activity-time">${formatTime(activity.timestamp)}</span>
    `;
    
    // Add to beginning of list
    list.insertBefore(item, list.firstChild);
    
    // Remove last item if list is too long
    if (list.children.length > 5) {
        list.removeChild(list.lastChild);
    }
    
    // Animate in
    item.style.opacity = '0';
    item.style.transform = 'translateY(-10px)';
    requestAnimationFrame(() => {
        item.style.transition = 'all 300ms ease-out';
        item.style.opacity = '1';
        item.style.transform = 'translateY(0)';
    });
}

function formatTime(timestamp) {
    const now = Date.now();
    const diff = now - new Date(timestamp).getTime();
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 60) return `${minutes}m`;
    if (hours < 24) return `${hours}h`;
    return `${days}d`;
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    // Add to body
    document.body.appendChild(notification);
    
    // Animate in
    requestAnimationFrame(() => {
        notification.style.transform = 'translateY(0)';
        notification.style.opacity = '1';
    });
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.transform = 'translateY(-100%)';
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// === Initialize on DOM ready ===
document.addEventListener('DOMContentLoaded', init);