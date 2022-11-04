/** @odoo-module **/
import { ComponentAdapter } from "web.OwlCompatibility";
import ReportEditorManager from "web_studio.ReportEditorManager";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

const { Component, xml } = owl;

class ReportEditorAdapter extends ComponentAdapter {
    constructor(props) {
        props.Component = ReportEditorManager;
        super(...arguments);
    }

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.user = useService("user");
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.studio = useService("studio");
        this.reportEnv = {};
        this.env = Component.env;
    }

    get handle() {
        return this.studio.editedReport;
    }

    async onWillStart() {
        const proms = [];
        await this._readReport();
        await this._loadEnvironment();
        proms.push(this._readModels());
        proms.push(this._readWidgetsOptions());
        proms.push(this._getReportViews());
        proms.push(this._readPaperFormat());
        await Promise.all(proms);
        return super.onWillStart();
    }

    get widgetArgs() {
        return [
            {
                env: this.reportEnv,
                //initialState: state,
                models: this.models,
                paperFormat: this.paperFormat,
                report: this.report,
                reportHTML: this.reportViews.report_html,
                reportMainViewID: this.reportViews.main_view_id,
                reportViews: this.reportViews.views,
                widgetsOptions: this.widgetsOptions,
            },
        ];
    }

    /**
     * Load and set the report environment.
     *
     * If the report is associated to the same model as the Studio action, the
     * action ids will be used ; otherwise a search on the report model will be
     * performed.
     *
     * @private
     * @returns {Promise}
     */
    async _loadEnvironment() {
        this.reportEnv.modelName = this.report.model;

        // TODO: Since 13.0, journal entries are also considered as 'account.move',
        // therefore must filter result to remove them; otherwise not possible
        // to print invoices and hard to lookup for them if lot of journal entries.
        let domain = [];
        if (this.report.model === "account.move") {
            domain = [["move_type", "!=", "entry"]];
        }

        const result = await this.orm.search(this.report.model, domain, {
            context: this.user.context,
        });
        this.reportEnv.ids = result;
        this.reportEnv.currentId = this.reportEnv.ids && this.reportEnv.ids[0];
    }
    /**
     * Read the models (ir.model) name and model to display them in a
     * user-friendly way in the sidebar (see AbstractReportComponent).
     *
     * @private
     * @returns {Promise}
     */
    async _readModels() {
        const models = await this.orm.searchRead(
            "ir.model",
            [
                ["transient", "=", false],
                ["abstract", "=", false],
            ],
            ["name", "model"],
            { context: this.user.context }
        );
        this.models = {};
        models.forEach((model) => {
            this.models[model.model] = model.name;
        });
    }
    /**
     * @private
     * @returns {Promise}
     */
    async _readReport() {
        const result = await this.orm.read("ir.actions.report", [this.handle.res_id], undefined, {
            context: this.user.context,
        });
        this.report = result[0];
    }
    /**
     * @private
     * @returns {Promise}
     */
    async _readPaperFormat() {
        this.paperFormat = "A4";
        const result = await this.rpc("/web_studio/read_paperformat", {
            report_id: this.handle.res_id,
            context: this.user.context,
        });
        this.paperFormat = result[0];
    }
    /**
     * Load the widgets options for t-options directive in sidebar.
     *
     * @private
     * @returns {Promise}
     */
    async _readWidgetsOptions() {
        this.widgetsOptions = await this.rpc("/web_studio/get_widgets_available_options", {
            context: this.user.context,
        });
    }
    /**
     * @private
     * @returns {Promise<Object>}
     */
    async _getReportViews() {
        // SAD: FIXME calling this when there are no record for the model crashes (no currentId)
        // used to show a danger notification
        this.reportViews = await this.rpc("/web_studio/get_report_views", {
            record_id: this.reportEnv.currentId,
            report_name: this.report.report_name,
        });
    }

    _trigger_up(ev) {
        switch (ev.name) {
            case "studio_edit_report":
                this._editReport(ev.data);
                break;
            case "open_record_form_view":
                this.actionService.doAction(
                    {
                        type: "ir.actions.act_window",
                        res_model: "ir.actions.report",
                        res_id: this.handle.res_id,
                        views: [[false, "form"]],
                        target: "current",
                    },
                    { clearBreadcrumbs: true }
                );
                break;
        }
        super._trigger_up(...arguments);
    }

    /**
     * @private
     * @param {Object} values
     * @returns {Promise}
     */
    async _editReport(values) {
        const result = await this.rpc("/web_studio/edit_report", {
            report_id: this.report.id,
            values: values,
            context: this.user.context,
        });
        this.report = result[0];
        this.render(true);
    }
}

// We need this to wrap in a div
// ViewEditor doesn't need this because it extends AbstractEditor, and defines a template
export class ReportEditor extends Component {}
ReportEditor.template = xml`<div class="o_web_studio_client_action"><ReportEditorAdapter /></div>`;
ReportEditor.components = { ReportEditorAdapter };
registry.category("actions").add("web_studio.report_editor", ReportEditor);
