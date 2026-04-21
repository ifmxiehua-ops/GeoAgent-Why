🌍 GeoAgent-Pro: 智能海洋空间处理 Agent 平台
GeoAgent-Pro 是一个面向海洋科学领域的智能空间分析平台。它通过大型语言模型（LLM）的函数调用（Function Calling）
技术，打通了自然语言与硬核 GIS 引擎（ArcPy）之间的壁垒。用户无需编写代码或操作复杂的工具条，只需通过对话即可完成海量海洋数据的空间裁剪、转换与分析。
🌟 核心特性
💬 语义化空间调度：深度集成 Gemini 2.5 Flash，精准理解“裁剪”、“提取”、“过滤”等空间操作意图。

⚙️ 跨环境执行中枢：独创的 agent_core 架构，完美解决了常规 Python Web 环境与 ArcGIS 专属 Python 环境（arcgispro-py3）的隔离问题。

🌊 海洋专业优化：针对海浪模型（如 SWAN）生成的 NetCDF (.nc) 格式数据进行了深度适配，支持自动点阵化与矢量化。

📊 响应式 Web 交互：基于 Streamlit 打造的极简 UI，支持实时日志滚动、密钥加密配置及处理结果反馈。
🛠️ 技术架构
项目采用了典型的“大脑-中枢-手脚”三层设计方案：
大脑 (Agent Interface)：基于 app.py，负责接收指令并利用 LLM 进行参数提取。

中枢 (Bridge Engine)：agent_core.py 负责逻辑封装与跨进程信号传递，确保指令安全触达底层。

手脚 (GIS Execution)：tool_swan_processor.py 直接调用 ArcGIS Pro 内置的 ArcPy 库，进行物理层面的空间运算。
📥 安装与快速启动
1. 环境准备
由于本项目深度依赖 ArcGIS 空间分析能力，必须在安装了 ArcGIS Pro 的机器上运行。
打开 Python Command Prompt (ArcGIS Pro)。
导航至项目目录：
cd /d D:\mygis\GeoAgent-Pro
2. 安装依赖库
pip install streamlit google-generativeai
3. 配置与启动
streamlit run app.py
4. 填写 API Key
在启动后的网页左侧边栏，输入您的 Gemini API Key（支持加密输入）。
💡 使用示例
您可以在对话框中尝试以下指令：

初级指令：
“帮我分析一下 D:\data\temp.nc 里的数据。”

进阶指令（自动提取路径）：
“把 D:\mygis\data\Wave_2.nc 这个海浪数据切了，裁剪范围参考 D:\mygis\data\mask.shp 这个多边形。”
📂 项目结构
GeoAgent-Pro/
├── app.py                  # Web 交互与 Agent 逻辑入口
├── agent_core.py           # 跨环境调度与桥接模块
├── tool_swan_processor.py   # 底层物理执行逻辑 (ArcPy 核心)
├── .gitignore              # 忽略大型 nc/shp 原始数据
└── README.md               # 本文档
👤 关于作者
本项目由 王浩宇 开发。作者目前就读于 同济大学海洋与地球科学学院。

研究方向：海洋 GIS 集成系统、面向具身智能的数据传输

技术栈：Python, C++, GIS Analysis, AI Algorithm

如何使用此模板？
1.在你的 GeoAgent-Pro 文件夹里，找到 README.md。

2.用记事本或 PyCharm 打开它，把上面的内容全部复制进去。

3.保存文件。

4.在终端里执行：
git add README.md
git commit -m "Update professional README"
git push




