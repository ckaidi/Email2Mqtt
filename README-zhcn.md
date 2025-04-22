# Email2MQTT

Email2MQTT 是一个监控邮箱收件箱中新消息并将其转发到 MQTT 代理的服务。它被设计为在 Docker 容器中运行，并可以通过环境变量轻松配置。

## 功能特点

- 监控 IMAP 邮件服务器的新（未读）消息
- 解析邮件发件人信息和主题
- 将邮件详情转发到 MQTT 代理
- 支持 SSL/TLS 安全 MQTT 连接
- 可配置的检查间隔
- 作为轻量级 Docker 容器运行

## 系统要求

- Docker 和 Docker Compose
- 支持 IMAP 的电子邮件账户
- MQTT 代理（可选 SSL/TLS 支持）

## 安装方法

### 使用 Docker Compose（推荐）

1. 克隆此仓库：
   ```bash
   git clone https://github.com/yourusername/email2mqtt.git
   cd email2mqtt
   ```

2. 通过编辑 `docker-compose.yml` 文件或设置环境变量来配置服务。

3. 如果使用带 SSL 的 MQTT，请将您的 CA 证书文件放在项目目录中，命名为 `ca.crt`。

4. 启动服务：
   ```bash
   docker-compose up -d
   ```

### 手动安装

1. 克隆此仓库：
   ```bash
   git clone https://github.com/yourusername/email2mqtt.git
   cd email2mqtt
   ```

2. 创建虚拟环境并安装依赖：
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows 系统：.venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. 设置所需的环境变量（参见配置部分）。

4. 运行应用程序：
   ```bash
   python app/main.py
   ```

## 配置

Email2MQTT 使用环境变量进行配置。这些变量可以在 `docker-compose.yml` 文件中设置或直接在您的环境中设置。

### 邮箱设置

| 变量 | 描述 | 默认值 |
|----------|-------------|--------|
| `IMAP_SERVER` | IMAP 服务器地址（例如，imap.gmail.com） | *必填* |
| `EMAIL_USERNAME` | 邮箱账户用户名 | *必填* |
| `EMAIL_PASSWORD` | 邮箱账户密码或应用密码 | *必填* |
| `CHECK_INTERVAL` | 邮件检查间隔时间（秒） | `5` |

### MQTT 设置

| 变量 | 描述 | 默认值 |
|----------|-------------|--------|
| `MQTT_BROKER` | MQTT 代理地址 | *必填* |
| `MQTT_PORT` | MQTT 代理端口 | `8883` |
| `MQTT_TOPIC` | 用于发布邮件通知的 MQTT 主题 | `email` |
| `MQTT_USERNAME` | MQTT 代理用户名 | *必填* |
| `MQTT_PASSWORD` | MQTT 代理密码 | *必填* |

### MQTT SSL 设置

| 变量 | 描述 | 默认值 |
|----------|-------------|--------|
| `MQTT_SSL` | 为 MQTT 连接启用 SSL/TLS | `True` |
| `MQTT_SSL_CA_CERTS` | CA 证书文件路径 | `ca.crt` |

### URL 设置

| 变量 | 描述 | 默认值 |
|----------|-------------|--------|
| `HTML_PROCESS_URL` | HTML 处理 URL，用于处理邮件中的 HTML 内容 | `''` (空字符串) |

## 消息格式

当检测到新邮件时，Email2MQTT 会向配置的 MQTT 主题发布一条消息，格式如下：

```python
{
    'id': 'email_id',
    'from': 'sender@example.com',
    'from_name': 'Sender Name',
    'subject': 'Email Subject',
    'timestamp': 1234567890
}
```

## Docker Compose 示例

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
      # 邮箱配置
      - IMAP_SERVER=imap.qq.com
      - EMAIL_USERNAME=your_email@qq.com
      - EMAIL_PASSWORD=your_email_password
      # MQTT配置
      - MQTT_BROKER=your_mqtt_broker
      - MQTT_PORT=8883
      - MQTT_TOPIC=email
      # MQTT SSL配置
      - MQTT_SSL=True
      - MQTT_SSL_CA_CERTS=ca.crt
      # MQTT认证
      - MQTT_USERNAME=your_mqtt_username
      - MQTT_PASSWORD=your_mqtt_password
      # URL配置
      - HTML_PROCESS_URL=''
    volumes:
      - ./ca.crt:/app/ca.crt 
    restart: unless-stopped
```

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 LICENSE 文件。

## 贡献

欢迎贡献！请随时提交 Pull Request。