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
config.py
全局配置文件
"""
"""
config.py
全局配置文件
"""
# ==================== 盲板层优先级与合并配置 ====================
# 优先级数字越小越先处理
SOCKET_LAYER_PRIORITY = {
    'PoweConXX底座': 1,
    '16A技术电源底座': 1,
    '话筒输入': 2,
    '线路输出': 3,
    '音箱底座': 4,
    '网络底座': 5,
    '多模光纤底座': 5,
    '单模光纤底座': 5,
    'MADI底座': 6,
    '视频BNC底座': 6,
    # 其他默认优先级 99
}

# 是否允许合并到其他行（True表示该类型插座可以塞入已有行）
SOCKET_MERGE_ALLOWED = {
    'PoweConXX底座': False,   # 强电不合并，必须独占新行
    '16A技术电源底座': False,
    '话筒输入': False,        # 话筒一般占独立行
    '线路输出': True,         # 线路可以合并到话筒行
    '音箱底座': True,
    '网络底座': True,
    '多模光纤底座': True,
    '单模光纤底座': True,
    'MADI底座': True,
    '视频BNC底座': True,
}

# 每种类型最多占用独立行数（0表示不限制，1表示最多占1行，多余必须合并）
SOCKET_MAX_OWN_ROWS = {
    '话筒输入': 1,
    '线路输出': 1,
    '音箱底座': 0,    # 不独立成行，总是合并
    '网络底座': 1,
    '多模光纤底座': 1,
    '单模光纤底座': 1,
    'MADI底座': 1,
    '视频BNC底座': 1,
    'PoweConXX底座': 1,
    '16A技术电源底座': 1,
}

# 布局参数
BLIND_PANEL_SPACING_X_MIN = 28      # 最小水平间距 (mm)，当数量多时可压缩
BLIND_PANEL_SPACING_X_DEFAULT = 36  # 默认水平间距
BLIND_PANEL_SPACING_Y = 50          # 垂直行间距 (2U时两行中心距)
BLIND_PANEL_MARGIN_LEFT = 36        # 左边距
BLIND_PANEL_MARGIN_RIGHT = 36       # 右边距（自动计算）



# ==================== 箱盒尺寸配置 ====================
BOX_WIDTH = 300       # 普通箱盒宽度 (mm)
BOX_HEIGHT = 200      # 普通箱盒高度 (mm)

# ==================== 1U 接线板配置 ====================
RACK_1U_WIDTH = 483       # 1U 接线板宽度 (mm) - 标准 19 英寸机架
RACK_1U_HEIGHT = 44.5     # 1U 接线板高度 (mm)
RACK_SOCKET_SPACING_X = 36  # 1U 插座水平间距 (mm)
RACK_SOCKET_FIRST_X = 43.5  # 第一个插座距离左侧距离 (mm)
RACK_SOCKETS_PER_ROW = 12   # 每行最多插座数量
SOCKET_THRESHOLD = 20       # 切换到 1U 架构的插座数量阈值

# ==================== 2U 接线板配置 ====================
RACK_2U_WIDTH = 483       # 1U 接线板宽度 (mm) - 标准 19 英寸机架
RACK_2U_HEIGHT = 89     # 1U 接线板高度 (mm)
RACK_SOCKET_SPACING_X = 36  # 1U 插座水平间距 (mm)
RACK_SOCKET_FIRST_X = 43.5  # 第一个插座距离左侧距离 (mm)
RACK_SOCKETS_PER_ROW = 12   # 每行最多插座数量
SOCKET_THRESHOLD = 20       # 切换到 1U 架构的插座数量阈值

# ==================== 普通箱盒插座排列配置 ====================
SOCKET_SPACING_X = 36   # 普通箱盒插座【横向】间距 (mm)
SOCKET_SPACING_Y = 55   # 普通箱盒插座【纵向】间距 (mm)
SOCKET_MARGIN = 25      # 普通箱盒插座距离边缘距离 (mm)
SOCKET_RADIUS = 12      # 插座圆圈半径 (mm)

# ==================== CAD图层配置 ====================
LAYERS = {
    'box': {'name': 'ELECTRICAL_BOX', 'color': 3},       # 绿色
    'rack': {'name': 'ELECTRICAL_RACK', 'color': 4},     # 青色 (1U 接线板)
    'socket': {'name': 'ELECTRICAL_SOCKET', 'color': 7}, # 红色
    'text': {'name': 'ELECTRICAL_TEXT', 'color': 7},     # 白色
    'dimension': {'name': 'ELECTRICAL_DIM', 'color': 6}, # 青色
    'hole': {'name': 'ELECTRICAL_HOLE', 'color': 8},     # 灰色 (开孔，新增)
}

# ==================== 接口类型映射 ====================
SOCKET_TYPE_MAP = {
    '话筒输入': 'Socket_XLR3F',
    '线路输出': 'Socket_XLR3M',
    '音箱底座': 'Socket_NL4M',
    '网络底座': 'Socket_CAT5E',
    '多模光纤底座': 'Socket_FO',
    '单模光纤底座': 'Socket_FO',
    'MADI底座': 'Socket_BNC',
    'BNC底座': 'Socket_BNC',
    'PoweConXX底座': 'Socket_POWERCON_20A',
    '16A技术电源底座': 'Socket_TechPOWER_16A',
}

# 键：插座块名，值：对应的开孔块名
SOCKET_HOLE_MAP = {
    'Socket_XLR3F': 'Socket_Hole_D_type',
    'Socket_XLR3M': 'Socket_Hole_D_type',
    'Socket_XLR5F': 'Socket_Hole_D_type',
    'Socket_XLR5F_INTERNAL': 'Socket_Hole_D_type',
    'Socket_NL4M': 'Socket_Hole_D_type',     
    'Socket_CAT5E': 'Socket_Hole_D_type',
    'Socket_CAT6A': 'Socket_Hole_D_type',
    'Socket_BNC': 'Socket_Hole_D_type',
    'Socket_FO': 'Socket_Hole_D_type',        # 单孔光纤
    'Socket_FO_MM': 'Socket_Hole_D_type',     # 兼容之前的配置
    'Socket_FO_SM': 'Socket_Hole_D_type',     # 兼容之前的配置
    'Socket_FO_DUPLEX': 'Socket_Hole_FO_DUPLEX', # 双孔光纤专用开孔
    'Socket_HDMI': 'Socket_Hole_D_type',      # 假设 HDMI 也用 D 型孔，如有专用请修改
    'Socket_POWERCON_20A': 'Socket_Hole_TYP1609B_10A',
    'Socket_TechPOWER_16': 'Socket_Hole_SCHUKO_16A',

}

# ==================== 绘图布局配置 ====================
LAYOUT = {
    'boxes_per_row': 5,      # 每行箱盒数量
    'spacing_x': 600,        # 箱盒横向间距 (mm)
    'spacing_y': 500,        # 箱盒纵向间距 (mm)
    'start_x': 0,            # 起始 X 坐标
    'start_y': 0,            # 起始 Y 坐标
}

# ==================== 文字配置 ====================
TEXT_HEIGHT = 40            # 文字高度 (mm)
TEXT_OFFSET_Y = 30          # 文字距离箱盒顶部偏移 (mm)


# ==================== 插座编号配置 ====================
# 接口类型 -> 编号前缀映射
SOCKET_PREFIX_MAP = {
    '话筒输入': 'MIC',
    '线路输出': 'CH',
    '音箱底座': 'SPK',
    '网络底座': 'NET',
    '多模光纤底座': 'OM',
    '单模光纤底座': 'OS',
    'MADI底座': 'MADI',
    'BNC底座': 'SDI',
    'PoweConXX底座': 'WSP',
    '16A技术电源底座': 'WP',
}

# 插座编号文字样式
SOCKET_LABEL_HEIGHT = 5       # 字高 (mm)
SOCKET_LABEL_OFFSET_Y = 18.0    # 距离插座中心向上的偏移 (mm)
SOCKET_LABEL_STYLE = "Standard" # 文字样式