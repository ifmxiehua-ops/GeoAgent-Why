import arcpy

nc_file = r"D:\mygis\data\海浪SWAN模式数据\Wave_2.nc"
nc_fp = arcpy.NetCDFFileProperties(nc_file)

print("这个 NC 文件里的【物理量变量】有：")
print(nc_fp.getVariables())
print("\n这个 NC 文件里的【坐标维度】有：")
print(nc_fp.getDimensions())