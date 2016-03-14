#!/usr/bin/env python
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

import contextlib
import mock
import sys
sys.modules['ethtool'] = mock.Mock()

from networking_mlnx.eswitchd.utils import pci_utils
from networking_mlnx.tests import base


class TestPciUtils(base.TestCase):

    def setUp(self):
        super(TestPciUtils, self).setUp()
        self.pci_utils = pci_utils.pciUtils()

    def _assert_get_auto_pf_error(self, log_msg):
        with mock.patch.object(pci_utils, 'LOG') as LOG:
            self.assertRaises(SystemExit,
                              self.pci_utils.get_auto_pf, 'fabtype')
            LOG.error.assert_called_with(log_msg)

    def _test_get_auto_pf(self, devices=[], is_vendor_pf=True,
                          is_sriov=True, valid_fabric_type=True):
        ifcs = devices if valid_fabric_type else []
        return contextlib.nested(
            mock.patch('ethtool.get_devices', return_value=devices),
            mock.patch.object(self.pci_utils, 'verify_vendor_pf',
                              return_value=is_vendor_pf),
            mock.patch.object(self.pci_utils, 'is_sriov_pf',
                              return_value=is_sriov),
            mock.patch.object(self.pci_utils, 'filter_ifcs_module',
                              return_value=ifcs),
        )

    def test_get_auto_pf_no_mlnx_devices(self):
        log_msg = "Didn't find any Mellanox devices."
        with self._test_get_auto_pf():
            self._assert_get_auto_pf_error(log_msg)

        log_msg = "Didn't find any Mellanox devices."
        with self._test_get_auto_pf(devices=['device-1'], is_vendor_pf=False):
            self._assert_get_auto_pf_error(log_msg)

    def test_get_auto_pf_no_mlnx_sriov_devices(self):
        log_msg = "Didn't find Mellanox NIC with SR-IOV capabilities."
        with self._test_get_auto_pf(devices=['device-1'], is_sriov=False):
            self._assert_get_auto_pf_error(log_msg)

    def test_get_auto_pf_wrong_fabric_type(self):
        log_msg = ("Didn't find Mellanox NIC of type fabtype with "
                   "SR-IOV capabilites.")
        with self._test_get_auto_pf(devices=['device-1'],
                                    valid_fabric_type=False):
            self._assert_get_auto_pf_error(log_msg)

    def test_get_auto_pf_multiple_pfs(self):
        devices = ['device-1', 'device-2']
        log_msg = "Found multiple PFs %s. Configure Manually." % devices
        with self._test_get_auto_pf(devices=devices):
            self._assert_get_auto_pf_error(log_msg)
