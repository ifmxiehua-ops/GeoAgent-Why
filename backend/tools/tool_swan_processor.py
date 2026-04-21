import arcpy
import numpy as np
from netCDF4 import Dataset
import argparse
import os

def process_swan_data(input_nc, mask_polygon, output_points):
    print("正在启动底层的海洋空间处理引擎...")
    arcpy.env.overwriteOutput = True 
    
    # 在输出路径同级目录建一个临时文件
    out_dir = os.path.dirname(output_points)
    temp_points = os.path.join(out_dir, "temp_raw_points.shp")

    try:
        print(f"1. 读取并拆解 NetCDF 数据: {input_nc} ...")
        nc = Dataset(input_nc)
        x_coords = np.array(nc.variables['nodes_x'][:]).flatten()
        y_coords = np.array(nc.variables['nodes_y'][:]).flatten()
        hs_raw = nc.variables['Hs'][0, :]
        
        print("2. 正在清洗 NaN 空值数据...")
        if hasattr(hs_raw, 'filled'):
            hs_raw = hs_raw.filled(-9999.0)
        hs_data_clean = np.array(hs_raw, dtype=np.float64).flatten()
        hs_data_clean[np.isnan(hs_data_clean)] = -9999.0

        print("3. 组装成 GIS 矢量点...")
        array_type = np.dtype([('X', np.float64), ('Y', np.float64), ('Hs', np.float64)])
        struct_arr = np.empty(len(x_coords), dtype=array_type)
        struct_arr['X'] = x_coords
        struct_arr['Y'] = y_coords
        struct_arr['Hs'] = hs_data_clean

        sr = arcpy.SpatialReference(4326) 
        if arcpy.Exists(temp_points):
            arcpy.management.Delete(temp_points)
        arcpy.da.NumPyArrayToFeatureClass(struct_arr, temp_points, ['X', 'Y'], sr)

        print(f"4. 正在使用 {mask_polygon} 进行掩膜裁剪...")
        if arcpy.Exists(output_points):
            arcpy.management.Delete(output_points)
        arcpy.analysis.Clip(temp_points, mask_polygon, output_points)
        
        # 成功后的标准输出（非常重要，Agent 靠识别这个单词来判断是否成功）
        print(f"SUCCESS: 结果已生成至 {output_points}")
        
    except Exception as e:
        # 失败后的标准输出
        print(f"ERROR: {e}")
    finally:
        if 'nc' in locals():
            nc.close()

if __name__ == "__main__":
    # 配置命令行参数解析
    parser = argparse.ArgumentParser(description="SWAN NetCDF 处理与裁剪工具")
    parser.add_argument("--input_nc", required=True, help="输入的 .nc 文件路径")
    parser.add_argument("--mask_shp", required=True, help="用于裁剪的 .shp 文件路径")
    parser.add_argument("--output_shp", required=True, help="输出的 .shp 结果路径")
    
    args = parser.parse_args()
    
    # 运行核心函数
    process_swan_data(args.input_nc, args.mask_shp, args.output_shp)