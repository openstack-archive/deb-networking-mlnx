# Copyright 2016 Mellanox Technologies, Ltd
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

"""start networking-mlnx contract branch

Revision ID: dfd1a1f22c4180
Create Date: 2016-07-24 12:34:56.789098

"""

from neutron.db.migration import cli


# revision identifiers, used by Alembic.
revision = 'dfd1a1f22c4180'
down_revision = 'start_networking_mlnx'
branch_labels = (cli.CONTRACT_BRANCH,)


def upgrade():
    pass
