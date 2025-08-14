# Second Brain Design Architecture
## Component System & Implementation Guide

This document defines the technical architecture for implementing the Second Brain design language with pixel-perfect precision.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────┐
│          Design Tokens                  │
│    (CSS Custom Properties)              │
└────────────────┬────────────────────────┘
                 │
┌────────────────┴────────────────────────┐
│         Base Styles                     │
│    (Reset, Typography, Layout)          │
└────────────────┬────────────────────────┘
                 │
┌────────────────┴────────────────────────┐
│      Component Library                  │
│   (Atoms → Molecules → Organisms)       │
└────────────────┬────────────────────────┘
                 │
┌────────────────┴────────────────────────┐
│        Page Templates                   │
│    (Layouts, Patterns, Flows)           │
└────────────────┬────────────────────────┘
                 │
┌────────────────┴────────────────────────┐
│      Application Views                  │
│    (Dashboard, Docs, Settings)          │
└─────────────────────────────────────────┘
```

---

## 📁 File Structure

```
static/
├── css/
│   ├── core/
│   │   ├── reset.css          # Browser normalization
│   │   ├── tokens.css         # Design tokens
│   │   ├── typography.css     # Type system
│   │   ├── layout.css         # Grid & spacing
│   │   └── utilities.css      # Helper classes
│   │
│   ├── components/
│   │   ├── atoms/
│   │   │   ├── button.css
│   │   │   ├── input.css
│   │   │   ├── badge.css
│   │   │   └── icon.css
│   │   │
│   │   ├── molecules/
│   │   │   ├── form-group.css
│   │   │   ├── metric-card.css
│   │   │   ├── nav-item.css
│   │   │   └── table-cell.css
│   │   │
│   │   └── organisms/
│   │       ├── navigation.css
│   │       ├── data-table.css
│   │       ├── dashboard-grid.css
│   │       └── modal.css
│   │
│   ├── layouts/
│   │   ├── dashboard-layout.css
│   │   ├── docs-layout.css
│   │   └── settings-layout.css
│   │
│   └── main.css               # Import orchestration
│
└── js/
    ├── core/
    │   ├── theme.js           # Theme management
    │   ├── density.js         # Density switching
    │   └── a11y.js           # Accessibility helpers
    │
    └── components/
        ├── navigation.js
        ├── data-table.js
        └── form-validation.js
```

---

## 🎨 CSS Architecture

### 1. Design Tokens (tokens.css)
```css
:root {
  /* Primitive Tokens */
  --primitive-blue-500: #3b82f6;
  --primitive-gray-900: #111827;
  
  /* Semantic Tokens */
  --color-primary: var(--primitive-blue-500);
  --color-text-primary: var(--primitive-gray-900);
  
  /* Component Tokens */
  --button-height-md: 40px;
  --button-padding-x-md: 16px;
}
```

### 2. Base Reset (reset.css)
```css
/* Modern CSS Reset */
*, *::before, *::after {
  box-sizing: border-box;
}

* {
  margin: 0;
  padding: 0;
  font: inherit;
}

html {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-size-adjust: 100%;
}

/* Accessible defaults */
:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
```

### 3. Component Structure
```css
/* Component Template */
.component {
  /* Layout */
  display: flex;
  align-items: center;
  
  /* Spacing */
  padding: var(--component-padding-y) var(--component-padding-x);
  gap: var(--component-gap);
  
  /* Visual */
  background: var(--component-bg);
  border: 1px solid var(--component-border);
  border-radius: var(--component-radius);
  
  /* Typography */
  font-size: var(--component-font-size);
  font-weight: var(--component-font-weight);
  line-height: var(--component-line-height);
  
  /* Interaction */
  cursor: pointer;
  transition: var(--component-transition);
}

/* States */
.component:hover {
  background: var(--component-bg-hover);
  border-color: var(--component-border-hover);
}

.component:active {
  transform: translateY(1px);
}

.component:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.component[disabled] {
  opacity: 0.5;
  cursor: not-allowed;
}
```

---

## 🧩 Component Library

### Atoms

#### Button Component
```css
/* button.css */
.btn {
  /* Base styles from design tokens */
  --btn-height: var(--button-height-md);
  --btn-padding-x: var(--button-padding-x-md);
  --btn-font-size: var(--text-base);
  --btn-font-weight: var(--font-medium);
  --btn-radius: var(--radius-md);
  
  /* Implementation */
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: var(--btn-height);
  padding: 0 var(--btn-padding-x);
  font-size: var(--btn-font-size);
  font-weight: var(--btn-font-weight);
  border-radius: var(--btn-radius);
  border: 1px solid transparent;
  cursor: pointer;
  transition: all var(--duration-fast) ease;
  white-space: nowrap;
  user-select: none;
}

/* Variants */
.btn--primary {
  background: var(--color-primary);
  color: var(--color-white);
  border-color: var(--color-primary);
}

.btn--secondary {
  background: transparent;
  color: var(--color-text-primary);
  border-color: var(--color-border-default);
}

/* Sizes */
.btn--sm {
  --btn-height: var(--button-height-sm);
  --btn-padding-x: var(--button-padding-x-sm);
  --btn-font-size: var(--text-sm);
}

.btn--lg {
  --btn-height: var(--button-height-lg);
  --btn-padding-x: var(--button-padding-x-lg);
}

/* States */
.btn:not([disabled]):hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.btn:not([disabled]):active {
  transform: translateY(0);
  box-shadow: none;
}
```

### Molecules

#### Metric Card Component
```css
/* metric-card.css */
.metric-card {
  --card-padding: var(--space-4);
  --card-gap: var(--space-3);
  
  display: grid;
  grid-template-areas:
    "label  trend"
    "value  trend"
    "change trend";
  grid-template-columns: 1fr auto;
  gap: var(--card-gap);
  padding: var(--card-padding);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  transition: all var(--duration-fast) ease;
}

.metric-card__label {
  grid-area: label;
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  font-weight: var(--font-medium);
}

.metric-card__value {
  grid-area: value;
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  line-height: 1;
}

.metric-card__change {
  grid-area: change;
  font-size: var(--text-sm);
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.metric-card__trend {
  grid-area: trend;
  width: 80px;
  height: 40px;
  align-self: center;
}

/* States */
.metric-card:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

/* Modifiers */
.metric-card--positive .metric-card__change {
  color: var(--color-success);
}

.metric-card--negative .metric-card__change {
  color: var(--color-danger);
}
```

### Organisms

#### Navigation Component
```css
/* navigation.css */
.nav {
  --nav-height: 64px;
  --nav-padding-x: var(--space-8);
  --nav-logo-size: var(--text-xl);
  --nav-link-gap: var(--space-8);
  
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  height: var(--nav-height);
  background: var(--color-bg-primary);
  border-bottom: 1px solid var(--color-border-subtle);
  box-shadow: var(--shadow-sm);
}

.nav__container {
  height: 100%;
  max-width: var(--container-2xl);
  margin: 0 auto;
  padding: 0 var(--nav-padding-x);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav__logo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--nav-logo-size);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  text-decoration: none;
}

.nav__links {
  display: flex;
  align-items: center;
  gap: var(--nav-link-gap);
  height: 100%;
  list-style: none;
}

.nav__link {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 var(--space-2);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-weight: var(--font-medium);
  position: relative;
  transition: color var(--duration-fast) ease;
}

.nav__link::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--color-primary);
  transform: scaleX(0);
  transition: transform var(--duration-fast) ease;
}

.nav__link:hover {
  color: var(--color-text-primary);
}

.nav__link--active {
  color: var(--color-primary);
}

.nav__link--active::after {
  transform: scaleX(1);
}

/* Mobile */
@media (max-width: 639px) {
  .nav__links {
    display: none;
  }
  
  .nav__mobile-toggle {
    display: block;
  }
}
```

---

## 🔄 State Management

### Theme System
```javascript
// theme.js
class ThemeManager {
  constructor() {
    this.themes = ['light', 'dark', 'gruvbox-dark'];
    this.current = this.getStoredTheme() || 'gruvbox-dark';
    this.apply();
  }
  
  apply() {
    document.documentElement.setAttribute('data-theme', this.current);
    this.updateMetaTheme();
  }
  
  switch(theme) {
    if (this.themes.includes(theme)) {
      this.current = theme;
      this.apply();
      this.store();
    }
  }
  
  store() {
    localStorage.setItem('sb-theme', this.current);
  }
  
  getStoredTheme() {
    return localStorage.getItem('sb-theme');
  }
  
  updateMetaTheme() {
    const meta = document.querySelector('meta[name="theme-color"]');
    const color = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-bg-primary');
    if (meta) meta.content = color;
  }
}
```

### Density System
```javascript
// density.js
class DensityManager {
  constructor() {
    this.densities = ['compact', 'comfortable', 'spacious'];
    this.current = this.getStoredDensity() || 'comfortable';
    this.apply();
  }
  
  apply() {
    document.documentElement.setAttribute('data-density', this.current);
    this.updateSpacing();
  }
  
  updateSpacing() {
    const multipliers = {
      compact: 0.75,
      comfortable: 1,
      spacious: 1.25
    };
    
    const root = document.documentElement;
    const multiplier = multipliers[this.current];
    
    // Update space tokens
    for (let i = 0; i <= 24; i++) {
      const base = i * 4; // 4px base
      const value = base * multiplier;
      root.style.setProperty(`--space-${i}`, `${value}px`);
    }
  }
}
```

---

## 📐 Layout System

### Grid Layout
```css
/* layout.css */
.layout-grid {
  display: grid;
  gap: var(--grid-gap, var(--space-4));
  grid-template-columns: repeat(var(--grid-cols, 12), minmax(0, 1fr));
}

/* Column spans */
.col-span-1 { grid-column: span 1; }
.col-span-2 { grid-column: span 2; }
.col-span-3 { grid-column: span 3; }
.col-span-4 { grid-column: span 4; }
.col-span-6 { grid-column: span 6; }
.col-span-8 { grid-column: span 8; }
.col-span-12 { grid-column: span 12; }

/* Responsive columns */
@media (max-width: 639px) {
  .layout-grid { --grid-cols: 4; }
  .col-sm-full { grid-column: 1 / -1; }
}

@media (min-width: 640px) and (max-width: 1023px) {
  .layout-grid { --grid-cols: 8; }
}

@media (min-width: 1024px) {
  .layout-grid { --grid-cols: 12; }
}
```

### Page Layouts
```css
/* dashboard-layout.css */
.dashboard-layout {
  --header-height: 64px;
  --sidebar-width: 240px;
  --content-max-width: 1440px;
  
  display: grid;
  grid-template-areas:
    "header header"
    "sidebar content";
  grid-template-columns: var(--sidebar-width) 1fr;
  grid-template-rows: var(--header-height) 1fr;
  min-height: 100vh;
}

.dashboard-layout__header {
  grid-area: header;
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
}

.dashboard-layout__sidebar {
  grid-area: sidebar;
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border-subtle);
  overflow-y: auto;
}

.dashboard-layout__content {
  grid-area: content;
  padding: var(--space-6);
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
}

/* Mobile layout */
@media (max-width: 767px) {
  .dashboard-layout {
    grid-template-areas:
      "header"
      "content";
    grid-template-columns: 1fr;
  }
  
  .dashboard-layout__sidebar {
    display: none;
  }
}
```

---

## 🚀 Performance Optimization

### Critical CSS
```html
<!-- Inline critical CSS -->
<style>
  /* Only above-the-fold styles */
  :root { /* tokens */ }
  body { /* base styles */ }
  .nav { /* navigation */ }
  .hero { /* hero section */ }
</style>

<!-- Async load non-critical -->
<link rel="preload" href="/css/main.css" as="style">
<link rel="stylesheet" href="/css/main.css" media="print" onload="this.media='all'">
```

### CSS Architecture Best Practices
1. **Use CSS Custom Properties** for all values
2. **Compose, don't override** - utility classes
3. **Single source of truth** - design tokens
4. **Progressive enhancement** - mobile first
5. **Minimize specificity** - max 2 levels deep

### Build Process
```javascript
// postcss.config.js
module.exports = {
  plugins: [
    require('postcss-import'),
    require('postcss-custom-properties'),
    require('postcss-calc'),
    require('autoprefixer'),
    require('cssnano')({
      preset: ['default', {
        discardComments: { removeAll: true },
        reduceIdents: false
      }]
    })
  ]
}
```

---

## 🧪 Testing & Validation

### Visual Regression Testing
```javascript
// visual-tests.js
const scenarios = [
  { name: 'navigation-desktop', viewport: { width: 1440, height: 900 } },
  { name: 'navigation-tablet', viewport: { width: 768, height: 1024 } },
  { name: 'navigation-mobile', viewport: { width: 375, height: 667 } }
];

const states = ['default', 'hover', 'active', 'focus'];
```

### Accessibility Testing
```javascript
// a11y-tests.js
const axe = require('axe-core');

async function testComponent(component) {
  const results = await axe.run(component, {
    rules: {
      'color-contrast': { enabled: true },
      'focus-visible': { enabled: true },
      'keyboard-navigation': { enabled: true }
    }
  });
  
  return results.violations.length === 0;
}
```

---

## 📋 Implementation Checklist

For each new component:

- [ ] Design tokens defined
- [ ] Component structure documented
- [ ] All states implemented
- [ ] Responsive behavior defined
- [ ] Accessibility validated
- [ ] Performance profiled
- [ ] Visual regression tests
- [ ] Documentation complete
- [ ] Code review passed
- [ ] Integration tested

---

## 🔗 Quick Reference

### Component Creation
```bash
# Create new component
mkdir -p static/css/components/molecules
touch static/css/components/molecules/new-component.css
```

### Token Usage
```css
/* Always use tokens */
padding: var(--space-4);          /* ✓ Good */
padding: 16px;                    /* ✗ Bad */

color: var(--color-primary);      /* ✓ Good */
color: #8ec07c;                   /* ✗ Bad */
```

### Naming Convention
```css
/* Block__Element--Modifier */
.card { }                         /* Block */
.card__header { }                 /* Element */
.card--active { }                 /* Modifier */
.card__header--compressed { }     /* Element with modifier */
```

---

Last Updated: 2024-01-27
Architecture Version: 3.0.0