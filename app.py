"""
app.py
GeoAgent-Pro Streamlit 前端
支持任意 NC 文件，变量参数可配置
"""

import streamlit as st
from openai import OpenAI
import os
import json
import time
import threading
from netCDF4 import Dataset
from agent_core import run_gis_agent, run_idw_agent, run_raster_clip_agent, run_contour_agent

# ══════════════════════════════════════════
# 页面基础配置
# ══════════════════════════════════════════
st.set_page_config(page_title="GeoAgent-Pro", page_icon="🌊", layout="centered", initial_sidebar_state="expanded", menu_items={"Get help": "https://github.com/ifmxiehua-ops/GeoAgent-Why"})

st.markdown(
    '<a href="https://github.com/ifmxiehua-ops/GeoAgent-Why" target="_blank" '
    'style="position:fixed;top:14px;right:80px;z-index:9999;">'
    '<img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" width="32"/>'
    '</a>',
    unsafe_allow_html=True
)

st.markdown("""
<style>
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stDeployButton"] { display: none; }
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
    if "api_key_input" not in st.session_state:
        st.session_state["api_key_input"] = os.environ.get("DEEPSEEK_API_KEY", "")

    st.text_input("DeepSeek API Key：", type="password", key="api_key_input")
    api_key = st.session_state["api_key_input"]

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
    st.warning("⚠️ 请先在左侧栏输入您的 DeepSeek API Key 以开始使用。")
    st.stop()

# ══════════════════════════════════════════
# 全局锁（防止 GIS 引擎并发调用）
# ══════════════════════════════════════════
_arcpy_lock = threading.Lock()

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
    if _arcpy_lock.locked():
        return "⚠️ **GIS 引擎正在处理其他任务**\n\n请稍后重试。"
    
    with _arcpy_lock:
        out_dir = output_dir.strip() if output_dir.strip() else default_output_dir
        ts_raw  = time_step.strip()  if time_step.strip()  else str(default_ts)
        ts      = "all" if ts_raw.lower() == "all" else int(ts_raw)

        fields = [v.strip() for v in var_fields.split(',') if v.strip()]
        if not fields:
            fields = ["Hs", "Dir", "Per"]

        fname = "ai_output_all.shp" if ts == "all" else f"ai_output_step{ts:03d}.shp"
        output_file = os.path.join(out_dir, fname)

        log_lines = []
        log_placeholder = st.empty()

        def update_log(line: str):
            log_lines.append(line)
            log_placeholder.code('\n'.join(log_lines[-60:]), language="")

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
    if _arcpy_lock.locked():
        return "⚠️ **GIS 引擎正在处理其他任务**\n\n请稍后重试。"
    
    with _arcpy_lock:
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
    if _arcpy_lock.locked():
        return "⚠️ **GIS 引擎正在处理其他任务**\n\n请稍后重试。"
    
    with _arcpy_lock:
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


def clip_raster(
    user_instruction: str,
    input_raster: str,
    mask_shp: str,
    output_raster: str
) -> str:
    """
    对已有 .tif 栅格执行掩膜裁剪。

    参数：
        user_instruction : 用户原始指令
        input_raster     : 输入 .tif 栅格文件绝对路径
        mask_shp         : 掩膜 .shp 文件绝对路径
        output_raster    : 输出裁剪后的 .tif 文件绝对路径
    """
    if _arcpy_lock.locked():
        return "⚠️ **GIS 引擎正在处理其他任务**\n\n请稍后重试。"

    with _arcpy_lock:
        log_lines = []
        log_placeholder = st.empty()

        def update_log(line: str):
            log_lines.append(line)
            log_placeholder.code('\n'.join(log_lines[-60:]), language="")

        success, _ = run_raster_clip_agent(
            task_description=user_instruction,
            input_raster=input_raster,
            mask_shp=mask_shp,
            output_raster=output_raster,
            log_callback=update_log
        )

        if success:
            return (
                f"✅ **栅格裁剪完成！**\n\n"
                f"- **输入栅格**：`{input_raster}`\n"
                f"- **掩膜文件**：`{mask_shp}`\n"
                f"- **输出文件**：`{output_raster}`"
            )
        else:
            return (
                f"❌ **栅格裁剪失败**\n\n"
                f"请查看上方日志了解详情。"
            )


# ══════════════════════════════════════════
# DeepSeek 配置
# ══════════════════════════════════════════
SYSTEM_PROMPT = (
    "你是一个GIS数据处理助手。你拥有以下5个工具：inspect_nc、clip_swan_data、idw_interpolate、generate_contour、clip_raster。"
    "请严格遵守以下规则：\n"
    "1. 除非用户明确要求查看变量或文件结构，否则不要调用inspect_nc工具。\n"
    "2. 每次用户指令只调用一个工具，工具执行完毕后直接返回结果，不得链式调用。\n"
    "3. 用户已提供所有路径和参数，直接使用，不需要预先验证。\n"
    "4. 如果用户未指定var_x/var_y，直接使用默认值nodes_x和nodes_y。\n"
    "5. 当输入文件是 .tif 栅格时，必须调用 clip_raster 工具，严禁调用 idw_interpolate；"
    "idw_interpolate 仅用于输入是散点 .shp 文件的插值任务。"
)

DS_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "inspect_nc",
            "description": "探查NC文件结构，列出所有变量信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "nc_path": {"type": "string", "description": "NC文件绝对路径"}
                },
                "required": ["nc_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clip_swan_data",
            "description": "处理NetCDF数据的完整裁剪工具，支持任意变量名。",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_instruction": {"type": "string"},
                    "nc_path": {"type": "string"},
                    "mask_path": {"type": "string"},
                    "output_dir": {"type": "string", "default": ""},
                    "time_step": {"type": "string", "default": ""},
                    "var_x": {"type": "string", "default": "nodes_x"},
                    "var_y": {"type": "string", "default": "nodes_y"},
                    "var_fields": {"type": "string", "default": "Hs,Dir,Per"},
                    "var_time": {"type": "string", "default": ""}
                },
                "required": ["user_instruction", "nc_path", "mask_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "idw_interpolate",
            "description": "对散点SHP数据执行IDW栅格插值，可选掩膜裁剪。",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_instruction": {"type": "string"},
                    "input_shp": {"type": "string"},
                    "field_name": {"type": "string"},
                    "output_raster": {"type": "string"},
                    "mask_shp": {"type": "string", "default": ""},
                    "cell_size": {"type": "string", "default": "0.01"},
                    "power": {"type": "string", "default": "2"}
                },
                "required": ["user_instruction", "input_shp", "field_name", "output_raster"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_contour",
            "description": "从栅格生成等值线SHP文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_instruction": {"type": "string"},
                    "input_raster": {"type": "string"},
                    "output_shp": {"type": "string"},
                    "interval": {"type": "string", "default": "0.5"}
                },
                "required": ["user_instruction", "input_raster", "output_shp"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clip_raster",
            "description": (
                "对已有 .tif 栅格执行掩膜裁剪。"
                "当用户输入是 .tif 文件时必须用此工具，而非 idw_interpolate。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_instruction": {"type": "string"},
                    "input_raster": {"type": "string"},
                    "mask_shp": {"type": "string"},
                    "output_raster": {"type": "string"}
                },
                "required": ["user_instruction", "input_raster", "mask_shp", "output_raster"]
            }
        }
    }
]

TOOL_MAP = {
    "inspect_nc": inspect_nc,
    "clip_swan_data": clip_swan_data,
    "idw_interpolate": idw_interpolate,
    "generate_contour": generate_contour,
    "clip_raster": clip_raster,
}

# ══════════════════════════════════════════
# 聊天会话初始化（Key 变化时自动重置）
# ══════════════════════════════════════════
if st.session_state.get("_session_sig") != api_key:
    st.session_state["_session_sig"] = api_key
    st.session_state.ds_client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )
    st.session_state.ds_history = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "您好！我是 GeoAgent-Pro 🌊\n\n"
                "现在使用 DeepSeek 驱动，支持：\n"
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

        ai_reply = ""
        try:
            st.session_state.ds_history.append({"role": "user", "content": user_input})

            response = st.session_state.ds_client.chat.completions.create(
                model="deepseek-chat",
                messages=st.session_state.ds_history,
                tools=DS_TOOLS,
                tool_choice="auto"
            )
            msg = response.choices[0].message

            if msg.tool_calls:
                st.session_state.ds_history.append(msg)
                for tc in msg.tool_calls:
                    func_name = tc.function.name
                    func_args = json.loads(tc.function.arguments)
                    tool_result = TOOL_MAP[func_name](**func_args)
                    st.session_state.ds_history.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_result
                    })

                final_response = st.session_state.ds_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=st.session_state.ds_history
                )
                ai_reply = final_response.choices[0].message.content
                st.session_state.ds_history.append({"role": "assistant", "content": ai_reply})
            else:
                ai_reply = msg.content
                st.session_state.ds_history.append({"role": "assistant", "content": ai_reply})

        except Exception as e:
            ai_reply = f"❌ 连接 DeepSeek 服务器失败：{e}"

        st.markdown("---")
        st.markdown(ai_reply)
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
