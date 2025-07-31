"""
Generate PNG favicons from SVG
This script helps generate PNG versions of the favicon for better compatibility.
It requires the cairosvg library: pip install cairosvg

The Second Brain favicon features a pink brain design with AI neural nodes.
"""

from pathlib import Path

# For environments without cairosvg, we'll provide instructions
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except ImportError:
    CAIROSVG_AVAILABLE = False

def generate_favicon_pngs():
    """Generate PNG versions of the favicon from SVG"""

    if not CAIROSVG_AVAILABLE:
        print("Error: cairosvg is not installed.")
        print("\nTo generate PNG favicons, install cairosvg:")
        print("  pip install cairosvg")
        print("\nAlternatively, you can convert SVG to PNG using:")
        print("  - Online converters like svgtopng.com")
        print("  - Design tools like Inkscape, GIMP, or Figma")
        print("  - Browser developer tools (save SVG as image)")
        return

    # Path to SVG and output directory
    svg_path = Path("static/favicon.svg")
    output_dir = Path("static")

    if not svg_path.exists():
        print(f"Error: {svg_path} not found!")
        return

    # Sizes to generate
    sizes = [16, 32, 48, 64, 128, 180, 192, 512]

    print("Generating favicon PNGs from SVG...")

    for size in sizes:
        output_path = output_dir / f"favicon-{size}.png"

        try:
            cairosvg.svg2png(
                url=str(svg_path),
                write_to=str(output_path),
                output_width=size,
                output_height=size
            )
            print(f"✓ Generated {output_path} ({size}x{size})")
        except Exception as e:
            print(f"✗ Failed to generate {size}x{size}: {e}")

    # Special files
    special_files = {
        "apple-touch-icon.png": 180,
        "favicon-192.png": 192,  # Android Chrome
        "favicon-512.png": 512   # PWA
    }

    for filename, size in special_files.items():
        output_path = output_dir / filename
        try:
            cairosvg.svg2png(
                url=str(svg_path),
                write_to=str(output_path),
                output_width=size,
                output_height=size
            )
            print(f"✓ Generated {output_path} ({size}x{size})")
        except Exception as e:
            print(f"✗ Failed to generate {filename}: {e}")

    print("\nFavicon generation complete!")
    print("\nTo use these in your HTML, add:")
    print("""
    <!-- PNG fallbacks for better compatibility -->
    <link rel="icon" type="image/png" sizes="16x16" href="/static/favicon-16.png">
    <link rel="icon" type="image/png" sizes="32x32" href="/static/favicon-32.png">
    <link rel="icon" type="image/png" sizes="48x48" href="/static/favicon-48.png">
    <link rel="apple-touch-icon" sizes="180x180" href="/static/apple-touch-icon.png">
    """)

def create_web_manifest():
    """Create a web app manifest for PWA support"""
    manifest = {
        "name": "Second Brain v3",
        "short_name": "Second Brain",
        "description": "AI-powered memory and knowledge management system",
        "start_url": "/",
        "display": "standalone",
        "theme_color": "#1a1a2e",
        "background_color": "#1a1a2e",
        "icons": [
            {
                "src": "/static/favicon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/favicon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            },
            {
                "src": "/static/favicon.svg",
                "sizes": "any",
                "type": "image/svg+xml"
            }
        ]
    }

    import json
    manifest_path = Path("static/manifest.json")

    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)

    print(f"\n✓ Created {manifest_path}")
    print("\nTo enable PWA support, add to your HTML:")
    print('    <link rel="manifest" href="/static/manifest.json">')


if __name__ == "__main__":
    print("Second Brain v3 - Favicon Generator")
    print("===================================\n")

    generate_favicon_pngs()
    create_web_manifest()

    print("\n✨ Done! Your favicons are ready.")
