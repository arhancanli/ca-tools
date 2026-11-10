# Contributing

This project takes covering arrays and certificates, each submitted as a new directory under `submissions/` (see `submissions/README.md`).
The table covers strengths 2 to 6, alphabets of up to 25 symbols and up to 100,000 columns.
A verified array past the baseline's column range whose size is above a published size rule at its width or wider (table/derived.csv) is still welcome; the report flags it and the maintainer decides it.
Pull requests that change code, tests, workflows or documents are closed unmerged.
Please report a fault as an issue. The maintainer writes every fix himself.
To report a published bound that the table is missing, or a credit that is wrong, open an issue with the template "Published bound or credit" (`.github/ISSUE_TEMPLATE/published-bound.md`): the paper (DOI or arXiv id), the theorem or table, and the sizes as CA(N; t, k, v). No array is needed. The size is entered as a CITED row with credit to its authors, or the credit is corrected with a line in `table/CREDIT_CORRECTIONS.csv`.
Many arrays here were found with AI-written search programs, and the rows say so where it is known. Every array is checked before it is entered, whatever produced it: exactly (VERIFIED), or, when it is too large for the exact check in the time the public check has, on random column windows (SCREENED, listed but not counted as best known until its exact check passes). Credit goes to the people who submit it and the published methods it uses.
