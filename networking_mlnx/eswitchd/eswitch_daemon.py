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

import sys
import zmq

from networking_mlnx._i18n import _LE, _LI
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils

from networking_mlnx.eswitchd.common import config
from networking_mlnx.eswitchd.common import constants
from networking_mlnx.eswitchd.eswitch_handler import eSwitchHandler
import networking_mlnx.eswitchd.msg_handler as message
from networking_mlnx.eswitchd.utils.helper_utils import set_conn_url

LOG = logging.getLogger(__name__)


class MlxEswitchDaemon(object):
    def __init__(self):
        self.max_polling_count = cfg.CONF.DAEMON.max_polling_count
        self.default_timeout = cfg.CONF.DAEMON.default_timeout
        fabrics = self._parse_physical_mapping()
        self.eswitch_handler = eSwitchHandler(fabrics)
        self.dispatcher = message.MessageDispatch(self.eswitch_handler)

    def start(self):
        self._init_connections()

    def _parse_physical_mapping(self):
        fabrics = []
        fabrics_config = cfg.CONF.DAEMON.fabrics
        for entry in fabrics_config:
            if ':' in entry:
                try:
                    fabric, pf = entry.split(':')
                    fabrics.append((fabric, pf))
                except ValueError:
                    LOG.error(_LE("Invalid fabric: "
                                "'%(entry)s' - "
                                "Service terminated!"),
                              locals())
                    raise
            else:
                LOG.error(_LE("Cannot parse Fabric Mappings"))
                raise Exception("Cannot parse Fabric Mappings")
        return fabrics

    def _init_connections(self):
        context = zmq.Context()
        self.socket_os = context.socket(zmq.REP)
        os_transport = constants.SOCKET_OS_TRANSPORT
        os_port = constants.SOCKET_OS_PORT
        os_addr = constants.SOCKET_OS_ADDR
        self.conn_os_url = set_conn_url(os_transport, os_addr, os_port)

        self.socket_os.bind(self.conn_os_url)
        self.poller = zmq.Poller()
        self.poller.register(self.socket_os, zmq.POLLIN)

    def _handle_msg(self):
        data = None

        msg = self.socket_os.recv()
        sender = self.socket_os
        if msg:
            data = jsonutils.loads(msg)

        msg = None
        if data:
            try:
                result = self.dispatcher.handle_msg(data)
                msg = jsonutils.dumps(result)
            except Exception as e:
                LOG.exception(_LE("Exception during message handling - %s"), e)
                msg = str(e)
            sender.send(msg)

    def daemon_loop(self):
        LOG.info(_LI("Daemon Started!"))
        polling_counter = 0
        while True:
            self._handle_msg()
            if polling_counter == self.max_polling_count:
                LOG.debug("Resync devices")
            # self.eswitch_handler.sync_devices()
                polling_counter = 0
            else:
                polling_counter += 1


def main():
    config.init(sys.argv[1:])
    config.setup_logging()
    try:
        daemon = MlxEswitchDaemon()
        daemon.start()
    except Exception as e:
        LOG.exception(_LE("Failed to start EswitchDaemon "
                          "- Daemon terminated! %s"), e)
        sys.exit(1)

    daemon.daemon_loop()


if __name__ == '__main__':
    main()
