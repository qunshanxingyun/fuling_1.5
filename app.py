from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from config import config
import os
from datetime import datetime
os.environ["MKL_THREADING_LAYER"] = "GNU"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
def create_app(config_name=None):
    """应用工厂函数"""
    app = Flask(__name__)
    
    # 加载配置
    config_name = config_name or os.getenv('FLASK_ENV', 'default')
    app.config.from_object(config[config_name])
    
    # 启用CORS
    CORS(app)
    
    # 设置JSON编码
    app.config['JSON_AS_ASCII'] = False
    app.config['JSONIFY_MIMETYPE'] = "application/json; charset=utf-8"
    
    # 注册自定义Jinja2过滤器
    register_filters(app)
    
    # 注册全局模板变量
    register_template_globals(app)
    
    # 注册API蓝图
    from api.compounds import compounds_bp
    from api.targets import targets_bp
    from api.prediction import prediction_bp
    app.register_blueprint(compounds_bp, url_prefix='/api')
    app.register_blueprint(targets_bp, url_prefix='/api')
    app.register_blueprint(prediction_bp)
    # 注册页面路由蓝图
    from views.pages import pages_bp
    from views.compounds import compounds_view_bp
    from views.targets import targets_view_bp
    from views.prediction import prediction_views
    app.register_blueprint(pages_bp)
    app.register_blueprint(compounds_view_bp)
    app.register_blueprint(targets_view_bp)
    app.register_blueprint(prediction_views)
    # API根路由
    @app.route('/api')
    def api_index():
        return jsonify({
            'name': 'Poria Cocos Target Prediction Database API',
            'version': '2.0',
            'description': 'RESTful API for accessing Poria cocos compound and target data',
            'endpoints': {
                'compounds': {
                    'list': 'GET /api/compounds',
                    'detail': 'GET /api/compounds/<id>',
                    'search': 'POST /api/compounds/search',
                    'statistics': 'GET /api/compounds/statistics',
                    'targets': 'GET /api/compounds/<id>/targets'
                },
                'targets': {
                    'list': 'GET /api/targets',
                    'detail': 'GET /api/targets/<gene_name>',
                    'compounds': 'GET /api/targets/<gene_name>/compounds',
                    'search': 'POST /api/targets/search',
                    'statistics': 'GET /api/targets/statistics'
                }
            }
        })
    
    # 健康检查端点
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '2.0',
            'database': 'operational'
        })
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'status': 'error',
                'message': 'Resource not found',
                'error_code': 404
            }), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'status': 'error',
                'message': 'Internal server error',
                'error_code': 500
            }), 500
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'status': 'error',
            'message': 'Bad request',
            'error_code': 400
        }), 400
    
    return app

def register_filters(app):
    """注册自定义Jinja2过滤器"""
    
    @app.template_filter('strftime')
    def strftime_filter(date, format_string='%Y-%m-%d'):
        """格式化日期时间"""
        if date == 'now':
            date = datetime.now()
        elif isinstance(date, str):
            try:
                date = datetime.fromisoformat(date)
            except:
                return date
        
        if hasattr(date, 'strftime'):
            return date.strftime(format_string)
        return str(date)

def register_template_globals(app):
    """注册全局模板变量"""
    
    @app.template_global()
    def current_year():
        """获取当前年份"""
        return datetime.now().year
    
    @app.template_global()
    def current_date(format_string='%Y-%m-%d'):
        """获取当前日期"""
        return datetime.now().strftime(format_string)
    
    @app.template_global()
    def current_month_year():
        """获取当前月份和年份"""
        return datetime.now().strftime('%B %Y')
    
    @app.template_global()
    def app_version():
        """获取应用版本"""
        return '2.0'

if __name__ == '__main__':
    app = create_app()
    """
    本地网络进行开发时，采用下面的命令
    """
    # app.run(debug=True, port=8980)
    """
    需要开放外部访问（服务器地址访问）时，采用下面的命令；初次使用需要：
    永久开放 8980 端口 (TCP协议)：
    sudo firewall-cmd --zone=public --add-port=8980/tcp --permanent

    --zone=public：表示在公共区域应用此规则。
    --add-port=8980/tcp：表示添加 TCP 协议的 8980 端口。
    --permanent：表示将这个规则永久保存，即使重启服务器也不会失效。

    重新加载防火墙规则使其生效：
    sudo firewall-cmd --reload

    这条命令会使刚才添加的永久规则立即生效。
    (可选) 确认端口是否已经开放：

    sudo firewall-cmd --zone=public --list-ports
    """
    app.run(host='0.0.0.0', debug=True, port=8980)