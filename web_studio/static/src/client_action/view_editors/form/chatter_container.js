/** @odoo-module */

import { formView } from "@web/views/form/form_view";

const { Component } = owl;

const components = formView.Controller.components;

export class ChatterContainer extends components.ChatterContainer {
    _insertFromProps(props) {
        props = { ...props };
        delete props.studioXpath;
        return super._insertFromProps(props);
    }
    onClick(ev) {
        this.env.config.onNodeClicked({
            xpath: this.props.studioXpath,
            target: ev.target,
        });
    }
}
ChatterContainer.template = "web_studio.ChatterContainer";
ChatterContainer.props = {
    ...ChatterContainer.props,
    studioXpath: String,
};

export class ChatterContainerHook extends Component {
    onClick() {
        this.env.config.onViewChange({
            structure: "chatter",
            ...this.props.chatterData,
        });
    }
}
ChatterContainerHook.template = "web_studio.ChatterContainerHook";
ChatterContainerHook.components = { ChatterContainer: components.ChatterContainer };
ChatterContainerHook.props = {
    chatterData: Object,
    threadModel: String,
};
