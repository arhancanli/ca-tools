# CA(242; 5, 122, 2): Paley-type doubling (Colbourn 2015) of the Paley matrix over GF(121) = GF(11^2).
# Needs the R package CAs (Groemping), version 0.24.4.
library(CAs)
A <- CAs:::Double(CAs::paley_mat(121))
write.table(A, "p121.txt", row.names = FALSE, col.names = FALSE)
