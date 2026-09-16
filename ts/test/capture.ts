/** pytest's capsys, in six lines: swap console.log while a drawing call runs. */
export function capture(run: () => void): string {
  const lines: string[] = [];
  const original = console.log;
  console.log = (...args: unknown[]) => void lines.push(args.join(" "));
  try {
    run();
  } finally {
    console.log = original;
  }
  return lines.map((line) => line + "\n").join("");
}
