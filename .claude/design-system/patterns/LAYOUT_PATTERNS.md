# Second Brain Layout Patterns

## Master Layout

All pages share this foundational structure:

```html
<div class="app-root">
  <!-- Global Navigation -->
  <header class="app-header">
    <nav class="global-nav">
      <!-- Logo, nav links, actions -->
    </nav>
  </header>
  
  <!-- Main Content Area -->
  <main class="app-main">
    <!-- Page-specific content -->
  </main>
  
  <!-- Global Footer (minimal) -->
  <footer class="app-footer">
    <!-- Version, status, legal -->
  </footer>
</div>
```

### CSS Grid Structure
```css
.app-root {
  display: grid;
  grid-template-rows: 64px 1fr auto;
  min-height: 100vh;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 40;
  background: white;
  border-bottom: 1px solid var(--color-neutral-200);
}

.app-main {
  background: var(--color-neutral-50);
}

.app-footer {
  background: white;
  border-top: 1px solid var(--color-neutral-200);
  padding: var(--space-3) var(--space-4);
}
```

## Page Layouts

### 1. Dashboard Layout
```html
<main class="app-main">
  <div class="dashboard-layout">
    <!-- Page Header -->
    <header class="page-header">
      <h1>Dashboard</h1>
      <div class="header-actions">
        <button class="button primary">Create Memory</button>
      </div>
    </header>
    
    <!-- Stats Grid -->
    <section class="stats-grid">
      <div class="stat-card"><!-- Total memories --></div>
      <div class="stat-card"><!-- This week --></div>
      <div class="stat-card"><!-- Importance avg --></div>
      <div class="stat-card"><!-- Connections --></div>
    </section>
    
    <!-- Content Grid -->
    <div class="dashboard-grid">
      <!-- Recent Memories -->
      <section class="dashboard-section">
        <h2>Recent Memories</h2>
        <div class="memory-list">
          <!-- Memory cards -->
        </div>
      </section>
      
      <!-- Insights -->
      <section class="dashboard-section">
        <h2>Insights</h2>
        <div class="insight-cards">
          <!-- Insight widgets -->
        </div>
      </section>
    </div>
  </div>
</main>
```

```css
.dashboard-layout {
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--space-4);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-6);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--space-4);
}

@media (max-width: 1023px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
```

### 2. Browse Layout (Memories, Search)
```html
<main class="app-main">
  <div class="browse-layout">
    <!-- Page Header with Search -->
    <header class="browse-header">
      <div class="header-content">
        <h1>Memories</h1>
        <p class="subtitle">1,234 total memories</p>
      </div>
      
      <div class="search-bar">
        <input type="search" placeholder="Search memories...">
        <button class="button primary">Search</button>
      </div>
    </header>
    
    <!-- Filter Sidebar + Results -->
    <div class="browse-content">
      <!-- Filters -->
      <aside class="filter-sidebar">
        <h2>Filters</h2>
        <form class="filter-form">
          <!-- Filter controls -->
        </form>
      </aside>
      
      <!-- Results -->
      <section class="browse-results">
        <!-- View Toggle -->
        <div class="results-header">
          <p class="results-count">Showing 1-20 of 234</p>
          <div class="view-toggle">
            <button aria-label="List view" class="active">
              <svg><!-- List icon --></svg>
            </button>
            <button aria-label="Grid view">
              <svg><!-- Grid icon --></svg>
            </button>
          </div>
        </div>
        
        <!-- Memory List/Grid -->
        <div class="memory-grid">
          <!-- Memory cards -->
        </div>
        
        <!-- Pagination -->
        <nav class="pagination">
          <!-- Page controls -->
        </nav>
      </section>
    </div>
  </div>
</main>
```

```css
.browse-layout {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.browse-header {
  background: white;
  border-bottom: 1px solid var(--color-neutral-200);
  padding: var(--space-4);
}

.search-bar {
  display: flex;
  gap: var(--space-2);
  max-width: 600px;
  margin-top: var(--space-3);
}

.browse-content {
  flex: 1;
  display: grid;
  grid-template-columns: 280px 1fr;
  height: 100%;
}

.filter-sidebar {
  background: white;
  border-right: 1px solid var(--color-neutral-200);
  padding: var(--space-4);
  overflow-y: auto;
}

.browse-results {
  padding: var(--space-4);
  overflow-y: auto;
}

@media (max-width: 767px) {
  .browse-content {
    grid-template-columns: 1fr;
  }
  
  .filter-sidebar {
    position: fixed;
    left: -100%;
    top: 64px;
    bottom: 0;
    width: 280px;
    z-index: 30;
    transition: left 200ms ease-out;
  }
  
  .filter-sidebar.open {
    left: 0;
  }
}
```

### 3. Detail Layout (Memory, Insight Detail)
```html
<main class="app-main">
  <div class="detail-layout">
    <!-- Breadcrumb -->
    <nav class="breadcrumb">
      <!-- Navigation path -->
    </nav>
    
    <!-- Content + Sidebar -->
    <div class="detail-content">
      <!-- Main Content -->
      <article class="detail-main">
        <header class="detail-header">
          <h1>Memory Title</h1>
          <div class="detail-actions">
            <button class="button secondary">Edit</button>
            <button class="button secondary">Share</button>
          </div>
        </header>
        
        <div class="detail-body">
          <!-- Content -->
        </div>
      </article>
      
      <!-- Metadata Sidebar -->
      <aside class="detail-sidebar">
        <section class="sidebar-section">
          <h3>Properties</h3>
          <dl class="property-list">
            <dt>Type</dt>
            <dd>Episodic</dd>
            <dt>Created</dt>
            <dd>Jan 15, 2024</dd>
            <dt>Importance</dt>
            <dd>85%</dd>
          </dl>
        </section>
        
        <section class="sidebar-section">
          <h3>Connections</h3>
          <ul class="connection-list">
            <!-- Related memories -->
          </ul>
        </section>
      </aside>
    </div>
  </div>
</main>
```

```css
.detail-layout {
  max-width: 1280px;
  margin: 0 auto;
  padding: var(--space-4);
}

.detail-content {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: var(--space-4);
  margin-top: var(--space-4);
}

.detail-main {
  background: white;
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.detail-sidebar {
  space-y: var(--space-4);
}

.sidebar-section {
  background: white;
  border-radius: var(--radius-md);
  padding: var(--space-4);
  margin-bottom: var(--space-3);
}

@media (max-width: 1023px) {
  .detail-content {
    grid-template-columns: 1fr;
  }
  
  .detail-sidebar {
    margin-top: var(--space-4);
  }
}
```

### 4. Documentation Layout
```html
<main class="app-main">
  <div class="docs-layout">
    <!-- Docs Navigation -->
    <nav class="docs-nav">
      <div class="nav-section">
        <h3>Getting Started</h3>
        <ul>
          <li><a href="#" class="active">Introduction</a></li>
          <li><a href="#">Quick Start</a></li>
          <li><a href="#">Installation</a></li>
        </ul>
      </div>
      <!-- More sections -->
    </nav>
    
    <!-- Docs Content -->
    <article class="docs-content">
      <header class="docs-header">
        <h1>Introduction</h1>
        <p class="lead">
          Welcome to Second Brain documentation
        </p>
      </header>
      
      <div class="docs-body">
        <!-- Markdown content -->
      </div>
      
      <!-- Page Navigation -->
      <footer class="docs-footer">
        <a href="#" class="prev-link">
          ← Previous: Overview
        </a>
        <a href="#" class="next-link">
          Next: Quick Start →
        </a>
      </footer>
    </article>
    
    <!-- Table of Contents -->
    <aside class="docs-toc">
      <h4>On this page</h4>
      <nav>
        <ul>
          <li><a href="#overview">Overview</a></li>
          <li><a href="#features">Features</a></li>
          <li><a href="#getting-started">Getting Started</a></li>
        </ul>
      </nav>
    </aside>
  </div>
</main>
```

```css
.docs-layout {
  display: grid;
  grid-template-columns: 280px 1fr 200px;
  gap: var(--space-6);
  max-width: 1440px;
  margin: 0 auto;
  padding: var(--space-4);
}

.docs-nav {
  position: sticky;
  top: 80px;
  height: calc(100vh - 96px);
  overflow-y: auto;
}

.docs-content {
  max-width: 45rem;
  min-width: 0;
}

.docs-toc {
  position: sticky;
  top: 80px;
  height: fit-content;
}

@media (max-width: 1279px) {
  .docs-layout {
    grid-template-columns: 280px 1fr;
  }
  
  .docs-toc {
    display: none;
  }
}

@media (max-width: 767px) {
  .docs-layout {
    grid-template-columns: 1fr;
  }
  
  .docs-nav {
    display: none;
  }
}
```

### 5. Settings Layout
```html
<main class="app-main">
  <div class="settings-layout">
    <header class="settings-header">
      <h1>Settings</h1>
    </header>
    
    <div class="settings-content">
      <!-- Settings Navigation -->
      <nav class="settings-nav">
        <ul>
          <li>
            <a href="#profile" class="active">Profile</a>
          </li>
          <li>
            <a href="#preferences">Preferences</a>
          </li>
          <li>
            <a href="#security">Security</a>
          </li>
          <li>
            <a href="#data">Data & Privacy</a>
          </li>
        </ul>
      </nav>
      
      <!-- Settings Panels -->
      <div class="settings-panels">
        <section id="profile" class="settings-panel">
          <h2>Profile Settings</h2>
          <form class="settings-form">
            <!-- Form fields -->
          </form>
        </section>
      </div>
    </div>
  </div>
</main>
```

```css
.settings-layout {
  max-width: 1024px;
  margin: 0 auto;
  padding: var(--space-4);
}

.settings-content {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: var(--space-6);
  margin-top: var(--space-4);
}

.settings-nav {
  position: sticky;
  top: 80px;
}

.settings-panel {
  background: white;
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}
```

## Responsive Strategies

### Mobile Navigation
```css
/* Mobile menu toggle */
@media (max-width: 767px) {
  .global-nav {
    position: fixed;
    inset: 0;
    background: white;
    transform: translateX(-100%);
    transition: transform 200ms ease-out;
  }
  
  .global-nav.open {
    transform: translateX(0);
  }
  
  .mobile-menu-toggle {
    display: block;
  }
}
```

### Content Reflow
```css
/* Stack sidebars on mobile */
@media (max-width: 767px) {
  .two-column-layout {
    grid-template-columns: 1fr;
  }
  
  .sidebar {
    order: -1; /* Move important filters above */
  }
}

/* Collapse margins on mobile */
@media (max-width: 639px) {
  .page-padding {
    padding: var(--space-3);
  }
}
```

### Touch Optimization
```css
/* Larger touch targets on mobile */
@media (max-width: 767px) {
  .button {
    min-height: 48px;
    padding: 12px 20px;
  }
  
  .clickable-row {
    padding: var(--space-3);
  }
}
```

## Common Patterns

### Page Headers
Every major page has a consistent header:
```html
<header class="page-header">
  <div class="header-main">
    <h1 class="page-title">Page Title</h1>
    <p class="page-description">Brief description of the page purpose</p>
  </div>
  <div class="header-actions">
    <!-- Primary page actions -->
  </div>
</header>
```

### Empty States
Consistent messaging when no content:
```html
<div class="empty-state">
  <svg class="empty-illustration"><!-- Contextual graphic --></svg>
  <h3>No memories found</h3>
  <p>Try adjusting your filters or create a new memory</p>
  <button class="button primary">Create Memory</button>
</div>
```

### Loading States
Skeleton screens that match final layout:
```html
<div class="skeleton-list">
  <div class="skeleton-item">
    <div class="skeleton skeleton-title"></div>
    <div class="skeleton skeleton-text"></div>
    <div class="skeleton skeleton-meta"></div>
  </div>
  <!-- Repeat for expected count -->
</div>
```

This ensures every page in Second Brain follows the same structural patterns while allowing for page-specific needs.