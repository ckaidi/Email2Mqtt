# 使用官方Python基础镜像
FROM docker.1ms.run/python:3.10-slim

# 设置工作目录
WORKDIR /app
# 设置工作目录
COPY requirements.txt .
# 复制项目文件
COPY . .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

# 运行应用
# 使用tail -f /dev/null保持容器运行
# CMD ["sh", "-c", "tail -f /dev/null"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]