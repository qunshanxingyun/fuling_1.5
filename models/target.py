import pandas as pd
import os
import re
from typing import List, Dict, Optional, Set
from config import Config

class Target:
    """靶点数据模型"""
    
    def __init__(self, prediction_dirs: Dict[str, str], targets_file: str = None):
        self.prediction_dirs = prediction_dirs
        self.targets_file = targets_file or Config.TARGETS_FILE
        self._targets_df = None
        self._gene_name_to_symbol_map = {}  # From值到gene_symbol的映射
        self._load_target_info()
    
    def _load_target_info(self):
        """加载靶点基础信息并建立名称映射"""
        if os.path.exists(self.targets_file):
            self._targets_df = pd.read_excel(self.targets_file)
            # 建立基因名称到基因符号的映射
            self._build_gene_name_mapping()
        else:
            self._targets_df = pd.DataFrame()
    
    def _build_gene_name_mapping(self):
        """建立基因名称（包括别名）到基因符号的映射"""
        if 'gene_names_full' in self._targets_df.columns and 'gene_symbol' in self._targets_df.columns:
            for _, row in self._targets_df.iterrows():
                gene_symbol = row['gene_symbol']
                gene_names_full = str(row['gene_names_full'])
                
                # gene_names_full包含多个名称，用空格分隔
                # 例如: "UGT1A6 GNT1 UGT1"
                gene_names = gene_names_full.split()
                
                # 为每个名称建立到gene_symbol的映射
                for name in gene_names:
                    self._gene_name_to_symbol_map[name] = gene_symbol
    
    def _get_gene_symbol_from_name(self, gene_name: str) -> Optional[str]:
        """根据基因名称（可能是别名）获取标准的gene_symbol"""
        return self._gene_name_to_symbol_map.get(gene_name)
    
    def get_compound_targets(self, compound_type: str, compound_id: int) -> Optional[pd.DataFrame]:
        """获取特定化合物的预测靶点"""
        type_map = {
            '挥发油': 'huifayou',
            '三萜': 'santie',
            '甾醇': 'zaichun'
        }
        
        dir_name = type_map.get(compound_type)
        if not dir_name:
            return None
        
        # 根据新命名规则
        filename = f'{dir_name}{compound_id}.xlsx'
        filepath = os.path.join(self.prediction_dirs[compound_type], filename)
        
        if os.path.exists(filepath):
            df = pd.read_excel(filepath)
            # 如果有靶点基础信息，进行关联
            if not self._targets_df.empty and 'From' in df.columns:
                # 添加标准化的基因符号列
                df['gene_symbol'] = df['From'].apply(self._get_gene_symbol_from_name)
                # 通过基因符号关联更多信息
                df = self._enrich_target_info(df)
            return df
        return None
    
    def _enrich_target_info(self, prediction_df: pd.DataFrame) -> pd.DataFrame:
        """用基础信息丰富预测数据"""
        # 如果没有gene_symbol列，直接返回
        if 'gene_symbol' not in prediction_df.columns:
            return prediction_df
        
        # 与targets_df合并，使用gene_symbol作为连接键
        enriched_df = pd.merge(
            prediction_df,
            self._targets_df,
            on='gene_symbol',
            how='left',
            suffixes=('', '_from_targets')
        )
        
        return enriched_df
    
    def get_all_unique_targets(self) -> pd.DataFrame:
        """Enhanced: Get all unique targets with proper column handling"""
        all_targets = []
        
        # From all prediction files collect targets
        for compound_type, dir_path in self.prediction_dirs.items():
            if os.path.exists(dir_path):
                for file in os.listdir(dir_path):
                    if file.endswith('.xlsx'):
                        try:
                            df = pd.read_excel(os.path.join(dir_path, file))
                            if not df.empty and 'From' in df.columns:
                                df['source_type'] = compound_type
                                df['source_file'] = file
                                # Add standardized gene_symbol
                                df['gene_symbol'] = df['From'].apply(self._get_gene_symbol_from_name)
                                
                                # Ensure score column is numeric
                                if 'score' in df.columns:
                                    df['score'] = pd.to_numeric(df['score'], errors='coerce')
                                
                                all_targets.append(df)
                        except Exception as e:
                            print(f"Error reading {file}: {str(e)}")
                            continue
        
        if all_targets:
            combined_df = pd.concat(all_targets, ignore_index=True)
            
            # Only process records with valid gene_symbol
            valid_targets = combined_df[combined_df['gene_symbol'].notna()]
            
            if valid_targets.empty:
                return pd.DataFrame()
            
            # Group by gene_symbol and calculate statistics
            target_stats = valid_targets.groupby('gene_symbol').agg({
                'score': ['mean', 'max', 'min', 'count'],
                'source_type': lambda x: list(set(x)),
                'source_file': 'nunique',  # Number of unique compounds
                'From': 'first'  # Keep original From value
            }).reset_index()
            
            # Flatten multi-level columns with clean names
            target_stats.columns = [
                'gene_symbol', 'avg_score', 'max_score', 'min_score', 
                'prediction_count', 'compound_types', 'compound_count', 'from_name'
            ]
            
            # Clean up data types
            numeric_cols = ['avg_score', 'max_score', 'min_score', 'prediction_count', 'compound_count']
            for col in numeric_cols:
                target_stats[col] = pd.to_numeric(target_stats[col], errors='coerce').fillna(0)
            
            # CRITICAL FIX: Merge with base target info using suffixes to avoid conflicts
            if not self._targets_df.empty:
                # Prepare base dataframe columns to avoid conflicts
                base_df = self._targets_df.copy()
                
                # Only keep essential columns from base data to avoid conflicts
                base_essential_cols = [
                    'gene_symbol', 'gene_name', 'species', 'uniprot_id', 
                    'protein_names', 'function_cc', 'subcellular_location_cc'
                ]
                
                # Filter to only existing columns
                base_available_cols = [col for col in base_essential_cols if col in base_df.columns]
                base_df = base_df[base_available_cols]
                
                # Merge WITHOUT creating duplicate columns
                target_stats = pd.merge(
                    target_stats, 
                    base_df, 
                    on='gene_symbol', 
                    how='left',
                    suffixes=('', '_base')  # Our calculated data gets no suffix, base data gets _base
                )
                
                # Fill missing gene_name with gene_symbol
                if 'gene_name' not in target_stats.columns:
                    target_stats['gene_name'] = target_stats['gene_symbol']
                else:
                    target_stats['gene_name'] = target_stats['gene_name'].fillna(target_stats['gene_symbol'])
            else:
                # If no base info, create essential columns
                target_stats['gene_name'] = target_stats['gene_symbol']
                target_stats['species'] = 'Homo sapiens'
            
            # Ensure all required columns exist with proper defaults
            required_columns = {
                'uniprot_id': '',
                'protein_names': '',
                'function_cc': '',
                'species': 'Homo sapiens'
            }
            
            for col, default_val in required_columns.items():
                if col not in target_stats.columns:
                    target_stats[col] = default_val
                else:
                    # Fill NaN values with defaults
                    target_stats[col] = target_stats[col].fillna(default_val)
            
            print(f"DEBUG: Final columns after merge: {target_stats.columns.tolist()}")
            print(f"DEBUG: Sample merged data: prediction_count = {target_stats.iloc[0]['prediction_count'] if not target_stats.empty else 'NO DATA'}")
            
            return target_stats
        
        return pd.DataFrame()
    
    def get_target_by_gene_name(self, gene_name: str) -> Optional[Dict]:
        """根据基因名获取靶点详情（支持基因符号和别名）"""
        # 首先尝试将输入的名称转换为标准的gene_symbol
        gene_symbol = self._get_gene_symbol_from_name(gene_name)
        
        if not gene_symbol:
            # 如果无法映射，尝试直接作为gene_symbol查找
            gene_symbol = gene_name
        
        # 从基础信息中查找
        if not self._targets_df.empty and 'gene_symbol' in self._targets_df.columns:
            target = self._targets_df[self._targets_df['gene_symbol'] == gene_symbol]
            if not target.empty:
                target_dict = target.iloc[0].to_dict()
                # 添加映射信息
                target_dict['queried_name'] = gene_name
                target_dict['mapped_symbol'] = gene_symbol
                return target_dict
        
        # 如果基础信息中没有，尝试从预测数据中查找
        all_targets = self.get_all_unique_targets()
        if not all_targets.empty:
            target = all_targets[all_targets['gene_symbol'] == gene_symbol]
            if not target.empty:
                return target.iloc[0].to_dict()
        
        return None
    
    def get_compounds_by_target(self, gene_name: str) -> List[Dict]:
        """获取预测到某个靶点的所有化合物（支持基因符号和别名）"""
        compounds = []
        
        # 获取标准的gene_symbol
        gene_symbol = self._get_gene_symbol_from_name(gene_name)
        if not gene_symbol:
            gene_symbol = gene_name
        
        for compound_type, dir_path in self.prediction_dirs.items():
            if os.path.exists(dir_path):
                type_map = {
                    '挥发油': 'huifayou',
                    '三萜': 'santie',
                    '甾醇': 'zaichun'
                }
                prefix = type_map[compound_type]
                
                for file in os.listdir(dir_path):
                    if file.endswith('.xlsx'):
                        # 从文件名提取化合物ID
                        compound_id = file.replace(prefix, '').replace('.xlsx', '')
                        
                        try:
                            df = pd.read_excel(os.path.join(dir_path, file))
                            if not df.empty and 'From' in df.columns:
                                # 添加标准化的基因符号
                                df['gene_symbol'] = df['From'].apply(self._get_gene_symbol_from_name)
                                
                                # 查找匹配的靶点（支持原始From值和映射后的gene_symbol）
                                target_rows = df[
                                    (df['From'] == gene_name) | 
                                    (df['gene_symbol'] == gene_symbol)
                                ]
                                
                                if not target_rows.empty:
                                    for _, row in target_rows.iterrows():
                                        compounds.append({
                                            'compound_id': int(compound_id),
                                            'compound_type': compound_type,
                                            'score': float(row.get('score', 0)),
                                            'from_name': row.get('From', ''),
                                            'gene_name_full': row.get('Gene Name', ''),
                                            'source_file': file
                                        })
                        except Exception as e:
                            print(f"Error reading {file}: {str(e)}")
                            continue
        
        return compounds
    
    def get_all_unique_targets(self) -> pd.DataFrame:
        """Enhanced: Get all unique targets with better data aggregation"""
        all_targets = []
        
        # From all prediction files collect targets with enhanced processing
        for compound_type, dir_path in self.prediction_dirs.items():
            if os.path.exists(dir_path):
                for file in os.listdir(dir_path):
                    if file.endswith('.xlsx'):
                        try:
                            df = pd.read_excel(os.path.join(dir_path, file))
                            if not df.empty and 'From' in df.columns:
                                df['source_type'] = compound_type
                                df['source_file'] = file
                                # Add standardized gene_symbol
                                df['gene_symbol'] = df['From'].apply(self._get_gene_symbol_from_name)
                                
                                # Ensure score column is numeric
                                if 'score' in df.columns:
                                    df['score'] = pd.to_numeric(df['score'], errors='coerce')
                                
                                all_targets.append(df)
                        except Exception as e:
                            print(f"Error reading {file}: {str(e)}")
                            continue
        
        if all_targets:
            combined_df = pd.concat(all_targets, ignore_index=True)
            
            # Enhanced aggregation with better statistics
            valid_targets = combined_df[combined_df['gene_symbol'].notna()]
            
            if valid_targets.empty:
                return pd.DataFrame()
            
            # Group by gene_symbol and calculate comprehensive statistics
            target_stats = valid_targets.groupby('gene_symbol').agg({
                'score': ['mean', 'max', 'min', 'count', 'std'],
                'source_type': lambda x: list(set(x)),
                'source_file': 'nunique',  # Number of unique files (compounds)
                'From': 'first'  # Keep original From value
            }).reset_index()
            
            # Flatten multi-level columns
            target_stats.columns = [
                'gene_symbol', 'avg_score', 'max_score', 'min_score', 
                'prediction_count', 'score_std', 'compound_types', 
                'compound_count', 'from_name'
            ]
            
            # Clean up data types and handle NaN values
            numeric_cols = ['avg_score', 'max_score', 'min_score', 'prediction_count', 'compound_count']
            for col in numeric_cols:
                target_stats[col] = pd.to_numeric(target_stats[col], errors='coerce').fillna(0)
            
            # Merge with target base information if available
            if not self._targets_df.empty:
                target_stats = pd.merge(
                    target_stats, 
                    self._targets_df, 
                    on='gene_symbol', 
                    how='left'
                )
                
                # Fill missing gene_name with gene_symbol
                if 'gene_name' in target_stats.columns:
                    target_stats['gene_name'] = target_stats['gene_name'].fillna(target_stats['gene_symbol'])
            else:
                # If no base info, use gene_symbol as gene_name
                target_stats['gene_name'] = target_stats['gene_symbol']
            
            # Add species column if missing
            if 'species' not in target_stats.columns:
                target_stats['species'] = 'Homo sapiens'
            
            # Ensure all required columns exist with proper defaults
            required_columns = {
                'uniprot_id': '',
                'protein_names': '',
                'function_cc': ''
            }
            
            for col, default_val in required_columns.items():
                if col not in target_stats.columns:
                    target_stats[col] = default_val
            
            return target_stats
        
        return pd.DataFrame()
