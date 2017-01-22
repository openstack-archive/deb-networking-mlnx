#!/usr/bin/env python
# Copyright 2016 Mellanox Technologies, Ltd
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

from networking_mlnx.eswitchd.db import device_db
from networking_mlnx.tests import base


class TestDeviceDB(base.TestCase):

    def setUp(self):
        super(TestDeviceDB, self).setUp()
        self.device_db_inst = device_db.DeviceDB()

    def _add_fabric(self):
        fabric = "fabric"
        details = {}
        details['pf'] = "pf"
        details['pci_id'] = "0000:81:00"
        details['hca_port'] = 1
        details['fabric_type'] = "fabric_type"
        details['pf_mlx_dev'] = "mlx4_0"
        self.device_db_inst.add_fabric(fabric, details['pf'],
                details['pci_id'], details['hca_port'],
                details['fabric_type'], details['pf_mlx_dev'])

        return {"fabric": fabric, "details": details}

    def test_add_fabric(self):
        data = self._add_fabric()
        fabric = data["fabric"]
        details = data["details"]

        self.assertIn(fabric, self.device_db_inst.device_db)
        for key in details:
            self.assertEqual(details[key],
                self.device_db_inst.device_db[fabric][key])

    def test_get_fabric_details(self):
        data = self._add_fabric()
        fabric = data["fabric"]
        details = data["details"]

        self.assertIn(fabric, self.device_db_inst.device_db)
        for key in details:
            self.assertEqual(details[key],
                self.device_db_inst.get_fabric_details(fabric)[key])

    def test_set_fabric_devices(self):
        self._add_fabric()
        fabric = "fabric"
        vfs = {}
        pci_id = "0000:81:00.1"
        vf_num = 8
        vf_device_type = "CX3"
        vfs[pci_id] = {'vf_num': vf_num, 'vf_device_type': vf_device_type}
        self.device_db_inst.set_fabric_devices(fabric, vfs)

        details = self.device_db_inst.get_fabric_details(fabric)
        self.assertIn(pci_id, details["vfs"])
        self.assertEqual(vf_num, details["vfs"][pci_id]["vf_num"])
        self.assertEqual(vf_device_type,
            details["vfs"][pci_id]["vf_device_type"])

    def test_get_dev_fabric_existent(self):
        self._add_fabric()
        fabric = "fabric"
        vfs = {}
        pci_id = "0000:81:00.1"
        vf_num = 8
        vf_device_type = "CX3"
        vfs[pci_id] = {'vf_num': vf_num, 'vf_device_type': vf_device_type}
        self.device_db_inst.set_fabric_devices(fabric, vfs)

        self.assertEqual(fabric, self.device_db_inst.get_dev_fabric(pci_id))

    def test_get_dev_fabric_inexistent(self):
        self.assertIsNone(self.device_db_inst.get_dev_fabric("inexistent_dev"))
