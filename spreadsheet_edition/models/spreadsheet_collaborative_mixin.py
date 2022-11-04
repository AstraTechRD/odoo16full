# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import base64
import psycopg2


from datetime import timedelta
from typing import Dict, Any, List

from odoo import fields, models
from odoo.exceptions import AccessError
from odoo.tools import mute_logger

_logger = logging.getLogger(__name__)

CollaborationMessage = Dict[str, Any]


class SpreadsheetCollaborativeMixin(models.AbstractModel):
    _name = "spreadsheet.collaborative.mixin"
    _description = "Collaboration on spreadsheets"

    raw = fields.Binary()
    spreadsheet_snapshot = fields.Binary()
    spreadsheet_revision_ids = fields.One2many(
        "spreadsheet.revision",
        "res_id",
        domain=lambda self: [('res_model', '=', self._name)],
        groups="base.group_system",
    )

    def join_spreadsheet_session(self):
        """Join a spreadsheet session.
        Returns the following data::
        - the last snapshot
        - pending revisions since the last snapshot
        - the spreadsheet name
        - whether the user favorited the spreadsheet or not
        - whether the user can edit the content of the spreadsheet or not
        """
        self.ensure_one()
        self._check_collaborative_spreadsheet_access("read")
        can_write = self._check_collaborative_spreadsheet_access(
            "write", raise_exception=False
        )
        return {
            "id": self.id,
            "name": self.display_name,
            "raw": self._get_spreadsheet_snapshot(),
            "revisions": self.sudo()._build_spreadsheet_messages(),
            "snapshot_requested": can_write and self._should_be_snapshotted(),
            "isReadonly": not can_write,
        }

    def dispatch_spreadsheet_message(self, message: CollaborationMessage):
        """This is the entry point of collaborative editing.
        Collaboration messages arrive here. For each received messages,
        the server decides if it's accepted or not. If the message is
        accepted, it's transmitted to all clients through the "bus.bus".
        Messages which do not update the spreadsheet state (a client moved
        joined or left) are always accepted. Messages updating the state
        require special care.

        Refused messages
        ----------------

        An important aspect of collaborative messages is their order. The server
        checks the order of received messages. If one is out of order, it is refused.
        How does it check the order?
        Each message has a `serverRevisionId` property which is the revision on which
        it should be applied. If it's not equal to the current known revision by the server,
        it is out of order and refused.

        Accepted messages
        -----------------

        If the message is found to be in order, it's accepted and the server registers it.
        The current server revision becomes the revision carried by the message, in the
        `nextRevisionId` property.
        With this strategy, we are guaranteed that all accepted message are ordered.
        See `_spreadsheet_revision_is_accepted`.

        :param message: collaborative message to process
        :return: if the message was accepted or not.
        :rtype: bool
        """
        self.ensure_one()

        if message["type"] in ["REMOTE_REVISION", "REVISION_UNDONE", "REVISION_REDONE"]:
            self._check_collaborative_spreadsheet_access("write")
            is_accepted = self._save_concurrent_revision(
                message["nextRevisionId"],
                message["serverRevisionId"],
                self._build_spreadsheet_revision_data(message),
            )
            if is_accepted:
                self._broadcast_spreadsheet_message(message)
            return is_accepted
        elif message["type"] == "SNAPSHOT":
            return self._snapshot_spreadsheet(
                message["serverRevisionId"], message["nextRevisionId"], message["data"]
            )
        elif message["type"] in ["CLIENT_JOINED", "CLIENT_LEFT", "CLIENT_MOVED"]:
            self._check_collaborative_spreadsheet_access("read")
            self._broadcast_spreadsheet_message(message)
            return True
        return False

    def _snapshot_spreadsheet(
        self, revision_id: str, snapshot_revision_id, spreadsheet_snapshot: dict
    ):
        """Save the spreadsheet snapshot along the revision id. Delete previous
        revisions which are no longer needed.
        If the `revision_id` is not the same as the server revision, the snapshot is
        not accepted and is ignored.

        :param revision_id: the revision on which the snapshot is based
        :param snapshot_revision_id: snapshot revision
        :param spreadsheet_snapshot: spreadsheet data
        :return: True if the snapshot was saved, False otherwise
        """
        is_accepted = self._save_concurrent_revision(
            snapshot_revision_id,
            revision_id,
            {"type": "SNAPSHOT_CREATED", "version": 1},
        )
        if is_accepted:
            self.spreadsheet_snapshot = base64.encodebytes(
                json.dumps(spreadsheet_snapshot).encode("utf-8")
            )
            self._delete_spreadsheet_revisions()
            self._broadcast_spreadsheet_message(
                {
                    "type": "SNAPSHOT_CREATED",
                    "serverRevisionId": revision_id,
                    "nextRevisionId": snapshot_revision_id,
                }
            )
        return is_accepted

    def _get_spreadsheet_snapshot(self):
        if not self.spreadsheet_snapshot:
            self.sudo().spreadsheet_snapshot = base64.encodebytes(self.raw)
        return base64.decodebytes(self.spreadsheet_snapshot)

    def _should_be_snapshotted(self):
        if not self.spreadsheet_revision_ids:
            return False
        last_activity = max(self.spreadsheet_revision_ids.mapped("create_date"))
        return last_activity < fields.Datetime.now() - timedelta(hours=12)

    def _save_concurrent_revision(self, next_revision_id, parent_revision_id, commands):
        """Save the given revision if no concurrency issue is found.
        i.e. if no other revision was saved based on the same `parent_revision_id`
        :param next_revision_id: the new revision id
        :param parent_revision_id: the revision on which the commands are based
        :param commands: revisions commands
        :return: True if the revision was saved, False otherwise
        """
        self.ensure_one()
        self._check_collaborative_spreadsheet_access("write")
        try:
            with mute_logger("odoo.sql_db"):
                self.env["spreadsheet.revision"].sudo().create(
                    {
                        "res_model": self._name,
                        "res_id": self.id,
                        "commands": json.dumps(commands),
                        "parent_revision_id": parent_revision_id,
                        "revision_id": next_revision_id,
                        "create_date": fields.Datetime.now(),
                    }
                )
            return True
        except psycopg2.IntegrityError:
            # If the creation failed with a unique violation error, it is because the parent_revision_id has already
            # been used. This means that at the same (relative) time, another user has made a modification to the
            # document while this user also modified the document, without knowing about each other modification.
            # We don't need to do anything: when the client that already did the modification will be done, the
            # situation will resolve itself when this client receives the other client's modification.
            _logger.info("Wrong base spreadsheet revision on %s", self)
            return False

    def _build_spreadsheet_revision_data(self, message: CollaborationMessage) -> dict:
        """Prepare revision data to save in the database from
        the collaboration message.
        """
        message = dict(message)
        message.pop("serverRevisionId", None)
        message.pop("nextRevisionId", None)
        message.pop("clientId", None)
        return message

    def _build_spreadsheet_messages(self) -> List[CollaborationMessage]:
        """Build spreadsheet collaboration messages from the saved
        revision data"""
        self.ensure_one()
        return [
            dict(
                json.loads(rev.commands),
                serverRevisionId=rev.parent_revision_id,
                nextRevisionId=rev.revision_id,
            )
            for rev in self.spreadsheet_revision_ids
        ]

    def _check_collaborative_spreadsheet_access(
        self, operation: str, *, raise_exception=True
    ):
        """Check that the user has the right to read/write on the document.
        It's used to ensure that a user can read/write the spreadsheet revisions
        of this document.
        """
        try:
            self.check_access_rights(operation)
            self.check_access_rule(operation)
        except AccessError as e:
            if raise_exception:
                raise e
            return False
        return True

    def _broadcast_spreadsheet_message(self, message: CollaborationMessage):
        """Send the message to the spreadsheet channel"""
        self.ensure_one()
        self.env["bus.bus"]._sendone(self, "spreadsheet", dict(message, id=self.id))

    def _delete_spreadsheet_revisions(self):
        """Delete spreadsheet revisions"""
        self.ensure_one()
        self._check_collaborative_spreadsheet_access("write")
        # For debug purposes, we archive revisions instead of unlinking them
        # self.spreadsheet_revision_ids.unlink()
        self.sudo().spreadsheet_revision_ids.active = False

    def unlink(self):
        """ Override unlink to delete spreadsheet revision. This cannot be
        cascaded, because link is done through (res_model, res_id). """
        if not self:
            return True
        self.sudo().spreadsheet_revision_ids.unlink()
        return super().unlink()
