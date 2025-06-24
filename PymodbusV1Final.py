# Final code for reading 1 register from PLC , logging data and plotting in Real-Time
# Uses new method for reading register (No RAM method)
# Working fine for one variable, we will go with this.  

# ------ Final Integrated Code for Logging + Plotting + Modbus ------
# ------ Importing Libraries -------
import matplotlib.pyplot as plt  # For Plotting the data points
import matplotlib.dates as mdates  # For synchronizing the data plotting with time
from pymodbus.client import ModbusTcpClient  # For Modbus TCP communication
import pandas as pd  # For logging data in csv file
import struct  # For data handling
from datetime import datetime, timedelta  # For Timestamp
import time  # For 1 sec delay between data acquisition
import os  # For ensuring that data logging file is created in the PC

# -------------------- CONFIGURATION --------------------
PLC_IP = '127.0.0.1'  # IP address of PLC 
PORT = 502  # Default port for Modbus TCP 
REGISTER_ADDR = 10  # %MW10
REGISTER_COUNT = 2  # Reading two consecutive register for REAL data type
CSV_FILE = "pressure_log.csv"  # File name
Y_MIN = 0  # Min limit of parameter
Y_MAX = 250  # Max limit of parameter
Y_TICKS = 20  # Uniform gap between Y-axis points
X_WINDOW = 180  #180 points => 3 minutes data plotted before refreshing
X_INTERVAL = 15  # 15 sec gap between x-axis points
READ_INTERVAL = 1  # Reading data every 1 sec

# -------------------- CSV File Setup --------------------
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as f:
        pd.DataFrame(columns=["Timestamp", "Pressure (REAL)"]).to_csv(f, index=False)
print(f"[INFO] CSV logging to file: {os.path.abspath(CSV_FILE)}")

# -------------------- Connect to PLC --------------------
print(f"[INFO] Connecting to PLC at {PLC_IP}:{PORT}...")
client = ModbusTcpClient(PLC_IP, port=PORT)
if not client.connect():
    print("[ERROR] Failed to connect to PLC.")
    exit()
print(f"[INFO] Connected to PLC.")

# -------------------- Plot Setup --------------------
plt.ion()
fig, ax = plt.subplots(figsize=(12, 6))  # Plotting window size(width,height)
fig.patch.set_facecolor('darkblue')
ax.set_facecolor('darkblue')

times = []
values = []
cycle_start_time = datetime.now()

line, = ax.plot([], [], 'o-', color='lime')

ax.set_ylim(Y_MIN, Y_MAX)
ax.set_yticks([Y_MIN + i * (Y_MAX - Y_MIN) / (Y_TICKS - 1) for i in range(Y_TICKS)])
ax.set_ylabel("Pressure", color='white', weight='bold')
ax.set_xlabel("Time (HH:MM:SS)", color='white', weight='bold')
ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
ax.xaxis.set_major_locator(mdates.SecondLocator(interval=X_INTERVAL))
ax.grid(True, color='white', alpha=0.3)
ax.tick_params(axis='x', colors='white')
ax.tick_params(axis='y', colors='white')

title_text = fig.text(0.5, 0.95, "", ha='center', va='top', color='white', fontsize=16, weight='bold')
info_text = fig.text(0.98, 0.90, "", ha='right', va='top', color='white', fontsize=12, weight='bold')

# -------------------- Main Loop --------------------
try:
    while True:
        now = datetime.now()

        # ---- Read from PLC ----
        result = client.read_holding_registers(address=REGISTER_ADDR, count=REGISTER_COUNT) 
        if result.isError():
            print("[WARNING] Modbus read failed.")
            time.sleep(READ_INTERVAL)
            continue

        reg1 = result.registers[0]
        reg2 = result.registers[1]

        try:
            float_bytes = struct.pack('>HH', reg1, reg2)
            pressure = struct.unpack('>f', float_bytes)[0]
        except Exception as e:
            print(f"[ERROR] Float conversion failed: {e}")
            time.sleep(READ_INTERVAL)
            continue

        # ---- Log to CSV ----
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[DATA] {timestamp} → Pressure = {pressure:.2f} units")
        with open(CSV_FILE, mode='a', newline='') as f:
            pd.DataFrame([[timestamp, round(pressure, 2)]],
                         columns=["Timestamp", "Pressure (REAL)"]).to_csv(f, index=False, header=False)

        # ---- Plotting ----
        times.append(now)
        values.append(pressure)

        if (now - cycle_start_time).total_seconds() >= X_WINDOW:
            times = []
            values = []
            cycle_start_time = now
            ax.cla()
            ax.set_facecolor('darkblue')
            ax.set_ylim(Y_MIN, Y_MAX)
            ax.set_yticks([Y_MIN + i * (Y_MAX - Y_MIN) / (Y_TICKS - 1) for i in range(Y_TICKS)])
            ax.set_ylabel("Pressure", color='white', weight='bold')
            ax.set_xlabel("Time (HH:MM:SS)", color='white', weight='bold')
            ax.grid(True, color='white', alpha=0.3)
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            ax.xaxis.set_major_locator(mdates.SecondLocator(interval=X_INTERVAL))
            line, = ax.plot([], [], 'o-', color='lime')
            title_text = fig.text(0.5, 0.95, "", ha='center', va='top',
                                  color='white', fontsize=16, weight='bold')
            info_text = fig.text(0.98, 0.90, "", ha='right', va='top',
                                 color='white', fontsize=12, weight='bold')

        # Update plot
        line.set_data(times, values)
        ax.set_xlim(cycle_start_time, cycle_start_time + timedelta(seconds=X_WINDOW))
        ax.relim()
        ax.autoscale_view(scalex=False, scaley=False)
        title_text.set_text(f"Real-Time Data plotting [{now.strftime('%Y-%m-%d')}]")
        info_text.set_text(f"Pressure: {pressure:.2f} mbar  |  Time: {now.strftime('%H:%M:%S')}")

        fig.autofmt_xdate()
        plt.draw()
        plt.pause(0.01)
        time.sleep(READ_INTERVAL)

except KeyboardInterrupt:
    print("\n[INFO] Logging and plotting stopped by user.")

finally:
    client.close()
    plt.ioff()
    plt.show()
    print("[INFO] Disconnected from PLC. CSV file is up to date.")
