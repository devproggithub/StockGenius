# second_rfid_handler.py
import serial
import requests
import json
import time
import threading

class ZoneRFIDHandler:
    def __init__(self, port='COM5', baud_rate=9600, api_url='http://localhost:5000/api/zone-rfid/data'):
        self.port = port
        self.baud_rate = baud_rate
        self.api_url = api_url
        self.serial_connection = None
        self.is_running = False
        self.thread = None
    
    def start(self):
        """Start the RFID reader in a separate thread"""
        if self.is_running:
            print(f"Zone RFID reader is already running on {self.port}")
            return False
            
        try:
            self.serial_connection = serial.Serial(self.port, self.baud_rate, timeout=1)
            self.is_running = True
            self.thread = threading.Thread(target=self._read_data_loop, daemon=True)
            self.thread.start()
            print(f"✅ Zone RFID reader started on {self.port}")
            return True
        except serial.SerialException as e:
            print(f"❌ Error connecting to Zone RFID reader on {self.port}: {e}")
            return False
    
    def stop(self):
        """Stop the RFID reader"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
            
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print(f"✅ Zone RFID reader on {self.port} stopped")
    
    def _read_data_loop(self):
        """Main loop for reading RFID data from serial port"""
        while self.is_running and self.serial_connection and self.serial_connection.is_open:
            try:
                if self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8').strip()
                    
                    # Check if it's valid JSON
                    if line.startswith('{') and line.endswith('}'):
                        try:
                            data = json.loads(line)
                            print(f"Zone RFID data received: {data}")
                            
                            # Add zone reader identifier
                            data['source'] = 'zone_reader'
                            
                            # Send to API
                            response = requests.post(self.api_url, json=data)
                            
                            if response.status_code == 200 or response.status_code == 201:
                                print(f"✅ Zone RFID data sent successfully! Code: {response.status_code}")
                            else:
                                print(f"❌ API Error: {response.status_code}")
                                print(response.text)
                                
                        except json.JSONDecodeError:
                            print(f"❌ Invalid JSON: {line}")
                        except requests.RequestException as e:
                            print(f"❌ API connection error: {e}")
                    else:
                        print(f"Zone RFID Message: {line}")
                        
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ Error in Zone RFID reader: {e}")
                time.sleep(1)  # Wait before retrying
                
        print("Zone RFID reader loop ended")