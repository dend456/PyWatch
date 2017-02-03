#! /usr/bin/env python3.6
import bs4
import requests
import re


display_name = 'Watch Cartoon Online'
categories = ['Dubbed', 'Subbed', 'Cartoon', 'OVA', 'Movies']
series_selector = '#ddmcc_container > div > ul > ul > li > a'

urls = {'Dubbed': 'https://www.watchcartoononline.io/dubbed-anime-list',
        'Subbed': 'https://www.watchcartoononline.io/subbed-anime-list',
        'Cartoon': 'https://www.watchcartoononline.io/cartoon-list',
        'OVA': 'https://www.watchcartoononline.io/ova-list',
        'Movies': 'https://www.watchcartoononline.io/movie-list'}

series = {c: [] for c in categories}
episode_cache = {c: dict() for c in categories}
episode_re = re.compile('file: "(?P<url>.*)"')
loaded = False


def get_series_from_url(url):
    s = []
    res = requests.get(url)
    if res:
        soup = bs4.BeautifulSoup(res.text, 'lxml')
        nodes = soup.select(series_selector)
        for node in nodes:
            title = node.contents[0]
            link = node['href']
            s.append((title, link))

    return sorted(s)


def get_movies_or_ovas(category, series_name):
    return []


def get_dubbed_subbed_cartoon(category, series_name):
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
                tables = soup.select('#sidebar > table')
                nodes = tables[0].select('tr > td > div > div > li > a')
                for node in nodes:
                    episodes.append((node.contents[0], node['href']))
            episodes.reverse()
            series_cache[series_name] = episodes
            return episodes
    return episodes


def get_series_episodes(category, series_name):
    if category in ['Movies', 'OVA']:
        return get_movies_or_ovas(category, series_name)
    elif category in ['Dubbed', 'Subbed', 'Cartoon']:
        return get_dubbed_subbed_cartoon(category, series_name)
    return []


def find_best_quality(urls):
    tests = ['1080p', '720p']
    for test in tests:
        for url in urls:
            if test in url:
                return url
    return urls[0]


def get_video_url(category, series_name, episode_title):
    link = None
    for l in episode_cache[category][series_name]:
        if l[0] == episode_title:
            link = l[1]
            break

    if not link:
        return None

    res = requests.get(link)
    if res:
        soup = bs4.BeautifulSoup(res.text, 'lxml')
        iframes = soup.select('iframe')
        frame_url = None
        for frame in iframes:
            if frame.has_attr('id') and frame['id'].startswith('frame'):
                frame_url = frame['src']
                break

        if not frame_url:
            return None

        post_data = {'fuck_you': '', 'confirm': 'Click+Here+to+Watch+Free%21%21'}
        res = requests.post(frame_url, data=post_data)
        if res:
            matches = episode_re.findall(res.text)
            if matches:
                return find_best_quality(matches)
    return None


def load():
    global loaded
    series['Dubbed'] = get_series_from_url(urls['Dubbed'])
    series['Subbed'] = get_series_from_url(urls['Subbed'])
    series['Cartoon'] = get_series_from_url(urls['Cartoon'])
    series['Movies'] = ('Movies', urls['Movies'])
    series['OVA'] = ('OVA', urls['OVA'])
    loaded = True

if __name__ == '__main__':
    load()
    get_series_episodes('Dubbed', 'Fairy Tail (Official Dub)')
    print(get_video_url('Dubbed', 'Fairy Tail (Official Dub)', 'Fairy Tail Episode 252 English Dubbed'))
    s4 = 2
