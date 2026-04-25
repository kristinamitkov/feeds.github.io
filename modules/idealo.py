import re
import urllib.parse
from typing import Any, Dict

import bs4
import database
import requests
import utils


def idealo_get(_url: str):
    # 1) Create session
    _session = requests.Session()

    # 2) Set cookies
    _session.cookies.set('consentStatus', 'false')

    # 3) Create headers
    _headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:149.0) Gecko/20100101 Firefox/149.0'
    }

    # 4) GET request
    _response = _session.get(_url, headers=_headers)

    return _response

def idealo_parse(_data: str, _link: str) -> Dict[str, Any]:
    # 1) Parse HTML data
    _soup = bs4.BeautifulSoup(_data, 'html.parser')

    # 2) Get elements
    _title = _soup.find('h1', id='oopStage-title')

    _meta = _soup.find('div', class_='oopStage-metaInfo')
    _meta_offers = _meta.find('span', class_='oopStage-priceRangeOffers')
    _meta_price = _meta.find('span', class_='oopStage-priceRangePrice')
    _meta_grade = _meta.find('span', class_='oopStage-metaInfoItemTestsReportGrade')

    _pubDate = _soup.find('li', class_='productOffers-listItemImportTime')

    _variants = _soup.find('h2', class_='text-sm')

    _offers = _soup.find('div', id='offerList')
    _offers_titles = _offers.find_all('div', class_='productOffers-listItemTitleWrapper')
    _offers_prices = _offers.find_all('div', class_='price-column')
    _offers_shop = _offers.find_all('div', class_='productOffers-listItemOfferShopV2Block')
    _offers_shop_link = _offers.find_all('a', class_='productOffers-listItemOfferCtaLeadout')

    assert(len(_offers_titles) == len(_offers_prices))
    assert(len(_offers_prices) == len(_offers_shop))
    assert(len(_offers_shop) == len(_offers_shop_link))

    # 3) Return data as a JSON dict
    return {
        'title': utils.clear_text(_title.get_text()),
        'link': _link,
        'pubDate': utils.clear_text(_pubDate.get_text()),
        'offers': utils.clear_text(_meta_offers.get_text()).rstrip(':'),
        'prices': utils.clear_text(_meta_price.get_text()),
        'grade': utils.clear_text(_meta_grade.get_text()),
        'variants': utils.clear_text(_variants.get_text()),
        'items': [
            {
                'title': utils.clear_text(_entry[0].get_text()),
                'price': utils.clear_text(_entry[1].get_text()),
                'shop': utils.clear_text(_entry[2].get_text()),
                'link': 'https://www.idealo.de' + _entry[3]['href'].strip(),
                'pubDate': utils.clear_text(_pubDate.get_text()),
            }
            for _entry in zip(_offers_titles, _offers_prices, _offers_shop, _offers_shop_link)
        ]
    }

def idealo_store(_response: requests.Response, _data: Dict[str, Any]):
    def _idealo_date(_date: str):
        _date = re.search(r'\d{2}\.\d{2}\.\d{4} \d{1,2}:\d{1,2}', _date.strip()).group()
        return utils.parse_date(_date, "%d.%m.%Y %H:%M")

    # 0) Pre-process some data
    _data_offers = int(re.search(r'[0-9]+', _data['offers']).group())
    _data_price = int(re.search(r'[0-9]+', _data['prices']).group())

    _pubDate = _idealo_date(_data['pubDate'])

    # 1) Save data
    # 1.1) Parse URL
    _url_parsed = urllib.parse.urlparse(_data['link'] or '')

    # 1.2) Create save path
    _path = _url_parsed.netloc + _url_parsed.path[:-5]
    _path = re.sub(r'[^a-zA-Z0-9]', '_', _path)
    _path = re.sub(r'__+', '_', _path)
    _path = 'data/' + _path + '_' + utils.parse_timestamp(_pubDate, '%Y%m%d') + '.html'

    # 1.3) Save data
    with open(_path, mode='wb') as _file:
        _file.write(_response.content)

    # 2) Get or create task
    _task = database.add_task(_data['title'], _data['link'], _pubDate, _response.status_code, _response.reason, (None if _response.ok else (_response.text or _response.reason)))

    # 3) Create or update product
    database.add_product(_data['title'], _data['link'], 'EUR', _data_price, _pubDate)

    # 4) Add price point
    database.add_price(_data['title'], _task, _data['link'], _pubDate, _data_price, 'EUR', _data_offers, _response.status_code, _response.reason, (None if _response.ok else (_response.text or _response.reason)))

def idealo(_url: str):
    _response = idealo_get(_url)
    _data_parsed = idealo_parse(_response.text, _url)
    idealo_store(_response, _data_parsed)
