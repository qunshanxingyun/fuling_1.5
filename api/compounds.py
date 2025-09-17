from flask import Blueprint, jsonify, request
from services.compound_service import CompoundService
from config import Config

compounds_bp = Blueprint('compounds', __name__)
compound_service = CompoundService()

@compounds_bp.route('/compounds', methods=['GET'])
def get_compounds():
    """
    获取化合物列表
    
    Query Parameters:
        - page: 页码（默认1）
        - page_size: 每页数量（默认20）
        - type: 化合物类型
        - search: 搜索关键词
        - sort_by: 排序字段
        - sort_order: 排序方向（asc/desc）
    """
    try:
        # 获取请求参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', Config.DEFAULT_PAGE_SIZE, type=int)
        compound_type = request.args.get('type')
        search = request.args.get('search')
        sort_by = request.args.get('sort_by', 'global_id')
        sort_order = request.args.get('sort_order', 'asc')
        
        # 验证参数
        page = max(1, page)
        page_size = min(max(1, page_size), Config.MAX_PAGE_SIZE)
        
        # 获取数据
        result = compound_service.get_compounds_list(
            page=page,
            page_size=page_size,
            compound_type=compound_type,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return jsonify({
            'status': 'success',
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@compounds_bp.route('/compounds/<int:compound_id>', methods=['GET'])
def get_compound_detail(compound_id):
    """获取化合物详情"""
    try:
        compound = compound_service.get_compound_detail(compound_id)
        
        if compound:
            return jsonify({
                'status': 'success',
                'data': compound
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Compound not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@compounds_bp.route('/compounds/search', methods=['POST'])
def search_compounds():
    """搜索化合物"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        search_type = data.get('type', 'all')
        
        results = compound_service.search_compounds(query, search_type)
        
        return jsonify({
            'status': 'success',
            'data': results,
            'total': len(results)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@compounds_bp.route('/compounds/statistics', methods=['GET'])
def get_statistics():
    """获取统计信息"""
    try:
        stats = compound_service.get_statistics()
        
        return jsonify({
            'status': 'success',
            'data': stats
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

from services.target_service import TargetService

target_service = TargetService()

@compounds_bp.route('/compounds/<int:compound_id>/targets', methods=['GET'])
def get_compound_targets(compound_id):
    """获取化合物的预测靶点"""
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 10, type=int)
        
        # 先获取化合物信息
        compound = compound_service.get_compound_detail(compound_id)
        
        if not compound:
            return jsonify({
                'status': 'error',
                'message': 'Compound not found'
            }), 404
        
        # 获取所有靶点信息（不带分页参数）
        targets_data = target_service.get_compound_targets(
            compound['compound_type'],
            compound['id']
        )
        
        # 在Python中实现分页
        all_targets = targets_data.get('targets', [])
        total_targets = len(all_targets)
        
        # 计算分页
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_targets = all_targets[start_idx:end_idx]
        
        # 构建分页信息
        total_pages = (total_targets + page_size - 1) // page_size
        pagination = {
            'page': page,
            'page_size': page_size,
            'total': total_targets,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
        
        return jsonify({
            'status': 'success',
            'data': {
                'compound_info': compound,
                'targets': paginated_targets,
                'statistics': targets_data.get('statistics', {}),
                'pagination': pagination
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500