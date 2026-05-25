import React, { createContext, useContext, useEffect, useState } from 'react';

export type Env = 'detecting' | 'desktop' | 'browser';

interface EnvironmentValue {
  env: Env;
}

const EnvironmentContext = createContext<EnvironmentValue>({ env: 'detecting' });

type PyWebView = { api: { show_window: () => void } };

function getPyWebView(): PyWebView | undefined {
  return (window as Window & { pywebview?: PyWebView }).pywebview;
}

export function EnvironmentProvider({ children }: { children: React.ReactNode }) {
  const [env, setEnv] = useState<Env>('detecting');

  useEffect(() => {
    if (getPyWebView()) {
      setEnv('desktop');
      return;
    }

    let resolved = false;

    const resolve = (value: Env) => {
      if (!resolved) {
        resolved = true;
        setEnv(value);
      }
    };

    window.addEventListener('pywebviewready', () => resolve('desktop'));

    // If pywebviewready hasn't fired within 800ms, we're in a browser
    const timer = setTimeout(() => resolve('browser'), 800);

    return () => clearTimeout(timer);
  }, []);

  // Show the pywebview window once the env is confirmed as desktop
  useEffect(() => {
    if (env !== 'desktop') return;
    const pyw = getPyWebView();
    if (pyw) {
      pyw.api.show_window();
    } else {
      const handler = () => getPyWebView()?.api.show_window();
      window.addEventListener('pywebviewready', handler);
      return () => window.removeEventListener('pywebviewready', handler);
    }
  }, [env]);

  return (
    <EnvironmentContext.Provider value={{ env }}>
      {children}
    </EnvironmentContext.Provider>
  );
}

export const useEnvironment = () => useContext(EnvironmentContext);
