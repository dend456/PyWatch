#! /usr/bin/env python3.6

import bs4
import requests

display_name = 'Media Server2'
categories = ['Videos', 'Movies']
selector = 'body > ul > li > a'

urls = {'base':   'http://192.168.0.163:8001',
        'Videos': 'http://192.168.0.163:8001/videos',
        'video_format': 'http://192.168.0.163:8001/videos/{}/{}',
        'series_format': 'http://192.168.0.163:8001/videos/{}',
        'Movies': 'http://192.168.0.163:8001/movies'}

series = {c: [] for c in categories}
episode_cache = {c: dict() for c in categories}
loaded = False


def get_series_from_url(url):
    s = []
    res = requests.get(url)
    if res:
        soup = bs4.BeautifulSoup(res.text, 'lxml')
        nodes = soup.select(selector)
        for node in nodes:
            title = node.contents[0]
            link = node['href']
            s.append((title[:-1], urls['series_format'].format(link[:-1])))
    return sorted(s)


def get_movies(series_name):
    return []


def get_videos(category, series_name):
    series_cache = episode_cache.get(category, None)
    if series_cache is not None:
        episodes = series_cache.get(series_name, None)
        if episodes:
            return episodes
    else:
        return []

    episodes = []
    selected_series = series[category]

    for link in selected_series:
        if link[0] == series_name:
            res = requests.get(link[1])
            if res:
                soup = bs4.BeautifulSoup(res.text, 'lxml')
                nodes = soup.select(selector)
                for node in nodes:
                    episodes.append(
                        (node.contents[0], urls['video_format'].format(series_name, node['href']).replace(' ', '%20')))
                # episodes.reverse()
                series_cache[series_name] = episodes
                return episodes
    return episodes


def get_series_episodes(category, series_name):
    if category == 'Movies':
        return get_movies(series_name)
    elif category == 'Videos':
        return get_videos(category, series_name)
    return []


def get_video_url(category, series_name, episode_title):
    for l in episode_cache[category][series_name]:
        if l[0] == episode_title:
            return l[1]
    return None


def load():
    global loaded
    series['Videos'] = get_series_from_url(urls['Videos'])
    series['Movies'] = ('Movies', urls['Movies'])
    loaded = True

if __name__ == '__main__':
    load()
    print(get_series_episodes('Videos', 'Log Horizon'))
    print(get_video_url('Videos', 'Log Horizon', 'Episode 3.mp4'))
