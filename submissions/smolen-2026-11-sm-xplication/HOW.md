# How these arrays were built

Construction: the strength-3 x-plication constructions of K. Shokri and L. Moura, New families of strength-3
covering arrays using linear feedback shift register sequences, J. Combin. Des. 33 (2025) 156-171, as stated in
Chapter 5 of K. Shokri's PhD thesis (University of Ottawa, 2026, doi:10.20381/ruor-31663; the journal text was not
read here, so the theorem numbers are the thesis's). They are checked as the certificate kind `sm-xplication-1` of
`tools/construction_cert.py` (`tools/CONSTRUCTION_CERT.md`, "Shokri and Moura, x-plication"). All five are the
general theorem of the thesis (Theorem 5.2.6): x column blocks, each a copy of the CA(2q^3 - 1; 3, q^2+q+1, q) of a
primitive cubic and its inverse (A(G1) over A(G2)), shifted block by block by the rows of a difference covering array
D, then q - 2 or 2q - 3 blocks of a CA(2q^2 - q; 2, q^2+q+1, q) shifted the same way, then a last block whose rows
are those of a strength-3 array on the x blocks that the blocks above do not already give. The checker proves each
array from these hypotheses, exactly: any two columns of G1 (and of G2) independent, no 3 columns dependent in both
(all pairs of lines of the two planes compared), the strength-2 array checked on every pair of columns, D checked on
every pair of columns, and the last block together with the shifts of D checked on every 3-set of the x blocks. Then
it rebuilds the array in the table's canonical text and hashes it. Nothing is sampled.

| array | thesis | q | x | certificate check (2-core VM) |
|---|---|---|---|---|
| CA(2281; 3, 2793, 7) | Theorem 5.2.11 (q^2-plication) | 7 | 49 | 0.6 s |
| CA(2275; 3, 2451, 7) | Theorem 5.2.13 ((q^2-q+1)-plication) | 7 | 43 | 0.4 s |
| CA(3480; 3, 4672, 8) | Corollary 5.2.12 (q^2-plication, even q) | 8 = 2^3 | 64 | 2 s |
| CA(46069; 3, 1106, 23) | Theorem 5.2.7 (2-plication) | 23 | 2 | 6 s |
| CA(59425; 3, 1302, 25) | Theorem 5.2.7 (2-plication) | 25 = 5^2 | 2 | 12 s |
| CA(18976; 3, 4368, 16) | Theorem 5.2.8 (q-plication) | 16 = 2^4 | 16 | 3 s |
| CA(22865; 3, 5219, 17) | Theorem 5.2.8 (q-plication) | 17 | 17 | 4 s |
| CA(32167; 3, 7239, 19) | Theorem 5.2.8 (q-plication) | 19 | 19 | 8 s |
| CA(57707; 3, 12719, 23) | Theorem 5.2.8 (q-plication) | 23 | 23 | 24 s |
| CA(74425; 3, 16275, 25) | Theorem 5.2.8 (q-plication) | 25 = 5^2 | 25 | 42 s |

Built from: nothing but the certificates. Each names the field (F_8 = F_2[y]/(y^3 + y^2 + 1), F_16 = F_2[y]/(y^4 +
y^3 + 1), F_25 = F_5[y]/(y^2 + y + 1)), the primitive cubic, the evaluation points of the strength-2 array, the
difference covering array D and the generator matrices of the last block. No array of the table is an ingredient.

Program: `tools/sm_xplication.py` (numpy) wrote the certificates and, independently of the checker, the arrays whose
sha256 the certificates record. The script follows the thesis's own deletions of rows; the checker computes which
rows the blocks above already give and checks that the rest still covers. From the root of the repository

    python3 tools/sm_xplication.py q 25 --certificate C.json > CA_74425_3_16275_25.txt
    python3 tools/sm_xplication.py q2even 8 --certificate C.json > CA_3480_3_4672_8.txt
    python3 tools/construction_cert.py submissions/smolen-2026-11-sm-xplication/CA_74425_3_16275_25.cert.json

(THEOREM is 2, q, q2, q2even or q2q1; the script prints the same certificate as the one in this folder, and the
checker prints CERTIFICATE VALID and the array_sha256 it records). The arrays are 11 MB to 3.2 GB as text and are not
stored here; the certificates rebuild them in seconds.

Cross-checks:
- The same script, at smaller q, rebuilds byte for byte (the same sha256) 18 arrays the table already has as VERIFIED
  rows from this paper: Bai XunDi's 2-plication arrays at q = 3, 5, 7, 9, 13, 16, 17, 19 and q-plication arrays at
  q = 4, 5, 7, 8, 9, 11, 13 (Zenodo 23787055; at q = 8 and 16 with his moduli y^3 + y + 1 and y^4 + y + 1), and
  T. N. Sitjar's thesis arrays CA(364; 3, 336, 4) (Corollary 5.2.12), CA(769; 3, 775, 5) (Theorem 5.2.11) and
  CA(765; 3, 651, 5) (Theorem 5.2.13, with his cubic x^3 + 3x + 2). All 18 are VERIFIED rows of the table, checked
  there on every 3-set with ca_verify.
- `tools/tests_construction/test_smx.py` checks the script against the checker for all five theorems at small q
  (ca_verify on every 3-set), compares the checker with an independent evaluation of every hypothesis on random
  certificates, with mutation tests, and checks these ten certificates with planted faults.

Two places where the thesis is not exact (`tools/CONSTRUCTION_CERT.md`): Theorem 5.2.13 needs G2' to have q - 1
columns with first entry 0, which holds for some primitive cubics and not others (21 of the 36 at q = 7), so the
certificate for CA(2275; 3, 2451, 7) uses the first cubic for which it holds; and the strength-2 ingredient "CA(2q^2 -
q; 2, q^2+q+1, q) in Corollary 5.1.9" is the first q^2+q+1 columns of the corollary's q^2+2q. Neither changes a size.

The rows already in the table as CITED (entered 2026-11-09 from the thesis) stay; these rows add the VERIFIED twins.
The credit stays with Shokri and Moura; the arrays are built and proved in ca-tools.
