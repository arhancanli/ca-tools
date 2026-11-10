# Replay record for CA(32; 2, 1427, 3)

The array in this folder has sha256 901be6e03091c1795f1383c1aa6e9ba5da971a6a11d34e025ceb4211f091c0e2.
Three separate executions of the same two commands gave this identical file.

1. Apple Silicon Mac (arm64), 2026-11-10, first run. Command
   `ext2t p32_1155.txt 32 1155 0 0 13 1700 0.7 out/t32f -chain 600 -ntry 200 -kick 200000`.
   The seventh argument is only an abort limit in seconds and does not enter the search.
2. Linux x86_64, 2026-11-10, from-scratch replay. The same command with the abort limit 1700. Its full output is
   REPLAY_x86_second_run_log.txt. The array at 1427 columns was saved at move 46,965,623.
3. Linux x86_64, 2026-11-10, the recipe script recipe32.sh, which wrote RECIPE.log itself. The array at 1427
   columns was again saved at move 46,965,623.

In all three the input product p32_1155.txt has sha256
e277a927b85483c3a9a8e5cf2469191646816246034fbfc1085c006f71715dea and ext2t.c has sha256
39d0e5ab01803e6b7ad2e0cf6580837bcbffe5c6212c3c80590ad6d079c6e95e.

To replay, run `bash recipe32.sh` in this folder (it needs cc and python3) and compare the sha256 of the
CA_32_2_1427_3.txt it writes. It takes about half an hour on one core. The value after -chain must stay 600,
because it enters the search path.
