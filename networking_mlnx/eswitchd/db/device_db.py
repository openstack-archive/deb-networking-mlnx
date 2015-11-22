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
import six

LOG = logging.getLogger(__name__)


class DeviceDB(object):
    def __init__(self):
        self.device_db = {}

    def get_pf(self, fabric):
        return self.device_db[fabric]['pf']

    def add_fabric(self, fabric, pf, pci_id, hca_port, fabric_type,
                   pf_mlx_dev):
        details = {}
        details['vfs'] = {}
        details['pf'] = pf
        details['pf_device_type'] = None
        details['pci_id'] = pci_id
        details['hca_port'] = hca_port
        details['fabric_type'] = fabric_type
        details['pf_mlx_dev'] = pf_mlx_dev
        self.device_db[fabric] = details

    def get_fabric_details(self, fabric):
        return self.device_db[fabric]

    def set_fabric_devices(self, fabric, vfs):
        self.device_db[fabric]['vfs'] = vfs
        vf = six.next(six.itervalues(vfs))
        self.device_db[fabric]['pf_device_type'] = vf['vf_device_type']

    def get_dev_fabric(self, dev):
        for fabric in self.device_db:
            if dev in self.device_db[fabric]['vfs']:
                return fabric
