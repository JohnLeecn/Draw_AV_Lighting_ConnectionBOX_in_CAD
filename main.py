"""
main.py
箱盒 CAD 自动绘图系统 - 主程序入口
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import sys

from config import LAYOUT, TEXT_HEIGHT, LAYERS,BOX_HEIGHT
from excel_loader import ExcelLoader
from cad_drawer import CADDrawer
from box_unit import BoxUnit


class BoxDrawerApp:
    """箱盒绘图应用程序"""
    
    def __init__(self):
        """初始化应用程序"""
        self.boxes = []
        self.drawer = CADDrawer()
        self.file_path = None
        self.block_stats = {'success': 0, 'fallback': 0}  # ✅ 确保初始化

    def select_file(self) -> bool:
        """选择 Excel 文件"""
        root = tk.Tk()
        root.withdraw()
        
        file_path = filedialog.askopenfilename(
            title="选择 Excel 文件",
            filetypes=[("Excel 文件", "*.xlsx *.xls")]
        )
        
        if not file_path:
            return False
        
        if not ExcelLoader.validate_file(file_path):
            messagebox.showerror("错误", "Excel 文件格式不正确")
            return False
        
        self.file_path = file_path
        print(f"✓ 选中文件：{file_path}")
        return True

    def load_data(self) -> bool:
        """加载 Excel 数据"""
        if not self.file_path:
            return False
        
        self.boxes = ExcelLoader.load_boxes(self.file_path)
        return len(self.boxes) > 0

    def connect_cad(self) -> bool:
        """连接 AutoCAD"""
        return self.drawer.connect()

    def draw_all(self):
        """绘制所有箱盒"""
        if not self.boxes:
            print("✗ 没有箱盒数据")
            return
        
        # 重置统计
        self.block_stats = {'success': 0, 'fallback': 0}
        
        # 创建图层
        self.drawer.create_all_layers()
        
        # 计算布局
        boxes_per_row = LAYOUT['boxes_per_row']
        spacing_x = LAYOUT['spacing_x']
        spacing_y = LAYOUT['spacing_y']
        start_x = LAYOUT['start_x']
        start_y = LAYOUT['start_y']
        
        print(f"\n开始绘制 {len(self.boxes)} 个箱盒...")
        print("-" * 60)
        
        # 显示箱盒布局统计
        print("📦 箱盒/接线板架构统计:")
        rack_count = 0
        box_count = 0
        for box in self.boxes:
            layout_info = box.get_layout_info()
            if layout_info['type'] == '1U_RACK':
                rack_count += 1
                print(f"   📡 {box.box_id}: {layout_info['total_sockets']}个插座 "
                      f"→ 1U 架构 ({layout_info['num_racks']}个接线板)")
            else:
                box_count += 1
                print(f"   📦 {box.box_id}: {layout_info['total_sockets']}个插座 "
                      f"→ 普通箱盒 ({layout_info['num_rows']}行 × {layout_info['max_per_row']}列)")
        print(f"   合计：1U 架构 {rack_count} 个，普通箱盒 {box_count} 个")
        print("-" * 60)
        
        # 统计使用的块类型
        used_blocks = set()
        
        for i, box in enumerate(self.boxes):
            # 计算位置
            row = i // boxes_per_row
            col = i % boxes_per_row
            pos_x = start_x + col * spacing_x
            pos_y = start_y - row * spacing_y
            
            # 考虑 1U 接线板的高度，调整纵向间距
            if box.use_rack_arch:
                pos_y -= (box.get_total_height() - BOX_HEIGHT) / 2
            
            box.set_position(pos_x, pos_y)
            
            # 绘制外框（箱盒或 1U 接线板）
            corners_list = box.get_box_corners()
            layer_name = LAYERS['rack']['name'] if box.use_rack_arch else LAYERS['box']['name']
            
            for corners in corners_list:
                polyline = self.drawer.draw_polyline(corners, layer_name)
                if box.use_rack_arch:
                    box.cad_rack_entities.append(polyline)
                else:
                    box.cad_box_entity = polyline
            
            # 绘制箱盒编号文字
            text_pos = box.get_text_position()
            text_obj = self.drawer.draw_text(
                box.box_id, 
                text_pos, 
                height=TEXT_HEIGHT,
                layer_name=LAYERS['text']['name']
            )
            box.cad_text_entity = text_obj
            
            # 绘制插座
            for socket in box.cad_ready_sockets:
                sock_pos = box.get_socket_absolute_position(socket)
                used_blocks.add(socket['cad_block'])

                # --- 第一步：绘制开孔 (Hole) ---
                # 放在最前面画，确保它在底层
                hole_entity = None
                if socket.get('hole_block'):
                    hole_entity = self.drawer.draw_hole(
                        block_name=socket['hole_block'],
                        insertion_point=sock_pos,
                        layer_name=LAYERS['hole']['name']  # 使用 HOLE 图层
                    )
                    if hole_entity:
                        box.cad_socket_entities.append(hole_entity) # 也可以单独存一个 list

                # --- 第二步：绘制插座 (Socket) ---
                # 后画，确保它在顶层
                entity = self.drawer.draw_socket(
                    sock_pos,
                    block_name=socket['cad_block'],
                    fallback_radius=12,
                    layer_name=LAYERS['socket']['name']
                )
                
                if entity:
                    try:
                        if entity.ObjectName == "AcDbBlockReference":
                            self.block_stats['success'] += 1
                        else:
                            self.block_stats['fallback'] += 1
                    except:
                        self.block_stats['fallback'] += 1
                    
                    box.cad_socket_entities.append(entity)
                    
                # --- 第三步：绘制编号文字 (Label) ---
                # 文字永远在最上面
                label_pos = box.get_socket_label_position(socket)
                label_text = socket['label_text']  # 如 "MIC1"
                
                self.drawer.draw_socket_label(
                    text=label_text,
                    insertion_point=label_pos,
                    height=2.5,          # 配置中的字高
                    style="Standard",    # 配置中的样式
                    layer_name=LAYERS['text']['name'] # 使用文字图层
                )   
            print(f"  ✓ {box.box_id} - {box.name[:30]}...")
        
        # 显示块使用统计
        print("-" * 60)
        print(f"📊 块使用统计:")
        print(f"   成功插入块：{self.block_stats['success']} 个")
        print(f"   圆圈代替：{self.block_stats['fallback']} 个")
        if used_blocks:
            print(f"   使用的块类型：{', '.join(sorted(used_blocks))}")
        print("-" * 60)
        
        # 缩放视图
        self.drawer.zoom_extents()
        print(f"\n✓ 绘图完成!")

    def save_drawing(self, default_name: str = "箱盒图纸.dwg"):
        """保存图纸"""
        root = tk.Tk()
        root.withdraw()
        
        file_path = filedialog.asksaveasfilename(
            title="保存 CAD 图纸",
            defaultextension=".dwg",
            initialfile=default_name,
            filetypes=[("DWG 文件", "*.dwg")]
        )
        
        if file_path:
            self.drawer.save_as(file_path)

    def run(self):
        """运行完整流程"""
        print("=" * 60)
        print("箱盒 CAD 自动绘图系统")
        print("=" * 60)
        
        # 1. 选择文件
        print("\n[1/4] 选择 Excel 文件...")
        if not self.select_file():
            print("✗ 未选择文件")
            return
        
        # 2. 加载数据
        print("\n[2/4] 加载 Excel 数据...")
        if not self.load_data():
            print("✗ 加载数据失败")
            return
        
        # 3. 连接 CAD
        print("\n[3/4] 连接 AutoCAD...")
        if not self.connect_cad():
            print("✗ 请确保 AutoCAD 已启动")
            return
        
        # 4. 绘图
        print("\n[4/4] 开始绘图...")
        self.draw_all()
        
        # 5. 询问保存
        save = input("\n是否保存图纸？(y/n): ").strip().lower()
        if save == 'y':
            self.save_drawing()
        
        print("\n" + "=" * 60)
        print("程序执行完毕")
        print("=" * 60)


def main():
    """主函数"""
    app = BoxDrawerApp()
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n✗ 用户中断")
    except Exception as e:
        print(f"\n✗ 程序错误：{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()