import matplotlib.pyplot as plt

# Corrected data (x matches Y length)
x = [1, 5, 10, 15, 20, 25, 30]
Y_rule_thro = [66.06, 415.76, 996.96, 1062.24, 1093.92, 1093.92, 1093.92]
Y_llm_thro = [66.06, 345, 635, 815, 815, 865, 1015]
Y_agent_thro = [66.06, 313.47, 779.93, 1039.71, 1085.48, 1084.5, 1089.5]

Y_rule_utli =  [4.2, 33.3, 75, 100, 100, 100, 100] # %
Y_llm_utli =   [4.2, 23.3, 47.5, 58.3, 58.3, 75, 75]
Y_agent_utli = [4.2, 30.8, 64.2, 100, 100, 100, 100]

# Create figure with compact layout
plt.figure(figsize=(7, 5))

# Plot curves with distinct styles
plt.plot(x, Y_rule_thro, 
         color='blue', marker='o', markersize=7, linewidth=2, linestyle='-',  # Solid line with circles
         label='Rule-based Method')
plt.plot(x, Y_agent_thro, 
         color='red', marker='^', markersize=7, linewidth=2, linestyle='-.',  # Dash-dot line with triangles
         label='WirelessAgent')
plt.plot(x, Y_llm_thro, 
         color='green', marker='s', markersize=7, linewidth=2, linestyle='--',  # Dashed line with squares
         label='Prompt-based Method')

# Axis labels configuration
plt.xlabel('The Number of Users', fontsize=12)
plt.ylabel('Toal Transmission Rate (Mbps)', fontsize=12)

# Legend configuration
plt.legend(loc='lower right', 
           frameon=True, 
           fontsize=12)

# Visual enhancements
plt.box(True)  # Add frame around plot
plt.grid(True, linestyle=':', alpha=0.6)  # Add dotted grid lines
plt.xlim((0.7, 30.25))  # Extended x-axis limit

# Remove padding and auto-adjust layout
plt.tight_layout()  # Reduced padding for compact display 
plt.show()