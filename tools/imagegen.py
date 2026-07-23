import requests
import os
PROMPT="""
Conway's Game of Life cellular automata embedded in a scalar potential field,
discrete cells dissolving into continuous wave-like fields,
phase transition visualization, critical phenomena,
dark background with cyan and magenta highlights,
isometric 3D view, computational aesthetic,
poster quality, ultra detailed 1080p size
"""

# Lightning 快速生成（推荐）
resp = requests.post("http://192.168.31.54:8001/v1/images/generations", json={
    "model": "qwen-image",
    "prompt": PROMPT,
    "size": "1080x1920",
    "num_inference_steps": 50,  # Lightning 默认
    "response_format": "url",
})
data = resp.json()
image_url = data["data"][0]["url"]
print(f"图片地址: {image_url}")
print(f"生成耗时: {data['usage']['generation_time']}")

# 下载图片
img_data = requests.get(image_url).content
from urllib.parse import urlparse

# 假设 image_url 是 'http://192.168.31.54:8001/images/1a64ba1481244d1a9bbf2825a11f337c.png'

# 1. 解析 URL 并提取出纯净的文件名
parsed_url = urlparse(image_url)
filename = os.path.basename(parsed_url.path)
# 结果会是: '1a64ba1481244d1a9bbf2825a11f337c.png'

# 2. 统一写入可视化资产目录（注意不要再加 +".png" 了）
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
asset_dir = os.path.join(project_root, "visualizations", "assets")
os.makedirs(asset_dir, exist_ok=True)
with open(os.path.join(asset_dir, filename), "wb") as f:
    f.write(img_data)
