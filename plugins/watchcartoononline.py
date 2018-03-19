#! /usr/bin/env python3.6
import bs4
import requests
import re
import json
import base64

display_name = 'Watch Cartoon Online'
categories = ['Dubbed', 'Subbed', 'Cartoon', 'OVA', 'Movies']
series_selector = '#ddmcc_container > div > ul > ul > li > a'
base_url = 'https://www.watchcartoononline.io'
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
        scripts = soup.select('script')
        reg = re.compile(r'var [a-zA-Z]+ = ""')
        video_urls = []
        for s in scripts:
            if len(s.attrs) == 0:
                stmts = s.text.split(';')
                if reg.match(stmts[0]):
                    pos = stmts[1].find('=') + 1
                    arr = stmts[1][pos:]
                    js = json.loads(arr)

                    off = stmts[2].rfind(' ')
                    sub = int(stmts[2][off + 1: -1])

                    frame_text = ''.join([chr(int(re.sub(r'\D', '', str(base64.b64decode(x)))) - sub) for x in js])
                    frame_soup = bs4.BeautifulSoup(frame_text, 'lxml')
                    src = frame_soup.select_one('iframe')['src']

                    video_urls.append(base_url + src)

        for u in video_urls:
            res = requests.get(u)
            if res:
                matches = episode_re.findall(res.text)
                if matches:
                    return find_best_quality(matches)


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
