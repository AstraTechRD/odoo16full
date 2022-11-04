/** @odoo-module **/

import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { localization } from "@web/core/l10n/localization";

const { Component } = owl;

class FollowupTrustPopOver extends Component {}
FollowupTrustPopOver.template = "account_followup.FollowupTrustPopOver";

class FollowupTrustWidget extends Component {
    setup() {
        super.setup();
        this.popover = usePopover();
    }

    displayTrust() {
        var selections = this.props.record.fields.trust.selection;
        var trust = this.props.value;
        for (var i=0; i < selections.length; i++) {
            if (selections[i][0] == trust) {
                return selections[i][1];
            }
        }
    }

    onTrustClick(ev) {
        if (this.popoverCloseFn) {
            this.closePopover();
        }
        this.popoverCloseFn = this.popover.add(
            ev.currentTarget,
            FollowupTrustPopOver,
            {
                record: this.props.record,
                widget: this,
                onClose: this.closePopover,
            },
            {
                position: localization.direction === "rtl" ? "bottom" : "right",
            },
        );
    }

    async setTrust(trust) {
        this.props.update(trust);
        this.closePopover();
    }

    closePopover() {
        this.popoverCloseFn();
        this.popoverCloseFn = null;
    }
}

FollowupTrustWidget.template = "account_followup.FollowupTrustWidget";
registry.category("fields").add("followup_trust_widget", FollowupTrustWidget);
