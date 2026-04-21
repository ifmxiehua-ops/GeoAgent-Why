import subprocess
import os



# 1. 配置你的 Gemini
# ... 后面保持不变 ...
def run_gis_agent(task_description, nc_file, mask_file, output_file):
    """
    这是智能体的核心调度函数。
    未来的大模型（LLM）在听懂用户的话之后，会自动调用这个函数，并把提取出来的路径填进来。
    """
    print("\n" + "="*50)
    print("🧠 [Agent 中枢] 开始工作...")
    print(f"🗣️ 用户需求: '{task_description}'")
    print("🧠 [Agent 中枢] 正在规划执行步骤...")
    print("🧠 [Agent 中枢] 决定跨环境调用底层 GIS 引擎: tool_swan_processor.py")
    
    # 组装我们要发送给终端的命令
    # 注意：这里的 "python" 会自动使用当前环境的 Python
    command = [
        "python", 
        "tool_swan_processor.py",
        "--input_nc", nc_file,
        "--mask_shp", mask_file,
        "--output_shp", output_file
    ]
    
    print("🚀 [Agent 中枢] 正在向下级环境发送物理指令，请稍候...")
    
    try:
        # subprocess.run 相当于让代码帮你悄悄打开一个隐形的终端，敲入上面的命令并回车
        # capture_output=True 意思是把底下脚本 print 的内容全部抓回来
        # 换成了系统默认的 gbk 编码，并且遇到生僻字直接忽略 (errors='ignore')，保证绝对不崩
        result = subprocess.run(command, capture_output=True, text=True, encoding='gbk', errors='ignore')
        
        # 检查底层工具是否执行成功 (returncode == 0 代表没有报错退出)
        if result.returncode == 0:
            print("\n✅ [Agent 中枢] 收到底层引擎的成功回执：")
            # 打印出底层工具 SUCCESS 的那句话
            print(result.stdout.strip())
            return True, result.stdout
        else:
            print("\n❌ [Agent 中枢] 底层引擎报告了错误：")
            print(result.stderr.strip() or result.stdout.strip())
            return False, result.stderr
            
    except Exception as e:
        print(f"\n❌ [Agent 中枢] 跨环境通讯失败：{e}")
        return False, str(e)
    
    print("="*50 + "\n")

if __name__ == "__main__":
    # ==========================================
    # 这里是模拟测试区：假装大模型已经做完了自然语言解析
    # ==========================================
    
    # 1. 模拟用户在网页上输入的自然语言
    user_prompt = "帮我用那个多边形文件，把 Wave_2.nc 里的海洋数据切出来，随便存个新名字吧。"
    
    # 2. 模拟大模型（如 GPT-4 / Gemini）聪明地从用户话语和上下文里提取出的绝对路径
    mock_input_nc = r"D:\mygis\data\海浪SWAN模式数据\Wave_2.nc"
    mock_mask_shp = r"D:\mygis\data\海浪SWAN模式数据\掩膜多边形\MaskPolygon.shp"
    mock_output_shp = r"D:\mygis\GeoAgent-Pro\result\agent_auto_test.shp"
    
    # 3. 大模型调用核心函数
    run_gis_agent(
        task_description=user_prompt, 
        nc_file=mock_input_nc, 
        mask_file=mock_mask_shp, 
        output_file=mock_output_shp
    )