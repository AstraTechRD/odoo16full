/** @odoo-module */

import { patch } from '@web/core/utils/patch';
import { registry } from '@web/core/registry';
import { utils } from '@web/../tests/helpers/mock_env';

const { prepareRegistriesWithCleanup } = utils;

export function makeFakeMessagingServiceForKnowledge() {
    return {
        start() {
            return {
                async get() {
                    return {
                        knowledge: {
                            randomEmojis: [{codepoints: "🥸"}, {codepoints: "🗿"}],
                            update() {},
                        },
                        messagingBus: {
                            addEventListener() {},
                            removeEventListener() {},
                            trigger() {},
                        },
                        openChat() {},
                        rpc() {},
                        emojiRegistry: {
                            allEmojis: [{codepoints: "🥸"}, {codepoints: "🗿"}],
                            isLoaded: true,
                            isLoading: false,
                            loadEmojiData: () => {},
                        },
                    };
                },
                modelManager: {
                    startListening() {},
                    stopListening() {},
                    removeListener() {},
                    messagingCreatedPromise: new Promise(() => {}),
                },
            };
        }
    };
}

function makeFakeKnowledgeCommandsService() {
    return {
        start() {
            return {
                setCommandsRecordInfo() {},
                getCommandsRecordInfo() { return null; },
            };
        }
    };
}

const serviceRegistry = registry.category('services');
patch(utils, 'knowledge_test_registries', {
    prepareRegistriesWithCleanup() {
        prepareRegistriesWithCleanup(...arguments);
        serviceRegistry.add('knowledgeCommandsService', makeFakeKnowledgeCommandsService());
    },
});
