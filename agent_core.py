"""
agent_core.py
Agent 核心调度模块：实时流式日志 + 跨环境调用底层 GIS 引擎
"""

import subprocess
import os
import sys
import copy


def run_gis_agent(task_description, nc_file, mask_file, output_file,
                  time_step=0, log_callback=None, var_x="nodes_x", var_y="nodes_y",
                  var_fields=None, var_time=""):
    """
    Agent 核心调度函数。

    参数：
        task_description : 用户原始需求
        nc_file          : 输入 .nc 文件路径
        mask_file        : 掩膜 .shp 文件路径
        output_file      : 输出 .shp 文件路径
        time_step        : 时间步索引（整数）或 "all"，默认 0
        log_callback     : 可选回调 f(line: str)，每行日志调用一次
        var_x            : X 坐标变量名（默认 "nodes_x"）
        var_y            : Y 坐标变量名（默认 "nodes_y"）
        var_fields       : 要提取的数据变量列表（默认 ["Hs", "Dir", "Per"]）
        var_time         : 时间变量名（可选，默认 ""）
    """
    if var_fields is None:
        var_fields = ["Hs", "Dir", "Per"]

    def _log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    _log("=" * 55)
    _log("[Agent] Starting...")
    _log(f"[Agent] Task        : {task_description}")
    _log(f"[Agent] NC file     : {nc_file}")
    _log(f"[Agent] Mask file   : {mask_file}")
    _log(f"[Agent] Output      : {output_file}")
    _log(f"[Agent] Time step   : {'all' if str(time_step) == 'all' else time_step}")
    _log("=" * 55)
    _log("[Agent] Calling GIS engine...\n")

    # 使用当前 Python 解释器（需与 arcpy 同环境）
    # 如果 arcpy 在独立 ArcGIS Pro 环境，请改为完整路径，例如：
    # python_exe = r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
    python_exe  = sys.executable
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "tool_swan_processor.py")

    command = [
        python_exe,
        script_path,
        "--input_nc",   nc_file,
        "--mask_shp",   mask_file,
        "--output_shp", output_file,
        "--time_step",  str(time_step),
        "--var_x",      var_x,
        "--var_y",      var_y,
        "--var_fields", ",".join(var_fields),
    ]
    
    # 添加可选的时间变量参数
    if var_time:
        command.extend(["--var_time", var_time])

    # 强制子进程使用 UTF-8，彻底避免 Windows GBK 编码错误
    env = copy.copy(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'

    all_output = []

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # 合并 stderr 到 stdout
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,                  # 行缓冲，保证实时性
            env=env                     # 传入强制 UTF-8 的环境变量
        )

        for line in iter(process.stdout.readline, ''):
            line = line.rstrip('\n')
            if line:
                _log(line)
                all_output.append(line)

        process.stdout.close()
        process.wait()

        full_output = '\n'.join(all_output)

        if process.returncode == 0 and any('SUCCESS' in l for l in all_output):
            _log("\n[Agent] GIS engine finished successfully.")
            _log("=" * 55 + "\n")
            return True, full_output
        else:
            _log("\n[Agent] GIS engine reported an error.")
            _log("=" * 55 + "\n")
            return False, full_output

    except FileNotFoundError:
        msg = (f"[Agent] Script not found: {script_path}\n"
               f"Please make sure tool_swan_processor.py is in the same directory as agent_core.py.")
        _log(msg)
        return False, msg

    except Exception as e:
        msg = f"[Agent] Unexpected error: {e}"
        _log(msg)
        return False, msg


def run_idw_agent(task_description, input_shp, field_name, output_raster,
                  cell_size=0.01, power=2, log_callback=None):
    """
    IDW 插值 Agent 核心调度函数。

    参数：
        task_description : 用户原始需求
        input_shp        : 输入散点 .shp 文件路径
        field_name       : 用于插值的字段名
        output_raster    : 输出栅格文件路径
        cell_size        : 栅格单元大小（默认 0.01）
        power            : IDW 幂次参数（默认 2）
        log_callback     : 可选回调 f(line: str)，每行日志调用一次
    """

    def _log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    _log("=" * 55)
    _log("[Agent] Starting IDW interpolation...")
    _log(f"[Agent] Task         : {task_description}")
    _log(f"[Agent] Input SHP    : {input_shp}")
    _log(f"[Agent] Field        : {field_name}")
    _log(f"[Agent] Output       : {output_raster}")
    _log(f"[Agent] Cell size    : {cell_size}")
    _log(f"[Agent] Power        : {power}")
    _log("=" * 55)
    _log("[Agent] Calling IDW engine...\n")

    python_exe  = sys.executable
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "tool_idw_processor.py")

    command = [
        python_exe,
        script_path,
        "--input_shp",      input_shp,
        "--field_name",     field_name,
        "--output_raster",  output_raster,
        "--cell_size",      str(cell_size),
        "--power",          str(power),
    ]

    # 强制子进程使用 UTF-8
    env = copy.copy(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'

    all_output = []

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            env=env
        )

        for line in iter(process.stdout.readline, ''):
            line = line.rstrip('\n')
            if line:
                _log(line)
                all_output.append(line)

        process.stdout.close()
        process.wait()

        full_output = '\n'.join(all_output)

        if process.returncode == 0 and any('SUCCESS' in l for l in all_output):
            _log("\n[Agent] IDW engine finished successfully.")
            _log("=" * 55 + "\n")
            return True, full_output
        else:
            _log("\n[Agent] IDW engine reported an error.")
            _log("=" * 55 + "\n")
            return False, full_output

    except FileNotFoundError:
        msg = (f"[Agent] Script not found: {script_path}\n"
               f"Please make sure tool_idw_processor.py is in the same directory as agent_core.py.")
        _log(msg)
        return False, msg

    except Exception as e:
        msg = f"[Agent] Unexpected error: {e}"
        _log(msg)
        return False, msg


def run_raster_clip_agent(task_description, input_raster, mask_shp, output_raster,
                          log_callback=None):
    """
    栅格裁剪 Agent 核心调度函数。

    参数：
        task_description : 用户原始需求
        input_raster     : 输入栅格文件路径
        mask_shp         : 掩膜 .shp 文件路径
        output_raster    : 输出栅格文件路径
        log_callback     : 可选回调 f(line: str)，每行日志调用一次
    """

    def _log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    _log("=" * 55)
    _log("[Agent] Starting raster clipping...")
    _log(f"[Agent] Task         : {task_description}")
    _log(f"[Agent] Input raster : {input_raster}")
    _log(f"[Agent] Mask SHP     : {mask_shp}")
    _log(f"[Agent] Output       : {output_raster}")
    _log("=" * 55)
    _log("[Agent] Calling raster clipping engine...\n")

    python_exe  = sys.executable
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "tool_idw_processor.py")

    command = [
        python_exe,
        script_path,
        "--mode",           "clip_raster",
        "--input_raster",   input_raster,
        "--mask_shp",       mask_shp,
        "--output_raster",  output_raster,
    ]

    # 强制子进程使用 UTF-8
    env = copy.copy(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'

    all_output = []

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            env=env
        )

        for line in iter(process.stdout.readline, ''):
            line = line.rstrip('\n')
            if line:
                _log(line)
                all_output.append(line)

        process.stdout.close()
        process.wait()

        full_output = '\n'.join(all_output)

        if process.returncode == 0 and any('SUCCESS' in l for l in all_output):
            _log("\n[Agent] Raster clipping engine finished successfully.")
            _log("=" * 55 + "\n")
            return True, full_output
        else:
            _log("\n[Agent] Raster clipping engine reported an error.")
            _log("=" * 55 + "\n")
            return False, full_output

    except FileNotFoundError:
        msg = (f"[Agent] Script not found: {script_path}\n"
               f"Please make sure tool_idw_processor.py is in the same directory as agent_core.py.")
        _log(msg)
        return False, msg

    except Exception as e:
        msg = f"[Agent] Unexpected error: {e}"
        _log(msg)
        return False, msg


def run_contour_agent(task_description, input_raster, output_shp, interval=0.5,
                      log_callback=None):
    """
    等值线生成 Agent 核心调度函数。

    参数：
        task_description : 用户原始需求
        input_raster     : 输入栅格文件路径
        output_shp       : 输出等值线 .shp 文件路径
        interval         : 等值线间距（默认 0.5）
        log_callback     : 可选回调 f(line: str)，每行日志调用一次
    """

    def _log(msg):
        print(msg)
        if log_callback:
            log_callback(msg)

    _log("=" * 55)
    _log("[Agent] Starting contour generation...")
    _log(f"[Agent] Task         : {task_description}")
    _log(f"[Agent] Input raster : {input_raster}")
    _log(f"[Agent] Output SHP   : {output_shp}")
    _log(f"[Agent] Interval     : {interval}")
    _log("=" * 55)
    _log("[Agent] Calling contour engine...\n")

    python_exe  = sys.executable
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "tool_idw_processor.py")

    command = [
        python_exe,
        script_path,
        "--mode",         "contour",
        "--input_raster", input_raster,
        "--output_shp",   output_shp,
        "--interval",     str(interval),
    ]

    env = copy.copy(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'

    all_output = []

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            env=env
        )

        for line in iter(process.stdout.readline, ''):
            line = line.rstrip('\n')
            if line:
                _log(line)
                all_output.append(line)

        process.stdout.close()
        process.wait()

        full_output = '\n'.join(all_output)

        if process.returncode == 0 and any('SUCCESS' in l for l in all_output):
            _log("\n[Agent] Contour engine finished successfully.")
            _log("=" * 55 + "\n")
            return True, full_output
        else:
            _log("\n[Agent] Contour engine reported an error.")
            _log("=" * 55 + "\n")
            return False, full_output

    except FileNotFoundError:
        msg = (f"[Agent] Script not found: {script_path}\n"
               f"Please make sure tool_idw_processor.py is in the same directory as agent_core.py.")
        _log(msg)
        return False, msg

    except Exception as e:
        msg = f"[Agent] Unexpected error: {e}"
        _log(msg)
        return False, msg


# ──────────────────────────────────────────
# 本地测试入口
# ──────────────────────────────────────────
if __name__ == "__main__":
    user_prompt     = "Clip Wave_2.nc step 0 with MaskPolygon.shp"
    mock_input_nc   = r"D:\mygis\data\海浪SWAN模式数据\Wave_2.nc"
    mock_mask_shp   = r"D:\mygis\data\海浪SWAN模式数据\掩膜多边形\MaskPolygon.shp"
    mock_output_shp = r"D:\mygis\test_res\agent_test.shp"

    run_gis_agent(
        task_description=user_prompt,
        nc_file=mock_input_nc,
        mask_file=mock_mask_shp,
        output_file=mock_output_shp,
        time_step=0
    )