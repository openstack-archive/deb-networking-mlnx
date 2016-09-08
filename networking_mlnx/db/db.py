# Copyright 2016 Mellanox Technologies, Ltd
# All Rights Reserved.
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
import datetime

from neutron.db import api as db_api
from oslo_db import api as oslo_db_api
from oslo_serialization import jsonutils
from sqlalchemy import asc
from sqlalchemy import func
from sqlalchemy import or_

from networking_mlnx.db.models import sdn_journal_db
from networking_mlnx.db.models import sdn_maintenance_db
from networking_mlnx.plugins.ml2.drivers.sdn import constants as sdn_const


def check_for_pending_or_processing_ops(session, object_uuid, operation=None):
    q = session.query(sdn_journal_db.SdnJournal).filter(
        or_(sdn_journal_db.SdnJournal.state == sdn_const.PENDING,
            sdn_journal_db.SdnJournal.state == sdn_const.PROCESSING),
        sdn_journal_db.SdnJournal.object_uuid == object_uuid)
    if operation:
        if isinstance(operation, (list, tuple)):
            q = q.filter(sdn_journal_db.SdnJournal.operation.in_(operation))
        else:
            q = q.filter(sdn_journal_db.SdnJournal.operation == operation)
    return session.query(q.exists()).scalar()


def check_for_pending_delete_ops_with_parent(session, object_type, parent_id):
    rows = session.query(sdn_journal_db.SdnJournal).filter(
        or_(sdn_journal_db.SdnJournal.state == sdn_const.PENDING,
            sdn_journal_db.SdnJournal.state == sdn_const.PROCESSING),
        sdn_journal_db.SdnJournal.object_type == object_type,
        sdn_journal_db.SdnJournal.operation == sdn_const.DELETE
    ).all()

    for row in rows:
        if parent_id in row.data:
            return True

    return False


def check_for_older_ops(session, row):
    q = session.query(sdn_journal_db.SdnJournal).filter(
        or_(sdn_journal_db.SdnJournal.state == sdn_const.PENDING,
            sdn_journal_db.SdnJournal.state == sdn_const.PROCESSING),
        sdn_journal_db.SdnJournal.operation == row.operation,
        sdn_journal_db.SdnJournal.object_uuid == row.object_uuid,
        sdn_journal_db.SdnJournal.created_at < row.created_at,
        sdn_journal_db.SdnJournal.id != row.id)
    return session.query(q.exists()).scalar()


def get_all_db_rows(session):
    return session.query(sdn_journal_db.SdnJournal).all()


def get_all_db_rows_by_state(session, state):
    return session.query(sdn_journal_db.SdnJournal).filter_by(
        state=state).all()


# Retry deadlock exception for Galera DB.
# If two (or more) different threads call this method at the same time, they
# might both succeed in changing the same row to pending, but at least one
# of them will get a deadlock from Galera and will have to retry the operation.
@db_api.retry_db_errors
def get_oldest_pending_db_row_with_lock(session):
    with session.begin():
        row = session.query(sdn_journal_db.SdnJournal).filter_by(
            state=sdn_const.PENDING).order_by(
            asc(sdn_journal_db.SdnJournal.last_retried)).with_for_update(
        ).first()
        if row:
            update_db_row_state(session, row, sdn_const.PROCESSING)

    return row


@db_api.retry_db_errors
def get_all_monitoring_db_row_by_oldest(session):
    with session.begin():
        rows = session.query(sdn_journal_db.SdnJournal).filter_by(
            state=sdn_const.MONITORING).order_by(
            asc(sdn_journal_db.SdnJournal.last_retried)).all()
    return rows


@oslo_db_api.wrap_db_retry(max_retries=db_api.MAX_RETRIES)
def update_db_row_state(session, row, state):
    row.state = state
    session.merge(row)
    session.flush()


@oslo_db_api.wrap_db_retry(max_retries=db_api.MAX_RETRIES)
def update_db_row_job_id(session, row, job_id):
    row.job_id = job_id
    session.merge(row)
    session.flush()


def update_pending_db_row_retry(session, row, retry_count):
    if row.retry_count >= retry_count and row.retry_count != -1:
        update_db_row_state(session, row, sdn_const.FAILED)
    else:
        row.retry_count += 1
        update_db_row_state(session, row, sdn_const.PENDING)


# This function is currently not used.
# Deleted resources are marked as 'deleted' in the database.
@oslo_db_api.wrap_db_retry(max_retries=db_api.MAX_RETRIES)
def delete_row(session, row=None, row_id=None):
    if row_id:
        row = session.query(sdn_journal_db.SdnJournal).filter_by(
            id=row_id).one()
    if row:
        session.delete(row)
        session.flush()


@oslo_db_api.wrap_db_retry(max_retries=db_api.MAX_RETRIES)
def create_pending_row(session, object_type, object_uuid,
                       operation, data):
    data = jsonutils.dumps(data)
    row = sdn_journal_db.SdnJournal(object_type=object_type,
                                    object_uuid=object_uuid,
                                    operation=operation, data=data,
                                    created_at=func.now(),
                                    state=sdn_const.PENDING)
    session.add(row)
    # Keep session flush for unit tests. NOOP for L2/L3 events since calls are
    # made inside database session transaction with subtransactions=True.
    session.flush()


@db_api.retry_db_errors
def _update_maintenance_state(session, expected_state, state):
    with session.begin():
        row = session.query(sdn_maintenance_db.SdnMaintenance).filter_by(
            state=expected_state).with_for_update().one_or_none()
        if row is None:
            return False

        row.state = state
        return True


def lock_maintenance(session):
    return _update_maintenance_state(session, sdn_const.PENDING,
                                     sdn_const.PROCESSING)


def unlock_maintenance(session):
    return _update_maintenance_state(session, sdn_const.PROCESSING,
                                     sdn_const.PENDING)


def update_maintenance_operation(session, operation=None):
    """Update the current maintenance operation details.

    The function assumes the lock is held, so it mustn't be run outside of a
    locked context.
    """
    op_text = None
    if operation:
        op_text = operation.__name__

    with session.begin():
        row = session.query(sdn_maintenance_db.SdnMaintenance).one_or_none()
        row.processing_operation = op_text


def delete_rows_by_state_and_time(session, state, time_delta):
    with session.begin():
        now = session.execute(func.now()).scalar()
        session.query(sdn_journal_db.SdnJournal).filter(
            sdn_journal_db.SdnJournal.state == state,
            sdn_journal_db.SdnJournal.last_retried < now - time_delta).delete(
            synchronize_session=False)
        session.expire_all()


def reset_processing_rows(session, max_timedelta):
    with session.begin():
        now = session.execute(func.now()).scalar()
        max_timedelta = datetime.timedelta(seconds=max_timedelta)
        rows = session.query(sdn_journal_db.SdnJournal).filter(
            sdn_journal_db.SdnJournal.last_retried < now - max_timedelta,
            sdn_journal_db.SdnJournal.state == sdn_const.PROCESSING,
        ).update({'state': sdn_const.PENDING})

    return rows
