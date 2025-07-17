"""
Database setup and initialization for Second Brain application.
Handles Qdrant vector database and PostgreSQL setup.
"""
import asyncio
import sys
from typing import Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import CollectionStatus, Distance, VectorParams
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import config
from app.utils.logger import logger


class DatabaseSetup:
    """Database setup and health check manager."""
    
    def __init__(self):
        self.config = config
        self.qdrant_client = None
        self.postgres_engine = None
        self.postgres_async_engine = None
        
    async def setup_all(self) -> Dict[str, bool]:
        """Setup all databases and return status."""
        results = {}
        
        # Setup Qdrant
        try:
            await self.setup_qdrant()
            results['qdrant'] = True
            logger.info("✅ Qdrant setup completed successfully")
        except Exception as e:
            logger.error(f"❌ Qdrant setup failed: {e}")
            results['qdrant'] = False
            
        # Setup PostgreSQL
        try:
            await self.setup_postgres()
            results['postgres'] = True
            logger.info("✅ PostgreSQL setup completed successfully")
        except Exception as e:
            logger.error(f"❌ PostgreSQL setup failed: {e}")
            results['postgres'] = False
            
        return results
    
    async def setup_qdrant(self) -> None:
        """Setup Qdrant vector database."""
        try:
            # Initialize client
            self.qdrant_client = QdrantClient(
                host=self.config.qdrant['host'],
                port=self.config.qdrant['port'],
                timeout=self.config.qdrant['timeout']
            )
            
            # Test connection
            health = await self.check_qdrant_health()
            if not health:
                raise Exception("Qdrant health check failed")
            
            # Create collection if it doesn't exist
            await self.create_qdrant_collection()
            
            logger.info(f"Qdrant connected: {self.config.qdrant['host']}:{self.config.qdrant['port']}")
            
        except Exception as e:
            logger.error(f"Failed to setup Qdrant: {e}")
            raise
    
    async def setup_postgres(self) -> None:
        """Setup PostgreSQL database."""
        try:
            # Create engines
            sync_url = self.config.get_postgres_url().replace('+asyncpg', '')
            async_url = self.config.get_postgres_url()
            
            self.postgres_engine = create_engine(sync_url)
            self.postgres_async_engine = create_async_engine(async_url)
            
            # Test connection
            health = await self.check_postgres_health()
            if not health:
                raise Exception("PostgreSQL health check failed")
            
            # Create tables if needed
            await self.create_postgres_tables()
            
            logger.info(f"PostgreSQL connected: {self.config.postgres['host']}:{self.config.postgres['port']}")
            
        except Exception as e:
            logger.error(f"Failed to setup PostgreSQL: {e}")
            raise
    
    async def check_qdrant_health(self) -> bool:
        """Check Qdrant health."""
        try:
            if not self.qdrant_client:
                return False
                
            # Simple health check
            collections = self.qdrant_client.get_collections()
            logger.debug(f"Qdrant collections: {len(collections.collections)}")
            return True
            
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
    
    async def check_postgres_health(self) -> bool:
        """Check PostgreSQL health."""
        try:
            if not self.postgres_async_engine:
                return False
                
            async with self.postgres_async_engine.begin() as conn:
                result = await conn.execute(text("SELECT 1"))
                return result.scalar() == 1
                
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False
    
    async def create_qdrant_collection(self) -> None:
        """Create Qdrant collection if it doesn't exist."""
        try:
            collection_name = self.config.qdrant['collection']
            
            # Check if collection exists
            try:
                collection_info = self.qdrant_client.get_collection(collection_name)
                if collection_info.status == CollectionStatus.GREEN:
                    logger.info(f"Qdrant collection '{collection_name}' already exists")
                    return
            except UnexpectedResponse:
                # Collection doesn't exist, create it
                pass
            
            # Create collection with vector configuration
            self.qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=1536,  # OpenAI text-embedding-3-small dimension
                    distance=Distance.COSINE
                )
            )
            
            logger.info(f"Created Qdrant collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to create Qdrant collection: {e}")
            raise
    
    async def create_postgres_tables(self) -> None:
        """Create PostgreSQL tables if they don't exist."""
        try:
            # Import models to ensure tables are created
            from app.models import Base
            
            # Create tables
            async with self.postgres_async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("PostgreSQL tables created/verified")
            
        except Exception as e:
            logger.error(f"Failed to create PostgreSQL tables: {e}")
            raise
    
    async def get_database_status(self) -> Dict[str, Any]:
        """Get comprehensive database status."""
        status = {
            'qdrant': {
                'connected': False,
                'collection_exists': False,
                'collection_size': 0,
                'host': self.config.qdrant['host'],
                'port': self.config.qdrant['port']
            },
            'postgres': {
                'connected': False,
                'tables_exist': False,
                'host': self.config.postgres['host'],
                'port': self.config.postgres['port']
            }
        }
        
        # Check Qdrant
        try:
            if await self.check_qdrant_health():
                status['qdrant']['connected'] = True
                
                # Check collection
                collection_name = self.config.qdrant['collection']
                try:
                    collection_info = self.qdrant_client.get_collection(collection_name)
                    status['qdrant']['collection_exists'] = True
                    status['qdrant']['collection_size'] = collection_info.points_count or 0
                except UnexpectedResponse:
                    pass
                    
        except Exception as e:
            logger.error(f"Error checking Qdrant status: {e}")
        
        # Check PostgreSQL
        try:
            if await self.check_postgres_health():
                status['postgres']['connected'] = True
                
                # Check if tables exist
                async with self.postgres_async_engine.begin() as conn:
                    result = await conn.execute(text("""
                        SELECT COUNT(*) FROM information_schema.tables 
                        WHERE table_schema = 'public'
                    """))
                    table_count = result.scalar()
                    status['postgres']['tables_exist'] = table_count > 0
                    
        except Exception as e:
            logger.error(f"Error checking PostgreSQL status: {e}")
        
        return status
    
    async def close(self) -> None:
        """Close database connections."""
        if self.qdrant_client:
            try:
                self.qdrant_client.close()
            except Exception as e:
                logger.error(f"Error closing Qdrant client: {e}")
        
        if self.postgres_async_engine:
            try:
                await self.postgres_async_engine.dispose()
            except Exception as e:
                logger.error(f"Error closing PostgreSQL async engine: {e}")
        
        if self.postgres_engine:
            try:
                self.postgres_engine.dispose()
            except Exception as e:
                logger.error(f"Error closing PostgreSQL engine: {e}")


# Global database setup instance
db_setup = DatabaseSetup()


async def main():
    """Main function for running database setup."""
    logger.info("🚀 Starting database setup...")
    
    try:
        # Setup all databases
        results = await db_setup.setup_all()
        
        # Print results
        print("\n" + "="*50)
        print("DATABASE SETUP RESULTS")
        print("="*50)
        
        for db_name, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"{db_name.upper()}: {status}")
        
        # Get detailed status
        status = await db_setup.get_database_status()
        print("\nDETAILED STATUS:")
        print("-" * 30)
        
        # Qdrant status
        qdrant = status['qdrant']
        print(f"Qdrant ({qdrant['host']}:{qdrant['port']}):")
        print(f"  Connected: {qdrant['connected']}")
        print(f"  Collection exists: {qdrant['collection_exists']}")
        print(f"  Collection size: {qdrant['collection_size']}")
        
        # PostgreSQL status
        postgres = status['postgres']
        print(f"\nPostgreSQL ({postgres['host']}:{postgres['port']}):")
        print(f"  Connected: {postgres['connected']}")
        print(f"  Tables exist: {postgres['tables_exist']}")
        
        all_success = all(results.values())
        if all_success:
            print("\n🎉 All databases setup successfully!")
            return 0
        else:
            print("\n⚠️  Some databases failed to setup. Check logs for details.")
            return 1
            
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        print(f"\n❌ Database setup failed: {e}")
        return 1
    finally:
        await db_setup.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
