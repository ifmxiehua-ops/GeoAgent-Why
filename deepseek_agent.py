"""
gemini_agent.py
命令行版 Gemini Geo-Agent
支持任意 NC 文件，变量参数可配置
"""

import os
import json
import google.generativeai as genai
from netCDF4 import Dataset
from agent_core import run_gis_agent, run_idw_agent, run_raster_clip_agent, run_contour_agent

# ══════════════════════════════════════════
# 1. 网络与 API Key 配置
# ══════════════════════════════════════════
proxy_port = "7897"
os.environ['http_proxy']  = f"http://127.0.0.1:{proxy_port}"
os.environ['https_proxy'] = f"http://127.0.0.1:{proxy_port}"

# 优先从环境变量读取，避免硬编码泄露
# 使用前可在终端执行：set GEMINI_API_KEY=你的Key（Windows）
api_key = os.environ.get("GEMINI_API_KEY", "").strip()
if not api_key:
    api_key = input("请输入你的 Gemini API Key（不会被保存）：").strip()
if not api_key:
    print("❌ 未提供 API Key，程序退出。")
    exit(1)

genai.configure(api_key=api_key)

# ══════════════════════════════════════════
# 2. 默认参数配置
# ══════════════════════════════════════════
DEFAULT_OUTPUT_DIR = r"D:\mygis\GeoAgent-Pro\result"

# ══════════════════════════════════════════
# 3. NC 文件探查工具
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
# 3. AI 工具定义
# ══════════════════════════════════════════
def clip_swan_data(
    user_instruction: str,
    nc_path: str,
    mask_path: str,
    output_dir: str = "",
    time_step: str = "0",
    var_x: str = "nodes_x",
    var_y: str = "nodes_y",
    var_fields: str = "Hs,Dir,Per",
    var_time: str = ""
) -> str:
    """
    处理 NetCDF 数据的完整裁剪工具（支持任意变量名）。

    参数：
        user_instruction : 用户原始指令
        nc_path          : 输入的 .nc 文件绝对路径
        mask_path        : 掩膜 .shp 文件绝对路径
        output_dir       : 输出目录（可选，AI 从指令提取；默认使用配置值）
        time_step        : 时间步索引字符串，或 "all"（默认 "0"）
        var_x            : X 坐标变量名（默认 "nodes_x"；AI 可从 inspect_nc 结果提取）
        var_y            : Y 坐标变量名（默认 "nodes_y"；AI 可从 inspect_nc 结果提取）
        var_fields       : 逗号分隔的数据变量名（默认 "Hs,Dir,Per"）
        var_time         : 时间变量名（可选；默认 ""）
    """
    out_dir = output_dir.strip() if output_dir.strip() else DEFAULT_OUTPUT_DIR
    ts_raw  = time_step.strip() if time_step.strip() else "0"
    ts      = "all" if ts_raw.lower() == "all" else int(ts_raw)
    
    # 解析变量字段列表
    fields = [v.strip() for v in var_fields.split(',') if v.strip()]
    if not fields:
        fields = ["Hs", "Dir", "Per"]

    fname       = "ai_output_all.shp" if ts == "all" else f"ai_output_step{ts:03d}.shp"
    output_file = os.path.join(out_dir, fname)

    print(f"\n[工具调用] clip_swan_data")
    print(f"   NC     : {nc_path}")
    print(f"   掩膜   : {mask_path}")
    print(f"   输出   : {output_file}")
    print(f"   时间步 : {'全部' if ts == 'all' else ts}")
    print(f"   坐标   : X={var_x}, Y={var_y}")
    print(f"   字段   : {', '.join(fields)}")
    print(f"   时间   : {var_time if var_time else '(none)'}\n")

    # 日志直接打印到终端（命令行模式）
    success, full_output = run_gis_agent(
        task_description=user_instruction,
        nc_file=nc_path,
        mask_file=mask_path,
        output_file=output_file,
        time_step=ts,
        log_callback=None,  # 命令行模式不需要回调
        var_x=var_x,
        var_y=var_y,
        var_fields=fields,
        var_time=var_time.strip() if var_time else ""
    )

    if success:
        step_desc = "全部时间步" if ts == "all" else f"第 {ts} 个时间步"
        return (
            f"✅ 【任务完成】{step_desc}已处理完毕！\n"
            f"提取字段：{', '.join(fields)}\n"
            f"结果已保存至：{output_file}"
        )
    else:
        return f"❌ 【执行失败】底层引擎报错，请查看上方终端日志。"


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
    cs = float(cell_size) if cell_size.strip() else 0.01
    pw = float(power) if power.strip() else 2.0

    print(f"\n[工具调用] idw_interpolate")
    print(f"   输入SHP  : {input_shp}")
    print(f"   字段     : {field_name}")
    print(f"   输出栅格 : {output_raster}")
    print(f"   掩膜     : {mask_shp if mask_shp.strip() else '(none)'}")
    print(f"   像元大小 : {cs}  幂次: {pw}\n")

    success, _ = run_idw_agent(
        task_description=user_instruction,
        input_shp=input_shp,
        field_name=field_name,
        output_raster=output_raster,
        cell_size=cs,
        power=pw,
        log_callback=None
    )

    if not success:
        return "❌ 【IDW 插值失败】底层引擎报错，请查看上方终端日志。"

    if mask_shp.strip():
        clipped_raster = output_raster.replace(".tif", "_clipped.tif")
        clip_success, _ = run_raster_clip_agent(
            task_description=user_instruction,
            input_raster=output_raster,
            mask_shp=mask_shp.strip(),
            output_raster=clipped_raster,
            log_callback=None
        )
        if clip_success:
            return (
                f"✅ 【IDW 插值 + 裁剪完成】\n"
                f"插值字段：{field_name}\n"
                f"裁剪结果：{clipped_raster}"
            )
        else:
            return (
                f"⚠️ 【IDW 插值成功，裁剪失败】\n"
                f"插值结果：{output_raster}\n"
                f"裁剪错误请查看上方终端日志。"
            )

    return (
        f"✅ 【IDW 插值完成】\n"
        f"插值字段：{field_name}\n"
        f"输出栅格：{output_raster}"
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
    iv = float(interval) if interval.strip() else 0.5

    print(f"\n[工具调用] generate_contour")
    print(f"   输入栅格 : {input_raster}")
    print(f"   输出SHP  : {output_shp}")
    print(f"   间距     : {iv}\n")

    success, _ = run_contour_agent(
        task_description=user_instruction,
        input_raster=input_raster,
        output_shp=output_shp,
        interval=iv,
        log_callback=None
    )

    if success:
        return (
            f"✅ 【等值线生成完成】\n"
            f"等值线间距：{iv}\n"
            f"输出文件：{output_shp}"
        )
    else:
        return "❌ 【等值线生成失败】底层引擎报错，请查看上方终端日志。"


# ══════════════════════════════════════════
# 4. 初始化 Gemini Agent
# ══════════════════════════════════════════
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",   # ← 如果报错，先运行 check_models.py 查看可用模型
    tools=[inspect_nc, clip_swan_data, idw_interpolate, generate_contour]
)
chat = model.start_chat(enable_automatic_function_calling=True)

# ══════════════════════════════════════════
# 5. 命令行交互
# ══════════════════════════════════════════
print("=" * 55)
print("🌊 [GeoAgent-Pro 命令行版] 已就绪！")
print("支持：空间裁剪 | Hs/Dir/Per 提取 | 单步/全步处理")
print("退出请键入 'exit'")
print("=" * 55)

while True:
    try:
        user_input = input("\n👤 用户: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ['exit', 'quit', '退出']:
            print("再见！")
            break

        print("🧠 AI 正在解析指令...")
        response = chat.send_message(user_input)
        print(f"\n🤖 AI: {response.text}")

    except KeyboardInterrupt:
        print("\n用户中断，退出。")
        break
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        print("请检查 API Key 和代理是否正常。")