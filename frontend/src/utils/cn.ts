export function cn(...inputs: any[]) {
  return inputs
    .flat(Infinity)
    .filter((x) => typeof x === 'string' && x.trim() !== '')
    .join(' ');
}
