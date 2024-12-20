import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from matplotlib import dates as mdates
from datetime import datetime, timedelta

def maximize_window(root):
    root.state('zoomed')  # Maximizes the window on Windows systems

def plot_graph(root, dataframe):
    fig, ax1 = plt.subplots()

    # Create y-axis for download1
    dataframe_without_zeroes_12 = dataframe[dataframe['DOWN12'] != 0]
    ax1.plot(dataframe_without_zeroes_12["DATETIME"], dataframe_without_zeroes_12["DOWN12"], marker='o', linestyle='-', color='b', label="Download1")
    ax1.set_xlabel('Date Time')
    ax1.set_ylabel('Speed (Mbps)')
    ax1.legend(loc='upper left')

    # Create y-axis for download2
    dataframe_without_zeroes_34 = dataframe[dataframe['DOWN34'] != 0]
    ax1.plot(dataframe_without_zeroes_34["DATETIME"], dataframe_without_zeroes_34["DOWN34"], marker='o', linestyle='-', color='g', label="Download2")
    ax1.legend(loc='upper left')

    # Create y-axis for download3
    dataframe_without_zeroes_5 = dataframe[dataframe['DOWN5'] != 0]
    ax1.plot(dataframe_without_zeroes_5["DATETIME"], dataframe_without_zeroes_5["DOWN5"], marker='o', linestyle='-', color='r', label="Download3")
    ax1.legend(loc='upper left')
    
    ax1.yaxis.set_ticks_position('both')  # Ticks on both left and right
    ax_right = ax1.twinx()  # Create a twin axis for the right side
    ax_right.set_ylim(ax1.get_ylim())  # Ensure the limits are the same

    # Format x-axis dates
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d\n%H:%M:%S'))  # Example format

    # Rotate and align the x-axis labels
    plt.xticks(rotation=45, ha='right')
    fig.autofmt_xdate()  # Automatically format date labels

    # Adding vertical dashed line at midnight for each unique date
    unique_dates = pd.to_datetime(dataframe["DATETIME"].dt.date.unique())
    for date in unique_dates:
        midnight = pd.Timestamp(date) + pd.Timedelta('00:00:00')
        ax1.axvline(x=midnight, color='gray', linestyle='--')

    # Add grid lines to the plot
    ax1.grid(True, which='both', linestyle=':', linewidth=0.5)  # Customize grid lines as needed

    # Calculate statistics
    max_download_1 = dataframe_without_zeroes_12["DOWN12"].max()
    min_download_1 = dataframe_without_zeroes_12["DOWN12"].min()
    avg_download_1 = dataframe_without_zeroes_12["DOWN12"].mean()

    max_download_2 = dataframe_without_zeroes_34["DOWN34"].max()
    min_download_2 = dataframe_without_zeroes_34["DOWN34"].min()
    avg_download_2 = dataframe_without_zeroes_34["DOWN34"].mean()

    max_download_3 = dataframe_without_zeroes_5["DOWN5"].max()
    min_download_3 = dataframe_without_zeroes_5["DOWN5"].min()
    avg_download_3 = dataframe_without_zeroes_5["DOWN5"].mean()

    # Display statistics
    stats_text = f"Download1 - Max:{max_download_1:6.2f} Mbps, Min:{min_download_1:6.2f} Mbps, Avg:{avg_download_1:6.2f} Mbps\n" \
                 f"Download2 - Max:{max_download_2:6.2f} Mbps, Min:{min_download_2:6.2f} Mbps, Avg:{avg_download_2:6.2f} Mbps\n" \
                 f"Download3 - Max:{max_download_3:6.2f} Mbps, Min:{min_download_3:6.2f} Mbps, Avg:{avg_download_3:6.2f} Mbps\n"

    monospace_font = ('Courier New', 12)  # Font family and size
    stats_label = ttk.Label(root, text=stats_text, font=monospace_font)
    stats_label.pack(pady=10)

    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    toolbar = NavigationToolbar2Tk(canvas, root)
    toolbar.update()
    toolbar.pack(side=tk.TOP, fill=tk.BOTH, expand=True)  # Pack toolbar above canvas

    # Ensure that the figure is properly closed when closing the window
    def on_close():
        plt.close(fig)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)  # Handle window close event

def on_date_select(cal_start, cal_end, root, dataframe):
    start_date = cal_start.get_date()
    end_date = cal_end.get_date()
    
    if start_date and end_date:
        # Filter dataframe for selected date range
        selected_data = dataframe[(dataframe['DATETIME'].dt.date >= pd.to_datetime(start_date).date()) &
                                  (dataframe['DATETIME'].dt.date <= pd.to_datetime(end_date).date())]
        # Clear existing plot if any
        for widget in root.winfo_children():
            widget.destroy()
        # Recreate plot with selected data
        plot_graph(root, selected_data)

def show_all_data(root, dataframe):
    # Clear existing plot if any
    for widget in root.winfo_children():
        widget.destroy()
    # Recreate plot with all data
    plot_graph(root, dataframe)

def show_last_n_days(root, dataframe, n):
    end_date = dataframe["DATETIME"].max().date()
    start_date = end_date - timedelta(days=n)
    selected_data = dataframe[(dataframe['DATETIME'].dt.date >= start_date) & 
                              (dataframe['DATETIME'].dt.date <= end_date)]
    # Clear existing plot if any
    for widget in root.winfo_children():
        widget.destroy()
    # Recreate plot with selected data
    plot_graph(root, selected_data)

def main():
    root = tk.Tk()
    root.title("plot")

    # Maximizing the window
    maximize_window(root)

    filename = 'speed.csv'
    dataframe = pd.read_csv(filename)
    dataframe["DATETIME"] = pd.to_datetime(dataframe['DATETIME'], format='%Y-%m-%d %H:%M:%S')

    # Date entry widgets for selecting start and end dates
    start_label = ttk.Label(root, text="Start Date")
    start_label.pack(pady=10)
    cal_start = DateEntry(root, width=12, background='darkblue', foreground='white', borderwidth=2)
    cal_start.pack(pady=10)

    end_label = ttk.Label(root, text="End Date")
    end_label.pack(pady=10)
    cal_end = DateEntry(root, width=12, background='darkblue', foreground='white', borderwidth=2)
    cal_end.pack(pady=10)

    # Button to select date range
    ttk.Button(root, text="Select Date Range", command=lambda: on_date_select(cal_start, cal_end, root, dataframe)).pack(pady=5)

    # Buttons to show data for the last 3 days, last week, last month, and last year
    ttk.Button(root, text="Last 3 Days", command=lambda: show_last_n_days(root, dataframe, 3)).pack(pady=5)
    ttk.Button(root, text="Last Week", command=lambda: show_last_n_days(root, dataframe, 7)).pack(pady=5)
    ttk.Button(root, text="Last Month", command=lambda: show_last_n_days(root, dataframe, 30)).pack(pady=5)
    ttk.Button(root, text="Last Year", command=lambda: show_last_n_days(root, dataframe, 365)).pack(pady=5)
    # Button to show all data
    ttk.Button(root, text="Show All Data", command=lambda: show_all_data(root, dataframe)).pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    main()
