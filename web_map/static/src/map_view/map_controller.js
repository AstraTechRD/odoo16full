/** @odoo-module **/

import { loadJS, loadCSS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { useModel } from "@web/views/model";
import { standardViewProps } from "@web/views/standard_view_props";
import { useSetupView } from "@web/views/view_hook";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";

const { Component, onWillUnmount, onWillStart } = owl;

export class MapController extends Component {
    setup() {
        this.action = useService("action");

        /** @type {typeof MapModel} */
        const Model = this.props.Model;
        const model = useModel(Model, this.props.modelParams);
        this.model = model;

        onWillUnmount(() => {
            this.model.stopFetchingCoordinates();
        });

        useSetupView({
            getLocalState: () => {
                return this.model.metaData;
            },
        });

        onWillStart(() =>
            Promise.all([
                loadJS("/web_map/static/lib/leaflet/leaflet.js"),
                loadCSS("/web_map/static/lib/leaflet/leaflet.css"),
            ])
        );

        usePager(() => {
            return {
                offset: this.model.metaData.offset,
                limit: this.model.metaData.limit,
                total: this.model.data.count,
                onUpdate: ({ offset, limit }) => this.model.load({ offset, limit }),
            };
        });
    }

    /**
     * @returns {any}
     */
    get rendererProps() {
        return {
            model: this.model,
            onMarkerClick: this.openRecords.bind(this),
        };
    }
    /**
     * @returns {string}
     */
    get googleMapUrl() {
        let url = "https://www.google.com/maps/dir/?api=1";
        if (this.model.data.records.length) {
            const allCoordinates = this.model.data.records.filter(
                ({ partner }) => partner && partner.partner_latitude && partner.partner_longitude
            );
            const uniqueCoordinates = allCoordinates.reduce((coords, { partner }) => {
                const coord = partner.partner_latitude + "," + partner.partner_longitude;
                if (!coords.includes(coord)) {
                    coords.push(coord);
                }
                return coords;
            }, []);
            if (uniqueCoordinates.length && this.model.metaData.routing) {
                // When routing is enabled, make last record the destination
                url += `&destination=${uniqueCoordinates.pop()}`;
            }
            if (uniqueCoordinates.length) {
                url += `&waypoints=${uniqueCoordinates.join("|")}`;
            }
        }
        return url;
    }

    /**
     * Redirects to views when clicked on open button in marker popup.
     *
     * @param {number[]} ids
     */
    openRecords(ids) {
        if (ids.length > 1) {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: this.env.config.getDisplayName() || this.env._t("Untitled"),
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                res_model: this.props.resModel,
                domain: [["id", "in", ids]],
            });
        } else {
            this.action.switchView("form", {
                resId: ids[0],
                mode: "readonly",
                model: this.props.resModel,
            });
        }
    }
}

MapController.template = "web_map.MapView";

MapController.components = {
    Layout,
};

MapController.props = {
    ...standardViewProps,
    Model: Function,
    modelParams: Object,
    Renderer: Function,
    buttonTemplate: String,
};
