#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
from functools import partial
import torch
from dgllife.utils import CanonicalAtomFeaturizer, CanonicalBondFeaturizer, smiles_to_bigraph
import pandas as pd
from tqdm import tqdm
from torch import nn
from typing import Tuple, Optional
from api.models import DrugBAN
from api.configs import get_cfg_defaults
from api.utils import integer_label_protein

class DrugPredictor:
    def __init__(self, 
                 model_path: str,
                 device: str = None,
                 max_drug_nodes: int = 290):
        """
        初始化预测器
        
        Args:
            model_path: 模型文件路径
            device: 设备选择 ('cuda:0', 'cuda:1', ..., 'cpu')
            max_drug_nodes: 最大药物节点数
        """
        self.max_drug_nodes = max_drug_nodes
        
        # 设置设备
        if device is None:
            self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
            
        # 初始化特征提取器
        self.atom_featurizer = CanonicalAtomFeaturizer()
        self.bond_featurizer = CanonicalBondFeaturizer(self_loop=True)
        self.fc = partial(smiles_to_bigraph, add_self_loop=True)
        
        # 加载模型
        cfg = get_cfg_defaults()
        self.model = DrugBAN(**cfg)
        
        # 检查模型文件是否存在
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
            
        # 加载模型权重
        self.model.load_state_dict(torch.load(model_path))
        self.model = self.model.to(self.device)
        
    def predict_single(self, smiles: str, protein_seq: str) -> float:
        """
        预测单个SMILES和蛋白质序列的结合概率
        
        Args:
            smiles: SMILES字符串
            protein_seq: 蛋白质序列
            
        Returns:
            float: 预测的结合概率
        """
        # 构建药物图
        drug_graph = self.fc(smiles=smiles, 
                           node_featurizer=self.atom_featurizer, 
                           edge_featurizer=self.bond_featurizer)
        drug_graph = drug_graph.to(self.device)
        
        # 处理节点特征
        actual_node_feats = drug_graph.ndata.pop('h').to(self.device)
        num_actual_nodes = actual_node_feats.shape[0]
        num_virtual_nodes = self.max_drug_nodes - num_actual_nodes
        
        virtual_node_bit = torch.zeros([num_actual_nodes, 1]).to(self.device)
        actual_node_feats = torch.cat((actual_node_feats, virtual_node_bit), 1)
        drug_graph.ndata['h'] = actual_node_feats
        
        virtual_node_feat = torch.cat(
            (torch.zeros(num_virtual_nodes, 74).to(self.device), 
             torch.ones(num_virtual_nodes, 1).to(self.device)), 1)
        drug_graph.add_nodes(num_virtual_nodes, {"h": virtual_node_feat})
        drug_graph = drug_graph.add_self_loop()
        
        # 处理蛋白质序列
        protein_feat = integer_label_protein(protein_seq)
        protein_feat = torch.from_numpy(protein_feat).to(self.device)
        protein_feat = protein_feat.unsqueeze(0)
        
        # 预测
        with torch.no_grad():
            self.model.eval()
            _, _, _, score = self.model(drug_graph, protein_feat)
            prob = nn.Sigmoid()(score)
            
        return prob.item()
    
    def predict_file(self, 
                    input_file: str, 
                    output_file: str,
                    smiles_column: str = 'Ingredient_Smile',
                    sequence_column: str = 'Sequence',
                    gene_column: str = 'Gene',
                    protein_column: str = 'Protein') -> bool:
        """
        预测文件中的所有样本
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            smiles_column: SMILES列名
            sequence_column: 序列列名
            gene_column: 基因列名
            protein_column: 蛋白质列名
            
        Returns:
            bool: 是否成功
        """
        try:
            # 读取数据
            data = pd.read_csv(input_file)
            
            # 检查必要的列是否存在
            required_columns = [smiles_column, sequence_column, gene_column, protein_column]
            for col in required_columns:
                if col not in data.columns:
                    raise ValueError(f"找不到列: {col}")
            
            # 预测结果列表
            results = []
            
            # 批量预测
            for _, row in tqdm(data.iterrows(), total=len(data)):
                score = self.predict_single(row[smiles_column], row[sequence_column])
                results.append({
                    'score': score,
                    'gene': row['Gene'],
                    'protein': row['Protein'],
                    'smiles': row['Ingredient_Smile'],
                    'sequence': row['Sequence'] 
                })
            
            # 保存结果
            result_df = pd.DataFrame(results)
            
            # 确保输出目录存在
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存结果
            result_df.to_csv(output_file, index=False)
            return True
            
        except Exception as e:
            print(f"预测过程中出错: {str(e)}")
            return False

    def predict_batch_datasets(self, 
                         input_dir: str,        
                         output_dir: str,
                         model_path: str = None,
                         device: str = None) -> Tuple[bool, Optional[str], dict]:
        """
        批量预测数据集
        
        Args:
            input_dir: 输入目录路径
            output_dir: 输出目录路径
            model_path: 模型文件路径（可选）
            device: 计算设备（可选）
            
        Returns:
            Tuple[bool, Optional[str], dict]: (是否成功, 错误信息, 处理结果统计)
        """
        try:
            # 检查输入目录是否存在
            input_path = Path(input_dir)
            if not input_path.exists() or not input_path.is_dir():
                return False, f"输入目录不存在: {input_dir}", {}
                
            # 创建输出目录
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 获取输入目录中的所有CSV文件
            csv_files = list(input_path.glob("*.csv"))
            if not csv_files:
                return False, f"目录中没有CSV文件: {input_dir}", {}
                
            # 统计信息
            stats = {
                'total_files': len(csv_files),
                'processed_files': 0,
                'failed_files': [],
                'total_compounds': 0,
                'processed_compounds': 0
            }
            
            # 处理每个文件
            for file_path in tqdm(csv_files, desc="处理文件"):
                try:
                    # 读取数据
                    data = pd.read_csv(file_path)
                    stats['total_compounds'] += len(data)
                    
                    # 检查必要的列是否存在
                    required_columns = ['Ingredient_Smile', 'Sequence', 'Gene', 'Protein']
                    if not all(col in data.columns for col in required_columns):
                        raise ValueError(f"文件缺少必要的列: {file_path}")
                    
                    # 预测结果
                    results = []
                    for _, row in tqdm(data.iterrows(), desc="预测化合物", leave=False):
                        score = self.predict_single(row['Ingredient_Smile'], row['Sequence'])
                        results.append({
                            'score': score,
                            'gene': row['Gene'],
                            'protein': row['Protein'],  # 修复：删除逗号和方括号
                            'smiles': row['Ingredient_Smile'],
                            'sequence': row['Sequence'] 
                        })
                        stats['processed_compounds'] += 1
                    
                    # 保存结果
                    output_file = output_path / f"{file_path.stem}_prediction.csv"
                    result_df = pd.DataFrame(results)
                    result_df.to_csv(output_file, index=False)
                    
                    stats['processed_files'] += 1
                    
                except Exception as e:
                    stats['failed_files'].append({
                        'file': str(file_path),
                        'error': str(e)
                    })
                    continue
            
            return True, None, stats
            
        except Exception as e:
            return False, f"批量预测过程中出错: {str(e)}", {}
        
def main():
    """
    主函数，用于测试批量预测功能
    """
    # 测试参数
    input_dir = "/home/zhengdenggao/drugban_test/datasets/三萜/data"
    output_dir = "/home/zhengdenggao/drugban_test/datasets/三萜/result"
    model_path = "result/best_model_epoch_29.pth"
    device = "cuda:0"
    
    try:
        # 初始化预测器
        predictor = DrugPredictor(
            model_path=model_path,
            device=device
        )
        
        # 执行批量预测
        success, error_msg, stats = predictor.predict_batch_datasets(
            input_dir=input_dir,
            output_dir=output_dir
        )
        
        if success:
            print(f"\n预测完成！")
            print(f"总文件数: {stats['total_files']}")
            print(f"成功处理文件数: {stats['processed_files']}")
            print(f"失败文件数: {len(stats['failed_files'])}")
            print(f"总化合物数: {stats['total_compounds']}")
            print(f"成功预测化合物数: {stats['processed_compounds']}")
            
            if stats['failed_files']:
                print("\n失败的文件:")
                for failed in stats['failed_files']:
                    print(f"文件: {failed['file']}")
                    print(f"错误: {failed['error']}")
                    print()
        else:
            print(f"\n预测失败: {error_msg}")
            
    except Exception as e:
        print(f"\n程序执行出错: {str(e)}")

if __name__ == "__main__":
    main()