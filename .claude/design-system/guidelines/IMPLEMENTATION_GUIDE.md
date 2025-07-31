# Second Brain Design System Implementation Guide

## Quick Start

### 1. Setup Design Tokens
```html
<!-- Include in document head -->
<link rel="stylesheet" href="/styles/tokens.css">
<link rel="stylesheet" href="/styles/reset.css">
<link rel="stylesheet" href="/styles/components.css">
<link rel="stylesheet" href="/styles/utilities.css">
```

### 2. Use the Base Template
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page Title - Second Brain</title>
  
  <!-- Design System -->
  <link rel="stylesheet" href="/styles/system.css">
  
  <!-- Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
</head>
<body>
  <div class="app-root">
    <!-- Global nav -->
    <!-- Main content -->
    <!-- Footer -->
  </div>
</body>
</html>
```

### 3. Follow Component Patterns
Always use predefined components rather than creating custom variations.

## CSS Architecture

### File Organization
```
styles/
├── tokens.css          # Design tokens as CSS variables
├── reset.css          # Normalize browser styles
├── base.css           # Base element styles
├── components/        # Component styles
│   ├── button.css
│   ├── card.css
│   ├── form.css
│   └── ...
├── layouts/           # Layout patterns
│   ├── dashboard.css
│   ├── browse.css
│   └── ...
├── utilities.css      # Utility classes
└── system.css         # Main bundle
```

### Naming Conventions

#### BEM-inspired Naming
```css
/* Block */
.memory-card { }

/* Element */
.memory-card__title { }
.memory-card__content { }

/* Modifier */
.memory-card--featured { }
.memory-card--loading { }

/* State */
.memory-card.is-selected { }
.memory-card.is-disabled { }
```

#### Utility Classes
```css
/* Spacing */
.mt-2 { margin-top: var(--space-2); }
.px-4 { padding-inline: var(--space-4); }

/* Typography */
.text-sm { font-size: var(--text-sm); }
.font-medium { font-weight: 500; }

/* Layout */
.flex { display: flex; }
.grid { display: grid; }

/* Visibility */
.sr-only { /* Screen reader only */ }
.hidden { display: none; }
```

## Component Implementation

### Basic Component
```html
<!-- Button Component -->
<button class="button button--primary">
  Save Changes
</button>

<!-- With loading state -->
<button class="button button--primary is-loading" disabled>
  <span class="button__text">Saving...</span>
  <span class="button__spinner"></span>
</button>
```

### Composite Component
```html
<!-- Memory Card -->
<article class="memory-card">
  <header class="memory-card__header">
    <h3 class="memory-card__title">Memory Title</h3>
    <span class="badge badge--episodic">Episodic</span>
  </header>
  
  <div class="memory-card__content">
    <p class="memory-card__preview">
      Content preview text...
    </p>
  </div>
  
  <footer class="memory-card__footer">
    <div class="memory-card__meta">
      <span class="importance-indicator" data-value="85">
        <svg class="importance-indicator__chart"><!-- Sparkline --></svg>
        <span class="importance-indicator__value">85%</span>
      </span>
      <time class="timestamp" datetime="2024-01-15T10:00:00Z">
        2 hours ago
      </time>
    </div>
  </footer>
</article>
```

## JavaScript Integration

### Component Initialization
```javascript
// components/MemoryCard.js
class MemoryCard {
  constructor(element) {
    this.element = element
    this.setupEventListeners()
  }
  
  setupEventListeners() {
    this.element.addEventListener('click', this.handleClick.bind(this))
  }
  
  handleClick(event) {
    // Don't trigger on interactive elements
    if (event.target.closest('button, a')) return
    
    // Navigate to detail view
    const memoryId = this.element.dataset.memoryId
    window.location.href = `/memories/${memoryId}`
  }
}

// Initialize all memory cards
document.querySelectorAll('.memory-card').forEach(element => {
  new MemoryCard(element)
})
```

### State Management
```javascript
// State classes
const STATE_CLASSES = {
  loading: 'is-loading',
  selected: 'is-selected',
  disabled: 'is-disabled',
  error: 'has-error'
}

// Add state
element.classList.add(STATE_CLASSES.loading)

// Remove state
element.classList.remove(STATE_CLASSES.loading)

// Toggle state
element.classList.toggle(STATE_CLASSES.selected)
```

### Animation Helpers
```javascript
// Respect reduced motion preference
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

// Transition helper
function transition(element, from, to, duration = 200) {
  if (prefersReducedMotion) {
    element.style.cssText = to
    return Promise.resolve()
  }
  
  return new Promise(resolve => {
    element.style.cssText = from
    element.style.transition = `all ${duration}ms ease-out`
    
    requestAnimationFrame(() => {
      element.style.cssText = to
      
      setTimeout(() => {
        element.style.transition = ''
        resolve()
      }, duration)
    })
  })
}
```

## Accessibility Implementation

### ARIA Patterns
```html
<!-- Loading state -->
<div aria-busy="true" aria-label="Loading memories">
  <!-- Skeleton content -->
</div>

<!-- Live region for updates -->
<div role="status" aria-live="polite" aria-atomic="true">
  <span class="sr-only">5 new memories found</span>
</div>

<!-- Modal dialog -->
<dialog role="dialog" 
        aria-labelledby="dialog-title" 
        aria-describedby="dialog-description">
  <h2 id="dialog-title">Confirm Delete</h2>
  <p id="dialog-description">This action cannot be undone.</p>
</dialog>
```

### Keyboard Navigation
```javascript
// Focus management
const focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
const focusableContent = element.querySelectorAll(focusableElements)
const firstFocusable = focusableContent[0]
const lastFocusable = focusableContent[focusableContent.length - 1]

// Trap focus in modal
element.addEventListener('keydown', (e) => {
  if (e.key === 'Tab') {
    if (e.shiftKey) {
      if (document.activeElement === firstFocusable) {
        lastFocusable.focus()
        e.preventDefault()
      }
    } else {
      if (document.activeElement === lastFocusable) {
        firstFocusable.focus()
        e.preventDefault()
      }
    }
  }
  
  if (e.key === 'Escape') {
    closeModal()
  }
})
```

## Performance Guidelines

### CSS Performance
```css
/* Use CSS containment */
.memory-card {
  contain: layout style;
}

/* Avoid expensive selectors */
/* Bad */
.page .content .section .memory-card:nth-child(odd) .title { }

/* Good */
.memory-card__title { }

/* Use will-change sparingly */
.modal {
  will-change: transform;
}
```

### Loading Optimization
```html
<!-- Preload critical resources -->
<link rel="preload" href="/fonts/Inter-Regular.woff2" as="font" crossorigin>
<link rel="preload" href="/styles/system.css" as="style">

<!-- Lazy load images -->
<img src="placeholder.jpg" 
     data-src="actual-image.jpg" 
     loading="lazy"
     alt="Description">
```

### Component Lazy Loading
```javascript
// Intersection Observer for lazy components
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const component = entry.target
      loadComponent(component)
      observer.unobserve(component)
    }
  })
}, {
  rootMargin: '50px'
})

// Observe components
document.querySelectorAll('[data-lazy-component]').forEach(el => {
  observer.observe(el)
})
```

## Testing Checklist

### Visual Testing
- [ ] Components match design specs
- [ ] Consistent spacing and alignment
- [ ] Proper color application
- [ ] Typography hierarchy clear
- [ ] States visually distinct

### Functional Testing
- [ ] Interactive elements work
- [ ] Forms validate properly
- [ ] Navigation functions
- [ ] Loading states appear
- [ ] Error states recoverable

### Accessibility Testing
- [ ] Keyboard navigation complete
- [ ] Screen reader announces properly
- [ ] Focus indicators visible
- [ ] Color contrast passes
- [ ] Touch targets adequate

### Performance Testing
- [ ] Page loads under 3s
- [ ] No layout shifts
- [ ] Animations smooth
- [ ] Images optimized
- [ ] CSS/JS minimized

## Migration Guide

### From Custom Styles
```css
/* Old */
.my-custom-button {
  padding: 10px 20px;
  background: #2563EB;
  color: white;
  border-radius: 6px;
}

/* New */
<button class="button button--primary">
  Click me
</button>
```

### Component Updates
```javascript
// Track deprecated patterns
console.warn('[Deprecation] Use .button--primary instead of .btn-primary')

// Provide migration path
if (element.classList.contains('btn-primary')) {
  element.classList.remove('btn-primary')
  element.classList.add('button', 'button--primary')
}
```

## Resources

### Documentation
- Component Library: `/design-system/components`
- Pattern Library: `/design-system/patterns`
- Design Tokens: `/design-system/tokens`

### Tools
- Figma Library: [Link to Figma]
- Storybook: `/storybook`
- Testing Suite: `/tests/design-system`

### Support
- Design System Team: design-system@secondbrain.app
- Slack Channel: #design-system
- Office Hours: Wednesdays 2-3pm

Remember: Consistency is key. When in doubt, refer to existing patterns rather than creating new ones.