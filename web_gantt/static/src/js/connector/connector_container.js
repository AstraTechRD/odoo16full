/** @odoo-module **/

import Connector from "./connector";
import { deepMerge } from "./connector_utils";
import { LegacyComponent } from "@web/legacy/legacy_component";

const { onMounted, onWillUnmount, onWillUpdateProps } = owl;

class ConnectorContainer extends LegacyComponent {

    // -----------------------------------------------------------------------------
    // Life cycle hooks
    // -----------------------------------------------------------------------------

    /**
     * @override
     */
    setup() {
        this._createsParentListenerHandlers();
        /**
         * Keeps track of the mouse events related info.
         * @type {{ isParentDragging: boolean, hoveredConnector: HTMLElement }}
         */
        this.mouseEventsInfo = { };
        // Connector component used in order to manage connector creation.
        this.newConnector = {
            id: "newConnectorId",
            canBeRemoved: false,
        };
        // Apply default styling (if any) to newConnector.
        if ('defaultStyle' in this.props) {
            this.newConnector = deepMerge(this.newConnector, { style: this.props.defaultStyle });
        }
        if ('newConnectorStyle' in this.props) {
            this.newConnector = deepMerge(this.newConnector, { style: this.props.newConnectorStyle });
        }
        this._refreshPropertiesFromProps(this.props);

        onMounted(this.onMounted);
        onWillUnmount(this.onWillUnmount);
        onWillUpdateProps(this.onWillUpdateProps);
    }

    /**
     * @override
     */
    onMounted() {
        if (this.parentElement && this.parentElement !== this.el.parentElement) {
            this._removeParentListeners();
        }
        this.parentElement = this.el.parentElement;
        this._addParentListeners();
    }

    /**
     * @override
     */
    onWillUnmount() {
        this._removeParentListeners();
    }

    /**
     *
     * @override
     * @param nextProps
     * @returns {Promise<void>}
     */
    async onWillUpdateProps(nextProps) {
        this._refreshPropertiesFromProps(nextProps);
    }

    // -----------------------------------------------------------------------------
    // Private
    // -----------------------------------------------------------------------------

    /**
     * Adds the ConnectorContainer's parent required EventListeners.
     *
     * @private
     */
    _addParentListeners() {
        this.parentElement.addEventListener('mousedown', this._onParentMouseDownHandler);
        this.parentElement.addEventListener('mousemove', this._throttledOnParentMouseOverHandler);
        this.parentElement.addEventListener('mouseup', this._onParentMouseUpHandler);
        this.parentElement.addEventListener('mouseleave', this._onParentMouseUpHandler);
    }

    /**
     * Creates the handlers used in _addParentListeners and _removeParentListeners calls.
     *
     * @private
     */
    _createsParentListenerHandlers() {
        this._throttledOnParentMouseOverHandler = _.throttle((ev) => this._onParentMouseOver(ev), 50);
        this._onParentMouseDownHandler = (ev) => this._onParentMouseDown(ev);
        this._onParentMouseUpHandler = (ev) => this._onParentMouseUp(ev);
    }

    /**
     * Gets the element offset against the connectorContainer's parent.
     *
     * @param {HTMLElement} element the element the offset position has to be calculated for.
     */
    _getElementPosition(element) {
        // This will not work for css translated elements and this is acceptable at this time.
        // If needed in the future, consider using getBoundingClientRect() if getComputedStyle() returns a style
        // having a transform (and place this also in the for loop as we would need to do it if the element or any of
        // its parent is using css transform).
        let left = element.offsetLeft || 0;
        let top = element.offsetTop || 0;
        for (let el = element.offsetParent; el != null && el !== this.el.parentElement; el = el.offsetParent) {
            left += el.offsetLeft || 0;
            top += el.offsetTop || 0;
        }
        return {
            left: left,
            top: top,
        };
    }

    /**
     * Refreshes the connector properties from the props.
     *
     * @param {Object} props
     * @private
     */
    _refreshPropertiesFromProps(props) {
        this.connectors = deepMerge(props.connectors);
        if (this.props.defaultStyle) {
            Object.keys(this.connectors)
                  .forEach((key) => {
                      this.connectors[key].style = deepMerge(this.props.defaultStyle, this.connectors[key].style);
                      if (!('hoverEaseWidth' in this.connectors[key]) && 'hoverEaseWidth' in props) {
                          this.connectors[key].hoverEaseWidth = props.hoverEaseWidth;
                      }
                  });
        }
        const isHoveredConnectorSet = 'hoveredConnector' in this.mouseEventsInfo;
        const isHoveredConnectorPartOfProps = isHoveredConnectorSet && this.mouseEventsInfo.hoveredConnector.dataset.id in this.connectors;
        if (isHoveredConnectorSet && !isHoveredConnectorPartOfProps) {
            // Ensures to reset the mouseEventsInfo in case the hoveredConnector is set but is no more part
            // of the new props.
            delete this.mouseEventsInfo.hoveredConnector;
        }
    }

    /**
     * Removes the ConnectorContainer's parent required EventListeners.
     *
     */
    _removeParentListeners() {
        this.parentElement.removeEventListener('mousedown', this._onParentMouseDownHandler);
        this.parentElement.removeEventListener('mousemove', this._throttledOnParentMouseOverHandler);
        this.parentElement.removeEventListener('mouseup', this._onParentMouseUpHandler);
        this.parentElement.removeEventListener('mouseleave', this._onParentMouseUpHandler);
    }

    /**
     * Updates the hover state of the connector and render
     *
     * @param {string} id the id of the connector which hover state has to be updated.
     * @param {boolean} hovered the hover state to be set.
     * @private
     */
    _updateConnectorHoverState(id, hovered) {
        this.connectors[id].hovered = hovered && !(this.props.preventHoverEffect || this.mouseEventsInfo.isParentDragging);
        if (hovered) {
            // When a connector is hover we need to ensure it is rendered as last element as svg z-index works
            // that way and unfortunately no css can be used to modify it.
            const hoverConnector = this.connectors[id];
            delete this.connectors[id];
            this.connectors[id] = hoverConnector;
        }
        this.render();
    }

    // -----------------------------------------------------------------------------
    // Public
    // -----------------------------------------------------------------------------

    /**
     * Gets the top, right, bottom and left anchors positions for the provided element with respect to the
     * ConnectorContainer's parent.
     *
     * @param {HTMLElement} element the element the anchors positions have to be calculated for.
     * @param {HTMLElement} container the container the anchors positions will be calculated with respect to. In order
     *                                to have a valid result, the container should be an element with position attribute
     *                                set to relative.
     * @returns {{
     *              top: {top: number, left: number},
     *              left: {top: number, left: number},
     *              bottom: {top: number, left: number},
     *              right: {top: number, left: number}
     *          }}
     */
    getAnchorsPositions(element) {
        const elementPosition = this._getElementPosition(element);
        return {
            top: {
                top: elementPosition.top,
                left: elementPosition.left + element.offsetWidth / 2,
            },
            right: {
                top: elementPosition.top + element.offsetHeight / 2,
                left: elementPosition.left + element.offsetWidth,
            },
            bottom: {
                top: elementPosition.top + element.offsetHeight,
                left: elementPosition.left + element.offsetWidth / 2,
            },
            left: {
                top: elementPosition.top + element.offsetHeight / 2,
                left: elementPosition.left,
            },
        };
    }

    // -----------------------------------------------------------------------------
    // Handlers
    // -----------------------------------------------------------------------------

    /**
     * Handler for the ConnectorContainer's parent mousedown event. This handle is responsible of managing the start of a possible
     * connector creation (depending on whether the event target matches the sourceQuerySelector).
     *
     * @param {MouseEvent} ev
     * @private
     */
    _onParentMouseDown(ev) {
        const connector_source = ev.target.closest(this.props.sourceQuerySelector);
        if (connector_source) {
            ev.stopPropagation();
            ev.preventDefault();
            this.mouseEventsInfo.isParentDragging = true;
            const anchors = this.getAnchorsPositions(ev.target);
            this.newConnector = deepMerge(
                this.newConnector,
                {
                    data: {
                        sourceElement: connector_source,
                    },
                    inCreation: true,
                    source: {
                        top: anchors.right.top,
                        left: anchors.right.left,
                    },
                    target: {
                        top: anchors.right.top + ev.offsetY,
                        left: anchors.right.left + ev.offsetX,
                    },
                });
            this.props.onCreationStart(deepMerge({ }, this.newConnector));
            this.render();
        }
    }

    /**
     * Handler for the ConnectorContainer's parent mouseover event. This handle is responsible of the update of the newConnector
     * component props if a connector creation has started.
     *
     * @param {MouseEvent} ev
     * @private
     */
    _onParentMouseOver(ev) {
        if (this.mouseEventsInfo.isParentDragging === true) {
            ev.stopPropagation();
            ev.preventDefault();
            const position = this._getElementPosition(ev.target);
            this.newConnector = deepMerge(
                this.newConnector,
            {
                target: {
                    top: position.top + ev.offsetY,
                    left: position.left + ev.offsetX,
                },
            });
            this.render();
        }
    }

    /**
     * Handler for the ConnectorContainer's parent mouseup event. This handle is responsible of triggering either the
     * connector-creation-done or connector-creation-abort (depending on whether the event target matches the
     * targetQuerySelector) if a connector creation has started.
     *
     * @param {MouseEvent} ev
     * @private
     */
    _onParentMouseUp(ev) {
        if (this.mouseEventsInfo.isParentDragging === true) {
            ev.stopPropagation();
            ev.preventDefault();
            const connector_target = ev.target.closest(this.props.targetQuerySelector || this.props.sourceQuerySelector);
            if (connector_target) {
                this.newConnector = deepMerge(
                    this.newConnector,
                    {
                        data: {
                            targetElement: connector_target,
                        },
                    });
                this.props.onCreationDone(deepMerge({ }, this.newConnector));
            } else {
                this.props.onCreationAbort(deepMerge({ }, this.newConnector));
            }
            this.mouseEventsInfo.isParentDragging = false;
            delete this.newConnector.source;
            delete this.newConnector.target;
            this.render();
        }
    }

    /**
     * Handler for the connector_manager svg mouseout event. Its purpose is to handle the hover state of the connectors.
     * It has been implemented here in order to manage it globally instead of in each connector (and thus limiting
     * the number of listeners).
     *
     * @param {OwlEvent} ev
     * @private
     */
    _onMouseOut(ev) {
        ev.stopPropagation();
        if (!('hoveredConnector' in this.mouseEventsInfo)) {
            // If hoverConnector is not set this means were not in a connector. So ignore it.
            return;
        }
        let relatedTarget = ev.relatedTarget;
        while (relatedTarget) {
            // Go up the parent chain
            if (relatedTarget === this.mouseEventsInfo.hoveredConnector) {
                // Check that we are still inside hoveredConnector.
                // If so it means it is a transition between child elements so ignore it.
                return;
            }
            relatedTarget = relatedTarget.parentElement;
        }
        this._updateConnectorHoverState(this.mouseEventsInfo.hoveredConnector.dataset.id, false);
        this.props.onMouseOut(this.connectors[this.mouseEventsInfo.hoveredConnector.dataset.id]);
        delete this.mouseEventsInfo.hoveredConnector;
    }

    /**
     * Handler for the connector_manager svg mouseover event. Its purpose is to handle the hover state of the connectors.
     * It has been implemented here in order to manage it globally instead of in each connector (and thus limiting
     * the number of listeners).
     *
     * @param {OwlEvent} ev
     * @private
     */
    _onMouseOver(ev) {
        ev.stopPropagation();
        if ('hoveredConnector' in this.mouseEventsInfo) {
            // As mouseout is call prior to mouseover, if hoveredConnector is set this means
            // that we haven't left it. So it's a mouseover inside it.
            return;
        }
        let target = ev.target.closest('.o_connector');
        if (!target) {
            // We are not into a connector si ignore.
            return;
        }
        if (!(target.dataset.id in this.connectors) || Object.is(this.connectors[target.dataset.id], this.newConnector)) {
            // We ensure that the connector to hover is not this.newConnector
            return;
        }
        this.mouseEventsInfo.hoveredConnector = target;
        this._updateConnectorHoverState(target.dataset.id, true);
        this.props.onMouseOver(this.connectors[target.dataset.id]);
    }

}

Object.assign(ConnectorContainer, {
    components: { Connector },
    props: {
        connectors: { type: Object },
        defaultStyle: Connector.props.style,
        hoverEaseWidth: {
            optional: true,
            type: Number,
        },
        newConnectorStyle: Connector.props.style,
        preventHoverEffect: {
            optional: true,
            type: Boolean
        },
        sourceQuerySelector: { type: String },
        targetQuerySelector: {
            optional: true,
            type: String,
        },
        onRemoveButtonClick: { type: Function, optional: true },
        onRescheduleSoonerButtonClick: { type: Function, optional: true },
        onRescheduleLaterButtonClick: { type: Function, optional: true },
        onCreationAbort: { type: Function, optional: true },
        onCreationDone: { type: Function, optional: true },
        onCreationStart: { type: Function, optional: true },
        onMouseOut: { type: Function, optional: true },
        onMouseOver: { type: Function, optional: true },
    },
    defaultProps: {
        onRemoveButtonClick: () => {},
        onRescheduleSoonerButtonClick: () => {},
        onRescheduleLaterButtonClick: () => {},
        onCreationAbort: () => {},
        onCreationDone: () => {},
        onCreationStart: () => {},
        onMouseOut: () => {},
        onMouseOver: () => {},
    },
    template: 'connector_container',
});

export default ConnectorContainer;
