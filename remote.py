#! usr/bin/env python3.6

import serial
import threading


class SerialRemote(threading.Thread):
    def __init__(self, com_port="COM4"):
        threading.Thread.__init__(self)
        self.binds = []
        self.serial = serial.Serial(port=com_port, timeout=1)
        self.running = False
        self.on_all = None
        self.com_port = com_port

    def add(self, value, func):
        self.binds.append((value, func))

    def on_event(self, val):
        if self.on_all:
            self.on_all(val)
        for b in self.binds:
            if b[0] == val:
                b[1]()

    def run(self):
        self.running = True
        while self.running:
            line = self.serial.readline().strip().decode('utf-8')
            if line:
                self.on_event(line)
        self.serial.close()

    def stop(self):
        self.running = False

    @staticmethod
    def open_ports():
        valid_ports = []
        for i in range(0, 256):
            try:
                port = f'COM{i}'
                s = serial.Serial(port)
                s.close()
                valid_ports.append(port)
            except Exception:
                pass

        return valid_ports

if __name__ == "__main__":
    print(SerialRemote.open_ports())
