/** @odoo-module **/

const { Component, useRef, useState } = owl;

export class PdfGroupName extends Component {

    /**
     * @override
     */
    setup() {
        this.state = useState({
            edit: false,
        });
        // used to get the value of the input when renaming.
        this.nameInputRef = useRef('nameInput');
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onBlur() {
        this.props.onEditName(
            this.props.groupId,
            this.nameInputRef.el.value,
        );
        this.state.edit = false;
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickGroupName(ev) {
        ev.stopPropagation();
        this.state.edit = true;
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onKeyDown(ev) {
        if (ev.code !== "Enter") {
            return;
        }
        ev.stopPropagation();
        this.props.onEditName(
            this.props.groupId,
            this.nameInputRef.el.value,
        );
        this.state.edit = false;
    }
}

PdfGroupName.props = {
    groupId: String,
    name: String,
    onEditName: {
        type: Function,
        optional: true,
    }
};

PdfGroupName.template = 'documents.component.PdfGroupName';
