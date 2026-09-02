/**
 * The slice of Python's `random.Random` that `data.ts` needs, bit-for-bit.
 *
 * A port of the datasets is worthless if `blobs(1)` disagrees across languages — the
 * answer key in `docs/answers.md` is keyed to the exact points Python produces. So this
 * is MT19937 with CPython's seeding, its `random()`, and its `gauss`/`shuffle`/`choices`
 * algorithms, not a lookalike PRNG. `test/parity.test.ts` holds it to that.
 */

const N = 624;
const M = 397;
const MATRIX_A = 0x9908b0df;
const UPPER_MASK = 0x80000000;
const LOWER_MASK = 0x7fffffff;
const TWO_PI = 2 * Math.PI;

const mul32 = (a: number, b: number): number => Math.imul(a, b) >>> 0;

/** Python's `round`: half-to-even, unlike JS's half-up `Math.round`. */
export function round(x: number): number {
  const floor = Math.floor(x);
  const frac = x - floor;
  if (frac > 0.5) return floor + 1;
  if (frac < 0.5) return floor;
  return floor % 2 === 0 ? floor : floor + 1;
}

export class Random {
  #mt = new Uint32Array(N);
  #index = N + 1;
  #gaussNext: number | null = null;

  constructor(seed = 0) {
    this.seed(seed);
  }

  seed(seed: number): void {
    // CPython splits |seed| into 32-bit little-endian words and calls init_by_array.
    const key: number[] = [];
    let n = Math.abs(Math.trunc(seed));
    do {
      key.push(n >>> 0);
      n = Math.floor(n / 4294967296);
    } while (n > 0);
    this.#initByArray(key);
    this.#gaussNext = null;
  }

  #initGenrand(s: number): void {
    const mt = this.#mt;
    mt[0] = s >>> 0;
    for (let i = 1; i < N; i++) {
      const prev = mt[i - 1]!;
      mt[i] = (mul32(1812433253, prev ^ (prev >>> 30)) + i) >>> 0;
    }
    this.#index = N;
  }

  #initByArray(key: number[]): void {
    this.#initGenrand(19650218);
    const mt = this.#mt;
    let i = 1;
    let j = 0;
    for (let k = Math.max(N, key.length); k > 0; k--) {
      const prev = mt[i - 1]!;
      mt[i] = (((mt[i]! ^ mul32(prev ^ (prev >>> 30), 1664525)) >>> 0) + key[j]! + j) >>> 0;
      i++;
      j++;
      if (i >= N) {
        mt[0] = mt[N - 1]!;
        i = 1;
      }
      if (j >= key.length) j = 0;
    }
    for (let k = N - 1; k > 0; k--) {
      const prev = mt[i - 1]!;
      mt[i] = (((mt[i]! ^ mul32(prev ^ (prev >>> 30), 1566083941)) >>> 0) - i) >>> 0;
      i++;
      if (i >= N) {
        mt[0] = mt[N - 1]!;
        i = 1;
      }
    }
    mt[0] = UPPER_MASK;
  }

  #genrand(): number {
    const mt = this.#mt;
    if (this.#index >= N) {
      for (let k = 0; k < N; k++) {
        const y = ((mt[k]! & UPPER_MASK) | (mt[(k + 1) % N]! & LOWER_MASK)) >>> 0;
        mt[k] = (mt[(k + M) % N]! ^ (y >>> 1) ^ (y & 1 ? MATRIX_A : 0)) >>> 0;
      }
      this.#index = 0;
    }
    let y = mt[this.#index++]!;
    y ^= y >>> 11;
    y = (y ^ ((y << 7) & 0x9d2c5680)) >>> 0;
    y = (y ^ ((y << 15) & 0xefc60000)) >>> 0;
    return (y ^ (y >>> 18)) >>> 0;
  }

  /** genrand_res53: 53 bits from two draws, assembled exactly as CPython does it. */
  random(): number {
    const a = this.#genrand() >>> 5;
    const b = this.#genrand() >>> 6;
    return (a * 67108864 + b) / 9007199254740992;
  }

  #getrandbits(k: number): number {
    return k === 0 ? 0 : this.#genrand() >>> (32 - k);
  }

  /** Rejection sampling on whole bits — why randint() burns a variable number of draws. */
  #below(n: number): number {
    const k = 32 - Math.clz32(n);
    let r = this.#getrandbits(k);
    while (r >= n) r = this.#getrandbits(k);
    return r;
  }

  randint(a: number, b: number): number {
    return a + this.#below(b - a + 1);
  }

  choice<T>(seq: readonly T[]): T {
    return seq[this.#below(seq.length)]!;
  }

  shuffle<T>(x: T[]): void {
    for (let i = x.length - 1; i > 0; i--) {
      const j = this.#below(i + 1);
      [x[i], x[j]] = [x[j]!, x[i]!];
    }
  }

  choices<T>(population: readonly T[], weights: readonly number[], k = 1): T[] {
    const cum: number[] = [];
    let running = 0;
    for (const w of weights) cum.push((running += w));
    const total = cum[cum.length - 1]!;
    const hi = population.length - 1;
    const out: T[] = [];
    for (let i = 0; i < k; i++) {
      const target = this.random() * total;
      let lo = 0; // bisect_right over cum[0:hi]
      let high = hi;
      while (lo < high) {
        const mid = (lo + high) >>> 1;
        if (target < cum[mid]!) high = mid;
        else lo = mid + 1;
      }
      out.push(population[lo]!);
    }
    return out;
  }

  /** Box-Muller with the second value cached, which is what makes draw order matter. */
  gauss(mu = 0, sigma = 1): number {
    let z = this.#gaussNext;
    this.#gaussNext = null;
    if (z === null) {
      const x2pi = this.random() * TWO_PI;
      const g2rad = Math.sqrt(-2 * Math.log(1 - this.random()));
      z = Math.cos(x2pi) * g2rad;
      this.#gaussNext = Math.sin(x2pi) * g2rad;
    }
    return mu + z * sigma;
  }
}
