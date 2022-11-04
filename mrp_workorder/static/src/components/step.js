/** @odoo-module **/

const { Component } = owl;

class StepComponent extends Component {
    get stepClass() {
        if (this.props.step.id === this.props.selectedStepId) {
            return "o_selected o_highlight";
        } else if (this.props.step.is_deleted) {
            return "o_deleted";
        } else {
            return "";
        }
    }

    selectStep() {
        this.props.onSelectStep(this.props.step.id);
    }

    get title() {
        return this.props.step.title || this.props.step.test_type;
    }

}

StepComponent.template = 'mrp_workorder.StepComponent';
StepComponent.props = ["step", "onSelectStep", "selectedStepId"];

export default StepComponent;
