## Submission

caverify 0.3.0. Speed release. A second exact method that checks each
set of t-1 columns against all later columns at once, one bit per
column, used by default where it fits in memory. Results are unchanged.
Full details in NEWS.md.

## Changes since 0.2.0

1. New method for the coverage check, many times faster on large
   arrays (about 40 to 50 times on the strength-4 binary arrays used in
   testing at a few hundred columns, growing with the number of
   columns). Same mixed-level support and same reading of NA as 0.2.0.
2. The method of 0.2.0 is kept as a fallback (above a memory budget,
   or above 64 symbols in a column) and can be selected with an option
   for comparison. The result gains one element, `kernel`, naming the
   method used.
3. Examples of missing combinations are now chosen deterministically
   (the first column sets with a gap in lexicographic order) for any
   number of threads.

## Testing of the new method

`covered`, `colsets`, `gaps`, `missing_tuples` and the examples agree
exactly with 0.2.0 on 1,900 random arrays (uniform, mixed-level and
binary, with and without NA, strengths 1 to 5, up to 600 columns, one to
four threads) and on 68 arrays derived from covering arrays of 'CAs'
(complete, a row removed, an entry changed, an entry set to NA). The
package tests compare the two methods on 60 further random arrays. The
code was also run under AddressSanitizer and UndefinedBehaviorSanitizer
without findings.

## Test environments

* local: Ubuntu 24.04, x86_64, R 4.3.3, gcc 13, `R CMD check --as-cran`:
  Status 3 NOTEs, all from the local environment (URLs on github.com
  return 403 through the network proxy there, "unable to verify current
  time", and the non-portable flag '-mno-omit-leaf-frame-pointer' set by
  the distribution's R build).
* local: macOS Golden Gate 27.0.1, aarch64-apple-darwin23, R 4.6.1
  (2026-06-24), Apple clang 21.0.0, `R CMD check --as-cran` on the
  submitted tarball (md5 2105cf6bb2b4c803579c98fbebde0f01), 2026-11-02: Status 1 NOTE.
* win-builder R-devel (2026-11-01 r90825 ucrt), on the same tarball,
  2026-11-02: Status OK.

## R CMD check results

0 errors | 0 warnings | 1 note

      checking HTML version of manual ... NOTE
      Skipping checking HTML validation: 'tidy' doesn't look like recent
      enough HTML Tidy.
      Skipping checking math rendering: package 'V8' unavailable

Local tooling only. It does not arise on CRAN.

## Reverse dependencies

* CAs 0.24-4 (Imports caverify (>= 0.2.0)): R CMD check with caverify
  0.3.0 installed, Status 1 NOTE (suggested package 'FrF2' not
  available in the test environment), tests OK. CAs uses only the
  `covered` element of the result.
* cafast 0.1.0 (Suggests caverify): Status OK.

## Notes for the reviewer

The package uses OpenMP where it is available, guarded by
`SHLIB_OPENMP_CFLAGS` in `src/Makevars` and `src/Makevars.win`, and runs
single-threaded where it is not. Threads default to half the logical
cores, are capped at two when `_R_CHECK_LIMIT_CORES_` is set, and can be
overridden with `options(caverify.threads)`.

## Previous submission record

0.1.2 submitted 2026-08-19, published 2026-08-20.
0.1.3 submitted 2026-08-23 (correction requested by the CRAN Team for
the fedora-clang flavour), published 2026-08-23.
0.2.0 published 2026-09-20.
