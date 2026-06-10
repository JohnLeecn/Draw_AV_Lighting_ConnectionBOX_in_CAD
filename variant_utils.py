'''
箱盒自动绘制/
├── main.py                 # 主程序入口
├── box_unit.py             # 箱盒对象类
├── cad_drawer.py           # CAD绘图管理器
├── excel_loader.py         # Excel数据加载器
├── variant_utils.py        # COM VARIANT辅助函数
├── config.py               # 配置文件
└── requirements.txt        # 依赖清单
'''

"""
variant_utils.py
COM VARIANT 数据类型辅助函数
"""

import win32com.client
import pythoncom


def create_variant_point(x, y, z=0):
    """创建COM兼容的3D点VARIANT"""
    return win32com.client.VARIANT(
        pythoncom.VT_ARRAY | pythoncom.VT_R8, 
        (x, y, z)
    )


def create_variant_points(points):
    """创建COM兼容的多点VARIANT数组"""
    flat_points = []
    for point in points:
        flat_points.extend([point[0], point[1], 0])
    return win32com.client.VARIANT(
        pythoncom.VT_ARRAY | pythoncom.VT_R8, 
        flat_points
    )


def create_variant_double(value):
    """创建COM兼容的双精度VARIANT"""
    return win32com.client.VARIANT(pythoncom.VT_R8, value)


def create_variant_string(value):
    """创建COM兼容的字符串VARIANT"""
    return win32com.client.VARIANT(pythoncom.VT_BSTR, str(value))