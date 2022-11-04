/** @odoo-module alias=web_gantt.GanttModel */

import AbstractModel from 'web.AbstractModel';
import { x2ManyCommands } from '@web/core/orm_service';
import concurrency from 'web.concurrency';
import core from 'web.core';
import fieldUtils from 'web.field_utils';
import { findWhere, groupBy } from 'web.utils';
import session from 'web.session';

const _t = core._t;

export default AbstractModel.extend({
    /**
     * @override
     */
    init(parent, params = {}) {
        this._super.apply(this, arguments);

        this.dp = new concurrency.DropPrevious();
        this.mutex = new concurrency.Mutex();
        this.dependencyField = params.dependencyField;
        this.dependencyInvertedField = params.dependencyInvertedField;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Collapses the given row.
     *
     * @param {string} rowId
     */
    collapseRow(rowId) {
        this.allRows[rowId].isOpen = false;
    },
    /**
     * Collapses all rows (first level only).
     */
    collapseRows() {
        this.ganttData.rows.forEach((group) => {
            group.isOpen = false;
        });
    },
    /**
     * Convert date to server timezone
     *
     * @param {Moment} date
     * @returns {string} date in server format
     */
    convertToServerTime(date) {
        const result = date.clone();
        if (!result.isUTC()) {
            result.subtract(session.getTZOffset(date), 'minutes');
        }
        return result.locale('en').format('YYYY-MM-DD HH:mm:ss');
    },
    /**
     * Adds a dependency between masterId and slaveId (slaveId depends
     * on masterId).
     *
     * @param masterId
     * @param slaveId
     * @returns {Promise<*>}
     */
    async createDependency(masterId, slaveId) {
        return this.mutex.exec(() => {
            const writeCommand = {};
            writeCommand[this.dependencyField] = [x2ManyCommands.linkTo(masterId)];
            return this._rpc({
                model: this.modelName,
                method: 'write',
                args: [[slaveId], writeCommand],
            });
        });
    },
    /**
     * Add or subtract value to a moment.
     * If we are changing by a whole day or more, adjust the time if needed to keep
     * the same local time, if the UTC offset has changed between the 2 dates
     * (usually, because of daylight savings)
     *
     * @param {Moment} date
     * @param {integer} offset
     * @param {string} unit
     */
    dateAdd(date, offset, unit) {
        const result = date.clone().add(offset, unit);
        if(Math.abs(result.diff(date, 'hours')) >= 24) {
            const tzOffsetDiff = result.clone().local().utcOffset() - date.clone().local().utcOffset();
            if(tzOffsetDiff !== 0) {
                result.subtract(tzOffsetDiff, 'minutes');
            }
        }
        return result;
    },
    /**
     * @override
     * @param {string} [rowId]
     * @returns {Object} the whole gantt data if no rowId given, the given row's
     *   description otherwise
     */
    __get(rowId) {
        if (rowId) {
            return this.allRows[rowId];
        } else {
            return Object.assign({ isSample: this.isSampleModel }, this.ganttData);
        }
    },
    /**
     * Expands the given row.
     *
     * @param {string} rowId
     */
    expandRow(rowId) {
        this.allRows[rowId].isOpen = true;
    },
    /**
     * Expands all rows.
     */
    expandRows() {
        Object.keys(this.allRows).forEach((rowId) => {
            const row = this.allRows[rowId];
            if (row.isGroup) {
                this.allRows[rowId].isOpen = true;
            }
        });
    },
    /**
     * @override
     * @param {Object} params
     * @param {Object} params.context
     * @param {Object} params.colorField
     * @param {string} params.dateStartField
     * @param {string} params.dateStopField
     * @param {string[]} params.decorationFields
     * @param {string} params.defaultGroupBy
     * @param {string} params.permanentGroupBy
     * @param {boolean} params.displayUnavailability
     * @param {Array[]} params.domain
     * @param {Object} params.fields
     * @param {boolean} params.dynamicRange
     * @param {string[]} params.groupedBy
     * @param {Moment} params.initialDate
     * @param {string} params.modelName
     * @param {string} params.scale
     * @returns {Promise<any>}
     */
    async __load(params) {
        await this._super(...arguments);
        this.modelName = params.modelName;
        this.fields = params.fields;
        this.domain = params.domain;
        this.context = params.context;
        this.decorationFields = params.decorationFields;
        this.colorField = params.colorField;
        this.progressField = params.progressField;
        this.consolidationParams = params.consolidationParams;
        this.collapseFirstLevel = params.collapseFirstLevel;
        this.displayUnavailability = params.displayUnavailability;
        this.SCALES = params.SCALES;
        this.progressBarFields = params.progressBarFields ? params.progressBarFields.split(",") : false;

        this.defaultGroupBy = params.defaultGroupBy ? params.defaultGroupBy.split(',') : [];
        this.permanentGroupBy  = params.permanentGroupBy
        let groupedBy = params.groupedBy;
        if (!groupedBy || !groupedBy.length) {
            groupedBy = this.defaultGroupBy;
        }
        if (this.permanentGroupBy && !groupedBy.includes(this.permanentGroupBy)) {
            groupedBy.push(this.permanentGroupBy)
        }
        groupedBy = this._filterDateInGroupedBy(groupedBy);

        this.ganttData = {
            dateStartField: params.dateStartField,
            dateStopField: params.dateStopField,
            groupedBy,
            fields: params.fields,
            dynamicRange: params.dynamicRange,
        };
        this._setRange(params.initialDate, params.scale);
        return this._fetchData().then(() => {
            // The 'load' function returns a promise which resolves with the
            // handle to pass to the 'get' function to access the data. In this
            // case, we don't want to pass any argument to 'get' (see its API).
            return Promise.resolve();
        });
    },
    /**
     * @param {any} handle
     * @param {Object} params
     * @param {Array[]} params.domain
     * @param {string[]} params.groupBy
     * @param {string} params.scale
     * @param {Moment} params.date
     * @returns {Promise<any>}
     */
    async __reload(handle, params) {
        await this._super(...arguments);
        if ('scale' in params) {
            this._setRange(this.ganttData.focusDate, params.scale);
        }
        if ('date' in params) {
            this._setRange(params.date, this.ganttData.scale);
        }
        if ('domain' in params) {
            this.domain = params.domain;
        }
        if ('groupBy' in params) {
            if (params.groupBy && params.groupBy.length) {
                this.ganttData.groupedBy = this._filterDateInGroupedBy(params.groupBy);
                if(this.ganttData.groupedBy.length !== params.groupBy.length){
                    this.displayNotification({ message: _t('Grouping by date is not supported'), type: 'danger' });
                }
                if (this.permanentGroupBy && !this.ganttData.groupedBy.includes(this.permanentGroupBy)) {
                    this.ganttData.groupedBy.push(this.permanentGroupBy)
                }
            } else {
                this.ganttData.groupedBy = this.defaultGroupBy;
            }
        }
        return this._fetchData().then(() => {
            // The 'reload' function returns a promise which resolves with the
            // handle to pass to the 'get' function to access the data. In this
            // case, we don't want to pass any argument to 'get' (see its API).
            return Promise.resolve();
        });
    },
    /**
     * Create a copy of a task with defaults determined by schedule.
     *
     * @param {integer} id
     * @param {Object} schedule
     * @returns {Promise}
     */
    copy(id, schedule) {
        const defaults = this.rescheduleData(schedule);
        return this.mutex.exec(() => {
            return this._rpc({
                model: this.modelName,
                method: 'copy',
                args: [id, defaults],
                context: this.context,
            });
        });
    },
    /**
     * Removes the dependency between masterId and slaveId (slaveId is no
     * more dependent on masterId).
     *
     * @param masterId
     * @param slaveId
     * @returns {Promise<*>}
     */
    async removeDependency(masterId, slaveId) {
        return this.mutex.exec(() => {
            const writeCommand = {};
            writeCommand[this.dependencyField] = [x2ManyCommands.forget(masterId)];
            return this._rpc({
                model: this.modelName,
                method: 'write',
                args: [[slaveId], writeCommand],
            });
        });
    },
    /**
     * Reschedule a task to the given schedule.
     *
     * @param {integer} id
     * @param {Object} schedule
     * @param {boolean} isUTC
     * @returns {Promise}
     */
    reschedule(ids, schedule, isUTC, callback) {
        if (!_.isArray(ids)) {
            ids = [ids];
        }
        const data = this.rescheduleData(schedule, isUTC);
        return this.mutex.exec(() => {
            return this._rpc({
                model: this.modelName,
                method: 'write',
                args: [ids, data],
                context: this.context,
            }).then((result) => {
                if (callback) {
                    callback(result);
                }
            });
        });
    },
    /**
     * Reschedule masterId or slaveId according to the direction
     *
     * @param direction
     * @param masterId
     * @param slaveId
     * @returns {Promise<*>}
     */
    async rescheduleAccordingToDependency(direction, masterId, slaveId) {
        return this.mutex.exec(() => {
            return this._rpc({
                model: this.modelName,
                method: 'web_gantt_reschedule',
                args: [
                    direction,
                    masterId,
                    slaveId,
                    this.dependencyField,
                    this.dependencyInvertedField,
                    this.ganttData.dateStartField,
                    this.ganttData.dateStopField
                ],
            });
        });
    },
    /**
     * @param {Object} schedule
     * @param {boolean} isUTC
     */
    rescheduleData(schedule, isUTC) {
        const allowedFields = [
            this.ganttData.dateStartField,
            this.ganttData.dateStopField,
            ...this.ganttData.groupedBy
        ];

        const data = _.pick(schedule, allowedFields);

        let type;
        for (let k in data) {
            type = this.fields[k].type;
            if (data[k] && (type === 'datetime' || type === 'date') && !isUTC) {
                data[k] = this.convertToServerTime(data[k]);
            }
        };
        return data
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetches records to display (and groups if necessary).
     *
     * @private
     * @returns {Deferred}
     */
    _fetchData() {
        const domain = this._getDomain();
        const context = Object.assign({}, this.context, { group_by: this.ganttData.groupedBy });

        let groupsDef;
        if (this.ganttData.groupedBy.length) {
            groupsDef = this._rpc({
                model: this.modelName,
                method: 'read_group',
                fields: this._getFields(),
                domain: domain,
                context: context,
                groupBy: this.ganttData.groupedBy,
                orderBy: this.ganttData.groupedBy.map((f) => { return {name: f}; }),
                lazy: this.ganttData.groupedBy.length === 1,
            });
        }

        const dataDef = this._rpc({
            route: '/web/dataset/search_read',
            model: this.modelName,
            fields: this._getFields(),
            context: context,
            orderBy: [{name: this.ganttData.dateStartField}],
            domain: domain,
        });

        return this.dp.add(Promise.all([groupsDef, dataDef])).then((results) => {
            const groups = results[0] || [];
            groups.forEach((g) => (g.fromServer = true));
            const searchReadResult = results[1];
            const oldRows = this.allRows;
            this.allRows = {};
            this.ganttData.records = this._parseServerData(searchReadResult.records);
            this.ganttData.rows = this._generateRows({
                groupedBy: this.ganttData.groupedBy,
                groups: groups,
                oldRows: oldRows,
                parentPath: [],
                records: this.ganttData.records,
            });
            const proms = [];
            if (this.displayUnavailability && !this.isSampleModel) {
                proms.push(this._fetchUnavailability());
            }
            if (this.progressBarFields && !this.isSampleModel) {
                proms.push(this._fetchProgressBarData());
            }
            return Promise.all(proms);
        });
    },
    /**
     * Compute rows for unavailability rpc call.
     *
     * @private
     * @param {Object} rows in the format of ganttData.rows
     * @returns {Object} simplified rows only containing useful attributes
     */
    _computeUnavailabilityRows(rows) {
        return _.map(rows, (r) => {
            if (r) {
                return {
                    groupedBy: r.groupedBy,
                    records: r.records,
                    name: r.name,
                    resId: r.resId,
                    rows: this._computeUnavailabilityRows(r.rows)
                }
            } else {
                return r;
            }
        });
    },
    /**
     * Fetches gantt unavailability.
     *
     * @private
     * @returns {Deferred}
     */
    _fetchUnavailability() {
        return this._rpc({
            model: this.modelName,
            method: 'gantt_unavailability',
            args: [
                this.convertToServerTime(this.ganttData.startDate),
                this.convertToServerTime(this.ganttData.stopDate),
                this.ganttData.scale,
                this.ganttData.groupedBy,
                this._computeUnavailabilityRows(this.ganttData.rows),
            ],
            context: this.context,
        }).then((enrichedRows) => {
            // Update ganttData.rows with the new unavailabilities data
            this._updateUnavailabilityRows(this.ganttData.rows, enrichedRows);
        });
    },
    /**
     * Update rows with unavailabilities from enriched rows.
     *
     * @private
     * @param {Object} original rows in the format of ganttData.rows
     * @param {Object} enriched rows as returned by the gantt_unavailability rpc call
     * @returns {Object} original rows enriched with the unavailabilities data
     */
    _updateUnavailabilityRows(original, enriched) {
        _.zip(original, enriched).forEach((rowPair) => {
            const o = rowPair[0];
            const e = rowPair[1];
            o.unavailabilities = _.map(e.unavailabilities, (u) => {
                // These are new data from the server, they haven't been parsed yet
                u.start = this._parseServerValue({ type: 'datetime' }, u.start);
                u.stop = this._parseServerValue({ type: 'datetime' }, u.stop);
                return u;
            });
            if (o.rows && e.rows) {
                this._updateUnavailabilityRows(o.rows, e.rows);
            }
        });
    },
    /**
     * Process groups and records to generate a recursive structure according
     * to groupedBy fields. Note that there might be empty groups (filled by
     * read_goup with group_expand) that also need to be processed.
     *
     * @private
     * @param {Object} params
     * @param {Object[]} params.groups
     * @param {Object[]} params.records
     * @param {string[]} params.groupedBy
     * @param {Object} params.oldRows previous version of this.allRows (prior to
     *   this reload), used to keep collapsed rows collapsed
     * @param {Object[]} params.parentPath used to determine the ancestors of a
     *   row through their groupedBy field and value.
     *   The stringification of this must give a unique identifier to the parent row.
     * @returns {Object[]}
     */
    _generateRows(params) {
        const { groupedBy, groups, oldRows, parentPath, records } = params;
        const groupLevel = this.ganttData.groupedBy.length - groupedBy.length;
        if (!groupedBy.length || !groups.length) {
            const row = {
                groupLevel,
                id: JSON.stringify([...parentPath, {}]),
                isGroup: false,
                name: "",
                records,
            };
            this.allRows[row.id] = row;
            return [row];
        }

        const rows = [];
        // Some groups might be empty (thanks to expand_groups), so we can't
        // simply group the data, we need to keep all returned groups
        const groupedByField = groupedBy[0];
        const currentLevelGroups = groupBy(groups, group => {
            if (group[groupedByField] === undefined) {
                // Here we change undefined value to false as:
                // 1/ we want to group together:
                //    - groups having an undefined value for groupedByField
                //    - groups having false value for groupedByField
                // 2/ we want to be sure that stringification keeps
                //    the groupedByField because of:
                //      JSON.stringify({ key: undefined }) === "{}"
                //      (see id construction below)
                group[groupedByField] = false;
            }
            return group[groupedByField];
        });
        const isM2MGrouped = this.ganttData.fields[groupedByField].type === "many2many";
        let groupedRecords;
        if (isM2MGrouped) {
            groupedRecords = {};
            for (const [key, currentGroup] of Object.entries(currentLevelGroups)) {
                groupedRecords[key] = [];
                const value = currentGroup[0][groupedByField];
                for (const r of records || []) {
                    if (
                        !value && r[groupedByField].length === 0 ||
                        value && r[groupedByField].includes(value[0])
                    ) {
                        groupedRecords[key].push(r)
                    }
                }
            }
        } else {
            groupedRecords = groupBy(records || [], groupedByField);
        }

        for (const key in currentLevelGroups) {
            const subGroups = currentLevelGroups[key];
            const groupRecords = groupedRecords[key] || [];
            // For empty groups (or when groupedByField is a m2m), we can't look at the record to get the
            // formatted value of the field, we have to trust expand_groups.
            let value;
            if (groupRecords && groupRecords.length && !isM2MGrouped) {
                value = groupRecords[0][groupedByField];
            } else {
                value = subGroups[0][groupedByField];
            }
            const part = {};
            part[groupedByField] = value;
            const path = [...parentPath, part];
            const id = JSON.stringify(path);
            const resId = Array.isArray(value) ? value[0] : value;
            const minNbGroups = this.collapseFirstLevel ? 0 : 1;
            const isGroup = groupedBy.length > minNbGroups;
            const fromServer = subGroups.some((g) => g.fromServer);
            const row = {
                name: this._getRowName(groupedByField, value),
                groupedBy,
                groupedByField,
                groupLevel,
                id,
                resId,
                isGroup,
                fromServer,
                isOpen: !findWhere(oldRows, { id: JSON.stringify(parentPath), isOpen: false }),
                records: groupRecords,
            };

            if (isGroup) {
                row.rows = this._generateRows({
                    ...params,
                    groupedBy: groupedBy.slice(1),
                    groups: subGroups,
                    oldRows,
                    parentPath: path,
                    records: groupRecords,
                });
                row.childrenRowIds = [];
                row.rows.forEach((subRow) => {
                    row.childrenRowIds.push(subRow.id);
                    row.childrenRowIds = row.childrenRowIds.concat(subRow.childrenRowIds || []);
                });
            }

            rows.push(row);
            this.allRows[row.id] = row;
        }
        return rows;
    },
    /**
     * Get domain of records to display in the gantt view.
     *
     * @private
     * @returns {Array[]}
     */
    _getDomain() {
        const domain = [
            [this.ganttData.dateStartField, '<=', this.convertToServerTime(this.ganttData.stopDate)],
            [this.ganttData.dateStopField, '>=', this.convertToServerTime(this.ganttData.startDate)],
        ];
        return this.domain.concat(domain);
    },
    /**
     * Get all the fields needed.
     *
     * @private
     * @returns {string[]}
     */
    _getFields() {
        let fields = ['display_name', this.ganttData.dateStartField, this.ganttData.dateStopField];
        fields = fields.concat(this.ganttData.groupedBy, this.decorationFields);

        if (this.progressField) {
            fields.push(this.progressField);
        }

        if (this.colorField) {
            fields.push(this.colorField);
        }

        if (this.consolidationParams.field) {
            fields.push(this.consolidationParams.field);
        }

        if (this.consolidationParams.excludeField) {
            fields.push(this.consolidationParams.excludeField);
        }

        return _.uniq(fields);
    },
    /**
     * Format field value to display purpose.
     *
     * @private
     * @param {any} value
     * @param {Object} field
     * @returns {string} formatted field value
     */
    _getFieldFormattedValue(value, field) {
        let options = {};
        if (field.type === 'boolean') {
            options = {forceString: true};
        }
        let label;
        if (field.type === "many2many") {
            label = Array.isArray(value) ? value[1] : value;
        } else {
            label = fieldUtils.format[field.type](value, field, options);
        }
        return label || _.str.sprintf(_t('Undefined %s'), field.string);
    },
    /**
     * @param {string} groupedByField
     * @param {*} value
     * @returns {string}
     */
    _getRowName(groupedByField, value) {
        const field = this.fields[groupedByField];
        return this._getFieldFormattedValue(value, field);
    },
    /**
     * @override
     */
    _isEmpty() {
        return !this.ganttData.records.length;
    },
    /**
     * Parse in place the server values (and in particular, convert datetime
     * field values to moment in UTC).
     *
     * @private
     * @param {Object} data the server data to parse
     * @returns {Promise<any>}
     */
    _parseServerData(data) {
        data.forEach((record) => {
            Object.keys(record).forEach((fieldName) => {
                record[fieldName] = this._parseServerValue(this.fields[fieldName], record[fieldName]);
            });
        });

        return data;
    },
    /**
     * Set date range to render gantt
     *
     * @private
     * @param {Moment} focusDate current activated date
     * @param {string} scale current activated scale
     */
    _setRange(focusDate, scale) {
        this.ganttData.scale = scale;
        this.ganttData.focusDate = focusDate;
        if (this.ganttData.dynamicRange) {
            this.ganttData.startDate = focusDate.clone().startOf(this.SCALES[scale].interval);
            this.ganttData.stopDate = this.ganttData.startDate.clone().add(1, scale);
        } else {
            this.ganttData.startDate = focusDate.clone().startOf(scale);
            this.ganttData.stopDate = focusDate.clone().endOf(scale);
        }
    },
    /**
     * Remove date in groupedBy field
     */
    _filterDateInGroupedBy(groupedBy) {
        return groupedBy.filter(
            groupedByField => {
                const fieldName = groupedByField.split(':')[0];
                return fieldName in this.fields && this.fields[fieldName].type.indexOf('date') === -1;
            }
        );
    },

    //----------------------
    // Gantt Progress Bars
    //----------------------
    /**
     * Get progress bars info in order to display progress bar in gantt title column
     *
     * @private
     */
    _fetchProgressBarData() {
        const progressBarFields = this.progressBarFields.filter(field => this.ganttData.groupedBy.includes(field));
        if (this.isSampleModel || !progressBarFields.length) {
            return;
        }
        const resIds = {};
        let hasResIds = false;
        for (const field of progressBarFields) {
            resIds[field] = this._getProgressBarResIds(field, this.ganttData.rows);
            hasResIds = hasResIds || resIds[field].length;
        }
        if (!hasResIds) {
            return;
        }
        return this._rpc({
            model: this.modelName,
            method: 'gantt_progress_bar',
            args: [
                progressBarFields,
                resIds,
                this.convertToServerTime(this.ganttData.startDate),
                this.convertToServerTime(this.ganttData.endDate || this.ganttData.startDate.clone().add(1, this.ganttData.scale)),
            ],
        }).then((progressBarInfo) => {
            for (const field of progressBarFields) {
                this._addProgressBarInfo(field, this.ganttData.rows, progressBarInfo[field]);
            }
        });
    },
    /**
     * Recursive function to get resIds of groups where the progress bar will be added.
     *
     * @private
     */
    _getProgressBarResIds(field, rows) {
        const resIds = [];
        for (const row of rows) {
            if (row.groupedByField === field) {
                if (row.resId !== false) {
                    resIds.push(row.resId);
                }
            } else {
                resIds.push(...this._getProgressBarResIds(field, row.rows || []));
            }
        }
        return [...new Set(resIds)];
    },
    /**
     * Recursive function to add progressBar info to rows grouped by the field.
     *
     * @private
     */
    _addProgressBarInfo(field, rows, progressBarInfo) {
        for (const row of rows) {
            if (row.groupedByField === field) {
                row.progressBar = progressBarInfo[row.resId];
                if (row.progressBar) {
                    row.progressBar.value_formatted = fieldUtils.format.float(row.progressBar.value, {'digits': [false, 0]});
                    row.progressBar.max_value_formatted = fieldUtils.format.float(row.progressBar.max_value, {'digits': [false, 0]});
                    row.progressBar.ratio = row.progressBar.max_value ? row.progressBar.value / row.progressBar.max_value * 100 : 0;
                    row.progressBar.warning = progressBarInfo.warning;
                }
            } else {
                this._addProgressBarInfo(field, row.rows, progressBarInfo);
            }
        }
    },
});
