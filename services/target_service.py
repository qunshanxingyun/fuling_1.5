from typing import Dict, List, Optional
import pandas as pd
from models.target import Target
from models.compound import Compound
from utils.pagination import Paginator
from config import Config

class TargetService:
    """靶点业务逻辑服务"""
    
    def __init__(self):
        self.target_model = Target(Config.PREDICTION_DIRS, Config.TARGETS_FILE)
        self.compound_model = Compound(Config.COMPOUNDS_FILE)
        self.paginator = Paginator()
    
    def get_compound_targets(self, compound_type: str, compound_id: int) -> Dict:
        """获取化合物的预测靶点"""
        targets_df = self.target_model.get_compound_targets(compound_type, compound_id)
        
        if targets_df is None or targets_df.empty:
            return {
                'targets': [],
                'statistics': {
                    'total': 0
                }
            }
        
        # 转换数据格式
        targets = targets_df.fillna('').to_dict('records')
        
        # 处理数值字段
        for target in targets:
            if 'score' in target and target['score']:
                target['score'] = float(target['score'])
            if 'prediction_count' in target and target['prediction_count']:
                target['prediction_count'] = int(target['prediction_count'])
            if 'compound_count' in target and target['compound_count']:
                target['compound_count'] = int(target['compound_count'])
        
        # 计算统计信息
        statistics = {
            'total': len(targets),
            'avg_score': float(targets_df['score'].mean()) if 'score' in targets_df else 0,
            'score_range': {
                'min': float(targets_df['score'].min()) if 'score' in targets_df else 0,
                'max': float(targets_df['score'].max()) if 'score' in targets_df else 0
            },
        }
        
        return {
            'targets': targets,
            'statistics': statistics
        }
    
    def get_targets_list(self,
                    page: int = 1,
                    page_size: int = 20,
                    search: Optional[str] = None,
                    sort_by: str = 'prediction_count',
                    sort_order: str = 'desc') -> Dict:
        """Enhanced targets list with FIXED column naming"""
        # Get all unique targets
        targets_df = self.target_model.get_all_unique_targets()
        
        if targets_df.empty:
            return {
                'items': [],
                'pagination': {
                    'page': 1,
                    'page_size': page_size,
                    'total': 0,
                    'total_pages': 0
                }
            }
        
        # CRITICAL FIX: Clean up duplicate column names from merge
        column_rename_map = {}
        
        # Handle duplicate columns from pandas merge
        if 'prediction_count_x' in targets_df.columns:
            # Use the aggregated prediction count (_x) which is from our calculation
            targets_df['prediction_count'] = targets_df['prediction_count_x']
            column_rename_map['prediction_count_x'] = 'prediction_count'
            
        if 'avg_score_x' in targets_df.columns:
            # Use the aggregated average score (_x) which is from our calculation  
            targets_df['avg_score'] = targets_df['avg_score_x']
            column_rename_map['avg_score_x'] = 'avg_score'
            
        if 'compound_count_x' in targets_df.columns:
            # Use the aggregated compound count (_x) which is from our calculation
            targets_df['compound_count'] = targets_df['compound_count_x']
            column_rename_map['compound_count_x'] = 'compound_count'
        
        # Remove duplicate columns to avoid confusion
        columns_to_drop = []
        for col in targets_df.columns:
            if col.endswith('_y') and col.replace('_y', '') in targets_df.columns:
                columns_to_drop.append(col)
            elif col.endswith('_x') and col.replace('_x', '') in targets_df.columns:
                columns_to_drop.append(col)
        
        if columns_to_drop:
            targets_df = targets_df.drop(columns=columns_to_drop)
        
        # Debug: Print cleaned columns
        print(f"DEBUG: Cleaned columns: {targets_df.columns.tolist()}")
        if not targets_df.empty:
            sample_row = targets_df.iloc[0]
            print(f"DEBUG: prediction_count = {sample_row.get('prediction_count', 'MISSING')}")
            print(f"DEBUG: avg_score = {sample_row.get('avg_score', 'MISSING')}")
        
        # Apply search
        if search:
            mask = pd.Series([False] * len(targets_df))
            search_fields = ['gene_name', 'gene_symbol', 'protein_names', 'function_cc', 'uniprot_id']
            
            for field in search_fields:
                if field in targets_df.columns:
                    mask |= targets_df[field].astype(str).str.contains(search, case=False, na=False)
            
            targets_df = targets_df[mask]
        
        # Ensure numeric columns are properly typed
        numeric_columns = ['prediction_count', 'avg_score', 'max_score', 'min_score', 'compound_count']
        for col in numeric_columns:
            if col in targets_df.columns:
                targets_df[col] = pd.to_numeric(targets_df[col], errors='coerce').fillna(0)
        
        # Apply sorting with proper column names
        if sort_by in targets_df.columns:
            ascending = (sort_order == 'asc')
            targets_df = targets_df.sort_values(by=sort_by, ascending=ascending)
        else:
            # Fallback sorting
            if 'prediction_count' in targets_df.columns:
                targets_df = targets_df.sort_values(by='prediction_count', ascending=False)
        
        # Apply pagination
        paginated_df, pagination_info = self.paginator.paginate_dataframe(
            targets_df, page, page_size
        )
        
        # Select display columns - using cleaned column names
        display_columns = [
            'gene_name', 'gene_symbol', 'prediction_count', 'avg_score', 
            'uniprot_id', 'protein_names', 'function_cc', 'compound_count'
        ]
        
        # Convert to dictionary list with proper data handling
        items = []
        for _, row in paginated_df.iterrows():
            item = {}
            for col in display_columns:
                if col in row.index:
                    value = row[col]
                    
                    # Handle NaN and None values
                    if pd.isna(value) or value is None:
                        if col in ['prediction_count', 'compound_count']:
                            item[col] = 0
                        elif col in ['avg_score']:
                            item[col] = 0.0
                        else:
                            item[col] = ''
                    else:
                        # Format values properly
                        if col in ['avg_score'] and value != 0:
                            item[col] = float(value)
                        elif col in ['prediction_count', 'compound_count']:
                            item[col] = int(value) if value != 0 else 0
                        else:
                            item[col] = str(value) if value else ''
                else:
                    # Column missing, set default
                    if col in ['prediction_count', 'compound_count']:
                        item[col] = 0
                    elif col in ['avg_score']:
                        item[col] = 0.0
                    else:
                        item[col] = ''
            
            # Ensure minimum required fields
            if 'gene_name' not in item or not item['gene_name']:
                item['gene_name'] = item.get('gene_symbol', 'Unknown')
            
            items.append(item)
        
        print(f"DEBUG: Sample processed item: {items[0] if items else 'No items'}")
        
        return {
            'items': items,
            'pagination': pagination_info
        }
    
    def get_target_detail(self, gene_name: str) -> Optional[Dict]:
        """获取靶点详细信息"""
        target = self.target_model.get_target_by_gene_name(gene_name)
        
        if target:
            # 处理NaN值
            for key, value in target.items():
                if pd.isna(value):
                    target[key] = None
            
            # 获取关联的化合物
            compounds = self.target_model.get_compounds_by_target(gene_name)
            
            # 为每个化合物添加详细信息
            enriched_compounds = []
            for comp in compounds:
                # 计算global_id
                compound_info = self._get_compound_info_by_type_and_id(
                    comp['compound_type'], 
                    comp['compound_id']
                )
                if compound_info:
                    enriched_compounds.append({
                        **comp,
                        'global_id': compound_info['global_id'],
                        'chinese_name': compound_info.get('chinese_name', ''),
                        'molecular_formula': compound_info.get('Molecular_Formula', '')
                    })
            
            target['associated_compounds'] = enriched_compounds
            target['associated_compounds_count'] = len(enriched_compounds)
            
            return target
        
        return None
    
    def _get_compound_info_by_type_and_id(self, compound_type: str, local_id: int) -> Optional[Dict]:
        """根据化合物类型和本地ID获取化合物信息"""
        df = self.compound_model._df
        compound = df[(df['compound_type'] == compound_type) & (df['id'] == local_id)]
        
        if not compound.empty:
            return compound.iloc[0].to_dict()
        return None
    
    def get_target_statistics(self) -> Dict:
        """获取靶点统计信息"""
        targets_df = self.target_model.get_all_unique_targets()
        
        if targets_df.empty:
            return {
                'total_targets': 0,
                'species_distribution': {},
                'top_predicted_targets': []
            }
        
        # 物种分布
        species_dist = {}
        if 'species' in targets_df.columns:
            species_dist = targets_df['species'].value_counts().to_dict()
        
        # 预测次数最多的前10个靶点
        top_targets = []
        if 'prediction_count' in targets_df.columns:
            top_df = targets_df.nlargest(10, 'prediction_count')[
                ['gene_name', 'gene_symbol', 'prediction_count', 'avg_score']
            ]
            top_targets = top_df.fillna('').to_dict('records')
        
        return {
            'total_targets': len(targets_df),
            'species_distribution': species_dist,
            'top_predicted_targets': top_targets
        }
    
    
    # Add this method to the existing TargetService class in services/target_service.py

    def get_targets_count(self, search: Optional[str] = None) -> int:
        """
        Get total count of targets matching search criteria
        
        Args:
            search: Search keyword
            
        Returns:
            int: Total count of targets
        """
        # Get all unique targets
        targets_df = self.target_model.get_all_unique_targets()
        
        if targets_df.empty:
            return 0
        
        # Apply search if provided
        if search:
            # Search in multiple fields
            mask = pd.Series([False] * len(targets_df))
            search_fields = ['gene_name', 'gene_symbol', 'protein_names', 'function_cc']
            
            for field in search_fields:
                if field in targets_df.columns:
                    mask |= targets_df[field].astype(str).str.contains(search, case=False, na=False)
            
            targets_df = targets_df[mask]
        
        return len(targets_df)
