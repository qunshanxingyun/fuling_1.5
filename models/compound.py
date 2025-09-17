import pandas as pd
from typing import List, Dict, Optional, Tuple
import os

class Compound:
    """化合物数据模型"""
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self._df = None
        self._load_data()
    
    def _load_data(self):
        """加载化合物数据"""
        if os.path.exists(self.data_path):
            self._df = pd.read_csv(self.data_path)
            # 确保global_id是整数类型
            if 'global_id' in self._df.columns:
                self._df['global_id'] = self._df['global_id'].astype(int)
        else:
            raise FileNotFoundError(f"数据文件不存在: {self.data_path}")
    
    def get_all(self, 
                filters: Optional[Dict] = None,
                search: Optional[str] = None,
                sort_by: str = 'global_id',
                sort_order: str = 'asc') -> pd.DataFrame:
        """
        获取化合物列表
        
        Args:
            filters: 筛选条件
            search: 搜索关键词
            sort_by: 排序字段
            sort_order: 排序方向
        
        Returns:
            筛选后的DataFrame
        """
        df = self._df.copy()
        
        # 应用筛选条件
        if filters:
            for key, value in filters.items():
                if key in df.columns and value is not None:
                    if key == 'compound_type' and value != 'all':
                        df = df[df[key] == value]
                    # 可以添加更多筛选逻辑
        
        # 应用搜索
        if search:
            # 在多个字段中搜索
            search_fields = ['chinese_name', 'Name', 'Molecular_Formula', 'SMILES']
            mask = False
            for field in search_fields:
                if field in df.columns:
                    mask |= df[field].astype(str).str.contains(search, case=False, na=False)
            df = df[mask]
        
        # 应用排序
        if sort_by in df.columns:
            ascending = (sort_order == 'asc')
            df = df.sort_values(by=sort_by, ascending=ascending)
        
        return df
    
    def get_by_id(self, compound_id: int) -> Optional[Dict]:
        """根据ID获取化合物详情"""
        result = self._df[self._df['global_id'] == compound_id]
        if not result.empty:
            # --- START: 核心修改 ---
            compound_dict = result.iloc[0].to_dict()
            
            # 定义键名映射规则：将带连字符的键名改为带下划线的
            rename_map = {
                'H-Bond_Donor_Count': 'H_Bond_Donor_Count',
                'H-Bond_Acceptor_Count': 'H_Bond_Acceptor_Count',
                'Rotatable_Bond_Count': 'Rotatable_Bond_Count'
            }
            
            # 执行重命名
            for old_key, new_key in rename_map.items():
                if old_key in compound_dict:
                    compound_dict[new_key] = compound_dict.pop(old_key)
            
            return compound_dict
            # --- END: 核心修改 ---
        return None
    
    def count(self, filters: Optional[Dict] = None, search: Optional[str] = None) -> int:
        """获取符合条件的化合物总数"""
        df = self.get_all(filters=filters, search=search)
        return len(df)
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        stats = {
            'total': len(self._df),
            'by_type': self._df['compound_type'].value_counts().to_dict() if 'compound_type' in self._df.columns else {},
            'with_smiles': self._df['SMILES'].notna().sum() if 'SMILES' in self._df.columns else 0,
            'with_pubchem_id': self._df['Compound_CID'].notna().sum() if 'Compound_CID' in self._df.columns else 0,
        }
        return stats