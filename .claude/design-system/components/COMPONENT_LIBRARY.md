# Second Brain Component Library

## Core Components

### Navigation Components

#### GlobalNav
Persistent navigation across all pages:
```html
<nav class="global-nav">
  <div class="nav-brand">
    <svg class="logo" width="24" height="24"><!-- Brain icon --></svg>
    <span class="wordmark">Second Brain</span>
  </div>
  
  <ul class="nav-links">
    <li><a href="/dashboard" class="nav-link active">Dashboard</a></li>
    <li><a href="/memories" class="nav-link">Memories</a></li>
    <li><a href="/insights" class="nav-link">Insights</a></li>
    <li><a href="/api" class="nav-link">API</a></li>
    <li><a href="/docs" class="nav-link">Docs</a></li>
  </ul>
  
  <div class="nav-actions">
    <button class="icon-button" aria-label="Search">
      <svg><!-- Search icon --></svg>
    </button>
    <button class="icon-button" aria-label="Settings">
      <svg><!-- Settings icon --></svg>
    </button>
  </div>
</nav>
```

#### Breadcrumb
Hierarchical navigation:
```html
<nav aria-label="Breadcrumb">
  <ol class="breadcrumb">
    <li><a href="/">Home</a></li>
    <li><a href="/memories">Memories</a></li>
    <li aria-current="page">Episodic</li>
  </ol>
</nav>
```

### Memory Components

#### MemoryCard
Consistent memory display across views:
```html
<article class="memory-card">
  <header class="memory-header">
    <h3 class="memory-title">Meeting with design team</h3>
    <span class="memory-type episodic">Episodic</span>
  </header>
  
  <p class="memory-preview">
    Discussed the new component architecture and agreed on...
  </p>
  
  <footer class="memory-meta">
    <span class="importance">
      <svg class="sparkline" width="60" height="20">
        <!-- Importance trend sparkline -->
      </svg>
      <span class="value">85%</span>
    </span>
    <time class="timestamp" datetime="2024-01-15T10:30:00Z">
      2 hours ago
    </time>
  </footer>
</article>
```

#### MemoryEditor
Unified creation/editing interface:
```html
<form class="memory-editor">
  <div class="editor-header">
    <input type="text" 
           class="title-input" 
           placeholder="Title (optional)"
           maxlength="100">
    
    <select class="type-selector" aria-label="Memory type">
      <option value="semantic">Semantic</option>
      <option value="episodic">Episodic</option>
      <option value="procedural">Procedural</option>
    </select>
  </div>
  
  <textarea class="content-input"
            placeholder="What would you like to remember?"
            rows="6"
            required></textarea>
  
  <div class="editor-footer">
    <span class="char-count">0 / 5000</span>
    <div class="actions">
      <button type="button" class="button secondary">Cancel</button>
      <button type="submit" class="button primary">Save</button>
    </div>
  </div>
</form>
```

### Form Components

#### TextField
Standard text input:
```html
<div class="form-field">
  <label for="search" class="field-label">
    Search memories
  </label>
  <input type="search" 
         id="search"
         class="text-input"
         placeholder="Type to search..."
         aria-describedby="search-help">
  <small id="search-help" class="field-help">
    Use quotes for exact phrases
  </small>
</div>
```

#### SelectField
Dropdown selection:
```html
<div class="form-field">
  <label for="filter-type" class="field-label">
    Memory type
  </label>
  <select id="filter-type" class="select-input">
    <option value="">All types</option>
    <option value="semantic">Semantic</option>
    <option value="episodic">Episodic</option>
    <option value="procedural">Procedural</option>
  </select>
</div>
```

### Feedback Components

#### EmptyState
Consistent empty states:
```html
<div class="empty-state">
  <svg class="empty-icon" width="64" height="64">
    <!-- Contextual icon -->
  </svg>
  <h3 class="empty-title">No memories yet</h3>
  <p class="empty-message">
    Create your first memory to get started
  </p>
  <button class="button primary">
    Create memory
  </button>
</div>
```

#### LoadingState
Skeleton screens:
```html
<div class="loading-state">
  <div class="skeleton skeleton-title"></div>
  <div class="skeleton skeleton-text"></div>
  <div class="skeleton skeleton-text skeleton-short"></div>
</div>
```

#### ErrorState
Error handling:
```html
<div class="error-state">
  <svg class="error-icon" width="48" height="48">
    <!-- Error icon -->
  </svg>
  <h3 class="error-title">Something went wrong</h3>
  <p class="error-message">
    We couldn't load your memories. Please try again.
  </p>
  <button class="button primary">Retry</button>
</div>
```

### Data Display Components

#### DataTable
Structured data display:
```html
<div class="data-table-container">
  <table class="data-table">
    <thead>
      <tr>
        <th scope="col">Memory</th>
        <th scope="col">Type</th>
        <th scope="col">Importance</th>
        <th scope="col">Created</th>
        <th scope="col">Actions</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="truncate">Project planning meeting notes</td>
        <td><span class="badge episodic">Episodic</span></td>
        <td>
          <div class="importance-bar">
            <div class="importance-fill" style="width: 85%"></div>
          </div>
        </td>
        <td><time>Jan 15, 2024</time></td>
        <td>
          <button class="icon-button" aria-label="More actions">
            <svg><!-- More icon --></svg>
          </button>
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

#### StatCard
Dashboard statistics:
```html
<div class="stat-card">
  <h3 class="stat-label">Total Memories</h3>
  <p class="stat-value">1,234</p>
  <p class="stat-change positive">
    <svg class="trend-icon"><!-- Up arrow --></svg>
    <span>12% from last week</span>
  </p>
</div>
```

### Layout Components

#### PageHeader
Consistent page headers:
```html
<header class="page-header">
  <div class="header-content">
    <h1 class="page-title">Dashboard</h1>
    <p class="page-description">
      Overview of your memory activity and insights
    </p>
  </div>
  <div class="header-actions">
    <button class="button secondary">Export</button>
    <button class="button primary">Create Memory</button>
  </div>
</header>
```

#### SidePanel
Collapsible side panels:
```html
<aside class="side-panel" aria-label="Filters">
  <div class="panel-header">
    <h2 class="panel-title">Filters</h2>
    <button class="icon-button" aria-label="Close panel">
      <svg><!-- Close icon --></svg>
    </button>
  </div>
  
  <div class="panel-content">
    <!-- Filter controls -->
  </div>
</aside>
```

### Interactive Components

#### Modal
Overlay dialogs:
```html
<dialog class="modal" role="dialog" aria-labelledby="modal-title">
  <div class="modal-content">
    <header class="modal-header">
      <h2 id="modal-title" class="modal-title">
        Delete Memory?
      </h2>
      <button class="icon-button" aria-label="Close">
        <svg><!-- Close icon --></svg>
      </button>
    </header>
    
    <div class="modal-body">
      <p>This action cannot be undone.</p>
    </div>
    
    <footer class="modal-footer">
      <button class="button secondary">Cancel</button>
      <button class="button danger">Delete</button>
    </footer>
  </div>
</dialog>
```

#### Dropdown
Context menus:
```html
<div class="dropdown">
  <button class="dropdown-trigger" 
          aria-expanded="false"
          aria-controls="dropdown-menu">
    Options
    <svg class="dropdown-arrow"><!-- Chevron --></svg>
  </button>
  
  <ul id="dropdown-menu" 
      class="dropdown-menu" 
      role="menu"
      hidden>
    <li role="menuitem">
      <button class="dropdown-item">Edit</button>
    </li>
    <li role="menuitem">
      <button class="dropdown-item">Duplicate</button>
    </li>
    <li role="separator" class="dropdown-divider"></li>
    <li role="menuitem">
      <button class="dropdown-item danger">Delete</button>
    </li>
  </ul>
</div>
```

## Component States

### Interactive States
```css
/* Rest state */
.button {
  background: var(--color-primary);
  color: white;
  transition: all 150ms ease-out;
}

/* Hover state */
.button:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
}

/* Active state */
.button:active {
  transform: scale(0.98);
}

/* Focus state */
.button:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* Disabled state */
.button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Loading state */
.button.loading {
  color: transparent;
  position: relative;
}

.button.loading::after {
  content: '';
  position: absolute;
  inset: 0;
  margin: auto;
  width: 16px;
  height: 16px;
  border: 2px solid white;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 600ms linear infinite;
}
```

## Responsive Behavior

### Breakpoint System
```css
/* Mobile First */
.component {
  /* Base mobile styles */
}

/* Tablet */
@media (min-width: 640px) {
  .component {
    /* Tablet adjustments */
  }
}

/* Desktop */
@media (min-width: 1024px) {
  .component {
    /* Desktop layout */
  }
}

/* Wide */
@media (min-width: 1280px) {
  .component {
    /* Wide screen optimizations */
  }
}
```

### Responsive Patterns
```css
/* Stack to inline */
.actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

@media (min-width: 640px) {
  .actions {
    flex-direction: row;
  }
}

/* Grid adaptation */
.memory-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-3);
}

@media (min-width: 640px) {
  .memory-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .memory-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

## Usage Guidelines

### Do
- Use components consistently across all pages
- Follow the established patterns
- Maintain semantic HTML structure
- Test with keyboard and screen readers
- Consider mobile experience first

### Don't
- Create one-off variations
- Override core component styles
- Mix component systems
- Ignore accessibility requirements
- Break established patterns

### Component Selection
- **MemoryCard**: For displaying memories in lists/grids
- **DataTable**: For tabular data with sorting/filtering
- **StatCard**: For dashboard metrics and KPIs
- **Modal**: For critical user decisions
- **EmptyState**: When no data is available
- **LoadingState**: During data fetching
- **ErrorState**: When operations fail

This component library ensures visual and behavioral consistency across all Second Brain interfaces.