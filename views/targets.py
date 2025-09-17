from flask import Blueprint, render_template, request, abort
from services.target_service import TargetService
from services.compound_service import CompoundService

targets_view_bp = Blueprint('targets_view', __name__, url_prefix='/targets')

# 实例化服务
target_service = TargetService()
compound_service = CompoundService()

@targets_view_bp.route('/')
def targets_list():
    """靶点列表页面"""
    # 获取查询参数
    # gene_family = request.args.get('family', 'all')
    search = request.args.get('search', '')
    
    try:
        # 获取统计信息用于页面展示
        stats = target_service.get_target_statistics()
        
        return render_template('targets/list.html', 
                            #  gene_family=gene_family,
                             search=search,
                             stats=stats)
    except Exception as e:
        return render_template('targets/list.html', 
                             error=str(e),
                            #  gene_family=gene_family,
                             search=search)

@targets_view_bp.route('/<gene_name>')
def target_detail(gene_name):
    """靶点详情页面"""
    try:
        # 获取靶点基本信息
        target = target_service.get_target_detail(gene_name)
        if not target:
            abort(404)
        
        return render_template('targets/detail.html',
                             target=target)
    except Exception as e:
        return render_template('targets/detail.html',
                             error=str(e),
                             gene_name=gene_name)