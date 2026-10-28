const hslToHex = (h: number, s: number, l: number) => {
  const a = (s * 100 * Math.min(l, 1 - l)) / 100;
  const f = (n: number) => {
    const k = (n + h / 30) % 12;
    const color = l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1);
    return Math.round(255 * color)
      .toString(16)
      .padStart(2, "0");
  };
  return `#${f(0)}${f(8)}${f(4)}`;
};

export { hslToHex };
export { default as capitalize } from "lodash/capitalize";
export { default as mapValues } from "lodash/mapValues";
export { default as pickBy } from "lodash/pickBy";
export { default as slugify } from "slugify";
