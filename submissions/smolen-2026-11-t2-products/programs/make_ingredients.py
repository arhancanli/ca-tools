"""Writes the orthogonal array used by submissions/smolen-2026-11-t2-products.

OA(q^2; 2, q+1, q) for a prime q (Bose 1938; Bush 1952): the rows are the pairs (a, b), a and b in
0..q-1, in the order a * q + b; column x (0 <= x < q) holds a + b x mod q, and column q holds b.
Row (a, b) = (0, 0) is the all-0 row.

Run in this folder: python3 make_ingredients.py
It writes OA_169_2_14_13.txt (q = 13, sha256 0aef1e42...). The fused array CA(165; 2, 14, 11) is then made by tools/construction_cert.py
from fuse12.json and fuse11.json (HOW.md)."""


def oa(q):
    return [[(a + b * x) % q for x in range(q)] + [b] for a in range(q) for b in range(q)]


def text(rows):
    return "".join(" ".join(map(str, r)) + "\n" for r in rows)


if __name__ == "__main__":
    open("OA_169_2_14_13.txt", "w").write(text(oa(13)))
