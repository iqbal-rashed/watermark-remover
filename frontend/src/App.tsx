import React, { useEffect, useState } from 'react';
import { HashRouter, Route, Routes, Navigate } from 'react-router-dom';
import { TopBar } from './components/TopBar';
import { UploadView } from './components/UploadView';
import { CropSelector } from './components/CropSelector';
import { OptionsPanel } from './components/OptionsPanel';
import { ProcessingState } from './components/ProcessingState';
import { ResultView } from './components/ResultView';
import { useWatermarkApp } from './hooks/useWatermarkApp';
import { Toaster } from './components/Sonner';
import { Onboarding } from './pages/Onboarding';
import { Loader2, RefreshCw, Monitor, Globe } from 'lucide-react';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import { EnvironmentProvider, useEnvironment } from './contexts/EnvironmentContext';
import { Logo } from './components/Logo';
import { Button } from './components/Button';

// ── Main app page ─────────────────────────────────────────────────────────────

function MainApp() {
  const { theme } = useTheme();
  const {
    appState, media, box, setBox, options, setOptions, progress, statusText,
    resultUrl, resultFilename, selectionMethod, setSelectionMethod,
    isDetecting, detectionProgress, detectionStatus,
    handleUpload, handleAutoDetect, handleManualBox, handleProcess, handleReset,
  } = useWatermarkApp();

  return (
    <div className="h-screen w-screen flex flex-col bg-background text-foreground overflow-hidden">
      <Toaster theme={theme} position="bottom-right" />
      <TopBar
        onNew={handleReset}
        showNew={appState !== 'idle'}
      />
      <main className="flex-1 flex overflow-hidden">
        {appState === 'idle' && <UploadView onUpload={handleUpload} />}

        {appState === 'editing' && media && (
          <>
            <div className="flex-1 min-w-0 flex flex-col bg-muted/30">
              <div className="flex-1 min-h-0 overflow-hidden">
                <CropSelector
                  mediaType={media.type}
                  mediaUrl={media.url}
                  naturalWidth={media.naturalWidth}
                  naturalHeight={media.naturalHeight}
                  box={box}
                  onBoxChange={setBox}
                  drawingEnabled={selectionMethod === 'draw'}
                  isDetecting={isDetecting}
                  detectionProgress={detectionProgress}
                  detectionStatus={detectionStatus}
                />
              </div>
            </div>
            <OptionsPanel
              media={media}
              box={box}
              setBox={setBox}
              options={options}
              setOptions={setOptions}
              selectionMethod={selectionMethod}
              setSelectionMethod={setSelectionMethod}
              isDetecting={isDetecting}
              onAutoDetect={handleAutoDetect}
              onManualBox={handleManualBox}
              onProcess={handleProcess}
              onClearBox={() => setBox(null as any)}
            />
          </>
        )}

        {appState === 'processing' && (
          <ProcessingState progress={progress} statusText={statusText} />
        )}

        {appState === 'done' && resultUrl && media && (
          <ResultView
            resultUrl={resultUrl}
            originalUrl={media.url}
            mediaType={media.type}
            filename={resultFilename}
            onReset={handleReset}
          />
        )}
      </main>
    </div>
  );
}

// ── No-backend screen ─────────────────────────────────────────────────────────

function NoBackendScreen({ onRetry }: { onRetry: () => void }) {
  const { env } = useEnvironment();

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-background text-foreground">
      <div className="flex flex-col items-center gap-6 max-w-sm text-center px-6">
        <Logo size={72} />
        <div className="flex flex-col gap-1">
          <h1 className="text-xl font-semibold">Backend not running</h1>
          <p className="text-sm text-muted-foreground">
            The server needs to be running to use Watermark Remover.
          </p>
        </div>

        <div className="w-full rounded-lg border border-border bg-muted/50 p-4 text-left flex flex-col gap-3">
          {env === 'browser' ? (
            <>
              <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                <Globe className="w-3.5 h-3.5" />
                Browser mode
              </div>
              <p className="text-sm text-muted-foreground">Start the server locally:</p>
              <code className="text-xs bg-background border border-border rounded px-3 py-2 block font-mono">
                python -m app.server
              </code>
              <p className="text-xs text-muted-foreground">
                Or use the desktop app for a self-contained experience:
              </p>
              <code className="text-xs bg-background border border-border rounded px-3 py-2 block font-mono">
                python desktop.py
              </code>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                <Monitor className="w-3.5 h-3.5" />
                Desktop mode
              </div>
              <p className="text-sm text-muted-foreground">
                The backend failed to start. Try restarting the app.
              </p>
            </>
          )}
        </div>

        <Button onClick={onRetry} variant="outline" className="gap-2">
          <RefreshCw className="w-4 h-4" />
          Retry
        </Button>
      </div>
    </div>
  );
}

// ── Setup guard ───────────────────────────────────────────────────────────────

function SetupGuard({ children }: { children: React.ReactNode }) {
  const { env } = useEnvironment();
  const [status, setStatus] = useState<'checking' | 'online-complete' | 'online-setup' | 'offline'>('checking');

  const check = () => {
    setStatus('checking');
    fetch('/api/setup/status')
      .then((r) => r.json())
      .then((s) => setStatus(s.complete ? 'online-complete' : 'online-setup'))
      .catch(() => setStatus('offline'));
  };

  useEffect(() => {
    // Wait until env is resolved before checking, so desktop mode has time to
    // start the embedded server before we declare it offline.
    if (env === 'detecting') return;
    check();
  }, [env]);

  if (env === 'detecting' || status === 'checking') {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (status === 'offline') return <NoBackendScreen onRetry={check} />;
  if (status === 'online-setup') return <Navigate to="/setup" replace />;
  return <>{children}</>;
}

// ── Root ──────────────────────────────────────────────────────────────────────

export function App() {
  return (
    <ThemeProvider>
      <EnvironmentProvider>
        <HashRouter>
          <Routes>
            <Route path="/setup" element={<Onboarding />} />
            <Route
              path="/app"
              element={
                <SetupGuard>
                  <MainApp />
                </SetupGuard>
              }
            />
            <Route path="*" element={<Navigate to="/app" replace />} />
          </Routes>
        </HashRouter>
      </EnvironmentProvider>
    </ThemeProvider>
  );
}
