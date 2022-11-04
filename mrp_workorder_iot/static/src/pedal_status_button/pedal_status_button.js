/** @odoo-module **/

const { Component } = owl;

export class PedalStatusButton extends Component {}
PedalStatusButton.props = {
    pedalConnected: { type: Boolean },
    takeOwnership: { type: Function},
}
PedalStatusButton.template = 'mrp_workorder_iot.PedalStatusButton';
