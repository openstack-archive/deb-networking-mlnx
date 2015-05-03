# Copyright 2015 Mellanox Technologies, Ltd
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

import constants as sdn_const
import functools
import requests
from requests import auth
from requests import ConnectionError

from oslo_config import cfg
from oslo_log import log
from oslo_serialization import jsonutils

from neutron.i18n import _LE
from neutron.plugins.common import constants
from neutron.plugins.ml2 import driver_api as api

LOG = log.getLogger(__name__)


sdn_opts = [
        cfg.StrOpt('url',
                   help=_("HTTP URL of SDN Provider."),
                   ),
        cfg.StrOpt('username',
                   help=_("HTTP username for authentication."),
                   ),
        cfg.StrOpt('password',
                   help=_("HTTP password for authentication."),
                   secret=True
                   ),
        cfg.IntOpt('timeout',
                   help=_("HTTP timeout in seconds."),
                   default=10
                   ),
]

cfg.CONF.register_opts(sdn_opts, sdn_const.GROUP_OPT)


class SDNConnectionError(ConnectionError):

    def __init__(self, msg, dest_url):
        self.msg = msg
        self.dest_url = dest_url

    def __str__(self):
        return (("failed to send request to URL: "
                "%s: %s") % (str(self.dest_url), str(self.msg)))

    def __repr__(self):
        return str(self)


def context_validator(context_type=None):
    def real_decorator(func):
        @functools.wraps(func)
        def wrapper(instance, context, *args, **kwargs):
            if context_type == sdn_const.PORT_PATH:
                # port context contain network_context
                # which include the segments
                segments = getattr(context._network_context, "_segments", None)
            elif context_type == sdn_const.NETWORK_PATH:
                segments = getattr(context, "_segments", None)
            else:
                segments = getattr(context, "segments_to_bind", None)
            if segments and getattr(instance, "check_segments", None):
                if instance.check_segments(segments):
                    return func(instance, context, *args, **kwargs)
        return wrapper
    return real_decorator


def error_handler(func):
    @functools.wraps(func)
    def wrapper(instance, *args, **kwargs):
        try:
            return func(instance, *args, **kwargs)
        except Exception as (e):
            LOG.error(
                    _LE("%(function_name)s %(exception_desc)s"),
                    {'function_name': func.__name__,
                    'exception_desc': str(e)}
            )
    return wrapper


class SDNMechanismDriver(api.MechanismDriver):

    """Mechanism Driver for SDN.

    This driver send notifications to SDN provider.
    The notifications are for port/network changes.
    """

    def _validate_mandatory_params_exist(self):
        mandatory_args = ("url", "username", "password")
        for arg in mandatory_args:
            if not getattr(self, arg):
                raise cfg.RequiredOptError(arg, sdn_const.GROUP_OPT)

    def _strings_to_url(self, *args):
        return "/".join(args)

    def initialize(self):
        self.url = cfg.CONF.sdn.url
        self.username = cfg.CONF.sdn.username
        self.password = cfg.CONF.sdn.password
        self.timeout = cfg.CONF.sdn.timeout
        self._validate_mandatory_params_exist()
        self.auth = auth.HTTPBasicAuth(self.username, self.password)

    @context_validator(sdn_const.NETWORK_PATH)
    @error_handler
    def create_network_postcommit(self, context):
        network_dic = context._network
        self._send_json_http_request(method=sdn_const.POST,
                                urlpath=sdn_const.NETWORK_PATH,
                               data=network_dic)

    @context_validator(sdn_const.NETWORK_PATH)
    @error_handler
    def update_network_postcommit(self, context):
        network_dic = context._network
        urlpath = self._strings_to_url(sdn_const.NETWORK_PATH,
                                       network_dic['id'])
        self._send_json_http_request(method=sdn_const.PUT, urlpath=urlpath,
                               data=network_dic)

    @context_validator(sdn_const.NETWORK_PATH)
    @error_handler
    def delete_network_postcommit(self, context):
        network_dic = context._network
        urlpath = self._strings_to_url(sdn_const.NETWORK_PATH,
                                       network_dic['id'])
        self._send_json_http_request(method=sdn_const.DELETE, urlpath=urlpath,
                               data=network_dic)

    @context_validator(sdn_const.PORT_PATH)
    @error_handler
    def update_port_postcommit(self, context):
        port_dic = context._port
        urlpath_port = self._strings_to_url(sdn_const.PORT_PATH,
                                            port_dic['id'])
        self._send_json_http_request(method=sdn_const.PUT,
                                     urlpath=urlpath_port,
                                     data=port_dic)

    @context_validator(sdn_const.PORT_PATH)
    @error_handler
    def delete_port_postcommit(self, context):
        port_dic = context._port
        urlpath_port = self._strings_to_url(sdn_const.PORT_PATH,
                                            port_dic['id'])
        self._send_json_http_request(method=sdn_const.DELETE,
                                     urlpath=urlpath_port,
                                     data=port_dic)

    @context_validator()
    @error_handler
    def bind_port(self, context):
        port_dic = context._port
        if self._is_bind_port_in_compute(port_dic):
            self._send_json_http_request(method=sdn_const.POST,
                                         urlpath=sdn_const.PORT_PATH,
                                         data=port_dic)

    def _is_bind_port_in_compute(self, port_context):
        """Verify that bind port is occur in compute context

        The request HTTP will occur only when bind port is in a compute context
        The bind port can occur for example in network
        """
        device_owner = port_context['device_owner']
        return (device_owner and
                device_owner.lower().startswith(
                                        sdn_const.PORT_DEVICE_OWNER_COMPUTE))

    def check_segment(self, segment):
        """Verify if a segment is valid for the SDN MechanismDriver.

        Verify if the requested segment is supported by SDN MD and return True
        or False to indicate this to callers.
        """
        network_type = segment[api.NETWORK_TYPE]
        return network_type in [constants.TYPE_VLAN]

    def check_segments(self, segments):
        """Verify if there is a segment in a list of segments that valid for
         the SDN MechanismDriver.

        Verify if the requested segments are supported by SDN MD and return
        True or False to indicate this to callers.
        """
        if segments:
            for segment in segments:
                if self.check_segment(segment):
                    return True
        return False

    def _send_json_http_request(self, urlpath, data, method):
        """send json http request to the SDN provider
        """
        dest_url = "/".join([self.url, urlpath])

        data = jsonutils.dumps(data, indent=2)

        try:
            LOG.debug("Sending METHOD %(method)s URL %(url)s JSON %(data)s",
                      {'method': method, 'url': dest_url, 'data': data})
            r = requests.request(method, url=dest_url,
                                 headers=sdn_const.JSON_HTTP_HEADER,
                                 data=data, timeout=self.timeout,
                                 auth=self.auth)
            r.raise_for_status()
        except Exception as e:
            raise SDNConnectionError(e, dest_url)
