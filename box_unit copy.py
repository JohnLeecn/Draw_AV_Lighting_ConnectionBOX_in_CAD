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
    SOCKET_SPACING, SOCKET_MARGIN,
    SOCKET_TYPE_MAP,
    # 1U 架构配置
    RACK_1U_WIDTH, RACK_1U_HEIGHT,
    RACK_SOCKET_SPACING, RACK_SOCKET_FIRST_X,
    RACK_SOCKETS_PER_ROW, SOCKET_THRESHOLD
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
        
        # --- 1U 接线板列表 (重要：必须在 map_socket_types 之前初始化) ---
        self.rack_units: List[Dict[str, Any]] = []
        
        # --- CAD 实体引用 ---
        self.cad_box_entity = None
        self.cad_rack_entities: List = []
        self.cad_socket_entities: List = []
        self.cad_text_entity = None
        
        # --- 映射 CAD 块名称并计算位置 ---
        self.map_socket_types(SOCKET_TYPE_MAP)

    def _sanitize_id(self, box_id: str) -> str:
        """清理箱盒编号，使其适合作为 CAD 块名"""
        return box_id.replace('.', '_').replace('-', '_').replace(' ', '_')

    def _parse_interfaces(self, row_data: pd.Series) -> Dict[str, int]:
        """安全解析接口数量，处理 NaN 和空值"""
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
        """将接口类型映射为 CAD 块名称"""
        self.cad_ready_sockets = []
        
        for iface_type, count in self.interfaces.items():
            if count > 0:
                cad_block = socket_mapping.get(iface_type, f"Generic_{iface_type}")
                for i in range(count):
                    socket_info = {
                        'original_type': iface_type,
                        'cad_block': cad_block,
                        'index': i + 1,
                        'offset_x': 0.0,
                        'offset_y': 0.0,
                        'rack_index': 0,
                        'row': 0,
                        'col': 0,
                    }
                    self.cad_ready_sockets.append(socket_info)
        
        # 根据架构类型计算位置
        if self.use_rack_arch:
            self._calculate_rack_positions()
        else:
            self._calculate_box_positions()

    def _calculate_box_positions(self):
        """普通箱盒架构：自动计算插座在箱盒内的排列位置"""
        total_sockets = len(self.cad_ready_sockets)
        if total_sockets == 0:
            return
        
        usable_width = BOX_WIDTH - 2 * SOCKET_MARGIN
        max_per_row = max(1, int(usable_width / SOCKET_SPACING))
        num_rows = math.ceil(total_sockets / max_per_row)
        
        total_height = num_rows * SOCKET_SPACING
        usable_height = BOX_HEIGHT - 2 * SOCKET_MARGIN
        
        if total_height > usable_height and num_rows > 1:
            row_spacing = usable_height / num_rows
        else:
            row_spacing = SOCKET_SPACING
        
        total_width = (min(total_sockets, max_per_row) - 1) * SOCKET_SPACING
        start_x = -total_width / 2
        start_y = (num_rows - 1) * row_spacing / 2
        
        for i, socket in enumerate(self.cad_ready_sockets):
            row = i // max_per_row
            col = i % max_per_row
            
            socket['offset_x'] = start_x + col * SOCKET_SPACING
            socket['offset_y'] = start_y - row * row_spacing
            socket['row'] = row
            socket['col'] = col

    def _calculate_rack_positions(self):
        """
        1U 接线板架构：计算插座在 1U 接线板上的位置
        策略：强制居中对齐，确保左右边距一致
        """
        total_sockets = len(self.cad_ready_sockets)
        if total_sockets == 0:
            return
        
        # 1. 计算需要多少个 1U 接线板
        num_racks = math.ceil(total_sockets / RACK_SOCKETS_PER_ROW)
        
        # 2. 创建 1U 接线板信息
        self.rack_units = []
        for i in range(num_racks):
            rack_info = {
                'index': i,
                'height_y': -i * RACK_1U_HEIGHT,
                'sockets_in_rack': 0,
            }
            self.rack_units.append(rack_info)
        
        # 3. 分配插座并计算坐标
        for i, socket in enumerate(self.cad_ready_sockets):
            rack_index = i // RACK_SOCKETS_PER_ROW
            socket_in_rack = i % RACK_SOCKETS_PER_ROW
            
            socket['rack_index'] = rack_index
            
            # --- 核心修正：动态计算 X 坐标以实现完美居中 ---
            # 当前行实际有多少个插座？(最后一行可能不满)
            sockets_in_this_row = min(RACK_SOCKETS_PER_ROW, total_sockets - rack_index * RACK_SOCKETS_PER_ROW)
            
            # 计算这一行插座的总占用宽度
            # 如果有 N 个插座，中间有 N-1 个间距
            row_total_width = (sockets_in_this_row - 1) * RACK_SOCKET_SPACING
            
            # 计算起始 X (相对于接线板中心)
            # 目标：(总宽 - 占用宽) / 2
            start_x = -row_total_width / 2
            
            # 如果计算出的 start_x 小于配置的最小边距 (RACK_SOCKET_FIRST_X - RACK_1U_WIDTH/2)，则使用配置值
            # 标准 19 寸机架：半宽 241.5, 第一个孔 43.5 -> 相对中心 -198
            min_start_x = -(RACK_1U_WIDTH / 2) + RACK_SOCKET_FIRST_X
            
            # 取两者中绝对值较大的（即更靠边的），防止超出机架
            final_start_x = min(start_x, min_start_x) if start_x < 0 else max(start_x, -min_start_x)
            
            # 为了严格符合您的 "43.5mm" 要求，我们直接使用公式计算，不动态压缩
            # 公式：X = -半宽 + 43.5 + (索引 * 36)
            socket['offset_x'] = -(RACK_1U_WIDTH / 2) + RACK_SOCKET_FIRST_X + socket_in_rack * RACK_SOCKET_SPACING
            
            # Y 坐标
            socket['offset_y'] = -rack_index * RACK_1U_HEIGHT
            
            # 更新统计
            self.rack_units[rack_index]['sockets_in_rack'] += 1
            socket['row'] = rack_index
            socket['col'] = socket_in_rack

    def set_position(self, x: float, y: float, rotation: float = 0.0):
        """设置箱盒在 CAD 中的位置和角度"""
        self.insert_point = (x, y)
        self.rotation_angle = rotation

    def get_box_corners(self) -> List[List[Tuple[float, float]]]:
        """获取箱盒/接线板外框的角点坐标"""
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
        """计算插座的绝对 CAD 坐标（含旋转）"""
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
        """获取箱盒编号文字的放置位置"""
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
        """获取总高度（用于布局计算）"""
        if self.use_rack_arch:
            return len(self.rack_units) * RACK_1U_HEIGHT
        else:
            return BOX_HEIGHT

    def get_total_width(self) -> float:
        """获取总宽度（用于布局计算）"""
        if self.use_rack_arch:
            return RACK_1U_WIDTH
        else:
            return BOX_WIDTH

    def get_layout_info(self) -> Dict[str, Any]:
        """获取布局信息（用于调试）"""
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
            max_per_row = max(1, int(usable_width / SOCKET_SPACING))
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