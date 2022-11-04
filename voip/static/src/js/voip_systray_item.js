/** @odoo-module **/

const { Component } = owl;


/**
 * Systray item allowing to toggle the voip DialingPanel.
 */
export class VoipSystrayItem extends Component {
    /**
     * Toggle the dialing panel.
     */
    onClick() {
        this.props.bus.trigger('TOGGLE_DIALING_PANEL');
    }
}
VoipSystrayItem.template = "voip.SystrayItem";
