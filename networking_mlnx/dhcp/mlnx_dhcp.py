# Copyright 2015 Mellanox Technologies, Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from neutron.agent.linux import dhcp
from neutron.extensions import extra_dhcp_opt as edo_ext


class DhcpOpt(object):
    def __init__(self, **kwargs):
        self.__dict__.update(ip_version=4)
        self.__dict__.update(kwargs)

    def __str__(self):
        return str(self.__dict__)


class MlnxDnsmasq(dhcp.Dnsmasq):
    _PREFIX = 'ff:00:00:00:00:00:02:00:00:02:c9:00:'
    _MIDDLE = ':00:00:'

    def _gen_client_id(self, port):
        mac_address = port.mac_address
        mac_first = mac_address[:8]
        mac_last = mac_address[9:]
        client_id = ''.join([self._PREFIX, mac_first, self._MIDDLE, mac_last])
        return client_id

    def _gen_client_id_opt(self, client_id):
        return DhcpOpt(opt_name=edo_ext.CLIENT_ID, opt_value=client_id)

    def _get_port_extra_dhcp_opts(self, port):
        client_id = self._gen_client_id(port)
        if hasattr(port, edo_ext.EXTRADHCPOPTS):
            for opt in port.extra_dhcp_opts:
                if opt.opt_name == edo_ext.CLIENT_ID:
                    opt.opt_value = client_id
                    return port.extra_dhcp_opts
            port.extra_dhcp_opts.append(self._gen_client_id_opt(client_id))
        else:
            setattr(port, edo_ext.EXTRADHCPOPTS,
                    [self._gen_client_id_opt(client_id)])
        return port.extra_dhcp_opts
