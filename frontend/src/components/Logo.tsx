import { useTheme } from '../contexts/ThemeContext';

interface LogoProps {
  size?: number;
  className?: string;
}

export function Logo({ size = 32, className }: LogoProps) {
  const { theme } = useTheme();
  const src = theme === 'dark' ? '/logo-dark.png' : '/logo-light.png';

  return (
    <img
      src={src}
      alt="Watermark Remover"
      width={size}
      height={size}
      className={className}
      style={{ borderRadius: size * 0.2 }}
    />
  );
}
