#!/usr/bin/env python3
"""
Complete setup script for Second Brain application.
Handles environment setup, dependency installation, and database initialization.
"""

import os
import subprocess
import sys
from pathlib import Path


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*50}")
    print(f"🚀 {title}")
    print(f"{'='*50}")


def print_step(step: str):
    """Print a formatted step."""
    print(f"\n📋 {step}")


def run_command(cmd: list, description: str = "", check: bool = True):
    """Run a command and handle errors."""
    if description:
        print(f"   Running: {description}")

    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        if result.stdout:
            print(f"   ✅ {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Command failed: {' '.join(cmd)}")
        print(f"   Error: {e.stderr.strip()}")
        if check:
            sys.exit(1)
        return e


def check_python_version():
    """Check if Python version is compatible."""
    print_step("Checking Python version...")


    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")


def check_docker():
    """Check if Docker is installed and running."""
    print_step("Checking Docker...")

    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Docker is not installed")
            print("Please install Docker from https://www.docker.com/get-started")
            sys.exit(1)

        print(f"✅ {result.stdout.strip()}")

        # Check if Docker is running
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Docker is not running")
            print("Please start Docker Desktop or Docker service")
            sys.exit(1)

        print("✅ Docker is running")

    except FileNotFoundError:
        print("❌ Docker is not installed")
        print("Please install Docker from https://www.docker.com/get-started")
        sys.exit(1)


def setup_virtual_environment():
    """Set up Python virtual environment."""
    print_step("Setting up virtual environment...")

    venv_path = Path("venv")

    if not venv_path.exists():
        print("Creating virtual environment...")
        run_command([sys.executable, "-m", "venv", "venv"], "Creating virtual environment")
    else:
        print("✅ Virtual environment already exists")

    # Activate virtual environment
    if os.name == 'nt':  # Windows
        python_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:  # Unix-like
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"

    return python_exe, pip_exe


def install_dependencies(pip_exe):
    """Install Python dependencies."""
    print_step("Installing Python dependencies...")

    # Upgrade pip
    run_command([str(pip_exe), "install", "--upgrade", "pip"], "Upgrading pip")

    # Install requirements
    if Path("requirements.txt").exists():
        run_command([str(pip_exe), "install", "-r", "requirements.txt"], "Installing requirements")
    else:
        print("⚠️  requirements.txt not found, installing essential packages...")
        essential_packages = [
            "fastapi", "uvicorn", "qdrant-client", "openai", "sqlalchemy",
            "asyncpg", "pydantic", "python-dotenv", "click", "requests"
        ]
        run_command([str(pip_exe), "install"] + essential_packages, "Installing essential packages")


def create_environment_file():
    """Create environment file."""
    print_step("Creating environment file...")

    env_file = Path('.env')
    if env_file.exists():
        print("✅ Environment file already exists")
        return

    env_content = """# Second Brain Environment Configuration
# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=second_brain
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=memories

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

    with open(env_file, 'w') as f:
        f.write(env_content)

    print("✅ Created .env file")
    print("⚠️  Please update .env file with your actual OpenAI API key!")


def setup_directories():
    """Create necessary directories."""
    print_step("Creating directories...")

    directories = [
        Path('app/data'),
        Path('app/data/memories'),
        Path('logs'),
        Path('qdrant_data'),
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created {directory}")


def start_database_services():
    """Start database services with Docker Compose."""
    print_step("Starting database services...")

    # Check if docker-compose.yml exists
    if not Path('docker-compose.yml').exists():
        print("⚠️  docker-compose.yml not found, skipping service startup")
        return

    # Check for docker compose command
    compose_cmd = ['docker', 'compose']
    try:
        result = subprocess.run(compose_cmd + ['--version'], capture_output=True, text=True)
        if result.returncode != 0:
            compose_cmd = ['docker-compose']
    except Exception:
        compose_cmd = ['docker-compose']

    # Start services
    run_command(compose_cmd + ['up', '-d', 'qdrant', 'postgres'], "Starting database services")

    # Wait for services to be ready
    print("⏳ Waiting for services to be ready...")
    import time
    time.sleep(10)  # Give services time to start

    print("✅ Database services started")


def initialize_databases(python_exe):
    """Initialize databases."""
    print_step("Initializing databases...")

    if Path('init_database.py').exists():
        result = run_command([str(python_exe), 'init_database.py'], "Initializing databases", check=False)
        if result.returncode == 0:
            print("✅ Database initialization completed")
        else:
            print("⚠️  Database initialization had issues, check logs")
    else:
        print("⚠️  init_database.py not found, skipping database initialization")


def print_next_steps():
    """Print next steps for the user."""
    print_section("Setup Complete!")

    print("""
🎉 Second Brain application setup is complete!

Next steps:
1. Update your .env file with your OpenAI API key
2. Start the application:
   - Windows: venv\\Scripts\\activate.bat && python -m uvicorn app.main:app --reload
   - Unix/Mac: source venv/bin/activate && python -m uvicorn app.main:app --reload

3. Test the application:
   - Health check: http://localhost:8000/health
   - API docs: http://localhost:8000/docs

4. Database management:
   - python manage_services.py start    # Start database services
   - python manage_services.py stop     # Stop database services
   - python manage_services.py status   # Check service status
   - python manage_services.py reset    # Reset databases (removes all data)

5. Database initialization:
   - python init_database.py           # Initialize/check databases

Troubleshooting:
- If services fail to start, check Docker Desktop is running
- If database connection fails, ensure services are running: docker-compose up -d
- For detailed logs: docker-compose logs -f

Happy building! 🚀
""")


def main():
    """Main setup function."""
    print_section("Second Brain Application Setup")

    try:
        check_python_version()
        check_docker()

        python_exe, pip_exe = setup_virtual_environment()
        install_dependencies(pip_exe)
        create_environment_file()
        setup_directories()
        start_database_services()
        initialize_databases(python_exe)

        print_next_steps()

    except KeyboardInterrupt:
        print("\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
