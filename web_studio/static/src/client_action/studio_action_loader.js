/** @odoo-module **/

import { registry } from "@web/core/registry";
import { LazyComponent } from "@web/core/assets";
import { loadLegacyViews } from "@web/legacy/legacy_views";
import { loadWysiwyg } from "web_editor.loader";
import { useService } from "@web/core/utils/hooks";

const { Component, onWillStart, xml } = owl;

class StudioActionLoader extends Component {
    setup() {
        this.orm = useService("orm");
        onWillStart(loadWysiwyg);
        onWillStart(() => loadLegacyViews({ orm: this.orm }));
    }
}
StudioActionLoader.components = { LazyComponent };
StudioActionLoader.template = xml`
    <LazyComponent bundle="'web_studio.studio_assets'" Component="'StudioClientAction'" props="props"/>
`;
registry.category("actions").add("studio", StudioActionLoader);
