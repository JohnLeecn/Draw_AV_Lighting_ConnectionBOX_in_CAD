"""
box_unit.py
箱盒对象类 - 储存 Excel 数据并为 CAD 绘图做准备
"""

import pandas as pd
import numpy as np
import math
from typing import List, Dict, Any, Tuple, Optional

from config import (
    BOX_WIDTH, BOX_HEIGHT, 
    SOCKET_SPACING_X, SOCKET_SPACING_Y, SOCKET_MARGIN,
    SOCKET_TYPE_MAP,
    # 1U 架构配置
    RACK_1U_WIDTH, RACK_1U_HEIGHT,
    RACK_SOCKET_SPACING_X, RACK_SOCKET_FIRST_X,
    RACK_SOCKETS_PER_ROW, SOCKET_THRESHOLD,SOCKET_RADIUS,SOCKET_PREFIX_MAP, 
    SOCKET_LABEL_OFFSET_Y,
    SOCKET_HOLE_MAP
)


class BoxUnit:
    """箱盒对象类"""
    
    def __init__(self, row_data: pd.Series):
        """初始化箱盒对象"""
        # --- 基础身份信息 ---
        self.name = str(row_data.get('名称', '') or '')
        self.box_id = str(row_data.get('箱盒编号', '') or '')
        
        # --- 接口数量统计 ---
        self.interfaces = self._parse_interfaces(row_data)
        
        # --- 计算插座总数 ---
        self.total_sockets = sum(self.interfaces.values())
        
        # --- 判断使用哪种架构 ---
        self.use_rack_arch = self.total_sockets > SOCKET_THRESHOLD
        
        # --- CAD 绘图属性 ---
        self.insert_point: Tuple[float, float] = (0.0, 0.0)
        self.rotation_angle: float = 0.0
        self.layer_name: str = "ELECTRICAL_RACK" if self.use_rack_arch else "ELECTRICAL_BOX"
        self.block_name: str = f"BOX_{self._sanitize_id(self.box_id)}"
        
        # --- 插座列表 ---
        self.cad_ready_sockets: List[Dict[str, Any]] = []
        
        # --- 1U 接线板列表 ---
        self.rack_units: List[Dict[str, Any]] = []
        
        # --- CAD 实体引用 ---
        self.cad_box_entity = None
        self.cad_rack_entities: List = []
        self.cad_socket_entities: List = []
        self.cad_text_entity = None
        
        # --- 映射 CAD 块名称并计算位置 ---
        self.map_socket_types(SOCKET_TYPE_MAP)

    def _sanitize_id(self, box_id: str) -> str:
        return box_id.replace('.', '_').replace('-', '_').replace(' ', '_')

    def _parse_interfaces(self, row_data: pd.Series) -> Dict[str, int]:
        def safe_int(value):
            if pd.isna(value) or value is None:
                return 0
            try:
                return int(float(value))
            except (ValueError, TypeError):
                return 0
        
        return {
            '话筒输入': safe_int(row_data.get('话筒输入')),
            '线路输出': safe_int(row_data.get('线路输出')),
            '音箱底座': safe_int(row_data.get('音箱底座')),
            '网络底座': safe_int(row_data.get('网络底座')),
            '多模光纤底座': safe_int(row_data.get('多模光纤底座')),
            '单模光纤底座': safe_int(row_data.get('单模光纤底座')),
            'MADI底座': safe_int(row_data.get('MADI底座')),
            'BNC底座': safe_int(row_data.get('BNC底座')),
        }

    
    def map_socket_types(self, socket_mapping: Dict[str, str]):
        """将接口类型映射为 CAD 块名称并生成编号"""
        self.cad_ready_sockets = []
        
        # 用于统计每种类型的当前数量，以便生成 MIC1, MIC2...
        type_counters = {}
        
        for iface_type, count in self.interfaces.items():
            if count > 0:
                cad_block = socket_mapping.get(iface_type, f"Generic_{iface_type}")
                prefix = SOCKET_PREFIX_MAP.get(iface_type, "UNK")  # 获取前缀，如 'MIC'

                # ✅ 获取对应的开孔块名
                hole_block = SOCKET_HOLE_MAP.get(cad_block, None)
                # 如果映射表中没有，尝试用通用规则或直接设为 None
                # 初始化计数器
                if hole_block is None:
                    # 可选：如果没有定义开孔，可以选择不画或者画一个默认孔
                    # 这里设为 None，绘图时会跳过
                    pass


                if iface_type not in type_counters:
                    type_counters[iface_type] = 0
                
                for i in range(count):
                    type_counters[iface_type] += 1
                    current_num = type_counters[iface_type]
                    
                    socket_info = {
                        'original_type': iface_type, # 
                        'cad_block': cad_block,
                        'hole_block': hole_block,  # ✅ 存储开孔块名
                        'index': i + 1,
                        'label_text': f"{prefix}{current_num}",  # ✅ 生成编号，如 MIC1
                        'offset_x': 0.0,
                        'offset_y': 0.0,
                        'rack_index': 0,
                        'row': 0,
                        'col': 0,
                    }
                    self.cad_ready_sockets.append(socket_info)
        
        if self.use_rack_arch:
            self._calculate_rack_positions()
        else:
            self._calculate_box_positions()

    def _calculate_box_positions(self):
        """普通箱盒架构：支持独立的横向/纵向间距"""
        total_sockets = len(self.cad_ready_sockets)
        if total_sockets == 0:
            return
        
        # 1. 计算每行最多能放多少个插座 (基于横向间距)
        usable_width = BOX_WIDTH - 2 * SOCKET_MARGIN
        max_per_row = max(1, int((usable_width + SOCKET_SPACING_X) / SOCKET_SPACING_X))
        
        # 2. 计算需要多少行
        num_rows = math.ceil(total_sockets / max_per_row)
        
        # 3. 计算纵向总高度，判断是否需要压缩纵向间距
        total_height_needed = (num_rows - 1) * SOCKET_SPACING_Y + SOCKET_RADIUS * 2 # 简单估算
        usable_height = BOX_HEIGHT - 2 * SOCKET_MARGIN
        
        # 如果高度不够且有多行，则动态压缩纵向间距
        if num_rows > 1 and total_height_needed > usable_height:
            # 重新计算可用的最大纵向间距
            # 总可用高度 = (行数-1)*间距 + 直径 (假设首尾各留半个直径空间，这里简化为总间距)
            # 更精确的算法：(usable_height) / (num_rows) 作为行高，间距 = 行高
            row_spacing = usable_height / num_rows
        else:
            row_spacing = SOCKET_SPACING_Y
        
        # 4. 计算起始位置（居中）
        # 实际占用的总宽度
        actual_width = (min(total_sockets, max_per_row) - 1) * SOCKET_SPACING_X
        start_x = -actual_width / 2
        
        # 实际占用的总高度
        actual_height = (num_rows - 1) * row_spacing
        start_y = actual_height / 2
        
        # 5. 分配坐标
        for i, socket in enumerate(self.cad_ready_sockets):
            row = i // max_per_row
            col = i % max_per_row
            
            socket['offset_x'] = start_x + col * SOCKET_SPACING_X
            socket['offset_y'] = start_y - row * row_spacing
            socket['row'] = row
            socket['col'] = col

    def _calculate_rack_positions(self):
        """1U 接线板架构"""
        total_sockets = len(self.cad_ready_sockets)
        if total_sockets == 0:
            return
        
        num_racks = math.ceil(total_sockets / RACK_SOCKETS_PER_ROW)
        
        self.rack_units = []
        for i in range(num_racks):
            rack_info = {
                'index': i,
                'height_y': -i * RACK_1U_HEIGHT,
                'sockets_in_rack': 0,
            }
            self.rack_units.append(rack_info)
        
        for i, socket in enumerate(self.cad_ready_sockets):
            rack_index = i // RACK_SOCKETS_PER_ROW
            socket_in_rack = i % RACK_SOCKETS_PER_ROW
            
            socket['rack_index'] = rack_index
            # 使用配置的横向间距
            socket['offset_x'] = -(RACK_1U_WIDTH / 2) + RACK_SOCKET_FIRST_X + socket_in_rack * RACK_SOCKET_SPACING_X
            socket['offset_y'] = -rack_index * RACK_1U_HEIGHT
            
            self.rack_units[rack_index]['sockets_in_rack'] += 1
            socket['row'] = rack_index
            socket['col'] = socket_in_rack

    def set_position(self, x: float, y: float, rotation: float = 0.0):
        self.insert_point = (x, y)
        self.rotation_angle = rotation

    def get_box_corners(self) -> List[List[Tuple[float, float]]]:
        x, y = self.insert_point
        
        if self.use_rack_arch:
            all_corners = []
            for i, rack in enumerate(self.rack_units):
                rack_y = y + rack['height_y']
                half_w = RACK_1U_WIDTH / 2
                half_h = RACK_1U_HEIGHT / 2
                
                corners = [
                    (x - half_w, rack_y - half_h),
                    (x + half_w, rack_y - half_h),
                    (x + half_w, rack_y + half_h),
                    (x - half_w, rack_y + half_h),
                    (x - half_w, rack_y - half_h),
                ]
                all_corners.append(corners)
            return all_corners
        else:
            half_w, half_h = BOX_WIDTH / 2, BOX_HEIGHT / 2
            corners = [
                (x - half_w, y - half_h),
                (x + half_w, y - half_h),
                (x + half_w, y + half_h),
                (x - half_w, y + half_h),
                (x - half_w, y - half_h),
            ]
            return [corners]

    def get_socket_absolute_position(self, socket: Dict[str, Any]) -> Tuple[float, float]:
        base_x = self.insert_point[0] + socket['offset_x']
        base_y = self.insert_point[1] + socket['offset_y']
        
        if self.rotation_angle != 0:
            rad = math.radians(self.rotation_angle)
            dx = base_x - self.insert_point[0]
            dy = base_y - self.insert_point[1]
            base_x = self.insert_point[0] + dx * math.cos(rad) - dy * math.sin(rad)
            base_y = self.insert_point[1] + dx * math.sin(rad) + dy * math.cos(rad)
        
        return (base_x, base_y)

    def get_text_position(self) -> Tuple[float, float]:
        from config import TEXT_OFFSET_Y
        
        if self.use_rack_arch:
            return (
                self.insert_point[0], 
                self.insert_point[1] + RACK_1U_HEIGHT / 2 + TEXT_OFFSET_Y
            )
        else:
            return (
                self.insert_point[0], 
                self.insert_point[1] + BOX_HEIGHT / 2 + TEXT_OFFSET_Y
            )

    def get_total_height(self) -> float:
        if self.use_rack_arch:
            return len(self.rack_units) * RACK_1U_HEIGHT
        else:
            return BOX_HEIGHT

    def get_total_width(self) -> float:
        if self.use_rack_arch:
            return RACK_1U_WIDTH
        else:
            return BOX_WIDTH

    def get_layout_info(self) -> Dict[str, Any]:
        if self.use_rack_arch:
            return {
                'type': '1U_RACK',
                'total_sockets': self.total_sockets,
                'num_racks': len(self.rack_units),
                'sockets_per_rack': RACK_SOCKETS_PER_ROW,
                'total_height': self.get_total_height(),
                'width': RACK_1U_WIDTH,
            }
        else:
            total_sockets = len(self.cad_ready_sockets)
            if total_sockets == 0:
                return {'type': 'BOX', 'rows': 0, 'cols': 0, 'total_height': BOX_HEIGHT, 'width': BOX_WIDTH}
            
            usable_width = BOX_WIDTH - 2 * SOCKET_MARGIN
            max_per_row = max(1, int((usable_width + SOCKET_SPACING_X) / SOCKET_SPACING_X))
            num_rows = math.ceil(total_sockets / max_per_row)
            
            return {
                'type': 'BOX',
                'total_sockets': total_sockets,
                'max_per_row': max_per_row,
                'num_rows': num_rows,
                'total_height': self.get_total_height(),
                'width': BOX_WIDTH,
            }

    def __repr__(self):
        arch_type = "1U_RACK" if self.use_rack_arch else "BOX"
        return f"<BoxUnit: {self.box_id} - {arch_type} - 接口数:{self.total_sockets}>"
    
    def get_socket_label_position(self, socket: Dict[str, Any]) -> Tuple[float, float]:
        """计算插座编号文字的绝对坐标 (中心上方 18mm)"""
        # 获取插座中心坐标
        center_x, center_y = self.get_socket_absolute_position(socket)
        
        # 应用旋转 (如果箱盒有旋转角度，文字也需要跟着旋转计算位置)
        # 简单处理：直接在 Y 轴方向偏移，若需严格跟随旋转可在此处增加旋转矩阵计算
        # 这里假设文字始终相对于世界坐标系的 Y 轴向上，或者跟随块旋转
        # 为了简单且符合通常制图习惯，我们直接在世界坐标 Y+18 处放置
        # 如果需要文字随块旋转，逻辑会复杂一些，目前按“上方”理解为世界坐标 Y 轴正向
        
        label_x = center_x
        label_y = center_y + SOCKET_LABEL_OFFSET_Y
        
        # 如果箱盒整体旋转了，插座的相对位置已经通过 get_socket_absolute_position 计算过了
        # 但“上方”这个概念如果是相对于箱盒本身的，则需要额外旋转计算。
        # 通常电气图纸中，文字是水平阅读的，所以直接 +Y 即可。
        # 如果您希望文字随箱盒旋转（即永远在插座的“物理上方”），请取消下面注释：
        """
        if self.rotation_angle != 0:
            rad = math.radians(self.rotation_angle)
            dx = 0
            dy = SOCKET_LABEL_OFFSET_Y
            label_x = center_x + dx * math.cos(rad) - dy * math.sin(rad)
            label_y = center_y + dx * math.sin(rad) + dy * math.cos(rad)
        """
        
        return (label_x, label_y)