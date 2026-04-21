# -*- coding: utf-8 -*-
import arcpy
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Clip raster using a mask polygon.")
    parser.add_argument("--input_raster", required=True, help="Input raster file")
    parser.add_argument("--mask_polygon", required=True, help="Mask polygon file")
    parser.add_argument("--output_raster", required=True, help="Output path for the clipped raster")

    args = parser.parse_args()

    # 允许覆盖输出
    arcpy.env.overwriteOutput = True

    try:
        # 检查并获取空间分析许可
        if arcpy.CheckExtension("Spatial") == "Available":
            arcpy.CheckOutExtension("Spatial")
        else:
            raise Exception("Spatial Analyst 许可不可用。")
            
        # 执行按掩膜提取 (Extract by Mask)
        out_extract_by_mask = arcpy.sa.ExtractByMask(args.input_raster, args.mask_polygon)
        
        # 保存输出结果
        out_extract_by_mask.save(args.output_raster)
        
        # 归还许可
        arcpy.CheckInExtension("Spatial")
        
        # 主程序将读取这行输出以判断是否成功
        print(f"SUCCESS: Raster clipped successfully. Saved to {args.output_raster}")
        
    except Exception as e:
        # 主程序将读取这行输出以获取错误信息
        print(f"ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
