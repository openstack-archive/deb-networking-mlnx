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
import os
import re
import sys

import ethtool
from neutron.i18n import _LE, _LW
from oslo_log import log as logging

from networking_mlnx.eswitchd.common import constants
from networking_mlnx.eswitchd.utils.command_utils import execute

LOG = logging.getLogger(__name__)


class pciUtils(object):

    ETH_PATH = "/sys/class/net/%(interface)s"
    ETH_DEV = ETH_PATH + "/device"
    ETH_PORT = ETH_PATH + "/dev_id"
    PF_MLX_DEV_PATH = "/sys/class/infiniband/*"
    VENDOR_PATH = ETH_DEV + '/vendor'
    DEVICE_TYPE_PATH = ETH_DEV + '/virtfn%(vf_num)s/device'
    _VIRTFN_RE = re.compile("virtfn(?P<vf_num>\d+)")
    VFS_PATH = ETH_DEV + "/virtfn*"

    def get_vfs_info(self, pf):
        vfs_info = {}
        try:
            dev_path = self.ETH_DEV % {'interface': pf}
            dev_info = os.listdir(dev_path)
            for dev_filename in dev_info:
                result = self._VIRTFN_RE.match(dev_filename)
                if result and result.group('vf_num'):
                    dev_file = os.path.join(dev_path, dev_filename)
                    vf_pci = os.readlink(dev_file).strip("./")
                    vf_num = result.group('vf_num')
                    vf_device_type = self.get_vf_device_type(pf, vf_num)
                    vfs_info[vf_pci] = {'vf_num': vf_num,
                                        'vf_device_type': vf_device_type}
        except Exception:
            LOG.exception(_LE("PCI device %s not found"), pf)
        return vfs_info

    def get_dev_attr(self, attr_path):
        try:
            fd = open(attr_path)
            return fd.readline().strip()
        except IOError:
            return

    def verify_vendor_pf(self, pf, vendor_id=constants.VENDOR):
        vendor_path = pciUtils.VENDOR_PATH % {'interface': pf}
        if self.get_dev_attr(vendor_path) == vendor_id:
            return True
        else:
            return False

    def get_vf_device_type(self, pf, vf_num):
        device_vf_type = None
        device_type_file = pciUtils.DEVICE_TYPE_PATH % {'interface': pf,
                                                        'vf_num': vf_num}
        try:
            with open(device_type_file, 'r') as fd:
                device_type = fd.read()
                device_type = device_type.strip(os.linesep)
                if device_type in constants.CX3_VF_DEVICE_TYPE_LIST:
                    device_vf_type = constants.CX3_VF_DEVICE_TYPE
                elif device_type in constants.CX4_VF_DEVICE_TYPE_LIST:
                    device_vf_type = constants.CX4_VF_DEVICE_TYPE
                elif device_type in constants.CX5_VF_DEVICE_TYPE_LIST:
                    device_vf_type = constants.CX5_VF_DEVICE_TYPE
        except IOError:
            pass
        return device_vf_type

    def is_sriov_pf(self, pf):
        vfs_path = pciUtils.VFS_PATH % {'interface': pf}
        vfs = glob.glob(vfs_path)
        if vfs:
            return True
        else:
            return

    def get_interface_type(self, ifc):
        cmd = ['ip', '-o', 'link', 'show', 'dev', ifc]
        try:
            result = execute(cmd, root_helper=None)
        except Exception as e:
            LOG.warning(_LW("Failed to execute command %(cmd)s due to %(e)s"),
                    {"cmd": cmd, "e": e})
            raise
        if result.find('link/ether') != -1:
            return 'eth'
        elif result.find('link/infiniband') != -1:
            return 'ib'
        else:
            return None

    def is_ifc_module(self, ifc, fabric_type):
        modules = {'eth': 'mlx4_en', 'ib': 'ipoib'}
        if modules[fabric_type] in ethtool.get_module(ifc):
            return True

    def filter_ifcs_module(self, ifcs, fabric_type):
        return [ifc for ifc in ifcs if self.is_ifc_module(ifc, fabric_type)]

    def get_auto_pf(self, fabric_type):
        def log_error_and_exit(err_msg):
            LOG.error(err_msg)
            sys.exit(1)

        mlnx_pfs = [ifc for ifc in ethtool.get_devices()
                    if self.verify_vendor_pf(ifc)]
        if not mlnx_pfs:
            log_error_and_exit("Didn't find any Mellanox devices.")

        mlnx_pfs = [ifc for ifc in mlnx_pfs if self.is_sriov_pf(ifc)]
        if not mlnx_pfs:
            log_error_and_exit("Didn't find Mellanox NIC "
                               "with SR-IOV capabilities.")
        mlnx_pfs = self.filter_ifcs_module(mlnx_pfs, fabric_type)
        if not mlnx_pfs:
            log_error_and_exit("Didn't find Mellanox NIC of type %s with "
                               "SR-IOV capabilites." % fabric_type)
        if len(mlnx_pfs) != 1:
            log_error_and_exit("Found multiple PFs %s. Configure Manually."
                               % mlnx_pfs)
        return mlnx_pfs[0]

    def get_eth_vf(self, dev):
        vf_path = pciUtils.ETH_DEV % {'interface': dev}
        try:
            device = os.readlink(vf_path)
            vf = device.split('/')[3]
            return vf
        except Exception:
            return None

    def get_pf_pci(self, pf, type=None):
        vf = self.get_eth_vf(pf)
        if vf:
            if type == 'normal':
                return vf
            else:
                return vf[:-2]
        return None

    def get_pf_mlx_dev(self, pci_id):
        paths = glob.glob(pciUtils.PF_MLX_DEV_PATH)
        for path in paths:
            id = os.readlink(path).split('/')[5]
            if pci_id == id:
                return path.split('/')[-1]

    def get_guid_index(self, pf_mlx_dev, dev, hca_port):
        guid_index = None
        path = constants.GUID_INDEX_PATH % (pf_mlx_dev, dev, hca_port)
        with open(path) as fd:
            guid_index = fd.readline().strip()
        return guid_index

    def get_eth_port(self, dev):
        port_path = pciUtils.ETH_PORT % {'interface': dev}
        try:
            with open(port_path) as f:
                dev_id = int(f.read(), 0)
                return dev_id + 1
        except IOError:
            return

    def get_vfs_macs_ib(self, fabric_details):
        if fabric_details['pf_device_type'] == constants.CX3_VF_DEVICE_TYPE:
            return self.get_vfs_macs_ib_cx3(fabric_details)
        elif fabric_details['pf_device_type'] == constants.CX4_VF_DEVICE_TYPE:
            return self.get_vfs_macs_ib_cx4(fabric_details)

    def get_vfs_macs_ib_cx3(self, fabric_details):
        hca_port = fabric_details['hca_port']
        pf_mlx_dev = fabric_details['pf_mlx_dev']
        macs_map = {}
        guids_path = constants.ADMIN_GUID_PATH % (pf_mlx_dev, hca_port,
                                                  '[1-9]*')
        paths = glob.glob(guids_path)
        for path in paths:
            vf_index = path.split('/')[-1]
            with open(path) as f:
                guid = f.readline().strip()
                if guid == constants.INVALID_GUID_CX3:
                    mac = constants.INVALID_MAC
                else:
                    head = guid[:6]
                    tail = guid[-6:]
                    mac = ":".join(re.findall('..?', head + tail))
                macs_map[str(int(vf_index))] = mac
        return macs_map

    def get_vfs_macs_ib_cx4(self, fabric_details):
        vfs = fabric_details['vfs']
        macs_map = {}
        for vf in vfs.values():
            vf_num = vf['vf_num']
            pf_mlx_dev = fabric_details['pf_mlx_dev']
            guid_path = constants.CX4_GUID_NODE_PATH % {'module': pf_mlx_dev,
                                                        'vf_num': vf_num}
            with open(guid_path) as f:
                guid = f.readline().strip()
                head = guid[:8]
                tail = guid[-9:]
                mac = head + tail
            macs_map[vf_num] = mac
        return macs_map

    def get_device_address(self, hostdev):
        domain = hostdev.attrib['domain'][2:]
        bus = hostdev.attrib['bus'][2:]
        slot = hostdev.attrib['slot'][2:]
        function = hostdev.attrib['function'][2:]
        dev = "%.4s:%.2s:%2s.%.1s" % (domain, bus, slot, function)
        return dev
