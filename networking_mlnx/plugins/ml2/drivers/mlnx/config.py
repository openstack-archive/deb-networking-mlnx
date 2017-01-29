# Copyright 2017 Mellanox Technologies, Ltd
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from neutron.conf.agent import common as config
from oslo_config import cfg

from networking_mlnx._i18n import _


mlnx_ib_opts = [
    cfg.BoolOpt('update_client_id', default=True,
                help=_("In case of migration with IB update the port's "
                       "client ID accordantly.")),
]

cfg.CONF.register_opts(mlnx_ib_opts, "MLNX_IB")
config.register_agent_state_opts_helper(cfg.CONF)
