from flask import Blueprint, render_template, request, jsonify, abort
from services.compound_service import CompoundService
from services.target_service import TargetService

compounds_view_bp = Blueprint('compounds_view', __name__, url_prefix='/compounds')

# 实例化服务
compound_service = CompoundService()
target_service = TargetService()

@compounds_view_bp.route('/')
def compounds_list():
    """化合物列表页面"""
    # 获取查询参数
    compound_type = request.args.get('type', 'all')
    search = request.args.get('search', '')
    
    try:
        # 获取统计信息
        stats = compound_service.get_statistics()
        
        return render_template('compounds/list.html', 
                             compound_type=compound_type,
                             search=search,
                             stats=stats)
    except Exception as e:
        return render_template('compounds/list.html', 
                             error=str(e),
                             compound_type=compound_type,
                             search=search)

@compounds_view_bp.route('/search')
def compounds_search():
    """化合物搜索页面"""
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'all')
    
    return render_template('compounds/search.html', 
                         query=query, 
                         search_type=search_type)

@compounds_view_bp.route('/type/<compound_type>')
def compounds_by_type(compound_type):
    """按类型查看化合物"""
    if compound_type not in ['挥发油', '三萜', '甾醇']:
        abort(404)
    
    try:
        stats = compound_service.get_statistics()
        return render_template('compounds/list.html', 
                             compound_type=compound_type,
                             stats=stats)
    except Exception as e:
        return render_template('compounds/list.html', 
                             error=str(e),
                             compound_type=compound_type)

@compounds_view_bp.route('/<int:compound_id>')
def compound_detail(compound_id):
    """化合物详情页面"""
    error_msg = None 
    try:
        # 获取化合物基本信息
        compound = compound_service.get_compound_detail(compound_id)
        if not compound:
            abort(404)
        
        # 获取预测靶点信息
        targets_data = target_service.get_compound_targets(
            compound['compound_type'],
            compound['id']
        )
        # 打印所有可用的键！
        print("Compound Keys:", compound.keys()) 
        return render_template('compounds/detail.html',
                             compound=compound,
                             targets_data=targets_data,
                             error_msg=error_msg)
    except Exception as e:
        return render_template('compounds/detail.html',
                             error=str(e),
                             compound_id=compound_id)

@compounds_view_bp.route('/compare')
def compounds_compare():
    """化合物对比页面"""
    compound_ids = request.args.getlist('ids', type=int)
    
    compounds = []
    for cid in compound_ids[:5]:  # 最多对比5个化合物
        compound = compound_service.get_compound_detail(cid)
        if compound:
            compounds.append(compound)
    
    return render_template('compounds/compare.html', compounds=compounds)

# AJAX接口用于页面动态加载
@compounds_view_bp.route('/api/list')
def compounds_api_list():
    """化合物列表API（用于DataTables）"""
    try:
        # 获取DataTables参数
        draw = request.args.get('draw', type=int)
        start = request.args.get('start', 0, type=int)
        length = request.args.get('length', 20, type=int)
        search_value = request.args.get('search[value]', '')
        
        # 计算页码
        page = (start // length) + 1
        
        # 获取排序参数
        order_column = request.args.get('order[0][column]', '0')
        order_dir = request.args.get('order[0][dir]', 'asc')
        
        # 列名映射
        columns = ['global_id', 'chinese_name', 'Name', 'compound_type', 
                  'Molecular_Formula', 'Molecular_Weight']
        sort_by = columns[int(order_column)] if int(order_column) < len(columns) else 'global_id'
        
        # 获取筛选参数
        compound_type = request.args.get('compound_type')
        
        # 调用服务获取数据
        result = compound_service.get_compounds_list(
            page=page,
            page_size=length,
            compound_type=compound_type,
            search=search_value if search_value else None,
            sort_by=sort_by,
            sort_order=order_dir
        )
        
        # 格式化返回数据
        return jsonify({
            'draw': draw,
            'recordsTotal': result['pagination']['total'],
            'recordsFiltered': result['pagination']['total'],
            'data': result['items']
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500