/** @odoo-module */

const { Component } = owl;

export class AbstractBehavior extends Component {
    setup() {
        super.setup();
        if (!this.props.readonly) {
            this.props.anchor.setAttribute('contenteditable', 'false');
        }
    }
}

AbstractBehavior.props = {
    readonly: { type: Boolean },
    anchor: { type: Element },
    wysiwyg: { type: Object, optional: true},
    record: { type: Object },
};
