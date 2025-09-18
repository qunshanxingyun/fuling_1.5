from flask import Blueprint, render_template, request, jsonify, abort
from services.compound_service import CompoundService
from services.target_service import TargetService

compounds_view_bp = Blueprint('compounds_view', __name__, url_prefix='/compounds')

# Initialize services
compound_service = CompoundService()
target_service = TargetService()

@compounds_view_bp.route('/')
def compounds_list():
    """Compounds list page"""
    # Get query parameters
    compound_type = request.args.get('type', 'all')
    search = request.args.get('search', '')
    
    try:
        # Get statistics
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
    """Compounds search page"""
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'all')
    
    return render_template('compounds/search.html', 
                         query=query, 
                         search_type=search_type)

@compounds_view_bp.route('/type/<compound_type>')
def compounds_by_type(compound_type):
    """View compounds by type"""
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
    """Compound detail page"""
    error_msg = None 
    try:
        # Get compound basic information
        compound = compound_service.get_compound_detail(compound_id)
        if not compound:
            abort(404)
        
        # Get predicted targets information
        targets_data = target_service.get_compound_targets(
            compound['compound_type'],
            compound['id']
        )
        
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
    """Compounds comparison page"""
    compound_ids = request.args.getlist('ids', type=int)
    
    compounds = []
    for cid in compound_ids[:5]:  # Maximum 5 compounds comparison
        compound = compound_service.get_compound_detail(cid)
        if compound:
            compounds.append(compound)
    
    return render_template('compounds/compare.html', compounds=compounds)

# AJAX API for dynamic page loading (FIXED PAGINATION LOGIC)
@compounds_view_bp.route('/api/list')
def compounds_api_list():
    """Compounds list API for DataTables - FIXED VERSION"""
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
        order_column = request.args.get('order[0][column]', '0')
        order_dir = request.args.get('order[0][dir]', 'asc')
        
        # Column name mapping
        columns = ['global_id', 'chinese_name', 'Name', 'compound_type', 
                  'Molecular_Formula', 'Molecular_Weight', 'actions']
        sort_by = columns[int(order_column)] if int(order_column) < len(columns) - 1 else 'global_id'
        
        # Get filter parameters
        compound_type = request.args.get('compound_type')
        if compound_type == 'all' or not compound_type:
            compound_type = None
        
        # Call service to get data
        result = compound_service.get_compounds_list(
            page=page,
            page_size=length,
            compound_type=compound_type,
            search=final_search if final_search else None,
            sort_by=sort_by,
            sort_order=order_dir
        )
        
        # Get total count without filters for recordsTotal
        total_without_filters = compound_service.count(filters=None, search=None)
        
        # Current result total is the filtered total
        filtered_total = result['pagination']['total']
        records_total = total_without_filters
        
        # Format return data for DataTables
        return jsonify({
            'draw': draw,
            'recordsTotal': records_total,
            'recordsFiltered': filtered_total,  # This fixes the "NaN total entries" issue
            'data': result['items']
        })
        
    except Exception as e:
        print(f"DataTables API Error: {e}")  # For debugging
        return jsonify({
            'draw': request.args.get('draw', type=int),
            'recordsTotal': 0,
            'recordsFiltered': 0,
            'data': [],
            'error': str(e)
        }), 500