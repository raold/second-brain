/**
 * Google Drive Integration JavaScript
 * Handles OAuth flow and Drive connectivity in the dashboard
 */

class GoogleDriveManager {
    constructor() {
        this.apiKey = 'test-token-for-development'; // Dashboard API key
        this.baseUrl = window.location.origin;
        this.isConnecting = false;
        this.retryCount = 0;
        this.maxRetries = 3;
        
        // UI elements
        this.connectButton = null;
        this.statusIndicator = null;
        this.statusText = null;
        this.progressContainer = null;
        
        this.init();
    }
    
    init() {
        // Find or create UI elements
        this.findUIElements();
        this.bindEvents();
        this.checkConnectionStatus();
        
        // Check for OAuth callback parameters
        this.handleOAuthCallback();
    }
    
    findUIElements() {
        // Connect button
        this.connectButton = document.getElementById('gdrive-connect-btn');
        
        // Status elements
        this.statusIndicator = document.getElementById('gdrive-status-indicator');
        this.statusText = document.getElementById('gdrive-status-text');
        this.progressContainer = document.getElementById('gdrive-progress');
        
        // Create elements if they don't exist (for dynamic injection)
        if (!this.connectButton) {
            this.createConnectButton();
        }
    }
    
    createConnectButton() {
        const container = document.getElementById('gdrive-section') || document.body;
        
        const buttonHtml = `
            <div id="gdrive-container" class="gdrive-integration">
                <div class="gdrive-header">
                    <h3>Google Drive Integration</h3>
                    <div id="gdrive-status-indicator" class="status-indicator disconnected"></div>
                </div>
                
                <div id="gdrive-status-text" class="status-text">
                    Not connected to Google Drive
                </div>
                
                <div id="gdrive-progress" class="progress-container" style="display: none;">
                    <div class="progress-bar">
                        <div class="progress-fill"></div>
                    </div>
                    <div class="progress-text">Connecting to Google Drive...</div>
                </div>
                
                <div class="gdrive-actions">
                    <button id="gdrive-connect-btn" class="btn btn-primary">
                        <span class="btn-icon">🔗</span>
                        Connect Google Drive
                    </button>
                    
                    <button id="gdrive-disconnect-btn" class="btn btn-secondary" style="display: none;">
                        <span class="btn-icon">❌</span>
                        Disconnect
                    </button>
                    
                    <button id="gdrive-test-btn" class="btn btn-secondary" style="display: none;">
                        <span class="btn-icon">🧪</span>
                        Test Connection
                    </button>
                </div>
                
                <div id="gdrive-info" class="gdrive-info" style="display: none;">
                    <div class="info-item">
                        <span class="info-label">Connected Account:</span>
                        <span id="gdrive-email" class="info-value">-</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Last Checked:</span>
                        <span id="gdrive-last-checked" class="info-value">-</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Storage Quota:</span>
                        <span id="gdrive-quota" class="info-value">-</span>
                    </div>
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', buttonHtml);
        this.findUIElements();
    }
    
    bindEvents() {
        if (this.connectButton) {
            this.connectButton.addEventListener('click', () => this.initiateConnection());
        }
        
        const disconnectBtn = document.getElementById('gdrive-disconnect-btn');
        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => this.disconnect());
        }
        
        const testBtn = document.getElementById('gdrive-test-btn');
        if (testBtn) {
            testBtn.addEventListener('click', () => this.testConnection());
        }
    }
    
    async initiateConnection() {
        if (this.isConnecting) {
            console.log('Connection already in progress');
            return;
        }
        
        this.isConnecting = true;
        this.showProgress('Initiating Google OAuth...');
        
        try {
            const response = await fetch(`${this.baseUrl}/api/v1/gdrive/connect?api_key=${this.apiKey}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    redirect_after_auth: '/dashboard'
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            console.log('OAuth URL generated:', data.auth_url);
            this.showProgress('Redirecting to Google...');
            
            // Open OAuth URL in same window
            window.location.href = data.auth_url;
            
        } catch (error) {
            console.error('Failed to initiate Google OAuth:', error);
            this.showError(`Connection failed: ${error.message}`);
            this.isConnecting = false;
        }
    }
    
    async checkConnectionStatus() {
        try {
            const response = await fetch(`${this.baseUrl}/api/v1/gdrive/status?api_key=${this.apiKey}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const status = await response.json();
            this.updateUI(status);
            
            console.log('Drive connection status:', status);
            
        } catch (error) {
            console.error('Failed to check Drive status:', error);
            this.updateUI({ 
                connected: false, 
                error: 'Status check failed' 
            });
        }
    }
    
    async disconnect() {
        if (!confirm('Are you sure you want to disconnect Google Drive access?')) {
            return;
        }
        
        this.showProgress('Disconnecting...');
        
        try {
            const response = await fetch(`${this.baseUrl}/api/v1/gdrive/disconnect?api_key=${this.apiKey}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Google Drive disconnected successfully');
                this.updateUI({ connected: false });
            } else {
                this.showError(result.message || 'Disconnect failed');
            }
            
        } catch (error) {
            console.error('Failed to disconnect:', error);
            this.showError(`Disconnect failed: ${error.message}`);
        }
    }
    
    async testConnection() {
        this.showProgress('Testing connection...');
        
        try {
            const response = await fetch(`${this.baseUrl}/api/v1/gdrive/test-connection?api_key=${this.apiKey}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Connection test successful');
                this.updateConnectionInfo(result);
            } else {
                this.showError(result.error || 'Connection test failed');
                
                if (result.requires_reauth) {
                    this.showReconnectOption();
                }
            }
            
        } catch (error) {
            console.error('Connection test failed:', error);
            this.showError(`Test failed: ${error.message}`);
        }
    }
    
    updateUI(status) {
        const isConnected = status.connected;
        
        // Update status indicator
        if (this.statusIndicator) {
            this.statusIndicator.className = `status-indicator ${isConnected ? 'connected' : 'disconnected'}`;
        }
        
        // Update status text
        if (this.statusText) {
            if (isConnected) {
                this.statusText.textContent = `Connected to Google Drive`;
                if (status.user_email) {
                    this.statusText.textContent += ` (${status.user_email})`;
                }
            } else {
                this.statusText.textContent = status.error || 'Not connected to Google Drive';
            }
        }
        
        // Update buttons
        const connectBtn = document.getElementById('gdrive-connect-btn');
        const disconnectBtn = document.getElementById('gdrive-disconnect-btn');
        const testBtn = document.getElementById('gdrive-test-btn');
        
        if (connectBtn) {
            connectBtn.style.display = isConnected ? 'none' : 'inline-block';
            connectBtn.textContent = status.requires_reauth ? 'Reconnect Google Drive' : 'Connect Google Drive';
        }
        
        if (disconnectBtn) {
            disconnectBtn.style.display = isConnected ? 'inline-block' : 'none';
        }
        
        if (testBtn) {
            testBtn.style.display = isConnected ? 'inline-block' : 'none';
        }
        
        // Update info panel
        const infoPanel = document.getElementById('gdrive-info');
        if (infoPanel) {
            infoPanel.style.display = isConnected ? 'block' : 'none';
            
            if (isConnected) {
                this.updateConnectionInfo(status);
            }
        }
        
        this.hideProgress();
    }
    
    updateConnectionInfo(info) {
        const emailEl = document.getElementById('gdrive-email');
        const lastCheckedEl = document.getElementById('gdrive-last-checked');
        const quotaEl = document.getElementById('gdrive-quota');
        
        if (emailEl && info.user_email) {
            emailEl.textContent = info.user_email;
        }
        
        if (lastCheckedEl && info.last_checked) {
            const date = new Date(info.last_checked);
            lastCheckedEl.textContent = date.toLocaleString();
        }
        
        if (quotaEl && info.storage_quota) {
            const quota = info.storage_quota;
            if (quota.limit && quota.usage) {
                const usedGB = Math.round(quota.usage / (1024 * 1024 * 1024));
                const totalGB = Math.round(quota.limit / (1024 * 1024 * 1024));
                quotaEl.textContent = `${usedGB} GB / ${totalGB} GB used`;
            } else {
                quotaEl.textContent = 'Available';
            }
        }
    }
    
    handleOAuthCallback() {
        const urlParams = new URLSearchParams(window.location.search);
        const connected = urlParams.get('connected');
        const error = urlParams.get('error');
        const email = urlParams.get('email');
        const details = urlParams.get('details');
        
        if (connected === 'true') {
            this.showSuccess(`Successfully connected to Google Drive${email ? ` (${email})` : ''}`);
            this.checkConnectionStatus();
            
            // Clean up URL
            this.cleanUrl();
            
        } else if (error) {
            let errorMessage = 'Google Drive connection failed';
            
            switch (error) {
                case 'oauth_denied':
                    errorMessage = 'Access was denied. Please try again and grant permission.';
                    break;
                case 'invalid_state':
                    errorMessage = 'Security error. Please try connecting again.';
                    break;
                case 'auth_failed':
                    errorMessage = `Authentication failed${details ? ': ' + details : ''}`;
                    break;
                case 'callback_failed':
                    errorMessage = 'Connection process failed. Please try again.';
                    break;
            }
            
            this.showError(errorMessage);
            
            // Clean up URL
            this.cleanUrl();
        }
    }
    
    cleanUrl() {
        // Remove OAuth parameters from URL
        const url = new URL(window.location);
        url.searchParams.delete('connected');
        url.searchParams.delete('error');
        url.searchParams.delete('email');
        url.searchParams.delete('details');
        window.history.replaceState({}, document.title, url.pathname);
    }
    
    showProgress(message) {
        if (this.progressContainer) {
            this.progressContainer.style.display = 'block';
            const progressText = this.progressContainer.querySelector('.progress-text');
            if (progressText) {
                progressText.textContent = message;
            }
        }
        
        if (this.connectButton) {
            this.connectButton.disabled = true;
        }
    }
    
    hideProgress() {
        if (this.progressContainer) {
            this.progressContainer.style.display = 'none';
        }
        
        if (this.connectButton) {
            this.connectButton.disabled = false;
        }
        
        this.isConnecting = false;
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showError(message) {
        this.showNotification(message, 'error');
        this.hideProgress();
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
        
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
    
    showReconnectOption() {
        if (this.connectButton) {
            this.connectButton.textContent = 'Reconnect Google Drive';
            this.connectButton.style.display = 'inline-block';
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.gdriveManager = new GoogleDriveManager();
});

// Also initialize if already loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.gdriveManager = new GoogleDriveManager();
    });
} else {
    window.gdriveManager = new GoogleDriveManager();
}