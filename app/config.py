import os
from typing import Optional

def get_env_var(name: str, default: Optional[str] = None) -> str:
    """
    从环境变量获取配置 / Get configuration from environment variables
    :param name: 环境变量名称 / Environment variable name
    :param default: 默认值 / Default value
    :return: 环境变量值 / Environment variable value
    :raises ValueError: 如果环境变量未设置 / If environment variable is not set
    """
    value = os.getenv(name, default)
    if value is None:
        raise ValueError(f"环境变量 {name} 未设置 / Environment variable {name} not set")
    return value

# 邮箱配置 / Email settings
IMAP_SERVER = get_env_var('IMAP_SERVER')  # IMAP服务器地址 / IMAP server address (e.g. imap.gmail.com)
USERNAME = get_env_var('EMAIL_USERNAME')  # 邮箱用户名 / Email account username
PASSWORD = get_env_var('EMAIL_PASSWORD')  # 邮箱密码或应用密码 / Email password or app password
CHECK_INTERVAL = int(get_env_var('CHECK_INTERVAL', '5'))  # 邮件检查间隔时间(秒) / Email check interval (seconds)

# MQTT配置 / MQTT settings
MQTT_BROKER = get_env_var('MQTT_BROKER')  # MQTT代理地址 / MQTT broker address
MQTT_PORT = int(get_env_var('MQTT_PORT', '8883'))  # MQTT端口 / MQTT port
MQTT_TOPIC = get_env_var('MQTT_TOPIC', 'email')  # MQTT主题 / MQTT topic

# MQTT SSL配置 / MQTT SSL settings
MQTT_SSL = get_env_var('MQTT_SSL', 'True').lower() == 'true'  # 是否启用SSL / Enable SSL
MQTT_SSL_CA_CERTS = get_env_var('MQTT_SSL_CA_CERTS', 'ca.crt')  # CA证书路径 / Path to CA certificate

# MQTT认证配置 / MQTT authentication
MQTT_USERNAME = get_env_var('MQTT_USERNAME')  # MQTT用户名 / MQTT username
MQTT_PASSWORD = get_env_var('MQTT_PASSWORD')  # MQTT密码 / MQTT password

HEALTHY_URL=get_env_var('HEALTHY_URL','')  # 健康检查URL / Health check URL

HTML_PROCESS_URL=get_env_var('HTML_PROCESS_URL','')  # HTML处理URL / HTML processing URL