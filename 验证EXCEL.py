# test_excel_columns.py
import pandas as pd

file_path = input("请输入 Excel 文件路径: ").strip()

try:
    df = pd.read_excel(file_path, sheet_name='Sheet1')
    
    print("\n" + "=" * 60)
    print("Excel 列名检查")
    print("=" * 60)
    print(f"\n所有列名 ({len(df.columns)} 列):")
    for i, col in enumerate(df.columns):
        print(f"  [{i}] '{col}' (长度:{len(col)})")
    
    print("\n" + "=" * 60)
    print("目标列检查")
    print("=" * 60)
    target_cols = ['MADI 底座', 'BNC 底座', '话筒输入', '音箱底座']
    for target in target_cols:
        if target in df.columns:
            print(f"✓ '{target}' 列存在")
            print(f"  示例数据: {df[target].head(3).tolist()}")
        else:
            print(f"✗ '{target}' 列不存在")
            # 查找相似的列名
            similar = [col for col in df.columns if target[:2] in col or target[-2:] in col]
            if similar:
                print(f"  可能相似的列: {similar}")
    
    print("\n" + "=" * 60)
    print("第一行完整数据")
    print("=" * 60)
    for col in df.columns:
        print(f"  {col}: {df.iloc[0][col]}")
        
except Exception as e:
    print(f"错误：{e}")