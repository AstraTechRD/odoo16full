/** @odoo-module **/


// -----------------------------------------------------------------------------
// Private
// -----------------------------------------------------------------------------

/**
 * Clones the value according to its type and returns it.
 *
 * @param value
 * @return {Object|Array|*} The cloned value.
 * @private
 */
function _clone(value) {
    if (_isPlainObject(value) || Array.isArray(value)) {
        return deepMerge(_getEmptyTarget(value), value);
    } else {
        return value;
    }
}

/**
 * Gets an empty value according to value's type.
 *
 * @param {Object | Array} value
 * @return {Object | Array} an empty Array or Object.
 * @private
 */
function _getEmptyTarget(value) {
    return Array.isArray(value) ? [] : { };
}

/**
 * Returns whether the provided argument is a plain object or not.
 *
 * @param {*} value
 * @returns {boolean} true if the provided argument is a plain object, false if not.
 */
function _isPlainObject(value) {
    if (typeof value == 'object' && value !== null) {
        const proto = Object.getPrototypeOf(value);
        return proto === Object.prototype || proto === null;
    }
    return false;
}

/**
 * Deep merges target and source arrays and returns the result.
 *
 * @param {Array} target
 * @param {Array} source
 * @return {Array} the result of the merge.
 * @private
 */
function _deepMergeArray(target, source) {
    return target.concat(source)
                 .map((entry) => _clone(entry));
}

/**
 * Deep merges target and source Objects and returns the result
 *
 * @param {Object} target
 * @param {Object} source
 * @return {Object} the result of the merge.
 */
function _mergeObject(target, source) {
    const destination = { };
    if (_isPlainObject(target)) {
        Object.keys(target).forEach((key) => {
            destination[key] = _clone(target[key]);
        });
    }
    Object.keys(source).forEach((key) => {
        if ((_isPlainObject(target) && key in target) && _isPlainObject(source[key])) {
            destination[key] = deepMerge(target[key], source[key]);
        } else {
            destination[key] = _clone(source[key]);
        }
    });
    return destination;
}

// -----------------------------------------------------------------------------
// Public
// -----------------------------------------------------------------------------

/**
 * Deep merges target and source and returns the result.
 * This implementation has been added since vanilla JS is now preferred.
 * A deep copy is made of all the plain objects and arrays.
 * For the other type of objects (like HTMLElement, etc.), the reference is passed.
 *
 * @param {Object | Array} target
 * @param {Object | Array} [source] if source is undefined, target wil be set to an empty value of source type.
 * @returns {Object | Array} the result of the merge.
 */
export function deepMerge(target, source) {
    if (typeof source === 'undefined') {
        source = _getEmptyTarget(source);
    }

    const isSourceAnArray = Array.isArray(source);
    const isTargetAnArray = Array.isArray(target);

    if (isSourceAnArray !== isTargetAnArray) {
        return _clone(source);
    } else if (isSourceAnArray) {
        return _deepMergeArray(target, source);
    } else {
        return _mergeObject(target, source);
    }
}

/**
 * Deep merges all the entries from the passed array and returns the result.
 *
 * @param {Array} array the elements to be merged together.
 * @return {Object | Array} the result of the merge.
 */
export function deepMergeAll(array) {
    if (!Array.isArray(array)) {
        throw new Error('deepmergeAll argument must be an Array.');
    }
    return array.reduce((accumulator, current) => deepMerge(accumulator, current), { });
}
