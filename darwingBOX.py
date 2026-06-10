import array
import win32com.client
import pythoncom

def get_cad_application():
    """
    自动兼容获取 AutoCAD 或 ZWCAD 进程
    """
    apps = [
        ("AutoCAD", "AutoCAD.Application"),
        ("ZWCAD", "ZWCAD.Application")
    ]
    
    for name, prog_id in apps:
        try:
            # 尝试获取当前运行的 CAD 实例
            app = win32com.client.GetActiveObject(prog_id)
            print(f"成功连接到 {name} 软件环境。")
            return app
        except Exception:
            continue
            
    raise RuntimeError("未检测到运行中的 AutoCAD 或 ZWCAD，请先打开软件。")

def create_patch_panel_24():
    # 1. 连接 CAD 全局环境
    try:
        cad_app = get_cad_application()
        cad_app.Visible = True
        doc = cad_app.ActiveDocument
        model_space = doc.ModelSpace
        blocks = doc.Blocks
    except Exception as e:
        print(f"连接 CAD 失败: {e}")
        return

    BLOCK_NAME = "Patch_Panel_24"

    # 2. 检查并清理同名块定义（防止重复运行报错）
    try:
        existing_block = blocks.Item(BLOCK_NAME)
        print(f"图块 [{BLOCK_NAME}] 已存在，正在覆盖更新定义...")
        # 注意：生产环境中通常建议重命名或更新，此处演示直接继续添加属性
    except Exception:
        pass

    # 3. 创建块定义 (原点 0, 0, 0)
    origin = array.array('d', [0.0, 0.0, 0.0])
    try:
        pp_block = blocks.Add(origin, BLOCK_NAME)
    except Exception:
        # 如果 Add 报错说明块已存在，直接获取引用
        pp_block = blocks.Item(BLOCK_NAME)

    # 4. 绘制配线架物理外框 (标准1U面板: 482.6mm x 44.45mm)
    # 使用轻量多段线 LWPolyline，需要 2D 坐标数组 [x1, y1, x2, y2, ...]
    width = 482.6
    height = 44.45
    box_points = array.array('d', [
        0.0, 0.0,
        width, 0.0,
        width, height,
        0.0, height,
        0.0, 0.0
    ])
    pp_block.AddLightWeightPolyline(box_points)

    # 5. 定义属性常量
    # acAttributeModeNormal = 1 (可见)
    # acAttributeModeInvisible = 2 (隐藏)
    MODE_VISIBLE = 1
    MODE_INVISIBLE = 2
    text_height_global = 3.5
    text_height_port = 2.5

    # 6. 注入最新的全局属性（资产与合同维度）
    # AddAttribute 参数: (Height, Mode, Prompt, InsertionPoint, Tag, Value)
    pp_block.AddAttribute(text_height_global, MODE_VISIBLE, "设备ID:", array.array('d', [10.0, 55.0, 0.0]), "device_id", "PP-01")
    pp_block.AddAttribute(text_height_global, MODE_VISIBLE, "设备名称:", array.array('d', [10.0, 65.0, 0.0]), "name", "24口网络配线架")
    pp_block.AddAttribute(text_height_global, MODE_VISIBLE, "品牌:", array.array('d', [150.0, 55.0, 0.0]), "brand", "CommScope")
    pp_block.AddAttribute(text_height_global, MODE_VISIBLE, "型号:", array.array('d', [150.0, 65.0, 0.0]), "model", "Cat6-24P")
    pp_block.AddAttribute(text_height_global, MODE_VISIBLE, "合同号:", array.array('d', [300.0, 55.0, 0.0]), "contract_no", "CON-2026-001")

    # 7. 参数化循环生成 24 个端口的几何位置与属性链路
    start_x = 20.0    # 第一个端口起始 X
    port_y = 22.2     # 1U 高度中心线
    gap = 18.5        # 端口网格物理间距

    for i in range(1, 25):
        suffix = f"{i:02d}"  # 格式化为两位数 01, 02 ... 24
        x_pos = start_x + (i - 1) * gap
        
        # 定义当前端口的基准点
        port_pt = array.array('d', [x_pos, port_y, 0.0])
        
        # A. 可见属性：物理端口显示编号
        pp_block.AddAttribute(text_height_port, MODE_VISIBLE, f"端口 {suffix} 编号:", port_pt, f"PORT_NO_{suffix}", suffix)
        
        # B. 隐藏属性：逻辑线缆/通道 ID（解耦中介）
        pp_block.AddAttribute(text_height_port, MODE_INVISIBLE, f"端口 {suffix} 线缆ID:", port_pt, f"CABLE_ID_{suffix}", f"C-{suffix}")
        
        # C. 隐藏属性：物理终端 Handle 强绑定
        pp_block.AddAttribute(text_height_port, MODE_INVISIBLE, f"端口 {suffix} 末端句柄:", port_pt, f"TARGET_HDL_{suffix}", "")

    print(f"成功在数据库中构建智能图块原型 [{BLOCK_NAME}]。")

    # 8. 在当前图纸 ModelSpace 中实例化一个配线架进行测试
    try:
        insert_pt = array.array('d', [100.0, 100.0, 0.0])
        # InsertBlock 参数: (InsertionPoint, Name, Xscale, Yscale, Zscale, Rotation)
        pp_instance = model_space.InsertBlock(insert_pt, BLOCK_NAME, 1.0, 1.0, 1.0, 0.0)
        print("已在坐标 (100, 100) 成功插入配线架图块实例！")
    except Exception as e:
        print(f"实例化图块失败: {e}")

if __name__ == "__main__":
    # 初始化 COM 库
    pythoncom.CoInitialize()
    try:
        create_patch_panel_24()
    finally:
        # 释放 COM 资源
        pythoncom.CoUninitialize()