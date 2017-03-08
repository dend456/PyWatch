#! /usr/bin/env python3.6

import sys
import os.path
import vlc
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
    def __init__(self, video_player, controls):
        QtGui.QDialog.__init__(self)
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

    def load_remote_vals(self):
        vals = {}
        with open('remote.txt', 'r') as f:
            for line in f:
                if line:
                    l = line.rstrip().split(' ')
                    vals[l[0]] = l[1]
        return vals

    def setup_ui(self):
        self.controls.setupUi(self)
        self.controls.host_box.addItems(self.guide.plugin_names)
        if self.guide.selected_plugin:
            self.controls.type_box.clear()
            self.controls.type_box.addItems(self.guide.get_categories())

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
            self.remote = None

        if port:
            self.remote = SerialRemote(port)
            self.remote.add(self.remote_vals['CH-'], self.prev_episode_button_clicked)
            self.remote.add(self.remote_vals['CH'], self.replay_button_clicked)
            self.remote.add(self.remote_vals['CH+'], self.next_episode_button_clicked)
            self.remote.add(self.remote_vals['VOL-'], self.volume_down)
            self.remote.add(self.remote_vals['VOL+'], self.volume_up)
            self.remote.add(self.remote_vals['EQ'], self.toggle_mute)
            self.remote.add(self.remote_vals['PLAY'], self.toggle_pause_clicked)
            self.remote.add(self.remote_vals['100+'], self.large_jump_backwards_clicked)
            self.remote.add(self.remote_vals['2'], self.small_jump_backwards_clicked)
            self.remote.add(self.remote_vals['200+'], self.large_jump_forwards_clicked)
            self.remote.add(self.remote_vals['3'], self.small_jump_forwards_clicked)
            self.remote.add(self.remote_vals['PREV'], self.decrease_speed)
            self.remote.add(self.remote_vals['NEXT'], self.increase_speed)
            self.remote.daemon = True
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
        if self.video_player.current_url:
            self.video_player.media.parse()
            self.play(self.video_player.current_url)
            self.video_player.pause(False)

    def next_episode_button_clicked(self):
        next_index = self.controls.episode_box.currentIndex() + 1
        self.controls.episode_box.setCurrentIndex(next_index)
        index = self.controls.episode_box.currentIndex()
        if index == next_index:
            self.play_episode_clicked()
            self.video_player.pause(False)

    def prev_episode_button_clicked(self):
        next_index = self.controls.episode_box.currentIndex() - 1
        if next_index >= 0:
            self.controls.episode_box.setCurrentIndex(next_index)
            index = self.controls.episode_box.currentIndex()
            if index == next_index:
                self.play_episode_clicked()
                self.video_player.pause(False)

    def toggle_pause_clicked(self):
        self.video_player.pause(not self.video_player.paused)

    def small_jump_forwards_clicked(self):
        self.video_player.media_player.set_time(self.video_player.media_player.get_time() + 5000)

    def small_jump_backwards_clicked(self):
        self.video_player.media_player.set_time(self.video_player.media_player.get_time() - 5000)

    def large_jump_forwards_clicked(self):
        self.video_player.media_player.set_time(self.video_player.media_player.get_time() + 30000)

    def large_jump_backwards_clicked(self):
        self.video_player.media_player.set_time(self.video_player.media_player.get_time() - 30000)

    def filter_changed(self):
        self.guide.filter = self.controls.filter_box.text()
        self.controls.series_box.clear()
        self.controls.series_box.addItems(self.guide.get_series())

    def volume_changed(self, vol):
        self.video_player.media_player.audio_set_volume(vol)

    def speed_changed(self, speed):
        speed = (speed / 100) * 2
        self.video_player.media_player.set_rate(speed)
        self.controls.speed_label.setText(str(int(speed * 100)) + '%')

    def toggle_fullscreen(self):
        win = self.video_player.videoframe.window()
        win.setWindowState(win.windowState() ^ QtCore.Qt.WindowFullScreen)

    def play_episode_clicked(self):
        url = self.guide.get_selected_url()
        if url:
            self.play(url)
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
        self.video_player.pause(True)

    def time_slider_released(self):
        self.video_player.media_player.set_position(self.controls.time_slider.value() / 10000)
        self.video_player.pause(False)

    def update_time_label(self, value):
        length = self.video_player.media_player.get_length()
        percent = (value / 10000)
        pos = length * percent
        total_min = int(length / 60000.0)
        total_sec = int(length / 1000.0 % 60.0)
        cur_min = int(pos / 60000.0)
        cur_sec = int(pos / 1000.0 % 60.0)
        time = '{:02}:{:02} / {:02}:{:02}'.format(cur_min, cur_sec, total_min, total_sec)
        self.controls.time_label.setText(time)

    def time_slider_moved(self, value):
        self.update_time_label(value)

    def play(self, url):
        self.video_player.media = self.video_player.instance.media_new(url, 'network-cache=1500000', 'file-cache=1500000')
        self.video_player.media_player.set_media(self.video_player.media)
        self.video_player.videoframe.window().setWindowTitle(self.guide.selected_episode)
        self.video_player.media_player.play()
        self.video_player.current_url = url

        print(f'Playing {url}')

        if sys.platform == "linux2":
            self.video_player.media_player.set_xwindow(self.video_player.videoframe.winId())
        elif sys.platform == "win32":
            self.video_player.media_player.set_hwnd(self.video_player.videoframe.winId())
        elif sys.platform == "darwin":
            self.video_player.media_player.set_agl(self.video_player.videoframe.windId())

    def update_ui(self):
        if not self.video_player.paused and self.video_player.media_player.is_playing():
            val = self.video_player.media_player.get_position() * 10000
            self.controls.time_slider.setValue(val)
            self.update_time_label(val)

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
    app = QtGui.QApplication(sys.argv)
    w = Watcher()
    w.resize(800, 600)
    w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
