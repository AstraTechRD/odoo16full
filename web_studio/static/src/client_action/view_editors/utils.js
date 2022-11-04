/** @odoo-module */

export function cleanHooks(el) {
    for (const hookEl of el.querySelectorAll(".o_web_studio_nearest_hook")) {
        hookEl.classList.remove("o_web_studio_nearest_hook");
    }
}

export function getActiveHook(el) {
    return el.querySelector(".o_web_studio_nearest_hook");
}

// A naive function that determines if the toXpath on which we dropped
// our object is actually the same as the fromXpath of the element we dropped.
// Naive because it won't evaluate xpath, just guess whether they are equivalent
// under precise conditions.
function isToXpathEquivalentFromXpath(position, toXpath, fromXpath) {
    if (toXpath === fromXpath) {
        return true;
    }
    const toParts = toXpath.split("/");
    const fromParts = fromXpath.split("/");

    // Are the paths at least in the same parent node ?
    if (toParts.slice(0, -1).join("/") !== fromParts.slice(0, -1).join("/")) {
        return false;
    }

    const nodeIdxRegExp = /(\w+)(\[(\d+)\])?/;
    const toMatch = toParts[toParts.length - 1].match(nodeIdxRegExp);
    const fromMatch = fromParts[fromParts.length - 1].match(nodeIdxRegExp);

    // Are the paths comparable in terms of their node tag ?
    if (fromMatch[1] !== toMatch[1]) {
        return false;
    }

    // Is the position actually referring to the same place ?
    if (position === "after" && parseInt(toMatch[3] || 1) + 1 === parseInt(fromMatch[3] || 1)) {
        return true;
    }
    return false;
}

export function getDroppedValues({ droppedData, xpath, fieldName, position }) {
    const isNew = droppedData.isNew;
    let values;
    if (isNew) {
        values = {
            type: "add",
            structure: droppedData.structure,
            field_description: droppedData.field_description,
            xpath,
            new_attrs: droppedData.new_attrs,
            position: position,
        };
    } else {
        if (isToXpathEquivalentFromXpath(position, xpath, droppedData.studioXpath)) {
            return;
        }
        values = {
            type: "move",
            xpath,
            position: position,
            structure: "field",
            new_attrs: {
                name: droppedData.fieldName,
            },
        };
    }
    return values;
}

export function getHooks(el) {
    return [...el.querySelectorAll(".o_web_studio_hook")];
}

export function extendEnv(env, extension) {
    const nextEnv = Object.create(env);
    const descrs = Object.getOwnPropertyDescriptors(extension);
    Object.defineProperties(nextEnv, descrs);
    return Object.freeze(nextEnv);
}

// A standardized method to determine if a component is visible
export function studioIsVisible(props) {
    return props.studioIsVisible !== undefined ? props.studioIsVisible : true;
}
