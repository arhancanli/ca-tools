# How these arrays were built

Construction: the generalized direct product of strength-2 covering arrays (Colbourn, Martirosyan, Mullen,
Shasha, Sherwood and Yucas 2006; Colbourn and Torres-Jimenez 2013), as implemented in U. Groemping's R
package CAs 0.24.4. `recBoseCA(type = "CA")` and `productCA` save one row for each constant row of either
ingredient (Colbourn and Torres-Jimenez 2013, Corollary 4.3); `recBoseCA(type = "PCA")` multiplies
partitioned covering arrays (Colbourn and Torres-Jimenez 2013). Only Bose arrays and the fused Bose array
below go in; CAs's recursiveBose uses no stored data set.

| array | construction | ingredients |
|---|---|---|
| CA(451; 2, 20339, 11) | `recBoseCA(2, 20339, 11, type = "PCA")` | four Bose OA(121; 2, 12, 11) |
| CA(475; 2, 20736, 11) | `recBoseCA(2, 20736, 11, type = "CA")` | four Bose OA(121; 2, 12, 11) |
| CA(519; 2, 24192, 11) | `productCA(A, B)` | A = CA(165; 2, 14, 11), B = the table's CA(358; 2, 1728, 11) |

Built from:
- Bose OA(121; 2, 12, 11), made inside CAs (`SCA_Bose(11)`).
- `table/arrays/CA_358_2_1728_11.txt` (array_sha256 2539311d7e3dc04ab21a4f7198edbef2d8a0805826a077c11d86ea8076d7afb0,
  VERIFIED, itself `recBoseCA(2, 1728, 11, type = "CA")` of CAs).
- CA(165; 2, 14, 11), `programs/CA_165_2_14_11.txt` (sha256 25eb3336...): the Bose OA(169; 2, 14, 13)
  (`programs/OA_169_2_14_13.txt`, written by `programs/make_ingredients.py`) fused from 13 to 12 symbols
  (`programs/fuse12.json`, giving `programs/CA_167_2_14_12.txt`) and from 12 to 11 symbols
  (`programs/fuse11.json`), each by `fuse-1` of `tools/construction_cert.py` (Colbourn, Keri, Rivas Soriano and
  Schlage-Puchta 2010, Lemma 3.1) with rows 0 and 1.

Program: from the root of the repository, with R and CAs 0.24.4 from CRAN

    cd submissions/smolen-2026-11-t2-products/programs
    python3 make_ingredients.py
    python3 ../../../tools/construction_cert.py fuse12.json --write CA_167_2_14_12.txt
    python3 ../../../tools/construction_cert.py fuse11.json --write CA_165_2_14_11.txt
    cd ../../..
    mkdir -p /tmp/out && Rscript submissions/smolen-2026-11-t2-products/programs/build.R /tmp/out

`build.R` writes the three arrays 0-based and prints their sha256, which equal the files here:
dcb323c9... (451), 4ec78848... (475), 62ce6bcd... (519). `ca_verify` (repository root) at t = 2, v = 11
verified all three on every pair of columns on 2026-11-10.

Why these three. They close part of the narrow-width gap of CA(561; 2, 100000, 11), the Sherwood CPHF row of
Arhan Canli, which the frame gives from 20,001 columns on: 451 up to 20,339, 475 up to 20,736 and 519 up to
24,192. They replace an earlier version of this folder (CA(478; 2, 20736, 11) and CA(522; 2, 24192, 11) by
`product-1` of `tools/construction_cert.py`, which saves only one row): CAs saves one row for each constant
row of either ingredient. The CA(358; 2, 1728, 11) has three constant rows (`table/MANIFEST.csv`) and each
of OA(121; 2, 12, 11) and CA(165; 2, 14, 11) one, so N = N1 + N2 - 4: three rows fewer from the same
ingredients. At v = 9, 23 and 25 CAs's `N_d_recursiveBose` gives 369, 2047 and 2425, the sizes the frame
already has from 20,001 columns on, so nothing is submitted there.
