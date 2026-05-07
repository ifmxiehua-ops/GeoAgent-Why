"""
app.py
GeoAgent-Pro Streamlit 前端
支持任意 NC 文件，变量参数可配置
"""

import streamlit as st
import google.generativeai as genai
import os
import json
from netCDF4 import Dataset
from agent_core import run_gis_agent, run_idw_agent, run_raster_clip_agent, run_contour_agent

# ══════════════════════════════════════════
# 页面基础配置
# ══════════════════════════════════════════
st.set_page_config(page_title="GeoAgent-Pro", page_icon="🌊", layout="centered", menu_items={"Get help": "https://github.com/ifmxiehua-ops/GeoAgent-Why"})

st.markdown(
    '<a href="https://github.com/ifmxiehua-ops/GeoAgent-Why" target="_blank" '
    'style="position:fixed;top:14px;right:80px;z-index:9999;">'
    '<img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" width="32"/>'
    '</a>',
    unsafe_allow_html=True
)

st.markdown("""
<style>
[data-testid="stToolbar"] {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("🌊 GeoAgent-Pro")
st.subheader("智能海洋空间数据处理中枢")
st.markdown("---")

# ══════════════════════════════════════════
# 侧边栏配置
# ══════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🔑 密钥配置")
    api_key = st.text_input("Gemini API Key：", type="password")

    st.markdown("### 🌐 网络配置")
    proxy_port = st.text_input("代理端口（留空不使用代理）：", value="7897")

    st.markdown("### ⚙️ 默认处理参数")
    default_output_dir = st.text_input(
        "默认输出目录：",
        value=r"D:\mygis\GeoAgent-Pro\result"
    )
    default_time_step = st.selectbox(
        "默认时间步：",
        options=["0 (第1步)", "all (全部121步)"] + [str(i) for i in range(1, 121)],
        index=0
    )
    # 解析时间步选项
    _ts_raw = default_time_step.split(" ")[0]
    default_ts = "all" if _ts_raw == "all" else int(_ts_raw)

    st.markdown("---")
    st.caption("💡 指令中可直接指定路径和时间步，AI 会自动识别并覆盖默认值。")

# ── 设置代理 ──
if proxy_port:
    os.environ['http_proxy']  = f"http://127.0.0.1:{proxy_port}"
    os.environ['https_proxy'] = f"http://127.0.0.1:{proxy_port}"

# ── 没有 Key 停止渲染 ──
if not api_key:
    st.warning("⚠️ 请先在左侧栏输入您的 Gemini API Key 以开始使用。")
    st.stop()

genai.configure(api_key=api_key)

# ══════════════════════════════════════════
# NC 文件探查工具（Gemini Function Calling）
# ══════════════════════════════════════════
def inspect_nc(nc_path: str) -> str:
    """
    探查 NC 文件结构，列出所有变量信息。
    AI 可在不知道变量名时先调用此工具来理解文件结构。
    
    参数：
        nc_path : NC 文件绝对路径
        
    返回：JSON 字符串，包含变量名、维度、数据类型信息
    """
    try:
        nc = Dataset(nc_path)
        info = {
            "file": nc_path,
            "dimensions": {dim: size for dim, size in nc.dimensions.items()},
            "variables": {}
        }
        
        for var_name in nc.variables:
            var = nc.variables[var_name]
            info["variables"][var_name] = {
                "shape": var.shape,
                "dtype": str(var.dtype),
                "dimensions": list(var.dimensions)
            }
        
        nc.close()
        return json.dumps(info, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

# ══════════════════════════════════════════
# AI 工具定义（Gemini Function Calling）
# ══════════════════════════════════════════
def clip_swan_data(
    user_instruction: str,
    nc_path: str,
    mask_path: str,
    output_dir: str = "",
    time_step: str = "",
    var_x: str = "nodes_x",
    var_y: str = "nodes_y",
    var_fields: str = "Hs,Dir,Per",
    var_time: str = ""
) -> str:
    """
    处理 NetCDF 数据的完整裁剪工具（支持任意变量名）。

    参数：
        user_instruction : 用户原始指令（描述任务意图）
        nc_path          : 输入的 .nc 文件绝对路径
        mask_path        : 用于裁剪的 .shp 掩膜文件绝对路径
        output_dir       : 输出目录路径（可选，AI 从指令提取；未提供则使用默认值）
        time_step        : 时间步索引，整数字符串 或 "all"（可选）
        var_x            : X 坐标变量名（默认 "nodes_x"；AI 可从 inspect_nc 结果提取）
        var_y            : Y 坐标变量名（默认 "nodes_y"；AI 可从 inspect_nc 结果提取）
        var_fields       : 逗号分隔的数据变量名（默认 "Hs,Dir,Per"）
        var_time         : 时间变量名（可选；默认 ""）
    """
    # ── 参数回退到侧边栏默认值 ──
    out_dir = output_dir.strip() if output_dir.strip() else default_output_dir
    ts_raw  = time_step.strip()  if time_step.strip()  else str(default_ts)
    ts      = "all" if ts_raw.lower() == "all" else int(ts_raw)
    
    # 解析变量字段列表
    fields = [v.strip() for v in var_fields.split(',') if v.strip()]
    if not fields:
        fields = ["Hs", "Dir", "Per"]

    # ── 构造输出文件路径 ──
    fname = "ai_output_all.shp" if ts == "all" else f"ai_output_step{ts:03d}.shp"
    output_file = os.path.join(out_dir, fname)

    # ── 日志收集列表 + Streamlit 实时容器 ──
    log_lines = []
    log_placeholder = st.empty()

    def update_log(line: str):
        """每收到一行日志，追加到列表并刷新 UI"""
        log_lines.append(line)
        # 用 code block 展示，保持等宽对齐
        log_placeholder.code('\n'.join(log_lines[-60:]), language="")  # 最多显示最近60行

    # ── 调用底层引擎 ──
    success, full_output = run_gis_agent(
        task_description=user_instruction,
        nc_file=nc_path,
        mask_file=mask_path,
        output_file=output_file,
        time_step=ts,
        log_callback=update_log,
        var_x=var_x,
        var_y=var_y,
        var_fields=fields,
        var_time=var_time.strip() if var_time else ""
    )

    # ── 返回 AI 最终总结 ──
    if success:
        step_desc = "全部时间步" if ts == "all" else f"第 {ts} 个时间步"
        return (
            f"✅ **任务完成！**\n\n"
            f"- **处理范围**：{step_desc}\n"
            f"- **提取字段**：{', '.join(fields)}\n"
            f"- **结果目录**：`{out_dir}`\n"
            f"- **文件名**：`{fname}`\n\n"
            f"可直接将 `{output_file}` 拖入 ArcGIS Pro 查看。"
        )
    else:
        return (
            f"❌ **任务失败**\n\n"
            f"底层引擎报错，请查看上方日志了解详情。\n\n"
            f"常见原因：\n"
            f"1. 变量名不匹配（用 inspect_nc 工具查看文件结构）\n"
            f"2. ArcPy 环境路径不对（检查 agent_core.py 中的 `python_exe`）\n"
            f"3. 输入文件路径不存在\n"
            f"4. 输出目录无写入权限"
        )


def idw_interpolate(
    user_instruction: str,
    input_shp: str,
    field_name: str,
    output_raster: str,
    mask_shp: str = "",
    cell_size: str = "0.01",
    power: str = "2"
) -> str:
    """
    对散点 SHP 数据执行 IDW 栅格插值，可选掩膜裁剪。

    参数：
        user_instruction : 用户原始指令
        input_shp        : 输入散点 .shp 文件绝对路径
        field_name       : 用于插值的字段名
        output_raster    : 输出栅格文件路径（.tif）
        mask_shp         : 掩膜 .shp 文件路径（可选；非空时对插值结果进行裁剪）
        cell_size        : 栅格单元大小字符串（默认 "0.01"）
        power            : IDW 幂次参数字符串（默认 "2"）
    """
    log_lines = []
    log_placeholder = st.empty()

    def update_log(line: str):
        log_lines.append(line)
        log_placeholder.code('\n'.join(log_lines[-60:]), language="")

    cs = float(cell_size) if cell_size.strip() else 0.01
    pw = float(power) if power.strip() else 2.0

    success, _ = run_idw_agent(
        task_description=user_instruction,
        input_shp=input_shp,
        field_name=field_name,
        output_raster=output_raster,
        cell_size=cs,
        power=pw,
        log_callback=update_log
    )

    if not success:
        return (
            f"❌ **IDW 插值失败**\n\n"
            f"请查看上方日志了解详情。"
        )

    if mask_shp.strip():
        clipped_raster = output_raster.replace(".tif", "_clipped.tif")
        clip_success, _ = run_raster_clip_agent(
            task_description=user_instruction,
            input_raster=output_raster,
            mask_shp=mask_shp.strip(),
            output_raster=clipped_raster,
            log_callback=update_log
        )
        if clip_success:
            return (
                f"✅ **IDW 插值 + 裁剪完成！**\n\n"
                f"- **插值字段**：{field_name}\n"
                f"- **裁剪结果**：`{clipped_raster}`"
            )
        else:
            return (
                f"⚠️ **IDW 插值成功，但裁剪失败**\n\n"
                f"- **插值结果**：`{output_raster}`\n"
                f"- 裁剪错误请查看上方日志。"
            )

    return (
        f"✅ **IDW 插值完成！**\n\n"
        f"- **插值字段**：{field_name}\n"
        f"- **输出栅格**：`{output_raster}`"
    )


def generate_contour(
    user_instruction: str,
    input_raster: str,
    output_shp: str,
    interval: str = "0.5"
) -> str:
    """
    从栅格生成等值线 SHP 文件。

    参数：
        user_instruction : 用户原始指令
        input_raster     : 输入栅格文件绝对路径
        output_shp       : 输出等值线 .shp 文件绝对路径
        interval         : 等值线间距字符串（默认 "0.5"）
    """
    log_lines = []
    log_placeholder = st.empty()

    def update_log(line: str):
        log_lines.append(line)
        log_placeholder.code('\n'.join(log_lines[-60:]), language="")

    iv = float(interval) if interval.strip() else 0.5

    success, _ = run_contour_agent(
        task_description=user_instruction,
        input_raster=input_raster,
        output_shp=output_shp,
        interval=iv,
        log_callback=update_log
    )

    if success:
        return (
            f"✅ **等值线生成完成！**\n\n"
            f"- **等值线间距**：{iv}\n"
            f"- **输出文件**：`{output_shp}`"
        )
    else:
        return (
            f"❌ **等值线生成失败**\n\n"
            f"请查看上方日志了解详情。"
        )


# ══════════════════════════════════════════
# 聊天会话初始化（Key 变化时自动重置）
# ══════════════════════════════════════════
if ("current_api_key" not in st.session_state
        or st.session_state.current_api_key != api_key):
    st.session_state.current_api_key = api_key
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",   # ← 如果报错，先运行 check_models.py 查看可用模型名
        tools=[inspect_nc, clip_swan_data, idw_interpolate, generate_contour]
    )
    st.session_state.chat_session = model.start_chat(
        enable_automatic_function_calling=True
    )
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "您好！我是 GeoAgent-Pro 🌊\n\n"
                "我可以帮您处理任意格式的 NetCDF 地理空间数据，支持：\n"
                "- 自动识别 NC 文件变量结构（使用 inspect_nc 工具）\n"
                "- 灵活配置坐标和数据字段名称\n"
                "- 空间裁剪（指定 .shp 掩膜）\n"
                "- 选择单个时间步或一次处理全部步骤\n\n"
                "**示例指令：**\n"
                "> 帮我查看一下 `D:\\mygis\\Wave_2.nc` 包含哪些变量"
            )
        }
    ]

# ══════════════════════════════════════════
# 渲染历史记录
# ══════════════════════════════════════════
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ══════════════════════════════════════════
# 聊天输入与响应
# ══════════════════════════════════════════
if user_input := st.chat_input("例如：处理第5步，结果保存到 D:\\mygis\\test_res..."):

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        st.markdown("🧠 **正在解析指令并调度底层引擎...**")
        st.markdown("---")

        try:
            response = st.session_state.chat_session.send_message(user_input)
            ai_reply = response.text
        except Exception as e:
            ai_reply = f"❌ 连接 Gemini 服务器失败：{e}"

        st.markdown("---")
        st.markdown(ai_reply)
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})