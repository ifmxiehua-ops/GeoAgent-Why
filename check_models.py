import google.generativeai as genai
import os

# 配置你的代理
proxy_port = "7897"
os.environ['http_proxy'] = f"http://127.0.0.1:{proxy_port}"
os.environ['https_proxy'] = f"http://127.0.0.1:{proxy_port}"

# 从环境变量读取 Key，避免硬编码
api_key = os.environ.get("GEMINI_API_KEY", "").strip()
if not api_key:
    api_key = input("请输入你的 Gemini API Key：").strip()

genai.configure(api_key=api_key, transport="rest")

print("正在拉取你可用的模型列表...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"可用型号: {m.name}")
except Exception as e:
    print(f"连不上服务器: {e}")