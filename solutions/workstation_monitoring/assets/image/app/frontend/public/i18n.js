// A single catalog is shared with the device's reason and overlay messages.
const browser = typeof window !== 'undefined' && typeof document !== 'undefined';
const catalogURL = new URL('./locales.json', import.meta.url);
export const messages = browser
  ? await (await fetch(catalogURL, {cache:'no-store'})).json()
  : JSON.parse(await (await import('node:fs/promises')).readFile(catalogURL, 'utf8'));
const preferenceKey = 'worktime.language';
let language = 'zh-CN';
if (browser) {
  try { if (localStorage.getItem(preferenceKey) === 'en') language = 'en'; } catch { /* Storage can be restricted. */ }
}
export function getLanguage() { return language; }
export function tr(key, params = {}, locale = language) {
  const template = messages[key]?.[locale] ?? messages['error.generic'][locale];
  return template.replace(/\{(\w+)\}/g, (_, name) => {
    const value = params[name];
    if (name === 'region' && ['pending','completed'].includes(value)) return tr('studio.'+value,{},locale);
    if (name === 'region' && ['station','seat'].includes(value)) return tr('roi.'+value, {}, locale);
    return String(value ?? '');
  });
}
export function text(id, key, params = {}) {
  const element = document.getElementById(id);
  if (element.dataset.i18n !== key) element.dataset.i18n = key;
  const serialized = JSON.stringify(params);
  if (element.dataset.i18nParams !== serialized) element.dataset.i18nParams = serialized;
  const value = tr(key, params);
  if (element.textContent !== value) element.textContent = value;
}
export function translatePage() {
  document.documentElement.lang = language;
  for (const element of document.querySelectorAll('[data-i18n]')) {
    element.textContent = tr(element.dataset.i18n, JSON.parse(element.dataset.i18nParams || '{}'));
  }
  for (const attribute of ['title','alt','aria-label']) {
    for (const element of document.querySelectorAll(`[data-i18n-${attribute}]`)) {
      element.setAttribute(attribute, tr(element.getAttribute(`data-i18n-${attribute}`)));
    }
  }
  for (const button of document.querySelectorAll('[data-language]')) {
    button.setAttribute('aria-pressed', String(button.dataset.language === language));
  }
}
function applyLanguage(value) {
  if (!['zh-CN','en'].includes(value) || value === language) return;
  language = value;
  translatePage();
  window.dispatchEvent(new Event('languagechange'));
}
export function setLanguage(value) {
  if (!['zh-CN','en'].includes(value)) return;
  try { localStorage.setItem(preferenceKey, value); } catch { /* Preference still works for this page. */ }
  applyLanguage(value);
}
export function errorDetails(error) {
  const key = error.message_key || 'error.' + error.code;
  return {key: messages[key] ? key : 'error.generic', params:error.message_params || {}};
}
export class LocalizedError extends Error {
  constructor(key, params = {}) {
    super(tr(key, params));
    this.message_key = key;
    this.message_params = params;
  }
}
if (browser) {
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-language]');
    if (button) setLanguage(button.dataset.language);
  });
  window.addEventListener('storage', event => {
    if (event.key === preferenceKey) applyLanguage(event.newValue || 'zh-CN');
  });
  translatePage();
}
