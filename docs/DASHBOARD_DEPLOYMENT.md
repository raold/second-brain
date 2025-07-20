# Dashboard Deployment Guide

This guide covers the development dashboard hosting solutions for Second Brain v2.6.0-dev.

> **Development Branch**: You are viewing documentation for the active development version on `develop` branch. Features are experimental and under active research.

## 🚀 Quick Start

### Development (Hot Reload)
```powershell
# Windows PowerShell
.\dashboard.ps1 dev

# Cross-platform Python
python scripts/dashboard/deploy.py dev
```

### Production Build
```powershell
# Windows PowerShell  
.\dashboard.ps1 build

# Cross-platform Python
python scripts/dashboard/deploy.py build
```

### GitHub Pages Deployment
```powershell
# Windows PowerShell
.\dashboard.ps1 pages

# Cross-platform Python
python scripts/dashboard/deploy.py pages
```

## 🏗️ Architecture Overview

### Three Deployment Options

1. **Development Server** (`dev_server.py`)
   - Hot reload on file changes
   - CORS support for development
   - Automatic git stats regeneration
   - Graceful shutdown handling

2. **GitHub Pages** (`.github/workflows/deploy-dashboard.yml`)
   - Automatic deployment on push
   - Fresh git statistics generation
   - Static hosting with CDN performance
   - No server management required

3. **Production Build** (`deploy.py build`)
   - Optimized static files
   - Relative path corrections
   - Production-ready assets

## 📁 File Structure

```
scripts/dashboard/
├── dev_server.py          # Hot-reload development server
├── deploy.py              # Multi-environment deployment manager
└── server_manager.py      # Legacy server (backwards compatibility)

.github/workflows/
└── deploy-dashboard.yml   # GitHub Actions deployment

dashboard.ps1              # Windows PowerShell interface
dashboard.bat              # Windows batch file (legacy)

static/
├── dashboard.html         # Main dashboard (enhanced for GitHub Pages)
├── *.css                  # Stylesheets  
└── *.js                   # JavaScript files

dashboard_data/
├── git_stats.json         # Real repository statistics
├── project_data.json      # Project metadata
└── *.json                 # Other data files
```

## 🛠️ Development Workflow

### Hot Reload Development
The new development server watches for changes in:
- `static/` - Dashboard HTML, CSS, JS
- `dashboard_data/` - Data files
- `scripts/development/` - Data generation scripts
- `scripts/dashboard/` - Dashboard management scripts

When files change, the server automatically:
1. Regenerates git statistics
2. Updates project metadata  
3. Triggers browser refresh (if using live reload client)

### Development Server Features
- **File Watching**: Automatic regeneration on changes
- **CORS Support**: Allows cross-origin development
- **Custom Routing**: `/` and `/dashboard` both serve dashboard
- **Graceful Shutdown**: Proper cleanup on Ctrl+C
- **Error Handling**: Robust error reporting and recovery

## 🌐 GitHub Pages Setup

### Automatic Deployment
The GitHub Actions workflow triggers on:
- Push to `main` or `develop` branches
- Changes to dashboard-related files
- Manual workflow dispatch

### Deployment Process
1. **Checkout**: Get repository with commit history
2. **Generate Data**: Fresh git statistics and metadata
3. **Build**: Prepare static files for hosting
4. **Deploy**: Upload to GitHub Pages

### GitHub Pages URL
After deployment: `https://raold.github.io/second-brain/`

## 🔧 Configuration

### Environment Variables
The system uses centralized configuration through `app/config.py`:
- Database settings
- Security configurations  
- Feature flags
- Environment detection

### Dashboard Data Sources
- **Git Statistics**: Real commit history, additions, deletions
- **Project Metadata**: Version, description, build info
- **Research Progress**: Hypothesis tracking, validation results
- **Performance Metrics**: System benchmarks and optimization data

## 📊 Dashboard Features

### Real Development Statistics
- **Commit History**: Timeline of development activity
- **Code Changes**: Lines added, deleted, modified over time
- **Branch Activity**: Development across different branches
- **Contributor Metrics**: Team development patterns

### Research Progress Tracking
- **Hypothesis Validation**: Success/failure rates
- **Cognitive Benchmarks**: Human correlation scores
- **Literature Integration**: Research paper implementation status
- **Energy Efficiency**: Performance optimization metrics

## 🚨 Troubleshooting

### Common Issues

#### Port Already in Use
```powershell
# Stop existing servers
.\dashboard.ps1 stop

# Or specify different port
.\dashboard.ps1 dev -Port 3000
```

#### Missing Dependencies
```powershell
# Install required packages
.\dashboard.ps1 install
```

#### GitHub Pages Not Updating
1. Check Actions tab in GitHub repository
2. Verify workflow permissions (Settings > Pages > Source: GitHub Actions)
3. Ensure branch protection doesn't block automatic commits

#### Development Server Not Reloading
1. Check file permissions in watched directories
2. Verify `watchdog` package is installed
3. Try disabling antivirus real-time scanning for project directory

### Legacy Compatibility
The PowerShell script supports backwards compatibility:
```powershell
# Legacy commands still work
.\dashboard.ps1 start      # Uses legacy server manager
.\dashboard.ps1 legacy start  # Explicit legacy mode
```

## 🔄 Migration from Old System

### From Manual Server Management
**Old Way:**
```powershell
# Find and kill process manually
netstat -ano | findstr :8000
taskkill /PID <pid> /F
python dashboard.py
```

**New Way:**
```powershell
# One command development
.\dashboard.ps1 dev
```

### From Static File Hosting
**Old Way:**
- Manual file copying
- Manual server restarts
- Manual path updates

**New Way:**
- Automatic deployment on git push
- Hot reload during development
- Automatic path correction for different environments

## 🎯 Best Practices

### Development
1. **Use Hot Reload**: `.\dashboard.ps1 dev` for active development
2. **Test Production Builds**: `.\dashboard.ps1 build` before deployment
3. **Monitor File Changes**: Watch console for regeneration messages
4. **Clean Shutdown**: Always use Ctrl+C to stop servers gracefully

### Deployment
1. **GitHub Pages**: Best for public dashboards, zero server maintenance
2. **Production Build**: For custom hosting or integration
3. **Development Mode**: Never use in production (has CORS, debug features)

### Performance
1. **Static Assets**: Use CDN-hosted libraries (Chart.js, D3.js)
2. **Data Caching**: Git statistics cached until code changes
3. **Lazy Loading**: Dashboard loads components on demand
4. **Compression**: GitHub Pages automatically compresses assets

## 📈 Future Enhancements

### Planned Features
- **Real-time Updates**: WebSocket connection for live data
- **Multi-environment**: Separate dev/staging/production dashboards
- **User Authentication**: Secure dashboards with GitHub OAuth
- **Custom Themes**: Multiple dashboard themes and layouts
- **Mobile Responsive**: Improved mobile dashboard experience

### Research Integration
- **Live Experiment Data**: Real-time research progress
- **Interactive Visualizations**: Explorable research results
- **Collaborative Features**: Multi-researcher dashboard views
- **Publication Integration**: Direct research paper generation

---

## 📞 Support

For issues with the new dashboard system:
1. Check this guide for common solutions
2. Review console output for error messages  
3. Test with legacy mode for comparison: `.\dashboard.ps1 legacy start`
4. Create GitHub issue with reproduction steps

**Enjoy your new elegant dashboard hosting! 🎉**
