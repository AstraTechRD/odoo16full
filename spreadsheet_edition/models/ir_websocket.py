# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models

class IrWebsocket(models.AbstractModel):
    _inherit = 'ir.websocket'

    def _build_bus_channel_list(self, channels):
        if self.env.uid:
            channels = self._add_spreadsheet_collaborative_bus_channels(channels)
        return super()._build_bus_channel_list(channels)

    def _add_spreadsheet_collaborative_bus_channels(self, channels):
        """Add collaborative bus channels for active spreadsheets.

        Listening to channel "spreadsheet_collaborative_session:{res_model}:{res_id}"
        tells the server the spreadsheet is active. But only users with read access
        can actually read the associate bus messages.
        We manually add the channel if the user has read access.
        This channel is used to safely send messages to allowed users.

        :param channels: bus channels
        :return: channels
        """
        channels = list(channels)
        for channel in channels:
            if not isinstance(channel, str):
                continue
            match = re.match(r'spreadsheet_collaborative_session:(\w+(?:\.\w+)*):(\d+)', channel)
            if match:
                model_name = match[1]
                res_id = int(match[2])
                if model_name not in self.env:
                    continue
                # The following search ensures that the user has the correct access rights
                record = self.env[model_name].with_context(active_test=False).search([("id", "=", res_id)])
                channels.append(record)
        return channels
