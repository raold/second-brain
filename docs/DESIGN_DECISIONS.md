# Second Brain Design Decisions

This document records key design decisions for consistency and future reference.

---

## Left Navigation Menu Design (2025-07-27)

**Decision**: Standardize all left navigation menus to match the documentation page design pattern.

### **Chosen Design Pattern:**
The documentation page (`/library`) navigation pattern with:

- **Emoji icons** for each menu item (improves visual hierarchy and accessibility)
- **Clean spacing** with `var(--space-1)` gaps between icon and text
- **Consistent structure**: `doc-link` class with `doc-icon` and text spans
- **Hover states** with color transitions to aqua theme
- **Active states** with background highlighting

### **Visual Structure:**
```html
<a href="#" class="doc-link" onclick="action()">
    <span class="doc-icon">🏠</span>
    <span>Menu Item</span>
</a>
```

### **CSS Pattern:**
```css
.doc-link {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    padding: var(--space-1) var(--space-2);
    color: var(--gruvbox-fg2);
    text-decoration: none;
    font-size: var(--text-sm);
    border-radius: var(--radius-sm);
    transition: all var(--duration-fast);
    cursor: pointer;
}

.doc-link:hover {
    background: var(--gruvbox-bg1);
    color: var(--gruvbox-aqua);
}

.doc-link.active {
    background: var(--gruvbox-bg1);
    color: var(--gruvbox-aqua);
    font-weight: 500;
}

.doc-icon {
    font-size: var(--text-sm);
    opacity: 0.8;
}
```

### **Rationale:**

1. **Visual Hierarchy**: Emojis provide instant visual recognition and categorization
2. **Accessibility**: Icons help users with different learning styles and language barriers
3. **Brand Consistency**: Maintains the modern, approachable feel of Second Brain
4. **Cognitive Load**: Reduces mental processing time for navigation
5. **Future-Proof**: Extensible pattern for new navigation sections

### **Rejected Alternative:**
Plain text links without icons (current API page style) - lacks visual interest and hierarchy.

### **Implementation Status:**
- ✅ Documentation page (`/library`) - Reference implementation
- 🔄 API Documentation page (`/api`) - To be updated
- 🔄 Dashboard page - To be updated (if applicable)
- 🔄 Future pages - Apply this pattern

### **Standard Icon Mapping:**
```
🏠 Home/Overview
📖 Documentation/Guides  
🚀 Setup/Getting Started
💡 Usage/Examples
🏛️ Architecture/System Design
🔌 API/Integration
🔄 Migration/Updates
👩‍💻 Development/Contributing
🤝 Community/Contributing
🧪 Testing/Validation
🚢 Deployment/Operations
⚙️ Configuration/Settings
🔐 Security/Environment
📝 Changelog/Release Notes
🎉 Announcements/News
📊 Analytics/Metrics
🔍 Search/Discovery
💾 Data/Storage
🔗 Integrations/External Services
📱 Mobile/Responsive
🌐 Network/API
🛠️ Tools/Utilities
📚 References/Documentation
✨ Features/Capabilities
🏥 Health/Status
🔧 Maintenance/Admin
```

### **Next Actions:**
1. Update API documentation page to use this pattern
2. Document any new icon additions in this file
3. Ensure all future navigation follows this standard

---

*This decision ensures consistent, accessible, and visually appealing navigation across the entire Second Brain application.*