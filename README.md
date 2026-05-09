🌍 GeoAgent-Pro：智能海洋空间处理 Agent 平台
GeoAgent-Pro 是一个面向海洋科学领域的智能空间分析平台。它通过大型语言模型（LLM）的函数调用（Function Calling）技术，打通了自然语言与硬核 GIS 引擎（ArcPy）之间的壁垒。用户无需编写代码或操作复杂的工具条，只需通过对话即可完成海量海洋数据的空间裁剪、IDW 插值、栅格裁剪与等值线生成。

🌟 核心特性

💬 语义化空间调度：Web 界面集成 DeepSeek（deepseek-chat），命令行界面集成 Gemini 2.5 Flash，精准理解"裁剪"、"插值"、"等值线"等空间操作意图。

⚙️ 跨环境执行中枢：独创的 agent_core 架构，完美解决了常规 Python Web 环境与 ArcGIS 专属 Python 环境（arcgispro-py3）的隔离问题。

🌊 海洋专业优化：针对海浪模型（如 SWAN）生成的 NetCDF（.nc）格式数据进行了深度适配，支持自动点阵化与矢量化，并支持任意坐标/字段变量名的参数化配置。

🔧 五大工具链：inspect_nc（文件探查）、clip_swan_data（NC 裁剪）、idw_interpolate（IDW 插值）、generate_contour（等值线生成）、clip_raster（栅格裁剪），覆盖海洋 GIS 核心工作流。

🔒 并发保护：Web 界面使用线程锁防止 ArcPy 引擎被并发调用，确保多用户场景下的稳定性。

📊 响应式 Web 交互：基于 Streamlit 打造的极简 UI，支持实时日志滚动、密钥加密输入、代理端口配置及默认参数预设。

🛠️ 技术架构

项目采用"大脑—中枢—手脚"三层设计方案，并提供 Web 与命令行两套入口：
```
┌─────────────────────────────────────────────────────┐
│               用户交互层（两套入口）                   │
│  app.py (Streamlit Web)  deepseek_agent.py (CLI)    │
│  LLM: DeepSeek           LLM: Gemini 2.5 Flash      │
└──────────────────┬───────────────────────────────────┘
                   │ Function Calling
┌──────────────────▼───────────────────────────────────┐
│            中枢调度层  agent_core.py                   │
│  run_gis_agent / run_idw_agent /                     │
│  run_raster_clip_agent / run_contour_agent           │
└──────────┬───────────────────────┬────────────────────┘
           │ subprocess             │ subprocess
┌──────────▼──────────┐  ┌─────────▼──────────────────┐
│ tool_swan_processor │  │   tool_idw_processor.py    │
│      .py            │  │  IDW 插值 / 栅格裁剪 /      │
│  NC → 矢量点 →      │  │  等值线生成                 │
│  掩膜裁剪 → SHP     │  └────────────────────────────┘
└─────────────────────┘
         ↓ 两者均依赖 ArcPy（arcgispro-py3 环境）
```

📦 文件结构
```
GeoAgent-Pro/
├── app.py                  # Streamlit Web 前端（DeepSeek 驱动）
├── deepseek_agent.py       # 命令行版 Agent（Gemini 驱动）
├── agent_core.py           # 跨环境调度中枢
├── tool_swan_processor.py  # GIS 执行引擎：NetCDF → SHP
├── tool_idw_processor.py   # GIS 执行引擎：IDW / 裁剪 / 等值线
├── check_nc.py             # 辅助工具：查看 NC 文件结构
├── check_models.py         # 辅助工具：查看可用 Gemini 模型
└── result/                 # 默认输出目录
```

📥 安装与快速启动

1. 环境准备

由于本项目深度依赖 ArcGIS 空间分析能力，必须在安装了 ArcGIS Pro 的机器上运行。

打开 Python Command Prompt (ArcGIS Pro)，导航至项目目录：
```
#替换成你电脑上的真实路径
cd /d D:\mygis\GeoAgent-Pro
```

2. 安装依赖库
```
pip install streamlit openai netCDF4 numpy
```

3.启动 Web 界面
```
streamlit run app.py
```

🚀 成果演示 (Showcase)

海洋数据自动化处理示例

本项目成功实现了对海浪模型（SWAN）输出数据的自动化空间分析。以下是使用 Agent 处理中国近海海浪数据的实际案例：
输入指令：

1.读取 D:\mygis\data\海浪SWAN模式数据\Wave_2.nc，使用 MaskPolygon.shp 进行空间裁剪，提取有效波高 Hs，结果保存到 D:\mygis\test_res。
2.对 D:\mygis\GeoAgent-Pro\result\ai_output_step000.shp 做 IDW 插值，字段名 Hs，用掩膜 D:\mygis\data\海浪SWAN模式数据\掩膜多边形\MaskPolygon.shp 裁剪，结果保存为 D:\mygis\GeoAgent-Pro\result\Hs_idw.tif
3.对 D:\mygis\GeoAgent-Pro\result\Hs_idw_masked_clipped.tif 提取等值线，间距 0.5，结果保存为 D:\mygis\GeoAgent-Pro\result\Hs_contour.shp

<img width="1437" height="870" alt="展示1" src="https://github.com/user-attachments/assets/582b660b-a923-4220-a5db-ebf8c76afd84" />
<img width="1410" height="777" alt="效果四" src="https://github.com/user-attachments/assets/6181051b-df97-4b39-9af5-af556d3175e0" />
