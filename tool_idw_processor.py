"""
tool_idw_processor.py
IDW 栅格插值引擎：散点 SHP -> IDW 插值 -> 输出栅格
"""

import arcpy
import argparse
import os


def run_idw(input_shp, field_name, output_raster, cell_size=0.01, power=2):
    """
    使用 IDW (Inverse Distance Weighting) 方法对散点数据进行插值。
    
    参数：
        input_shp     : 输入散点 .shp 文件路径
        field_name    : 用于插值的字段名
        output_raster : 输出栅格文件路径（.tif）
        cell_size     : 栅格单元大小（默认 0.01）
        power         : IDW 幂次参数（默认 2）
    """
    print("=" * 60)
    print("IDW Raster Interpolation Engine Starting")
    print(f"   input_shp     : {input_shp}")
    print(f"   field_name    : {field_name}")
    print(f"   output_raster : {output_raster}")
    print(f"   cell_size     : {cell_size}")
    print(f"   power         : {power}")
    print("=" * 60)

    arcpy.env.overwriteOutput = True
    
    out_dir = os.path.dirname(output_raster)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)
        print(f"[INFO] Created output directory: {out_dir}")

    try:
        arcpy.env.workspace = out_dir
        
        print("\n[Step 1] Validating input shapefile...")
        if not arcpy.Exists(input_shp):
            raise FileNotFoundError(f"Input shapefile not found: {input_shp}")
        
        # 检查字段是否存在
        fields = [f.name for f in arcpy.ListFields(input_shp)]
        if field_name not in fields:
            raise ValueError(f"Field '{field_name}' not found in shapefile. Available fields: {fields}")
        
        print(f"   Input shapefile validated")
        print(f"   Field '{field_name}' found")

        print("\n[Step 2] Checking Spatial Analyst license...")
        if arcpy.CheckExtension("Spatial") == "Available":
            arcpy.CheckOutExtension("Spatial")
            print(f"   Spatial Analyst license checked out")
        else:
            raise Exception("Spatial Analyst license is not available")

        print("\n[Step 3] Performing IDW interpolation...")

        # 执行 IDW 插值
        out_raster = arcpy.sa.Idw(
            input_shp,
            field_name,
            cell_size,
            power
        )

        print(f"   IDW calculation completed")

        print("\n[Step 4] Saving output raster...")

        # 保存输出栅格
        out_raster.save(output_raster)

        print(f"   Raster saved to: {output_raster}")
        print(f"\nSUCCESS: IDW interpolation completed -> {output_raster}")

        # 归还许可
        arcpy.CheckInExtension("Spatial")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("=" * 60)


def run_raster_clip(input_raster, mask_shp, output_raster):
    """
    使用掩膜对栅格进行裁剪 (ExtractByMask)。
    
    参数：
        input_raster : 输入栅格文件路径
        mask_shp     : 掩膜 .shp 文件路径
        output_raster : 输出栅格文件路径
    """
    print("=" * 60)
    print("Raster Clipping Engine Starting")
    print(f"   input_raster  : {input_raster}")
    print(f"   mask_shp      : {mask_shp}")
    print(f"   output_raster : {output_raster}")
    print("=" * 60)

    arcpy.env.overwriteOutput = True
    
    out_dir = os.path.dirname(output_raster)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)
        print(f"[INFO] Created output directory: {out_dir}")

    try:
        arcpy.env.workspace = out_dir
        
        print("\n[Step 1] Validating input files...")
        if not arcpy.Exists(input_raster):
            raise FileNotFoundError(f"Input raster not found: {input_raster}")
        if not arcpy.Exists(mask_shp):
            raise FileNotFoundError(f"Mask shapefile not found: {mask_shp}")
        
        print(f"   Input raster validated")
        print(f"   Mask shapefile validated")
        
        print("\n[Step 2] Checking Spatial Analyst license...")
        if arcpy.CheckExtension("Spatial") == "Available":
            arcpy.CheckOutExtension("Spatial")
            print(f"   Spatial Analyst license checked out")
        else:
            raise Exception("Spatial Analyst license is not available")
        
        print("\n[Step 3] Performing raster clipping...")
        
        # 执行掩膜提取
        clipped_raster = arcpy.sa.ExtractByMask(input_raster, mask_shp)
        
        print(f"   Clipping completed")
        
        print("\n[Step 4] Saving output raster...")
        
        # 保存输出栅格
        clipped_raster.save(output_raster)
        
        print(f"   Raster saved to: {output_raster}")
        print(f"\nSUCCESS: Raster clipping completed -> {output_raster}")
        
        # 归还许可
        arcpy.CheckInExtension("Spatial")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("=" * 60)


def run_contour(input_raster, output_shp, interval=0.5):
    """
    从栅格生成等值线。

    参数：
        input_raster : 输入栅格文件路径
        output_shp   : 输出等值线 .shp 文件路径
        interval     : 等值线间距（默认 0.5）
    """
    print("=" * 60)
    print("Contour Generation Engine Starting")
    print(f"   input_raster : {input_raster}")
    print(f"   output_shp   : {output_shp}")
    print(f"   interval     : {interval}")
    print("=" * 60)

    arcpy.env.overwriteOutput = True

    out_dir = os.path.dirname(output_shp)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)
        print(f"[INFO] Created output directory: {out_dir}")

    try:
        arcpy.env.workspace = out_dir

        print("\n[Step 1] Validating input raster...")
        if not arcpy.Exists(input_raster):
            raise FileNotFoundError(f"Input raster not found: {input_raster}")
        print(f"   Input raster validated")

        print("\n[Step 2] Checking Spatial Analyst license...")
        if arcpy.CheckExtension("Spatial") == "Available":
            arcpy.CheckOutExtension("Spatial")
            print(f"   Spatial Analyst license checked out")
        else:
            raise Exception("Spatial Analyst license is not available")

        print("\n[Step 3] Generating contours...")
        arcpy.sa.Contour(input_raster, output_shp, interval)
        print(f"   Contour generation completed")

        print(f"\nSUCCESS: Contour generation completed -> {output_shp}")

        # 归还许可
        arcpy.CheckInExtension("Spatial")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Raster Processing Tools (IDW Interpolation, Raster Clipping, or Contour)")
    parser.add_argument("--mode", default="idw", choices=["idw", "clip_raster", "contour"],
                        help="Processing mode: 'idw' (default), 'clip_raster', or 'contour'")
    
    # IDW 模式参数
    parser.add_argument("--input_shp",      help="[IDW mode] Input point .shp file path")
    parser.add_argument("--field_name",     help="[IDW mode] Field name for interpolation")
    parser.add_argument("--cell_size",      type=float, default=0.01,
                        help="[IDW mode] Cell size for output raster (default: 0.01)")
    parser.add_argument("--power",          type=float, default=2,
                        help="[IDW mode] Power parameter for IDW (default: 2)")
    
    # 共用参数
    parser.add_argument("--output_raster",  help="Output raster file path (.tif)")
    
    # 栅格裁剪模式参数
    parser.add_argument("--input_raster",   help="[Clip/Contour mode] Input raster file path")
    parser.add_argument("--mask_shp",       help="[Clip mode] Mask .shp file path")

    # 等值线模式参数
    parser.add_argument("--output_shp",     help="[Contour mode] Output contour .shp file path")
    parser.add_argument("--interval",       type=float, default=0.5,
                        help="[Contour mode] Contour interval (default: 0.5)")

    args = parser.parse_args()

    if args.mode == "idw":
        if not args.input_shp or not args.field_name or not args.output_raster:
            parser.error("IDW mode requires: --input_shp, --field_name, --output_raster")

        run_idw(
            input_shp=args.input_shp,
            field_name=args.field_name,
            output_raster=args.output_raster,
            cell_size=args.cell_size,
            power=args.power
        )

    elif args.mode == "clip_raster":
        if not args.input_raster or not args.mask_shp or not args.output_raster:
            parser.error("clip_raster mode requires: --input_raster, --mask_shp, --output_raster")

        run_raster_clip(
            input_raster=args.input_raster,
            mask_shp=args.mask_shp,
            output_raster=args.output_raster
        )

    elif args.mode == "contour":
        if not args.input_raster or not args.output_shp:
            parser.error("contour mode requires: --input_raster, --output_shp")

        run_contour(
            input_raster=args.input_raster,
            output_shp=args.output_shp,
            interval=args.interval
        )
