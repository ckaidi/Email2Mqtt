import imaplib  # 用于IMAP邮件操作 / For IMAP mail operations
import email  # 用于解析邮件 / For parsing emails
from re import M  # 正则表达式模块 / Regular expression module
import sys
import time  # 时间相关操作 / Time-related operations
import socket  # 网络套接字操作 / Network socket operations
from email.header import decode_header  # 解码邮件头 / Decode email headers
import paho.mqtt.client as mqtt  # MQTT客户端 / MQTT client
import requests  # 用于HTTP请求 / For HTTP requests
import uvicorn
import logging
from fastapi import FastAPI
from config import (  # 从配置文件导入配置 / Import configuration from config file
    IMAP_SERVER, USERNAME, PASSWORD, CHECK_INTERVAL,
    MQTT_BROKER, MQTT_PORT, MQTT_TOPIC,
    MQTT_SSL, MQTT_SSL_CA_CERTS, HTML_PROCESS_URL,
    MQTT_USERNAME, MQTT_PASSWORD  # MQTT认证信息 / MQTT authentication info
)

app = FastAPI()

class DuplicateMessageFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        self.last_message = None
        self.count = 0

    def filter(self, record):
        current_message = record.getMessage()
        if current_message == self.last_message:
            self.count += 1
            if self.count>=60:
                self.count = 0
                return True
            return False
        else:
            self.last_message = current_message
            self.count = 0
            return True

logger = logging.getLogger('uvicorn')
logger.setLevel(logging.DEBUG)
duplicate_filter = DuplicateMessageFilter()
logger.addFilter(duplicate_filter)

# 已读邮件ID列表 / List of read email IDs
read = []
def connect_to_imap(timeout=30):
    """连接到IMAP服务器
    Connect to the IMAP server
    
    Args:
        timeout (int, optional): 连接超时时间（秒）。默认为30秒。
                                Connection timeout in seconds. Default is 30 seconds.
    
    Returns:
        imaplib.IMAP4_SSL: 连接成功返回邮箱对象，失败返回None
        Returns mailbox object if connection is successful, None if failed
    """
    try:
        # 创建IMAP连接并设置超时
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, timeout=timeout)
        
        # 设置登录和命令操作的超时
        mail.socket().settimeout(timeout)
        
        # 登录邮箱
        mail.login(USERNAME, PASSWORD)
        
        # 选择收件箱
        mail.select('inbox')
        
        return mail
    except (imaplib.IMAP4.error, socket.timeout, ConnectionRefusedError, OSError) as e:
        print(f"连接失败: {e}")
        return None
    except Exception as e:
        print(f"未知错误: {e}")
        return None

def process_text_content(payload, charset):
    """处理纯文本内容
    Process plain text content
    
    Args:
        payload (bytes): 邮件内容的二进制数据 / Binary data of email content
        charset (str): 字符编码 / Character encoding
        
    Returns:
        str: 解码后的文本内容 / Decoded text content
    """
    try:
        return payload.decode(charset, 'replace')
    except Exception as e:
        print(f"解码纯文本内容出错: {e}")
        return payload.decode('utf-8', 'replace')

def process_html_content(payload, charset):
    """处理HTML内容
    Process HTML content
    
    Args:
        payload (bytes): 邮件内容的二进制数据 / Binary data of email content
        charset (str): 字符编码 / Character encoding
        
    Returns:
        str: 解码后的HTML内容，如果配置了HTML处理URL，则返回处理后的内容
        Decoded HTML content, if HTML_PROCESS_URL is configured, returns processed content
    """
    try:
        html = payload.decode(charset, 'replace')
        if HTML_PROCESS_URL != '':           
            try:
                response = requests.post(HTML_PROCESS_URL, data={'html': html})
                return response.text
            except Exception as e:
                print(e)
        # with open('temp.html', 'wb') as file:
        #     file.write(payload)
        return html
    except Exception as e:
        print(f"解码HTML内容出错: {e}")
        return payload.decode('utf-8', 'replace')

def process_email_part(part, content_disposition):
    """处理邮件的单个部分
    Process a single part of an email
    
    Args:
        part (email.message.Message): 邮件部分对象 / Email part object
        content_disposition (str): 内容处置类型 / Content disposition type
        
    Returns:
        dict: 包含文本和HTML内容的字典 / Dictionary containing text and HTML content
    """
    content = {'text': '', 'html': ''}
    
    # 跳过附件
    if 'attachment' in content_disposition:
        return content
        
    content_type = part.get_content_type()
    payload = part.get_payload(decode=True)
    
    if not payload:
        return content
        
    charset = part.get_content_charset() or 'utf-8'
    
    if content_type == 'text/plain' and 'attachment' not in content_disposition:
        content['text'] = process_text_content(payload, charset)
    elif content_type == 'text/html' and 'attachment' not in content_disposition:
        content['html'] = process_html_content(payload, charset)
        
    return content

def extract_email_content(email_message):
    """提取邮件内容（纯文本和HTML）
    Extract email content (plain text and HTML)
    
    Args:
        email_message (email.message.Message): 邮件消息对象 / Email message object
        
    Returns:
        dict: 包含文本和HTML内容的字典 / Dictionary containing text and HTML content
    """
    content = {
        'text': '',
        'html': ''
    }
    
    if email_message.is_multipart():
        for part in email_message.walk():
            content_disposition = str(part.get('Content-Disposition'))
            part_content = process_email_part(part, content_disposition)
            
            if part_content['text']:
                content['text'] += part_content['text']
            if part_content['html']:
                content['html'] += part_content['html']
    else:
        # 非多部分邮件
        content_type = email_message.get_content_type()
        payload = email_message.get_payload(decode=True)
        
        if payload:
            charset = email_message.get_content_charset() or 'utf-8'
            
            if content_type == 'text/plain':
                content['text'] = process_text_content(payload, charset)
            elif content_type == 'text/html':
                content['html'] = process_html_content(payload, charset)
    
    return content

def check_new_emails(mail, last_uid=None):
    """检查新邮件
    Check for new emails
    
    Args:
        mail (imaplib.IMAP4_SSL): 邮箱连接对象 / Mailbox connection object
        last_uid (str, optional): 上次检查的最后一封邮件的UID / UID of the last email checked
        
    Returns:
        list: 新邮件列表，每个邮件包含ID、主题、发件人和内容 / List of new emails, each containing ID, subject, sender and content
        如果出错则返回None / Returns None if an error occurs
    """
    try:
        # 搜索所有未读邮件
        status, messages = mail.search(None, 'UNSEEN')
        if status != 'OK':
            return None

        email_ids = messages[0].split()
        new_emails = []
        
        for e_id in email_ids:
            # 获取邮件内容
            status, msg_data = mail.fetch(e_id, '(RFC822)')
            if status != 'OK':
                continue
                
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # 解码邮件主题
            subject, encoding = decode_header(email_message['Subject'])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or 'utf-8')
            
            # 提取邮件正文
            content = extract_email_content(email_message)
                
            new_emails.append({
                'id': e_id,
                'subject': subject,
                'from': email_message['From'],
                'content': content
            })
            
        return new_emails
    except Exception as e:
        print(f"检查邮件出错: {e}")
        return None

def parse_sender(sender):
    """解析发件人信息
    Parse sender information
    
    Args:
        sender (str): 发件人字符串，格式可能是"Name <email@example.com>"或纯邮箱地址
        Sender string, format could be "Name <email@example.com>" or just email address
        
    Returns:
        dict: 包含发件人名称和邮箱的字典 / Dictionary containing sender's name and email
    """
    try:
        # 处理没有尖括号的情况
        if '<' not in sender and '>' not in sender:
            return {
                'name': '',
                'email': sender.strip()
            }
        
        # 提取邮箱部分
        email_start = sender.rfind('<')
        email_end = sender.rfind('>')
        email_part = sender[email_start+1:email_end].strip()
        
        # 提取名称部分
        name_part = sender[:email_start].strip()
        
        # 处理名称部分的引号和MIME编码
        if name_part.startswith('"') and name_part.endswith('"'):
            name_part = name_part[1:-1]
            
        # 解码MIME编码的名称
        decoded_name = []
        for part in name_part.split():
            if part.startswith('=?') and part.endswith('?='):
                decoded_part = decode_header(part)[0][0]
                if isinstance(decoded_part, bytes):
                    decoded_part = decoded_part.decode('utf-8')
                decoded_name.append(decoded_part)
            else:
                decoded_name.append(part)
                
        return {
            'name': ' '.join(decoded_name).strip(),
            'email': email_part
        }
    except Exception as e:
        print(f"解析发件人信息出错: {e}")
        return {
            'name': sender,
            'email': sender
        }

def on_connect(client, userdata, flags, rc):
    """MQTT连接回调函数
    MQTT connection callback function
    
    Args:
        client (mqtt.Client): MQTT客户端对象 / MQTT client object
        userdata: 用户数据 / User data
        flags: 连接标志 / Connection flags
        rc (int): 结果代码，0表示连接成功 / Result code, 0 means successful connection
    """
    if rc == 0:
        print("MQTT连接成功")
    else:
        print(f"MQTT连接失败，错误码: {rc}")

def on_disconnect(client, userdata, rc):
    """MQTT断开连接回调函数
    MQTT disconnection callback function
    
    Args:
        client (mqtt.Client): MQTT客户端对象 / MQTT client object
        userdata: 用户数据 / User data
        rc (int): 结果代码，0表示正常断开，非0表示意外断开 / Result code, 0 means normal disconnection, non-zero means unexpected disconnection
    """
    print(f"MQTT连接断开，错误码: {rc}")
    # 自动重连逻辑
    if rc != 0:
        print("尝试重新连接...")
        client.reconnect()

def main():
    """主函数，程序入口点
    Main function, program entry point
    
    持续监听邮箱，检查新邮件并通过MQTT发送邮件内容
    Continuously monitors mailbox, checks for new emails and sends email content via MQTT
    """
    print("开始监听邮箱...")  # 开始监听提示 / Start monitoring prompt
    last_uid = None
    
    # 初始化MQTT客户端 / Initialize MQTT client
    mqtt_client = mqtt.Client(client_id='email2mqtt')  # 使用指定的客户端ID / Use specified client ID
    
    # 设置回调函数 / Set callback functions
    mqtt_client.on_connect = on_connect  # 连接回调 / Connection callback
    mqtt_client.on_disconnect = on_disconnect  # 断开连接回调 / Disconnection callback
    
    # 设置MQTT用户名和密码 / Set MQTT username and password
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    # 配置SSL连接 / Configure SSL connection
    if MQTT_SSL:
        mqtt_client.tls_set(
            ca_certs=MQTT_SSL_CA_CERTS,  # CA证书路径 / Path to CA certificate
            #certfile=MQTT_SSL_CERTFILE,  # 客户端证书 / Client certificate
            #keyfile=MQTT_SSL_KEYFILE  # 客户端密钥 / Client key
        )
    
    # 连接到MQTT代理 / Connect to MQTT broker
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
    mqtt_client.loop_start()  # 启动网络循环 / Start network loop
    
    # 连接到邮箱服务器 / Connect to mail server
    mail = connect_to_imap()
    if not mail:
        print("初始邮箱连接失败，程序退出")  # 初始连接失败提示 / Initial connection failure prompt
        return
        
    print("邮箱连接成功，开始监听新邮件")  # 连接成功提示 / Connection success prompt
    
    while True:
        try:
            # 检查邮箱连接是否有效 / Check if mailbox connection is valid
            try:
                # 尝试执行一个简单的IMAP命令来检查连接 / Try to execute a simple IMAP command to check connection
                mail.noop()
            except Exception as e:
                print(f"邮箱连接已断开，尝试重新连接: {e}")  # 连接断开提示 / Connection lost prompt
                mail = connect_to_imap()
                if not mail:
                    print("重新连接失败，等待下一次尝试")  # 重连失败提示 / Reconnection failure prompt
                    time.sleep(CHECK_INTERVAL)
                    continue
                print("邮箱重新连接成功")  # 重连成功提示 / Reconnection success prompt
            
            # 检查新邮件 / Check for new emails
            new_emails = check_new_emails(mail, last_uid)
            # 如果有新邮件，处理并发送到MQTT / If there are new emails, process and send to MQTT
            if new_emails:
                # 打印发现的新邮件数量 / Print number of new emails found
                print(f"发现 {len(new_emails)} 封新邮件:")
                
                # 处理每封新邮件 / Process each new email
                for email_info in new_emails:
                    # 获取邮件ID，确保是字符串格式 / Get email ID, ensure it's in string format
                    email_id = email_info['id'].decode('utf-8') if isinstance(email_info['id'], bytes) else email_info['id']
                    
                    # 检查邮件是否已处理过 / Check if email has been processed before
                    if email_id not in read:
                        # 解析发件人信息 / Parse sender information
                        sender_info = parse_sender(email_info['from'])
                        
                        # 打印邮件信息 / Print email information
                        print(f"邮件ID: {email_id}")
                        print(f"发件人名称: {sender_info['name']}")
                        print(f"发件人邮箱: {sender_info['email']}")
                        print(f"主题: {email_info['subject']}")
                        print("-" * 50)
                        
                        # 构建MQTT消息 / Build MQTT message
                        # 包含发件人名称和邮件主题 / Include sender name and email subject
                        message = f"{sender_info['name']}\n{email_info['subject']}\n"
                        
                        # 添加邮件内容 / Add email content
                        # 优先使用纯文本内容 / Prefer plain text content
                        if email_info['content']['text']:
                            message += email_info['content']['text']
                        # 如果没有纯文本但有HTML内容，使用HTML内容 / If no plain text but has HTML content, use HTML
                        elif email_info['content']['html']:
                            # message += "[邮件包含HTML内容]" / [Email contains HTML content]
                            message += email_info['content']['html']
                            
                        # 发布消息到MQTT主题 / Publish message to MQTT topic
                        mqtt_client.publish(MQTT_TOPIC, message)
                        
                        # 将邮件ID添加到已读列表 / Add email ID to read list
                        read.append(email_id)
                    # 邮件已处理过，跳过 / Email already processed, skip
                    else:
                        print(f"邮件ID {email_id} 已存在，跳过处理")
                
                # 更新最后处理的邮件ID / Update last processed email ID
                last_uid = new_emails[-1]['id']
            
            # 等待指定的检查间隔时间 / Wait for the specified check interval
            time.sleep(CHECK_INTERVAL)
            
            # 打印当前时间 / Print current time
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print(f"当前时间: {current_time}")
            sys.stdout.flush()
        # 捕获并记录异常 / Catch and log exceptions
        except Exception as e:
            print(f"程序异常: {e}")  # 异常日志 / Exception log
    # mqtt_client.disconnect()


@app.get('/')
async def index():
    from . import __version__
    return 'version:' +__version__

@app.get('/health')
async def health_check():
    # 检查子线程是否存活
    if 't' in globals() and t.is_alive():
        return {"status": "healthy", "thread_status": "alive"}
    else:
        return {"status": "unhealthy", "thread_status": "dead"}, 400

if __name__ == '__main__':
    try:
        import threading
        # 创建并启动子线程运行main函数
        t = threading.Thread(target=main, daemon=True)
        t.start()
        
        # 启动FastAPI服务
        uvicorn.run(
            app, 
            host="localhost", 
            port=8000,
            # ssl_keyfile="./ssl/cert.key",  # 替换为你的私钥路径
            # ssl_certfile="./ssl/cert.pem",  # 替换为你的证书路径
        )
    except KeyboardInterrupt:
        # 处理键盘中断（Ctrl+C） / Handle keyboard interrupt (Ctrl+C)
        print("程序退出")  # 程序退出提示 / Program exit prompt
    except Exception as e:
        # 处理其他异常 / Handle other exceptions
        print(f"程序异常退出: {e}")  # 异常退出日志 / Exception exit log
    
    # 最终退出提示 / Final exit prompt
    print("程序退出")