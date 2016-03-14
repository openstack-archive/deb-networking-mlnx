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

import os
import shlex
import subprocess

from networking_mlnx._i18n import _LI
from oslo_config import cfg
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


def get_root_helper():
    root_helper = 'sudo neutron-rootwrap %s' % cfg.CONF.DAEMON.rootwrap_conf
    return root_helper


def execute(cmd, root_helper=None, process_input=None, addl_env=None,
            check_exit_code=True, return_stderr=False):
    if not root_helper:
        root_helper = get_root_helper()
    cmd = shlex.split(root_helper) + cmd
    cmd = map(str, cmd)
    LOG.info(_LI("Running command: %s") % " ".join(cmd))
    env = os.environ.copy()
    if addl_env:
        env.update(addl_env)
    obj = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           env=env)

    _stdout, _stderr = (process_input and
                        obj.communicate(process_input) or
                        obj.communicate())
    obj.stdin.close()
    m = ("\nCommand: %s\nExit code: %s\nStdout: %r\nStderr: %r" %
         (cmd, obj.returncode, _stdout, _stderr))
    LOG.info(m)
    if obj.returncode and check_exit_code:
        raise RuntimeError(m)
    return return_stderr and (_stdout, _stderr) or _stdout


def execute_bg(cmd, root_helper=None, log=None):
    if not root_helper:
        root_helper = get_root_helper()
    cmd = shlex.split(root_helper) + cmd
    cmd = map(str, cmd)
    LOG.info(_LI("Running command: %s") % " ".join(cmd))
