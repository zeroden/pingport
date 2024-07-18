import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from matplotlib import dates as mdates

def maximize_window(root):
    root.state('zoomed')  # Maximizes the window on Windows systems

def plot_graph(root, dataframe):
    fig, ax1 = plt.subplots()

    # Plot download and upload speeds on primary y-axis (left) with markers
    ax1.plot(dataframe["DATETIME"], dataframe["DOWNLOAD"], marker='o', linestyle='-', color='b', label="Download")
    ax1.plot(dataframe["DATETIME"], dataframe["UPLOAD"], marker='o', linestyle='-', color='g', label="Upload")
    ax1.set_xlabel("Date Time")
    ax1.set_ylabel("Speed (Mbps)")
    ax1.legend(loc='upper left')

    # Create a secondary y-axis for ping with markers
    ax2 = ax1.twinx()
    ax2.plot(dataframe["DATETIME"], dataframe["PING"], marker='o', linestyle='-', color='r', label="Ping")
    ax2.set_ylabel("Ping (ms)")
    ax2.legend(loc='upper right')

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
    max_download = dataframe["DOWNLOAD"].max()
    min_download = dataframe["DOWNLOAD"].min()
    avg_download = dataframe["DOWNLOAD"].mean()

    max_upload = dataframe["UPLOAD"].max()
    min_upload = dataframe["UPLOAD"].min()
    avg_upload = dataframe["UPLOAD"].mean()

    max_ping = dataframe["PING"].max()
    min_ping = dataframe["PING"].min()
    avg_ping = dataframe["PING"].mean()

    # Display statistics
    stats_text = f"Download - Max: {max_download:.2f} Mbps, Min: {min_download:.2f} Mbps, Avg: {avg_download:.2f} Mbps\n" \
                 f"Upload - Max: {max_upload:.2f} Mbps, Min: {min_upload:.2f} Mbps, Avg: {avg_upload:.2f} Mbps\n" \
                 f"Ping - Max: {max_ping:.2f} ms, Min: {min_ping:.2f} ms, Avg: {avg_ping:.2f} ms"

    stats_label = ttk.Label(root, text=stats_text, wraplength=600)
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
    ttk.Button(root, text="Select Date Range", command=lambda: on_date_select(cal_start, cal_end, root, dataframe)).pack()

    # Button to show all data
    ttk.Button(root, text="Show All Data", command=lambda: show_all_data(root, dataframe)).pack()

    root.mainloop()

if __name__ == "__main__":
    main()
