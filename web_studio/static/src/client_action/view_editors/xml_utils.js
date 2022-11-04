/** @odoo-module */

const nodeWeak = new WeakMap();
export function computeXpath(node, upperBoundTag = "form") {
    if (nodeWeak.has(node)) {
        return nodeWeak.get(node);
    }
    const tagName = node.tagName;
    let count = 1;
    let previous = node;
    while ((previous = previous.previousElementSibling)) {
        if (previous.tagName === tagName) {
            count++;
        }
    }
    let xpath = `${tagName}[${count}]`;
    const parent = node.parentElement;
    if (tagName !== upperBoundTag) {
        const parentXpath = computeXpath(parent, upperBoundTag);
        xpath = `${parentXpath}/${xpath}`;
    } else {
        xpath = `/${xpath}`;
    }
    nodeWeak.set(node, xpath);
    return xpath;
}

function xmlNodeToLegacyNode(xpath, node) {
    const attrs = {};

    for (const att of node.getAttributeNames()) {
        attrs[att] = node.getAttribute(att);
    }

    if (attrs.modifiers) {
        attrs.modifiers = JSON.parse(attrs.modifiers);
    } else {
        attrs.modifiers = {};
    }

    if (!attrs.studioXpath) {
        attrs.studioXpath = xpath;
    } else if (attrs.studioXpath !== xpath) {
        // WOWL to remove
        throw new Error("You rascal!");
    }

    const legNode = {
        tag: node.tagName,
        attrs,
    };
    return legNode;
}

export function getLegacyNode(xpath, xml) {
    const nodes = getNodesFromXpath(xpath, xml);
    if (nodes.length !== 1) {
        throw new Error(`xpath ${xpath} yielded no or multiple nodes`);
    }
    return xmlNodeToLegacyNode(xpath, nodes[0]);
}

export function xpathToLegacyXpathInfo(xpath) {
    // eg: /form[1]/field[3]
    // RegExp notice: group 1 : form ; group 2: [1], group 3: 1
    const xpathInfo = [];
    const matches = xpath.matchAll(/\/?(\w+)(\[(\d+)\])?/g);
    for (const m of matches) {
        const info = {
            tag: m[1],
            indice: parseInt(m[3] || 1),
        };
        xpathInfo.push(info);
    }
    return xpathInfo;
}

function getXpathNodes(xpathResult) {
    const nodes = [];
    let res;
    while ((res = xpathResult.iterateNext())) {
        nodes.push(res);
    }
    return nodes;
}

export function getNodesFromXpath(xpath, xml) {
    const owner = "evaluate" in xml ? xml : xml.ownerDocument;
    const xpathResult = owner.evaluate(xpath, xml, null, XPathResult.ORDERED_NODE_ITERATOR_TYPE);
    return getXpathNodes(xpathResult);
}

const parser = new DOMParser();
export const parseStringToXml = (str) => {
    return parser.parseFromString(str, "text/xml");
};

const serializer = new XMLSerializer();
export const serializeXmlToString = (xml) => {
    return serializer.serializeToString(xml);
};
