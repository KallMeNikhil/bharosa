import "@testing-library/jest-dom/vitest";

// Node 26 defines its own global localStorage, which is undefined unless Node is started
// with --localstorage-file and which hides jsdom's. Give the tests an in-memory one.
if (typeof window !== "undefined" && !window.localStorage) {
  const store = new Map<string, string>();
  const memoryStorage: Storage = {
    get length() {
      return store.size;
    },
    clear: () => store.clear(),
    getItem: (key) => store.get(key) ?? null,
    key: (index) => Array.from(store.keys())[index] ?? null,
    removeItem: (key) => {
      store.delete(key);
    },
    setItem: (key, value) => {
      store.set(key, String(value));
    },
  };
  Object.defineProperty(window, "localStorage", { configurable: true, value: memoryStorage });
}

window.scrollTo = () => undefined;
