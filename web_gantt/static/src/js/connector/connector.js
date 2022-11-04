/** @odoo-module **/

import { deepMerge } from "./connector_utils";

const { Component, onWillUpdateProps } = owl;

class Connector extends Component {

    // -----------------------------------------------------------------------------
    // Life cycle hooks
    // -----------------------------------------------------------------------------

    /**
     * @override
     */
    setup() {
        this._refreshPropertiesFromProps(this.props);

        onWillUpdateProps(this.onWillUpdateProps);
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
     * Refreshes the connector properties from the props.
     *
     * @param {Object} props
     * @private
     */
    _refreshPropertiesFromProps(props) {
        const defaultStyleProps = {
            drawHead: true,
            outlineStroke: {
                color: 'rgba(255,255,255,0.5)',
                hoveredColor: 'rgba(255,255,255,0.9)',
                width: 2,
            },
            slackness: 0.5,
            stroke: {
                color: 'rgba(0,0,0,0.5)',
                hoveredColor: 'rgba(0,0,0,0.9)',
                width: 2,
            },
        };
        this.hoverEaseWidth = props.hoverEaseWidth ? props.hoverEaseWidth : 1;
        this.style = deepMerge(defaultStyleProps, props.style);
        const pathInfo = this._getPathInfo(props.source, props.target,  this.style.slackness);
        this.path = `M ${pathInfo.singlePath.source.left} ${pathInfo.singlePath.source.top} \
                     C ${pathInfo.singlePath.sourceControlPoint.left} ${pathInfo.singlePath.sourceControlPoint.top} \
                       ${pathInfo.singlePath.targetControlPoint.left} ${pathInfo.singlePath.targetControlPoint.top} \
                       ${pathInfo.singlePath.target.left} ${pathInfo.singlePath.target.top}`;
        this.removeButtonPosition = pathInfo.doublePath.startingPath.target;
    }

    /**
     * Returns the parameters of both the single Bezier curve as well as is decomposition into two beziers curves
     * (which allows to get the middle position of the single Bezier curve) for the provided source, target and
     * slackness (0 being a straight line).
     *
     * @param {{ left: number, top: number }} source
     * @param {{ left: number, top: number }} target
     * @param {number} slackness [0, 1]
     * @returns {{
     *              singlePath: {
     *                      source: {
     *                          top: number,
     *                          left: number
     *                      },
     *                      sourceControlPoint: {
     *                          top: number,
     *                          left: number
     *                      },
     *                      target: {
     *                          top: number,
     *                          left: number
     *                      },
     *                      targetControlPoint: {
     *                          top: number,
     *                          left: number
     *                      }
     *              },
     *              doublePath: {
     *                  endingPath: {
     *                      source: {
     *                          top: number,
     *                          left: number
     *                      },
     *                      sourceControlPoint: {
     *                          top: number,
     *                          left: number
     *                      },
     *                      target: {
     *                          top: number,
     *                          left: number
     *                      },
     *                      targetControlPoint: {
     *                          top: number,
     *                          left: number
     *                      }
     *                  },
     *                  startingPath: {
     *                      source: {
     *                          top: number,
     *                          left: number
     *                      },
     *                      sourceControlPoint: {
     *                          top: number,
     *                          left: number
     *                      },
     *                      target: {
     *                          top: number,
     *                          left: number
     *                      },
     *                      targetControlPoint: {
     *                          top: number,
     *                          left: number
     *                      }
     *                  }
     *              }
     *          }}
     * @private
     */
    _getPathInfo(source, target, slackness) {
        const b = { left: 0, top: 0 };
        const c = { left: 0, top: 0 };
        // If the source is on the left of the target, we need to invert the control points.
        const directionFactor = source.left < target.left ? 1 : -1;
        // What follows can be seen as magic numbers. And those are indeed such numbers as they have been determined
        // by observing their shape while creating short and long connectors. These seems to allow keeping the same
        // kind of shape amongst short and long connectors.
        const xDelta = 100 + directionFactor * (target.left - source.left) * slackness / 10;
        const yDelta = Math.abs(source.top - target.top) < 16 && source.left > target.left ? 15 + 0.001 * (source.left - target.left) * slackness : 0;
        b.left = source.left + xDelta;
        b.top = source.top + yDelta;
        // Prevent having the air pin effect when in creation and having target on the left of the source
        if (!this.props.inCreation || directionFactor > 0) {
            c.left = target.left - xDelta;
        } else {
            c.left = target.left + xDelta;
        }
        c.top = target.top + yDelta;

        const cuttingDistance = 0.5;
        const e = Connector._getLinearInterpolation(source, b, cuttingDistance);
        const f = Connector._getLinearInterpolation(b, c, cuttingDistance);
        const g = Connector._getLinearInterpolation(c, target, cuttingDistance);
        const h = Connector._getLinearInterpolation(e, f, cuttingDistance);
        const i = Connector._getLinearInterpolation(f, g, cuttingDistance);
        const j = Connector._getLinearInterpolation(h, i, cuttingDistance);

        return {
            singlePath: {
                source: source,
                sourceControlPoint: b,
                target: target,
                targetControlPoint: c,
            },
            doublePath: {
                endingPath: {
                    source: j,
                    sourceControlPoint: i,
                    target: target,
                    targetControlPoint: g,
                },
                startingPath: {
                    source: source,
                    sourceControlPoint: e,
                    target: j,
                    targetControlPoint: h,
                },
            },
        };
    }

    // -----------------------------------------------------------------------------
    // Handlers
    // -----------------------------------------------------------------------------

    /**
     * Handler for connector_stroke_buttons remove click event.
     *
     * @param {OwlEvent} ev
     */
    _onRemoveButtonClick(ev) {
        const payload = {
            data: deepMerge(this.props.data),
            id: this.props.id,
        };
        this.props.onRemoveButtonClick(payload);
    }
    /**
     * Handler for connector_stroke_buttons reschedule sooner click event.
     *
     * @param {OwlEvent} ev
     */
    _onRescheduleSoonerClick(ev) {
        const payload = {
            data: deepMerge(this.props.data),
            id: this.props.id,
        };
        this.props.onRescheduleSoonerButtonClick(payload);
    }
    /**
     * Handler for connector_stroke_buttons reschedule later click event.
     *
     * @param {OwlEvent} ev
     */
    _onRescheduleLaterClick(ev) {
        const payload = {
            data: deepMerge(this.props.data),
            id: this.props.id,
        };
        this.props.onRescheduleLaterButtonClick(payload);
    }

}

const endProps = {
    shape: {
        left: Number,
        top: Number,
    },
    type: Object,
};
const strokeStyleProps = {
    optional: true,
    shape: {
        color: {
            optional: true,
            type: String,
        },
        hoveredColor: {
            optional: true,
            type: String,
        },
        width: {
            optional: true,
            type: Number,
        },
    },
    type: Object,
};

Object.assign(Connector, {
    props: {
        canBeRemoved: {
            optional: true,
            type: Boolean
        },
        data: {
            optional: true,
            type: Object,
        },
        hoverEaseWidth: {
            optional: true,
            type: Number,
        },
        hovered: {
            optional: true,
            type: Boolean
        },
        inCreation: {
            optional: true,
            type: Boolean,
        },
        id: { type: String | Number },
        source: endProps,
        style: {
            optional: true,
            shape: {
                drawHead: {
                    optional: true,
                    type: Boolean,
                },
                outlineStroke: strokeStyleProps,
                slackness: {
                    optional: true,
                    type: Number,
                    validate: slackness => (0 <= slackness && slackness <= 1),
                },
                stroke: strokeStyleProps,
            },
            type: Object,
        },
        target: endProps,
        onRemoveButtonClick: { type: Function, optional: true },
        onRescheduleSoonerButtonClick: { type: Function, optional: true },
        onRescheduleLaterButtonClick: { type: Function, optional: true },
    },
    defaultProps: {
        onRemoveButtonClick: () => {},
        onRescheduleSoonerButtonClick: () => {},
        onRescheduleLaterButtonClick: () => {},
    },
    template: 'connector',

    // -----------------------------------------------------------------------------
    // Private Static
    // -----------------------------------------------------------------------------

    /**
     * Returns the linear interpolation for a point to be found somewhere between a startingPoint and a endingPoint.
     *
     * @param {{top: number, left: number}} startingPoint
     * @param {{top: number, left: number}} endingPoint
     * @param {number} interpolationPercentage [0, 1] the distance (from 0 startingPoint to 1 endingPoint)
     *        the point has to be computed at.
     * @returns {{top: number, left: number}}
     * @private
     */
    _getLinearInterpolation(startingPoint, endingPoint, interpolationPercentage) {
        if (interpolationPercentage < 0 || 1 > interpolationPercentage) {
            // Ensures interpolationPercentage is within expected boundaries.
            interpolationPercentage = Math.min(Math.max (0, interpolationPercentage), 1);
        }
        const remaining = 1 - interpolationPercentage;
        return {
            left: startingPoint.left * remaining + endingPoint.left * interpolationPercentage,
            top: startingPoint.top * remaining + endingPoint.top * interpolationPercentage
        };
    },
});

export default Connector;
