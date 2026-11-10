Construction: the binary covering arrays of Kleitman and Spencer (1973) and Katona (1973). An array has N rows; row 0 is all zeros, and each column holds ones exactly in a set of ceil(N/2) of the rows 1, ..., N-1, different sets for different columns. Two different columns of the same weight each have a row with (1, 0) and a row with (0, 1); since 2 ceil(N/2) > N - 1 they share a row with (1, 1); row 0 gives (0, 0). So N rows serve up to C(N-1, ceil(N/2)) columns, which is optimal: CAN(2, k, 2) is the least N with C(N-1, ceil(N/2)) >= k. The four arrays here are CA(18; 2, 24310, 2), CA(19; 2, 43758, 2), CA(20; 2, 92378, 2) and CA(21; 2, 100000, 2), so together they give the exact value at every k from 20,001 to 100,000.

Built from: nothing.

Program: the columns are the first k sets of ceil(N/2) elements of {1, ..., N-1} in lexicographic order (Python's itertools.combinations(range(1, N), (N + 1) // 2)); entry (r, c) is 1 when row r is in the set of column c, else 0. For example: `python3 -c 'import itertools; N, k = 21, 100000; S = [set(s) for s in itertools.islice(itertools.combinations(range(1, N), (N + 1) // 2), k)]; print("\n".join(" ".join("1" if r in s else "0" for s in S) for r in range(N)))'` prints CA(21; 2, 100000, 2).

The construction is Kleitman and Spencer's and Katona's. Arhan Canli (Quantavane) only enters these arrays; no credit for the construction is asked.

Checks before submission: every pair of columns of each array checked exactly by two programs of ours (bitsets in C; numpy), both passing; red controls (a duplicated column; one entry of row 0 flipped) fail both, at the same pair.

This submission was prepared with the help of Claude, an AI system from Anthropic. Arhan Canli takes responsibility for it.
