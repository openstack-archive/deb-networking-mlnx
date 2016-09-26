# Copyright 2013 Mellanox Technologies, Ltd
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

from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import importutils
import six

from networking_mlnx._i18n import _LE
from networking_mlnx.plugins.ml2.drivers.mlnx.agent import comm_utils
from networking_mlnx.plugins.ml2.drivers.mlnx.agent import exceptions

zmq = importutils.try_import('eventlet.green.zmq')

LOG = logging.getLogger(__name__)


class EswitchUtils(object):
    def __init__(self, daemon_endpoint, timeout):
        if not zmq:
            LOG.error(_LE("Failed to import eventlet.green.zmq. "
                          "Won't connect to eSwitchD - exiting..."))
            raise SystemExit(1)
        self.__conn = None
        self.daemon = daemon_endpoint
        self.timeout = timeout

    @property
    def _conn(self):
        if self.__conn is None:
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.LINGER, 0)
            socket.connect(self.daemon)
            self.__conn = socket
            self.poller = zmq.Poller()
            self.poller.register(self._conn, zmq.POLLIN)
        return self.__conn

    @comm_utils.RetryDecorator(exceptions.RequestTimeout)
    def send_msg(self, msg):
        self._conn.send(msg)

        socks = dict(self.poller.poll(self.timeout))
        if socks.get(self._conn) == zmq.POLLIN:
            recv_msg = self._conn.recv()
            response = self.parse_response_msg(recv_msg)
            return response
        else:
            self._conn.setsockopt(zmq.LINGER, 0)
            self._conn.close()
            self.poller.unregister(self._conn)
            self.__conn = None
            raise exceptions.RequestTimeout()

    def parse_response_msg(self, recv_msg):
        msg = jsonutils.loads(recv_msg)
        if msg['status'] == 'OK':
            if 'response' in msg:
                return msg.get('response')
            return
        elif msg['status'] == 'FAIL':
            msg_dict = dict(action=msg['action'], reason=msg['reason'])
            error_msg = _LE("Action %(action)s failed: %(reason)s") % msg_dict
        else:
            error_msg = _LE("Unknown operation status %s") % msg['status']
        LOG.error(error_msg)
        raise exceptions.OperationFailed(err_msg=error_msg)

    def get_attached_vnics(self):
        LOG.debug("get_attached_vnics")
        msg = jsonutils.dumps({'action': 'get_vnics', 'fabric': '*'})
        vnics = self.send_msg(msg)
        return vnics

    def set_port_vlan_id(self, physical_network,
                         segmentation_id, port_mac):
        LOG.debug("Set Vlan  %(segmentation_id)s on Port %(port_mac)s "
                  "on Fabric %(physical_network)s",
                  {'port_mac': port_mac,
                   'segmentation_id': segmentation_id,
                   'physical_network': physical_network})
        msg = jsonutils.dumps({'action': 'set_vlan',
                               'fabric': physical_network,
                               'port_mac': port_mac,
                               'vlan': segmentation_id})
        self.send_msg(msg)

    def define_fabric_mappings(self, interface_mapping):
        for fabric, phy_interface in six.iteritems(interface_mapping):
            LOG.debug("Define Fabric %(fabric)s on interface %(ifc)s",
                      {'fabric': fabric,
                       'ifc': phy_interface})
            msg = jsonutils.dumps({'action': 'define_fabric_mapping',
                                   'fabric': fabric,
                                   'interface': phy_interface})
            self.send_msg(msg)

    def port_up(self, fabric, port_mac):
        LOG.debug("Port Up for %(port_mac)s on fabric %(fabric)s",
                  {'port_mac': port_mac, 'fabric': fabric})
        msg = jsonutils.dumps({'action': 'port_up',
                               'fabric': fabric,
                               'ref_by': 'mac_address',
                               'mac': 'port_mac'})
        self.send_msg(msg)

    def port_down(self, fabric, port_mac):
        LOG.debug("Port Down for %(port_mac)s on fabric %(fabric)s",
                  {'port_mac': port_mac, 'fabric': fabric})
        msg = jsonutils.dumps({'action': 'port_down',
                               'fabric': fabric,
                               'ref_by': 'mac_address',
                               'mac': port_mac})
        self.send_msg(msg)

    def port_release(self, fabric, port_mac):
        LOG.debug("Port Release for %(port_mac)s on fabric %(fabric)s",
                  {'port_mac': port_mac, 'fabric': fabric})
        msg = jsonutils.dumps({'action': 'port_release',
                               'fabric': fabric,
                               'ref_by': 'mac_address',
                               'mac': port_mac})
        self.send_msg(msg)

    def get_eswitch_ports(self, fabric):
        # TODO(irena) - to implement for next phase
        return {}

    def get_eswitch_id(self, fabric):
        # TODO(irena) - to implement for next phase
        return ""
