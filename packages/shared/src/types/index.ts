type Replace<
  S extends string,
  From extends string,
  To extends string,
> = S extends `${infer L}${From}${infer R}`
  ? `${L}${To}${Replace<R, From, To>}`
  : S;

export type EnumToConstant<T extends readonly string[]> = {
  [K in Uppercase<Replace<T[number], "-", "_">>]: Extract<
    T[number],
    Lowercase<Replace<K, "_", "-">>
  >;
};
