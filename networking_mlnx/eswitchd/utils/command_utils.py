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

from oslo_concurrency import processutils
from oslo_config import cfg
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


def get_root_helper():
    root_helper = 'sudo neutron-rootwrap %s' % cfg.CONF.DAEMON.rootwrap_conf
    return root_helper


def execute(*cmd, **kwargs):
    if kwargs.get('root_helper') is None:
        kwargs['run_as_root'] = True
        kwargs['root_helper'] = get_root_helper()
    return processutils.execute(*cmd, **kwargs)
