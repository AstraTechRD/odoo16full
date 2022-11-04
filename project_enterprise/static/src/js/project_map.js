/** @odoo-module **/

import { mapView } from "@web_map/map_view/map_view";
import { ProjectControlPanel } from "@project/components/project_control_panel/project_control_panel";
import { registry } from "@web/core/registry";

export const projectMapView = {...mapView, ControlPanel: ProjectControlPanel };

registry.category("views").add("project_map", projectMapView);
