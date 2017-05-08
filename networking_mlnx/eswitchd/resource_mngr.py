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

from lxml import etree

import libvirt
from networking_mlnx._i18n import _LE, _LI, _LW
from oslo_log import log as logging

from networking_mlnx.eswitchd.common import constants
from networking_mlnx.eswitchd.db import device_db
from networking_mlnx.eswitchd.utils import pci_utils

LOG = logging.getLogger(__name__)


class ResourceManager(object):

    def __init__(self):
        self.pci_utils = pci_utils.pciUtils()
        self.device_db = device_db.DeviceDB()

    def add_fabric(self, fabric, pf, fabric_type):
        pci_id, hca_port, pf_mlx_dev = self._get_pf_details(pf)
        self.device_db.add_fabric(fabric, pf, pci_id, hca_port, fabric_type,
                                  pf_mlx_dev)
        vfs = self.discover_devices(pf)
        LOG.info(_LI("PF %(pf)s, vfs = %(vf)s"), {'pf': pf, 'vf': vfs})
        self.device_db.set_fabric_devices(fabric, pf, vfs)

    def scan_attached_devices(self):
        devices = []
        vm_ids = {}
        conn = libvirt.openReadOnly('qemu:///system')
        domains = []
        self.macs_map = self._get_vfs_macs()
        domains_names = conn.listDefinedDomains()
        defined_domains = map(conn.lookupByName, domains_names)
        domains_ids = conn.listDomainsID()
        running_domains = map(conn.lookupByID, domains_ids)
        for domain in defined_domains:
            [state, maxmem, mem, ncpu, cputime] = domain.info()
            if state in (libvirt.VIR_DOMAIN_PAUSED,
                         libvirt.VIR_DOMAIN_SHUTDOWN,
                         libvirt.VIR_DOMAIN_SHUTOFF):
                domains.append(domain)
        domains += running_domains

        for domain in domains:
            raw_xml = domain.XMLDesc(0)
            tree = etree.XML(raw_xml)
            hostdevs = tree.xpath("devices/hostdev/source/address")
            vm_id = tree.find('uuid').text
            for dev in self._get_attached_hostdevs(hostdevs):
                devices.append(dev)
                vm_ids[dev[0]] = vm_id
        return devices, vm_ids

    def get_fabric_details(self, fabric, pf=None):
        return self.device_db.get_fabric_details(fabric, pf)

    def discover_devices(self, pf):
        return self.pci_utils.get_vfs_info(pf)

    def get_fabric_for_dev(self, dev):
        return self.device_db.get_dev_fabric(dev)

    def _get_vfs_macs(self):
        macs_map = {}
        fabrics = self.device_db.device_db.keys()
        for fabric in fabrics:
            fabric_details = self.device_db.get_fabric_details(fabric)
            try:
                macs_map[fabric] = \
                    self.pci_utils.get_vfs_macs_ib(fabric_details)
            except Exception:
                LOG.exception(_LE("Failed to get vfs macs for fabric %s "),
                              fabric)
                continue
        return macs_map

    def _get_attached_hostdevs(self, hostdevs):
        devs = []
        for hostdev in hostdevs:
            dev = self.pci_utils.get_device_address(hostdev)
            fabric = self.get_fabric_for_dev(dev)
            if fabric:
                fabric_details = self.get_fabric_details(fabric)
                for pf_fabric_details in fabric_details.values():
                    if (pf_fabric_details['pf_device_type'] ==
                        constants.MLNX4_VF_DEVICE_TYPE):
                        hca_port = pf_fabric_details['hca_port']
                        pf_mlx_dev = pf_fabric_details['pf_mlx_dev']
                        vf_index = self.pci_utils.get_guid_index(
                            pf_mlx_dev, dev, hca_port)
                    elif (pf_fabric_details['pf_device_type'] ==
                          constants.MLNX5_VF_DEVICE_TYPE):
                        if dev in pf_fabric_details['vfs']:
                            vf_index = pf_fabric_details['vfs'][dev]['vf_num']
                        else:
                            continue
                    try:
                        mac = self.macs_map[fabric][str(vf_index)]
                        devs.append((dev, mac, fabric))
                    except KeyError:
                        LOG.warning(_LW("Failed to retrieve Hostdev MAC"
                                        "for dev %s"), dev)
            else:
                LOG.info(_LI("No Fabric defined for device %s"), hostdev)
        return devs

    def _get_pf_details(self, pf):
        hca_port = self.pci_utils.get_eth_port(pf)
        pci_id = self.pci_utils.get_pf_pci(pf)
        pf_pci_id = self.pci_utils.get_pf_pci(pf, 'normal')
        pf_mlx_dev = self.pci_utils.get_pf_mlx_dev(pf_pci_id)
        return (pci_id, hca_port, pf_mlx_dev)
