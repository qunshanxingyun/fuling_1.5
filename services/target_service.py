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
        """Enhanced targets list with proper data loading"""
        # Get all unique targets with enhanced data processing
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
        
        # Debug: Print columns to see what data we have
        print(f"DEBUG: Available columns: {targets_df.columns.tolist()}")
        print(f"DEBUG: Sample data shape: {targets_df.shape}")
        if not targets_df.empty:
            print(f"DEBUG: First row sample: {targets_df.iloc[0].to_dict()}")
        
        # Apply search
        if search:
            # Search in multiple fields with case-insensitive matching
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
        
        # Apply sorting
        if sort_by in targets_df.columns:
            ascending = (sort_order == 'asc')
            targets_df = targets_df.sort_values(by=sort_by, ascending=ascending)
        
        # Apply pagination
        paginated_df, pagination_info = self.paginator.paginate_dataframe(
            targets_df, page, page_size
        )
        
        # Select and prepare display columns
        display_columns = [
            'gene_name', 'gene_symbol', 'species', 'prediction_count',
            'compound_count', 'avg_score', 'max_score', 'min_score',
            'uniprot_id', 'protein_names', 'function_cc'
        ]
        
        # Ensure columns exist and prepare data
        available_columns = [col for col in display_columns if col in paginated_df.columns]
        
        # Convert to dictionary list with enhanced data formatting
        items = []
        for _, row in paginated_df.iterrows():
            item = {}
            for col in available_columns:
                value = row[col]
                
                # Handle NaN and None values
                if pd.isna(value) or value is None:
                    if col in numeric_columns:
                        item[col] = 0
                    else:
                        item[col] = ''
                else:
                    # Format numeric values
                    if col in ['avg_score', 'max_score', 'min_score'] and value != 0:
                        item[col] = float(value)
                    elif col in ['prediction_count', 'compound_count']:
                        item[col] = int(value) if value != 0 else 0
                    else:
                        item[col] = str(value) if value else ''
            
            # Ensure minimum required fields exist
            if 'gene_name' not in item or not item['gene_name']:
                item['gene_name'] = item.get('gene_symbol', 'Unknown')
            
            items.append(item)
        
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
