import os

class Config:
    """基础配置"""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    
    # 数据文件路径
    COMPOUNDS_FILE = os.path.join(DATA_DIR, 'compounds.csv')
    TARGETS_FILE = os.path.join(DATA_DIR, 'targets.xlsx')  # 新增
    PREDICTION_DIRS = {
        '挥发油': os.path.join(DATA_DIR, 'huifayou'),
        '三萜': os.path.join(DATA_DIR, 'santie'),
        '甾醇': os.path.join(DATA_DIR, 'zaichun')
    }
    
    # 分页配置
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # 缓存配置
    CACHE_ENABLED = True
    CACHE_TIMEOUT = 300  # 5分钟
    
    # API配置
    JSON_AS_ASCII = False
    JSON_SORT_KEYS = False

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    
class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
# 根据环境变量选择配置
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
