#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pandas as pd
from rdkit import Chem
from typing import Optional, Tuple
from pathlib import Path

class DataProcessor:
    def __init__(self, work_dir: str = 'D:/CurrentProjects/FuLing/茯苓/fuling_final/datasets'):
        """
        初始化数据处理器
        
        Args:
            work_dir: 工作目录路径
        """
        self.work_dir = Path(work_dir)
        self.protein_info_path = self.work_dir / "protein_info_with_gene.csv"
        
        # 确保工作目录存在
        if not self.work_dir.exists():
            raise FileNotFoundError(f"工作目录不存在: {self.work_dir}")
        
        # 确保蛋白质信息文件存在
        if not self.protein_info_path.exists():
            raise FileNotFoundError(f"蛋白质信息文件不存在: {self.protein_info_path}")
        
        # 加载蛋白质信息
        self.protein_df = pd.read_csv(self.protein_info_path)
        
    @staticmethod
    def validate_smiles(smiles: str) -> Tuple[bool, Optional[str]]:
        """
        验证SMILES字符串的有效性
        
        Args:
            smiles: SMILES字符串
            
        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误信息)
        """
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return False, "无效的SMILES字符串"
            return True, None
        except Exception as e:
            return False, f"SMILES验证出错: {str(e)}"

    def build_dataset(self, smiles: str, save_path: str) -> Tuple[bool, Optional[str]]:
        """
        构建数据集
        
        Args:
            smiles: 化合物的SMILES字符串
            save_path: 保存路径（相对于工作目录）
            
        Returns:
            Tuple[bool, Optional[str]]: (是否成功, 错误信息)
        """
        # 验证SMILES
        is_valid, error_msg = self.validate_smiles(smiles)
        if not is_valid:
            return False, error_msg

        try:
            # 构建数据集
            dataset = pd.DataFrame({
                'Ingredient_Smile': smiles,
                'Sequence': self.protein_df['sequence'],
                'Gene': self.protein_df['gene'],
                'Protein': self.protein_df['protein']
            })

            # 确保保存路径存在
            save_dir = Path(self.work_dir) / Path(save_path).parent
            save_dir.mkdir(parents=True, exist_ok=True)

            # 保存数据集
            full_save_path = self.work_dir / save_path
            dataset.to_csv(full_save_path, index=False)
            
            return True, None

        except Exception as e:
            return False, f"构建数据集时出错: {str(e)}"
        
    def build_batch_datasets(self, input_file: str, output_dir: str, id_column: str = '编号', 
                            smiles_column: str = 'Smiles格式') -> Tuple[bool, Optional[str], dict]:
        """
        批量构建数据集
        
        Args:
            input_file: 输入文件路径（支持csv格式）
            output_dir: 输出目录路径
            id_column: ID列的名称
            smiles_column: SMILES列的名称
        """
        try:
            # 读取输入文件
            if input_file.endswith('.csv'):
                compounds_df = pd.read_csv(input_file)
            elif input_file.endswith(('.xlsx', '.xls')):
                compounds_df = pd.read_excel(input_file)
            else:
                return False, f"不支持的文件格式: {input_file}", {}
                
            # 检查必要的列是否存在
            if id_column not in compounds_df.columns:
                return False, f"找不到ID列: {id_column}", {}
            if smiles_column not in compounds_df.columns:
                return False, f"找不到SMILES列: {smiles_column}", {}
                
            # 去除SMILES为空的行
            compounds_df = compounds_df.dropna(subset=[smiles_column])
            
            # 确保输出目录存在
            output_path = Path(self.work_dir) / output_dir
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 统计信息
            stats = {
                'total': len(compounds_df),
                'success': 0,
                'failed': 0,
                'failed_compounds': []
            }
            
            # 批量处理每个化合物
            for _, row in compounds_df.iterrows():
                compound_id = str(row[id_column])  # 确保ID为字符串
                smiles = row[smiles_column]
                
                # 验证SMILES
                is_valid, error_msg = self.validate_smiles(smiles)
                if not is_valid:
                    stats['failed'] += 1
                    stats['failed_compounds'].append({
                        'id': compound_id,
                        'error': error_msg
                    })
                    continue
                
                try:
                    # 为每个化合物构建数据集
                    # 每行包含一个蛋白质序列和对应的基因、蛋白质信息
                    dataset = pd.DataFrame({
                        'Ingredient_Smile': [smiles] * len(self.protein_df),  # 重复SMILES以匹配蛋白质数量
                        'Sequence': self.protein_df['sequence'],
                        'Gene': self.protein_df['gene'],
                        'Protein': self.protein_df['protein']
                    })
                    
                    # 保存数据集
                    save_path = output_path / f"{compound_id}.csv"
                    dataset.to_csv(save_path, index=False)
                    stats['success'] += 1
                    
                except Exception as e:
                    stats['failed'] += 1
                    stats['failed_compounds'].append({
                        'id': compound_id,
                        'error': str(e)
                    })
            
            return True, None, stats
            
        except Exception as e:
            return False, f"处理过程中出错: {str(e)}", {}

def main():
    """
    主函数，用于测试
    """
    # 测试用例
    processor = DataProcessor()
    
    # 测试SMILES
    test_smiles = "C=C(CC[C@@H](C(=O)O)C1CC[C@@]2(C)C3=CC[C@H]4C(C)(C)C(OC(C)=O)CC[C@]4(C)C3=CC[C@]12C)C(C)C"
    
    # 验证SMILES
    is_valid, error_msg = processor.validate_smiles(test_smiles)
    if not is_valid:
        print(f"SMILES验证失败: {error_msg}")
        return

    # 构建数据集
    success, error_msg = processor.build_dataset(
        smiles=test_smiles,
        save_path="test/test_compound.csv"
    )
    
    if success:
        print("数据集构建成功！")
    else:
        print(f"数据集构建失败: {error_msg}")

def main():
    """
    主函数，用于测试批量处理功能
    """
    processor = DataProcessor()
    
    # 测试批量构建数据集
    success, error_msg, stats = processor.build_batch_datasets(
        input_file="D:/CurrentProjects/FuLing/茯苓/fuling_final/datasets/zc_output_compounds.csv",
        output_dir="D:/CurrentProjects/FuLing/茯苓/fuling_final/datasets/test",
        id_column="编号",
        smiles_column="Smiles格式"
    )
    
    if success:
        print(f"处理完成！")
        print(f"总计处理: {stats['total']} 个化合物")
        print(f"成功: {stats['success']} 个")
        print(f"失败: {stats['failed']} 个")
        
        if stats['failed'] > 0:
            print("\n失败的化合物:")
            for compound in stats['failed_compounds']:
                print(f"ID: {compound['id']}, 错误: {compound['error']}")
    else:
        print(f"处理失败: {error_msg}")

if __name__ == "__main__":
    main()
