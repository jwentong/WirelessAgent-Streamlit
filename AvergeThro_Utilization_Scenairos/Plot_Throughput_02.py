import matplotlib.pyplot as plt

x = [1, 5, 10, 15, 20, 25, 30]
Y_rule_thro = [66.06, 415.76, 996.96, 1062.24, 1093.92, 1093.92, 1093.92]
Y_llm_thro = [66.06, 345, 635, 815, 815, 865, 1015]
Y_agent_thro = [66.06, 313.47, 779.93, 1039.71, 1085.48, 1084.5, 1089.5]

# idle rate
Y_rule_idle = [95.8, 66.7, 25.0, 0.0, 0.0, 0.0, 0.0]
Y_llm_idle = [95.8, 76.7, 52.5, 41.7, 41.7, 25.0, 25.0]
Y_agent_idle = [95.8, 69.2, 35.8, 0.0, 0.0, 0.0, 0.0]

# plot
fig, ax1 = plt.subplots(figsize=(8, 5))
ax2 = ax1.twinx()

# color map
COLOR_MAP = {
    'Rule-based': 'blue',  
    'Prompt-based': 'black', 
    'WirelessAgent': 'red' 
}

# 绘制吞吐量曲线（实线）
ax1.plot(x, Y_rule_thro, color=COLOR_MAP['Rule-based'], linestyle='-', 
        linewidth=2, marker='o', markersize=7, label='_nolegend_')
ax1.plot(x, Y_llm_thro, color=COLOR_MAP['Prompt-based'], linestyle='-',
        linewidth=2, marker='s', markersize=7, label='_nolegend_')
ax1.plot(x, Y_agent_thro, color=COLOR_MAP['WirelessAgent'], linestyle='-',
        linewidth=2, marker='^', markersize=7, label='_nolegend_')

# 绘制带宽空闲率曲线（虚线）
ax2.plot(x, Y_rule_idle, color=COLOR_MAP['Rule-based'], linestyle='--',
        linewidth=2, marker='o', markersize=7, label='Rule-based')
ax2.plot(x, Y_llm_idle, color=COLOR_MAP['Prompt-based'], linestyle='--',
        linewidth=2, marker='s', markersize=7, label='Prompt-based')
ax2.plot(x, Y_agent_idle, color=COLOR_MAP['WirelessAgent'], linestyle='--',
        linewidth=2, marker='^', markersize=7, label='WirelessAgent')

# 坐标轴设置
ax1.set_xlabel('Number of Users', fontsize=20)
ax1.set_ylabel('Total Throughput (Mbps)', fontsize=20)
ax2.set_ylabel('Bandwidth Idle Rate (%)', fontsize=20)

# 智能图例布局
handles, labels = ax2.get_legend_handles_labels()
legend = ax1.legend(handles, labels, 
                  loc='right',
                  frameon=True,
                  title_fontsize=14,
                  title="Method Types:",
                  fontsize=14,
                  ncol=1,
                  borderpad=0.8,
                  handletextpad=0.8)

# 添加线型说明
from matplotlib.lines import Line2D
custom_lines = [
    Line2D([0], [0], color='blue', linestyle='-', lw=2),
    Line2D([0], [0], color='blue', linestyle='--', lw=2)
]
ax1.legend(custom_lines, ['Throughput', 'Idle Rate'],
          loc='lower right',
          frameon=True,
          fontsize=14,
          title="Metric Types:",
          title_fontsize=14)

# 添加双图例
ax1.add_artist(legend)

# 图形优化
ax1.set_xlim(0, 31)
ax1.grid(True, linestyle=':', alpha=0.7)
ax2.set_ylim(0, 100)
plt.tight_layout()

plt.show()