from flask import Blueprint, render_template, request, abort, jsonify
from services.target_service import TargetService
from services.compound_service import CompoundService

targets_view_bp = Blueprint('targets_view', __name__, url_prefix='/targets')

# Initialize services
target_service = TargetService()
compound_service = CompoundService()

@targets_view_bp.route('/')
def targets_list():
    """Targets list page"""
    # Get query parameters
    search = request.args.get('search', '')
    
    try:
        # Get statistics for page display
        stats = target_service.get_target_statistics()
        
        return render_template('targets/list.html', 
                             search=search,
                             stats=stats)
    except Exception as e:
        return render_template('targets/list.html', 
                             error=str(e),
                             search=search)

@targets_view_bp.route('/<gene_name>')
def target_detail(gene_name):
    """Target detail page"""
    try:
        # Get target basic information
        target = target_service.get_target_detail(gene_name)
        if not target:
            abort(404)
        
        return render_template('targets/detail.html',
                             target=target)
    except Exception as e:
        return render_template('targets/detail.html',
                             error=str(e),
                             gene_name=gene_name)

# NEW: AJAX API for dynamic page loading (FIXED DATA LOADING)
@targets_view_bp.route('/api/list')
def targets_api_list():
    """Targets list API for DataTables - FIXED VERSION"""
    try:
        # Get DataTables parameters
        draw = request.args.get('draw', type=int)
        start = request.args.get('start', 0, type=int)
        length = request.args.get('length', 20, type=int)
        
        # Get search parameters (both DataTables default and custom)
        search_value = request.args.get('search[value]', '')
        custom_search = request.args.get('search_custom', '')
        
        # Use custom search if available, otherwise use DataTables search
        final_search = custom_search or search_value
        
        # Calculate page number
        page = (start // length) + 1
        
        # Get sorting parameters
        order_column = request.args.get('order[0][column]', '2')  # Default sort by prediction_count
        order_dir = request.args.get('order[0][dir]', 'desc')
        
        # Column name mapping
        columns = ['gene_name', 'gene_symbol', 'prediction_count', 'avg_score', 
                  'uniprot_id', 'actions']
        sort_by = columns[int(order_column)] if int(order_column) < len(columns) - 1 else 'prediction_count'
        
        # Call service to get data with proper parameters
        result = target_service.get_targets_list(
            page=page,
            page_size=length,
            search=final_search if final_search else None,
            sort_by=sort_by,
            sort_order=order_dir
        )
        
        # Get total count without filters for recordsTotal
        total_without_filters = target_service.get_targets_count(search=None)
        
        # Current result total is the filtered total
        filtered_total = result['pagination']['total']
        records_total = total_without_filters
        
        # Format return data for DataTables
        return jsonify({
            'draw': draw,
            'recordsTotal': records_total,
            'recordsFiltered': filtered_total,
            'data': result['items']
        })
        
    except Exception as e:
        print(f"Targets DataTables API Error: {e}")  # For debugging
        return jsonify({
            'draw': request.args.get('draw', type=int),
            'recordsTotal': 0,
            'recordsFiltered': 0,
            'data': [],
            'error': str(e)
        }), 500