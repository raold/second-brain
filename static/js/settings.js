// Settings Management System - Second Brain v3.0
// Handles theme, density, and other user preferences

class SettingsManager {
    constructor() {
        this.settings = {
            theme: 'gruvbox-dark',
            density: 'comfortable',
            animations: true,
            autoSave: true
        };
        
        this.originalSettings = {};
        this.modal = null;
        this.hasChanges = false;
        
        this.init();
    }
    
    init() {
        // Load saved settings
        this.loadSettings();
        
        // Apply settings to all pages
        this.applySettings();
        
        // Always create modal
        this.createModal();
    }
    
    loadSettings() {
        const saved = localStorage.getItem('secondBrainSettings');
        if (saved) {
            try {
                this.settings = { ...this.settings, ...JSON.parse(saved) };
            } catch (e) {
                console.error('Failed to load settings:', e);
            }
        }
    }
    
    saveSettings() {
        localStorage.setItem('secondBrainSettings', JSON.stringify(this.settings));
        this.hasChanges = false;
        this.updateButtons();
        
        // Show success message
        this.showMessage('Settings saved successfully', 'success');
        
        // Apply settings immediately
        this.applySettings();
        
        // Close modal after short delay
        setTimeout(() => this.closeModal(), 1000);
    }
    
    cancelSettings() {
        // Restore original settings
        this.settings = { ...this.originalSettings };
        this.applySettings();
        this.hasChanges = false;
        this.updateButtons();
        this.closeModal();
    }
    
    applySettings() {
        // Apply theme
        document.documentElement.setAttribute('data-theme', this.settings.theme);
        
        // Apply density
        document.documentElement.setAttribute('data-density', this.settings.density);
        
        // Apply animations
        if (!this.settings.animations) {
            document.documentElement.classList.add('reduce-motion');
        } else {
            document.documentElement.classList.remove('reduce-motion');
        }
        
        // Update theme color meta tag
        const themeColors = {
            'gruvbox-dark': '#1d2021',
            'gruvbox-light': '#fbf1c7',
            'nord': '#2e3440'
        };
        const metaTheme = document.querySelector('meta[name="theme-color"]');
        if (metaTheme && themeColors[this.settings.theme]) {
            metaTheme.content = themeColors[this.settings.theme];
        }
    }
    
    createModal() {
        // Create modal HTML
        const modalHtml = `
            <div id="settingsModal" class="settings-modal" style="display: none;">
                <div class="settings-backdrop" onclick="settingsManager.closeModal()"></div>
                <div class="settings-content">
                    <div class="settings-header">
                        <h2>Settings</h2>
                        <button class="settings-close" onclick="settingsManager.closeModal()">×</button>
                    </div>
                    
                    <div class="settings-body">
                        <!-- Theme Selection -->
                        <div class="settings-group">
                            <label class="settings-label">Theme</label>
                            <div class="settings-options">
                                <label class="radio-option">
                                    <input type="radio" name="theme" value="gruvbox-dark" 
                                           ${this.settings.theme === 'gruvbox-dark' ? 'checked' : ''}
                                           onchange="settingsManager.updateSetting('theme', this.value)">
                                    <span>Gruvbox Dark</span>
                                </label>
                                <label class="radio-option">
                                    <input type="radio" name="theme" value="gruvbox-light"
                                           ${this.settings.theme === 'gruvbox-light' ? 'checked' : ''}
                                           onchange="settingsManager.updateSetting('theme', this.value)">
                                    <span>Gruvbox Light</span>
                                </label>
                                <label class="radio-option">
                                    <input type="radio" name="theme" value="nord"
                                           ${this.settings.theme === 'nord' ? 'checked' : ''}
                                           onchange="settingsManager.updateSetting('theme', this.value)">
                                    <span>Nord</span>
                                </label>
                            </div>
                        </div>
                        
                        <!-- Density Selection -->
                        <div class="settings-group">
                            <label class="settings-label">Density</label>
                            <div class="settings-options">
                                <label class="radio-option">
                                    <input type="radio" name="density" value="compact"
                                           ${this.settings.density === 'compact' ? 'checked' : ''}
                                           onchange="settingsManager.updateSetting('density', this.value)">
                                    <span>Compact</span>
                                </label>
                                <label class="radio-option">
                                    <input type="radio" name="density" value="comfortable"
                                           ${this.settings.density === 'comfortable' ? 'checked' : ''}
                                           onchange="settingsManager.updateSetting('density', this.value)">
                                    <span>Comfortable</span>
                                </label>
                                <label class="radio-option">
                                    <input type="radio" name="density" value="spacious"
                                           ${this.settings.density === 'spacious' ? 'checked' : ''}
                                           onchange="settingsManager.updateSetting('density', this.value)">
                                    <span>Spacious</span>
                                </label>
                            </div>
                        </div>
                        
                        <!-- Other Settings -->
                        <div class="settings-group">
                            <label class="checkbox-option">
                                <input type="checkbox" ${this.settings.animations ? 'checked' : ''}
                                       onchange="settingsManager.updateSetting('animations', this.checked)">
                                <span>Enable animations</span>
                            </label>
                        </div>
                        
                        <div class="settings-group">
                            <label class="checkbox-option">
                                <input type="checkbox" ${this.settings.autoSave ? 'checked' : ''}
                                       onchange="settingsManager.updateSetting('autoSave', this.checked)">
                                <span>Auto-save memories</span>
                            </label>
                        </div>
                    </div>
                    
                    <div class="settings-footer">
                        <div id="settingsMessage" class="settings-message"></div>
                        <div class="settings-actions">
                            <button class="settings-btn secondary" onclick="settingsManager.cancelSettings()">
                                Cancel
                            </button>
                            <button id="saveSettingsBtn" class="settings-btn primary" onclick="settingsManager.saveSettings()" disabled>
                                Save Changes
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Insert modal into DOM
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        this.modal = document.getElementById('settingsModal');
        
        // Add styles
        this.addStyles();
    }
    
    addStyles() {
        const styles = `
            <style id="settingsStyles">
                .settings-modal {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    z-index: 1000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 1rem;
                    background: rgba(0, 0, 0, 0.5);
                    backdrop-filter: blur(2px);
                }
                
                .settings-backdrop {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                }
                
                .settings-content {
                    position: relative;
                    background: #1d2021;
                    border: 1px solid #504945;
                    border-radius: 0.75rem;
                    width: 100%;
                    max-width: 500px;
                    max-height: 80vh;
                    display: flex;
                    flex-direction: column;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
                    opacity: 0;
                    transform: translateY(1rem);
                    transition: all 0.3s ease;
                }
                
                .settings-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 1.5rem;
                    border-bottom: 1px solid #504945;
                }
                
                .settings-header h2 {
                    font-size: 1.25rem;
                    font-weight: 600;
                    color: #ebdbb2;
                    margin: 0;
                }
                
                .settings-close {
                    width: 2rem;
                    height: 2rem;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: transparent;
                    border: none;
                    color: #a89984;
                    font-size: 1.5rem;
                    cursor: pointer;
                    border-radius: 0.375rem;
                    transition: all 0.15s;
                }
                
                .settings-close:hover {
                    background: #3c3836;
                    color: #ebdbb2;
                }
                
                .settings-body {
                    flex: 1;
                    overflow-y: auto;
                    padding: 1.5rem;
                }
                
                .settings-group {
                    margin-bottom: 1.5rem;
                }
                
                .settings-group:last-child {
                    margin-bottom: 0;
                }
                
                .settings-label {
                    display: block;
                    font-size: 1rem;
                    font-weight: 500;
                    color: #ebdbb2;
                    margin-bottom: 0.75rem;
                }
                
                .settings-options {
                    display: flex;
                    flex-direction: column;
                    gap: 0.5rem;
                }
                
                .radio-option,
                .checkbox-option {
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    padding: 0.75rem;
                    background: #282828;
                    border: 1px solid #504945;
                    border-radius: 0.375rem;
                    cursor: pointer;
                    transition: all 0.15s;
                }
                
                .radio-option:hover,
                .checkbox-option:hover {
                    background: #3c3836;
                    border-color: #665c54;
                }
                
                .radio-option input[type="radio"],
                .checkbox-option input[type="checkbox"] {
                    width: 1.25rem;
                    height: 1.25rem;
                    cursor: pointer;
                }
                
                .radio-option span,
                .checkbox-option span {
                    flex: 1;
                    color: #d5c4a1;
                }
                
                .settings-footer {
                    padding: 1.5rem;
                    border-top: 1px solid #504945;
                }
                
                .settings-message {
                    margin-bottom: 1rem;
                    padding: 0.75rem;
                    border-radius: 0.375rem;
                    font-size: 0.875rem;
                    opacity: 0;
                    transition: opacity 0.15s;
                }
                
                .settings-message.show {
                    opacity: 1;
                }
                
                .settings-message.success {
                    background: #b8bb26;
                    color: #1d2021;
                }
                
                .settings-message.error {
                    background: #fb4934;
                    color: #1d2021;
                }
                
                .settings-actions {
                    display: flex;
                    gap: 0.75rem;
                    justify-content: flex-end;
                }
                
                .settings-btn {
                    padding: 0.75rem 1.5rem;
                    border: none;
                    border-radius: 0.375rem;
                    font-size: 0.875rem;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.15s;
                }
                
                .settings-btn.primary {
                    background: #8ec07c;
                    color: #1d2021;
                }
                
                .settings-btn.primary:hover:not(:disabled) {
                    background: #a8d18a;
                }
                
                .settings-btn.primary:disabled {
                    background: #504945;
                    color: #7c6f64;
                    cursor: not-allowed;
                }
                
                .settings-btn.secondary {
                    background: #3c3836;
                    color: #d5c4a1;
                    border: 1px solid #504945;
                }
                
                .settings-btn.secondary:hover {
                    background: #504945;
                    color: #ebdbb2;
                }
                
                /* Animation */
                @keyframes slideIn {
                    from {
                        opacity: 0;
                        transform: translateY(1rem);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
                
                .settings-modal.show .settings-content {
                    opacity: 1;
                    transform: translateY(0);
                }
                
                /* Reduce motion */
                .reduce-motion * {
                    animation-duration: 0.01ms !important;
                    transition-duration: 0.01ms !important;
                }
            </style>
        `;
        
        document.head.insertAdjacentHTML('beforeend', styles);
    }
    
    openModal() {
        if (!this.modal) {
            this.createModal();
        }
        
        // Store original settings
        this.originalSettings = { ...this.settings };
        
        // Show modal
        this.modal.style.display = 'flex';
        
        // Force a reflow then add the show class for animation
        this.modal.offsetHeight;
        this.modal.classList.add('show');
        
        // Reset state
        this.hasChanges = false;
        this.updateButtons();
    }
    
    closeModal() {
        if (this.modal) {
            this.modal.classList.remove('show');
            setTimeout(() => {
                this.modal.style.display = 'none';
            }, 300);
        }
    }
    
    updateSetting(key, value) {
        this.settings[key] = value;
        
        // Apply setting immediately for preview
        this.applySettings();
        
        // Mark as changed
        this.hasChanges = true;
        this.updateButtons();
    }
    
    updateButtons() {
        const saveBtn = document.getElementById('saveSettingsBtn');
        if (saveBtn) {
            saveBtn.disabled = !this.hasChanges;
        }
    }
    
    showMessage(text, type = 'success') {
        const messageEl = document.getElementById('settingsMessage');
        if (messageEl) {
            messageEl.textContent = text;
            messageEl.className = `settings-message ${type} show`;
            
            setTimeout(() => {
                messageEl.classList.remove('show');
            }, 3000);
        }
    }
}

// Initialize settings manager
const settingsManager = new SettingsManager();

// Global function for opening settings
function showSettings() {
    settingsManager.openModal();
}