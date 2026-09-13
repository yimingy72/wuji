const canonicalDecimalRevision = /^(0|[1-9][0-9]*)$/;

export function isRevisionString(value: unknown): value is string {
  return typeof value === 'string' && canonicalDecimalRevision.test(value);
}

export function compareRevisionStrings(left: string, right: string): number {
  if (!isRevisionString(left) || !isRevisionString(right)) {
    throw new Error('Invalid canonical decimal revision');
  }
  if (left.length !== right.length) return left.length < right.length ? -1 : 1;
  if (left === right) return 0;
  return left < right ? -1 : 1;
}
