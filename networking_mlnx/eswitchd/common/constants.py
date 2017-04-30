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

VENDOR = '0x15b3'
VIF_TYPE_HOSTDEV = 'ib_hostdev'


VPORT_STATE_ATTACHED = 'attached'
VPORT_STATE_PENDING = 'pending'
VPORT_STATE_UNPLUGGED = 'unplugged'

UNTAGGED_VLAN_ID = 4095

INVALID_MAC = '00:00:00:00:00:00'

# MLNX4
MLNX4_ADMIN_GUID_PATH = "/sys/class/infiniband/%s/iov/ports/%s/admin_guids/%s"
MLNX4_GUID_INDEX_PATH = "/sys/class/infiniband/%s/iov/%s/ports/%s/gid_idx/0"
MLNX4_PKEY_INDEX_PATH = "/sys/class/infiniband/%s/iov/%s/ports/%s/pkey_idx/%s"

# MLNX5
MLNX5_GUID_NODE_PATH = ('/sys/class/infiniband/%(module)s/device/sriov/'
                      '%(vf_num)s/node')
MLNX5_GUID_PORT_PATH = ('/sys/class/infiniband/%(module)s/device/sriov/'
                      '%(vf_num)s/port')
MLNX5_GUID_POLICY_PATH = ('/sys/class/infiniband/%(module)s/device/sriov/'
                        '%(vf_num)s/policy')
UNBIND_PATH = '/sys/bus/pci/drivers/mlx5_core/unbind'
BIND_PATH = '/sys/bus/pci/drivers/mlx5_core/bind'

MLNX4_INVALID_GUID = 'ffffffffffffffff'
MLNX5_INVALID_GUID = 'ff:ff:ff:ff:ff:ff:ff:ff'

CONN_URL = '%(transport)s://%(addr)s:%(port)s'

MLNX4_VF_DEVICE_TYPE_LIST = ('0x1004', )
MLNX5_VF_DEVICE_TYPE_LIST = ('0x1014', '0x1016', '0x1018')

MLNX4_VF_DEVICE_TYPE = 'MLNX4'
MLNX5_VF_DEVICE_TYPE = 'MLNX5'

SOCKET_OS_PORT = '60001'
SOCKET_OS_TRANSPORT = 'tcp'
SOCKET_OS_ADDR = '0.0.0.0'
