"""
Main application entry point using factory pattern
"""

import os
from app.factory import create_app

# Determine environment
environment = os.getenv("ENVIRONMENT", "development")

# Create app using factory
app = create_app(environment)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=environment == "development"
    )