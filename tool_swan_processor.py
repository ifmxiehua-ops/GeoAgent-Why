"""
tool_swan_processor.py
底层 GIS 处理引擎：读取任意 NetCDF -> 矢量点 -> 掩膜裁剪
支持参数化的坐标变量、数据字段、时间变量
"""

import arcpy
import numpy as np
from netCDF4 import Dataset
import argparse
import os
import json


def decode_time(time_str_var, idx):
    """将 NC 里的字符数组时间转成可读字符串"""
    try:
        return ''.join([c.decode('utf-8') for c in time_str_var[idx]]).strip()
    except Exception:
        return f"step_{idx:04d}"


def inspect_nc(nc_path: str) -> dict:
    """
    探查 NC 文件结构，返回所有变量信息。
    
    返回：{
        "variables": {
            "var_name": {"shape": (...), "dtype": "...", "dimensions": [...]},
            ...
        },
        "dimensions": {"dim_name": size, ...}
    }
    """
    try:
        nc = Dataset(nc_path)
        info = {
            "variables": {},
            "dimensions": dict(nc.dimensions)
        }
        
        for var_name in nc.variables:
            var = nc.variables[var_name]
            info["variables"][var_name] = {
                "shape": var.shape,
                "dtype": str(var.dtype),
                "dimensions": list(var.dimensions)
            }
        
        nc.close()
        return info
    except Exception as e:
        return {"error": str(e)}


def clean_nan(arr, fill=-9999.0):
    """
    彻底清洗 NaN：
      - 如果是 MaskedArray，先 filled()
      - 再用 np.isnan 替换残余 NaN
    """
    if hasattr(arr, 'filled'):
        arr = arr.filled(fill)
    arr = np.array(arr, dtype=np.float64).flatten()
    arr[np.isnan(arr)] = fill
    return arr


def process_single_step(nc, x_coords, y_coords, step_idx, mask_polygon,
                        output_path, sr, time_label, var_fields, var_time):
    """
    处理单个时间步，生成一个裁剪后的 shp 文件。
    
    参数：
        nc           : NetCDF Dataset 对象
        x_coords     : X 坐标数组
        y_coords     : Y 坐标数组
        step_idx     : 当前时间步索引
        mask_polygon : 掩膜 .shp 路径
        output_path  : 输出 .shp 路径
        sr           : 空间参考
        time_label   : 时间标签字符串
        var_fields   : 要提取的变量名列表 (e.g. ["Hs", "Dir", "Per"])
        var_time     : 时间变量名 (可选，为空则不写TIME字段)
    """
    out_dir   = os.path.dirname(output_path)
    temp_path = os.path.join(out_dir, "_temp_raw.shp")

    # 动态读取指定的数据变量
    data_dict = {}
    stats_lines = []
    
    for field_name in var_fields:
        try:
            raw_data = clean_nan(nc.variables[field_name][step_idx, :])
            data_dict[field_name] = raw_data
            
            valid_data = raw_data[raw_data != -9999.0]
            if len(valid_data) > 0:
                stats_lines.append(
                    f"   {field_name:8s}: {valid_data.min():.3f} ~ {valid_data.max():.3f}"
                )
            else:
                stats_lines.append(f"   {field_name:8s}: (no valid data)")
        except KeyError:
            print(f"   ⚠️  Warning: variable '{field_name}' not found in NC file, skipping")
            data_dict[field_name] = np.full_like(x_coords, -9999.0, dtype=np.float64)
    
    valid_count = int(np.sum(data_dict[var_fields[0]] != -9999.0)) if var_fields else 0
    print(f"   [step {step_idx:03d}] {time_label} | valid nodes: {valid_count}/{len(x_coords)}")
    for line in stats_lines:
        print(line)

    # 构建 NumPy 结构化数组的 dtype
    dtype_list = [
        ('X', np.float64),
        ('Y', np.float64),
    ]
    for field_name in var_fields:
        dtype_list.append((field_name, np.float64))
    
    dtype = np.dtype(dtype_list)
    arr = np.empty(len(x_coords), dtype=dtype)
    arr['X'] = x_coords
    arr['Y'] = y_coords

    for field_name in var_fields:
        arr[field_name] = data_dict[field_name]

    # 剔除陆地无效点（第一个数据变量为 -9999.0 的行），避免 IDW 插值时极端值导致 ArcPy 崩溃
    valid_mask = arr[var_fields[0]] != -9999.0
    arr = arr[valid_mask]
    print(f"   [filter] {int(valid_mask.sum())}/{len(valid_mask)} valid points after removing -9999 nodes")

    # 生成临时 shp，然后裁剪
    if arcpy.Exists(temp_path):
        arcpy.management.Delete(temp_path)
    arcpy.da.NumPyArrayToFeatureClass(arr, temp_path, ['X', 'Y'], sr)

    if arcpy.Exists(output_path):
        arcpy.management.Delete(output_path)
    arcpy.analysis.Clip(temp_path, mask_polygon, output_path)

    if arcpy.Exists(temp_path):
        arcpy.management.Delete(temp_path)

    # 如果指定了时间变量名，添加 TIME 字段
    if var_time:
        arcpy.management.AddField(output_path, var_time, "TEXT", field_length=25)
        with arcpy.da.UpdateCursor(output_path, [var_time]) as cursor:
            for row in cursor:
                row[0] = time_label
                cursor.updateRow(row)

    count = int(arcpy.management.GetCount(output_path)[0])
    print(f"   => clip done, {count} nodes saved -> {output_path}")
    return count


def process_swan_data(input_nc, mask_polygon, output_path, time_step,
                      var_x="nodes_x", var_y="nodes_y", var_fields=None, var_time=""):
    """
    处理 NetCDF 数据的完整工作流。
    
    参数：
        input_nc   : 输入 .nc 文件路径
        mask_polygon : 掩膜 .shp 文件路径
        output_path  : 输出 .shp 文件路径
        time_step    : 时间步索引（整数）或 "all"
        var_x        : X 坐标变量名（默认 "nodes_x"）
        var_y        : Y 坐标变量名（默认 "nodes_y"）
        var_fields   : 要提取的数据变量列表（默认 ["Hs", "Dir", "Per"]）
        var_time     : 时间变量名（可选，默认 ""）
    """
    if var_fields is None:
        var_fields = ["Hs", "Dir", "Per"]
    
    print("=" * 60)
    print("GIS Engine Starting (Generic NetCDF Processor)")
    print(f"   input_nc   : {input_nc}")
    print(f"   mask_shp   : {mask_polygon}")
    print(f"   output_shp : {output_path}")
    print(f"   time_step  : {'all' if time_step == 'all' else time_step}")
    print(f"   var_x      : {var_x}")
    print(f"   var_y      : {var_y}")
    print(f"   var_fields : {', '.join(var_fields)}")
    print(f"   var_time   : {var_time if var_time else '(none)'}")
    print("=" * 60)

    arcpy.env.overwriteOutput = True

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)
        print(f"[INFO] Created output directory: {out_dir}")

    try:
        print("\n[Step 1] Reading NetCDF coordinates...")
        nc = Dataset(input_nc)

        x_coords     = np.array(nc.variables[var_x][:]).flatten().astype(np.float64)
        y_coords     = np.array(nc.variables[var_y][:]).flatten().astype(np.float64)
        total_nodes  = len(x_coords)
        total_steps  = nc.variables[var_fields[0]].shape[0]  # 从第一个数据变量获取时间步数
        
        time_str_var = None
        if var_time and var_time in nc.variables:
            time_str_var = nc.variables[var_time]

        print(f"   nodes      : {total_nodes}")
        print(f"   time steps : {total_steps}")
        print(f"   lon range  : {x_coords.min():.2f} ~ {x_coords.max():.2f} deg")
        print(f"   lat range  : {y_coords.min():.2f} ~ {y_coords.max():.2f} deg")

        sr = arcpy.SpatialReference(4326)

        print("\n[Step 2] Clipping and extracting attributes...")

        if time_step != 'all':
            idx = int(time_step)
            if idx >= total_steps:
                raise ValueError(f"time_step={idx} out of range (total {total_steps})")
            time_label = decode_time(time_str_var, idx) if time_str_var else f"step_{idx:04d}"
            process_single_step(nc, x_coords, y_coords, idx,
                                 mask_polygon, output_path, sr, time_label, var_fields, var_time)
            print(f"\nSUCCESS: result -> {output_path}")

        else:
            base, ext = os.path.splitext(output_path)
            for idx in range(total_steps):
                time_label = decode_time(time_str_var, idx) if time_str_var else f"step_{idx:04d}"
                safe_time  = time_label.replace('-', '').replace(' ', '_').replace(':', '')
                step_path  = f"{base}_{idx:03d}_{safe_time}{ext}"
                process_single_step(nc, x_coords, y_coords, idx,
                                     mask_polygon, step_path, sr, time_label, var_fields, var_time)

            print(f"\nSUCCESS: all {total_steps} steps done")
            print(f"   output dir: {out_dir}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'nc' in locals():
            nc.close()
        print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generic NetCDF to Point SHP processing tool")
    parser.add_argument("--input_nc",   required=True,  help="Input .nc file path")
    parser.add_argument("--mask_shp",   required=True,  help="Mask .shp file path")
    parser.add_argument("--output_shp", required=True,  help="Output .shp file path")
    parser.add_argument("--time_step",  default="0",
                        help="Time step index (int), or 'all' for all steps. Default: 0")
    parser.add_argument("--var_x",      default="nodes_x",
                        help="X coordinate variable name (default: nodes_x)")
    parser.add_argument("--var_y",      default="nodes_y",
                        help="Y coordinate variable name (default: nodes_y)")
    parser.add_argument("--var_fields", default="Hs,Dir,Per",
                        help="Comma-separated data variable names (default: Hs,Dir,Per)")
    parser.add_argument("--var_time",   default="",
                        help="Time variable name for TIME field (optional, default: none)")
    args = parser.parse_args()

    ts = args.time_step if args.time_step.lower() == 'all' else int(args.time_step)
    var_fields = [v.strip() for v in args.var_fields.split(',')]
    
    process_swan_data(
        input_nc=args.input_nc,
        mask_polygon=args.mask_shp,
        output_path=args.output_shp,
        time_step=ts,
        var_x=args.var_x,
        var_y=args.var_y,
        var_fields=var_fields,
        var_time=args.var_time.strip() if args.var_time else ""
    )