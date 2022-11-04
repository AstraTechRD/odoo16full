/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { StudioApprovalInfos } from "@web_studio/approval/approval_infos";

const { useState, Component, onWillUnmount, useRef } = owl;

function useOpenExternal() {
    const closeFns = [];
    function open(_open) {
        const close = _open();
        closeFns.push(close);
        return close;
    }

    onWillUnmount(() => {
        closeFns.forEach((cb) => cb());
    });
    return open;
}

export class StudioApproval extends Component {
    setup() {
        this.dialog = useService("dialog");
        this.popover = useService("popover");
        this.rootRef = useRef("root");
        this.openExternal = useOpenExternal();

        const approval = this.props.approval;
        this.approval = approval;
        this.state = useState(approval.state);
    }

    toggleApprovalInfo() {
        if (this.isOpened) {
            this.closeInfos();
            this.closeInfos = null;
            return;
        }
        const onClose = () => {
            this.isOpened = false;
        };
        if (this.env.isSmall) {
            this.closeInfos = this.openExternal(() =>
                this.dialog.add(StudioApprovalInfos, { approval: this.approval }, { onClose })
            );
        } else {
            this.closeInfos = this.openExternal(() =>
                this.popover.add(
                    this.rootRef.el,
                    StudioApprovalInfos,
                    { approval: this.approval, isPopover: true },
                    { onClose }
                )
            );
        }
    }

    getEntry(ruleId) {
        return this.state.entries.find((e) => e.rule_id[0] === ruleId);
    }
}
StudioApproval.template = "StudioApproval";
