import { Sun, Moon, Plus } from 'lucide-react';
import { Button } from './Button';
import { Logo } from './Logo';
import { useTheme } from '../contexts/ThemeContext';

interface TopBarProps {
  onNew: () => void;
  showNew: boolean;
}

export function TopBar({ onNew, showNew }: TopBarProps) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="h-14 border-b border-border bg-card flex items-center justify-between px-4 sm:px-6 shrink-0">
      <div className="flex items-center gap-2.5">
        <Logo size={32} className="shadow-sm" />
        <div className="flex flex-col leading-tight">
          <span className="font-heading font-semibold text-sm tracking-tight">
            Watermark Remover
          </span>
          <span className="text-[10px] text-muted-foreground font-mono">
            v1.0
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {showNew && (
          <Button
            variant="outline"
            size="sm"
            onClick={onNew}
            className="gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            New
          </Button>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          aria-label="Toggle theme"
        >
          {theme === 'light' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
        </Button>
      </div>
    </header>
  );
}
