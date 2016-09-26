# Copyright 2016 Mellanox Technologies, Ltd
#
#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from datetime import timedelta

from oslo_config import cfg
from oslo_log import log as logging

from networking_mlnx._i18n import _LI
from networking_mlnx.db import db
from networking_mlnx.plugins.ml2.drivers.sdn import config
from networking_mlnx.plugins.ml2.drivers.sdn import constants as sdn_const

LOG = logging.getLogger(__name__)
cfg.CONF.register_opts(config.sdn_opts, sdn_const.GROUP_OPT)


class JournalCleanup(object):
    """Journal maintenance operation for deleting completed rows."""
    def __init__(self):
        self._rows_retention = cfg.CONF.sdn.completed_rows_retention
        self._processing_timeout = cfg.CONF.sdn.processing_timeout

    def delete_completed_rows(self, session):
        if self._rows_retention is not -1:
            LOG.debug("Deleting completed rows")
            db.delete_rows_by_state_and_time(
                session, sdn_const.COMPLETED,
                timedelta(seconds=self._rows_retention))

    def cleanup_processing_rows(self, session):
        row_count = db.reset_processing_rows(session, self._processing_timeout)
        if row_count:
            LOG.info(_LI("Reset %(num)s orphaned rows back to pending"),
                     {"num": row_count})
