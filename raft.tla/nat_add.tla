---- MODULE nat_add ----
EXTENDS Naturals

VARIABLES n, m

Init == n = 0 /\ m = 0

Next == /\ n' = n + 1
        /\ m' = m + 1

Spec == Init /\ [][Next]_<<n, m>>

Commutative == n + m = m + n

====