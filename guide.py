#! /usr/bin/env python3.6

import importlib
import glob
import os


class Guide:
    def __init__(self):
        self.plugins = []
        self.plugin_names = []
        self.reload_plugins()
        self._selected_plugin = None
        self._selected_series = None
        self._selected_episode = None
        self._selected_category = None
        self._filter = ''
        if self.plugins:
            self._selected_plugin = self.plugins[0]
            self._selected_plugin.load()
            self._selected_category = self.selected_plugin.categories[0]

    @property
    def selected_plugin(self):
        return self._selected_plugin

    @selected_plugin.setter
    def selected_plugin(self, host):
        if isinstance(host, int):
            self._selected_plugin = self.plugins[host]
            if not self._selected_plugin.loaded:
                self._selected_plugin.load()

    @property
    def selected_series(self):
        return self._selected_series

    @selected_series.setter
    def selected_series(self, series):
        self._selected_series = series

    @property
    def selected_category(self):
        return self._selected_category

    @selected_category.setter
    def selected_category(self, cat):
        self._selected_category = cat
        self.selected_series = self._selected_plugin.series[cat]

    @property
    def selected_episode(self):
        return self._selected_episode

    @selected_episode.setter
    def selected_episode(self, episode):
        self._selected_episode = episode

    @property
    def filter(self):
        return self._filter

    @filter.setter
    def filter(self, val):
        self._filter = val.lower()

    def reload_plugins(self):
        self.plugins = []
        files = glob.glob('plugins/*.py')
        for file in files:
            mod_name, ext = os.path.splitext(os.path.split(file)[-1])
            p = importlib.import_module('plugins.' + mod_name)
            self.plugins.append(p)
        self.plugin_names = [p.display_name for p in self.plugins]

    def get_categories(self):
        if self.selected_plugin:
            return self.selected_plugin.categories
        return []

    def get_series(self):
        if self._selected_plugin:
            return [x[0] for x in self._selected_plugin.series[self._selected_category] if self._filter in x[0].lower()]
        return []

    def get_episodes(self):
        if self._selected_plugin:
            return [x[0] for x in self._selected_plugin.get_series_episodes(self._selected_category, self._selected_series)]
        return []

    def get_selected_url(self):
        if self._selected_plugin:
            return self._selected_plugin.get_video_url(self._selected_category, self._selected_series, self._selected_episode)
        return None

if __name__ == "__main__":
    g = Guide()
    print(g.plugins)
