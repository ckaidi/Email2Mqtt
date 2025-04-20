# 自动递增版本的脚本
# bump_version.py
# scripts/bump_version.py
import re
from pathlib import Path
import subprocess

# 定义版本文件路径
VERSION_FILE = Path("__init__.py")

def bump_version():
    if not VERSION_FILE.exists():
        print(f"Error: {VERSION_FILE} does not exist.")
        return

    # 读取文件内容
    with open(VERSION_FILE, "r") as f:
        content = f.read()

    # 使用正则表达式匹配版本号（假设版本号格式为 x.y.z）
    version_pattern = r'(\d+)\.(\d+)\.(\d+)'
    match = re.search(version_pattern, content)
    if not match:
        print(f"Error: No version found in {VERSION_FILE}.")
        return

    # 解析版本号
    major, minor, patch = map(int, match.groups())

    # 增加 patch 版本号
    patch += 1

    # 替换为新版本号
    new_version = f"{major}.{minor}.{patch}"
    new_content = re.sub(version_pattern, new_version, content)

    # 写回文件
    with open(VERSION_FILE, "w") as f:
        f.write(new_content)

    print(f"Bumped version to {new_version} in {VERSION_FILE}.")

    # 将更新后的版本文件加入 Git 暂存区
    try:
        subprocess.run(["git", "add", str(VERSION_FILE)], check=True)
        print(f"Added {VERSION_FILE} to Git staging area.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to add {VERSION_FILE} to Git staging area: {e}")

if __name__ == "__main__":
    bump_version()
