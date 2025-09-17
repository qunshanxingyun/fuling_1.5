from flask import Blueprint, jsonify, request
from services.target_service import TargetService
from config import Config

targets_bp = Blueprint('targets', __name__)
target_service = TargetService()

@targets_bp.route('/targets', methods=['GET'])
def get_targets():
    """
    获取靶点列表
    
    Query Parameters:
        - page: 页码（默认1）
        - page_size: 每页数量（默认20）
        - gene_family: 基因家族筛选（UGT/CYP450/Others/all）
        - search: 搜索关键词
        - sort_by: 排序字段（prediction_count/avg_score/compound_count）
        - sort_order: 排序方向（asc/desc）
    """
    try:
        # 获取请求参数
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', Config.DEFAULT_PAGE_SIZE, type=int)
        gene_family = request.args.get('gene_family', 'all')
        search = request.args.get('search')
        sort_by = request.args.get('sort_by', 'prediction_count')
        sort_order = request.args.get('sort_order', 'desc')
        
        # 验证参数
        page = max(1, page)
        page_size = min(max(1, page_size), Config.MAX_PAGE_SIZE)
        
        # 获取数据
        result = target_service.get_targets_list(
            page=page,
            page_size=page_size,
            # gene_family=gene_family,
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

@targets_bp.route('/targets/find', methods=['GET'])
def find_target():
    """通过各种标识符查找靶点"""
    query = request.args.get('q')
    # 支持基因符号、完整名称等多种查询

@targets_bp.route('/targets/<gene_name>', methods=['GET'])
def get_target_detail(gene_name):
    """获取靶点详细信息"""
    try:
        target = target_service.get_target_detail(gene_name)
        
        if target:
            return jsonify({
                'status': 'success',
                'data': target
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Target not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@targets_bp.route('/targets/<gene_name>/compounds', methods=['GET'])
def get_target_compounds(gene_name):
    """获取靶点关联的化合物"""
    try:
        target = target_service.get_target_detail(gene_name)
        
        if not target:
            return jsonify({
                'status': 'error',
                'message': 'Target not found'
            }), 404
        
        compounds = target.get('associated_compounds', [])
        
        # 按得分排序
        compounds.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return jsonify({
            'status': 'success',
            'data': {
                'target_info': {
                    'gene_name': target.get('gene_name'),
                    'gene_symbol': target.get('gene_symbol'),
                    'protein_names': target.get('protein_names')
                },
                'compounds': compounds,
                'total': len(compounds)
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@targets_bp.route('/targets/search', methods=['POST'])
def search_targets():
    """搜索靶点"""
    try:
        data = request.get_json()
        query = data.get('query', '')
        search_type = data.get('type', 'all')  # all, gene_name, protein_name, function
        
        # 使用列表接口的搜索功能
        result = target_service.get_targets_list(
            page=1,
            page_size=100,  # 搜索返回更多结果
            search=query
        )
        
        return jsonify({
            'status': 'success',
            'data': result['items'],
            'total': len(result['items'])
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@targets_bp.route('/targets/statistics', methods=['GET'])
def get_target_statistics():
    """获取靶点统计信息"""
    try:
        stats = target_service.get_target_statistics()
        
        return jsonify({
            'status': 'success',
            'data': stats
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
