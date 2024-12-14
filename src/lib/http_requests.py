from datetime import datetime
from pprint import pprint

import requests

class HTTPRequests:
    def __init__(self, config):
        """ESPKey HTTP request library

        Args:
            config (dict): Configuration form the configurator.
        """
        self.__config = config


    def http_get(self, url, auth=True):
        """Run an HTTP get request.

        Args:
            url (str): URL to request against.
            auth (bool, optional): Send basic creds with request. Defaults to True.

        Returns:
            bool: True for sccuess, False for failure.
        """

        request_kwargs = {}
        response = {
            "auth": False,
            "url": url
        }

        if auth:
            response.update({
                "auth": True,
            })

            request_kwargs.update({
                "auth": (self.__config['web_user'], self.__config['web_pass'])
            })

        r_dts = datetime.utcnow()
        r = requests.get(url, **request_kwargs)

        # Get relative timestamp frmo uC
        if 'Now' in r.headers:
            response.update({"now_header": r.headers['Now']})

        response.update({
            "headers": r.headers,
            "req_dts": r_dts,
            "status": r.status_code,
            "text": r.text
        })

        return response

        
    def http_form_post(self, url, file_name, data, auth=True):
        """Post a file as part of a form.

        Args:
            url (str): URL to post to.
            file_name (str): File name
            data (str): Data to send as file
            auth (bool, optional): Send basic creds with request. Defaults to True.

        Returns:
            bool: True for success, False for failure.
        """

        request_kwargs = {
            "files": {"file": (file_name, data)}
        }

        response = {
            "auth": False,
            "url": url
        }

        if auth:
            response.update({
                "auth": True,
            })

            request_kwargs.update({
                "auth": (self.__config['web_user'], self.__config['web_pass'])
            })

        r_dts = datetime.utcnow()
        r = requests.post(url, **request_kwargs)

        response.update({
            "headers": r.headers,
            "req_unix_ts": r_dts,
            "status": r.status_code,
            "text": r.text
        })

        return response
