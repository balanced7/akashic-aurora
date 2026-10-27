/**
Creates an ID generator.
The total length of the ID is the sum of the prefix, separator, and random part length.
Not cryptographically secure.

@param alphabet - The alphabet to use for the ID. Default: '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'.
@param prefix - The prefix of the ID to generate. Optional.
@param separator - The separator between the prefix and the random part of the ID. Default: '-'.
@param size - The size of the random part of the ID to generate. Default: 16.
 */
export const createIdGenerator = ({
  prefix,
  size = 32,
  alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
  separator = "-",
}: {
  prefix?: string;
  separator?: string;
  size?: number;
  alphabet?: string;
} = {}) => {
  const generator = () => {
    const alphabetLength = alphabet.length;
    const chars = new Array(size);
    for (let i = 0; i < size; i++) {
      chars[i] = alphabet[(Math.random() * alphabetLength) | 0];
    }
    return chars.join("");
  };

  if (prefix == null) {
    return generator;
  }

  // check that the prefix is not part of the alphabet (otherwise prefix checking can fail randomly)
  if (alphabet.includes(separator)) {
    throw new Error(
      `The separator "${separator}" must not be part of the alphabet "${alphabet}".`,
    );
  }

  return () => `${prefix}${separator}${generator()}`;
};

export const generateId = createIdGenerator();
