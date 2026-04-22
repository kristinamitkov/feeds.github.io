import re
import urllib.parse

def clear_text(_text: str) -> str:
    _text = _text.replace('\xad', '')
    _text = re.sub(r'\s+', ' ', re.sub(r'[\s\n\r\t]+', ' ', _text).strip()).strip()

    return _text

def get_origin(_url: str) -> str:
    _url_parsed = urllib.parse.urlparse(_url)
    return _url_parsed.scheme + '://' + _url_parsed.netloc
