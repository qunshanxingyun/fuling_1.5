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
                        # gene_family: Optional[str] = None,
                        search: Optional[str] = None,
                        sort_by: str = 'prediction_count',
                        sort_order: str = 'desc') -> Dict:
        """获取靶点列表（带分页）"""
        # 获取所有独特靶点
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
        
        # 应用搜索
        if search:
            # 在多个字段中搜索
            mask = pd.Series([False] * len(targets_df))
            search_fields = ['gene_name', 'gene_symbol', 'protein_names', 'function_cc']
            
            for field in search_fields:
                if field in targets_df.columns:
                    mask |= targets_df[field].astype(str).str.contains(search, case=False, na=False)
            
            targets_df = targets_df[mask]
        
        # 应用基因家族筛选
        # if gene_family and gene_family != 'all':
        #     if gene_family == 'UGT':
        #         targets_df = targets_df[targets_df['gene_name'].str.contains('UGT', na=False)]
        #     elif gene_family == 'CYP450':
        #         targets_df = targets_df[targets_df['gene_name'].str.contains('CYP', na=False)]
        #     elif gene_family == 'Others':
        #         targets_df = targets_df[
        #             ~targets_df['gene_name'].str.contains('UGT|CYP', na=False)
        #         ]
        
        # 应用排序
        if sort_by in targets_df.columns:
            ascending = (sort_order == 'asc')
            targets_df = targets_df.sort_values(by=sort_by, ascending=ascending)
        
        # 分页
        paginated_df, pagination_info = self.paginator.paginate_dataframe(
            targets_df, page, page_size
        )
        
        # 选择要返回的字段
        display_columns = [
            'gene_name', 'gene_symbol', 'species', 'prediction_count',
            'compound_count', 'avg_score', 'uniprot_id', 'protein_names'
        ]
        
        # 确保列存在
        available_columns = [col for col in display_columns if col in paginated_df.columns]
        
        # 转换为字典列表
        items = paginated_df[available_columns].fillna('').to_dict('records')
        
        # 格式化数值字段
        for item in items:
            if 'avg_score' in item and item['avg_score']:
                item['avg_score'] = round(float(item['avg_score']), 4)
            if 'prediction_count' in item and item['prediction_count']:
                item['prediction_count'] = int(item['prediction_count'])
            if 'compound_count' in item and item['compound_count']:
                item['compound_count'] = int(item['compound_count'])
        
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
