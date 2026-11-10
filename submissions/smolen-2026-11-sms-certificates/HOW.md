# How these arrays were built

Construction: the two strength-4 constructions of K. Shokri, L. Moura and B. Stevens, arXiv:2510.13122v3
(16 Oct 2026), for odd prime powers q, as the certificate kinds `sms51-1` and `sms65-1` of
`tools/construction_cert.py` (`tools/CONSTRUCTION_CERT.md`, "Shokri, Moura and Stevens"). `sms51-1` is their
Theorem 5.1, CA(3q^4 - 2; 4, (q^2+1)/2, q): three arrays of all F_q-linear combinations of 4 x (q^2+1)/2
generator matrices from the ovoid of PG(3, q) given by the powers alpha^((q+1)i) (multipliers 1, 2, 4),
stacked, two zero rows removed. `sms65-1` is their Theorem 6.2 with the ingredient size of their
Corollary 6.5, CA(3q^4 + (q - 2)(2q^3 - q); 4, q^2 + 1, q), with the strength-3 ingredient
CA(2q^3 - q; 3, (q^2+1)/2, q) built from the pair of orthogoval planes beta^j, beta^-j over F_(q^3). The checker
proves each array from these hypotheses, exactly: alpha (and beta) primitive, the plane and line lists complete,
the three truncated Moebius planes anti-cocircular (their Theorem 4.25, checked for the given q by listing every
circle through one point and using the cyclic shift), any three columns of the half matrices independent, the
four columns x, x + half, x', x' + half independent, and every three columns of the ingredient independent in
one of the two planes. Then it rebuilds the array in the table's canonical text and hashes it. Nothing is sampled.

| array | theorem | q | certificate check (2-core VM) |
|---|---|---|---|
| CA(250561; 4, 145, 17) | 5.1 | 17 | 2 s |
| CA(390961; 4, 181, 19) | 5.1 | 19 | 3 s |
| CA(839521; 4, 265, 23) | 5.1 | 23 | 7 s |
| CA(1171873; 4, 313, 25) | 5.1 | 25 = 5^2 | 17 s |
| CA(133874; 4, 170, 13) | 6.2, Cor. 6.5 | 13 | 1 s |
| CA(397698; 4, 290, 17) | 6.2, Cor. 6.5 | 17 | 4 s |
| CA(623846; 4, 362, 19) | 6.2, Cor. 6.5 | 19 | 6 s |
| CA(1350054; 4, 530, 23) | 6.2, Cor. 6.5 | 23 | 20 s |
| CA(1890050; 4, 626, 25) | 6.2, Cor. 6.5 | 25 = 5^2 | 32 s |

Built from: nothing but the certificates. Each names the field (F_q, and F_25 = F_5[y]/(y^2 + y + 1) for q = 25),
the primitive quartic over it, the column choice p = 0 (Theorem 5.1), and for Theorem 6.2 the primitive cubic and
the (q^2+1)/2 points of the ingredient. No array of the table is an ingredient, and no Torres-Jimenez array is used:
the ingredient of Theorem 6.2 has the size of their Theorem 3.4 (Torres-Jimenez and Izquierdo-Marquez 2018,
Remark 6.4 of the paper) but is built here from the orthogoval planes of their Theorem 3.3.

Program: `tools/sms_theorem51.py` and `tools/sms_theorem62.py` (numpy) wrote the certificates and, independently of
the checker, the arrays whose sha256 the certificates record. From the root of the repository

    python3 tools/sms_theorem51.py 17 --certificate C.json > CA_250561_4_145_17.txt
    python3 tools/sms_theorem62.py 25 --certificate C.json > CA_1890050_4_626_25.txt
    python3 tools/construction_cert.py submissions/smolen-2026-11-sms-certificates/CA_250561_4_145_17.cert.json

(the same for every q; the scripts print the same certificate as the one in this folder apart from its notes and key order,
and the checker prints CERTIFICATE VALID and the array_sha256 it records). The arrays are 0.1 to 3 GB as text
and are not stored; the certificates rebuild them in seconds.

Cross-checks:
- The arrays for q = 17, 19 (Theorem 5.1) and q = 17 (Theorem 6.2) were built separately on a second machine with
  the same scripts (before prime powers were added; the output for a prime q is unchanged, byte for byte) and
  verified there with ca_verify on every 4-set of columns, with the same sha256 as the rebuilds here.
  For q = 23 (Theorem 5.1) and q = 19, 23 (Theorem 6.2) the arrays built there have the same sha256 as well; they
  were screened there, and the full check of q = 23 (Theorem 5.1) was still running.
- The prime power arithmetic: at q = 9 both constructions were verified in full with ca_verify (19681 x 41 and
  29826 x 82), at q = 25 the Theorem 5.1 array on its first 20 columns and the Theorem 6.2 array on 12 columns
  that include the pairs x, x + half, and at q = 27 the Theorem 5.1 array on its first 16 columns.
- `tools/tests_construction/test_sms.py` compares the checker with an independent evaluation of every hypothesis on
  random small certificates, with mutation tests.

The rows already in the table as CITED (entered 2026-11-09 from the paper) stay; these rows add the VERIFIED
twins. The credit stays with Shokri, Moura and Stevens; the arrays are built and proved in ca-tools.
