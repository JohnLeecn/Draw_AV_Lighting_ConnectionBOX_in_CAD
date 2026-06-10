"""
cad_drawer.py
AutoCAD COM 绘图管理器
"""

import win32com.client
import pythoncom
from typing import List, Tuple, Optional

from variant_utils import (
    create_variant_point, 
    create_variant_points, 
    create_variant_double
)
from config import LAYERS


class CADDrawer:
    """ZWCAD绘图管理器"""
    
    def __init__(self):
        self.acad = None
        self.doc = None
        self.layers = {}
        self.is_connected = False

    def connect(self) -> bool:
        """连接ZWCAD"""
        try:
            pythoncom.CoInitialize()
            self.acad = win32com.client.Dispatch("ZWCAD.Application")
            self.acad.Visible = True
            self.doc = self.acad.ActiveDocument
            self.is_connected = True
            print("✓ 成功连接 ZWCAD")
            return True
        except Exception as e:
            print(f"✗ 连接 ZWCAD 失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        try:
            if self.acad:
                self.acad.Quit()
            self.is_connected = False
            print("✓ 已断开 ZWCAD 连接")
        except:
            pass

    def create_layer(self, layer_name: str, color: int = 7):
        """创建或获取CAD图层"""
        if layer_name not in self.layers:
            try:
                layer = self.doc.Layers.Add(layer_name)
                layer.Color = color
                self.layers[layer_name] = layer
            except Exception as e:
                print(f"  创建图层失败 {layer_name}: {e}")
        return self.layers.get(layer_name)

    def create_all_layers(self):
        """创建所有配置图层"""
        for layer_key, layer_config in LAYERS.items():
            self.create_layer(layer_config['name'], layer_config['color'])
        print(f"✓ 已创建 {len(self.layers)} 个图层")

    def draw_polyline(self, points: List[Tuple[float, float]], 
                      layer_name: str, closed: bool = True):
        """绘制多段线"""
        try:
            variant_points = create_variant_points(points)
            polyline = self.doc.ModelSpace.AddPolyline(variant_points)
            polyline.Layer = layer_name
            polyline.Closed = closed
            return polyline
        except Exception as e:
            print(f"  绘制多段线失败: {e}")
            return None

    def draw_circle(self, center: Tuple[float, float], 
                    radius: float, layer_name: str):
        """绘制圆"""
        try:
            point = create_variant_point(center[0], center[1], 0)
            circle = self.doc.ModelSpace.AddCircle(point, radius)
            circle.Layer = layer_name
            return circle
        except Exception as e:
            print(f"  绘制圆失败: {e}")
            return None

    def draw_text(self, text: str, insertion_point: Tuple[float, float], 
                  height: float = 40, layer_name: str = "0"):
        """绘制文字"""
        try:
            point = create_variant_point(insertion_point[0], insertion_point[1], 0)
            text_obj = self.doc.ModelSpace.AddText(text, point, height)
            text_obj.Layer = layer_name
            return text_obj
        except Exception as e:
            print(f"  绘制文字失败: {e}")
            return None

    def draw_block(self, block_name: str, insertion_point: Tuple[float, float], 
                   scale: float = 1.0, rotation: float = 0.0, 
                   layer_name: str = "0"):
        """插入块"""
        try:
            # 检查块是否存在
            try:
                self.doc.Blocks.Item(block_name)
            except:
                print(f"  警告: 块 '{block_name}' 不存在")
                return None
            
            point = create_variant_point(insertion_point[0], insertion_point[1], 0)
            block_ref = self.doc.ModelSpace.InsertBlock(
                point, block_name, scale, scale, scale, rotation
            )
            block_ref.Layer = layer_name
            return block_ref
        except Exception as e:
            print(f"  插入块失败: {e}")
            return None
    
    def draw_socket(self, sock_pos: Tuple[float, float], 
                    block_name: str, fallback_radius: float = 15,
                    layer_name: str = "ELECTRICAL_SOCKET"):
        """
        绘制插座：优先使用块，块不存在则用圆圈代替
        返回绘制的实体对象
        """
        # 尝试绘制块
        block_ref = self.draw_block(
            block_name, 
            sock_pos, 
            scale=1.0, 
            rotation=0.0, 
            layer_name=layer_name
        )
        
        if block_ref:
            return block_ref  # 块绘制成功
        else:
            # 块不存在，用圆圈代替
            circle = self.draw_circle(sock_pos, fallback_radius, layer_name)
            return circle

    def zoom_extents(self):
        """缩放至范围"""
        try:
            self.doc.Application.ZoomExtents()
        except:
            pass

    def save_as(self, file_path: str):
        """保存图纸"""
        try:
            self.doc.SaveAs(file_path)
            print(f"✓ 图纸已保存: {file_path}")
        except Exception as e:
            print(f"✗ 保存失败: {e}")

    # 在 cad_drawer.py 中添加绘制 1U 接线板的方法        
    def draw_rack_unit(self, corners: List[Tuple[float, float]], layer_name: str):
        """绘制 1U 接线板外框"""
        return self.draw_polyline(corners, layer_name, closed=True)
    #一个专门绘制插座编号的方法。
    def draw_socket_label(self, text: str, insertion_point: Tuple[float, float], 
                          height: float = 2.5, style: str = "Standard", 
                          layer_name: str = "ELECTRICAL_TEXT"):
        """
        绘制插座编号文字
        特性：单行文字，居中对齐，指定样式
        """
        try:
            point = create_variant_point(insertion_point[0], insertion_point[1], 0)
            
            # 添加文字到模型空间
            text_obj = self.doc.ModelSpace.AddText(text, point, height)
            
            # 设置属性
            text_obj.Layer = layer_name
            text_obj.StyleName = style
            text_obj.Alignment = 1  # acAlignmentCenter (居中对齐)
            # 注意：设置 Alignment 后，InsertionPoint 可能需要重新赋值以确保基准点正确
            text_obj.InsertionPoint = point 
            
            return text_obj
        except Exception as e:
            # 如果样式不存在，可能会报错，这里捕获异常并尝试用默认样式
            # print(f"  ⚠ 绘制文字 '{text}' 失败 (样式问题?): {e}")
            try:
                # 重试：不使用特定样式
                text_obj = self.doc.ModelSpace.AddText(text, point, height)
                text_obj.Layer = layer_name
                text_obj.Alignment = 1
                text_obj.InsertionPoint = point
                return text_obj
            except Exception as e2:
                print(f"  ✗ 绘制文字彻底失败: {e2}")
                return None
    
    #增加绘制开孔方法
    def draw_hole(self, block_name: str, insertion_point: Tuple[float, float], 
                  layer_name: str = "ELECTRICAL_HOLE"):
        """
        绘制开孔块
        如果块不存在，可以选择跳过或画一个圆圈示意（这里选择静默跳过，避免图纸杂乱）
        """
        try:
            # 检查块是否存在
            try:
                self.doc.Blocks.Item(block_name)
            except:
                # 开孔块不存在，不绘制，也不报错（因为不是所有插座都有定义好的开孔块）
                return None
            
            point = create_variant_point(insertion_point[0], insertion_point[1], 0)
            block_ref = self.doc.ModelSpace.InsertBlock(
                point, block_name, 1.0, 1.0, 1.0, 0.0
            )
            block_ref.Layer = layer_name
            return block_ref
        except Exception as e:
            # print(f"  ⚠ 绘制开孔 {block_name} 失败：{e}")
            return None    