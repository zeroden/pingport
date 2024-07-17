import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import tkinter as tk
from matplotlib import dates as mdates

def maximize_window(root):
    root.state('zoomed')  # Maximizes the window on Windows systems

def plot_with_day_change_vertical_line(ax, x_data, y_data, label, color):
    for i in range(len(x_data) - 1):
        if x_data[i].day != x_data[i + 1].day:
            ax.axvline(x=x_data[i + 1], color='gray', linestyle='--', linewidth=1)
    ax.plot(x_data, y_data, marker='o', linestyle='-', color=color, label=label)

def main():
    root = tk.Tk()
    root.title("My Application")
    
    # Maximizing the window
    maximize_window(root)

    filename = 'speed.csv'
    dataframe = pd.read_csv(filename)

    dataframe["DATETIME"] = pd.to_datetime(dataframe['DATETIME'], format='%Y-%m-%d %H:%M:%S')

    fig, ax1 = plt.subplots()

    # Plot download and upload speeds on primary y-axis (left) with markers and day change vertical line
    plot_with_day_change_vertical_line(ax1, dataframe["DATETIME"], dataframe["DOWNLOAD"], "Download", 'b')
    plot_with_day_change_vertical_line(ax1, dataframe["DATETIME"], dataframe["UPLOAD"], "Upload", 'g')

    ax1.set_xlabel("Date Time")
    ax1.set_ylabel("Speed (Mbps)")
    ax1.legend(loc='upper left')

    # Create a secondary y-axis for ping with markers and day change vertical line
    ax2 = ax1.twinx()
    plot_with_day_change_vertical_line(ax2, dataframe["DATETIME"], dataframe["PING"], "Ping", 'r')
    ax2.set_ylabel("Ping (ms)")
    ax2.legend(loc='upper right')

    # Format x-axis dates
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d\n%H:%M:%S'))  # Example format

    # Rotate and align the x-axis labels
    plt.xticks(rotation=45, ha='right')
    fig.autofmt_xdate()  # Automatically format date labels

    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    toolbar = NavigationToolbar2Tk(canvas, root)
    toolbar.update()
    toolbar.pack(side=tk.TOP, fill=tk.BOTH, expand=True)  # Pack toolbar above canvas

    root.mainloop()

if __name__ == "__main__":
    main()