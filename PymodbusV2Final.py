# Final Pymodbus Project code version-2 (Working as expected)
# Integrated code for data reading, logging and real-time plotting
'''In this code we input a csv file cointaining information about Parameters, register address and range of value. 
Using this information pymodbus communicates with PLC as a client to request data for all parameter and reads them sequentially.
After reading data every 1 sec, the data is logged in csv file and simultaneously plotted on GUI based 2D graph.
In the plot, we can plot upto 2 parameters on the same graph with different colors to identify.
We can change the parameter to plot at any moment by selecting parameter from drop-down menu.'''

# ----------- Code Starts ---------------
# ---------- Importing Libraries ----------
import tkinter as tk   # For GUI functionality (drop-down menu)
from tkinter import ttk # For GUI elements
import matplotlib.pyplot as plt  # For plotting-window/screen design
from matplotlib.animation import FuncAnimation  # For Real-Time plotting and updating values
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # For backend connection of matplotlib with Tkinter
import matplotlib.dates as mdates  # For Timestamp update on X-axis and Synchronization
from datetime import datetime, timedelta # For date and timestamp update
import numpy as np  # For data handling
import pandas as pd  # For logging data in csv file
import time  # for time delay between reading data (1 sec)
import os # For verifying whether csv file exist or not
import easygui  # For GUI interface design
import traceback  # For tracing the error if it occurs
from pymodbus.client import ModbusTcpClient  # Fot Modbus TCP Communication with PLC
import struct  # For data handling (REAL to float conversion)
'''Pymodbus makes a client to request data from server(PLC) using pre-defined Modbus protocol function codes and reads the data received'''

# ---------- Configuration Information ----------
PLC_IP = '127.0.0.1'  # PLC IP address
PORT = 502  # Default port for Modbus TCP
REGISTER_COUNT = 2  # For REAL (float32): occupies 2 registers
MAX_POINTS = 300  # Maximum number of points to plot before refreshing the graph window (5 minutes data)
INTERVAL = 1000  # milliseconds (1 sec)

# ---------- Global Variables ----------
time_data, left_data, right_data = [], [], []  # empty list created for important data to store
left_param, right_param = "None", "None"  # default parameters to show at the start of plotting 
start_time = datetime.now() # Initial time
left_change_time = None
right_change_time = None
df_params = None  # To read the content of input csv file
LOG_FILE = None  # csv File to store the logging data
plc_values = {}  # Store last plc values (dictionary)
info_text = None  # Add global info_text variable to show time and real-time values of left Y-axis and right Y-axis parameters

# Add parameter colors mapping
PARAMETER_COLORS = {
    "Temperature": "#FF0000",  # Red
    "Pressure": "#00FF00",     # Green
    "Flow": "#0000FF",         # Blue
    "Level": "#800080"         # Purple
}

# ---------- CSV File Selection and Loading ----------
def select_param_csv():
    # pop-up for selecting the input csv file
    return easygui.fileopenbox(
        title="Select Parameter Configuration CSV",
        filetypes=["*.csv"]
    # returns the file path in 'string' form
    )

def load_parameter_info(csv_path):  # Loading parameter information in csv file before logging
    try:
        df = pd.read_csv(csv_path)
        df['Address'] = df['Address'].str.replace('%MW', '', regex=False).astype(int)
        df[['Min', 'Max']] = df['Range'].str.split('-', expand=True).astype(float)
        return df
    except Exception as e:
        print(f"[ERROR] Failed to process parameter CSV: {e}")
        return None

def create_log_file(file_name, param_names):
    try:
        # Create logs directory if it doesn't exist
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Create full path for log file
        full_path = os.path.join(log_dir, file_name)
        
        # Create CSV with headers
        columns = ["Timestamp"] + param_names
        df = pd.DataFrame(columns=columns)
        df.to_csv(full_path, index=False)
        print(f"[INFO] Created CSV: {os.path.abspath(full_path)}")
        return full_path
    except Exception as e:
        print(f"[ERROR] Failed to create log file: {e}")
        return None

# ---------- PLC Register Reading Functions ----------
def read_plc_register(param_name, addr):
    # Make TCP client and connect
    global client
    client = ModbusTcpClient(PLC_IP, port=PORT)  # Connecting to PLC as client
    if not client.connect():
        print("[ERROR] Could not connect to PLC.")
        return None
    # Reading register data 
    result = client.read_holding_registers(address=addr, count=REGISTER_COUNT) 
    if result.isError():
            print(f"  → [ERROR] {param_name:<12} (%MW{addr}) - Read failed")
            value = None
    else:
        try:
            reg1, reg2 = result.registers  # Acquiring 2 consecutive register data seperately
            byte_data = struct.pack('>HH', reg1, reg2)  # Packing them to form combined parameter data
            value = struct.unpack('>f', byte_data)[0]  # Unpacking them to form 32-bit float value
            plc_values[param_name] = value  # Storing register data in dictionary with parameter name as 'key' 
            print(f"  → {param_name:<12} = {value:.2f} units (%MW{addr})")
        except Exception as e:
                print(f"  → [ERROR] {param_name:<12} - Conversion failed: {e}")
                value = None

    return round(plc_values[param_name], 3)  # Returning the register data after trunacating to 3 decimal places

# ---------- PLC Data Reading Function ----------
# Reading data received from read_plc_register() function
def read_plc_data():
    global df_params, LOG_FILE
    
    timestamp = datetime.now() # For storing data with timestamp
    row_data = [timestamp]  # First element of list 'row_data' will be Timestamp
    values = {}  # Storing value of parameters in dictionary
    
    # Acquiring parameters information from 'df_params'
    for _, row in df_params.iterrows():
        param_name = row['Parameter']
        addr = row['Address']
        min_val = row['Min']
        max_val = row['Max']
        # Running register reading function for all parameters
        value = read_plc_register(param_name, addr)  # Storing data in value
        print(f"  → {param_name:<12} = {value:.2f} units (SIMULATED) [Range: {min_val}-{max_val}]")
        values[param_name] = value   # Updating values in dictionary with param_name as key
        row_data.append(value)  # Appending data in row_data list

    # Log to CSV
    try:
        with open(LOG_FILE, mode='a', newline='') as f:
            pd.DataFrame([row_data], columns=["Timestamp"] + df_params['Parameter'].tolist()).to_csv(f, index=False, header=False)
        print(f"[INFO] Data logged to: {LOG_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to log data: {e}")

    return values

# ---------- GUI Setup ----------
def setup_gui():
    global window, left_combo, right_combo, fig, ax_left, ax_right, canvas, left_tick_count, right_tick_count, info_text

    window = tk.Tk()
    window.title("Real-time Data Visualizer (Simulation Mode)")

    # Top Parameter Selection Frame
    top_control_frame = tk.Frame(window)
    top_control_frame.pack(side=tk.TOP, pady=8)

    tk.Label(top_control_frame, text="Left Y-axis:", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=10, pady=5)
    left_combo = ttk.Combobox(top_control_frame, values=["None"] + df_params['Parameter'].tolist(), state="readonly", font=("Arial", 13), width=15)
    left_combo.set("None")
    left_combo.grid(row=0, column=1, padx=10, pady=5)

    tk.Label(top_control_frame, text="Right Y-axis:", font=("Arial", 14, "bold")).grid(row=0, column=2, padx=10, pady=5)
    right_combo = ttk.Combobox(top_control_frame, values=["None"] + df_params['Parameter'].tolist(), state="readonly", font=("Arial", 13), width=15)
    right_combo.set("None")
    right_combo.grid(row=0, column=3, padx=10, pady=5)

    # Plot and Axes
    fig, ax_left = plt.subplots()
    ax_right = ax_left.twinx()
    fig.patch.set_facecolor('white')
    ax_left.set_facecolor('white')
    ax_left.grid(True)
    ax_left.set_xlabel("Time", fontsize=14, weight='bold')
    fig.autofmt_xdate(rotation=45)
    title = ax_left.set_title("Real-Time Plot", fontsize=16, weight="bold")  # Restored title

    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    # Bottom Grid Control Frame
    bottom_frame = tk.Frame(window)
    bottom_frame.pack(side=tk.BOTTOM, pady=10)

    tk.Label(bottom_frame, text="Left Y-grid:", font=("Arial", 14, "bold")).grid(row=0, column=0, padx=10)
    left_tick_count = tk.Spinbox(bottom_frame, from_=2, to=15, width=7, font=("Arial", 13))
    left_tick_count.grid(row=0, column=1)
    left_tick_count.delete(0, "end")
    left_tick_count.insert(0, "6")

    tk.Label(bottom_frame, text="Right Y-grid:", font=("Arial", 14, "bold")).grid(row=0, column=2, padx=10)
    right_tick_count = tk.Spinbox(bottom_frame, from_=2, to=15, width=7, font=("Arial", 13))
    right_tick_count.grid(row=0, column=3)
    right_tick_count.delete(0, "end")
    right_tick_count.insert(0, "6")

    # Create initial info text
    info_text = fig.text(0.5, 0.95, "", ha='center', fontsize=14, weight='bold')

# ---------- Update Function for Plotting ----------
def update(frame):
    global left_line, right_line, start_time, left_change_time, right_change_time, left_param, right_param, info_text
    
    try:
        # Read PLC data
        values = read_plc_data()
        if values is None:
            return []

        current_time = datetime.now()  # Getting current time
        time_data.append(current_time)  # Appending real-time/current time
        left_data.append(None)
        right_data.append(None)

        # Fetch parameters and check for changes
        new_left_param = left_combo.get()
        new_right_param = right_combo.get()
        
        # Check if parameters changed
        if new_left_param != left_param:
            left_change_time = current_time
            left_param = new_left_param
            if left_line:
                left_line.remove()
                left_line = None
            
        if new_right_param != right_param:
            right_change_time = current_time
            right_param = new_right_param
            if right_line:
                right_line.remove()
                right_line = None

        # Update values
        if left_param != "None":
            left_val = values.get(left_param)
            left_data[-1] = left_val
        else:
            left_val = "-"

        if right_param != "None":
            right_val = values.get(right_param)
            right_data[-1] = right_val
        else:
            right_val = "-"

        # Reset plot every MAX_POINTS
        if len(time_data) > MAX_POINTS:
            time_data.clear()
            left_data.clear()
            right_data.clear()
            start_time = datetime.now()
            left_change_time = None
            right_change_time = None
            ax_left.cla()
            ax_right.cla()
            ax_left.grid(True)
            ax_left.set_xlabel("Time", fontsize=14, weight='bold')
            fig.autofmt_xdate(rotation=45)
            title = ax_left.set_title("Real-Time Plot", fontsize=16, weight="bold")
            left_line, right_line = None, None
            return

        # Plot left Y-axis
        if left_param != "None":
            if not left_line or left_line.get_label() != left_param:
                left_line, = ax_left.plot([], [], color=PARAMETER_COLORS.get(left_param, '#FF0000'), label=left_param)  # Default color for left Y-axis plot
            
            if left_change_time is None:
                plot_times = time_data
                plot_values = left_data
            else:
                mask = [t >= left_change_time for t in time_data]
                plot_times = [t for t, m in zip(time_data, mask) if m]
                plot_values = [v for v, m in zip(left_data, mask) if m]
            
            if len(plot_times) == len(plot_values):
                left_line.set_data(plot_times, plot_values)
            
            ax_left.set_ylabel(left_param, color=PARAMETER_COLORS.get(left_param, "#FF0000"), fontsize=14, weight='bold')  # Default color for right Y-axis legend
            ax_left.yaxis.set_label_coords(-0.07, 0.5)
            
            # Set y-axis limits based on parameter range
            param_info = df_params[df_params['Parameter'] == left_param].iloc[0]
            ax_left.set_ylim(param_info['Min'], param_info['Max'])
            
            try:
                tick_count = int(left_tick_count.get())
                ax_left.set_yticks(np.linspace(param_info['Min'], param_info['Max'], tick_count))
                ax_left.tick_params(axis='y', labelsize=12)
            except: pass
        else:
            ax_left.set_ylabel("")
            ax_left.set_ylim(0, 1)
            ax_left.set_yticks([0, 1])
            left_line = None

        # Plot right Y-axis
        if right_param != "None":
            if not right_line or right_line.get_label() != right_param:
                right_line, = ax_right.plot([], [], color=PARAMETER_COLORS.get(right_param, '#0000FF'), label=right_param)  # Default color for right Y-axis plot
            
            if right_change_time is None:
                plot_times = time_data
                plot_values = right_data
            else:
                mask = [t >= right_change_time for t in time_data]
                plot_times = [t for t, m in zip(time_data, mask) if m]
                plot_values = [v for v, m in zip(right_data, mask) if m]
            
            if len(plot_times) == len(plot_values):
                right_line.set_data(plot_times, plot_values)
            
            ax_right.set_ylabel(right_param, color=PARAMETER_COLORS.get(right_param, '#0000FF'), fontsize=14, weight='bold')  # Default color for right Y-axis legend
            ax_right.yaxis.set_label_coords(1.07, 0.5)
            
            # Set y-axis limits based on parameter range
            param_info = df_params[df_params['Parameter'] == right_param].iloc[0]
            ax_right.set_ylim(param_info['Min'], param_info['Max'])
            
            try:
                tick_count_r = int(right_tick_count.get())
                ax_right.set_yticks(np.linspace(param_info['Min'], param_info['Max'], tick_count_r))
                ax_right.tick_params(axis='y', labelsize=12)
            except: pass
        else:
            ax_right.set_ylabel("")
            ax_right.set_ylim(0, 1)
            ax_right.set_yticks([0, 1])
            right_line = None

        # X-axis formatting
        ax_left.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        if time_data:
            ax_left.set_xlim(time_data[0], time_data[0] + timedelta(seconds=MAX_POINTS))
            ax_left.set_xticks([time_data[0] + timedelta(seconds=i) for i in range(0, MAX_POINTS + 1, 30)])
            ax_left.set_xticklabels(
                [(time_data[0] + timedelta(seconds=i)).strftime('%H:%M:%S') for i in range(0, MAX_POINTS + 1, 30)],
                rotation=45, ha='right', fontsize=12, weight='bold'
            )

        # Update info text instead of creating new one
        info_text.set_text(f"{left_param}: {left_val}  |  Time: {current_time.strftime('%H:%M:%S')}  |  {right_param}: {right_val}")

        return left_line, right_line

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        traceback.print_exc()
        return []

# ---------- Main ----------
if __name__ == "__main__":
    # Select and load parameter configuration
    csv_path = select_param_csv()  # file path stored as string
    if not csv_path:
        print("[ERROR] No file selected. Exiting.")
        exit()

    df_params = load_parameter_info(csv_path)
    if df_params is None:
        exit()

    # Create log file
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')  # Notes down the time of start
    LOG_FILE = create_log_file(f"{current_time}Param_log.csv", df_params['Parameter'].tolist())  # Creates log file (csv)
    if LOG_FILE is None:
        print("[ERROR] Failed to create log file. Exiting.")
        exit()

    # Setup GUI and start plotting
    setup_gui()
    ani = FuncAnimation(fig, update, interval=INTERVAL)
    
    # Handle window close
    window.protocol("WM_DELETE_WINDOW", window.destroy)
    window.mainloop()
