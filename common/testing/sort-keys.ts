export const byKey = ([left]: [string, unknown], [right]: [string, unknown]) =>
  left.localeCompare(right);

export const sortKeys = (value: unknown): unknown => {
  if (Array.isArray(value)) {
    return value.map(sortKeys);
  }

  if (value != null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .sort(byKey)
        .map(([key, entry]) => [key, sortKeys(entry)]),
    );
  }

  return value;
};
