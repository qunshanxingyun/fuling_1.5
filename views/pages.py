from flask import Blueprint, render_template, jsonify, request
from services.compound_service import CompoundService
from services.target_service import TargetService

pages_bp = Blueprint('pages', __name__)

# 实例化服务
compound_service = CompoundService()
target_service = TargetService()

@pages_bp.route('/')
def index():
    """首页"""
    try:
        # 获取统计数据
        compound_stats = compound_service.get_statistics()
        target_stats = target_service.get_target_statistics()
        
        # 合并统计数据
        stats = {
            'compounds': compound_stats,
            'targets': target_stats
        }
        
        return render_template('pages/index.html', stats=stats)
    except Exception as e:
        # 如果获取统计数据失败，使用默认值
        default_stats = {
            'compounds': {'total': 0, 'by_type': {}},
            'targets': {'total_targets': 0}
        }
        return render_template('pages/index.html', stats=default_stats)

@pages_bp.route('/search')
def search_page():
    """全局搜索页面"""
    return render_template('pages/search.html')

@pages_bp.route('/help')
def help_page():
    """帮助文档页面"""
    return render_template('pages/help.html')

@pages_bp.route('/about')
def about_page():
    """关于页面"""
    return render_template('pages/about.html')

@pages_bp.route('/statistics')
def statistics_page():
    """统计分析页面"""
    try:
        # 获取详细统计数据
        compound_stats = compound_service.get_statistics()
        target_stats = target_service.get_target_statistics()
        
        # 合并统计数据
        stats = {
            'compounds': compound_stats,
            'targets': target_stats
        }
        # 转换numpy类型为Python原生类型（新增这部分）
        def convert_numpy_types(obj):
            if isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            elif hasattr(obj, 'item'):  # numpy类型
                return obj.item()
            else:
                return obj
        # 应用转换
        compound_stats = convert_numpy_types(compound_stats)
        target_stats = convert_numpy_types(target_stats)
        
        # 合并统计数据
        stats = {
            'compounds': compound_stats,
            'targets': target_stats
        }
        
        return render_template('pages/statistics.html', stats=stats)
    except Exception as e:
        # 如果获取统计数据失败，使用默认值
        default_stats = {
            'compounds': {'total': 0, 'by_type': {}},
            'targets': {'total_targets': 0}
        }
        return render_template('pages/statistics.html', stats=default_stats, error=str(e))
    
@pages_bp.route('/predict')
def predict_page():
    """预测页面"""
    return render_template('pages/predict.html')

@pages_bp.route('/predict/results/<job_id>')
def prediction_results(job_id):
    """预测结果页面"""
    return render_template('pages/prediction_results.html', job_id=job_id)