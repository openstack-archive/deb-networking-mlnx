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

import glob
import sys

from networking_mlnx._i18n import _LE, _LI, _LW
from oslo_log import log as logging

from networking_mlnx.eswitchd.common import constants
from networking_mlnx.eswitchd.common import exceptions
from networking_mlnx.eswitchd.db import eswitch_db
from networking_mlnx.eswitchd.resource_mngr import ResourceManager
from networking_mlnx.eswitchd.utils import command_utils
from networking_mlnx.eswitchd.utils import pci_utils


LOG = logging.getLogger(__name__)

INVALID_PKEY = 'none'
DEFAULT_PKEY_IDX = '0'
PARTIAL_PKEY_IDX = '1'
DEFAULT_MASK = 0x7fff
DEFAULT_PKEY = '0xffff'


class eSwitchHandler(object):

    def __init__(self, fabrics=None):
        self.eswitches = {}
        self.pci_utils = pci_utils.pciUtils()
        self.rm = ResourceManager()
        self.devices = set()
        if fabrics:
            self.add_fabrics(fabrics)

    def add_fabrics(self, fabrics):
        res_fabrics = []
        for fabric, pf in fabrics:
            fabric_type = None

            if pf in ('autoib', 'autoeth'):
                fabric_type = pf.strip('auto')
                pf = self.pci_utils.get_auto_pf(fabric_type)
            else:
                fabric_type = self.pci_utils.get_interface_type(pf)
                verify_vendor_pf = (
                    self.pci_utils.verify_vendor_pf(pf, constants.VENDOR))
                if (not verify_vendor_pf or
                        not self.pci_utils.is_sriov_pf(pf) or
                        not self.pci_utils.is_ifc_module(pf, fabric_type)):
                    LOG.error(_LE("PF %s must have Mellanox Vendor ID"
                              ",SR-IOV and driver module "
                              "enabled. Terminating!") % pf)
                    sys.exit(1)

            if fabric_type:
                self.eswitches[fabric] = eswitch_db.eSwitchDB()
                self._add_fabric(fabric, pf, fabric_type)
                res_fabrics.append((fabric, pf, fabric_type))
            else:
                LOG.info(_LI("No fabric type for PF:%s.Terminating!") % pf)
                sys.exit(1)
        self.sync_devices()

    def sync_devices(self):
        devices, vm_ids = self.rm.scan_attached_devices()
        added_devs = {}
        removed_devs = {}
        added_devs = set(devices) - self.devices
        removed_devs = self.devices - set(devices)
        self._treat_added_devices(added_devs, vm_ids)
        self._treat_removed_devices(removed_devs)
        self.devices = set(devices)

    def _add_fabric(self, fabric, pf, fabric_type):
        self.rm.add_fabric(fabric, pf, fabric_type)
        self._config_port_up(pf)
        fabric_details = self.rm.get_fabric_details(fabric)

        for vf in fabric_details['vfs']:
            self.eswitches[fabric].create_port(vf, constants.VIF_TYPE_HOSTDEV)

    def _treat_added_devices(self, devices, vm_ids):
        for device in devices:
            dev, mac, fabric = device
            if fabric:
                self.eswitches[fabric].attach_vnic(
                    port_name=dev, device_id=vm_ids[dev], vnic_mac=mac)
                if self.eswitches[fabric].vnic_exists(mac):
                    self.eswitches[fabric].plug_nic(port_name=dev)
            else:
                LOG.info(_LI("No Fabric defined for device %s"), dev)

    def _treat_removed_devices(self, devices):
        for dev, mac in devices:
            fabric = self.rm.get_fabric_for_dev(dev)
            if fabric:
                self.eswitches[fabric].detach_vnic(vnic_mac=mac)
            else:
                LOG.info(_LI("No Fabric defined for device %s"), dev)

    def get_vnics(self, fabrics):
        vnics = {}
        for fabric in fabrics:
            eswitch = self._get_vswitch_for_fabric(fabric)
            if eswitch:
                vnics_for_eswitch = eswitch.get_attached_vnics()
                vnics.update(vnics_for_eswitch)
            else:
                LOG.error(_LE("No eSwitch found for Fabric %s"), fabric)
                continue
        LOG.info(_LI("vnics are %s"), vnics)
        return vnics

    def create_port(self, fabric, vnic_type, device_id, vnic_mac, pci_slot):
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            try:
                if eswitch.attach_vnic(
                        pci_slot, device_id, vnic_mac, pci_slot):
                    self._config_vf_mac_address(fabric, pci_slot, vnic_mac)
                else:
                    raise exceptions.MlxException('Failed to attach vnic')
            except (RuntimeError, exceptions.MlxException):
                LOG.error(_LE('Create port operation failed '))
                pci_slot = None
        else:
            LOG.error(_LE("No eSwitch found for Fabric %s"), fabric)

        return pci_slot

    def plug_nic(self, fabric, device_id, vnic_mac, pci_slot):
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            eswitch.port_table[pci_slot]['vnic'] = vnic_mac
            eswitch.port_policy.update(
                {vnic_mac:
                    {'vlan': None,
                     'dev': pci_slot,
                     'device_id': device_id}})

            self._config_vf_mac_address(fabric, pci_slot, vnic_mac)
            eswitch.plug_nic(pci_slot)
        else:
            LOG.error(_LE("No eSwitch found for Fabric %s"), fabric)

        return pci_slot

    def delete_port(self, fabric, vnic_mac):
        dev = None
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            dev = eswitch.detach_vnic(vnic_mac)
            if dev:
                self._config_vf_mac_address(fabric, dev)
        else:
            LOG.warning(_LW("No eSwitch found for Fabric %s"), fabric)
        return dev

    def port_release(self, fabric, vnic_mac):
        ret = None
        eswitch = self._get_vswitch_for_fabric(fabric)
        dev = eswitch.get_dev_for_vnic(vnic_mac)
        if dev:
            if (eswitch.get_port_state(dev) ==
                    constants.VPORT_STATE_UNPLUGGED):
                ret = self.set_vlan(
                    fabric, vnic_mac, constants.UNTAGGED_VLAN_ID)
                self.port_down(fabric, vnic_mac)
        eswitch = self._get_vswitch_for_fabric(fabric)
        eswitch.port_release(vnic_mac)
        return ret

    def port_up(self, fabric, vnic_mac):
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            dev = eswitch.get_dev_for_vnic(vnic_mac)
            if not dev:
                LOG.info(_LI("No device for MAC %s"), vnic_mac)

    def port_down(self, fabric, vnic_mac):
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            dev = eswitch.get_dev_for_vnic(vnic_mac)
            if dev:
                LOG.info(_LI("IB port for MAC %s doen't support "
                         "port down"), vnic_mac)
            else:
                LOG.info(_LI("No device for MAC %s"), vnic_mac)

    def set_vlan(self, fabric, vnic_mac, vlan):
        eswitch = self._get_vswitch_for_fabric(fabric)
        if eswitch:
            eswitch.set_vlan(vnic_mac, vlan)
            dev = eswitch.get_dev_for_vnic(vnic_mac)
            state = eswitch.get_port_state(dev)
            if dev:
                if state in (constants.VPORT_STATE_ATTACHED,
                             constants.VPORT_STATE_UNPLUGGED):
                    if eswitch.get_port_table()[dev]['alias']:
                        dev = eswitch.get_port_table()[dev]['alias']
                    try:
                        self._config_vlan_ib(fabric, dev, vlan)
                        return True
                    except RuntimeError:
                        LOG.error(_LE('Set VLAN operation failed'))
        return False

    def get_eswitch_tables(self, fabrics):
        tables = {}
        for fabric in fabrics:
            eswitch = self._get_vswitch_for_fabric(fabric)
            if eswitch:
                tables[fabric] = {
                    'port_table': eswitch.get_port_table_matrix(),
                    'port_policy': eswitch.get_port_policy_matrix()
                }
            else:
                LOG.info(_LI("Get eswitch tables: No eswitch %s") % fabric)
        return tables

    def _get_vswitch_for_fabric(self, fabric):
        if fabric in self.eswitches:
            return self.eswitches[fabric]
        else:
            return

    def _config_vf_pkey(self, ppkey_idx, pkey_idx,
                        pf_mlx_dev, vf_pci_id, hca_port):
        path = constants.PKEY_INDEX_PATH % (pf_mlx_dev, vf_pci_id,
                                            hca_port, pkey_idx)
        cmd = ['ebrctl', 'write-sys', path, ppkey_idx]
        command_utils.execute(*cmd)

    def _get_guid_idx(self, pf_mlx_dev, dev, hca_port):
        path = constants.GUID_INDEX_PATH % (pf_mlx_dev, dev, hca_port)
        with open(path) as fd:
            idx = fd.readline().strip()
        return idx

    def _get_guid_from_mac(self, mac, device_type):
        guid = None
        if device_type == constants.CX3_VF_DEVICE_TYPE:
            if mac is None:
                guid = constants.INVALID_GUID_CX3
            else:
                mac = mac.replace(':', '')
                prefix = mac[:6]
                suffix = mac[6:]
                guid = prefix + '0000' + suffix
        elif device_type == constants.CX4_VF_DEVICE_TYPE:
            if mac is None:
                guid = constants.INVALID_GUID_CX4
            else:
                prefix = mac[:9]
                suffix = mac[9:]
                guid = prefix + '00:00:' + suffix
        return guid

    def _config_vf_mac_address(self, fabric, dev, vnic_mac=None):
        fabric_details = self.rm.get_fabric_details(fabric)
        vf_device_type = fabric_details['vfs'][dev]['vf_device_type']
        vguid = self._get_guid_from_mac(vnic_mac, vf_device_type)
        if vf_device_type == constants.CX3_VF_DEVICE_TYPE:
            self._config_vf_mac_address_cx3(vguid, dev, fabric_details)
        elif vf_device_type == constants.CX4_VF_DEVICE_TYPE:
            self._config_vf_mac_address_cx4(vguid, dev, fabric_details)
        else:
            LOG.error(_LE("Unsupported vf device type: %s "),
                      vf_device_type)

    def _config_vf_mac_address_cx3(self, vguid, dev, fabric_details):
        hca_port = fabric_details['hca_port']
        pf_mlx_dev = fabric_details['pf_mlx_dev']
        self._config_vf_pkey(
            INVALID_PKEY, DEFAULT_PKEY_IDX, pf_mlx_dev, dev, hca_port)

        guid_idx = self._get_guid_idx(pf_mlx_dev, dev, hca_port)
        path = constants.ADMIN_GUID_PATH % (pf_mlx_dev, hca_port, guid_idx)
        cmd = ['ebrctl', 'write-sys', path, vguid]
        command_utils.execute(*cmd)
        ppkey_idx = self._get_pkey_idx(
            int(DEFAULT_PKEY, 16), pf_mlx_dev, hca_port)
        if ppkey_idx >= 0:
            self._config_vf_pkey(
                ppkey_idx, PARTIAL_PKEY_IDX, pf_mlx_dev, dev, hca_port)
        else:
            LOG.error(_LE("Can't find partial management pkey for"
                          "%(pf)s:%(dev)s"), {'pf': pf_mlx_dev, 'dev': dev})

    def _config_vf_mac_address_cx4(self, vguid, dev, fabric_details):
        vf_num = fabric_details['vfs'][dev]['vf_num']
        pf_mlx_dev = fabric_details['pf_mlx_dev']
        guid_node = constants.CX4_GUID_NODE_PATH % {'module': pf_mlx_dev,
                                                    'vf_num': vf_num}
        guid_port = constants.CX4_GUID_PORT_PATH % {'module': pf_mlx_dev,
                                                    'vf_num': vf_num}
        guid_poliy = constants.CX4_GUID_POLICY_PATH % {'module': pf_mlx_dev,
                                                       'vf_num': vf_num}
        for path in (guid_node, guid_port):
            cmd = ['ebrctl', 'write-sys', path, vguid]
            command_utils.execute(*cmd)

        cmd = ['ebrctl', 'write-sys', guid_poliy, 'Up\n']
        command_utils.execute(*cmd)

    def _config_vlan_ib(self, fabric, dev, vlan):
        fabric_details = self.rm.get_fabric_details(fabric)
        hca_port = fabric_details['hca_port']
        pf_mlx_dev = fabric_details['pf_mlx_dev']
        vf_device_type = fabric_details['vfs'][dev]['vf_device_type']
        if vf_device_type == constants.CX3_VF_DEVICE_TYPE:
            self._config_vlan_ib_cx3(vlan, pf_mlx_dev, dev, hca_port)
        elif vf_device_type == constants.CX4_VF_DEVICE_TYPE:
            pass
        else:
            LOG.error(_LE("Unsupported vf device type: %s "),
                      vf_device_type)

    def _config_vlan_ib_cx3(self, vlan, pf_mlx_dev, dev, hca_port):
        if vlan == 0:
            ppkey_idx = self._get_pkey_idx(
                int(DEFAULT_PKEY, 16), pf_mlx_dev, hca_port)
            if ppkey_idx >= 0:
                self._config_vf_pkey(
                    ppkey_idx, DEFAULT_PKEY_IDX, pf_mlx_dev, dev, hca_port)
        else:
            ppkey_idx = self._get_pkey_idx(str(vlan), pf_mlx_dev, hca_port)
            if ppkey_idx:
                self._config_vf_pkey(
                    ppkey_idx, DEFAULT_PKEY_IDX, pf_mlx_dev, dev, hca_port)

    def _get_pkey_idx(self, vlan, pf_mlx_dev, hca_port):
        PKEYS_PATH = "/sys/class/infiniband/%s/ports/%s/pkeys/*"
        paths = PKEYS_PATH % (pf_mlx_dev, hca_port)
        for path in glob.glob(paths):
            fd = open(path)
            pkey = fd.readline()
            fd.close()
            # the MSB in pkey is the membership bit ( 0 - partial, 1 - full)
            # the other 15 bit are the number of the pkey
            # so we want to remove the 16th bit when compare pkey file
            # to the vlan (pkey) we are looking for
            is_match = int(pkey, 16) & DEFAULT_MASK == int(vlan) & DEFAULT_MASK
            if is_match:
                return path.split('/')[-1]
        return None

    def _config_port_up(self, dev):
        cmd = ['ip', 'link', 'set', dev, 'up']
        command_utils.execute(*cmd)
