#! usr/bin/env python3.6

import serial
import sys
from PyQt4 import QtCore


class SerialRemote(QtCore.QThread, QtCore.QObject):
    signal_chmin = QtCore.pyqtSignal()
    signal_ch = QtCore.pyqtSignal()
    signal_chplus = QtCore.pyqtSignal()
    signal_prev = QtCore.pyqtSignal()
    signal_next = QtCore.pyqtSignal()
    signal_play = QtCore.pyqtSignal()
    signal_volmin = QtCore.pyqtSignal()
    signal_volplus = QtCore.pyqtSignal()
    signal_eq = QtCore.pyqtSignal()
    signal_100 = QtCore.pyqtSignal()
    signal_200 = QtCore.pyqtSignal()
    signal_0 = QtCore.pyqtSignal()
    signal_1 = QtCore.pyqtSignal()
    signal_2 = QtCore.pyqtSignal()
    signal_3 = QtCore.pyqtSignal()
    signal_4 = QtCore.pyqtSignal()
    signal_5 = QtCore.pyqtSignal()
    signal_6 = QtCore.pyqtSignal()
    signal_7 = QtCore.pyqtSignal()
    signal_8 = QtCore.pyqtSignal()
    signal_9 = QtCore.pyqtSignal()

    signals = {'CH-': 'signal_chmin',
               'CH': 'signal_ch',
               'CH+': 'signal_chplus',
               'PREV': 'signal_prev',
               'NEXT': 'signal_next',
               'PLAY': 'signal_play',
               'VOL-': 'signal_volmin',
               'VOL+': 'signal_volplus',
               'EQ': 'signal_eq',
               '100+': 'signal_100',
               '200+': 'signal_200',
               '0': 'signal_0',
               '1': 'signal_1',
               '2': 'signal_2',
               '3': 'signal_3',
               '4': 'signal_4',
               '5': 'signal_5',
               '6': 'signal_6',
               '7': 'signal_7',
               '8': 'signal_8',
               '9': 'signal_9'}
    values = {}

    def __init__(self, com_port="COM4"):
        QtCore.QObject.__init__(self)
        QtCore.QThread.__init__(self)
        self.serial = serial.Serial(port=com_port, timeout=1)
        self.running = False
        self.on_all = None
        self.com_port = com_port

    def on_event(self, val):
        if self.on_all:
            self.on_all(val)

        try:
            key = self.values[val]
            signal = getattr(self, self.signals[key], None)
            if signal:
                signal.emit()
        except KeyError:
            print(f'Unknown remote value {val}.', file=sys.stderr)

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
