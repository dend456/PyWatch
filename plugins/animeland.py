#! /usr/bin/env python3.6
import bs4
import requests
import re
import cfscrape


display_name = 'Anime Land'
categories = ['Dubbed', 'Movies']
series_selector = '#ddmcc_container > div > ul > ul > li > a'
dubbed_selector = '#meta > ul > li > a'

headers = {}
cookies = {}
urls = {'base':   'http://www3.animeland.tv',
        'Dubbed': 'http://www3.animeland.tv/anime-list',
        'Movies': 'http://www3.animeland.tv/anime-movie'}

series = {c: [] for c in categories}
episode_cache = {c: dict() for c in categories}
episode_re = re.compile('file: "(?P<url>.*)"')
episode_loader_re = re.compile(r'#load"\).load\(\'(?P<url>\/ep\.php\?a=.+&id=.+)\'')
loaded = False


def get_series_from_url(url):
    s = []
    res = requests.get(url, headers=headers, cookies=cookies)
    if res:
        soup = bs4.BeautifulSoup(res.text, 'lxml')
        nodes = soup.select(series_selector)
        for node in nodes:
            title = node.contents[0]
            link = node['href']
            s.append((title, link))

    return sorted(s)


def get_movies(series_name):
    return []


def get_dubbed(category, series_name):
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
            res = requests.get(link[1], headers=headers, cookies=cookies)
            if res:
                matches = episode_loader_re.findall(res.text)
                if matches:
                    loader_url = urls['base'] + matches[0]
                    res = requests.get(loader_url, headers=headers, cookies=cookies)
                    if res:
                        soup = bs4.BeautifulSoup(res.text, 'lxml')
                        nodes = soup.select(dubbed_selector)
                        for node in nodes:
                            episodes.append((node.contents[0], urls['base'] + node['href']))
                        episodes.reverse()
                        series_cache[series_name] = episodes
                        return episodes
    return episodes


def get_series_episodes(category, series_name):
    if category == 'Movies':
        return get_movies(series_name)
    elif category == 'Dubbed':
        return get_dubbed(category, series_name)
    return []


def get_video_url(category, series_name, episode_title):
    link = None
    for l in episode_cache[category][series_name]:
        if l[0] == episode_title:
            link = l[1]
            break

    if not link:
        return None

    res = requests.get(link, headers=headers, cookies=cookies)
    if res:
        soup = bs4.BeautifulSoup(res.text, 'lxml')
        iframe = soup.select('iframe#video')
        if iframe:
            frame_url = urls['base'] + iframe[0]['src']

        res = requests.get(frame_url, headers=headers, cookies=cookies)
        if res:
            matches = episode_re.findall(res.text)
            if matches:
                return matches[0]
    return None


def load():
    global cookies, headers, loaded
    cookies, user_agent = cfscrape.get_tokens(urls['base'])
    headers = {'User-Agent': user_agent}
    series['Dubbed'] = get_series_from_url(urls['Dubbed'])
    series['Movies'] = ('Movies', urls['Movies'])
    loaded = True

if __name__ == '__main__':
    load()
    print(get_series_episodes('Dubbed', '009-1'))
    print(get_video_url('Dubbed', '009-1', 'Episode 3'))
