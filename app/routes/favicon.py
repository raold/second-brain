"""
Favicon route - serves brain emoji as favicon for all pages
"""

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()

# SVG favicon with brain emoji
BRAIN_FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<text y=".9em" font-size="90">🧠</text>
</svg>"""

@router.get("/favicon.ico")
async def favicon():
    """Serve brain emoji as favicon"""
    return Response(content=BRAIN_FAVICON_SVG, media_type="image/svg+xml")

@router.get("/favicon.svg")
async def favicon_svg():
    """Serve brain emoji as SVG favicon"""
    return Response(content=BRAIN_FAVICON_SVG, media_type="image/svg+xml")
