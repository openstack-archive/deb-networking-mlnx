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

    def add_fabric(self, fabric, pf, hca_port, pf_mlx_dev):
        pf_details = {}
        pf_details['vfs'] = {}
        pf_details['pf_device_type'] = None
        pf_details['hca_port'] = hca_port
        pf_details['pf_mlx_dev'] = pf_mlx_dev
        if self.device_db.get(fabric) is None:
            self.device_db[fabric] = {pf: pf_details}
        else:
            self.device_db[fabric][pf] = pf_details

    def get_fabric_details(self, fabric, pf=None):
        if pf is None:
            return self.device_db[fabric]
        else:
            return self.device_db[fabric][pf]

    def set_fabric_devices(self, fabric, pf, vfs):
        self.device_db[fabric][pf]['vfs'] = vfs
        vf = six.next(six.itervalues(vfs))
        self.device_db[fabric][pf]['pf_device_type'] = vf['vf_device_type']

    def get_dev_fabric(self, dev):
        for fabric in self.device_db:
            for pf in self.device_db[fabric]:
                if dev in self.device_db[fabric][pf]['vfs']:
                    return fabric
