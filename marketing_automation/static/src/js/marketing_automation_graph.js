/** @odoo-module */


import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
const fieldRegistry = registry.category("fields");
const { Component, onWillStart, onWillUnmount, useEffect, useRef } = owl;

/**
 * Inspired from the GraphView
 */
export class MarketingActivityGraph extends Component {
    setup() {
        this.chart = null;
        this.canvasRef = useRef("canvas");

        onWillStart(() => loadJS("/web/static/lib/Chart/Chart.js"));
        useEffect(() => this.renderChart());
        onWillUnmount(this.onWillUnmount);
    }

    onWillUnmount() {
        if (this.chart) {
            this.chart.destroy();
        }
    }

    //--------------------------------------------------------------------------
    // Business
    //--------------------------------------------------------------------------

    /**
     * Instantiates a Chart (Chart.js lib) to render the graph according to
     * the current config.
     */
    renderChart() {
        if (this.chart) {
            this.chart.destroy();
        }
        const config = this.getChartConfig();
        this.chart = new Chart(this.canvasRef.el, config);
    }

    getChartConfig() {
        const chartData = JSON.parse(this.props.value);

        const datasets = chartData.map((group) => {
            const borderColor = this.hexToRGBA(group.color, 1);
            const fillColor = this.hexToRGBA(group.color, 0.6);
            return {
                label: group.label,
                data: group.points,
                fill: 'origin',
                backgroundColor: fillColor,
                borderColor: borderColor,
                borderWidth: 2,
                pointBackgroundColor: 'rgba(0, 0, 0, 0)',
                pointBorderColor: borderColor,
            };
        });

        const labels = chartData[0].points.map((point) => {
            return point.x;
        });

        Chart.defaults.global.elements.line.tension = 0;

        return {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets,
            },
            options: {
                animation: false,
                layout: {
                    padding: {left: 25, right: 20, top: 5, bottom: 20}
                },
                legend: {
                    display: false,
                },
                maintainAspectRatio: false,
                scales: {
                    yAxes: [{
                        type: 'linear',
                        display: false,
                        ticks: {
                            beginAtZero: true,
                        },
                    }],
                    xAxes: [{
                        ticks: {
                            maxRotation: 0,
                        },
                    }],
                },
                tooltips: {
                    mode: 'index',
                    intersect: false,
                    bodyFontColor: 'rgba(0,0,0,1)',
                    titleFontSize: 13,
                    titleFontColor: 'rgba(0,0,0,1)',
                    backgroundColor: 'rgba(255,255,255,0.6)',
                    borderColor: 'rgba(0,0,0,0.2)',
                    borderWidth: 2,
                    callbacks: {
                        labelColor: (tooltipItem, chart) => {
                            const dataset = chart.data.datasets[tooltipItem.datasetIndex];
                            const tooltipBorderColor = chart.tooltip._model.backgroundColor;
                            return {
                                borderColor: tooltipBorderColor,
                                backgroundColor: dataset.backgroundColor,
                            };
                        },
                    }
                }
            }
        };
    }

    //--------------------------------------------------------------------------
    // Tools
    //--------------------------------------------------------------------------

    /**
     * Converts a hex color code with an opacity to apply into a rgba string.
     *
     * @param {String} hex the hex color code (e.g: #AB05D7)
     * @param {float} opacity the float opacity to apply
     * @returns {String} the rgba string
     */
    hexToRGBA(hex, opacity) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        const rgb = result.slice(1, 4).map((n) => {
            return parseInt(n, 16);
        }).join(',');
        return 'rgba(' + rgb + ',' + opacity + ')';
    }
}

MarketingActivityGraph.template = "marketing_automation.MarketingActivityGraph";

fieldRegistry.add('marketing_activity_graph', MarketingActivityGraph);
