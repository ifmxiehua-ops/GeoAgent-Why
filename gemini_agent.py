import os
import google.generativeai as genai
from agent_core import run_gis_agent

# ==========================================
# 1. 核心网络与安全配置
# ==========================================
# 如果你在中国大陆使用，请务必配置你的代理端口（常见如 7890, 7897, 10809）
proxy_port = "7897"
os.environ['http_proxy'] = f"http://127.0.0.1:{proxy_port}"
os.environ['https_proxy'] = f"http://127.0.0.1:{proxy_port}"

# 请在此处填入你从 Google AI Studio 获取的 API Key
# 替换为以下两行：
st.sidebar.markdown("### 🔑 密钥配置")
os.environ["GEMINI_API_KEY"] = st.sidebar.text_input("请输入您的 Gemini API Key：", type="password")
genai.configure(api_key=os.environ["GEMINI_API_KEY"])


# ==========================================
# 2. 定义 AI 的“手脚”：地理处理工具函数
# ==========================================
def clip_swan_data(user_instruction, nc_path, mask_path):
    """
    专门用于处理海洋 SWAN 模式 nc 数据的裁剪工具。
    参数:
    user_instruction: 用户的原始指令描述
    nc_path: 输入的 .nc 文件绝对路径（由 AI 自动从对话中提取）
    mask_path: 用于裁剪的 .shp 掩膜文件绝对路径（由 AI 自动从对话中提取）
    """
    # 自动定义一个输出结果路径
    output_path = r"D:\mygis\GeoAgent-Pro\result\ai_output.shp"

    print(f"\n[AI 指令执行] 正在尝试裁剪文件...")
    print(f"   - NC文件: {nc_path}")
    print(f"   - 掩膜SHP: {mask_path}")

    # 跨环境调用之前写好的 agent_core 逻辑
    success, message = run_gis_agent(user_instruction, nc_path, mask_path, output_path)

    if success:
        return f"【任务完成】长官！裁剪操作已成功执行。结果已保存至：{output_path}"
    else:
        return f"【执行失败】底层引擎报错：{message}"


# ==========================================
# 3. 初始化 Gemini 3 智能体大脑
# ==========================================
# 在 2026 年，我们使用最先进的 Gemini 3 Flash 模型
model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    tools=[clip_swan_data]  # 将工具箱交给 AI
)

# 开启自动函数调用模式（这是 Agent 自动干活的核心）
chat = model.start_chat(enable_automatic_function_calling=True)

# ==========================================
# 4. 交互界面
# ==========================================
print("-" * 50)
print("🤖 [Gemini 3 Geo-Agent] 已就绪！")
print("提示：你可以直接用中文下达指令，我会自动提取路径并操作。")
print("退出请键入 'exit'")
print("-" * 50)

while True:
    try:
        user_input = input("\n👤 用户: ").strip()

        if not user_input:
            continue
        if user_input.lower() in ['exit', 'quit', '退出']:
            print("再见！")
            break

        print("🧠 AI 正在思考并执行规划...")

        # 发送消息给 Gemini
        response = chat.send_message(user_input)

        # 打印 AI 的最终回复
        print(f"\n🤖 AI: {response.text}")

    except Exception as e:
        print(f"\n❌ 发生了意外错误: {e}")
        print("提示：请检查你的 API Key 是否有效，或代理服务器是否正常连接。")