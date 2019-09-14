# MakerSpace Leiden Aggregator

- Listens to MQTT messages
- Aggregates useful information (like who is at the space now, what machines are on, etc.)
- Publishes the information live via HTTP and WebSockets

## Architecture

https://balsamiq.cloud/s84bb/pl6cb2r

![Aggregator Architecture](Aggregator%20Architecture.png)


## Features

- [Chores](./src/aggregator/chores/README.md)

## Installation and maintenance

### Requirements
- Redis
- git
- Python 3.7
- Python 3 venv
 
  E.g:
 
      apt install python3 python3-venv git

- Recent copy of the code:

      git clone https://github.com/MakerSpaceLeiden/aggregator.git

### Setup virtual environment

    python3.7 -m venv venv
    . venv/bin/activate

### Install dependencies

    pip install -r requirements.txt 

_NOTE_: OSX 10.14 users with a locked down ~/Library: use
`pip install --no-cache-dir -r requirements.txt`
to avoid having to write in `~/Library/Caches/pip/wheel`.

### Run server locally

    python server-dev.py
    
Run the tests:

    python run-tests.py


### Production

Server server runs in production using systemd.

Location: /usr/local/aggregator

Environment variables:

    sudo systemctl show-environment
    sudo systemctl set-environment var=value

Restart with:

    sudo systemctl restart msl_aggregator

Show logs with:

    sudo journalctl _PID=<pid>
    sudo journalctl --since="10 minutes ago"
