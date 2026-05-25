import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle,
  Download,
  Cpu,
  Zap,
  ChevronRight,
  AlertCircle,
  Loader2,
  Sun,
  Moon,
} from "lucide-react";
import {
  getSetupStatus,
  streamSetup,
  SetupStatus,
  SetupEvent,
} from "../utils/api";
import { Logo } from "../components/Logo";
import { useTheme } from "../contexts/ThemeContext";

// ── Types ────────────────────────────────────────────────────────────────────

type SetupStage = "checking" | "welcome" | "installing" | "done" | "error";

interface StepState {
  label: string;
  status: "pending" | "active" | "done" | "skipped" | "error";
  progress: number;
  detail: string;
}

const STEPS: Record<string, string> = {
  cv2: "OpenCV + NumPy",
  torch: "PyTorch",
  transformers: "Transformers + HuggingFace",
  florence2: "Florence-2 Model (~3 GB)",
};

// ── Component ────────────────────────────────────────────────────────────────

export function Onboarding() {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const [stage, setStage] = useState<SetupStage>("checking");
  const [setupStatus, setSetupStatus] = useState<SetupStatus | null>(null);
  const [steps, setSteps] = useState<Record<string, StepState>>(() =>
    Object.fromEntries(
      Object.entries(STEPS).map(([key, label]) => [
        key,
        { label, status: "pending" as const, progress: 0, detail: "" },
      ]),
    ),
  );
  const [overallProgress, setOverallProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState("");
  const [log, setLog] = useState<string[]>([]);
  const logRef = useRef<HTMLDivElement>(null);
  const cleanupRef = useRef<(() => void) | null>(null);

  // ── Check setup on mount ─────────────────────────────────────────────────
  useEffect(() => {
    getSetupStatus()
      .then((s) => {
        if (s.complete) {
          navigate("/app", { replace: true });
        } else {
          setSetupStatus(s);
          setStage("welcome");
        }
      })
      .catch(() => setStage("welcome"));

    return () => cleanupRef.current?.();
  }, []);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [log]);

  // ── Start installation ───────────────────────────────────────────────────
  const startInstall = () => {
    setStage("installing");
    const gpu = setupStatus?.gpu_available ?? false;

    const stepOrder = ["cv2", "torch", "transformers", "florence2"];
    let totalPct = 0;

    const cleanup = streamSetup(gpu, (event: SetupEvent) => {
      const { step, status, progress, done_step, all_done, error, skipped } =
        event;

      setLog((l) => [...l, status]);

      if (step && step in STEPS) {
        const idx = stepOrder.indexOf(step);
        const base = (idx / stepOrder.length) * 100;
        const share = 100 / stepOrder.length;
        totalPct = Math.round(base + (progress / 100) * share);
        setOverallProgress(totalPct);

        setSteps((prev) => ({
          ...prev,
          [step]: {
            ...prev[step],
            status: error
              ? "error"
              : done_step
                ? skipped
                  ? "skipped"
                  : "done"
                : "active",
            progress,
            detail: status,
          },
        }));
      }

      if (error) {
        setErrorMsg(status);
        setStage("error");
        return;
      }

      if (all_done) {
        setOverallProgress(100);
        setStage("done");
      }
    });

    cleanupRef.current = cleanup;
  };

  // ── Finish ────────────────────────────────────────────────────────────────
  const goToApp = () => navigate("/app", { replace: true });

  // ── Render ────────────────────────────────────────────────────────────────

  if (stage === "checking") {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex flex-col items-center justify-center bg-background text-foreground p-6 overflow-auto relative">
      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        className="absolute top-4 right-4 p-2 rounded-lg hover:bg-muted transition-colors text-muted-foreground"
        aria-label="Toggle theme"
      >
        {theme === "light" ? (
          <Moon className="w-4 h-4" />
        ) : (
          <Sun className="w-4 h-4" />
        )}
      </button>

      {/* Header */}
      <div className="mb-8 text-center">
        <div className="flex items-center justify-center gap-3 mb-3">
          <Logo size={48} className="shadow-lg" />
          <h1 className="text-3xl font-bold tracking-tight">
            Watermark Remover
          </h1>
        </div>
        <p className="text-muted-foreground text-sm">
          {stage === "welcome" &&
            "First-time setup — downloads required components once"}
          {stage === "installing" && "Setting up components…"}
          {stage === "done" && "Setup complete!"}
          {stage === "error" && "Setup encountered an error"}
        </p>
      </div>

      {/* Card */}
      <div className="w-full max-w-md bg-card border border-border rounded-2xl shadow-xl overflow-hidden">
        {/* ── Welcome ─────────────────────────────────────────────────────── */}
        {stage === "welcome" && (
          <div className="p-6 space-y-5">
            {/* GPU badge */}
            <div
              className={`flex items-center gap-3 p-3 rounded-xl border ${setupStatus?.gpu_available ? "bg-green-500/10 border-green-500/30" : "bg-muted border-border"}`}
            >
              {setupStatus?.gpu_available ? (
                <>
                  <Zap className="w-5 h-5 text-green-500 shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-green-600 dark:text-green-400">
                      NVIDIA GPU detected
                    </p>
                    <p className="text-xs text-muted-foreground">
                      CUDA acceleration will be used
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <Cpu className="w-5 h-5 text-muted-foreground shrink-0" />
                  <div>
                    <p className="text-sm font-medium">CPU mode</p>
                    <p className="text-xs text-muted-foreground">
                      No GPU detected — processing will be slower
                    </p>
                  </div>
                </>
              )}
            </div>

            {/* What will be downloaded */}
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                What will be downloaded
              </p>
              <div className="space-y-2">
                {Object.entries(STEPS).map(([key, label]) => {
                  const installed =
                    (key === "cv2" && setupStatus?.cv2_installed) ||
                    (key === "torch" && setupStatus?.torch_installed) ||
                    (key === "transformers" &&
                      setupStatus?.transformers_installed) ||
                    (key === "florence2" && setupStatus?.florence_downloaded);
                  return (
                    <div key={key} className="flex items-center gap-2 text-sm">
                      {installed ? (
                        <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
                      ) : (
                        <Download className="w-4 h-4 text-muted-foreground shrink-0" />
                      )}
                      <span
                        className={
                          installed ? "text-muted-foreground line-through" : ""
                        }
                      >
                        {label}
                      </span>
                      {installed && (
                        <span className="text-xs text-muted-foreground ml-auto">
                          already installed
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            <p className="text-xs text-muted-foreground">
              Total download: ~{setupStatus?.gpu_available ? "5–8" : "4–6"} GB
              depending on what's already installed. Models are cached locally
              and only downloaded once.
            </p>

            <button
              onClick={startInstall}
              className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground rounded-xl py-3 font-semibold hover:opacity-90 transition-opacity"
            >
              Start Setup
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* ── Installing ─────────────────────────────────────────────────── */}
        {stage === "installing" && (
          <div className="p-6 space-y-5">
            {/* Overall progress */}
            <div>
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>Overall progress</span>
                <span>{overallProgress}%</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-500"
                  style={{ width: `${overallProgress}%` }}
                />
              </div>
            </div>

            {/* Step list */}
            <div className="space-y-3">
              {Object.entries(steps).map(([key, step]) => (
                <StepRow key={key} step={step} />
              ))}
            </div>

            {/* Log */}
            <div
              ref={logRef}
              className="h-24 bg-muted rounded-lg p-2 overflow-y-auto font-mono text-xs text-muted-foreground space-y-0.5"
            >
              {log.map((line, i) => (
                <div key={i}>{line}</div>
              ))}
              {log.length === 0 && <div className="opacity-50">Waiting…</div>}
            </div>

            <p className="text-xs text-muted-foreground text-center">
              Please keep this window open. This may take several minutes.
            </p>
          </div>
        )}

        {/* ── Done ─────────────────────────────────────────────────────────── */}
        {stage === "done" && (
          <div className="p-6 text-center space-y-5">
            <div className="flex justify-center">
              <div className="w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center">
                <CheckCircle className="w-10 h-10 text-green-500" />
              </div>
            </div>
            <div>
              <h2 className="text-xl font-bold">All done!</h2>
              <p className="text-sm text-muted-foreground mt-1">
                Everything is set up and ready to use.
              </p>
            </div>
            <button
              onClick={goToApp}
              className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground rounded-xl py-3 font-semibold hover:opacity-90 transition-opacity"
            >
              Open App
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* ── Error ────────────────────────────────────────────────────────── */}
        {stage === "error" && (
          <div className="p-6 space-y-4">
            <div className="flex items-start gap-3 p-3 rounded-xl bg-destructive/10 border border-destructive/30">
              <AlertCircle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-destructive">
                  Setup failed
                </p>
                <p className="text-xs text-muted-foreground mt-1">{errorMsg}</p>
              </div>
            </div>
            <div
              ref={logRef}
              className="h-32 bg-muted rounded-lg p-2 overflow-y-auto font-mono text-xs text-muted-foreground"
            >
              {log.map((line, i) => (
                <div key={i}>{line}</div>
              ))}
            </div>
            <button
              onClick={() => {
                setStage("welcome");
                setLog([]);
                setOverallProgress(0);
                setSteps(
                  Object.fromEntries(
                    Object.entries(STEPS).map(([k, l]) => [
                      k,
                      {
                        label: l,
                        status: "pending" as const,
                        progress: 0,
                        detail: "",
                      },
                    ]),
                  ),
                );
              }}
              className="w-full border border-border rounded-xl py-2.5 text-sm font-medium hover:bg-muted transition-colors"
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Step Row sub-component ────────────────────────────────────────────────────

function StepRow({ step }: { step: StepState }) {
  const { label, status, progress, detail } = step;

  const icon = {
    pending: (
      <div className="w-4 h-4 rounded-full border-2 border-muted-foreground/30" />
    ),
    active: <Loader2 className="w-4 h-4 animate-spin text-primary" />,
    done: <CheckCircle className="w-4 h-4 text-green-500" />,
    skipped: <CheckCircle className="w-4 h-4 text-muted-foreground" />,
    error: <AlertCircle className="w-4 h-4 text-destructive" />,
  }[status];

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <span className="shrink-0">{icon}</span>
        <span
          className={`text-sm font-medium ${status === "pending" ? "text-muted-foreground" : status === "error" ? "text-destructive" : ""}`}
        >
          {label}
        </span>
        {status === "skipped" && (
          <span className="text-xs text-muted-foreground ml-auto">
            already installed
          </span>
        )}
        {status === "active" && (
          <span className="text-xs text-muted-foreground ml-auto">
            {progress}%
          </span>
        )}
      </div>
      {status === "active" && (
        <>
          <div className="ml-6 h-1 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          {detail && (
            <p className="ml-6 text-xs text-muted-foreground truncate">
              {detail}
            </p>
          )}
        </>
      )}
    </div>
  );
}
