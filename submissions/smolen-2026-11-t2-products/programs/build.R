# Rebuilds the three arrays of submissions/smolen-2026-11-t2-products with U. Groemping's R package CAs
# (version 0.24.4, CRAN). Run from the root of the repository:
#   Rscript submissions/smolen-2026-11-t2-products/programs/build.R OUTDIR
# It writes CA_475_2_20736_11.txt (about 11 s), CA_519_2_24192_11.txt (seconds) and CA_451_2_20339_11.txt
# (about 25 minutes) to OUTDIR, 0-based, one run per line, and prints the sha256 of each.
suppressMessages(library(CAs))
stopifnot(packageVersion("CAs") == "0.24.4")
out <- commandArgs(trailingOnly = TRUE)[1]
stopifnot(!is.na(out), dir.exists(out))
wr <- function(A, f) {
  A <- unclass(A); attributes(A) <- list(dim = dim(A)); storage.mode(A) <- "integer"
  if (min(A) == 1) A <- A - 1L
  p <- file.path(out, f)
  write.table(A, p, row.names = FALSE, col.names = FALSE, quote = FALSE)
  cat(f, nrow(A), "x", ncol(A), system(paste("sha256sum", shQuote(p)), intern = TRUE), "\n")
}
here <- "submissions/smolen-2026-11-t2-products/programs"
# 1. four Bose OA(121; 2, 12, 11) multiplied by the generalized direct product (type CA)
wr(recBoseCA(2, 20736, 11, type = "CA"), "CA_475_2_20736_11.txt")
# 2. the fused Bose CA(165; 2, 14, 11) times the table's CA(358; 2, 1728, 11)
A <- as.matrix(read.table(file.path(here, "CA_165_2_14_11.txt")))
B <- as.matrix(read.table("table/arrays/CA_358_2_1728_11.txt"))
wr(productCA(A, B), "CA_519_2_24192_11.txt")
# 3. four Bose OA(121; 2, 12, 11) multiplied as partitioned covering arrays (type PCA)
wr(recBoseCA(2, 20339, 11, type = "PCA"), "CA_451_2_20339_11.txt")
