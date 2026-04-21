import streamlit as st
import google.generativeai as genai
import os
import time
from agent_core import run_gis_agent

# ==========================================
# 1. 网络与大模型配置 (与之前一致)
# ==========================================
proxy_port = "7897"  # 你的专属通关端口
os.environ['http_proxy'] = f"http://127.0.0.1:{proxy_port}"
os.environ['https_proxy'] = f"http://127.0.0.1:{proxy_port}"

# 【请在这里填入你的真实 API KEY】
# 替换为以下两行：
st.sidebar.markdown("### 🔑 密钥配置")
os.environ["GEMINI_API_KEY"] = st.sidebar.text_input("请输入您的 Gemini API Key：", type="password")
genai.configure(api_key=os.environ["GEMINI_API_KEY"])


# ==========================================
# 2. 定义 AI 工具 (无缝接入 ArcPy)
# ==========================================
def clip_swan_data(user_instruction, nc_path, mask_path):
    """用于处理海洋 SWAN 模式 nc 数据的裁剪工具"""
    output_path = r"D:\mygis\GeoAgent-Pro\result\ai_output.shp"

    # 跨环境唤醒底层引擎
    success, message = run_gis_agent(user_instruction, nc_path, mask_path, output_path)
    if success:
        return f"✅ 报告长官：空间裁剪任务已完成！\n\n📁 **结果文件路径**：`{output_path}`\n\n您可以直接将此文件拖入 ArcGIS Pro 中查看。"
    else:
        return f"❌ 任务失败。底层报错：{message}"


# ==========================================
# 3. 网页 UI 设计与交互逻辑
# ==========================================
# 设置网页标题和图标
st.set_page_config(page_title="GeoAgent-Pro", page_icon="🌍", layout="centered")

st.title("🌍 GeoAgent-Pro")
st.subheader("智能海洋空间数据处理中枢")
st.markdown("---")

# 初始化 Session State (用于保存聊天记录和 AI 记忆)
if "chat_session" not in st.session_state:
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        tools=[clip_swan_data]
    )
    st.session_state.chat_session = model.start_chat(enable_automatic_function_calling=True)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant",
         "content": "您好！我是 GeoAgent。我可以帮您自动调用底层 GIS 引擎处理数据。请问今天需要切点什么？"}
    ]

# 在网页上渲染历史聊天记录
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==========================================
# 4. 聊天输入与 AI 响应处理
# ==========================================
# 聊天输入框
if user_input := st.chat_input("例如：帮我把D盘的波浪nc数据切一下，掩膜用桌面上的shp..."):
    # 1. 把用户的话显示在界面上
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. 让 AI 开始思考并调用工具
    with st.chat_message("assistant"):
        # 用一个华丽的加载动画掩盖底层的运算时间
        with st.spinner('🧠 正在进行意图识别与空间运算，请稍候... (跨环境唤醒 ArcPy 中)'):
            try:
                # 发送给 Gemini，如果是指令，它会在后台默默执行 clip_swan_data
                response = st.session_state.chat_session.send_message(user_input)
                ai_reply = response.text
            except Exception as e:
                ai_reply = f"❌ 连接服务器发生错误：{e}"

        # 3. 运算完毕，打字机效果输出结果
        st.markdown(ai_reply)
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})