# MakerSpace Leiden Aggregator

Welcome to the MakerSpace Leiden Aggregator. This software aggregates and distributes real-time information about the makerspace.
- [Features](#features)
- [System Design](#system-design)
  - [Architecture](#architecture)
- [Quick Start Guide](#quick-start-guide)
  - [System Requirements](#system-requirements)
  - [Installation](#installation)
  - [Running Locally](#running-locally)
  - [Testing](#testing)
  - [Production Environment](#production-environment)

## Features

- Listens to MQTT messages
- Aggregates useful information (like who is at the space now, what machines are on, etc.)
- Publishes the information live via HTTP and WebSockets

## System Design

### Architecture

![Aggregator Architecture Diagram](Aggregator%20Architecture.png)

Architecture diagram also available at: https://balsamiq.cloud/s84bb/pl6cb2r


## Quick Start Guide

### System Requirements
- Python 3.7
- Python 3 venv
- Redis
- git

### Installation

**Standard Setup**

1. Clone the repository:
   ```
   git clone https://github.com/MakerSpaceLeiden/aggregator.git
   ```
2. Set up virtual environment:
   ```
   python3.7 -m venv venv
   . venv/bin/activate
   ```
3. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

**Note for OSX 10.14 users**: If you have a locked down ~/Library, use:
```
pip install --no-cache-dir -r requirements.txt
```
to avoid having to write in `~/Library/Caches/pip/wheel`.

### Running Locally
After installation, start the development server:
```
python server-dev.py
```

### Testing
Run the test suite with:
```
python run-tests.py
```

### Production Environment
The server runs in production using systemd.

**Location**: /usr/local/aggregator

**Managing the Service**:
- View environment:
  ```
  sudo systemctl show-environment
  ```
- Set environment variables:
  ```
  sudo systemctl set-environment var=value
  ```
- Restart service:
  ```
  sudo systemctl restart msl_aggregator
  ```
- View logs:
  ```
  sudo journalctl _PID=<pid>
  sudo journalctl --since="10 minutes ago"
  ```
