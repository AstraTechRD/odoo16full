/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { graphView } from "@web/views/graph/graph_view";
import { pivotView } from "@web/views/pivot/pivot_view";

const viewRegistry = registry.category("views");

const { useComponent } = owl;

function useOpenView() {
    const comp = useComponent();
    const { title } = comp.model.metaData;
    const actionService = useService("action");
    const orm = useService("orm");
    return async (domain, views, context) => {
        const res = await orm.call("hr.contract.employee.report", "search_read", [], {
            context: context,
            domain: domain,
            fields: ["id"], // id is equal to contract_id
        });
        const contractDomain = [["id", "in", res.map((r) => r.id)]];
        actionService.doAction({
            type: "ir.actions.act_window",
            name: title,
            res_model: "hr.contract",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
            context,
            domain: contractDomain,
        });
    };
}

export class HrContractEmployeeReportGraphController extends graphView.Controller {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.openView = useOpenView();
    }
}

viewRegistry.add("contract_employee_report_graph", {
    ...graphView,
    Controller: HrContractEmployeeReportGraphController,
});

export class HrContractEmployeeReportPivotController extends pivotView.Controller {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.openView = useOpenView();
    }
}

viewRegistry.add("contract_employee_report_pivot", {
    ...pivotView,
    Controller: HrContractEmployeeReportPivotController,
});
