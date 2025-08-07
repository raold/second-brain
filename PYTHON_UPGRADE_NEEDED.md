# Python Version Issue - Action Required

## Current Situation
- **Required**: Python 3.11+ (ideally 3.13 for best performance)
- **Installed**: Python 3.10.12 (Ubuntu 22.04 default)
- **Impact**: Project may not work correctly with Python 3.10

## Why Python 3.11+?
The project uses features introduced in Python 3.11+:
- Better error messages with detailed tracebacks
- Performance improvements (10-60% faster)
- Enhanced type hints support
- Improved asyncio performance (critical for this project)
- Better exception groups handling

## Installation Options

### Option 1: Install Python 3.13 via deadsnakes PPA (Recommended)
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.13 python3.13-venv python3.13-dev
```

### Option 2: Install via pyenv
```bash
# Install pyenv
curl https://pyenv.run | bash

# Add to ~/.bashrc
echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc
source ~/.bashrc

# Install Python 3.13
pyenv install 3.13.1
pyenv local 3.13.1
```

### Option 3: Build from source
```bash
# Install dependencies
sudo apt update
sudo apt install -y build-essential zlib1g-dev libncurses5-dev \
    libgdbm-dev libnss3-dev libssl-dev libreadline-dev \
    libffi-dev libsqlite3-dev wget libbz2-dev

# Download and build Python 3.13
wget https://www.python.org/ftp/python/3.13.1/Python-3.13.1.tgz
tar -xf Python-3.13.1.tgz
cd Python-3.13.1
./configure --enable-optimizations
make -j $(nproc)
sudo make altinstall
```

## After Installing Python 3.13

1. **Create new virtual environment**:
```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

2. **Install requirements**:
```bash
pip install -r requirements.txt
```

3. **Run tests**:
```bash
pytest tests/
```

## Temporary Workaround (NOT RECOMMENDED)
The project *might* work with Python 3.10, but you may encounter:
- Performance issues
- Missing features
- Unexpected errors
- Incompatible type hints

Current .venv is using Python 3.10 - upgrade recommended!