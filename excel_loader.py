"""
excel_loader.py
Excel数据加载器
"""

import pandas as pd
from typing import List, Optional
from box_unit import BoxUnit


class ExcelLoader:
    """Excel数据加载器"""
    
    @staticmethod
    def load_boxes(file_path: str, sheet_name: str = 'Sheet1') -> List[BoxUnit]:
        """从Excel加载箱盒数据"""
        try:
            # 读取Excel
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # 预处理：将接口列转换为整数
            int_columns = [
                '话筒输入', '线路输出', '音箱底座', '网络底座',
                '多模光纤底座', '单模光纤底座', 'MADI底座', 'BNC底座'
            ]
            
            for col in int_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            
            # 创建箱盒对象列表
            box_list = []
            for index, row in df.iterrows():
                box = BoxUnit(row)
                box_list.append(box)
            
            print(f"✓ 成功加载 {len(box_list)} 个箱盒")
            return box_list
            
        except FileNotFoundError:
            print(f"✗ 文件不存在: {file_path}")
            return []
        except Exception as e:
            print(f"✗ 加载Excel失败: {e}")
            return []

    @staticmethod
    def load_socket_mapping(file_path: str, 
                            sheet_name: str = 'Sheet2') -> dict:
        """从Sheet2加载接口类型映射（可选功能）"""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            mapping = {}
            for _, row in df.iterrows():
                excel_name = row.get('接口类型', '')
                cad_block = row.get('CAD块名', '')
                if excel_name and cad_block:
                    mapping[str(excel_name)] = str(cad_block)
            return mapping
        except:
            return {}

    @staticmethod
    def validate_file(file_path: str) -> bool:
        """验证Excel文件格式"""
        try:
            df = pd.read_excel(file_path, sheet_name='Sheet1')
            required_columns = ['名称', '箱盒编号']
            for col in required_columns:
                if col not in df.columns:
                    print(f"✗ 缺少必需列: {col}")
                    return False
            return True
        except Exception as e:
            print(f"✗ 文件验证失败: {e}")
            return False