/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
const { onMounted, onWillStart, Component } = owl;

class SummaryStep extends Component {
    setup() {
        this.effect = useService('effect');
        this.orm = useService('orm');
        onMounted(() => this.makeRainbow());
        onWillStart(() => this.getData());
    }

    async getData() {
        this.data = await this.orm.call(
            'mrp.workorder',
            'get_summary_data',
            [this.props.workorder]
        );
    }

    makeRainbow() {
        if (this.data.show_rainbow) {
            this.effect.add({type: 'rainbow_man', fadeout: "fast"});
        }
    }
}

SummaryStep.template = 'mrp_workorder.SummaryStep';
SummaryStep.props = ["workorder"];

export default SummaryStep;
