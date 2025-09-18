from typing import Dict, List, Optional
import pandas as pd
from models.compound import Compound
from utils.pagination import Paginator
from config import Config

class CompoundService:
    """化合物业务逻辑服务"""
    
    def __init__(self):
        self.compound_model = Compound(Config.COMPOUNDS_FILE)
        self.paginator = Paginator()
    
    def get_compounds_list(self,
                          page: int = 1,
                          page_size: int = 20,
                          compound_type: Optional[str] = None,
                          search: Optional[str] = None,
                          sort_by: str = 'global_id',
                          sort_order: str = 'asc') -> Dict:
        """
        获取化合物列表（带分页）
        """
        # 构建筛选条件
        filters = {}
        if compound_type and compound_type != 'all':
            filters['compound_type'] = compound_type
        
        # 获取数据
        df = self.compound_model.get_all(
            filters=filters,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 分页
        paginated_df, pagination_info = self.paginator.paginate_dataframe(df, page, page_size)
        
        # 选择要返回的字段
        display_columns = [
            'global_id', 'id', 'chinese_name', 'Name', 
            'compound_type', 'Molecular_Formula', 'Molecular_Weight',
            'SMILES', 'Compound_CID'
        ]
        
        # 确保列存在
        available_columns = [col for col in display_columns if col in paginated_df.columns]
        
        # 转换为字典列表
        items = paginated_df[available_columns].fillna('').to_dict('records')
        
        # 格式化数值字段
        for item in items:
            if 'Molecular_Weight' in item and item['Molecular_Weight']:
                try:
                    item['Molecular_Weight'] = round(float(item['Molecular_Weight']), 2)
                except:
                    pass
        
        return {
            'items': items,
            'pagination': pagination_info
        }
    
    def get_compound_detail(self, compound_id: int) -> Optional[Dict]:
        """获取化合物详情"""
        compound = self.compound_model.get_by_id(compound_id)
        if compound:
            # 处理NaN值
            for key, value in compound.items():
                if pd.isna(value):
                    compound[key] = None
            return compound
        return None
    
    def search_compounds(self, query: str, search_type: str = 'all') -> List[Dict]:
        """搜索化合物"""
        if search_type == 'name':
            search_fields = ['chinese_name', 'Name']
        elif search_type == 'formula':
            search_fields = ['Molecular_Formula']
        elif search_type == 'smiles':
            search_fields = ['SMILES']
        else:
            search_fields = None
        
        df = self.compound_model.get_all(search=query)
        
        # 限制返回数量
        df = df.head(100)
        
        display_columns = ['global_id', 'chinese_name', 'Name', 'compound_type', 
                          'Molecular_Formula', 'Molecular_Weight']
        available_columns = [col for col in display_columns if col in df.columns]
        
        return df[available_columns].fillna('').to_dict('records')
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return self.compound_model.get_statistics()
    
    def count(self, filters: Optional[Dict] = None, search: Optional[str] = None) -> int:
        """
        Get total count of compounds matching criteria
        
        Args:
            filters: Filter conditions
            search: Search keyword
            
        Returns:
            int: Total count
        """
        return self.compound_model.count(filters=filters, search=search)
