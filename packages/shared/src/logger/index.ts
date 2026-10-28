/**
 * Shared logger used across apps.
 *
 * Deliberately a thin alias over `console` so it works unchanged in Node,
 * the browser and React Native. Swap the implementation here if the apps ever
 * need levels, redaction or a transport.
 */
export const logger = console;
