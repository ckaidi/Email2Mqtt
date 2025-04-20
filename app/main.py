import imaplib
import email
from re import M
import time
from email.header import decode_header
import paho.mqtt.client as mqtt
import requests  # 添加导入
from config import (  # 从配置文件导入配置
    IMAP_SERVER, USERNAME, PASSWORD, CHECK_INTERVAL,
    MQTT_BROKER, MQTT_PORT, MQTT_TOPIC,
    MQTT_SSL, MQTT_SSL_CA_CERTS,
    HEALTHY_URL,HTML_PROCESS_URL,
    MQTT_USERNAME, MQTT_PASSWORD  # 新增导入
)

read=[]
def connect_to_imap():
    """连接到IMAP服务器"""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(USERNAME, PASSWORD)
        mail.select('inbox')  # 选择收件箱
        return mail
    except Exception as e:
        print(f"连接失败: {e}")
        return None

def process_text_content(payload, charset):
    """处理纯文本内容"""
    try:
        return payload.decode(charset, 'replace')
    except Exception as e:
        print(f"解码纯文本内容出错: {e}")
        return payload.decode('utf-8', 'replace')

def process_html_content(payload, charset):
    """处理HTML内容"""
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
    """处理邮件的单个部分"""
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
    """提取邮件内容（纯文本和HTML）"""
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
    """检查新邮件"""
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
    """解析发件人信息"""
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
    """MQTT连接回调函数"""
    if rc == 0:
        print("MQTT连接成功")
    else:
        print(f"MQTT连接失败，错误码: {rc}")

def on_disconnect(client, userdata, rc):
    """MQTT断开连接回调函数"""
    print(f"MQTT连接断开，错误码: {rc}")
    # 自动重连逻辑
    if rc != 0:
        print("尝试重新连接...")
        client.reconnect()

def main():
    print("开始监听邮箱...")
    last_uid = None
    
    # 初始化MQTT客户端 - 修改客户端ID
    # 修改MQTT客户端初始化部分
    mqtt_client = mqtt.Client(client_id='email2mqtt')  # 使用空字符串让broker自动分配ID
    
    # 设置回调函数
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    
    # 设置MQTT用户名和密码
    mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    
    # 配置SSL连接
    if MQTT_SSL:
        mqtt_client.tls_set(
            ca_certs=MQTT_SSL_CA_CERTS,
            #certfile=MQTT_SSL_CERTFILE,
            #keyfile=MQTT_SSL_KEYFILE
        )
    
    while True:
        try:
            if HEALTHY_URL != '':
                try:
                    # 发送心跳ping
                    requests.get(HEALTHY_URL, timeout=5)
                except Exception as e:
                    print(f"心跳ping失败: {e}")

            mail = connect_to_imap()
            if mail:
                new_emails = check_new_emails(mail, last_uid)
                if new_emails:
                    # 开始连接
                    mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
                    # mqtt_client.loop_start()  # 启动网络循环
                    print(f"发现 {len(new_emails)} 封新邮件:")
                    for email_info in new_emails:
                        email_id = email_info['id'].decode('utf-8') if isinstance(email_info['id'], bytes) else email_info['id']
                        
                        if email_id not in read:
                            sender_info = parse_sender(email_info['from'])
                            print(f"邮件ID: {email_id}")
                            print(f"发件人名称: {sender_info['name']}")
                            print(f"发件人邮箱: {sender_info['email']}")
                            print(f"主题: {email_info['subject']}")
                            print("-" * 50)
                            
                            # 发送MQTT消息
                            # 构建包含邮件内容的消息
                            message = f"{sender_info['name']}\n{email_info['subject']}\n"
                            
                            # 添加纯文本内容（如果有）
                            if email_info['content']['text']:
                                message += email_info['content']['text']
                            # 如果没有纯文本但有HTML内容，也添加提示
                            elif email_info['content']['html']:
                                # message += "[邮件包含HTML内容]"
                                message += email_info['content']['html']
                                
                            mqtt_client.publish(MQTT_TOPIC, message)
                            
                            # 将邮件ID写入Redis
                            read.append(email_id)
                        else:
                            print(f"邮件ID {email_id} 已存在，跳过处理")
                    mqtt_client.disconnect()
                    # mqtt_client.loop_stop()  # 停止网络循环    
                    last_uid = new_emails[-1]['id']
                
                mail.logout()
            
            time.sleep(CHECK_INTERVAL)
            # 打印当前时间
            current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            print(f"当前时间: {current_time}")
        except Exception as e:
            print(f"程序异常: {e}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("程序退出")
    except Exception as e:
        print(f"程序异常退出: {e}")
    print("程序退出")