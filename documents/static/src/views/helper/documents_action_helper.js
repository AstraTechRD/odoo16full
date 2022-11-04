/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart, onWillUpdateProps, useState } = owl;

export class DocumentsActionHelper extends Component {
    setup() {
        this.orm = useService("orm");
        this.hasShareReadAccessRights = undefined;
        this.state = useState({
            mailTo: undefined,
        });
        onWillStart(async () => {
            await this.updateShareInformation();
        });
        onWillUpdateProps(async () => {
            await this.updateShareInformation();
        });
    }

    async updateShareInformation() {
        this.state.mailTo = undefined;
        // Only load data if we are in a single folder.
        const domain = this.env.searchModel.domain.filter((leaf) => Array.isArray(leaf) && leaf.includes("folder_id"));
        if (domain.length !== 1) {
            return;
        }
        if (this.hasShareReadAccessRights === undefined) {
            this.hasShareReadAccessRights = await this.orm.call("documents.share", "check_access_rights", [], {
                operation: "read",
                raise_exception: false,
            });
        }
        if (!this.hasShareReadAccessRights) {
            return;
        }
        const shares = await this.orm.searchRead("documents.share", domain, ["id", "alias_id"], {
            limit: 1,
        });
        if (shares.length) {
            this.state.mailTo = shares[0].alias_id[1];
        }
    }
}
DocumentsActionHelper.template = "documents.DocumentsActionHelper";
