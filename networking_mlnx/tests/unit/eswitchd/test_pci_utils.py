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
import six
import subprocess
import sys

sys.modules['ethtool'] = mock.Mock()

from networking_mlnx._i18n import _LE
from networking_mlnx.eswitchd.utils import pci_utils
from networking_mlnx.tests import base

if six.PY3:
    @contextlib.contextmanager
    def nested(*contexts):
        with contextlib.ExitStack() as stack:
            yield [stack.enter_context(c) for c in contexts]
else:
    nested = contextlib.nested


class TestPciUtils(base.TestCase):

    def setUp(self):
        super(TestPciUtils, self).setUp()
        self.pci_utils = pci_utils.pciUtils()

    def _assert_get_auto_pf_error(self, log_msg):
        with mock.patch.object(pci_utils, 'LOG') as LOG:
            self.assertRaises(SystemExit,
                              self.pci_utils.get_auto_pf, 'fabtype')
            LOG.error.assert_called_with(log_msg)

    def _test_get_auto_pf(self, devices=None, is_vendor_pf=True,
                          is_sriov=True, valid_fabric_type=True):
        devices = devices if devices else []
        ifcs = devices if valid_fabric_type else []
        return nested(
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

    def test_get_vfs_info_not_found_device(self):
        pf = "pf_that_does_not_exist"
        with mock.patch.object(pci_utils, 'LOG') as LOG:
            self.pci_utils.get_vfs_info(pf)
            LOG.error.assert_called_with(_LE("PCI device %s not found"), pf)

    def test_get_dev_attr_valid_attr(self):
        cmd = "find /sys/class/net/*/device/vendor | head -1 | cut -d '/' -f5"
        pf = subprocess.check_output(cmd, shell=True)
        pf = pf.strip().decode("utf-8")
        if pf:
            attr_path = "/sys/class/net/%s/device/vendor" % pf
            return_val = self.pci_utils.get_dev_attr(attr_path)
            self.assertIsNotNone(return_val)

    def test_get_dev_attr_invalid_attr(self):
        attr_path = "/path/that/does/not/exist"
        return_val = self.pci_utils.get_dev_attr(attr_path)
        self.assertIsNone(return_val)

    def test_verify_vendor_pf_valid_vendor(self):
        cmd = "find /sys/class/net/*/device/vendor | head -1 | cut -d '/' -f5"
        pf = subprocess.check_output(cmd, shell=True)
        pf = pf.strip().decode("utf-8")
        if pf:
            attr_path = "/sys/class/net/%s/device/vendor" % pf
            attr = subprocess.check_output("cat %s" % attr_path, shell=True)
            attr = attr.strip().decode("utf-8")
            return_val = self.pci_utils.verify_vendor_pf(pf, attr)
            self.assertTrue(return_val)

    def test_verify_vendor_pf_invalid_vendor(self):
        cmd = "ls -U /sys/class/net | head -1"
        pf = subprocess.check_output(cmd, shell=True)
        pf = pf.strip()
        attr = "0x0000"

        return_val = self.pci_utils.verify_vendor_pf(pf, attr)
        self.assertFalse(return_val)

    def test_is_sriov_pf_false(self):
        pf = "pf_that_does_not_exist"

        is_sriov = self.pci_utils.is_sriov_pf(pf)
        self.assertFalse(is_sriov)
