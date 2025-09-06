import pandas as pd
import numpy as np
import os
import re

def extract_rank_from_partition(partition_str):
    """从分区字符串中提取排名，例如 '4 [625/778]' 返回 625"""
    if pd.isna(partition_str) or partition_str == '':
        return np.nan
    match = re.search(r'\[(\d+)/\d+\]', str(partition_str))
    if match:
        return int(match.group(1))
    return np.nan

def extract_total_from_partition(partition_str):
    """从分区字符串中提取总数，例如 '4 [625/778]' 返回 778"""
    if pd.isna(partition_str) or partition_str == '':
        return np.nan
    match = re.search(r'\[\d+/(\d+)\]', str(partition_str))
    if match:
        return int(match.group(1))
    return np.nan

def extract_zone_from_partition(partition_str):
    """从分区字符串中提取分区，例如 '4 [625/778]' 返回 4"""
    if pd.isna(partition_str) or partition_str == '':
        return np.nan
    match = re.search(r'^(\d+)', str(partition_str))
    if match:
        return int(match.group(1))
    return np.nan

def calculate_authority_level(rank, zone_counts):
    """根据排名和各分区期刊数量计算权威期刊分级"""
    if pd.isna(rank):
        return np.nan
    
    x1, x2, x3, x4 = zone_counts[1], zone_counts[2], zone_counts[3], zone_counts[4]
    
    # 一级权威期刊：1~ x1+x2/2
    if rank <= x1 + x2/2:
        return "一级"
    # 二级权威期刊：x1+x2/2~x1+x2+x3  
    elif rank <= x1 + x2 + x3:
        return "二级"
    # 三级权威期刊：x1+x2+x3~x1+x2+x3+x4
    else:
        return "三级"

def main():
    # 读取两个CSV文件
    print("正在读取CSV文件...")
    
    # 读取分区表格
    fq_df = pd.read_csv('FQBJCR2025-UTF8.csv')
    print(f"已读取分区表格，共 {len(fq_df)} 行")
    
    # 读取影响因子表格
    jcr_df = pd.read_csv('JCR2024-UTF8.csv')
    print(f"已读取影响因子表格，共 {len(jcr_df)} 行")
    
    # 处理ISSN/EISSN列，分离出ISSN和EISSN
    fq_df['ISSN'] = fq_df['ISSN/EISSN'].str.split('/').str[0]
    fq_df['EISSN'] = fq_df['ISSN/EISSN'].str.split('/').str[1]
    
    # 创建ISSN到影响因子的映射
    issn_if_map = {}
    for _, row in jcr_df.iterrows():
        if pd.notna(row['ISSN']):
            issn_if_map[row['ISSN']] = row['IF(2024)']
        if pd.notna(row['eISSN']):
            issn_if_map[row['eISSN']] = row['IF(2024)']
    
    # 添加影响因子列
    fq_df['影响因子'] = fq_df.apply(lambda row: 
        issn_if_map.get(row['ISSN'], issn_if_map.get(row['EISSN'], np.nan)), axis=1)
    
    # 在Web of Science和标注列之间插入影响因子列
    cols = fq_df.columns.tolist()
    ws_index = cols.index('Web of Science')
    # 移除影响因子列（如果已存在）
    if '影响因子' in cols:
        cols.remove('影响因子')
    # 在Web of Science后插入影响因子列
    cols.insert(ws_index + 1, '影响因子')
    fq_df = fq_df[cols]
    
    print(f"成功匹配影响因子 {fq_df['影响因子'].notna().sum()} 个期刊")
    
    # 提取大类分区信息
    fq_df['排名'] = fq_df['大类分区'].apply(extract_rank_from_partition)
    fq_df['总数'] = fq_df['大类分区'].apply(extract_total_from_partition)
    fq_df['分区'] = fq_df['大类分区'].apply(extract_zone_from_partition)
    
    # 按大类处理
    disciplines = fq_df['大类'].unique()
    disciplines = [d for d in disciplines if pd.notna(d)]
    
    # 创建输出目录
    if not os.path.exists('Disciplines'):
        os.makedirs('Disciplines')
    
    all_results = []
    
    for discipline in disciplines:
        print(f"\n处理大类：{discipline}")
        
        # 筛选当前大类的期刊
        discipline_df = fq_df[fq_df['大类'] == discipline].copy()
        total_journals = len(discipline_df)
        print(f"该大类共有 {total_journals} 本期刊")
        
        # 统计各分区期刊数量
        zone_counts = {}
        for zone in [1, 2, 3, 4]:
            zone_counts[zone] = len(discipline_df[discipline_df['分区'] == zone])
        
        print(f"大类分区统计：一区：{zone_counts[1]} 本，二区：{zone_counts[2]} 本，三区：{zone_counts[3]} 本，四区：{zone_counts[4]} 本")
        
        # 计算权威期刊分级
        discipline_df['权威期刊'] = discipline_df['排名'].apply(
            lambda rank: calculate_authority_level(rank, zone_counts)
        )
        
        # 统计权威期刊分级
        authority_counts = {
            '一级': len(discipline_df[discipline_df['权威期刊'] == '一级']),
            '二级': len(discipline_df[discipline_df['权威期刊'] == '二级']),
            '三级': len(discipline_df[discipline_df['权威期刊'] == '三级'])
        }
        
        print(f"权威期刊统计：一级：{authority_counts['一级']} 本，二级：{authority_counts['二级']} 本，三级：{authority_counts['三级']} 本")
        
        # 在Top列和小类1列之间插入权威期刊列
        cols = discipline_df.columns.tolist()
        
        # 先移除权威期刊列（如果存在）
        if '权威期刊' in cols:
            cols.remove('权威期刊')
        
        # 找到Top列和小类1列的位置
        top_index = cols.index('Top')
        xiaolei1_index = cols.index('小类1')
        
        # 在Top列后插入权威期刊列
        cols.insert(top_index + 1, '权威期刊')
        
        # 重新排列DataFrame列顺序
        discipline_df = discipline_df[cols]
        
        # 按排名排序（NaN值放在最后）
        discipline_df_sorted = discipline_df.sort_values('排名', na_position='last')
        
        # 移除临时列
        columns_to_remove = ['ISSN', 'EISSN', '排名', '总数', '分区']
        for col in columns_to_remove:
            if col in discipline_df_sorted.columns:
                discipline_df_sorted = discipline_df_sorted.drop(columns=[col])
        
        # 输出到文件
        output_filename = f'Disciplines/FQBJCR2025-{discipline}-UTF8.csv'
        discipline_df_sorted.to_csv(output_filename, index=False, encoding='utf-8-sig')
        print(f"已输出到：{output_filename}")
        
        # 保存到总结果中
        all_results.append(discipline_df_sorted)
    
    # 合并所有结果并输出总表格
    final_df = pd.concat(all_results, ignore_index=True)
    
    # 确保权威期刊列在正确位置
    cols = final_df.columns.tolist()
    if '权威期刊' in cols:
        cols.remove('权威期刊')
    top_index = cols.index('Top')
    cols.insert(top_index + 1, '权威期刊')
    final_df = final_df[cols]
    
    # 输出最终结果
    final_df.to_csv('FQBJCR2025-QWQKFJ-UTF8.csv', index=False, encoding='utf-8-sig')
    print(f"\n最终结果已输出到：FQBJCR2025-QWQKFJ-UTF8.csv")
    print(f"总共处理了 {len(final_df)} 本期刊，涵盖 {len(disciplines)} 个大类")

if __name__ == "__main__":
    main()