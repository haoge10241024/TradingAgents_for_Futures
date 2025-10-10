from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import os
from futures_position_analysis import FuturesPositionAnalyzer
import threading
from pyngrok import ngrok

app = Flask(__name__)
CORS(app)

# 初始化分析器
data_dir = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(data_dir, exist_ok=True)
analyzer = FuturesPositionAnalyzer(data_dir)

def start_ngrok():
    """启动ngrok隧道"""
    try:
        # 启动ngrok，将本地5000端口映射到公网
        public_url = ngrok.connect(5000)
        print(f"\n=== 公网访问地址: {public_url} ===\n")
        return public_url
    except Exception as e:
        print(f"启动ngrok失败: {str(e)}")
        return None

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """分析接口"""
    try:
        data = request.get_json()
        trade_date = data.get('trade_date')
        
        if not trade_date or len(trade_date) != 8 or not trade_date.isdigit():
            return jsonify({
                'success': False,
                'message': '日期格式错误，请使用YYYYMMDD格式'
            })
        
        # 获取数据并分析
        results = analyzer.fetch_and_analyze(trade_date)
        
        if not results:
            return jsonify({
                'success': False,
                'message': '没有获取到任何分析结果'
            })
        
        # 处理分析结果
        analysis_results = {}
        for strategy in analyzer.strategies:
            strategy_name = strategy.name
            strategy_results = {
                'long_signals': [],
                'short_signals': []
            }
            
            for contract, data in results.items():
                strategy_data = data['strategies'][strategy_name]
                signal_data = {
                    'contract': contract,
                    'strength': strategy_data['strength'],
                    'reason': strategy_data['reason']
                }
                
                if strategy_data['signal'] == '看多':
                    strategy_results['long_signals'].append(signal_data)
                elif strategy_data['signal'] == '看空':
                    strategy_results['short_signals'].append(signal_data)
            
            # 按强度排序
            strategy_results['long_signals'].sort(key=lambda x: x['strength'], reverse=True)
            strategy_results['short_signals'].sort(key=lambda x: x['strength'], reverse=True)
            
            analysis_results[strategy_name] = strategy_results
        
        return jsonify({
            'success': True,
            'data': analysis_results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'分析过程中出错：{str(e)}'
        })

if __name__ == '__main__':
    # 启动ngrok
    public_url = start_ngrok()
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000, debug=True) 