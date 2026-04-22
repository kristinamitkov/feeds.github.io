import datetime
import hashlib
import pprint
import re
import sqlite3
import time
import urllib.parse
from typing import Any, Dict, List

import bs4
import database
import requests
import utils
import xml.dom.minidom
import xml.etree.ElementTree


def finanztip_get():
    # 1) Create session
    _session = requests.Session()

    # 2) Create headers
    _headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:149.0) Gecko/20100101 Firefox/149.0'
    }

    # 3) GET request
    _response = _session.get('https://www.finanztip.de/daily/', headers=_headers)

    # 4) Save data

    # 4.1) Create save path
    _path = 'www.finanztip.de/daily/'
    _path = re.sub(r'[^a-zA-Z0-9]', '_', _path)
    _path = re.sub(r'__+', '_', _path)
    _path = 'data/' + _path + datetime.datetime.now().strftime("%Y%m%d") + '.html'

    # 4.2) Save data
    with open(_path, mode='w') as _file:
        _file.write(_response.text)

    return _response.text

def finanztip_parse(_data: str) -> Dict[str, Any]:
    # 1) Parse HTML data
    _soup = bs4.BeautifulSoup(_data, 'html.parser')

    # 2) Get elements
    _title = _soup.find('h2', class_='heading-subtitle')
    _description = _soup.find('div', class_='tw-fc-hidden')

    _image = _soup.find('div', class_='main-image')
    assert(_image is not None)
    _image = _image.find('img')
    assert(_image)

    _image_url = _image.get('src', None)
    _image_title = _image.get('title', _image.get('alt'))
    assert(_image_url is not None)
    assert(_image_title is not None)
    _image_link = utils.get_origin(str(_image_url))

    _pubDate = _soup.find_all('time', class_='news-list-date')[0]

    _articles_container = _soup.find('div', class_='articles')

    assert(_articles_container is not None)

    _items: List[Dict[str, Any]] = []
    for _article in _articles_container.find_all('div', class_='article-daily-list'):
        assert(_article)

        _article_title = _article.find('h3', class_='daily-list-title')
        assert(_article_title)

        _article_description = _article.find('h3', class_='daily-list-title')
        _article_pubDate = _article.find('time')

        _article_image = _article.find('img', class_='lazy')
        assert(_article_image is not None)

        _article_image_src = _article_image.get('src', None)
        _article_image_title = _article_image.get('title', _article_image.get('alt'))
        assert(_article_image_src is not None)
        assert(_article_image_title is not None)
        _article_image_link = utils.get_origin(str(_article_image_src))

        _article_link = _article_title.find('a', href=True)
        assert(_article_link is not None)
        _artile_link_raw = _article_link.get('href', None)
        assert (_artile_link_raw is not None)

        assert(_article_description is not None)
        assert(_article_pubDate is not None)

        _items.append({
            'title': utils.clear_text(_article_title.get_text()),
            'description': utils.clear_text(_article_description.get_text()),
            'link': str(_artile_link_raw),
            'pubDate': utils.clear_text(_article_pubDate.get_text()),
            'image': {'url': str(_article_image_src), 'title': _article_image_title, 'link': _article_image_link},
        })

    assert(_title is not None)
    assert(_description is not None)
    assert(_pubDate is not None)

    # 4) Return data as a JSON dict
    return {
        'title': utils.clear_text(_title.get_text()),
        'description': utils.clear_text(_title.get_text()),
        'link': 'https://www.finanztip.de/daily/',
        'image': {'url': str(_image_url), 'title': str(_image_title), 'link': _image_link},
        'items': _items,
        'pubDate': utils.clear_text(_pubDate.get_text())
    }

def finanztip_rss(_data: Dict[str, Any]):
    def _finanztip_date(_date: str) -> str:
        _dt = datetime.datetime.strptime(_date, "%d.%m.%Y")
        return _dt.strftime("%a, %d %b %Y %H:%M:%S GMT")

    def _finanztip_link(_link: str) -> str:
        return _link if _link.startswith('http') else ('https://www.finanztip.de' + _link)

    # 1) Create RSS channel as an XML element
    _rss = xml.etree.ElementTree.Element("rss", version="2.0")
    _channel = xml.etree.ElementTree.SubElement(_rss, "channel")

    # 2) Top-level meta information
    xml.etree.ElementTree.SubElement(_channel, "title").text = _data["title"]
    xml.etree.ElementTree.SubElement(_channel, "link").text = _finanztip_link(_data["link"])
    xml.etree.ElementTree.SubElement(_channel, "description").text = _data["description"]
    xml.etree.ElementTree.SubElement(_channel, "pubDate").text = _finanztip_date(_data['pubDate'])
    xml.etree.ElementTree.SubElement(_channel, "language").text = "de-DE"

    _image_el = xml.etree.ElementTree.SubElement(_channel, "image")
    xml.etree.ElementTree.SubElement(_image_el, "url").text = _data["image"]["url"]
    xml.etree.ElementTree.SubElement(_image_el, "title").text = _data["image"]["title"]
    xml.etree.ElementTree.SubElement(_image_el, "link").text = _data["image"]["link"]

    # 3) Parse each item
    for _item in _data['items']:
        _item_el = xml.etree.ElementTree.SubElement(_channel, "item")

        xml.etree.ElementTree.SubElement(_item_el, "title").text = _item["title"]
        xml.etree.ElementTree.SubElement(_item_el, "link").text = _finanztip_link(_item["link"])
        xml.etree.ElementTree.SubElement(_item_el, "guid").text = hashlib.sha256(_finanztip_link(_item['link']).encode("utf-8")).hexdigest()
        xml.etree.ElementTree.SubElement(_item_el, "description").text = _item["description"]
        xml.etree.ElementTree.SubElement(_item_el, "pubDate").text = _finanztip_date(_item['pubDate'])

        # <enclosure url="https://cdn.finanztip.de/_generate/1/4/85415/Zeitung_Sparplaene_Geld_landscape.png?class=large" type="image/png"/>
        _item_image_el = xml.etree.ElementTree.SubElement(_item_el, "enclosure")
        _item_image_el.set('url', _item["image"]["url"])
        _item_image_el.set('type', 'image/png')
        
        # xml.etree.ElementTree.SubElement(_item_image_el, "url").text = _item["image"]["url"]
        # xml.etree.ElementTree.SubElement(_item_image_el, "type").text = "image/png"

    # 4) Save Data as a file
    _xml_str = xml.etree.ElementTree.tostring(_rss, encoding="utf-8")
    _xml_raw = xml.dom.minidom.parseString(_xml_str).toprettyxml(indent='  ', encoding='utf-8')

    # 4.1) Create save path
    _path_1 = 'www.finanztip.de/daily/'
    _path_1 = re.sub(r'[^a-zA-Z0-9]', '_', _path_1)
    _path_1 = re.sub(r'__+', '_', _path_1)

    _path_2 = 'data/' + _path_1 + '.rss'
    _path_1 = 'data/' + _path_1 + datetime.datetime.now().strftime("%Y%m%d") + '.rss'

    # 4.2) Save data
    with open(_path_1, mode='wb') as _file:
        _file.write(_xml_raw)
    with open(_path_2, mode='wb') as _file:
        _file.write(_xml_raw)

    # 5) Save data locally in DB
    _conn = sqlite3.connect(database.DATABASE)
    _cursor = _conn.cursor()

    # 1) Create or update product
    try:
        _cursor.execute(
            "INSERT INTO task (url, active, last) VALUES (?, 1, 0);",
            ('https://www.finanztip.de/daily/',)
        )
    except Exception:
        _cursor.execute(
            "UPDATE task SET last=? WHERE url=?;",
            (datetime.datetime.strptime(_data['pubDate'], "%d.%m.%Y").timestamp(), 'https://www.finanztip.de/daily/')
        )
    _conn.commit()

    _conn.close()

    return _xml_raw
