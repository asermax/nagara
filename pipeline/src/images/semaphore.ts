export const semaphore = (permits: number) => {
  let available = permits;
  const waiting: (() => void)[] = [];

  const acquire = async () => {
    if (available > 0) {
      available -= 1;

      return;
    }

    await new Promise<void>((resolve) => waiting.push(resolve));
  };

  // A released permit passes straight to the next waiter, so it is never counted as available in
  // between and taken by a newcomer.
  const release = () => {
    const next = waiting.shift();

    if (next == null) {
      available += 1;
    } else {
      next();
    }
  };

  return async <T>(work: () => Promise<T>) => {
    await acquire();

    try {
      return await work();
    } finally {
      release();
    }
  };
};
