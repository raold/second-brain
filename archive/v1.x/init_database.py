#!/usr/bin/env python3
"""
Database initialization script for Second Brain application.
Sets up Qdrant vector database and PostgreSQL with proper configuration.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import config
from app.storage.database_setup import DatabaseSetup
from app.utils.logger import logger


async def check_docker_services():
    """Check if Docker services are running."""
    try:
        import subprocess
        
        # Check if Docker is running
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("Docker is not running. Please start Docker first.")
            return False
        
        # Check if our services are running
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'], 
                               capture_output=True, text=True)
        
        services = result.stdout
        qdrant_running = 'qdrant' in services
        postgres_running = 'postgres' in services
        
        if not qdrant_running or not postgres_running:
            logger.warning("Database services not detected. You may need to start them:")
            logger.warning("  docker-compose up -d")
            
        return True
        
    except Exception as e:
        logger.error(f"Error checking Docker services: {e}")
        return False


async def create_environment_file():
    """Create a sample .env file if it doesn't exist."""
    env_file = Path('.env')
    if env_file.exists():
        logger.info("Environment file already exists")
        return
    
    env_content = f"""# Second Brain Environment Configuration
# Database Configuration
POSTGRES_HOST={config.postgres['host']}
POSTGRES_PORT={config.postgres['port']}
POSTGRES_DB={config.postgres['database']}
POSTGRES_USER={config.postgres['user']}
POSTGRES_PASSWORD={config.postgres['password']}

# Qdrant Configuration
QDRANT_HOST={config.qdrant['host']}
QDRANT_PORT={config.qdrant['port']}
QDRANT_COLLECTION={config.qdrant['collection']}

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here

# Application Configuration
API_TOKENS=dev-token,admin-token
DEBUG=true
LOG_LEVEL=INFO

# Cache Configuration
CACHE_ENABLED=true
CACHE_SIZE=1000

# Model Versions
MODEL_VERSION_LLM=gpt-4o
MODEL_VERSION_EMBEDDING=text-embedding-3-small
"""
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        logger.info(f"Created sample environment file: {env_file}")
        logger.warning("⚠️  Please update .env file with your actual configuration!")
    except Exception as e:
        logger.error(f"Failed to create environment file: {e}")


async def setup_data_directories():
    """Create necessary data directories."""
    directories = [
        Path('app/data'),
        Path('app/data/memories'),
        Path('logs'),
        Path('qdrant_data'),
    ]
    
    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {directory}")
        except Exception as e:
            logger.error(f"Failed to create directory {directory}: {e}")


async def main():
    """Main initialization function."""
    print("🚀 Second Brain Database Initialization")
    print("=" * 50)
    
    # Check configuration
    logger.info("Checking configuration...")
    config.validate()
    
    # Check Docker services
    logger.info("Checking Docker services...")
    docker_ok = await check_docker_services()
    
    # Create environment file
    logger.info("Setting up environment...")
    await create_environment_file()
    
    # Setup data directories
    logger.info("Creating data directories...")
    await setup_data_directories()
    
    # Initialize database setup
    logger.info("Initializing database setup...")
    db_setup = DatabaseSetup()
    
    try:
        # Setup databases
        logger.info("Setting up databases...")
        results = await db_setup.setup_all()
        
        # Print results
        print("\n" + "="*50)
        print("DATABASE INITIALIZATION RESULTS")
        print("="*50)
        
        for db_name, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"{db_name.upper()}: {status}")
        
        # Get detailed status
        logger.info("Getting database status...")
        status = await db_setup.get_database_status()
        
        print("\nDETAILED STATUS:")
        print("-" * 30)
        
        # Qdrant status
        qdrant = status['qdrant']
        print(f"Qdrant ({qdrant['host']}:{qdrant['port']}):")
        print(f"  ✓ Connected: {qdrant['connected']}")
        print(f"  ✓ Collection exists: {qdrant['collection_exists']}")
        print(f"  ✓ Collection size: {qdrant['collection_size']}")
        
        # PostgreSQL status
        postgres = status['postgres']
        print(f"\nPostgreSQL ({postgres['host']}:{postgres['port']}):")
        print(f"  ✓ Connected: {postgres['connected']}")
        print(f"  ✓ Tables exist: {postgres['tables_exist']}")
        
        # Overall status
        all_success = all(results.values())
        
        print("\n" + "="*50)
        if all_success:
            print("🎉 DATABASE INITIALIZATION COMPLETED SUCCESSFULLY!")
            print("\nNext steps:")
            print("1. Update .env file with your OpenAI API key")
            print("2. Start the application: python -m uvicorn app.main:app --reload")
            print("3. Check health: curl http://localhost:8000/health")
            return_code = 0
        else:
            print("⚠️  SOME COMPONENTS FAILED TO INITIALIZE")
            print("\nTroubleshooting:")
            print("1. Check Docker services are running: docker-compose up -d")
            print("2. Verify environment variables in .env file")
            print("3. Check logs for detailed error messages")
            return_code = 1
            
        print("="*50)
        return return_code
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"\n❌ INITIALIZATION FAILED: {e}")
        return 1
    finally:
        await db_setup.close()


if __name__ == "__main__":
    try:
        return_code = asyncio.run(main())
        sys.exit(return_code)
    except KeyboardInterrupt:
        print("\n⚠️  Initialization interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
