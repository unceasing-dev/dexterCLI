"""dexterCLI API utilities"""

import json
from urllib.parse import urlencode, urljoin

import requests


def api(profile, path, base='.', method=None, params=None, data=None):
    """Call the API and output the results to stdout"""
    # pylint: disable=too-many-arguments
    method = ('GET' if data is None else 'POST') if method is None else method
    url = urljoin(urljoin(profile['root'].rstrip('/') + '/', base), path)
    if profile.get('debug'):
        print(f'{method} {url}{"?" + urlencode(params) if params else ""}')
        if data:
            print(json.dumps(data, indent=2))
    response = requests.request(
        method,
        url,
        auth=('dexter', profile['api-key']),
        json=data,
        params=params,
        timeout=30
    )
    return response
