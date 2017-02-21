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

# CX3
ADMIN_GUID_PATH = "/sys/class/infiniband/%s/iov/ports/%s/admin_guids/%s"
GUID_INDEX_PATH = "/sys/class/infiniband/%s/iov/%s/ports/%s/gid_idx/0"
PKEY_INDEX_PATH = "/sys/class/infiniband/%s/iov/%s/ports/%s/pkey_idx/%s"

# CX4
CX4_GUID_NODE_PATH = ('/sys/class/infiniband/%(module)s/device/sriov/'
                      '%(vf_num)s/node')
CX4_GUID_PORT_PATH = ('/sys/class/infiniband/%(module)s/device/sriov/'
                      '%(vf_num)s/port')
CX4_GUID_POLICY_PATH = ('/sys/class/infiniband/%(module)s/device/sriov/'
                        '%(vf_num)s/policy')
UNBIND_PATH = '/sys/bus/pci/drivers/mlx5_core/unbind'
BIND_PATH = '/sys/bus/pci/drivers/mlx5_core/bind'

INVALID_GUID_CX3 = 'ffffffffffffffff'
INVALID_GUID_CX4 = 'ff:ff:ff:ff:ff:ff:ff:ff'

CONN_URL = '%(transport)s://%(addr)s:%(port)s'

CX3_VF_DEVICE_TYPE_LIST = ('0x1004', )
CX4_VF_DEVICE_TYPE_LIST = ('0x1014', '0x1016')
CX5_VF_DEVICE_TYPE_LIST = ('0x1018', )

CX3_VF_DEVICE_TYPE = 'CX3'
CX4_VF_DEVICE_TYPE = 'CX4'
CX5_VF_DEVICE_TYPE = 'CX5'

SOCKET_OS_PORT = '60001'
SOCKET_OS_TRANSPORT = 'tcp'
SOCKET_OS_ADDR = '0.0.0.0'
