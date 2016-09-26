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

"""sdn_journal change data to text

Revision ID: 5d5e04ea01d5
Create Date: 2016-08-16 06:01:54.795542

"""

from alembic import op
import sqlalchemy as sa

from networking_mlnx.plugins.ml2.drivers.sdn import constants as sdn_const


# revision identifiers, used by Alembic.
revision = '5d5e04ea01d5'
down_revision = 'd02c04effb34'


def upgrade():
    op.alter_column('sdn_journal', 'data',
                    existing_type=sa.PickleType(),
                    type_=sa.Text,
                    existing_nullable=True)
    op.alter_column('sdn_journal', 'state',
                    existing_type=sa.Enum(
                        sdn_const.PENDING, sdn_const.FAILED,
                        sdn_const.PROCESSING, sdn_const.COMPLETED,
                        name='state'),
                    type_=sa.Enum(
                        sdn_const.PENDING, sdn_const.FAILED,
                        sdn_const.PROCESSING, sdn_const.MONITORING,
                        sdn_const.COMPLETED,
                        name='state'),
                    existing_nullable=True)
