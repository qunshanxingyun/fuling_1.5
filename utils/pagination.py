from typing import Dict, List, Any, Tuple
import math

class Paginator:
    """分页工具类"""
    
    @staticmethod
    def paginate(data: List[Any], 
                 page: int = 1, 
                 page_size: int = 20,
                 max_page_size: int = 100) -> Dict:
        """
        对数据进行分页
        
        Args:
            data: 要分页的数据列表
            page: 页码（从1开始）
            page_size: 每页数量
            max_page_size: 最大每页数量
        
        Returns:
            包含分页信息的字典
        """
        # 参数验证
        page = max(1, page)
        page_size = min(max(1, page_size), max_page_size)
        
        total = len(data)
        total_pages = math.ceil(total / page_size)
        
        # 计算起始和结束索引
        start = (page - 1) * page_size
        end = start + page_size
        
        # 获取当前页数据
        items = data[start:end]
        
        return {
            'items': items,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages
            }
        }
    
    @staticmethod
    def paginate_dataframe(df, page: int = 1, page_size: int = 20) -> Tuple:
        """
        对DataFrame进行分页
        
        Returns:
            (分页后的DataFrame, 分页信息)
        """
        total = len(df)
        total_pages = math.ceil(total / page_size)
        
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_df = df.iloc[start:end]
        
        pagination_info = {
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }
        
        return paginated_df, pagination_info
