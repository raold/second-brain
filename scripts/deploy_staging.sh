#!/bin/bash
# Deploy Second Brain to Staging Environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.staging.yml"
ENV_FILE=".env"
ENV_TEMPLATE=".env.staging"

echo -e "${GREEN}Second Brain Staging Deployment${NC}"
echo "================================="

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

# Check environment file
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_TEMPLATE" ]; then
        echo -e "${YELLOW}Creating .env from template...${NC}"
        cp "$ENV_TEMPLATE" "$ENV_FILE"
        echo -e "${RED}Please edit .env and set your configuration values${NC}"
        exit 1
    else
        echo -e "${RED}Error: No .env file found${NC}"
        exit 1
    fi
fi

# Parse command line arguments
ACTION=${1:-"deploy"}
BUILD_FLAG=""

if [ "$2" == "--build" ]; then
    BUILD_FLAG="--build"
fi

case $ACTION in
    "deploy")
        echo -e "\n${YELLOW}Deploying staging environment...${NC}"
        docker-compose -f "$COMPOSE_FILE" up -d $BUILD_FLAG
        
        echo -e "\n${YELLOW}Waiting for services to be ready...${NC}"
        sleep 10
        
        echo -e "\n${GREEN}Deployment complete!${NC}"
        echo -e "Services available at:"
        echo -e "  - Application: http://localhost:8000"
        echo -e "  - Database Admin: http://localhost:8081"
        echo -e "  - Monitoring: http://localhost:3001"
        ;;
        
    "stop")
        echo -e "\n${YELLOW}Stopping staging environment...${NC}"
        docker-compose -f "$COMPOSE_FILE" stop
        ;;
        
    "down")
        echo -e "\n${YELLOW}Removing staging environment...${NC}"
        docker-compose -f "$COMPOSE_FILE" down
        ;;
        
    "clean")
        echo -e "\n${RED}WARNING: This will delete all staging data!${NC}"
        read -p "Are you sure? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose -f "$COMPOSE_FILE" down -v
            echo -e "${GREEN}Staging environment cleaned${NC}"
        fi
        ;;
        
    "logs")
        SERVICE=${2:-""}
        if [ -z "$SERVICE" ]; then
            docker-compose -f "$COMPOSE_FILE" logs -f
        else
            docker-compose -f "$COMPOSE_FILE" logs -f "$SERVICE"
        fi
        ;;
        
    "status")
        echo -e "\n${YELLOW}Staging environment status:${NC}"
        docker-compose -f "$COMPOSE_FILE" ps
        ;;
        
    "backup")
        echo -e "\n${YELLOW}Creating database backup...${NC}"
        BACKUP_FILE="backup_staging_$(date +%Y%m%d_%H%M%S).sql"
        docker-compose -f "$COMPOSE_FILE" exec -T postgres \
            pg_dump -U secondbrain secondbrain_staging > "$BACKUP_FILE"
        echo -e "${GREEN}Backup saved to: $BACKUP_FILE${NC}"
        ;;
        
    "migrate")
        echo -e "\n${YELLOW}Running database migrations...${NC}"
        docker-compose -f "$COMPOSE_FILE" exec app alembic upgrade head
        echo -e "${GREEN}Migrations complete${NC}"
        ;;
        
    *)
        echo "Usage: $0 {deploy|stop|down|clean|logs|status|backup|migrate} [options]"
        echo ""
        echo "Commands:"
        echo "  deploy [--build]  Deploy staging environment"
        echo "  stop              Stop all services"
        echo "  down              Stop and remove containers"
        echo "  clean             Remove everything including volumes"
        echo "  logs [service]    View logs (all services or specific)"
        echo "  status            Show service status"
        echo "  backup            Create database backup"
        echo "  migrate           Run database migrations"
        exit 1
        ;;
esac