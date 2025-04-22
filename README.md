# Email2MQTT

[中文文档](README-zhcn.md)

Email2MQTT is a service that monitors an email inbox for new messages and forwards them to an MQTT broker. It's designed to be run as a Docker container and can be easily configured through environment variables.

## Features

- Monitors an IMAP email server for new (unread) messages
- Parses email sender information and subject
- Forwards email details to an MQTT broker
- Supports SSL/TLS for secure MQTT connections
- Configurable check interval
- Runs as a lightweight Docker container

## Requirements

- Docker and Docker Compose
- IMAP-enabled email account
- MQTT broker (with optional SSL/TLS support)

## Installation

### Using Docker Compose (Recommended)

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/email2mqtt.git
   cd email2mqtt
   ```

2. Configure the service by editing the `docker-compose.yml` file or setting up environment variables.

3. If using MQTT with SSL, place your CA certificate file in the project directory as `ca.crt`.

4. Start the service:
   ```bash
   docker-compose up -d
   ```

### Manual Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/email2mqtt.git
   cd email2mqtt
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set the required environment variables (see Configuration section).

4. Run the application:
   ```bash
   python app/main.py
   ```

## Configuration

Email2MQTT is configured using environment variables. These can be set in the `docker-compose.yml` file or directly in your environment.

### Email Settings

| Variable | Description | Default |
|----------|-------------|--------|
| `IMAP_SERVER` | IMAP server address (e.g., imap.gmail.com) | *Required* |
| `EMAIL_USERNAME` | Email account username | *Required* |
| `EMAIL_PASSWORD` | Email account password or app password | *Required* |
| `CHECK_INTERVAL` | Time between email checks (in seconds) | `5` |

### MQTT Settings

| Variable | Description | Default |
|----------|-------------|--------|
| `MQTT_BROKER` | MQTT broker address | *Required* |
| `MQTT_PORT` | MQTT broker port | `8883` |
| `MQTT_TOPIC` | MQTT topic for publishing email notifications | `email` |
| `MQTT_USERNAME` | MQTT broker username | *Required* |
| `MQTT_PASSWORD` | MQTT broker password | *Required* |

### MQTT SSL Settings

| Variable | Description | Default |
|----------|-------------|--------|
| `MQTT_SSL` | Enable SSL/TLS for MQTT connection | `True` |
| `MQTT_SSL_CA_CERTS` | Path to CA certificate file | `ca.crt` |

### URL Settings

| Variable | Description | Default |
|----------|-------------|--------|
| `HTML_PROCESS_URL` | HTML processing URL for handling HTML content in emails | `''` (empty string) |

## Message Format

When a new email is detected, Email2MQTT publishes a message to the configured MQTT topic with the following format:

```python
{
    'id': 'email_id',
    'from': 'sender@example.com',
    'from_name': 'Sender Name',
    'subject': 'Email Subject',
    'timestamp': 1234567890
}
```

## Docker Compose Example

```yaml
version: '3.8'

services:
  email2mqtt:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: email2mqtt
    environment:
      - TZ=Asia/Shanghai
      - CHECK_INTERVAL=5
      # Email configuration
      - IMAP_SERVER=imap.qq.com
      - EMAIL_USERNAME=your_email@qq.com
      - EMAIL_PASSWORD=your_email_password
      # MQTT configuration
      - MQTT_BROKER=your_mqtt_broker
      - MQTT_PORT=8883
      - MQTT_TOPIC=email
      # MQTT SSL configuration
      - MQTT_SSL=True
      - MQTT_SSL_CA_CERTS=ca.crt
      # MQTT authentication
      - MQTT_USERNAME=your_mqtt_username
      - MQTT_PASSWORD=your_mqtt_password
      # URL configuration
      - HTML_PROCESS_URL=''
    volumes:
      - ./ca.crt:/app/ca.crt 
    restart: unless-stopped
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.