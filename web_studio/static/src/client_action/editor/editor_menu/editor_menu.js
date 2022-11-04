/** @odoo-module */

import { useBus, useService } from "@web/core/utils/hooks";
import { _lt } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";

const { Component, useState } = owl;
const editorTabRegistry = registry.category("web_studio.editor_tabs");

export class EditorMenu extends Component {
    setup() {
        this.l10n = localization;
        this.studio = useService("studio");
        this.rpc = useService("rpc");
        this.state = useState({
            redo_available: false,
            undo_available: false,
            snackbar: undefined,
        });

        this.nextCrumbId = 1;

        useBus(this.studio.bus, "UPDATE", async () => {
            await this.render(true);
            this.state.snackbar = "off";
        });

        useBus(this.studio.bus, "undo_available", () => {
            this.state.undo_available = true;
        });
        useBus(this.studio.bus, "undo_not_available", () => {
            this.state.undo_available = false;
        });
        useBus(this.studio.bus, "redo_available", () => {
            this.state.redo_available = true;
        });
        useBus(this.studio.bus, "redo_not_available", () => {
            this.state.redo_available = false;
        });

        useBus(this.studio.bus, "toggle_snack_bar", (e) => {
            this.state.snackbar = e.detail;
        });
    }

    get breadcrumbs() {
        const { editorTab } = this.studio;
        const currentTab = this.editorTabs.find((tab) => tab.id === editorTab);
        const crumbs = [
            {
                name: currentTab.name,
                handler: () => this.openTab(currentTab.id),
            },
        ];
        if (currentTab.id === "views") {
            const { editedViewType, x2mEditorPath } = this.studio;
            if (editedViewType) {
                const currentViewType = this.constructor.viewTypes.find(
                    (vt) => vt.type === editedViewType
                );
                crumbs.push({
                    name: currentViewType.title,
                    handler: () =>
                        this.studio.setParams({
                            x2mEditorPath: [],
                        }),
                });
            }
            x2mEditorPath.forEach(({ x2mViewType }, index) => {
                const viewType = this.constructor.viewTypes.find((vt) => vt.type === x2mViewType);
                crumbs.push({
                    name: sprintf(
                        this.env._t("Subview %s"),
                        (viewType && viewType.title) || this.env._t("Other")
                    ),
                    handler: () =>
                        this.studio.setParams({
                            x2mEditorPath: x2mEditorPath.slice(0, index + 1),
                        }),
                });
            });
        } else if (currentTab.id === "reports" && this.studio.editedReport) {
            crumbs.push({
                name: this.studio.editedReport.data.name,
                handler: () => this.studio.setParams({}),
            });
        }
        for (const crumb of crumbs) {
            crumb.id = this.nextCrumbId++;
        }
        return crumbs;
    }

    get activeViews() {
        const action = this.studio.editedAction;
        const viewTypes = (action._views || action.views).map(([, type]) => type);
        return this.constructor.viewTypes.filter((vt) => viewTypes.includes(vt.type));
    }

    get editorTabs() {
        const entries = editorTabRegistry.getEntries();
        return entries.map((entry) => Object.assign({}, entry[1], { id: entry[0] }));
    }

    openTab(tab) {
        this.props.switchTab({ tab });
    }
}
EditorMenu.template = "web_studio.EditorMenu";
EditorMenu.viewTypes = [
    {
        title: _lt("Form"),
        type: "form",
        iconClasses: "fa fa-address-card",
    },
    {
        title: _lt("List"),
        type: "list",
        iconClasses: "oi oi-view-list",
    },
    {
        title: _lt("Kanban"),
        type: "kanban",
        iconClasses: "oi oi-view-kanban",
    },
    {
        title: _lt("Map"),
        type: "map",
        iconClasses: "fa fa-map-marker",
    },
    {
        title: _lt("Calendar"),
        type: "calendar",
        iconClasses: "fa fa-calendar",
    },
    {
        title: _lt("Graph"),
        type: "graph",
        iconClasses: "fa fa-area-chart",
    },
    {
        title: _lt("Pivot"),
        type: "pivot",
        iconClasses: "oi oi-view-pivot",
    },
    {
        title: _lt("Gantt"),
        type: "gantt",
        iconClasses: "fa fa-tasks",
    },
    {
        title: _lt("Dashboard"),
        type: "dashboard",
        iconClasses: "fa fa-tachometer",
    },
    {
        title: _lt("Cohort"),
        type: "cohort",
        iconClasses: "oi oi-view-cohort",
    },
    {
        title: _lt("Activity"),
        type: "activity",
        iconClasses: "fa fa-clock-o",
    },
    {
        title: _lt("Search"),
        type: "search",
        iconClasses: "oi oi-search",
    },
];

editorTabRegistry
    .add("views", { name: _lt("Views"), action: "web_studio.action_editor" })
    .add("reports", { name: _lt("Reports") })
    .add("automations", { name: _lt("Automations") })
    .add("acl", { name: _lt("Access Control") })
    .add("filters", { name: _lt("Filter Rules") });
