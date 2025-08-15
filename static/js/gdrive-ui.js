// Google Drive UI - Interactive JavaScript

class GoogleDriveUI {
    constructor() {
        this.apiBase = '/api/v1/gdrive';
        this.isConnected = false;
        this.selectedFolders = new Set();
        this.syncTasks = new Map();
        
        this.initializeElements();
        this.attachEventListeners();
        this.checkConnectionStatus();
    }
    
    initializeElements() {
        // Main sections
        this.connectionSection = document.getElementById('connectionSection');
        this.fileExplorer = document.getElementById('fileExplorer');
        this.errorBanner = document.getElementById('errorBanner');
        
        // Buttons
        this.connectBtn = document.getElementById('connectBtn');
        this.syncSelectedBtn = document.getElementById('syncSelectedBtn');
        this.errorAction = document.getElementById('errorAction');
        
        // Status elements
        this.connectionStatus = document.getElementById('connectionStatus');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        
        // Stats
        this.totalFiles = document.getElementById('totalFiles');
        this.processedFiles = document.getElementById('processedFiles');
        this.pendingFiles = document.getElementById('pendingFiles');
        
        // Dynamic content
        this.folderTree = document.getElementById('folderTree');
        this.activityList = document.getElementById('activityList');
        this.toastContainer = document.getElementById('toastContainer');
    }
    
    attachEventListeners() {
        this.connectBtn.addEventListener('click', () => this.connectGoogleDrive());
        this.syncSelectedBtn.addEventListener('click', () => this.syncSelectedFolders());
        this.errorAction.addEventListener('click', () => this.reconnect());
    }
    
    async checkConnectionStatus() {
        try {
            const response = await fetch(`${this.apiBase}/status`);
            const status = await response.json();
            
            if (status.connected) {
                this.showConnectedState(status.user_email);
                await this.loadDriveContents();
            } else if (status.requires_reauth) {
                this.showError('Connection to Google Drive has been lost. Please reconnect.');
            }
        } catch (error) {
            console.error('Failed to check connection status:', error);
        }
    }
    
    async connectGoogleDrive() {
        this.connectBtn.disabled = true;
        this.connectBtn.textContent = 'Connecting...';
        
        try {
            const response = await fetch(`${this.apiBase}/connect`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.auth_url) {
                // Redirect to Google OAuth
                window.location.href = data.auth_url;
            }
        } catch (error) {
            this.showToast('Failed to initiate Google Drive connection', 'error');
            this.connectBtn.disabled = false;
            this.connectBtn.textContent = 'Connect Google Drive';
        }
    }
    
    showConnectedState(email) {
        this.isConnected = true;
        
        // Update connection status
        this.connectionStatus.classList.add('connected');
        this.connectionStatus.querySelector('.status-text').textContent = `Connected: ${email}`;
        
        // Show file explorer
        this.connectionSection.classList.add('hidden');
        this.fileExplorer.classList.remove('hidden');
    }
    
    async loadDriveContents() {
        try {
            // Load real files from Google Drive
            const response = await fetch(`${this.apiBase}/files`);
            if (response.ok) {
                const data = await response.json();
                this.renderFileList(data.files);
            } else {
                // Fallback to mock for demo
                const mockFolders = this.createMockFolderStructure();
                this.renderFolderTree(mockFolders);
            }
        } catch (error) {
            this.showToast('Failed to load Drive contents', 'error');
        }
    }
    
    createMockFolderStructure() {
        return [
            {
                id: 'root',
                name: 'My Drive',
                type: 'folder',
                children: [
                    {
                        id: 'docs',
                        name: 'Documents',
                        type: 'folder',
                        children: [
                            { id: 'doc1', name: 'Project Plan.docx', type: 'file' },
                            { id: 'doc2', name: 'Meeting Notes.pdf', type: 'file' }
                        ]
                    },
                    {
                        id: 'projects',
                        name: 'Projects',
                        type: 'folder',
                        children: [
                            {
                                id: 'proj1',
                                name: 'Website Redesign',
                                type: 'folder',
                                children: [
                                    { id: 'file1', name: 'Design Specs.pdf', type: 'file' },
                                    { id: 'file2', name: 'Wireframes.fig', type: 'file' }
                                ]
                            }
                        ]
                    },
                    { id: 'readme', name: 'README.md', type: 'file' }
                ]
            }
        ];
    }
    
    renderFolderTree(folders, container = this.folderTree, level = 0) {
        folders.forEach(item => {
            const itemElement = this.createTreeItem(item, level);
            container.appendChild(itemElement);
            
            if (item.children && item.children.length > 0) {
                const childrenContainer = document.createElement('div');
                childrenContainer.className = 'tree-children';
                childrenContainer.id = `children-${item.id}`;
                container.appendChild(childrenContainer);
                this.renderFolderTree(item.children, childrenContainer, level + 1);
            }
        });
    }
    
    createTreeItem(item, level) {
        const div = document.createElement('div');
        div.className = 'tree-item';
        div.dataset.id = item.id;
        div.dataset.type = item.type;
        
        const label = document.createElement('label');
        label.className = 'tree-label';
        
        if (item.type === 'folder') {
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'tree-checkbox';
            checkbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.selectedFolders.add(item.id);
                } else {
                    this.selectedFolders.delete(item.id);
                }
                this.updateSyncButton();
            });
            label.appendChild(checkbox);
        }
        
        const icon = document.createElement('span');
        icon.className = 'tree-icon';
        icon.innerHTML = item.type === 'folder' ? '📁' : '📄';
        label.appendChild(icon);
        
        const name = document.createElement('span');
        name.className = 'tree-name';
        name.textContent = item.name;
        label.appendChild(name);
        
        div.appendChild(label);
        return div;
    }
    
    updateSyncButton() {
        this.syncSelectedBtn.disabled = this.selectedFolders.size === 0;
        if (this.selectedFolders.size > 0) {
            this.syncSelectedBtn.textContent = `Sync ${this.selectedFolders.size} Folder${this.selectedFolders.size > 1 ? 's' : ''}`;
        } else {
            this.syncSelectedBtn.textContent = 'Sync Selected Folders';
        }
    }
    
    async syncSelectedFolders() {
        if (this.selectedFolders.size === 0) return;
        
        this.syncSelectedBtn.disabled = true;
        this.syncSelectedBtn.textContent = 'Starting sync...';
        
        let totalQueued = 0;
        
        for (const fileId of this.selectedFolders) {
            try {
                const response = await fetch(`${this.apiBase}/sync/file`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        file_id: fileId,
                        process: true
                    })
                });
                
                const result = await response.json();
                if (result.task_id) {
                    this.syncTasks.set(result.task_id, folderId);
                    totalQueued++;
                    this.addActivity(`📁 Folder sync queued`, 'success');
                }
            } catch (error) {
                this.addActivity(`❌ Failed to queue folder sync`, 'error');
            }
        }
        
        if (totalQueued > 0) {
            this.showToast(`✨ ${totalQueued} folder${totalQueued > 1 ? 's' : ''} queued for processing`, 'success');
            this.startProgressTracking();
        }
        
        this.syncSelectedBtn.disabled = false;
        this.updateSyncButton();
    }
    
    startProgressTracking() {
        // Start polling for task status
        this.progressInterval = setInterval(() => {
            this.updateProgress();
        }, 2000);
        
        // Initial progress update
        this.updateProgress();
    }
    
    async updateProgress() {
        let total = 0;
        let completed = 0;
        let pending = 0;
        
        for (const [taskId, folderId] of this.syncTasks) {
            try {
                const response = await fetch(`${this.apiBase}/sync/status/${taskId}?api_key=${this.getApiKey()}`);
                const status = await response.json();
                
                if (status.status === 'completed') {
                    completed++;
                    this.syncTasks.delete(taskId);
                    this.addActivity(`✅ Folder sync completed`, 'success');
                } else if (status.status === 'processing') {
                    // Still processing
                } else if (status.status === 'failed') {
                    this.syncTasks.delete(taskId);
                    this.addActivity(`❌ Folder sync failed`, 'error');
                } else {
                    pending++;
                }
                
                total++;
            } catch (error) {
                console.error('Failed to check task status:', error);
            }
        }
        
        // Update UI
        this.totalFiles.textContent = total;
        this.processedFiles.textContent = completed;
        this.pendingFiles.textContent = pending;
        
        const progress = total > 0 ? (completed / total) * 100 : 0;
        this.progressFill.style.width = `${progress}%`;
        this.progressText.textContent = `${Math.round(progress)}%`;
        
        // Stop tracking when all tasks are done
        if (this.syncTasks.size === 0 && this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }
    
    addActivity(message, type = 'info') {
        const activity = document.createElement('div');
        activity.className = 'activity-item';
        
        const icon = document.createElement('span');
        icon.className = `activity-icon ${type}`;
        icon.innerHTML = type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ';
        
        const text = document.createElement('span');
        text.className = 'activity-text';
        text.textContent = message;
        
        const time = document.createElement('span');
        time.className = 'activity-time';
        time.textContent = new Date().toLocaleTimeString();
        
        activity.appendChild(icon);
        activity.appendChild(text);
        activity.appendChild(time);
        
        // Add to top of list
        this.activityList.insertBefore(activity, this.activityList.firstChild);
        
        // Keep only last 10 activities
        while (this.activityList.children.length > 10) {
            this.activityList.removeChild(this.activityList.lastChild);
        }
    }
    
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = document.createElement('span');
        icon.className = 'toast-icon';
        icon.innerHTML = type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ';
        
        const msg = document.createElement('span');
        msg.className = 'toast-message';
        msg.textContent = message;
        
        const close = document.createElement('button');
        close.className = 'toast-close';
        close.innerHTML = '✕';
        close.onclick = () => toast.remove();
        
        toast.appendChild(icon);
        toast.appendChild(msg);
        toast.appendChild(close);
        
        this.toastContainer.appendChild(toast);
        
        // Auto remove after 5 seconds
        setTimeout(() => toast.remove(), 5000);
    }
    
    showError(message) {
        this.errorBanner.classList.remove('hidden');
        document.getElementById('errorMessage').textContent = message;
    }
    
    async reconnect() {
        this.errorBanner.classList.add('hidden');
        await this.connectGoogleDrive();
    }
    
    renderFileList(files) {
        // Clear and render real files
        this.folderTree.innerHTML = '';
        
        if (!files || files.length === 0) {
            this.folderTree.innerHTML = '<div class="empty-state">No files found. Upload files to your Google Drive to get started.</div>';
            return;
        }
        
        files.forEach(file => {
            const fileItem = this.createFileItem(file);
            this.folderTree.appendChild(fileItem);
        });
    }
    
    createFileItem(file) {
        const div = document.createElement('div');
        div.className = 'tree-item';
        div.dataset.id = file.id;
        
        const label = document.createElement('label');
        label.className = 'tree-label';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'tree-checkbox';
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                this.selectedFolders.add(file.id);
            } else {
                this.selectedFolders.delete(file.id);
            }
            this.updateSyncButton();
        });
        label.appendChild(checkbox);
        
        const icon = document.createElement('span');
        icon.className = 'tree-icon';
        icon.innerHTML = file.mimeType && file.mimeType.includes('folder') ? '📁' : '📄';
        label.appendChild(icon);
        
        const name = document.createElement('span');
        name.className = 'tree-name';
        name.textContent = file.name;
        label.appendChild(name);
        
        const size = document.createElement('span');
        size.className = 'file-size';
        size.textContent = file.size ? `(${(file.size / 1024).toFixed(1)} KB)` : '';
        label.appendChild(size);
        
        div.appendChild(label);
        return div;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new GoogleDriveUI();
});