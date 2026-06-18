// Plugin host context — TypeScript declarations.
// contract_version: 1
//
// Shape of the `ctx` object passed to a plugin's exported `activate(ctx)`.
// Source of truth: frontend/src/modules/plugin-loader.js (~:84-97).
// Hand-maintained — keep in sync with that object.

export interface PluginI18n {
  /** Merge translation keys for a locale into the host i18n store. */
  mergeTranslations(locale: string, keys: Record<string, unknown>): void;
}

export interface PluginRouter {
  /** Navigate to a hash route within the host SPA. */
  navigate(path: string): void;
  [key: string]: unknown;
}

export interface PluginApi {
  /** Returns the HTTP API base URL of the host backend. */
  getApiBase(): string;
  /** Returns the WebSocket base URL of the host backend. */
  getWsBase(): string;
}

export interface PluginContext {
  /** This plugin's id (manifest.id). */
  pluginId: string;
  /** The parsed plugin.json manifest. */
  manifest: Record<string, unknown>;
  /** The host app root element (document.getElementById('app')). */
  app: HTMLElement | null;
  /** Host SPA router. */
  router: PluginRouter;
  /** Host i18n module. */
  i18n: PluginI18n;
  /** Translate a key via the host i18n store. */
  t(key: string, params?: Record<string, unknown>): string;
  /** Show a transient toast notification. */
  toast(message: string, type?: string): void;
  /** Host backend API/WS base URL accessors. */
  api: PluginApi;
  /** Resolve a relative plugin asset path to a fully-qualified URL. */
  getPluginAsset(path: string): string;
  /** Register a callback invoked when the plugin settings panel renders. */
  onSettingsRender(callback: (...args: unknown[]) => void): void;
}

export interface PluginModule {
  /** Optional activation hook called with the host context. */
  activate?(ctx: PluginContext): void | Promise<void>;
  /** Optional deactivation hook. */
  deactivate?(): void | Promise<void>;
}
