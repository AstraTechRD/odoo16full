/** @odoo-module */

import { WithSearch } from "@web/search/with_search/with_search";

const { Component, xml, useSubEnv } = owl;

const HEIGHT = "height: 100%;";

export class StudioView extends Component {
    setup() {
        this.style = this.props.setOverlay ? `pointer-events: none; ${HEIGHT}` : HEIGHT;
        this.withSearchProps = {
            resModel: this.props.controllerProps.resModel,
            SearchModel: this.props.SearchModel,
            context: this.props.context,
            domain: this.props.domain,
        };

        useSubEnv({
            config: { ...this.env.config },
            __beforeLeave__: null,
        });
    }
}
StudioView.components = { WithSearch };
StudioView.template = xml`
    <div t-att-style="style">
        <WithSearch t-props="withSearchProps" t-slot-scope="search">
            <t t-component="props.Controller"
                t-props="props.controllerProps"
                context="search.context"
                domain="search.domain"
                groupBy="search.groupBy"
                orderBy="search.orderBy"
                comparison="search.comparison"
            />
        </WithSearch>
    </div>
`;
