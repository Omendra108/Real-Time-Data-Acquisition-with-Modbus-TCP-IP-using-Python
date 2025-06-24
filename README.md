<div align="center" width="50">
<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Roboto+Mono&size=25&duration=3000&pause=1000&color=2de151&center=true&width=500&lines=Welcome+to+my+Github!;feel+free+to+clone+and+..;raise+issues+if+you+think..;something+could+be+better" alt="Typing SVG" />
</p>

<div align="center" width="50">
  
![image](https://github.com/user-attachments/assets/bc536ca5-48a1-4961-90e8-0539f163bed3)


# Real-Time-Data-Acquisition-with-Modbus-TCP-IP-using-Python

---
</div>

## Disclaimer: This repository is part of my internship project at ISRO in 2025. Since the project does not involve any sensitive or confidential aspects of ISRO’s work, it has been made publicly accessible to support and assist others working on similar projects.
---
</div>

## Introduction 📖
Data serves as the backbone of all rocketry and space exploration missions, where precision and continuous monitoring are critical. Sensors mounted on launch vehicles (rockets) are used to measure vital parameters such as pressure, temperature, flow rate, leak rate, oxygen concentration, and more.

These sensors typically produce analog signals, which are passed through signal conditioning circuits to convert them into suitable electrical forms—voltage, current, or impedance. The conditioned signals are then digitized using ADCs (Analog-to-Digital Converters) and stored for monitoring and analysis.

To acquire and manage this sensor data efficiently, PLCs (Programmable Logic Controllers) are commonly used—not just in the space industry, but also across various industrial domains. Tools like SCADA offer powerful interfaces for real-time visualization and control of such systems.

In this project, I developed a Python-based application that:

1) Connects to a PLC using the Modbus TCP/IP protocol

2) Acquires sensor data in real-time

3) Logs the data to a CSV file with timestamps

4) Visualizes the data dynamically on a 2D interactive GUI graph

This tool aims to provide a lightweight and customizable solution for real-time industrial data acquisition and visualization.

## What is Modbus TCP/IP ?
Modbus TCP/IP is an industrial communication protocol used for transmitting data between electronic devices over Ethernet networks. It is a variant of the original Modbus protocol, adapted to work over TCP/IP networks, making it ideal for modern industrial automation systems.

⚙️ How It Works:

Client-Server Model: Modbus TCP/IP operates on a master-slave (client-server) architecture.

1. The client (master) sends requests.

2. The server (slave) (like a PLC) responds with data or performs actions.

3. TCP/IP Layer:The protocol runs over standard Ethernet using TCP port 502. This allows Modbus communication across local or wide-area networks without special hardware.

4. Data Structure: Data is organized into registers:

   4.1. Coils: Binary outputs (read/write)

   4.2. Discrete Inputs: Binary inputs (read-only)

   4.3. Input Registers: Analog inputs (read-only)

   4.4. Holding Registers: Analog outputs (read/write)

5. Function Codes: The client sends a request using a function code (like read/write), and the server replies with the requested data or a status message.

## Requirements 📂

Following are the requirements for implementing the project objectives:

1. Python 3.11.9 (or 3.11.x)
2. Python Libraries:
   
   2.1. Pymodbus 3.9.2
   
   2.2. pandas 2.3.0
   
   2.3. matplotlib 3.10.3
   
   2.4. easygui 0.98.3
   
4. PLC and ethernet connection (I used Unity Pro XL software to simulate PLC and finally tested on real PLC with physical ethernet connection)

## Project Overview 🧠

![image](https://github.com/user-attachments/assets/74579956-e220-4b42-becd-67d987b7fd09)

## About Attached Files 📁

1. There are 3 code files and 1 csv file.
  
2. All the code file have extension .py
   
3. The csv file is for input cointaining the variables to read from PLC, their addresses and value range.
 
4. Their are 3 version of the project(three phases):
   
    4.1. V1 is for single variable
   
    4.2. V2 is for multiple variable but onyl 2 plot at a time
   
    4.3. V3 is the final version for multiple variables with multiple plots at a time
   






  
