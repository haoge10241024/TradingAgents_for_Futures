# 期货持仓分析系统

基于Streamlit的期货持仓分析系统，支持多空力量变化策略和蜘蛛网策略分析。

## 功能特点

- 支持多个交易所的持仓数据分析
- 提供多空力量变化策略分析
- 提供蜘蛛网策略分析
- 可视化展示分析结果
- 支持移动端访问

## 安装说明

1. 克隆仓库：
```bash
git clone [仓库地址]
cd [仓库目录]
```

2. 创建虚拟环境：
```bash
python -m venv venv
```

3. 激活虚拟环境：
```bash
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

4. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 运行程序：
```bash
streamlit run app_streamlit.py
```

2. 在浏览器中访问：
- 本地访问：http://localhost:8501
- 局域网访问：http://[电脑IP]:8501

3. 使用步骤：
- 选择要分析的交易日期
- 点击"开始分析"按钮
- 查看不同策略的分析结果
- 可以通过标签页切换不同的分析策略

## 项目结构

```
.
├── app_streamlit.py          # Streamlit应用主文件
├── futures_position_analysis.py  # 核心分析逻辑
├── requirements.txt          # 项目依赖
├── data/                     # 数据存储目录
└── README.md                # 项目说明文档
```

## 注意事项

- 首次运行需要下载数据，可能较慢
- 确保网络连接正常
- 建议使用Chrome或Edge浏览器
- 数据文件会自动保存在data目录

## 依赖版本

- streamlit==1.32.2
- akshare==1.12.22
- pandas==2.2.1
- numpy==1.26.4
- plotly==5.19.0

## 许可证

MIT License 