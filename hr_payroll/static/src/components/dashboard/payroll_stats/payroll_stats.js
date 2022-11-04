/** @odoo-module **/

import { loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";
import { getColor } from "@web/views/graph/colors";

const { Component, onWillUnmount, useEffect, useRef, useState, onWillStart } = owl;

export class PayrollDashboardStats extends Component {
    setup() {
        this.actionService = useService("action");
        this.canvasRef = useRef('canvas');
        this.state = useState({ monthly: true });
        onWillStart(() => loadJS("/web/static/lib/Chart/Chart.js"));
        useEffect(() => this.renderChart());
        onWillUnmount(() => {
            if (this.chart) {
                this.chart.destroy();
            }
        });
    }

    /**
     * @returns {string}
     */
    get tooltipInfo() {
        return JSON.stringify({
            help: this.props.help,
        });
    }

    toggle() {
        this.state.monthly = !this.state.monthly;
    }

    /**
     * @returns {object} The current chart data to be used depending on the state
     */
    get graphData() {
        return this.props.data[this.state.monthly ? 'monthly': 'yearly'];
    }

    /**
     * Creates and binds the chart on `canvasRef`.
     */
    renderChart() {
        if (this.chart) {
            this.chart.destroy();
        }
        const ctx = this.canvasRef.el.getContext('2d');
        this.chart = new Chart(ctx, this.getChartConfig());
    }

    /**
     * @returns {object} Chart config for the current data
     */
    getChartConfig() {
        const type = this.props.type;
        if (type === 'line') {
            return this.getLineChartConfig();
        } else if (type === 'bar') {
            return this.getBarChartConfig();
        } else if (type === 'stacked_bar') {
            return this.getStackedBarChartConfig();
        }
        return {};
    }

    /**
     * @returns {object} Chart config of type 'line'
     */
    getLineChartConfig() {
        const data = this.graphData
        const labels = data.map(function (pt) {
            return pt.x;
        });
        const borderColor = this.props.is_sample ? '#dddddd' : '#875a7b';
        const backgroundColor = this.props.is_sample ? '#ebebeb' : '#dcd0d9';
        return {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    fill: 'start',
                    label: this.props.label,
                    backgroundColor: backgroundColor,
                    borderColor: borderColor,
                    borderWidth: 2,
                }],
            },
            options: {
                legend: {display: false},
                scales: {
                    yAxes: [
                        {
                            display: false,
                            ticks: {
                                beginAtZero: true,
                            },
                        }
                    ],
                    xAxes: [{display: false}],
                },
                maintainAspectRatio: false,
                elements: {
                    line: {
                        tension: 0.000001,
                    },
                },
                tooltips: {
                    intersect: false,
                    position: 'nearest',
                    caretSize: 0,
                },
            },
        };
    }

    /**
     * @returns {object} Chart config of type 'bar'
     */
    getBarChartConfig() {
        const data = [];
        const labels = [];
        const backgroundColors = [];
        this.graphData.forEach((pt) => {
            data.push(pt.value);
            labels.push(pt.label);
            const color = this.props.is_sample ? '#ebebeb' : (pt.type === 'past' ? '#ccbdc8' : (pt.type === 'future' ? '#a5d8d7' : getColor(19)));
            backgroundColors.push(color);
        });

        return {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    fill: 'start',
                    label: this.props.label,
                    backgroundColor: backgroundColors,
                }],
            },
            options: {
                legend: {display: false},
                scales: {
                    yAxes: [
                        {
                            display: false,
                            ticks: {
                                beginAtZero: true,
                            },
                        }
                    ],
                },
                maintainAspectRatio: false,
                tooltips: {
                    intersect: false,
                    position: 'nearest',
                    caretSize: 0,
                },
                elements: {
                    line: {
                        tension: 0.000001
                    }
                }
            }
        };
    }

    /**
     * @returns {object} Chart config of type 'stacked bar'
     */
    getStackedBarChartConfig() {
        const labels = [];
        const datasets = [];
        const datasets_labels = [];
        const colors = this.props.is_sample ? ['#e7e7e7', '#dddddd', '#f0f0f0', '#fafafa'] : [getColor(13), '#a5d8d7', '#ebebeb', '#ebebeb'];


        _.each(this.graphData, function(graphData, code) {
            datasets_labels.push(code);
            const dataset_data = [];
            const formatted_data = []
            graphData.forEach(function (pt) {
                if (!labels.includes(pt.label)) {
                    labels.push(pt.label);
                }
                formatted_data.push(`${code}: ${pt.formatted_value || pt.value}`);
                dataset_data.push(pt.value);
            })
            datasets.push({
                data: dataset_data,
                label: code,
                backgroundColor: colors[datasets_labels.length - 1],
                formatted_data: formatted_data
            })
        });


        return {
            type: 'bar',
            data: {
                labels: labels,
                datasets: datasets,
            },
            options: {
                legend: {display: false},
                responsive: true,
                scales: {
                    xAxes: [
                        {
                            stacked: true,
                        }
                    ],
                    yAxes: [
                        {
                            display: false,
                            stacked: true,
                            ticks: {
                                beginAtZero: true,
                            },
                        }
                    ],
                },
                maintainAspectRatio: false,
                tooltips: {
                    intersect: false,
                    position: 'nearest',
                    caretSize: 0,
                    callbacks: {
                        label: function(tooltipItem, data) {
                            const {datasetIndex, index} = tooltipItem;
                            return data.datasets[datasetIndex].formatted_data[index];
                        }
                    }
                },
                elements: {
                    line: {
                        tension: 0.000001
                    }
                }
            }
        }
    }


}

PayrollDashboardStats.template = 'hr_payroll.DashboardStats';
