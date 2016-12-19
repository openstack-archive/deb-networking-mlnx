# Copyright 2016 Mellanox Technologies, Ltd
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_config import cfg
from oslo_log import log
from oslo_serialization import jsonutils
import requests

from networking_mlnx.plugins.ml2.drivers.sdn import config
from networking_mlnx.plugins.ml2.drivers.sdn import constants as sdn_const
from networking_mlnx.plugins.ml2.drivers.sdn import exceptions as sdn_exc
from networking_mlnx.plugins.ml2.drivers.sdn import utils as sdn_utils

LOG = log.getLogger(__name__)
cfg.CONF.register_opts(config.sdn_opts, sdn_const.GROUP_OPT)


class SdnRestClient(object):

    MANDATORY_ARGS = ('url', 'username', 'password')

    @classmethod
    def create_client(cls):
        return cls(
            cfg.CONF.sdn.url,
            cfg.CONF.sdn.domain,
            cfg.CONF.sdn.username,
            cfg.CONF.sdn.password,
            cfg.CONF.sdn.timeout)

    def __init__(self, url, domain, username, password, timeout):
        self.url = url
        self.domain = domain
        self.timeout = timeout
        self.username = username
        self.password = password
        self._validate_mandatory_params_exist()
        self.url.rstrip("/")

    def _validate_mandatory_params_exist(self):
        for arg in self.MANDATORY_ARGS:
            if not getattr(self, arg):
                raise cfg.RequiredOptError(
                    arg, cfg.OptGroup(sdn_const.GROUP_OPT))

    def _get_session(self):
        login_url = sdn_utils.strings_to_url(str(self.url), "login")
        login_data = "username=%s&password=%s" % (self.username,
                                                  self.password)
        login_headers = sdn_const.LOGIN_HTTP_HEADER
        try:
            session = requests.session()
            LOG.debug("Login to SDN Provider. Login URL %(url)s",
                     {'url': login_url})
            r = session.request(sdn_const.POST, login_url, data=login_data,
                                headers=login_headers, timeout=self.timeout)
            LOG.debug("request status: %d", r.status_code)
            r.raise_for_status()
        except Exception as e:
            raise sdn_exc.SDNLoginError(login_url=login_url, msg=e)
        return session

    def get(self, urlpath='', data=None):
        urlpath = sdn_utils.strings_to_url(self.url, urlpath)
        return self.request(sdn_const.GET, urlpath, data)

    def put(self, urlpath='', data=None):
        urlpath = sdn_utils.strings_to_url(self.url, self.domain, urlpath)
        return self.request(sdn_const.PUT, urlpath, data)

    def post(self, urlpath='', data=None):
        urlpath = sdn_utils.strings_to_url(self.url, self.domain, urlpath)
        return self.request(sdn_const.POST, urlpath, data)

    def delete(self, urlpath='', data=None):
        urlpath = sdn_utils.strings_to_url(self.url, self.domain, urlpath)
        return self.request(sdn_const.DELETE, urlpath, data)

    def request(self, method, urlpath='', data=None):
        data = jsonutils.dumps(data, indent=2) if data else None
        session = self._get_session()

        LOG.debug("Sending METHOD %(method)s URL %(url)s JSON %(data)s",
                  {'method': method, 'url': urlpath, 'data': data})
        return self._check_rensponse(session.request(
                method, url=str(urlpath), headers=sdn_const.JSON_HTTP_HEADER,
                data=data, timeout=self.timeout))

    def _check_rensponse(self, response):
        try:
            LOG.debug("request status: %d", response.status_code)
            if response.text:
                LOG.debug("request text: %s", response.text)
            if response.status_code != requests.codes.not_implemented:
                response.raise_for_status()
        except Exception as e:
            raise sdn_exc.SDNConnectionError(msg=e)
        return response
