# Second Brain Design Language v3.0

This document defines the pixel-perfect design language for the Second Brain application, ensuring absolute consistency across all interfaces for enterprise-grade UX.

---

## 🎨 Design Philosophy

### Core Principles
1. **Consistency Above All** - Every pixel, every interaction, identical behavior
2. **Information Density** - Maximize data-ink ratio (Tufte principle)
3. **Accessibility First** - WCAG 2.1 AA compliant
4. **Performance Optimized** - Sub-100ms interactions
5. **Maintainability** - Single source of truth for all design decisions

### Design Pillars
- **Predictability**: Users know exactly what will happen
- **Efficiency**: Minimum cognitive load, maximum productivity
- **Scalability**: Design patterns that work from 1 to 1M items
- **Adaptability**: Responsive without compromise

---

## 📐 Grid System

### Base Grid
- **Unit**: 4px base unit (all measurements divisible by 4)
- **Columns**: 12-column grid with 24px gutters
- **Breakpoints**:
  - Mobile: 320px - 639px (4 columns)
  - Tablet: 640px - 1023px (8 columns)
  - Desktop: 1024px - 1439px (12 columns)
  - Wide: 1440px+ (12 columns, max-width: 1440px)

### Spacing Scale
```
--space-0: 0px      (0rem)
--space-1: 4px      (0.25rem)
--space-2: 8px      (0.5rem)
--space-3: 12px     (0.75rem)
--space-4: 16px     (1rem)
--space-5: 20px     (1.25rem)
--space-6: 24px     (1.5rem)
--space-8: 32px     (2rem)
--space-10: 40px    (2.5rem)
--space-12: 48px    (3rem)
--space-16: 64px    (4rem)
--space-20: 80px    (5rem)
--space-24: 96px    (6rem)
```

### Layout Containers
```
--container-xs: 480px
--container-sm: 640px
--container-md: 768px
--container-lg: 1024px
--container-xl: 1280px
--container-2xl: 1440px
```

---

## 🔤 Typography

### Type Scale (1.25 Major Third)
```
--text-xs: 10px     (0.625rem)   // Annotations, labels
--text-sm: 13px     (0.8125rem)  // Secondary text, captions
--text-base: 16px   (1rem)       // Body text
--text-lg: 20px     (1.25rem)    // Subheadings
--text-xl: 25px     (1.5625rem)  // Section headers
--text-2xl: 31px    (1.9375rem)  // Page titles
--text-3xl: 39px    (2.4375rem)  // Hero text
```

### Font Stack
```css
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace;
```

### Line Heights
```
--leading-none: 1
--leading-tight: 1.25
--leading-snug: 1.375
--leading-normal: 1.5
--leading-relaxed: 1.625
--leading-loose: 2
```

### Font Weights
```
--font-normal: 400
--font-medium: 500
--font-semibold: 600
--font-bold: 700
```

---

## 🎨 Color System

### Gruvbox Dark Theme
```css
/* Background Hierarchy */
--color-bg-primary: #1d2021     /* Main background */
--color-bg-secondary: #282828   /* Cards, panels */
--color-bg-tertiary: #32302f    /* Hover states */
--color-bg-quaternary: #3c3836  /* Active states */

/* Text Hierarchy */
--color-text-primary: #fbf1c7   /* Primary text */
--color-text-secondary: #ebdbb2 /* Secondary text */
--color-text-tertiary: #d5c4a1  /* Muted text */
--color-text-quaternary: #bdae93 /* Disabled text */

/* Semantic Colors */
--color-primary: #8ec07c        /* Aqua - Primary actions */
--color-success: #b8bb26        /* Green - Success states */
--color-warning: #fabd2f        /* Yellow - Warning states */
--color-danger: #fb4934         /* Red - Error states */
--color-info: #83a598           /* Blue - Information */

/* Border Colors */
--color-border-subtle: #3c3836
--color-border-default: #504945
--color-border-strong: #665c54
```

---

## 🧩 Component Architecture

### Component Naming Convention
```
[Component]-[Variant]-[State]-[Size]

Examples:
- btn-primary-hover-lg
- card-metric-active-sm
- input-text-focus-base
```

### Component Hierarchy

#### 1. Atoms (Indivisible)
- Buttons
- Inputs
- Labels
- Icons
- Badges

#### 2. Molecules (Simple Combinations)
- Form Groups (label + input)
- Metric Cards (label + value + chart)
- Navigation Items (icon + text + badge)
- Table Cells (text + status indicator)

#### 3. Organisms (Complex Components)
- Navigation Bar
- Data Tables
- Dashboard Grids
- Search Interface
- Modal Dialogs

#### 4. Templates (Page Structures)
- Dashboard Layout
- Documentation Layout
- Settings Layout
- API Explorer Layout

### Component States
Every interactive component must define:
1. **Default** - Resting state
2. **Hover** - Mouse over
3. **Active** - Being clicked
4. **Focus** - Keyboard navigation
5. **Disabled** - Non-interactive
6. **Loading** - Async operation
7. **Error** - Invalid state

---

## 📏 Standardized Components

### Navigation Bar
```css
Height: 64px (fixed)
Padding: 0 32px
Background: var(--color-bg-primary)
Border-bottom: 1px solid var(--color-border-subtle)
Z-index: 1000

Logo:
- Font-size: 24px
- Font-weight: 700
- Spacing: 8px gap between icon and text

Links:
- Font-size: 16px
- Font-weight: 500
- Spacing: 32px between items
- Height: 100% (64px)
- Active indicator: 3px bottom border
```

### Buttons
```css
Sizes:
- Small: height 32px, padding 0 12px, font-size 13px
- Medium: height 40px, padding 0 16px, font-size 16px
- Large: height 48px, padding 0 24px, font-size 16px

Border-radius: 6px (all sizes)
Transition: all 150ms ease
Min-width: 64px
```

### Cards
```css
Padding: 16px (compact), 24px (normal), 32px (spacious)
Border: 1px solid var(--color-border-subtle)
Border-radius: 8px
Background: var(--color-bg-secondary)
Shadow (hover): 0 4px 12px rgba(0,0,0,0.15)
```

### Form Inputs
```css
Height: 40px
Padding: 0 12px
Border: 1px solid var(--color-border-default)
Border-radius: 6px
Font-size: 16px
Transition: all 150ms ease

Focus:
- Border-color: var(--color-primary)
- Box-shadow: 0 0 0 3px rgba(142, 192, 124, 0.1)
```

### Data Tables
```css
Header:
- Height: 48px
- Background: var(--color-bg-tertiary)
- Font-weight: 600
- Sticky positioning

Rows:
- Height: 48px (compact), 56px (normal)
- Border-bottom: 1px solid var(--color-border-subtle)
- Hover background: var(--color-bg-tertiary)

Cells:
- Padding: 0 16px
- Text overflow: ellipsis
```

---

## 🎯 Interaction Patterns

### Click Targets
- Minimum size: 44x44px (mobile), 32x32px (desktop)
- Touch targets: 48x48px minimum
- Spacing between targets: 8px minimum

### Hover States
- Transition duration: 150ms
- Elevation change: translateY(-2px)
- Opacity change: 0.8 for secondary elements

### Focus Indicators
- Style: 2px solid var(--color-primary)
- Offset: 2px
- Border-radius: Inherit from element
- Visible in all color modes

### Loading States
- Skeleton screens for content
- Spinner for actions
- Progress bars for deterministic operations
- Pulse animation for indeterminate states

---

## 📱 Responsive Behavior

### Breakpoint Rules
```scss
// Mobile First
@media (min-width: 640px) { }  // Tablet
@media (min-width: 1024px) { } // Desktop
@media (min-width: 1440px) { } // Wide

// Component-specific overrides
.component {
  // Mobile: Stack vertically
  flex-direction: column;
  
  @media (min-width: 640px) {
    // Tablet: Side by side
    flex-direction: row;
  }
}
```

### Content Reflow
1. **Navigation**: Hamburger menu < 640px
2. **Tables**: Horizontal scroll with sticky first column
3. **Cards**: 1 column → 2 columns → 3-4 columns
4. **Forms**: Full width → max-width 480px

---

## ⚡ Performance Standards

### CSS Architecture
1. **Critical CSS**: < 14KB inline
2. **Component CSS**: Lazy loaded
3. **Utility classes**: Composed at build time
4. **No !important**: Specificity through architecture

### Animation Performance
- Use `transform` and `opacity` only
- Will-change for heavy animations
- 60fps target (16.67ms per frame)
- GPU acceleration for transforms

### Loading Performance
- First Paint: < 1s
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3s
- Cumulative Layout Shift: < 0.1

---

## 🔧 Implementation Guidelines

### CSS Variable Naming
```css
--[property]-[context]-[variant]-[state]

Examples:
--color-bg-primary
--space-component-lg
--shadow-card-hover
--duration-transition-fast
```

### Class Naming (BEM-inspired)
```css
.block__element--modifier

Examples:
.nav__link--active
.card__header--compressed
.btn__icon--loading
```

### State Management
```css
/* Attribute-based states */
[data-state="loading"] { }
[data-theme="dark"] { }
[data-density="compact"] { }

/* Pseudo-class states */
:hover, :focus, :active
:disabled, :checked, :invalid
```

---

## 🛡️ Accessibility Requirements

### Color Contrast
- Normal text: 4.5:1 minimum
- Large text: 3:1 minimum
- Interactive elements: 3:1 minimum
- Focus indicators: 3:1 minimum

### Keyboard Navigation
- All interactive elements reachable
- Logical tab order
- Skip links for main content
- Escape key closes modals

### Screen Reader Support
- Semantic HTML structure
- ARIA labels where needed
- Live regions for updates
- Descriptive link text

### Motion Preferences
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 📋 Quality Checklist

Before any UI component ships:

- [ ] Pixel-perfect at all breakpoints
- [ ] All states implemented (hover, focus, active, disabled)
- [ ] Keyboard navigable
- [ ] Screen reader tested
- [ ] Color contrast validated
- [ ] Performance profiled
- [ ] Cross-browser tested
- [ ] Documentation complete
- [ ] Design tokens used (no magic numbers)
- [ ] Consistent with existing patterns

---

## 🔄 Versioning

Design Language Version: 3.0.0
- Major: Breaking visual changes
- Minor: New components/patterns
- Patch: Bug fixes/refinements

Last Updated: 2024-01-27
Next Review: 2024-04-27