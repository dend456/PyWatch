#! /usr/bin/env python3.6

import sys
import os.path
import argparse
import ipaddress
import asyncio
import threading
import vlc
import math
from websocket_server import WebsocketServer
from PyQt4 import QtGui, QtCore
from controlsdialog import Ui_ControlsDialog
from guide import Guide
from remote import SerialRemote


class VideoPlayer:
    def __init__(self, instance, media_player, palette, videoframe):
        self.instance = instance
        self.media_player = media_player
        self.media = None
        self.palette = palette
        self.videoframe = videoframe
        self.paused = False
        self.current_url = None

    def pause(self, p):
        self.paused = p
        self.media_player.set_pause(p)


class ControlsDialog(QtGui.QDialog):
    def __init__(self, video_player, controls, server_ip=None, server_port=None):
        QtGui.QDialog.__init__(self)
        self.server_ip = server_ip
        self.server_port = server_port
        self.sock = None
        self.msg_q = asyncio.Queue() if server_ip else None
        self.timer = None
        self.video_player = video_player
        self.controls = controls
        self.guide = Guide()
        self.setup_ui()
        self.prev_volume = 100
        self.muted = False
        self.remote_vals = self.load_remote_vals()
        self.remote = None
        self.remote_refresh_clicked()
        self.setFixedSize(self.size())

        if server_ip:
            self.sock = WebsocketServer(self.server_port, host=self.server_ip)
            self.sock.set_fn_new_client(self.on_open)
            self.sock.set_fn_message_received(self.on_message)
            self.sock_thread = threading.Thread(target=self.sock.run_forever, daemon=True)
            self.sock_thread.start()

    def on_message(self, cli, serv, msg):
        print(msg)
        p = msg.find(':')
        if p == -1:
            command = msg
        else:
            command = msg[:p]
            data = msg[p+1:]

        if command == 'time':
            try:
                data = data.split('/')
                current_f = float(data[0])
                total_f = float(data[1])
                current = int(current_f * 1000)
                total = int(total_f * 1000)
            except ValueError:
                return
            pos = int((current / total) * 10000)
            self.controls.time_slider.setValue(pos)
            self.update_time_label(pos, total)
            if math.isclose(current_f, total_f):
                self.next_episode_button_clicked()

        elif command == 'vol':
            vol = int(float(data) * 100)
            self.controls.volume_slider.setValue(vol)


    def on_open(self, cli, serv):
        print('got connection')

    def load_remote_vals(self):
        vals = {}
        with open('remote.txt', 'r') as f:
            for line in f:
                if line:
                    l = line.rstrip().split(' ')
                    vals[l[0]] = l[1]

        for k, v in vals.items():
            SerialRemote.values[v] = k

        return vals

    def setup_ui(self):
        self.controls.setupUi(self)
        self.controls.host_box.addItems(self.guide.plugin_names)
        if self.guide.selected_plugin:
            self.controls.type_box.clear()
            self.controls.type_box.addItems(self.guide.get_categories())

        if self.video_player:
            self.timer = QtCore.QTimer(self)
            self.timer.setInterval(200)
            self.connect(self.timer, QtCore.SIGNAL("timeout()"), self.update_ui)
            self.timer.start()

    def remote_refresh_clicked(self):
        open_ports = [''] + SerialRemote.open_ports()
        self.controls.remote_box.clear()
        self.controls.remote_box.addItems(open_ports)

    def remote_box_changed(self, port):
        if self.remote:
            self.remote.stop()
            self.remote.wait()
            self.remote = None

        if port:
            self.remote = SerialRemote(port)

            self.remote.signal_chmin.connect(self.prev_episode_button_clicked)
            self.remote.signal_ch.connect(self.replay_button_clicked)
            self.remote.signal_chplus.connect(self.next_episode_button_clicked)

            self.remote.signal_volmin.connect(self.volume_down)
            self.remote.signal_volplus.connect(self.volume_up)
            self.remote.signal_eq.connect(self.toggle_mute)

            self.remote.signal_play.connect(self.toggle_pause_clicked)
            self.remote.signal_100.connect(self.large_jump_backwards_clicked)
            self.remote.signal_2.connect(self.small_jump_backwards_clicked)
            self.remote.signal_200.connect(self.large_jump_forwards_clicked)
            self.remote.signal_3.connect(self.small_jump_forwards_clicked)
            self.remote.signal_prev.connect(self.decrease_speed)
            self.remote.signal_next.connect(self.increase_speed)

            self.remote.start()

    def decrease_speed(self):
        self.controls.speed_slider.setValue(self.controls.speed_slider.value() - 1)
        self.speed_changed(self.controls.speed_slider.value())

    def increase_speed(self):
        self.controls.speed_slider.setValue(self.controls.speed_slider.value() + 1)
        self.speed_changed(self.controls.speed_slider.value())

    def volume_down(self):
        self.controls.volume_slider.setValue(self.controls.volume_slider.value() - 10)
        self.prev_volume = self.controls.volume_slider.value()
        self.volume_changed(self.prev_volume)
        self.muted = False

    def volume_up(self):
        self.controls.volume_slider.setValue(self.controls.volume_slider.value() + 10)
        self.prev_volume = self.controls.volume_slider.value()
        self.volume_changed(self.prev_volume)
        self.muted = False

    def toggle_mute(self):
        if self.muted:
            self.controls.volume_slider.setValue(self.prev_volume)
            self.volume_changed(self.prev_volume)
            self.muted = False
        else:
            self.prev_volume = self.controls.volume_slider.value()
            self.controls.volume_slider.setValue(0)
            self.volume_changed(0)
            self.muted = True

    def replay_button_clicked(self):
        if self.video_player and self.video_player.current_url:
            self.video_player.media.parse()
            self.play(self.video_player.current_url)
            self.video_player.pause(False)
        elif self.sock:
            self.sock.send_message_to_all('replay')

    def next_episode_button_clicked(self):
        next_index = self.controls.episode_box.currentIndex() + 1
        self.controls.episode_box.setCurrentIndex(next_index)
        index = self.controls.episode_box.currentIndex()
        if index == next_index:
            self.play_episode_clicked()
            if self.video_player:
                self.video_player.pause(False)

    def prev_episode_button_clicked(self):
        next_index = self.controls.episode_box.currentIndex() - 1
        if next_index >= 0:
            self.controls.episode_box.setCurrentIndex(next_index)
            index = self.controls.episode_box.currentIndex()
            if index == next_index:
                self.play_episode_clicked()
                if self.video_player:
                    self.video_player.pause(False)

    def toggle_pause_clicked(self):
        if self.video_player:
            self.video_player.pause(not self.video_player.paused)
        elif self.sock:
            self.sock.send_message_to_all('toggle_pause')

    def small_jump_forwards_clicked(self):
        self.offset_time(10000)

    def small_jump_backwards_clicked(self):
        self.offset_time(-10000)

    def large_jump_forwards_clicked(self):
        self.offset_time(60000)

    def large_jump_backwards_clicked(self):
        self.offset_time(-60000)

    def offset_time(self, offset):
        if self.video_player:
            self.video_player.media_player.set_time(self.video_player.media_player.get_time() + offset)
        elif self.sock:
            self.sock.send_message_to_all(f'offset:{offset/1000}')

    def filter_changed(self):
        self.guide.filter = self.controls.filter_box.text()
        self.controls.series_box.clear()
        self.controls.series_box.addItems(self.guide.get_series())

    def volume_changed(self, vol):
        if self.video_player:
            self.video_player.media_player.audio_set_volume(vol)
        elif self.sock:
            self.sock.send_message_to_all(f'vol:{vol/100}')

    def speed_changed(self, speed):
        speed = (speed / 100) * 2
        self.controls.speed_label.setText(str(int(speed * 100)) + '%')
        if self.video_player:
            self.video_player.media_player.set_rate(speed)
        elif self.sock:
            self.sock.send_message_to_all(f'speed:{speed}')

    def toggle_fullscreen(self):
        if self.video_player:
            win = self.video_player.videoframe.window()
            win.setWindowState(win.windowState() ^ QtCore.Qt.WindowFullScreen)

    def play_episode_clicked(self):
        url = self.guide.get_selected_url()
        if url:
            self.play(url)
            if self.video_player:
                self.video_player.pause(False)

    def host_box_changed(self, index):
        self.guide.selected_plugin = index
        self.controls.type_box.clear()
        self.controls.type_box.addItems(self.guide.get_categories())
        self.controls.series_box.clear()
        self.controls.series_box.addItems(self.guide.get_series())

    def series_box_changed(self, series):
        self.guide.selected_series = series
        self.controls.episode_box.clear()
        self.controls.episode_box.addItems(self.guide.get_episodes())

    def episode_box_changed(self, episode):
        self.guide.selected_episode = episode

    def type_box_changed(self, cat):
        if cat != '':
            self.guide.selected_category = cat
            self.controls.series_box.clear()
            self.controls.series_box.addItems(self.guide.get_series())

    def time_slider_pressed(self):
        if self.video_player:
            self.video_player.pause(True)
        elif self.sock:
            self.sock.send_message_to_all('pause')

    def time_slider_released(self):
        if self.video_player:
            self.video_player.media_player.set_position(self.controls.time_slider.value() / 10000)
            self.video_player.pause(False)
        elif self.sock:
            pos = self.controls.time_slider.value() / 10000
            self.sock.send_message_to_all(f'time:{pos}')

    def update_time_label(self, value, length):
        percent = (value / 10000)
        pos = length * percent
        total_min = int(length / 60000.0)
        total_sec = int(length / 1000.0 % 60.0)
        cur_min = int(pos / 60000.0)
        cur_sec = int(pos / 1000.0 % 60.0)
        time = '{:02}:{:02} / {:02}:{:02}'.format(cur_min, cur_sec, total_min, total_sec)
        self.controls.time_label.setText(time)

    def time_slider_moved(self, value):
        if self.video_player:
            self.update_time_label(value, self.video_player.media_player.get_length())

    def play(self, url):
        print(f'Playing {url}')
        if self.video_player:
            self.video_player.media = self.video_player.instance.media_new(url, 'network-cache=1500000', 'file-cache=1500000')
            self.video_player.media_player.set_media(self.video_player.media)
            self.video_player.videoframe.window().setWindowTitle(self.guide.selected_episode)
            self.video_player.media_player.play()
            self.video_player.current_url = url

            if sys.platform == "linux2":
                self.video_player.media_player.set_xwindow(self.video_player.videoframe.winId())
            elif sys.platform == "win32":
                self.video_player.media_player.set_hwnd(self.video_player.videoframe.winId())
            elif sys.platform == "darwin":
                self.video_player.media_player.set_agl(self.video_player.videoframe.windId())
        elif self.sock:
            self.sock.send_message_to_all(f'play:{url}')

    def update_ui(self):
        if self.video_player:
            if not self.video_player.paused and self.video_player.media_player.is_playing():
                val = self.video_player.media_player.get_position() * 10000
                self.controls.time_slider.setValue(val)
                self.update_time_label(val, self.video_player.media_player.get_length())

            if self.video_player.media_player.get_state() == vlc.State.Ended:
                cur = self.video_player.media_player.get_position()
                if cur < .99:
                    print(f'Error at {cur*100}%, replaying', file=sys.stderr)
                    self.replay_button_clicked()
                    self.video_player.media_player.set_position(cur)
                else:
                    self.next_episode_button_clicked()


class Watcher(QtGui.QMainWindow):
    def __init__(self, master=None):
        QtGui.QMainWindow.__init__(self, master)
        self.widget = None
        self.vboxlayout = None
        self.controls_dialog = None
        self.controls = None
        self.video_player = None

        self.setup_ui()
        self.setup_control_window()
        self.controls_dialog.show()
        self.is_paused = False

    def setup_control_window(self):
        self.controls = Ui_ControlsDialog()
        self.controls_dialog = ControlsDialog(self.video_player, self.controls)
        self.controls_dialog.setWindowFlags(QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowMinimizeButtonHint)

    def setup_ui(self):
        self.setWindowTitle("PyWatch")
        instance = vlc.Instance()
        media_player = instance.media_player_new()
        self.widget = QtGui.QWidget(self)
        self.setCentralWidget(self.widget)

        if sys.platform == "darwin":
            videoframe = QtGui.QMacCocoaViewContainer(0)
        else:
            videoframe = QtGui.QFrame()

        palette = videoframe.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(0, 0, 0))
        videoframe.setPalette(palette)
        videoframe.setAutoFillBackground(True)

        self.vboxlayout = QtGui.QVBoxLayout()
        self.vboxlayout.setMargin(0)
        self.vboxlayout.addWidget(videoframe)

        self.widget.setLayout(self.vboxlayout)
        self.video_player = VideoPlayer(instance, media_player, palette, videoframe)

        self.connect(QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Escape), self), QtCore.SIGNAL('activated()'), self.disable_fullscreen)

    def disable_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()

    def closeEvent(self, event):
            QtGui.QApplication.closeAllWindows()
            event.accept()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', dest='ip', help='IP address to bind server to')
    parser.add_argument('-p', dest='port', type=int, default=5001, help='Port to bind server to. Default = 5001')
    args = parser.parse_args()

    if not args.ip:
        app = QtGui.QApplication(sys.argv)
        w = Watcher()
        w.resize(800, 600)
        w.show()
        sys.exit(app.exec_())
    else:
        try:
            ip = str(ipaddress.ip_address(args.ip))

            app = QtGui.QApplication(sys.argv)
            controls = Ui_ControlsDialog()
            controls_dialog = ControlsDialog(None, controls, ip, args.port)
            controls_dialog.show()
            sys.exit(app.exec_())

        except ValueError:
            print('Error: Invalid IP address.')


if __name__ == "__main__":
    main()
