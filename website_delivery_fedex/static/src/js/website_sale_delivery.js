/** @odoo-module alias=website_delivery_fedex.checkout**/

import publicWidget from "web.public.widget";
import { qweb } from "web.core";
import "website_sale_delivery.checkout";

const WebsiteSaleDeliveryWidget = publicWidget.registry.websiteSaleDelivery;

WebsiteSaleDeliveryWidget.include({
    events: _.extend(
        {
            "click .o_fedex_address_select": "_onClickFedexLocation",
            "click .o_remove_fedex_order_location": "_onClickRemoveFedexLocation",
            "click .o_show_fedex_pickup_locations": "_onClickShowFedexLocations",
        },
        WebsiteSaleDeliveryWidget.prototype.events
    ),

    // @override
    start: function () {
        const self = this;
        return this._super(...arguments).then(function () {
            self._getCurrentLocation();
        });
    },

    // @override
    _handleCarrierUpdateResult: function (result) {
        const return_value = this._super(...arguments);
        const show_locations = document
            .getElementById("delivery_carrier")
            .getElementsByClassName("o_show_fedex_pickup_locations");
        for (const show_loc of show_locations) {
            while (show_loc.firstChild) {
                show_loc.lastChild.remove();
            }
            const span = document.createElement("em");
            const current_carrier_id = show_loc.closest("li").getElementsByTagName("input")[0].value;
            if (current_carrier_id == result.carrier_id) {
                const chevron_down = document.createElement("i");
                chevron_down.classList.add("fa", "fa-angle-down");
                span.textContent = "Pick-Up Locations ";
                span.classList.add("link-primary");
                span.appendChild(chevron_down);
            } else {
                span.textContent = "select to see available Pick-Up Locations";
                span.classList.add("text-muted");
            }
            show_loc.appendChild(span);
        }
        return return_value;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getCurrentLocation: function () {
        this._rpc({
            route: "/shop/fedex_access_point/get",
        }).then(function (data) {
            const order_locations = document.getElementsByClassName("o_fedex_order_location");
            for (const order_loc of order_locations) {
                const show_loc = order_loc.parentElement.nextElementSibling;
                if (!show_loc)
                    break ;
                while (order_loc.firstChild) {
                    order_loc.lastChild.remove();
                }
                if (data.fedex_access_point) {
                    order_loc.innerText = data.fedex_access_point;
                    order_loc.parentElement.classList.remove("d-none");
                    show_loc.classList.add("d-none");
                } else {
                    order_loc.parentElement.classList.add("d-none");
                    show_loc.classList.remove("d-none");
                }
            }
        });
    },

    _onClickRemoveFedexLocation: function (ev) {
        const self = this;
        this._rpc({
            route: "/shop/fedex_access_point/set",
            params: {
                access_point_encoded: null,
            },
        }).then(function () {
            self._getCurrentLocation();
        });
    },

    _onClickShowFedexLocations: function (ev) {
        const show_pickup_locations = ev.currentTarget;
        let modal = show_pickup_locations.nextElementSibling;
        if (show_pickup_locations.getElementsByClassName("link-primary").length) {
            const should_load_content = modal.firstChild ? false : true;
            while (modal.firstChild) {
                modal.lastChild.remove();
            }
            if (should_load_content) {
                $(qweb.render("fedex_pickup_location_loading")).appendTo($(modal));
                this._rpc({
                    route: "/shop/fedex_access_point/close_locations",
                }).then(function (data) {
                    modal.firstChild.remove();
                    if (data.close_locations) {
                        $(qweb.render("fedex_pickup_location_list", {
                            fedex_pickup_locations: data.close_locations,
                            partner_address: data.partner_address,
                        })).appendTo($(modal));
                    } else {
                        const error_message = document.createElement("em");
                        error_message.classList.add("text-error");
                        error_message.innerText = data.error ? data.error : "No available Pick-Up Locations";
                        modal.appendChild(error_message);
                    }
                });
            }
        }
    },

    _onClickFedexLocation: function (ev) {
        ev.preventDefault();
        const self = this;
        const modal = ev.currentTarget.closest(".o_list_fedex_pickup_locations");
        const encoded_location = ev.target.previousElementSibling.innerText;
        this._rpc({
            route: "/shop/fedex_access_point/set",
            params: {
                access_point_encoded: encoded_location,
            },
        }).then(function () {
            while (modal.firstChild) {
                modal.lastChild.remove();
            }
            self._getCurrentLocation();
        });
    },
});
