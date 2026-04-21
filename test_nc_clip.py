import arcpy
import numpy as np
from netCDF4 import Dataset

input_nc = r"D:\mygis\data\海浪SWAN模式数据\Wave_2.nc"
mask_polygon = r"D:\mygis\data\海浪SWAN模式数据\掩膜多边形\MaskPolygon.shp"
output_points = r"D:\mygis\GeoAgent-Pro\result\clip_points.shp"
temp_points = r"D:\mygis\GeoAgent-Pro\result\temp_raw_points.shp"

print("正在启动降维打击方案，请稍候...")
arcpy.env.overwriteOutput = True

try:
    print("1. 读取 NetCDF 数据并强制降维...")
    nc = Dataset(input_nc)

    # 【修复1】：提取坐标并强制压平为一维数组 (flatten)
    x_coords = np.array(nc.variables['nodes_x'][:]).flatten()
    y_coords = np.array(nc.variables['nodes_y'][:]).flatten()

    # 提取波高原始数据
    hs_raw = nc.variables['Hs'][0, :]
    print(f"   -> 提取成功！一共扒出来 {len(x_coords)} 个数据节点。")

    print("2. 终极暴力清洗空值数据...")
    # 【修复2】：专门针对 netCDF 的 MaskedArray 清洗法，先填空值再转格式
    if hasattr(hs_raw, 'filled'):
        hs_raw = hs_raw.filled(-9999.0)

    # 强制压平并转换为标准的 64 位浮点数，扫除一切非数字障碍
    hs_data_clean = np.array(hs_raw, dtype=np.float64).flatten()
    hs_data_clean[np.isnan(hs_data_clean)] = -9999.0

    print("3. 将干干净净的数据组装成 GIS 矢量点...")
    array_type = np.dtype([('X', np.float64), ('Y', np.float64), ('Hs', np.float64)])
    struct_arr = np.empty(len(x_coords), dtype=array_type)
    struct_arr['X'] = x_coords
    struct_arr['Y'] = y_coords
    struct_arr['Hs'] = hs_data_clean

    sr = arcpy.SpatialReference(4326)  # WGS1984

    # 【修复3】：如果上一次执行留下了一半的坏文件，强行删掉防止 create table 报错
    if arcpy.Exists(temp_points):
        arcpy.management.Delete(temp_points)

    arcpy.da.NumPyArrayToFeatureClass(struct_arr, temp_points, ['X', 'Y'], sr)
    print("   -> 全海域散点构建完毕！")

    print("4. 正在执行掩膜裁剪...")
    if arcpy.Exists(output_points):
        arcpy.management.Delete(output_points)
    arcpy.analysis.Clip(temp_points, mask_polygon, output_points)

    print("=======================================")
    print("大功告成！物理通路已彻底打通！")
    print(f"最终裁剪后的文件已生成: {output_points}")
    print("=======================================")

except Exception as e:
    print(f"\n哎呀，又报错了：\n{e}")
finally:
    if 'nc' in locals():
        nc.close()