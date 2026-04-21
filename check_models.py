import google.generativeai as genai
import os

# 配置你的代理和 KEY
proxy_port = "7897"
os.environ['http_proxy'] = f"http://127.0.0.1:{proxy_port}"
os.environ['https_proxy'] = f"http://127.0.0.1:{proxy_port}"

genai.configure(api_key="AIzaSyAU_YgO1buynuYOQPl1Qi-ER8rN1Dk4ucE", transport="rest")

print("正在拉取你可用的模型列表...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"可用型号: {m.name}")
except Exception as e:
    print(f"连不上服务器: {e}")