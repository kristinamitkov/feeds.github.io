import datetime
import re
import urllib.parse

def parse_timestamp(_ts: float, _format: str):
    _dt = datetime.datetime.fromtimestamp(_ts)
    return datetime.datetime.strftime(_dt, _format)

def parse_date(_date: str, _format: str):
    _dt = datetime.datetime.strptime(_date, _format)
    return _dt.timestamp()

def clear_text(_text: str):
    _text = _text.replace('\xad', '')
    _text = re.sub(r'\s+', ' ', re.sub(r'[\s\n\r\t]+', ' ', _text).strip()).strip()

    try:
        _text = _text.encode('latin1').decode('utf-8')
    except Exception as e:
        pass

    return _text

def get_origin(_url: str):
    _url_parsed = urllib.parse.urlparse(_url)
    return _url_parsed.scheme + '://' + _url_parsed.netloc
