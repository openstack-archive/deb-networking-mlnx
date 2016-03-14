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

from neutron.i18n import _LE, _LI
from oslo_log import log as logging

from networking_mlnx.eswitchd.common import constants

LOG = logging.getLogger(__name__)


class BasicMessageHandler(object):
    MSG_ATTRS_MANDATORY_MAP = set()

    def __init__(self, msg):
        self.msg = msg

    def execute(self):
        raise Exception("execute method MUST be implemented!")

    def validate(self):
        ret = True
        msg_attr = set(self.msg.keys())
        for attr in self.MSG_ATTRS_MANDATORY_MAP:
            if attr not in msg_attr:
                return False
        if 'vnic_type' in self.msg.keys():
            ret = self.validate_vnic_type(self.msg['vnic_type'])
        return ret

    def validate_vnic_type(self, vnic_type):
        if vnic_type in (constants.VIF_TYPE_HOSTDEV, ):
            return True
        return False

    def build_response(self, status, reason=None, response=None):
        if status:
            msg = {'status': 'OK', 'response': response}
        else:
            msg = {'status': 'FAIL', 'reason': reason}
        return msg


class AttachVnic(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = set(['fabric', 'vnic_type',
                                   'device_id', 'vnic_mac',
                                   'dev_name'])

    def __init__(self, msg):
        super(AttachVnic, self).__init__(msg)

    def execute(self, eswitch_handler):
        fabric = self.msg['fabric']
        vnic_type = self.msg['vnic_type']
        device_id = self.msg['device_id']
        vnic_mac = (self.msg['vnic_mac']).lower()
        dev_name = self.msg['dev_name']
        dev = eswitch_handler.create_port(
            fabric, vnic_type, device_id, vnic_mac, dev_name)
        if dev:
            return self.build_response(True, response={'dev': dev})
        else:
            return self.build_response(False, reason='Attach vnic failed')


class PlugVnic(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = ('fabric', 'device_id',
                               'vnic_mac', 'dev_name')

    def __init__(self, msg):
        super(PlugVnic, self).__init__(msg)

    def execute(self, eswitch_handler):
        fabric = self.msg['fabric']
        device_id = self.msg['device_id']
        vnic_mac = (self.msg['vnic_mac']).lower()
        dev_name = self.msg['dev_name']

        dev = eswitch_handler.plug_nic(fabric, device_id, vnic_mac, dev_name)
        if dev:
            return self.build_response(True, response={'dev': dev})
        else:
            return self.build_response(False, reason='Plug vnic failed')


class DetachVnic(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = ('fabric', 'vnic_mac')

    def __init__(self, msg):
        super(DetachVnic, self).__init__(msg)

    def execute(self, eswitch_handler):
        fabric = self.msg['fabric']
        vnic_mac = (self.msg['vnic_mac']).lower()
        dev = eswitch_handler.delete_port(fabric, vnic_mac)
        if dev:
            return self.build_response(True, response={'dev': dev})
        else:
            return self.build_response(True, response={})


class SetVLAN(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = ('fabric', 'port_mac', 'vlan')

    def __init__(self, msg):
        super(SetVLAN, self).__init__(msg)

    def execute(self, eswitch_handler):
        fabric = self.msg['fabric']
        vnic_mac = (self.msg['port_mac']).lower()
        vlan = self.msg['vlan']
        ret = eswitch_handler.set_vlan(fabric, vnic_mac, vlan)
        reason = None
        if not ret:
            reason = 'Set VLAN Failed'
        if reason:
            return self.build_response(False, reason=reason)
        return self.build_response(True, response={})


class GetVnics(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = ('fabric', )

    def __init__(self, msg):
        super(GetVnics, self).__init__(msg)

    def execute(self, eswitch_handler):
        fabric = self.msg['fabric']
        if fabric == '*':
            fabrics = eswitch_handler.eswitches.keys()
            LOG.info(_LI("fabrics = %s") % fabrics)
        else:
            fabrics = [fabric]
        vnics = eswitch_handler.get_vnics(fabrics)
        return self.build_response(True, response=vnics)


class PortRelease(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = ('fabric', 'ref_by', 'mac')

    def __init__(self, msg):
        super(PortRelease, self).__init__(msg)

    def execute(self, eswitch_handler):
        ref_by_keys = ['mac_address']
        fabric = self.msg['fabric']
        vnic_mac = (self.msg['mac']).lower()
        ref_by = self.msg['ref_by']
        reason = None
        if ref_by not in ref_by_keys:
            reason = "reb_by %s is not supported" % ref_by
        else:
            try:
                eswitch_handler.port_release(fabric, vnic_mac)
            except Exception:
                reason = "port release failed"
                LOG.exception(_LE("PortRelease failed"))
        if reason:
            return self.build_response(False, reason=reason)
        return self.build_response(True, response={})


class SetFabricMapping(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = ('fabric', 'interface')

    def __init__(self, msg):
        super(SetFabricMapping, self).__init__(msg)

    def execute(self, eswitch_handler):
        fabric = self.msg['fabric']
        interface = self.msg['interface']
        response = {'fabric': fabric, 'dev': interface}
        return self.build_response(True, response=response)


class PortUp(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = ('fabric', 'mac')

    def __init__(self, msg):
        super(PortUp, self).__init__(msg)

    def execute(self, eswitch_handler):
        # fabric = self.msg['fabric']
        # mac = self.msg['mac']
        # eswitch_handler.port_up(fabric, mac)
        return self.build_response(True, response={})


class PortDown(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = ('fabric', 'mac')

    def __init__(self, msg):
        super(PortDown, self).__init__(msg)

    def execute(self, eswitch_handler):
        # fabric = self.msg['fabric']
        # mac = self.msg['mac']
        # eswitch_handler.port_down(fabric, mac)
        return self.build_response(True, response={})


class GetEswitchTables(BasicMessageHandler):
    MSG_ATTRS_MANDATORY_MAP = ('fabric',)

    def __init__(self, msg):
        super(GetEswitchTables, self).__init__(msg)

    def execute(self, eswitch_handler):
        fabric = self.msg.get('fabric', '*')
        if fabric == '*':
            fabrics = eswitch_handler.eswitches.keys()
            LOG.info(_LI("fabrics = %s"), fabrics)
        else:
            fabrics = [fabric]
        response = {'tables': eswitch_handler.get_eswitch_tables(fabrics)}
        return self.build_response(True, response=response)


class MessageDispatch(object):
    MSG_MAP = {'create_port': AttachVnic,
               'delete_port': DetachVnic,
               'set_vlan': SetVLAN,
               'get_vnics': GetVnics,
               'port_release': PortRelease,
               'port_up': PortUp,
               'port_down': PortDown,
               'define_fabric_mapping': SetFabricMapping,
               'plug_nic': PlugVnic,
               'get_eswitch_tables': GetEswitchTables}

    def __init__(self, eswitch_handler):
        self.eswitch_handler = eswitch_handler

    def handle_msg(self, msg):
        LOG.info(_LI("Handling message - %s"), msg)
        result = {}
        action = msg.pop('action')

        if action in MessageDispatch.MSG_MAP.keys():
            msg_handler = MessageDispatch.MSG_MAP[action](msg)
            if msg_handler.validate():
                result = msg_handler.execute(self.eswitch_handler)
            else:
                LOG.error(_LE('Invalid message - cannot handle'))
                result = {'status': 'FAIL', 'reason': 'validation failed'}
        else:
            LOG.error(_LE("Unsupported action - %s"), action)
            result = {'action': action, 'status': 'FAIL',
                      'reason': 'unknown action'}
        result['action'] = action
        return result
