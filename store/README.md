# Stores

Two things are written as they happen, and read live when a number is needed.

- `reviews/` — one record per review round: its verdict, finding count, change
  size, and cost.
- `suites/` — one record per suite run.

Written by `bin/store.py review` and `bin/store.py suite`. Read by
`bin/store.py query`, which stamps every answer with the moment it ran.

A number that no query here can produce is a hole in collection. Closing the
hole is the task; estimating around it is not.
