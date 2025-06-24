# Final Pymodbus V3 code (Working as expected)
# Sucessfully tested at MST on 18th June
# Integrated PLC Data Reader & Real-Time Plotter
# Reads multiple PLC registers via Modbus TCP/IP, logs to CSV, and plots in real-time GUI
# Combined functionality: PLC reading + CSV logging + Real-time plotting + Auto-reconnect

# ---------- Code Starts ----------
# ----- Importing Libraries -----
import tkinter as tk  # For Tkinter functionalities
from tkinter import ttk, messagebox  # For GUI Functionalities
import matplotlib.pyplot as plt  # For Plotting
from matplotlib.animation import FuncAnimation   # For Real-time updating of plot
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # For backend integeration of plot with Tkinter
import matplotlib.dates as mdates  # For Time data and synchronization
from datetime import datetime, timedelta   # For system clock and Time
import numpy as np  # For data handling
import pandas as pd  # For data logging
import time  # For 1 sec delay in reading data
import easygui  # For input csv file GUI
import traceback  # For tracing errors
import os  # For ensuring the logging csv file exist's
import struct  # For REAL to Float conversion
from pymodbus.client import ModbusTcpClient  # For Modbus TCP communication
import threading  # For parallely reconnecting with PLC

# ---------- Configuration Information ----------
MAX_POINTS = 900  # 15 minutes × 60 seconds = 900 data points in single graph window
INTERVAL = 1000   # 1 second delay between reading the data from PLC
REFRESH_MINUTES = 15  # 15-minute sliding window
RECONNECT_INTERVAL = 5  # Seconds between reconnection attempts if connection with PLC lost

# ------------- UI Configuration(Font Style and Font size) --------------------
LABEL_FONT = ("Arial", 10, "bold")  # Other labels
BUTTON_FONT = ("Arial", 10, "bold")
STATUS_FONT = ("Arial", 10, "bold")
CHECKBOX_FONT = ("Arial", 10, "bold") 
TITLE_FONT = ("Arial", 12, "bold") 
AXIS_LABEL_FONT_SIZE = 14
TICK_LABEL_FONT_SIZE = 12
LEGEND_FONT_SIZE = 11
PLOT_TITLE_FONT_SIZE = 16

# ------- PLC Configuration ----------------
PLC_IP = '10.10.68.20'  # PLC IP address
PORT = 502  # Default port
REGISTER_COUNT = 2  # For REAL (float32): occupies 2 registers

# ---------- Global Variables ----------
df_params = None  # For reading content of input csv file
parameter_data = {}  # Dictionary to get parameter value
left_checkboxes = {}  # To get information about active parameters in left Y-axis (dictionary)
right_checkboxes = {} # To get information about active parameters in right Y-axis (dictionary)
left_selected_params = []  # List to store how many active parameters in Left Y-axis
right_selected_params = []  # List to store how many active parameters in Left Y-axis

window_start_time = None
current_point_count = 0

window = None
fig = None
ax_left = None
ax_right = None
canvas = None
left_frame = None
right_frame = None
connection_frame = None

# PLC Connection variables
plc_client = None
is_connected = False
connection_status = "Disconnected"
plc_ip_address = PLC_IP
plc_port = PORT
reconnect_thread = None
stop_reconnect = False
log_file_path = None

COLORS = ['#FF0000', '#00FF00', '#0000FF', '#800080', '#FFA500',
          '#FF69B4', '#00FFFF', '#FFD700', '#32CD32', '#8A2BE2']

# ----- Selecting Input CSV file ----- 
def select_param_csv():   # Extracting path of choosen file
    return easygui.fileopenbox(
        title="Select Parameter Configuration CSV",
        filetypes=["*.csv"]
    )

# ----- Reading input csv file to get Parameter information -----
def load_parameter_info(csv_path):
    try:
        df = pd.read_csv(csv_path)
        df['Address'] = df['Address'].str.replace('%MW', '', regex=False).astype(int)
        df[['Min', 'Max']] = df['Range'].str.split('-', expand=True).astype(float)
        return df
    except Exception as e:
        print(f"[ERROR] Failed to process parameter CSV: {e}")
        return None

# ----- Creating data logging csv file and putting headers -----
def create_log_file(file_name, param_names):
    if not os.path.exists(file_name):  
        columns = ["Timestamp"] + param_names
        pd.DataFrame(columns=columns).to_csv(file_name, index=False)
        print(f"[INFO] Created CSV: {os.path.abspath(file_name)}")

# ----- For tracking status of parameters -----
class ParameterTracker:
    # Initialization
    def __init__(self, param_name, min_val, max_val, address):
        self.param_name = param_name
        self.min_val = min_val
        self.max_val = max_val
        self.address = address
        self.segments = []
        self.current_segment = None
        self.is_active = False

    # Starting of plot
    def start_plotting(self, current_point):
        self.current_segment = {
            'start_point': current_point,
            'points': [],
            'values': []
        }
        self.is_active = True
        print(f"[INFO] Started plotting {self.param_name}")

    # Stop plotting
    def stop_plotting(self, current_point):
        if self.current_segment and len(self.current_segment['points']) > 0:
            self.segments.append(self.current_segment)
        self.current_segment = None
        self.is_active = False
        print(f"[INFO] Stopped plotting {self.param_name}")
    
    # Appending data in plot
    def add_data_point(self, point_index, value):
        if self.is_active and self.current_segment is not None:
            self.current_segment['points'].append(point_index)
            self.current_segment['values'].append(value)

    def get_all_plot_data(self):
        all_points = []
        all_values = []
        for segment in self.segments:
            all_points.extend(segment['points'])
            all_values.extend(segment['values'])
        if self.current_segment:
            all_points.extend(self.current_segment['points'])
            all_values.extend(self.current_segment['values'])
        return all_points, all_values
    
    # Clearing graph for new datapoints to plot
    def clear_all_data(self):
        self.segments.clear()
        if self.is_active:
            self.current_segment = {
                'start_point': 0,
                'points': [],
                'values': []
            }

def initialize_parameter_data():
    global parameter_data
    parameter_data = {}
    for _, row in df_params.iterrows():
        param_name = row['Parameter']
        min_val = row['Min']
        max_val = row['Max']
        address = row['Address']
        parameter_data[param_name] = ParameterTracker(param_name, min_val, max_val, address)

# Connecting to PLC
def connect_to_plc(ip_address, port):
    global plc_client, is_connected, connection_status
    try:
        if plc_client:
            plc_client.close()
        
        plc_client = ModbusTcpClient(ip_address, port=port)
        if plc_client.connect():
            is_connected = True
            connection_status = "Connected"
            print(f"[INFO] Connected to PLC at {ip_address}:{port}")
            return True
        else:
            is_connected = False
            connection_status = "Connection Failed"
            print(f"[ERROR] Could not connect to PLC at {ip_address}:{port}")
            return False
    except Exception as e:
        is_connected = False
        connection_status = f"Error: {str(e)[:20]}..."
        print(f"[ERROR] PLC connection failed: {e}")
        return False

# If Ctrl+C pressed then disconnect manually from PLC
def disconnect_from_plc():
    global plc_client, is_connected, connection_status, stop_reconnect
    stop_reconnect = True
    if plc_client:
        plc_client.close()
        is_connected = False
        connection_status = "Manually Disconnected"
        print("[INFO] Manually disconnected from PLC")

# Check PLC connection status
def check_connection():
    """Check if PLC connection is still alive"""
    global plc_client, is_connected
    if not plc_client or not is_connected:
        return False
    
    try:
        # Try a simple read to check connection
        result = plc_client.read_holding_registers(address=0, count=1)
        return not result.isError()
    except Exception:
        return False

# If disconnected then connect again
def reconnect_worker():
    """Background thread to handle reconnection attempts"""
    global plc_client, is_connected, connection_status, stop_reconnect
    
    while not stop_reconnect:
        if not is_connected:
            print(f"[INFO] Attempting to reconnect to PLC at {plc_ip_address}:{plc_port}")
            connection_status = "Reconnecting..."
            
            if connect_to_plc(plc_ip_address, plc_port):
                print("[INFO] Reconnection successful!")
                break
            else:
                print(f"[INFO] Reconnection failed. Retrying in {RECONNECT_INTERVAL} seconds...")
                for i in range(RECONNECT_INTERVAL):
                    if stop_reconnect:
                        return
                    time.sleep(1)
        else:
            break

# 5 sec break between reconnection attempts
def start_reconnect_thread():
    """Start the reconnection thread"""
    global reconnect_thread, stop_reconnect
    if reconnect_thread and reconnect_thread.is_alive():
        return
    
    stop_reconnect = False
    reconnect_thread = threading.Thread(target=reconnect_worker, daemon=True)
    reconnect_thread.start()

# Reading register data from PLC
def read_plc_data():
    global plc_client, is_connected, connection_status
    values = {}
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Check connection status first
    if not is_connected or not check_connection():
        if is_connected:  # Connection was lost
            is_connected = False
            connection_status = "Connection Lost"
            print("[WARNING] PLC connection lost. Starting reconnection attempts...")
            start_reconnect_thread()
        
        # Log empty data when disconnected
        print("[WARNING] No PLC connection - logging empty values")
        for param_name in parameter_data.keys():
            values[param_name] = None
        
        # Still log to CSV with empty values and timestamp
        if log_file_path:
            try:
                row_data = [timestamp] + [values.get(param, "") for param in df_params['Parameter'].tolist()]
                with open(log_file_path, mode='a', newline='') as f:
                    pd.DataFrame([row_data], columns=["Timestamp"] + df_params['Parameter'].tolist()).to_csv(f, index=False, header=False)
            except Exception as e:
                print(f"[ERROR] CSV logging failed: {e}")
        
        return values
    
    # Read real PLC data when connected
    for param_name, tracker in parameter_data.items():
        try:
            result = plc_client.read_holding_registers(address=tracker.address, count=REGISTER_COUNT)
            if result.isError():
                print(f"[ERROR] Failed to read {param_name} (%MW{tracker.address})")
                values[param_name] = None
            else:
                reg1, reg2 = result.registers
                byte_data = struct.pack('>HH', reg1, reg2)
                value = struct.unpack('>f', byte_data)[0]
                values[param_name] = round(value, 2)
                print(f"[INFO] {param_name} = {value:.2f} (%MW{tracker.address})")
        except Exception as e:
            print(f"[ERROR] Error reading {param_name}: {e}")
            # Connection might have been lost during reading
            is_connected = False
            connection_status = "Connection Lost"
            values[param_name] = None
            start_reconnect_thread()
    
    # Log to CSV
    if log_file_path:
        try:
            row_data = [timestamp] + [values.get(param, "") for param in df_params['Parameter'].tolist()]
            with open(log_file_path, mode='a', newline='') as f:
                pd.DataFrame([row_data], columns=["Timestamp"] + df_params['Parameter'].tolist()).to_csv(f, index=False, header=False)
        except Exception as e:
            print(f"[ERROR] CSV logging failed: {e}")
    
    return values

def generate_data():
    values = read_plc_data()
    if values:
        for param_name, value in values.items():
            if value is not None and parameter_data[param_name].is_active:
                parameter_data[param_name].add_data_point(current_point_count, value)
    return values

def on_left_checkbox_change(param_name):
    global left_selected_params
    checkbox = left_checkboxes[param_name]
    if checkbox.get():
        if param_name not in left_selected_params:
            left_selected_params.append(param_name)
            parameter_data[param_name].start_plotting(current_point_count)
    else:
        if param_name in left_selected_params:
            left_selected_params.remove(param_name)
            if param_name not in right_selected_params:
                parameter_data[param_name].stop_plotting(current_point_count)

def on_right_checkbox_change(param_name):
    global right_selected_params
    checkbox = right_checkboxes[param_name]
    if checkbox.get():
        if param_name not in right_selected_params:
            right_selected_params.append(param_name)
            if not parameter_data[param_name].is_active:
                parameter_data[param_name].start_plotting(current_point_count)
    else:
        if param_name in right_selected_params:
            right_selected_params.remove(param_name)
            if param_name not in left_selected_params:
                parameter_data[param_name].stop_plotting(current_point_count)

def setup_time_axis():
    global window_start_time
    if window_start_time is None:
        window_start_time = datetime.now()
    
    # Calculate the actual time difference between start and current point
    current_time = datetime.now()
    
    # Create time points corresponding to each data point index (0 to MAX_POINTS-1)
    time_points_for_ticks = []
    time_labels = []
    
    # Create ticks every 60 seconds (60 points) for 1-minute intervals
    for i in range(0, MAX_POINTS + 1, 60):
        # Calculate the actual time for this point based on current real time
        time_offset = i - current_point_count
        time_point = current_time + timedelta(seconds=time_offset)
        time_points_for_ticks.append(i)
        time_labels.append(time_point.strftime('%H:%M'))
    
    # Set x-axis limits to point indices (0 to MAX_POINTS-1)
    ax_left.set_xlim(0, MAX_POINTS - 1)
    ax_left.set_xticks(time_points_for_ticks)
    ax_left.set_xticklabels(time_labels, rotation=45, ha='right', fontsize=TICK_LABEL_FONT_SIZE, weight='bold')
    ax_left.set_xlabel("Time (HH:MM)", fontsize=AXIS_LABEL_FONT_SIZE, weight='bold')
    ax_left.grid(True, alpha=0.3)

# After 15 min reset the graph window to plot new upcoming datapoints
def reset_window():
    global current_point_count, window_start_time
    print(f"[INFO] Resetting 15-minute window at {datetime.now().strftime('%H:%M:%S')}")
    for tracker in parameter_data.values():
        tracker.clear_all_data()
    current_point_count = 0
    window_start_time = datetime.now()

def setup_connection_controls():
    global connection_frame, plc_ip_address, plc_port
    connection_frame = tk.Frame(window)
    connection_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)  # Reduced padding
    
    # PLC Connection controls
    tk.Label(connection_frame, text="PLC IP:", font=LABEL_FONT).pack(side=tk.LEFT, padx=(0, 5))
    ip_entry = tk.Entry(connection_frame, width=12, font=("Arial", 10))  # Reduced width
    ip_entry.insert(0, PLC_IP)
    ip_entry.pack(side=tk.LEFT, padx=(0, 10))
    
    tk.Label(connection_frame, text="Port:", font=LABEL_FONT).pack(side=tk.LEFT, padx=(0, 5))
    port_entry = tk.Entry(connection_frame, width=6, font=("Arial", 10))  # Reduced width
    port_entry.insert(0, str(PORT))
    port_entry.pack(side=tk.LEFT, padx=(0, 10))
    
    def connect_plc():
        global plc_ip_address, plc_port, stop_reconnect
        stop_reconnect = True  # Stop any ongoing reconnection attempts
        plc_ip_address = ip_entry.get()
        plc_port = int(port_entry.get())
        
        if connect_to_plc(plc_ip_address, plc_port):
            messagebox.showinfo("Success", f"Connected to PLC at {plc_ip_address}:{plc_port}")
        else:
            messagebox.showerror("Connection Failed", 
                               f"Could not connect to PLC at {plc_ip_address}:{plc_port}\n"
                               "The system will automatically attempt to reconnect.")
            start_reconnect_thread()
            
    def disconnect_plc():
        disconnect_from_plc()
        messagebox.showinfo("Disconnected", "Manually disconnected from PLC.")
    
    tk.Button(connection_frame, text="Connect", command=connect_plc, 
              bg="green", fg="white", font=BUTTON_FONT, padx=10, pady=3).pack(side=tk.LEFT, padx=5)  # Reduced padding
    tk.Button(connection_frame, text="Disconnect", command=disconnect_plc,
              bg="red", fg="white", font=BUTTON_FONT, padx=10, pady=3).pack(side=tk.LEFT, padx=5)  # Reduced padding
    
    # Status indicator
    status_label = tk.Label(connection_frame, text="Status: Disconnected", 
                           font=STATUS_FONT, fg="red")
    status_label.pack(side=tk.RIGHT, padx=15)
    
    def update_status():
        if is_connected:
            status_label.config(text="Status: Connected to PLC", fg="green")
        elif connection_status == "Manually Disconnected":
            status_label.config(text="Status: Disconnected", fg="red")
        elif connection_status == "Reconnecting...":
            status_label.config(text="Status: Reconnecting...", fg="orange")
        elif "Connection Lost" in connection_status:
            status_label.config(text="Status: Connection Lost - Reconnecting", fg="orange")
        else:
            status_label.config(text=f"Status: {connection_status}", fg="red")
        window.after(1000, update_status)
    
    update_status()

def setup_gui():
    global window, fig, ax_left, ax_right, canvas, left_frame, right_frame
    window = tk.Tk()
    window.title("PLC Data Reader & Real-Time Plotter")
    window.state('zoomed')
    
    # Connection controls at top
    setup_connection_controls()
    
    main_frame = tk.Frame(window)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)  # Reduced padding
    
    # Left frame for checkboxes - Optimized width (reduced from 250 to 180)
    left_frame = tk.Frame(main_frame, relief=tk.RAISED, borderwidth=2, width=180)
    left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))  # Reduced padding
    left_frame.pack_propagate(False)  # Maintain fixed width
    tk.Label(left_frame, text="Left Y-axis", font=TITLE_FONT,
             fg="blue").pack(pady=10)  # Reduced padding
    
    # Right frame for checkboxes - Optimized width (reduced from 250 to 180)
    right_frame = tk.Frame(main_frame, relief=tk.RAISED, borderwidth=2, width=180)
    right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))  # Reduced padding
    right_frame.pack_propagate(False)  # Maintain fixed width
    tk.Label(right_frame, text="Right Y-axis", font=TITLE_FONT,
             fg="red").pack(pady=10)  # Reduced padding
    
    # Plot frame with better margins
    plot_frame = tk.Frame(main_frame)
    plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)  # Reduced padding
    
    # Create figure with adjusted margins to prevent overlap
    fig, ax_left = plt.subplots(figsize=(14, 8))  # Increased width from 12 to 14
    fig.subplots_adjust(left=0.08, right=0.92, bottom=0.15, top=0.9)  # Optimized margins
    ax_right = ax_left.twinx()
    fig.patch.set_facecolor('white')
    ax_left.set_facecolor('white')
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    create_parameter_checkboxes()

def create_parameter_checkboxes():
    global left_checkboxes, right_checkboxes
    param_names = df_params['Parameter'].tolist()
    
    # Configure style for compact checkboxes
    style = ttk.Style()
    style.configure('Compact.TCheckbutton', font=CHECKBOX_FONT)
    
    for i, param_name in enumerate(param_names):
        var = tk.BooleanVar()
        checkbox = tk.Checkbutton(
            left_frame,
            text=param_name,
            variable=var,
            font=CHECKBOX_FONT,
            command=lambda p=param_name: on_left_checkbox_change(p),
            padx=3,  # Reduced from 5
            pady=2,  # Reduced from 3
            indicatoron=1,
            anchor='w'
        )
        checkbox.pack(anchor=tk.W, padx=10, pady=2, fill=tk.X)  # Reduced padding
        left_checkboxes[param_name] = var
        
    for i, param_name in enumerate(param_names):
        var = tk.BooleanVar()
        checkbox = tk.Checkbutton(
            right_frame,
            text=param_name,
            variable=var,
            font=CHECKBOX_FONT,
            command=lambda p=param_name: on_right_checkbox_change(p),
            padx=3,  # Reduced from 5
            pady=2,  # Reduced from 3
            indicatoron=1,
            anchor='w'
        )
        checkbox.pack(anchor=tk.W, padx=10, pady=2, fill=tk.X)  # Reduced padding
        right_checkboxes[param_name] = var

def update_plot(frame):
    global current_point_count
    try:
        # Generate data first
        values = generate_data()
        if values:
            current_point_count += 1
            
            # Check if we need to reset after plotting this point
            if current_point_count >= MAX_POINTS:
                # Plot this final point first, then reset
                plot_current_data()
                reset_window()
                return
            
            # Normal plotting
            plot_current_data()
        
    except Exception as e:
        print(f"[ERROR] Update failed: {e}")
        traceback.print_exc()

def plot_current_data():
    ax_left.clear()
    ax_right.clear()
    setup_time_axis()

    left_plotted = False
    right_plotted = False

    if left_selected_params:
        left_values = []
        color_idx = 0
        for param_name in left_selected_params:
            points, values_list = parameter_data[param_name].get_all_plot_data()
            if points and values_list:
                color = COLORS[color_idx % len(COLORS)]
                ax_left.plot(points, values_list, color=color, linewidth=3,
                             label=f"{param_name} (L)")  # Removed markers
                left_values.extend([parameter_data[param_name].min_val, parameter_data[param_name].max_val])
                color_idx += 1
                left_plotted = True
        if left_values:
            margin = (max(left_values) - min(left_values)) * 0.1
            ax_left.set_ylim(min(left_values) - margin, max(left_values) + margin)
            ax_left.yaxis.set_major_locator(plt.MaxNLocator(nbins=15))  # Ensure 15 ticks
            ax_left.set_ylabel("Left Y-axis", fontsize=AXIS_LABEL_FONT_SIZE, weight='bold', color='blue')
            ax_left.tick_params(axis='y', labelcolor='blue', labelsize=TICK_LABEL_FONT_SIZE)
            ax_left.yaxis.set_label_position("left")
            ax_left.yaxis.set_label_coords(-0.06, 0.5)

    if right_selected_params:
        right_values = []
        color_idx = len(left_selected_params)
        for param_name in right_selected_params:
            points, values_list = parameter_data[param_name].get_all_plot_data()
            if points and values_list:
                color = COLORS[color_idx % len(COLORS)]
                ax_right.plot(points, values_list, color=color, linewidth=3,
                              label=f"{param_name} (R)")  # Removed markers
                right_values.extend([parameter_data[param_name].min_val, parameter_data[param_name].max_val])
                color_idx += 1
                right_plotted = True
        if right_values:
            margin = (max(right_values) - min(right_values)) * 0.1
            ax_right.set_ylim(min(right_values) - margin, max(right_values) + margin)
            ax_right.yaxis.set_major_locator(plt.MaxNLocator(nbins=15))  # Ensure 15 ticks
            ax_right.set_ylabel("Right Y-axis", fontsize=AXIS_LABEL_FONT_SIZE, weight='bold', color='red')
            ax_right.tick_params(axis='y', labelcolor='red', labelsize=TICK_LABEL_FONT_SIZE)
            ax_right.yaxis.set_label_position("right")
            ax_right.yaxis.set_label_coords(1.06, 0.5)

    # Position legends to avoid overlap
    if left_plotted and right_plotted:
        ax_left.legend(loc='upper left', fontsize=LEGEND_FONT_SIZE, framealpha=0.9)
        ax_right.legend(loc='upper right', fontsize=LEGEND_FONT_SIZE, framealpha=0.9)
    elif left_plotted:
        ax_left.legend(loc='upper left', fontsize=LEGEND_FONT_SIZE, framealpha=0.9)
    elif right_plotted:
        ax_right.legend(loc='upper right', fontsize=LEGEND_FONT_SIZE, framealpha=0.9)

    progress = (current_point_count / MAX_POINTS) * 100
    active_params = len(set(left_selected_params + right_selected_params))
    status = "Connected" if is_connected else connection_status
    ax_left.set_title(f"Real-Time PLC Data Plot [{status}] - Progress: {progress:.1f}% ({current_point_count}/{MAX_POINTS}) | Active: {active_params} params",
                      fontsize=PLOT_TITLE_FONT_SIZE, weight='bold', pad=20)
    canvas.draw_idle()

def on_window_close():
    global stop_reconnect
    stop_reconnect = True
    disconnect_from_plc()
    window.destroy()

if __name__ == "__main__":
    print("[INFO] Starting PLC Data Reader & Real-Time Plotter")
    csv_path = select_param_csv()
    if not csv_path:
        print("[ERROR] No file selected. Exiting.")
        exit()
    
    df_params = load_parameter_info(csv_path)
    if df_params is None:
        print("[ERROR] Failed to load parameter configuration. Exiting.")
        exit()
    
    print(f"[INFO] Loaded {len(df_params)} parameters:")
    for _, row in df_params.iterrows():
        print(f"  → {row['Parameter']}: %MW{row['Address']}, Range {row['Min']}-{row['Max']}")
    
    # Create log file
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M')
    log_file_path = f"{current_time}_PLC_Data_log.csv"
    create_log_file(log_file_path, df_params['Parameter'].tolist())
    
    initialize_parameter_data()
    
    setup_gui()
    window_start_time = datetime.now()
    ani = FuncAnimation(fig, update_plot, interval=INTERVAL, blit=False)
    window.protocol("WM_DELETE_WINDOW", on_window_close)
    print("[INFO] GUI started. Please connect to PLC to begin data logging.")
    print(f"[INFO] Data will be logged to: {log_file_path}")
    window.mainloop()
    print("[INFO] Application closed.")
